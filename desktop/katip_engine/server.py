"""The engine's HTTP API. Local only, token only, one document at a time.

Routes (JSON in, JSON out):

    GET  /healthz                 {"ok": true}; the only route without the token
    GET  /v1/status               version, uptime, memory, model, profile list, sources and whether they're on
    POST /v1/mask                 {text, profile?, matter?} -> masked text, placeholders, counts
    POST /v1/mask_file            {path, profile?, matter?, page?} -> Kalkan's mask_file result
    POST /v1/restore              {text, matter?} -> the text with real values back. For local apps only:
                                  never pass its answer to an AI model.
    POST /v1/forget               {matter} -> deletes that case's key
    POST /v1/sources/mevzuat      {citation_text?, text?} -> statute lookup, offline
    POST /v1/sources/emsal        {queries, ...} -> precedent search; off unless KATIP_EMSAL_ONLINE=1
    POST /v1/shutdown             stop the engine (launchd starts it again on the next `start`)

  Setup, for the Mac app (desktop/macos):
    GET  /v1/settings  POST /v1/settings {model?, default_profile?, emsal_online?, documents_folder?, ...}
    GET  /v1/models                which models are on this Mac, and the running download's progress
    POST /v1/models/download       {name, use?} -> 202; downloads in the background, switches if use is true
    POST /v1/models/delete {name}  POST /v1/models/custom {path}  POST /v1/models/custom/remove {path}
    GET  /v1/matters               cases with a key on this Mac (labels kept encrypted)
    GET  /v1/claude  POST /v1/claude/connect {app}  POST /v1/claude/disconnect {app}   (desktop | code)
    GET  /v1/features              each extra feature: on, state, what it needs, its setup job
    POST /v1/features {id, enabled}   POST /v1/features/action {id, action}  (refresh | install_browser | logout)
    GET  /v1/paths                 where models, cases, MASAK lists, gazette pages, the log are kept
    GET  /v1/review                the review queue (masking candidates) and the learned lists
    POST /v1/review/judge {id, verdict: mask|allow|later}  /v1/review/undo {id}  /v1/review/learned/remove {list, text}

Why these rules: the measured serving study (lab/inference/RESULTS.md) found that on CPU one document at a time
gives the best latency, and that batching can change int8 results; that a fresh process answers in well under
a second; and that dropping a model inside a running process doesn't give its memory back. So the engine runs
one request at a time and exits after --idle-exit seconds instead of unloading anything.
"""
from __future__ import annotations

import json
import os
import resource
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import DEFAULT_PORT, __version__

MAX_BODY = 20 * 2**20  # 20 MB of JSON is far more than any document's text


def state_file() -> Path:
    from katip_kalkan.vault import katip_home
    return katip_home() / "engine.json"


def rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / 2**20 if sys.platform == "darwin" else peak / 1024, 1)


