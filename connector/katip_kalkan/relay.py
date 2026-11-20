"""Katip relay: the remote MCP connector for ChatGPT (and claude.ai on the web).

The relay never sees an original document and never sees a real name.

Tools: open_masked_document (below), plus the same research tools as the local Kalkan:
emsal_ara (Yargıtay decisions; only lowercase keywords go to the court's public search), mevzuat_bak
(statutes, offline index) and geri_bildirim (the lawyer's verdict on a decision, from the gavel button in
the results view). ChatGPT shows emsal_ara results with the same MCP Apps view as Claude (ui/emsal.html).

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

from pathlib import Path

from . import __version__, emsal, mevzuat
from .mcp_proto import Resource, Server, Tool
from .vault import b64u, open_sealed, unb64u

log = logging.getLogger("katip.relay")
TTL = int(os.environ.get("KATIP_RELAY_TTL", 900))
MAX_READS = int(os.environ.get("KATIP_RELAY_MAX_READS", 1))
MAX_DROP = int(os.environ.get("KATIP_RELAY_MAX_KB", 2048)) * 1024
MAX_TOTAL = int(os.environ.get("KATIP_RELAY_MAX_TOTAL_MB", 256)) * 1024 * 1024
DROPS_PER_HOUR = int(os.environ.get("KATIP_RELAY_DROPS_PER_HOUR", 60))  # per client address
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


class RateLimit:
    """At most n uploads per address per hour (the web app can't hold a secret upload token)."""

    def __init__(self, n: int):
        self.n, self._seen, self._lock = n, {}, threading.Lock()

    def allow(self, who: str) -> bool:
        now = time.time()
        with self._lock:
            hits = [t for t in self._seen.get(who, []) if now - t < 3600]
            if len(hits) >= self.n:
                self._seen[who] = hits
                return False
            self._seen[who] = hits + [now]
            if len(self._seen) > 10000:  # forget idle addresses
                self._seen = {k: v for k, v in self._seen.items() if v and now - v[-1] < 3600}
            return True


UPLOADS = RateLimit(DROPS_PER_HOUR)


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


INSTRUCTIONS = """Katip opens documents that a lawyer masked on their own device with the Katip app or the
katip-kalkan command, and finds Turkish case law and statutes for them.
When the user gives a code that looks like katip-XXXX.YYYY, call open_masked_document with it.
The text contains placeholders such as [AD SOYAD-1]; keep them exactly as written in your answer, so Katip can
put the real values back on the user's device. Never ask the user for the real names or for the original file,
and if they paste or attach an unmasked client document, say that it has already been sent with the message and
point them to the Katip app (https://fikrifirat.github.io/katip) for next time.
For case law ("emsal", "içtihat", "Yargıtay kararı"), call emsal_ara with 1-5 short lowercase keyword queries
that name the legal issue (never names, digits or places). You may pass baglam: one or two masked sentences that
state the issue, used only to rank the results. Present each result with its decision number, link, outcome and
the quoted paragraph; never invent or alter a decision number, and cite only decisions the tool returned. Ask the
lawyer to judge the ones they read with the gavel ("Hüküm ver") button on each card, or in words, and save each
verdict with geri_bildirim.
Before you state what a statute article says, or when the user asks to check citations, call mevzuat_bak.
Remind the user once to review the work: Katip can miss a value, and the AI can be wrong about the law."""

UI_DIR = Path(__file__).parent / "ui"
EMSAL_UI = "ui://katip-kalkan/emsal.html"
DIGITS = re.compile(r"\d{5,}|@|https?://")
GRADES_NOTE = ("Hükümleriniz Katip'e gider: yalnızca karar kimliği, arama kelimeleri ve verdiğiniz hüküm; "
               "sizi tanıtan bir bilgi ya da belge metni saklanmaz.")


def emsal_ara(sorgular: list[str], baglam: str = "", alan: str | None = None, adet: int = 8) -> dict:
    """Same search as the local Kalkan, run on the relay. ChatGPT only ever saw masked text, so the real values
    are not in its context; the query rule (lowercase words only, no digits or signs) still applies, and the
    optional context must look masked (no long digit runs, e-mail addresses or links). Nothing here is stored
    except the public run record (query words, decision ids) that geri_bildirim needs."""
    baglam = (baglam or "")[:3000]
    if DIGITS.search(baglam):
        raise ValueError("baglam must be masked text: it has a long number, an e-mail address or a link. Use the "
                         "placeholders (e.g. [T.C. KİMLİK NO-1]) instead, or leave baglam empty.")
    out = emsal.find(sorgular, "relay", baglam, alan, max(1, min(int(adet), 10)))
    out["note"] = ("Only the queries in queries_sent were sent to the court's public search (bedesten.adalet.gov.tr); "
                   "baglam was used for ranking and not stored. Every decision's esas/karar numbers were found in the "
                   "official text, and the quote is word for word. Read the decision before citing it.")
    out["grades_note"] = GRADES_NOTE
    return out


def geri_bildirim(result_id: str, puan: int, atif_yapar: bool | None = None) -> dict:
    """The lawyer's verdict on one result. No free-text note here: notes could carry client details."""
    r = emsal.grade(result_id, puan, atif_yapar, "", "relay")
    r.pop("grades_on_this_computer", None)
    r["where"] = "Katip relay (decision id, query words and the verdict only)"
    return r


TOOLS = [
    Tool("open_masked_document", "Open a Katip-masked document",
         "Fetch a document that the user already masked on their own device with Katip. "
         "Takes the share code the user pasted (katip-XXXX.YYYY). Codes work once and expire in 15 minutes.",
         {"type": "object", "properties": {"share_code": {"type": "string"}}, "required": ["share_code"],
          "additionalProperties": False},
         open_masked_document,
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}),
    Tool("emsal_ara", "Yargıtay kararı ara · Search Yargıtay decisions",
         "Finds Yargıtay decisions for a legal issue from the official source (mevzuat.adalet.gov.tr). Only the "
         "lowercase keywords in sorgular are sent to the court's search; a query with capitals, digits or signs is "
         "refused before anything is sent. baglam (optional) is masked text stating the issue, used only to rank. "
         "A decision whose esas/karar numbers are not in the official text is not shown. Takes about 30 seconds.",
         {"type": "object", "properties": {
             "sorgular": {"type": "array", "minItems": 1, "maxItems": 5,
                          "items": {"type": "string", "description": "1-5 lowercase words, no names/digits/places"},
                          "description": "Short keyword queries naming the legal issue, e.g. \"kira tespit hakkaniyet\""},
             "baglam": {"type": "string", "maxLength": 3000,
                        "description": "Optional: one or two masked sentences stating the issue (placeholders, no names)"},
             "alan": {"type": "string", "enum": ["ceza", "hukuk"],
                      "description": "Criminal or civil: also searches that General Assembly"},
             "adet": {"type": "integer", "minimum": 1, "maximum": 10, "default": 8}},
          "required": ["sorgular"], "additionalProperties": False},
         emsal_ara,
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
         {"ui": {"resourceUri": EMSAL_UI}}),
    Tool("mevzuat_bak", "Kanun maddesi / atıf denetimi · Statute lookup",
         "Returns a Turkish statute article (e.g. \"TBK 344\", \"İş Kanunu 25/II\") or checks every statute "
         "citation in a text: does the article exist, is it in force or repealed, do number and name match. Uses "
         "Katip's offline copy of mevzuat.adalet.gov.tr; its date is in the result.",
         {"type": "object", "properties": {
             "atif": {"type": "string", "description": "One citation, e.g. \"TBK 344\""},
             "metin": {"type": "string", "maxLength": 20000,
                       "description": "A masked text whose statute citations should all be checked"}},
          "additionalProperties": False},
         lambda atif="", metin="": mevzuat.lookup(atif, metin),
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("geri_bildirim", "Karara hüküm ver · Judge a decision",
         "Saves the lawyer's verdict on one emsal_ara result: 0 not relevant, 1 related, 2 would cite. Stores "
         "only the decision id, the query words and the verdict; nothing that identifies the user.",
         {"type": "object", "properties": {
             "result_id": {"type": "string", "description": "result_id from emsal_ara"},
             "puan": {"type": "integer", "enum": [0, 1, 2], "description": "0 not relevant, 1 related, 2 would cite"},
             "atif_yapar": {"type": "boolean", "description": "Would the lawyer cite it?"}},
          "required": ["result_id", "puan"], "additionalProperties": False},
         geri_bildirim,
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
]
VIEWS = [Resource(EMSAL_UI, "Emsal sonuçları", "text/html;profile=mcp-app",
                  lambda: (UI_DIR / "emsal.html").read_text(encoding="utf-8"),
                  # no csp domains: the view cannot reach the network; it only talks to the host
                  {"ui": {"prefersBorder": False,
                          **({"domain": os.environ["KATIP_RELAY_PUBLIC_URL"]}
                             if os.environ.get("KATIP_RELAY_PUBLIC_URL") else {})}})]

MCP = Server("katip-relay", __version__, INSTRUCTIONS, TOOLS, None, VIEWS)


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
        who = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
        if not UPLOADS.allow(who):
            return self._send(429, {"error": "too many uploads, try again later"}, {**cors, "Retry-After": "600"})
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
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8787)))
    a = ap.parse_args()
    logging.basicConfig(level=os.environ.get("KATIP_LOG", "INFO"), format="relay %(message)s")
    srv = serve(a.host, a.port)
    log.info("listening on %s:%d (ttl %ss, max reads %d)", a.host, a.port, TTL, MAX_READS)
    srv.serve_forever()


if __name__ == "__main__":
    main()
