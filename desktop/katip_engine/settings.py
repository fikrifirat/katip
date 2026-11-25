"""The engine's settings, chosen in the Mac app: ~/.katip/engine-settings.json (readable only by this user).

They become the environment Kalkan reads (KATIP_MODEL, KATIP_PROFILE, KATIP_EMSAL_ONLINE, KATIP_TSG_SESSION_HOURS),
applied when the engine starts and whenever they change, so the next document already uses them. Which extra
features Claude may use is in "features" (see features.py); precedent search keeps its own switch, emsal_online.
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
    "features": {"mevzuat": True, "dd_masak": False, "dd_ilan": False, "dd_gazette": False},
    "tsg_session_hours": 8,     # keep the lawyer's Trade Registry Gazette login this long; 0 = log out every run
    "custom_models": [],        # model folders the lawyer added; "model" may be one of them
}
FEATURE_KEYS = tuple(DEFAULTS["features"])


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
    st = {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}
    st["features"] = {**DEFAULTS["features"], **{k: v for k, v in (st.get("features") or {}).items()
                                                 if k in FEATURE_KEYS and isinstance(v, bool)}}
    return st


def validate(changes: dict, current: dict | None = None) -> dict:
    for k, v in changes.items():
        if k not in DEFAULTS:
            raise Invalid(f"unknown setting {k!r}")
        if k == "model":
            customs = changes.get("custom_models", (current or load())["custom_models"])
            if v not in MODELS and v not in customs:
                raise Invalid(f"model must be one of {', '.join(MODELS)} or a model folder added in the app")
        if k == "features" and not (isinstance(v, dict) and all(f in FEATURE_KEYS and isinstance(b, bool)
                                                                for f, b in v.items())):
            raise Invalid(f"features must map {', '.join(FEATURE_KEYS)} to true or false")
        if k == "tsg_session_hours" and not (isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 24):
            raise Invalid("tsg_session_hours must be between 0 and 24")
        if k == "custom_models" and not (isinstance(v, list) and all(isinstance(p, str) and Path(p).is_absolute()
                                                                     for p in v)):
            raise Invalid("custom_models must be a list of full paths")
        if k == "default_profile" and v not in PROFILES:
            raise Invalid(f"profile must be one of {', '.join(PROFILES)}")
        if k in ("emsal_online", "include_downloads", "first_run_done") and not isinstance(v, bool):
            raise Invalid(f"{k} must be true or false")
        if k == "documents_folder" and not (isinstance(v, str) and Path(v).expanduser().is_absolute()):
            raise Invalid("documents_folder must be a full path")
    return changes


def save(changes: dict) -> dict:
    cur = load()
    validate(changes, cur)
    if "features" in changes:  # a partial map changes only the features it names
        changes = {**changes, "features": {**cur["features"], **changes["features"]}}
    st = {**cur, **changes}
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
    os.environ["KATIP_TSG_SESSION_HOURS"] = str(st["tsg_session_hours"])
    if os.environ.get("KATIP_HOME") and not os.environ.get("KATIP_DD_HOME"):  # keep DD data with the rest
        os.environ["KATIP_DD_HOME"] = str(Path(os.environ["KATIP_HOME"]) / "dd")
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
