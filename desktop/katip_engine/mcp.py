"""Katip's MCP tools for Claude (`katip-engine mcp`), limited to the features switched on in the Mac app.

Kalkan's local server does the work; this wraps it so Claude sees a feature's tools only while the feature is on
and ready (features.visible_tools), refuses a call to a hidden tool, and tells a running Claude when the list
changes (notifications/tools/list_changed), so a switch flipped in the app reaches it within seconds.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading

from . import features, settings

HIDDEN = ("Bu özellik Katip uygulamasında kapalı ya da henüz kurulmadı (Katip → Özellikler). · This feature is off "
          "or not set up yet in the Katip app (Katip → Features).")


class Gate:
    def __init__(self, out, server=None):
        if server is None:
            from katip_kalkan import local_server
            server = local_server.build()
        self.server, self.out = server, out
        self.lock = threading.Lock()
        self.shown: set[str] | None = None  # what Claude last listed; None until it asks

    def visible(self) -> set[str]:
        """What Claude may see. If working that out fails, the core tools (masking) stay and every feature hides."""
        names = set(self.server.tools)
        try:
            return features.visible_tools(names)
        except Exception:  # noqa: BLE001
            logging.getLogger("katip").warning("feature check failed; showing core tools only")
            return names - features.GATED

    def handle(self, msg: dict) -> dict | None:
        method, mid = msg.get("method", ""), msg.get("id")
        if mid is not None and method == "tools/list":
            vis = self.visible()
            self.shown = vis
            return {"jsonrpc": "2.0", "id": mid,
                    "result": {"tools": [t.describe() for n, t in self.server.tools.items() if n in vis]}}
        if mid is not None and method == "tools/call":
            name = (msg.get("params") or {}).get("name")
            if name in features.GATED and name in self.server.tools and name not in self.visible():
                return {"jsonrpc": "2.0", "id": mid,
                        "result": {"content": [{"type": "text", "text": HIDDEN}], "isError": True}}
        resp = self.server.handle(msg)
        if method == "initialize" and resp and "result" in resp:
            resp["result"]["capabilities"]["tools"] = {"listChanged": True}
        return resp

    def send(self, obj) -> None:
        with self.lock:
            self.out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self.out.flush()

    def check(self) -> bool:
        """Tell Claude if what it may see changed since it last asked. True when a notice went out."""
        if self.shown is None:
            return False
        vis = self.visible()
        if vis == self.shown:
            return False
        self.shown = vis
        self.send({"jsonrpc": "2.0", "method": "notifications/tools/list_changed"})
        return True


def _watch(gate: Gate, interval: float) -> None:
    last = None
    while True:
        try:
            try:
                m = settings.path().stat().st_mtime
            except OSError:
                m = None
            if m != last:
                last = m
                settings.apply(folders=True)
            gate.check()  # also catches setup done elsewhere: MASAK lists fetched, a browser downloaded
        except Exception:  # noqa: BLE001 - never let the watcher take the server down
            logging.getLogger("katip").warning("settings watch failed", exc_info=False)
        threading.Event().wait(interval)


def _safe(gate: Gate, m: dict) -> dict | None:
    """One bad message never stops the server (and with it every Katip tool)."""
    try:
        return gate.handle(m)
    except Exception:  # noqa: BLE001
        logging.getLogger("katip").error("request failed", exc_info=False)
        if m.get("id") is None:
            return None
        return {"jsonrpc": "2.0", "id": m["id"], "error": {"code": -32603, "message": "internal error"}}


def main(argv: list[str]) -> None:
    logging.basicConfig(stream=sys.stderr, level=os.environ.get("KATIP_LOG", "WARNING"),
                        format="katip %(levelname)s %(message)s")
    settings.apply(folders=True)
    from . import review
    review.install("claude")  # before the tools are built, so they use the hooked detection
    gate = Gate(sys.stdout)
    threading.Thread(target=_watch, args=(gate, 2.0), daemon=True, name="katip-settings").start()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            gate.send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        batch = msg if isinstance(msg, list) else [msg]
        resps = [r for r in (_safe(gate, m) for m in batch if isinstance(m, dict)) if r is not None]
        if resps:
            gate.send(resps if isinstance(msg, list) else resps[0])
