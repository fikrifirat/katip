"""A deliberately tiny MCP (JSON-RPC 2.0) server core with no dependencies.

Why not the MCP SDK: the local connector must install with nothing but Python's
standard library (plus optional `cryptography`), so it can ship inside a Claude
plugin or an MCPB bundle without native wheels. MCP over stdio is newline-
delimited JSON-RPC, and we only need initialize / tools/list / tools/call / ping.

Logging rule: nothing that came from a document or a tool argument is ever
written to a log. We log method names, tool names and durations only.
"""
from __future__ import annotations

import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

SUPPORTED = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
log = logging.getLogger("katip")


@dataclass
class Tool:
    name: str
    title: str
    description: str
    schema: dict
    fn: Callable[..., dict]
    annotations: dict = field(default_factory=dict)

    def describe(self) -> dict:
        return {"name": self.name, "title": self.title, "description": self.description,
                "inputSchema": self.schema, "annotations": {"title": self.title, **self.annotations}}


class Server:
    def __init__(self, name: str, version: str, instructions: str, tools: list[Tool]):
        self.name, self.version, self.instructions = name, version, instructions
        self.tools = {t.name: t for t in tools}

    def handle(self, msg: dict) -> dict | None:
        """One JSON-RPC message in, one response out (None for notifications)."""
        mid, method = msg.get("id"), msg.get("method", "")
        if mid is None:  # notification, e.g. notifications/initialized
            return None
        t0 = time.monotonic()
        try:
            result = self._dispatch(method, msg.get("params") or {})
            return {"jsonrpc": "2.0", "id": mid, "result": result}
        except _RpcError as e:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": e.code, "message": e.message}}
        finally:
            log.info("rpc %s %.0fms", method, (time.monotonic() - t0) * 1000)

    def _dispatch(self, method: str, params: dict) -> Any:
        if method == "initialize":
            want = params.get("protocolVersion")
            return {"protocolVersion": want if want in SUPPORTED else SUPPORTED[0],
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": self.name, "version": self.version},
                    "instructions": self.instructions}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [t.describe() for t in self.tools.values()]}
        if method == "tools/call":
            tool = self.tools.get(params.get("name"))
            if not tool:
                raise _RpcError(-32602, f"unknown tool {params.get('name')!r}")
            try:
                out = tool.fn(**(params.get("arguments") or {}))
                return {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
                        "structuredContent": out, "isError": False}
            except TypeError as e:
                return _tool_error(f"bad arguments: {e}")
            except (OSError, ValueError, RuntimeError, KeyError) as e:
                return _tool_error(str(e))
            except Exception:  # noqa: BLE001
                log.error("tool %s crashed: %s", tool.name, traceback.format_exc(limit=1).splitlines()[-1][:120])
                return _tool_error("internal error")
        raise _RpcError(-32601, f"method not found: {method}")


def _tool_error(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": True}


class _RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message
