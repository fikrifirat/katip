"""Connect Claude Desktop and Claude Code to Katip, on the lawyer's button press only.

Both get Katip's MCP tools through this same engine binary (`katip-engine mcp`), so nothing else is installed.
Claude Desktop: Katip is merged into claude_desktop_config.json (other servers and settings untouched) and the
previous file is kept as claude_desktop_config.json.katip-backup. Claude Code: its own `claude mcp add` is used.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

NAME = "katip"


def desktop_config() -> Path:
    env = os.environ.get("KATIP_CLAUDE_DESKTOP_CONFIG")
    if env:
        return Path(env)
    return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"


def desktop_installed() -> bool:
    if os.environ.get("KATIP_CLAUDE_DESKTOP_CONFIG"):
        return True
    return Path("/Applications/Claude.app").exists() or (Path.home() / "Applications" / "Claude.app").exists()


def claude_bin() -> str | None:
    env = os.environ.get("KATIP_CLAUDE_BIN")
    if env:
        return env if os.access(env, os.X_OK) else None
    # the app starts with a short PATH, so look where the installers put it
    for c in (shutil.which("claude"), Path.home() / ".local/bin/claude", Path.home() / ".claude/local/claude",
              Path("/opt/homebrew/bin/claude"), Path("/usr/local/bin/claude")):
        if c and os.access(str(c), os.X_OK):
            return str(c)
    return None


def code_config() -> Path:
    """Claude Code keeps user-scope MCP servers in ~/.claude.json."""
    env = os.environ.get("KATIP_CLAUDE_CODE_CONFIG")
    return Path(env) if env else Path.home() / ".claude.json"


def mcp_command() -> dict:
    """How Claude starts Katip: this engine in MCP mode. The lawyer's settings (model, profile, precedent search,
    folders) are read from engine-settings.json by that process and followed live, so they are never stale here."""
    from .cli import DESKTOP, FROZEN
    env = {"KATIP_AUTO_DEPS": "0"}
    for k in ("KATIP_HOME", "KATIP_NO_KEYCHAIN"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    if FROZEN:
        return {"command": sys.executable, "args": ["mcp"], "env": env}
    env["PYTHONPATH"] = str(DESKTOP)
    return {"command": sys.executable, "args": ["-m", "katip_engine", "mcp"], "env": env}


class Refused(RuntimeError):
    """The change would damage something of the lawyer's, or can't work, so nothing was changed."""


def _check_location() -> None:
    if "/AppTranslocation/" in sys.executable:
        raise Refused("Move Katip to the Applications folder first, then connect Claude "
                      "(macOS runs apps from Downloads in a temporary place that disappears)")


def _read_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text() or "{}")
    except ValueError:
        raise Refused("Claude's settings file is not valid JSON; fix it in Claude first, Katip left it as it is")
    if not isinstance(data, dict):
        raise Refused("Claude's settings file has an unexpected shape; Katip left it as it is")
    return data


def _read_desktop() -> dict:
    return _read_json(desktop_config())


def _write_desktop(data: dict) -> None:
    p = desktop_config()
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = 0o600
    if p.exists():
        mode = p.stat().st_mode & 0o777
        backup = p.with_name(p.name + ".katip-backup")
        if not backup.exists():  # keep the file as it was before Katip ever touched it
            shutil.copy2(p, backup)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".katip-")
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps(data, indent=2, ensure_ascii=False))
    os.chmod(tmp, mode)  # other servers' tokens can live in this file: never widen who can read it
    os.replace(tmp, p)


def _extension_installed() -> bool:
    ext = desktop_config().parent / "Claude Extensions"
    return ext.is_dir() and any("katip" in d.name.lower() for d in ext.iterdir())


def _entry_ok(entry: dict | None) -> bool | None:
    """None: no entry. False: points at a Katip that is gone (app moved or deleted). True: usable."""
    if not isinstance(entry, dict):
        return None
    return Path(str(entry.get("command", ""))).exists()


def _code_entry() -> dict | None:
    try:
        return (_read_json(code_config()).get("mcpServers") or {}).get(NAME)
    except Refused:
        return None


def status() -> dict:
    try:
        ok = _entry_ok((_read_desktop().get("mcpServers") or {}).get(NAME))
        desktop = {"installed": desktop_installed(), "connected": ok is True, "stale": ok is False,
                   "broken_config": False}
    except Refused:
        desktop = {"installed": desktop_installed(), "connected": False, "stale": False, "broken_config": True}
    desktop["extension"] = _extension_installed()
    ok = _entry_ok(_code_entry())
    code = {"installed": bool(claude_bin()), "connected": ok is True, "stale": ok is False}
    return {"desktop": desktop, "code": code}


def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, OSError) as e:
        raise Refused(f"Claude Code did not answer ({e.__class__.__name__}); try again")


def connect(app: str) -> dict:
    _check_location()
    if app == "desktop":
        data = _read_desktop()
        servers = data.get("mcpServers")
        if servers is not None and not isinstance(servers, dict):
            raise Refused("Claude's settings file has an unexpected shape; Katip left it as it is")
        data["mcpServers"] = {**(servers or {}), NAME: mcp_command()}
        _write_desktop(data)
        return {"app": "desktop", "connected": True, "restart_needed": True}
    if app == "code":
        b = claude_bin()
        if not b:
            raise Refused("Claude Code is not installed on this Mac")
        old = _code_entry()
        c = mcp_command()
        if old is not None:
            _run([b, "mcp", "remove", "--scope", "user", NAME])
        envs = [x for k, v in c["env"].items() for x in ("-e", f"{k}={v}")]
        r = _run([b, "mcp", "add", "--scope", "user", NAME, *envs, "--", c["command"], *c["args"]])
        if r.returncode:
            if old is not None:  # put the previous entry back rather than leave Claude Code without Katip
                _run([b, "mcp", "add-json", "--scope", "user", NAME, json.dumps(old)])
            raise Refused("Claude Code did not accept the connection: " + (r.stderr.strip()[:200] or "unknown error"))
        return {"app": "code", "connected": True, "restart_needed": False}
    raise ValueError("app must be desktop or code")


def disconnect(app: str) -> dict:
    if app == "desktop":
        data = _read_desktop()
        if NAME in (data.get("mcpServers") or {}):
            data["mcpServers"].pop(NAME)
            _write_desktop(data)
        return {"app": "desktop", "connected": False, "restart_needed": True}
    if app == "code":
        b = claude_bin()
        if b and _code_entry() is not None:
            _run([b, "mcp", "remove", "--scope", "user", NAME])
        return {"app": "code", "connected": False, "restart_needed": False}
    raise ValueError("app must be desktop or code")
