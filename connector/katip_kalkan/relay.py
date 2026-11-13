"""Katip relay: the remote MCP connector for ChatGPT (and claude.ai on the web).

The relay never sees an original document and never sees a real name.

  1. On the lawyer's device (Katip app or `katip-kalkan share`), the file is masked
     locally and the masked text is encrypted with a fresh one-time key.
  2. The device uploads only nonce + ciphertext to POST /v1/drops and gets an id.
  3. The lawyer pastes the share code "katip-<id>.<key>" into ChatGPT.
  4. ChatGPT calls the MCP tool open_masked_document(share_code); the relay decrypts in
     memory, returns the masked text and deletes the drop.

Zero retention: drops live in RAM only (no disk, no database), expire after
KATIP_RELAY_TTL seconds (default 900) and are deleted after KATIP_RELAY_MAX_READS
reads (default 1). The relay stores ciphertext only; the key exists only in the share
code. Access logs carry method, path, status and size, never bodies or codes.

    python -m katip_kalkan.relay --port 8787     # put TLS (Caddy/nginx) in front
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from .mcp_proto import Server, Tool
from .vault import b64u, open_sealed, unb64u

log = logging.getLogger("katip.relay")
TTL = int(os.environ.get("KATIP_RELAY_TTL", 900))
MAX_READS = int(os.environ.get("KATIP_RELAY_MAX_READS", 1))
MAX_DROP = int(os.environ.get("KATIP_RELAY_MAX_KB", 2048)) * 1024
MAX_TOTAL = int(os.environ.get("KATIP_RELAY_MAX_TOTAL_MB", 256)) * 1024 * 1024
CODE = re.compile(r"katip-([A-Za-z0-9_-]{16})\.([A-Za-z0-9_-]{22})")


class DropStore:
    """In-memory, expiring, read-limited. Nothing here is ever written to disk."""

    def __init__(self):
        self._d: dict[str, dict] = {}
        self._lock = threading.Lock()

    def put(self, nonce: bytes, ct: bytes, ttl: int) -> str:
        with self._lock:
            self._sweep()
            if sum(len(v["ct"]) for v in self._d.values()) + len(ct) > MAX_TOTAL:
                raise MemoryError("relay is full, try again in a few minutes")
            drop_id = b64u(secrets.token_bytes(12))
            self._d[drop_id] = {"nonce": nonce, "ct": ct, "exp": time.time() + min(ttl, TTL), "reads": 0}
            return drop_id

    def take(self, drop_id: str) -> tuple[bytes, bytes] | None:
        with self._lock:
            self._sweep()
            v = self._d.get(drop_id)
            if not v:
                return None
            v["reads"] += 1
            if v["reads"] >= MAX_READS:
                del self._d[drop_id]
            return v["nonce"], v["ct"]

    def _sweep(self):
        now = time.time()
        for k in [k for k, v in self._d.items() if v["exp"] < now]:
            del self._d[k]

    def __len__(self):
        with self._lock:
            self._sweep()
            return len(self._d)


STORE = DropStore()


def open_masked_document(share_code: str) -> dict:
    m = CODE.search(share_code or "")
    if not m:
        raise ValueError("this is not a Katip share code (it looks like katip-XXXX.YYYY)")
    got = STORE.take(m.group(1))
    if not got:
        raise ValueError("this share code has expired or was already used; ask the user to share the file "
                         "again from the Katip app")
    try:
        doc = json.loads(open_sealed(unb64u(m.group(2)), *got))
    except Exception:  # noqa: BLE001 - wrong key or tampered ciphertext
        raise ValueError("this share code could not be opened") from None
    return {**doc, "note": ("Masked on the user's device; placeholders like [AD SOYAD-1] stand for real values "
                            "that never left it. Keep them exactly as written so Katip can restore them.")}


INSTRUCTIONS = """Katip opens documents that a lawyer masked on their own computer with the Katip app.
When the user gives a code that looks like katip-XXXX.YYYY, call open_masked_document with it.
The text contains placeholders such as [AD SOYAD-1]; keep them exactly as written in your answer.
Never ask the user for the real names or for the original file."""

TOOLS = [Tool(
    "open_masked_document", "Open a Katip-masked document",
    "Fetch a document that the user already masked on their own computer with Katip (KVKK-safe). "
    "Takes the share code the user pasted (katip-XXXX.YYYY). Codes work once and expire in 15 minutes.",
    {"type": "object", "properties": {"share_code": {"type": "string"}}, "required": ["share_code"],
     "additionalProperties": False},
    open_masked_document,
    {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False})]

MCP = Server("katip-relay", __version__, INSTRUCTIONS, TOOLS)


class Handler(BaseHTTPRequestHandler):
    server_version = "katip-relay"
    sys_version = ""

    def log_message(self, fmt, *args):  # default logs the request line; ours adds nothing from bodies
        pass

    def _send(self, code: int, body: dict | None = None, extra: dict | None = None):
        raw = b"" if body is None else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Strict-Transport-Security", "max-age=31536000")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
        log.info("%s %s %d %dB", self.command, self.path.split("?")[0], code, len(raw))

    def _cors(self) -> dict:
        allowed = [o for o in os.environ.get("KATIP_RELAY_ORIGINS", "").split(",") if o]
        origin = self.headers.get("Origin", "")
        if origin and origin in allowed:
            return {"Access-Control-Allow-Origin": origin, "Vary": "Origin",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Access-Control-Allow-Methods": "POST, OPTIONS"}
        return {}

    def _body(self) -> bytes | None:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_DROP * 2:
            self._send(413, {"error": "too large"})
            return None
        return self.rfile.read(n)

    def do_OPTIONS(self):
        self._send(204, None, self._cors())

    def do_GET(self):
        if self.path == "/healthz":
            return self._send(200, {"ok": True, "drops": len(STORE), "version": __version__})
        if self.path.startswith("/mcp"):
            return self._send(405, {"error": "use POST"}, {"Allow": "POST"})
        self._send(404, {"error": "not found"})

    def do_DELETE(self):
        self._send(405 if self.path.startswith("/mcp") else 404, {"error": "no sessions"})

    def do_POST(self):
        body = self._body()
        if body is None:
            return
        if self.path == "/v1/drops":
            return self._drop(body)
        if self.path.startswith("/mcp"):
            return self._mcp(body)
        self._send(404, {"error": "not found"})

    def _drop(self, body: bytes):
        cors = self._cors()
        token = os.environ.get("KATIP_RELAY_UPLOAD_TOKEN")
        if token and not secrets.compare_digest(self.headers.get("Authorization", ""), f"Bearer {token}"):
            return self._send(401, {"error": "unauthorized"}, cors)
        try:
            d = json.loads(body)
            nonce, ct = unb64u(d["nonce"]), unb64u(d["ciphertext"])
            assert len(nonce) == 12 and 16 < len(ct) <= MAX_DROP
        except Exception:  # noqa: BLE001
            return self._send(400, {"error": "expected {nonce, ciphertext} as base64url"}, cors)
        try:
            drop_id = STORE.put(nonce, ct, int(d.get("ttl", TTL)))
        except MemoryError as e:
            return self._send(503, {"error": str(e)}, cors)
        self._send(201, {"id": drop_id, "expires_in": min(int(d.get("ttl", TTL)), TTL), "max_reads": MAX_READS}, cors)

    def _mcp(self, body: bytes):
        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            return self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
        batch = msg if isinstance(msg, list) else [msg]
        resps = [r for r in (MCP.handle(m) for m in batch) if r is not None]
        if not resps:
            return self._send(202)
        self._send(200, resps if isinstance(msg, list) else resps[0])


def serve(host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args()
    logging.basicConfig(level=os.environ.get("KATIP_LOG", "INFO"), format="relay %(message)s")
    srv = serve(a.host, a.port)
    log.info("listening on %s:%d (ttl %ss, max reads %d)", a.host, a.port, TTL, MAX_READS)
    srv.serve_forever()


if __name__ == "__main__":
    main()
