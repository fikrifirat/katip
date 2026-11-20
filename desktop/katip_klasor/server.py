"""The window's backend: a small HTTP API on 127.0.0.1 with a random token, plus the static UI.

The window (pywebview) or a browser tab loads http://127.0.0.1:<port>/?t=<token>. Every API call must carry
the token, so another program or web page on the same computer can't read the review data."""
from __future__ import annotations

import json
import mimetypes
import os
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from katip_kalkan import engine, ner

from . import __version__, layout, modules, pipeline, store
from .watcher import Watcher

UI = Path(__file__).resolve().parent / "ui"
PREVIEW_CHARS = 120_000


def _job_row(j: dict) -> dict:
    open_flags = [f for f in j.get("flags", []) if f["kind"] != "ocr"]
    return {"key": j["key"], "name": j["name"], "safe": j["safe"], "status": j["status"], "kind": j.get("kind"),
            "profile": j.get("profile"), "flags": len(open_flags), "ocr": j.get("ocr", False),
            "counts": j.get("counts", {}), "outputs": j.get("outputs", []), "error": j.get("error"),
            "at": j.get("at"), "released_at": j.get("released_at")}


def state(w: Watcher) -> dict:
    s = store.load_settings()
    root = layout.ensure(store.folder(s))
    cases = []
    for case in [layout.GENERAL] + layout.cases(root):
        jobs = store.load_jobs(case)
        if case == layout.GENERAL and not jobs:
            continue
        rows = sorted((_job_row(j) for j in jobs.values()), key=lambda r: -(r["at"] or 0))
        cases.append({"name": case, "profile": (s.get("profiles") or {}).get(case) or s.get("default_profile", "ai"),
                      "terms": (s.get("terms") or {}).get(case, {"mask": [], "keep": []}), "jobs": rows})
    return {"version": __version__, "root": str(root), "warning": layout.synced_warning(root), "cases": cases,
            "busy": w.busy, "error": w.last_error, "settings": {k: s[k] for k in ("model", "lang", "auto_release", "default_profile")},
            "profiles": {k: v["label"] for k, v in engine.PROFILES.items()}, "folders": list(layout.FOLDERS),
            "modules": modules.catalogue()}


def preview(job: dict) -> list[dict]:
    """The document as segments: plain text, a span that will be masked, or a candidate that won't."""
    text = job["text"][:PREVIEW_CHARS]
    fl = {(f["type"], pipeline.norm(f["value"])): f for f in job["flags"] if f["kind"] != "ocr"}
    final = pipeline.final_spans(job)
    marks = [dict(s, m="mask") for s in final]
    marks += [dict(c, m="cand") for c in job["cands"] if not pipeline._overlaps(c, final)]
    out, pos = [], 0
    for s in sorted(marks, key=lambda s: (s["start"], -s["end"])):
        if s["start"] < pos or s["start"] >= len(text):
            continue
        if s["start"] > pos:
            out.append({"t": text[pos:s["start"]]})
        f = fl.get((s["entity_type"], pipeline.norm(s["text"])))
        out.append({"t": text[s["start"]:s["end"]], "m": s["m"], "type": pipeline.type_label(s["entity_type"]),
                    "flag": f["id"] if f else None})
        pos = s["end"]
    if pos < len(text):
        out.append({"t": text[pos:]})
    if len(job["text"]) > PREVIEW_CHARS:
        out.append({"t": "\n\n[… önizleme burada kesildi; maskeleme belgenin tamamına uygulanır]"})
    return out


def open_path(p: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    elif os.name == "nt":
        os.startfile(str(p))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(p)])


