"""katip-engine: run and control the Katip engine, Docker style.

    katip-engine serve [--port N] [--idle-exit S]   run in the foreground (what launchd runs)
    katip-engine install                            register the launchd agent for this user (macOS)
    katip-engine uninstall                          stop it and remove the agent
    katip-engine start | stop | restart
    katip-engine status                             running? port, version, memory, model
    katip-engine mask [--profile ai] [--matter M] < file.txt
    katip-engine restore [--matter M] < answer.txt
    katip-engine logs                               where the log is, and its last lines
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import DEFAULT_PORT, LABEL, __version__

LOG = Path.home() / "Library" / "Logs" / "Katip" / "engine.log"


def plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


# -- talking to a running engine ------------------------------------------------------------------------
def _state() -> dict | None:
    from .server import state_file
    try:
        return json.loads(state_file().read_text())
    except (OSError, ValueError):
        return None


def call(path: str, body: dict | None = None, timeout: float = 120) -> dict:
    st = _state()
    if not st:
        raise ConnectionError("the Katip engine is not running (katip-engine start)")
    req = urllib.request.Request(f"http://127.0.0.1:{st['port']}{path}",
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {st['token']}", "Content-Type": "application/json"},
                                 method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read() or b"{}").get("error", str(e)), "status": e.code}


def running() -> bool:
    try:
        return "engine" in call("/v1/status", timeout=3)
    except (ConnectionError, OSError):
        return False


def wait_ready(seconds: float = 20) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if running():
            return True
        time.sleep(0.2)
    return False


# -- launchd ----------------------------------------------------------------------------------------------
def agent_plist(python: str, idle_exit: int) -> dict:
    desktop = Path(__file__).resolve().parent.parent
    return {
        "Label": LABEL,
        "ProgramArguments": [python, "-m", "katip_engine", "serve", "--idle-exit", str(idle_exit), "--quiet"],
        "WorkingDirectory": str(desktop),
        "EnvironmentVariables": {"PYTHONPATH": str(desktop), "PYTHONUNBUFFERED": "1"},
        "RunAtLoad": False,   # started on demand (katip-engine start, or the menu bar app)
        "KeepAlive": False,   # an idle exit is meant to stay down: that's how memory is given back
        "ProcessType": "Interactive",
        "StandardOutPath": str(LOG),
        "StandardErrorPath": str(LOG),
    }


def install(idle_exit: int = 900) -> dict:
    if sys.platform != "darwin":
        raise SystemExit("install is for macOS; elsewhere run `katip-engine serve`")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    p = plist_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    _launchctl("bootout", f"{_domain()}/{LABEL}")
    with open(p, "wb") as fh:
        plistlib.dump(agent_plist(sys.executable, idle_exit), fh)
    r = _launchctl("bootstrap", _domain(), str(p))
    return {"installed": str(p), "ok": r.returncode == 0, **({"launchctl": r.stderr.strip()} if r.returncode else {})}


def uninstall() -> dict:
    _launchctl("bootout", f"{_domain()}/{LABEL}")
    p = plist_path()
    existed = p.exists()
    p.unlink(missing_ok=True)
    return {"removed": existed}


def start() -> dict:
    if running():
        return {"running": True, "already": True}
    if sys.platform == "darwin" and plist_path().exists():
        _launchctl("kickstart", f"{_domain()}/{LABEL}")
    else:  # no agent: run it detached from this terminal
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "ab") as log:
            subprocess.Popen([sys.executable, "-m", "katip_engine", "serve", "--quiet"], stdout=log, stderr=log,
                             cwd=Path(__file__).resolve().parent.parent, start_new_session=True,
                             env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent.parent)})
    t = time.monotonic()
    ok = wait_ready()
    return {"running": ok, "start_s": round(time.monotonic() - t, 2)}


def stop() -> dict:
    if not running():
        return {"running": False}
    call("/v1/shutdown", {})
    for _ in range(50):
        if not running():
            return {"running": False, "stopped": True}
        time.sleep(0.1)
    return {"running": running()}


# -- command line -----------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="katip-engine", description="Run and control the Katip engine.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=int(os.environ.get("KATIP_ENGINE_PORT", DEFAULT_PORT)))
    s.add_argument("--idle-exit", type=float, default=900, help="exit after this many idle seconds (0 = never)")
    s.add_argument("--quiet", action="store_true")
    i = sub.add_parser("install")
    i.add_argument("--idle-exit", type=int, default=900)
    for name in ("uninstall", "start", "stop", "restart", "status", "logs", "version"):
        sub.add_parser(name)
    m = sub.add_parser("mask")
    m.add_argument("--profile", default=None)
    m.add_argument("--matter", default="default")
    m.add_argument("--json", action="store_true")
    r = sub.add_parser("restore")
    r.add_argument("--matter", default="default")
    a = ap.parse_args(argv)

    if a.cmd == "serve":
        from .server import serve
        serve(a.port, a.idle_exit or None, a.quiet)
        return 0
    if a.cmd == "version":
        print(__version__)
        return 0
    if a.cmd == "logs":
        print(LOG)
        if LOG.exists():
            print("".join(LOG.read_text(errors="replace").splitlines(keepends=True)[-20:]), end="")
        return 0
    if a.cmd in ("mask", "restore"):
        if not running() and not start()["running"]:
            print("the Katip engine did not start; see katip-engine logs", file=sys.stderr)
            return 1
        text = sys.stdin.read()
        if a.cmd == "mask":
            res = call("/v1/mask", {"text": text, "profile": a.profile, "matter": a.matter})
            out = json.dumps(res, ensure_ascii=False, indent=1) if a.json or "error" in res else res["masked_text"]
        else:
            res = call("/v1/restore", {"text": text, "matter": a.matter})
            out = res.get("text", json.dumps(res))
        print(out, end="" if out.endswith("\n") else "\n")
        return 1 if "error" in res else 0
    res = {"install": lambda: install(a.idle_exit), "uninstall": uninstall, "start": start, "stop": stop,
           "restart": lambda: (stop(), start())[1],
           "status": lambda: call("/v1/status") if running() else {"running": False,
                                                                   "agent": plist_path().exists()}}[a.cmd]()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0
