"""The engine's settings, chosen in the Mac app: ~/.katip/engine-settings.json (readable only by this user).

They become the environment Kalkan reads (KATIP_MODEL, KATIP_PROFILE, KATIP_EMSAL_ONLINE), applied when the
engine starts and whenever they change, so the next document already uses them.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PROFILES = ("ai", "court", "anon", "eu")
MODELS = ("nano", "mini", "base")
DEFAULTS = {
    "model": "nano",            # included in the app; Mini and Base are downloaded on request
    "default_profile": "ai",
    "emsal_online": False,      # precedent search sends keywords (never document text) to bedesten.adalet.gov.tr
    "documents_folder": str(Path.home() / "Documents" / "katip-documents"),
    "include_downloads": True,  # UYAP downloads and e-mail attachments land there
    "first_run_done": False,
}


class Invalid(ValueError):
    """A setting the app may not set, or a value it may not take."""


def path() -> Path:
    from katip_kalkan.vault import katip_home
    return katip_home() / "engine-settings.json"


def load() -> dict:
    try:
        saved = json.loads(path().read_text())
    except (OSError, ValueError):
        saved = {}
    return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}


def validate(changes: dict) -> dict:
    for k, v in changes.items():
        if k not in DEFAULTS:
            raise Invalid(f"unknown setting {k!r}")
        if k == "model" and v not in MODELS:
            raise Invalid(f"model must be one of {', '.join(MODELS)}")
        if k == "default_profile" and v not in PROFILES:
            raise Invalid(f"profile must be one of {', '.join(PROFILES)}")
        if k in ("emsal_online", "include_downloads", "first_run_done") and not isinstance(v, bool):
            raise Invalid(f"{k} must be true or false")
        if k == "documents_folder" and not (isinstance(v, str) and Path(v).expanduser().is_absolute()):
            raise Invalid("documents_folder must be a full path")
    return changes


def save(changes: dict) -> dict:
    st = {**load(), **validate(changes)}
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(st, fh, indent=1)
    os.replace(tmp, p)
    apply(st)
    return st


def allowed_dirs(st: dict | None = None) -> list[str]:
    st = st or load()
    return [st["documents_folder"]] + ([str(Path.home() / "Downloads")] if st["include_downloads"] else [])


def apply(st: dict | None = None, folders: bool = False) -> dict:
    """Put the settings into the environment Kalkan reads. folders=True also limits which folders Katip may
    open to the chosen ones (the MCP server Claude runs; the engine itself opens what the lawyer picks)."""
    st = st or load()
    os.environ["KATIP_MODEL"] = st["model"]
    os.environ["KATIP_PROFILE"] = st["default_profile"]
    os.environ["KATIP_EMSAL_ONLINE"] = "1" if st["emsal_online"] else "0"
    if folders:
        os.environ["KATIP_ALLOWED_DIRS"] = os.pathsep.join(allowed_dirs(st))
    return st


def follow(interval: float = 2.0) -> None:
    """Re-apply the settings whenever the file changes, so a switch flipped in the app (precedent search off,
    Downloads off) reaches a Claude session that is already running, within seconds."""
    import threading

    def loop():
        last = None
        while True:
            try:
                m = path().stat().st_mtime
            except OSError:
                m = None
            if m != last:
                last = m
                apply(folders=True)
            threading.Event().wait(interval)

    threading.Thread(target=loop, daemon=True, name="katip-settings").start()