class Api:
    def __init__(self, w: Watcher):
        self.w = w

    def root(self) -> Path:
        return layout.ensure(store.folder())

    def get_job(self, q):
        case, key = q["case"], q["key"]
        j = store.load_jobs(case)[key]
        row = _job_row(j)
        if j["status"] == "error":
            return {"job": row, "flags": [], "segments": []}
        return {"job": row, "flags": j["flags"], "segments": preview(j), "readers": j.get("readers", [])}

    def post_decide(self, b):
        j = pipeline.set_decision(b["case"], b["key"], b["flag"], b["decision"])
        return {"segments": preview(j), "flags": j["flags"]}

    def post_release(self, b):
        s = store.load_settings()
        try:
            j = pipeline.release(self.root(), b["case"], b["key"], s, who=store._user())
        except pipeline.Changed as e:
            self.w.kick()
            return {"error": str(e)}
        return {"job": _job_row(j)}

    def post_reprocess(self, b):
        s = store.load_settings()
        root = self.root()
        keys = [b["key"]] if b.get("key") else [k for k, j in store.load_jobs(b["case"]).items() if j["status"] != "released"]
        for k in keys:
            p = root / layout.INBOX / k
            if p.exists():
                pipeline.process(root, p, s, force=True)
        return {"ok": True, "n": len(keys)}

    def post_profile(self, b):
        if b["profile"] not in engine.PROFILES:
            raise ValueError("unknown profile")
        s = store.load_settings()
        s.setdefault("profiles", {})[b["case"]] = b["profile"]
        store.save_settings(s)
        return self.post_reprocess({"case": b["case"]})

    def post_term(self, b):
        term = " ".join(str(b["term"]).split())
        if len(term) < 2:
            raise ValueError("term too short")
        s = store.load_settings()
        t = s.setdefault("terms", {}).setdefault(b["case"], {"mask": [], "keep": []})
        lst = t.setdefault(b["action"], [])
        if b.get("remove"):
            t[b["action"]] = [x for x in lst if x != term]
        elif term not in lst:
            lst.append(term)
        store.save_settings(s)
        return self.post_reprocess({"case": b["case"], "key": b.get("key")})

    def post_restore(self, b):
        return pipeline.restore_text(self.root(), b["text"], b.get("case") or None, "cevap", ".docx")

    def post_open(self, b):
        root = self.root()
        top = {"inbox": layout.INBOX, "out": layout.OUT, "answers": layout.ANSWERS, "restored": layout.RESTORED}[b["which"]]
        d = layout.case_dir(root, top, b["case"]) if b.get("case") else root / top
        d.mkdir(parents=True, exist_ok=True)
        open_path(d)
        return {"ok": True}

    def post_case(self, b):
        name = layout.nfc(" ".join(str(b["name"]).split())).strip(". ")
        if not name or any(c in name for c in '/\\:*?"<>|') or name == layout.GENERAL:
            raise ValueError("Bu ad klasör adı olamaz.")
        (self.root() / layout.INBOX / name).mkdir(parents=True, exist_ok=True)
        return {"ok": True, "case": name}

    def post_settings(self, b):
        s = store.load_settings()
        for k in ("model", "lang", "auto_release", "default_profile", "folder"):
            if k in b:
                s[k] = b[k]
        store.save_settings(s)
        self.w.kick()
        return {"ok": True}

    def post_forget(self, b):
        pipeline.forget(b["case"])
        return {"ok": True}

    def post_scan(self, b):
        self.w.kick()
        return {"ok": True}

    def get_audit(self, q):
        return {"rows": store.audit_rows(q["case"])}

    def get_status(self, q):
        return {"engine": ner.describe(), "detection": engine.source(), "version": __version__}


def make_handler(api: Api, token: str):
    class H(BaseHTTPRequestHandler):
        server_version = "KatipKlasor"

        def log_message(self, *a):  # quiet: request lines would put file names in a terminal
            pass

        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; frame-ancestors 'none'")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def _authed(self, q) -> bool:
            got = self.headers.get("X-Katip-Token") or (q.get("t") or [""])[0]
            return secrets.compare_digest(got, token)

        def _route(self, method: str):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if not u.path.startswith("/api/"):
                if method != "GET":
                    return self._send(405, b"", "text/plain")
                rel = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
                f = (UI / rel).resolve()
                if not str(f).startswith(str(UI.resolve())) or not f.is_file():
                    return self._send(404, b"not found", "text/plain")
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                if f.suffix == ".js":
                    ctype = "text/javascript"
                return self._send(200, f.read_bytes(), ctype)
            if not self._authed(q):
                return self._json({"error": "token"}, 403)
            name = u.path[len("/api/"):]
            if name == "state":
                return self._json(state(api.w))
            if name == "audit.csv":
                body = store.audit_csv(q["case"][0]).encode("utf-8-sig")
                return self._send(200, body, "text/csv; charset=utf-8",
                                  {"Content-Disposition": 'attachment; filename="katip-kayit.csv"'})
            fn = getattr(api, f"{method.lower()}_{name}", None)
            if not fn:
                return self._json({"error": "not found"}, 404)
            try:
                if method == "GET":
                    return self._json(fn({k: v[0] for k, v in q.items()}))
                n = int(self.headers.get("Content-Length") or 0)
                if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{self.server.server_address[1]}"):
                    return self._json({"error": "origin"}, 403)
                body = json.loads(self.rfile.read(n) or b"{}")
                return self._json(fn(body))
            except (KeyError, ValueError, FileNotFoundError, StopIteration) as e:  # includes pipeline.Ambiguous
                return self._json({"error": str(e) or e.__class__.__name__}, 400)
            except Exception as e:  # noqa: BLE001
                return self._json({"error": f"{e.__class__.__name__}: {e}"}, 500)

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

    return H


def serve(port: int = 0, watcher: Watcher | None = None, token: str | None = None):
    """Start the API in a thread. Returns (url, server, watcher)."""
    w = watcher or Watcher()
    token = token or secrets.token_urlsafe(24)
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Api(w), token))
    threading.Thread(target=srv.serve_forever, name="katip-api", daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}/?t={token}", srv, w