class Engine:
    """Wraps Kalkan's detection, case vault and leak check. One call at a time."""

    def __init__(self):
        from katip_kalkan import core, engine, ner, vault
        from . import settings
        self.core, self.engine, self.ner, self.vault = core, engine, ner, vault
        settings.apply()
        from . import review
        review.install("app")  # learned lists apply to every document; unsure names join the review queue
        self.lock = threading.Lock()
        self.started = time.time()
        self.served = 0

    def mask(self, text: str, profile: str | None = None, matter: str = "default") -> dict:
        c = self.core
        t = time.perf_counter()
        with self.lock:
            profile = c._profile(profile)
            v = self.vault.open_vault(matter)
            spans = c._detect(text, v, profile)
            masked, spans = c._mask_safely(text, v, spans)  # raises rather than return a readable detected value
            v.save()
            self.served += 1
            self._touch(matter)
        return {"masked_text": masked, "matter": matter, "profile": profile,
                "entity_counts": c._counts(spans),
                "placeholders": sorted({v.labels[f"{s['entity_type']}|{self.vault._norm(s['text'])}"] for s in spans}),
                "ms": round((time.perf_counter() - t) * 1000, 1)}

    def mask_file(self, path: str, profile: str | None = None, matter: str = "default", page: int = 1) -> dict:
        with self.lock:
            self.served += 1
            out = self.core.mask_file(path=path, matter=matter, page=page, profile=profile)
            self._touch(matter)
        return out

    def restore(self, text: str, matter: str = "default") -> dict:
        with self.lock:
            restored, n = self.vault.open_vault(matter).unmask(text)
        return {"text": restored, "placeholders_restored": n}

    def forget(self, matter: str) -> dict:
        from . import matters
        with self.lock:
            out = self.core.forget_matter(matter)
            matters.drop(matter)
        return out

    @staticmethod
    def _touch(matter: str) -> None:
        from . import matters
        matters.touch(matter)

    # -- setup ----------------------------------------------------------------------------------------------
    def settings_get(self) -> dict:
        from . import settings
        return settings.load()

    def settings_set(self, body: dict) -> dict:
        from . import models, settings
        settings.validate(body)
        if "model" in body and not models.downloaded(body["model"], verify=True):
            raise Conflict(f"download the {body['model']} model first (POST /v1/models/download)")
        with self.lock:
            return settings.save(body)

    def models_get(self) -> dict:
        from . import models, settings
        st = settings.load()
        return models.listing(st["model"], st["custom_models"])

    def models_delete(self, body: dict) -> dict:
        from . import models, settings
        name = str(body["name"])
        if name not in ("mini", "base"):
            raise settings.Invalid("only a downloaded Mini or Base can be deleted (Nano is part of the app)")
        if settings.load()["model"] == name:
            raise Conflict("this model is in use: pick another one first")
        with self.lock:
            models.delete(name)
        return self.models_get()

    def models_custom(self, body: dict, add: bool) -> dict:
        from . import models, settings
        p = str(body["path"])
        if not Path(p).is_absolute():
            raise settings.Invalid("path must be a full path")
        p = str(Path(p).resolve())
        st = settings.load()
        with self.lock:
            if add:
                if not models.is_model_folder(Path(p)):
                    raise settings.Invalid("not a Katip model folder (config.json, tokenizer.json, "
                                           "onnx/model_quantized.onnx)")
                if p not in st["custom_models"]:
                    settings.save({"custom_models": [*st["custom_models"], p]})
            else:
                if st["model"] == p:
                    raise Conflict("this model is in use: pick another one first")
                settings.save({"custom_models": [c for c in st["custom_models"] if c != p]})
        return self.models_get()

    def paths(self) -> dict:
        """Where everything is kept, for the app's Show in Finder buttons."""
        from katip_kalkan.dd.store import home as dd_home
        from katip_kalkan.vault import katip_home
        from katip_mask import models as sdk
        from . import claude, cli, settings
        st, h, dd = settings.load(), katip_home(), dd_home()
        return {"katip": str(h), "cases": str(h / "vault"), "documents": st["documents_folder"],
                "downloads": str(Path.home() / "Downloads"), "models": str(sdk.cache_dir()), "masak": str(dd),
                "gazette": str(dd / "tsg"), "precedents": str(h / "emsal"), "log": str(cli.LOG),
                "claude_desktop": str(claude.desktop_config())}

    def review_get(self) -> dict:
        from . import review
        return review.listing()

    def review_post(self, what: str, body: dict) -> dict:
        from . import review
        if what == "judge":
            return review.judge(str(body["id"]), str(body["verdict"]))
        if what == "undo":
            return review.undo(str(body["id"]))
        if what == "reset":
            review.reset()
            return review.listing()
        return review.forget_learned(str(body["list"]), str(body["text"]))

    def features_get(self) -> dict:
        from . import features
        return features.listing()

    def features_set(self, body: dict) -> dict:
        from . import features
        with self.lock:
            return features.set_enabled(str(body["id"]), body["enabled"])

    def features_act(self, body: dict) -> dict:
        from . import features
        return features.act(str(body["id"]), str(body["action"]))

    def models_download(self, body: dict) -> dict:
        from . import models, settings
        name = str(body["name"])
        if name not in settings.MODELS:
            raise settings.Invalid(f"model must be one of {', '.join(settings.MODELS)}")
        use = bool(body.get("use"))
        return {"download": models.start_download(name, on_done=(lambda n: self.settings_set({"model": n})) if use else None)}

    def matters_get(self) -> dict:
        from . import matters
        return {"matters": matters.listing()}

    def claude_get(self) -> dict:
        from . import claude
        return claude.status()

    def claude_change(self, body: dict, on: bool) -> dict:
        from . import claude
        app = str(body["app"])
        if app not in ("desktop", "code"):
            from .settings import Invalid
            raise Invalid("app must be desktop or code")
        try:
            return claude.connect(app) if on else claude.disconnect(app)
        except claude.Refused as x:
            raise Conflict(str(x))

    def mevzuat(self, citation_text: str = "", text: str = "") -> dict:
        from katip_kalkan import mevzuat
        return mevzuat.lookup(citation_text=citation_text, text=text)

    def emsal(self, body: dict) -> dict:
        from katip_kalkan import emsal
        args = {k: body[k] for k in ("queries", "reference", "domain", "limit", "fetch", "matter") if k in body}
        return emsal.find(**args)  # raises PermissionError while precedent search is switched off

    def status(self) -> dict:
        from katip_kalkan import engine as eng
        # exe: which binary this is, so a Katip.app can tell its own engine from one another copy left running
        return {"engine": "katip-engine", "version": __version__, "pid": os.getpid(),
                "exe": os.path.realpath(sys.executable) if getattr(sys, "frozen", False) else None,
                "uptime_s": round(time.time() - self.started, 1), "served": self.served, "rss_peak_mb": rss_mb(),
                "model": self.ner.describe(), "profiles": sorted(eng.PROFILES),
                "vault": "encrypted on this device" if self.vault.persistent() else "memory only",
                "sources": {"mevzuat": {"on": True, "network": False},
                            "emsal": {"on": os.environ.get("KATIP_EMSAL_ONLINE", "0").lower() in ("1", "true", "yes", "on"),
                                      "network": True}}}


