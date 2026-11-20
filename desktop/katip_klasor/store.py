"""Where the app keeps its own state, under ~/.katip/klasor (or $KATIP_HOME/klasor).

* jobs: one encrypted file per case (same key and AES-GCM as Kalkan's vault). A job holds the document text
  and the flagged spots, which contain real values, so it is never written in clear.
* audit: one JSON-lines file per case. It holds counts, types, hashes and safe names, never a real value
  or an original file name, so it can be exported as it is.
* settings: plain JSON (folder, model, language, profile per case, thresholds).
"""
from __future__ import annotations

import csv
import getpass
import io
import json
import os
import secrets
import threading
import time
from pathlib import Path

from katip_kalkan import vault

from . import __version__

_lock = threading.RLock()
_memory: dict[str, dict] = {}


def home() -> Path:
    d = vault.katip_home() / "klasor"
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    return d


def _case_file(kind: str, case: str, ext: str) -> Path:
    d = home() / kind
    d.mkdir(exist_ok=True, mode=0o700)
    return d / f"{vault._file_id('klasor:' + case)}{ext}"


# ---------------------------------------------------------------- settings
DEFAULTS = {
    "folder": None,          # None = ~/Documents/Katip
    "model": "base",         # base | mini | nano | none
    "lang": "tr",
    "auto_release": False,   # release files with nothing flagged without a review
    "default_profile": "ai",
    "profiles": {},          # case -> court | ai | anon
    "terms": {},             # case -> {"mask": [...], "keep": [...]}
    "low": 0.30,             # candidates scored from here up to the mask threshold are "maybe missed"
    "unsure": 0.70,          # masked spans scored under this are "unsure"
}


def load_settings() -> dict:
    p = home() / "settings.json"
    s = dict(DEFAULTS)
    if p.exists():
        try:
            s.update(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return s


def save_settings(s: dict) -> None:
    with _lock:
        p = home() / "settings.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, p)


def folder(s: dict | None = None) -> Path:
    s = s or load_settings()
    f = os.environ.get("KATIP_KLASOR_DIR") or s.get("folder")
    return Path(f).expanduser() if f else Path.home() / "Documents" / "Katip"


# ---------------------------------------------------------------- jobs (encrypted)
def load_jobs(case: str) -> dict:
    with _lock:
        if not vault.persistent():
            return json.loads(json.dumps(_memory.get(case, {})))
        p = _case_file("jobs", case, ".bin")
        if not p.exists():
            return {}
        raw = p.read_bytes()
        data = vault.AESGCM(vault._key()).decrypt(raw[3:15], raw[15:], ("klasor:" + case).encode())
        return json.loads(data)


def save_jobs(case: str, jobs: dict) -> None:
    with _lock:
        if not vault.persistent():
            _memory[case] = json.loads(json.dumps(jobs))
            return
        p = _case_file("jobs", case, ".bin")
        nonce = secrets.token_bytes(12)
        blob = vault.AESGCM(vault._key()).encrypt(nonce, json.dumps(jobs, ensure_ascii=False).encode(),
                                                  ("klasor:" + case).encode())
        tmp = p.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(b"KJ1" + nonce + blob)
        os.replace(tmp, p)


def forget_case(case: str) -> None:
    with _lock:
        _memory.pop(case, None)
        p = _case_file("jobs", case, ".bin")
        if p.exists():
            p.unlink()


# ---------------------------------------------------------------- audit (no personal data)
AUDIT_FIELDS = ["at", "event", "case_id", "file", "sha256", "kind", "profile", "counts", "detail", "user", "version"]


def audit(event: str, case: str, **kw) -> dict:
    row = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event,
           "case_id": vault._file_id("klasor:" + case)[:10], "user": _user(), "version": __version__, **kw}
    with _lock:
        p = _case_file("audit", case, ".jsonl")
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        os.chmod(p, 0o600)
    return row


def audit_rows(case: str) -> list[dict]:
    p = _case_file("audit", case, ".jsonl")
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def audit_csv(case: str) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=AUDIT_FIELDS, extrasaction="ignore")
    w.writeheader()
    for r in audit_rows(case):
        r = dict(r)
        if isinstance(r.get("counts"), dict):
            r["counts"] = "; ".join(f"{k}={v}" for k, v in sorted(r["counts"].items()))
        w.writerow(r)
    return buf.getvalue()


def _user() -> str:
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001 - no user name is not worth failing over
        return "?"
