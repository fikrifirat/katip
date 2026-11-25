"""Katip's extra features, for the Mac app's Features panel and for what Claude may see.

Each feature has a switch (in the settings) and something it needs before it works: consent to go online, the
MASAK lists, a browser, the lawyer's own login. A feature's tools reach Claude only while it is on and ready
(see mcp.py). Everything here is cheap to ask: file checks and one SQLite count, so the MCP process can ask
every few seconds.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from . import settings

CATALOG = [
    {"id": "mevzuat", "online": False, "sends_to": None, "needs": None, "tools": ["mevzuat_bak"]},
    {"id": "emsal", "online": True, "sends_to": "bedesten.adalet.gov.tr", "needs": None,
     "tools": ["emsal_ara", "geri_bildirim"]},
    {"id": "dd_masak", "online": True, "sends_to": "masak.hmb.gov.tr", "needs": "data", "tools": ["dd_update"]},
    {"id": "dd_ilan", "online": True, "sends_to": "www.ilan.gov.tr", "needs": "browser", "tools": ["dd_ilan_lookup"]},
    {"id": "dd_gazette", "online": True, "sends_to": "www.ticaretsicil.gov.tr", "needs": "browser",
     "tools": ["dd_gazette_lookup", "dd_gazette_logout"]},
]
IDS = tuple(f["id"] for f in CATALOG)
DD = ("dd_masak", "dd_ilan", "dd_gazette")
DD_SHARED = ("dd_screen", "dd_record", "dd_sources")  # reading the local DD index: with any DD feature
ACTIONS = {"dd_masak": ("refresh",), "dd_ilan": ("install_browser", "test_browser"),
           "dd_gazette": ("install_browser", "test_browser", "logout")}
GATED = {t for f in CATALOG for t in f["tools"]} | set(DD_SHARED)

_lock = threading.Lock()
_jobs: dict[str, dict] = {}


# -- browser --------------------------------------------------------------------------------------------
def _chrome_app() -> Path:
    return Path(os.environ.get("KATIP_CHROME_APP", "/Applications/Google Chrome.app"))


def _browsers_dir() -> Path:
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    return Path(env) if env and env != "0" else Path.home() / "Library" / "Caches" / "ms-playwright"


def chromium_revision() -> str | None:
    """The Chromium build the bundled Playwright drives (another build would not start)."""
    try:
        import playwright
        f = Path(playwright.__file__).parent / "driver" / "package" / "browsers.json"
        return next(b["revision"] for b in json.loads(f.read_text())["browsers"] if b["name"] == "chromium")
    except Exception:  # noqa: BLE001 - Playwright missing or a layout we don't know
        return None


def browser() -> dict:
    """Google Chrome if the Mac has it (Katip prefers the lawyer's own browser), else the Chromium Playwright
    downloaded, else nothing."""
    chrome = _chrome_app() / "Contents" / "MacOS" / "Google Chrome"
    if chrome.is_file():
        return {"kind": "chrome", "path": str(chrome)}
    rev = chromium_revision()
    for d in sorted(_browsers_dir().glob(f"chromium-{rev}" if rev else "chromium-*")):
        for exe in d.glob("*/*.app/Contents/MacOS/*"):
            if exe.is_file() and os.access(exe, os.X_OK):
                return {"kind": "chromium", "path": str(exe)}
    return {"kind": None, "path": None}


def _install_chromium() -> None:
    """Playwright's own installer (the bundled Node driver), about 150 MB from Playwright's CDN."""
    from playwright._impl._driver import compute_driver_executable, get_driver_env
    exe = compute_driver_executable()
    cmd = [*exe] if isinstance(exe, (tuple, list)) else [str(exe)]
    subprocess.run([*map(str, cmd), "install", "chromium"], env=get_driver_env(), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=1800)


def _test_browser() -> None:
    """Start the browser the DD lookups will use, headless, on a page of our own (nothing goes online)."""
    from playwright.sync_api import sync_playwright
    kind = browser()["kind"]
    if kind is None:
        raise FileNotFoundError("no browser")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True) if kind == "chrome" else p.chromium.launch(headless=True)
        try:
            pg = b.new_page()
            pg.set_content("<p id=k>katip</p>")
            if pg.inner_text("#k") != "katip":
                raise RuntimeError("browser did not render")
        finally:
            b.close()


# -- MASAK data -----------------------------------------------------------------------------------------
def _masak() -> dict:
    """How many MASAK records are here. A locked or damaged store counts as none (never an error: Claude's tool
    list is built from this)."""
    import sqlite3
    try:
        from katip_kalkan.dd.store import home
        f = home() / "dd.sqlite"
        if not f.exists():
            return {"records": 0, "data_as_of": None}
        db = sqlite3.connect(f"file:{f}?mode=ro", uri=True, timeout=2)
        try:
            (n,) = db.execute("select count(*) from records where source='masak'").fetchone()
            row = db.execute("select finished from runs where source='masak' and status='ok' order by id desc limit 1").fetchone()
        finally:
            db.close()
        return {"records": n, "data_as_of": row[0] if row and n else None}
    except Exception:  # noqa: BLE001
        return {"records": 0, "data_as_of": None}


def _gazette() -> dict:
    hours = settings.load()["tsg_session_hours"]
    until = None
    try:
        from katip_kalkan.dd.sources import gazette_browser
        s = gazette_browser.session_read()
        if s and s.get("expires", 0) > time.time():
            until = s["expires"]
        elif s:  # the kept login ran out: log out on the site now, not "on the next run" that may never come
            _logout_soon()
    except Exception:  # noqa: BLE001 - no key yet, damaged file: not logged in
        pass
    return {"session_hours": hours, "session_until": until}


# -- state ----------------------------------------------------------------------------------------------
def enabled(st: dict, fid: str) -> bool:
    return bool(st["emsal_online"]) if fid == "emsal" else bool(st["features"].get(fid))


def _ready(fid: str, br: dict, masak: dict | None) -> bool:
    need = next(f["needs"] for f in CATALOG if f["id"] == fid)
    if need == "browser":
        return br["kind"] is not None
    if need == "data":
        return bool(masak and masak["records"])
    return True


def visible_tools(all_tools: set[str]) -> set[str]:
    """The tools Claude may see now: every core tool, plus those of features that are on and ready."""
    st = settings.load()
    br = browser() if any(enabled(st, f) for f in ("dd_ilan", "dd_gazette")) else {"kind": None}
    masak = _masak() if enabled(st, "dd_masak") else None
    show = all_tools - GATED
    for f in CATALOG:
        if enabled(st, f["id"]) and _ready(f["id"], br, masak):
            show |= set(f["tools"])
            if f["id"] in DD:
                show |= set(DD_SHARED)
    return show & all_tools


def listing() -> dict:
    st, br, masak = settings.load(), browser(), _masak()
    out = []
    with _lock:
        jobs = {k: dict(v) for k, v in _jobs.items()}
    for f in CATALOG:
        fid, on, job = f["id"], enabled(st, f["id"]), jobs.get(f["id"])
        if not on:
            state = "off"
        elif job and job["state"] == "running":
            state = "working"
        elif _ready(fid, br, masak):
            state = "ready"
        elif job and job["state"] == "failed":
            state = "problem"
        else:
            state = "needs_setup"
        detail = masak if fid == "dd_masak" else _gazette() if fid == "dd_gazette" else {}
        out.append({"id": fid, "enabled": on, "state": state, "online": f["online"], "sends_to": f["sends_to"],
                    "needs": f["needs"], "actions": list(ACTIONS.get(fid, ())), "detail": detail, "job": job})
    return {"features": out, "browser": br}


def _logout_soon() -> None:
    def run():
        try:
            from katip_kalkan.dd import service
            service.gazette_logout()
        except Exception:  # noqa: BLE001 - offline: the kept cookies are deleted anyway
            try:
                from katip_kalkan.dd.sources import gazette_browser
                gazette_browser.session_delete()
            except Exception:  # noqa: BLE001
                pass
    with _lock:
        if _jobs.get("dd_gazette", {}).get("state") == "running":
            return
    threading.Thread(target=run, daemon=True, name="katip-tsg-logout").start()


def set_enabled(fid: str, on: bool) -> dict:
    if fid not in IDS:
        raise settings.Invalid(f"feature must be one of {', '.join(IDS)}")
    if not isinstance(on, bool):
        raise settings.Invalid("enabled must be true or false")
    settings.save({"emsal_online": on} if fid == "emsal" else {"features": {fid: on}})
    if on and fid == "dd_masak" and not _masak()["records"]:
        _start(fid, "refresh")  # switching MASAK on is its setup: fetch the lists
    if not on and fid == "dd_gazette":
        _logout_soon()  # switching the Gazette off ends the lawyer's session on the site and deletes the cookies
    return listing()


def busy() -> bool:
    with _lock:
        return any(j["state"] == "running" for j in _jobs.values())


def _start(fid: str, action: str) -> None:
    with _lock:
        if fid in _jobs and _jobs[fid]["state"] == "running":
            return
        _jobs[fid] = {"action": action, "state": "running", "error": None, "started": time.time()}

    def run():
        err = None
        try:
            if action == "refresh":
                from katip_kalkan.dd import service
                r = service.update("masak")
                if r.get("status") != "ok":
                    err = r.get("status") or "error"
            elif action == "install_browser":
                _install_chromium()
                if browser()["kind"] is None:
                    err = "not_found"
                else:
                    _test_browser()
            elif action == "test_browser":
                _test_browser()
        except Exception as e:  # noqa: BLE001 - offline, blocked, disk full
            err = e.__class__.__name__
        with _lock:
            _jobs[fid].update(state="failed" if err else "done", error=err, finished=time.time())

    threading.Thread(target=run, daemon=True, name=f"katip-{fid}").start()


def act(fid: str, action: str) -> dict:
    if action not in ACTIONS.get(fid, ()):
        raise settings.Invalid(f"{fid} has no action {action!r}")
    if action != "logout" and not enabled(settings.load(), fid):
        raise settings.Invalid("switch the feature on first (that is the lawyer's consent to go online)")
    if action == "logout":
        from katip_kalkan.dd import service
        result = service.gazette_logout()
        return {**listing(), "result": result}
    _start(fid, action)
    return listing()