L_UNREADABLE = ("Katip öğrendiği listeleri okuyamıyor (Anahtar Zinciri izin vermedi). Maskeleme güvenlik için durdu: "
                "İnceleme ekranından listeleri yeniden başlatın. · Katip can't read its learned lists (the Keychain "
                "refused). Masking stopped to be safe: start the lists again on the Review screen.")


class Conflict(RuntimeError):
    """The request is fine but can't be done now; the message says why, in words the app can show."""


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port: int, token: str, idle_exit: float | None):
        self.token = token
        self.engine = Engine()
        self.idle_exit = idle_exit
        self.last = time.monotonic()
        super().__init__(("127.0.0.1", port), Handler)
        self.port = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        if idle_exit:
            threading.Thread(target=self._idle_watch, daemon=True).start()

    def _idle_watch(self):
        while True:
            time.sleep(min(5.0, self.idle_exit / 4))
            from . import features
            if features.busy():  # a setup download is running: not idle
                self.last = time.monotonic()
            elif time.monotonic() - self.last > self.idle_exit:
                threading.Thread(target=self.shutdown, daemon=True).start()
                return


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: Server

    def log_message(self, *a):  # request lines could carry file paths; keep the log free of them
        pass

    def _send(self, code: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _guard(self, need_token: bool = True) -> bool:
        """Local clients only: right Host (stops DNS rebinding), no browser Origin, the token."""
        if self.headers.get("Host", "") not in self.server.allowed_hosts:
            self._send(403, {"error": "wrong host"})
            return False
        if self.headers.get("Origin") or self.headers.get("Sec-Fetch-Site"):
            self._send(403, {"error": "web pages can't call the Katip engine"})
            return False
        if need_token and not secrets.compare_digest(self.headers.get("Authorization", ""), f"Bearer {self.server.token}"):
            self._send(401, {"error": "missing or wrong token (see ~/.katip/engine.json)"})
            return False
        self.server.last = time.monotonic()
        return True

    def do_GET(self):
        if self.path == "/healthz":
            if self._guard(need_token=False):
                self._send(200, {"ok": True})
            return
        if not self._guard():
            return
        e = self.server.engine
        gets = {"/v1/status": e.status, "/v1/settings": e.settings_get, "/v1/models": e.models_get,
                "/v1/matters": e.matters_get, "/v1/claude": e.claude_get, "/v1/features": e.features_get,
                "/v1/review": e.review_get,
                "/v1/paths": e.paths}
        if self.path in gets:
            try:
                return self._send(200, gets[self.path]())
            except Exception as x:  # noqa: BLE001
                return self._send(500, {"error": x.__class__.__name__})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._guard():
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            return self._send(413, {"error": "too large"})
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, {"error": "body must be JSON"})
        e = self.server.engine
        routes = {
            "/v1/mask": lambda: e.mask(str(body["text"]), body.get("profile"), body.get("matter") or "default"),
            "/v1/mask_file": lambda: e.mask_file(str(body["path"]), body.get("profile"), body.get("matter") or "default",
                                                 int(body.get("page") or 1)),
            "/v1/restore": lambda: e.restore(str(body["text"]), body.get("matter") or "default"),
            "/v1/forget": lambda: e.forget(str(body["matter"])),
            "/v1/sources/mevzuat": lambda: e.mevzuat(body.get("citation_text", ""), body.get("text", "")),
            "/v1/sources/emsal": lambda: e.emsal(body),
            "/v1/settings": lambda: e.settings_set(body),
            "/v1/models/download": lambda: e.models_download(body),
            "/v1/models/delete": lambda: e.models_delete(body),
            "/v1/models/custom": lambda: e.models_custom(body, True),
            "/v1/models/custom/remove": lambda: e.models_custom(body, False),
            "/v1/features": lambda: e.features_set(body),
            "/v1/features/action": lambda: e.features_act(body),
            "/v1/review/judge": lambda: e.review_post("judge", body),
            "/v1/review/undo": lambda: e.review_post("undo", body),
            "/v1/review/learned/remove": lambda: e.review_post("remove", body),
            "/v1/review/reset": lambda: e.review_post("reset", body),
            "/v1/claude/connect": lambda: e.claude_change(body, True),
            "/v1/claude/disconnect": lambda: e.claude_change(body, False),
        }
        if self.path == "/v1/shutdown":
            self._send(200, {"stopping": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if self.path not in routes:
            return self._send(404, {"error": "not found"})
        from .review import NotFound, Unreadable
        from .settings import Invalid
        try:
            self._send(202 if self.path == "/v1/models/download" else 200, routes[self.path]())
        except Invalid as x:  # our own messages about the request, never document text
            self._send(400, {"error": str(x)})
        except Unreadable as x:
            self._send(409, {"error": L_UNREADABLE})
        except NotFound:
            self._send(404, {"error": "no such candidate (already judged, or expired)"})
        except Conflict as x:
            self._send(409, {"error": str(x)})
        except KeyError as x:
            self._send(400, {"error": f"missing field {x}"})
        except PermissionError as x:  # a source that is switched off
            self._send(403, {"error": str(x)})
        except Exception as x:  # noqa: BLE001 - never put document text in an error
            self._send(500, {"error": x.__class__.__name__})


def serve(port: int = DEFAULT_PORT, idle_exit: float | None = 900, quiet: bool = False) -> None:
    token = secrets.token_urlsafe(32)
    srv = Server(port, token, idle_exit)
    sf = state_file()
    fd = os.open(sf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump({"port": srv.port, "token": token, "pid": os.getpid(), "version": __version__,
                   "started": time.time()}, fh)
    if not quiet:
        print(json.dumps({"ready": True, "port": srv.port, "pid": os.getpid()}), flush=True)
    try:
        srv.serve_forever()
    finally:
        srv.server_close()
        try:
            if json.loads(sf.read_text()).get("pid") == os.getpid():
                sf.unlink()
        except (OSError, ValueError):
            pass
