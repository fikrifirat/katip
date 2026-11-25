"""Setup routes the Mac app's first run uses: settings, models, case list, Claude connection.

Synthetic data only; Claude's settings file and CLI are fakes in tmp_path, so nothing on this computer changes.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import threading
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from test_engine import TEXT, req  # noqa: E402


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    monkeypatch.setenv("KATIP_CLAUDE_DESKTOP_CONFIG", str(tmp_path / "claude" / "claude_desktop_config.json"))
    monkeypatch.setenv("KATIP_CLAUDE_BIN", str(tmp_path / "no-claude"))
    monkeypatch.setenv("KATIP_CLAUDE_CODE_CONFIG", str(tmp_path / "claude.json"))
    for k in ("KATIP_EMSAL_ONLINE", "KATIP_MODEL", "KATIP_PROFILE"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def srv():
    from katip_engine.server import Server
    s = Server(0, "t0k3n", idle_exit=None)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s
    s.shutdown()
    s.server_close()


# -- settings ---------------------------------------------------------------------------------------------
def test_settings_defaults_and_change(srv):
    code, st = req(srv, "GET", "/v1/settings")
    assert code == 200
    assert st["model"] == "nano" and st["emsal_online"] is False and st["default_profile"] == "ai"
    assert st["first_run_done"] is False
    code, st = req(srv, "POST", "/v1/settings", {"default_profile": "court", "emsal_online": True,
                                                  "first_run_done": True})
    assert code == 200 and st["default_profile"] == "court" and st["first_run_done"] is True
    assert os.environ["KATIP_EMSAL_ONLINE"] == "1" and os.environ["KATIP_PROFILE"] == "court"
    assert req(srv, "GET", "/v1/status")[1]["sources"]["emsal"]["on"] is True
    from katip_engine import settings
    assert oct(settings.path().stat().st_mode & 0o777) == "0o600" or sys.platform == "win32"


def test_settings_refuse_unknown_values(srv):
    assert req(srv, "POST", "/v1/settings", {"default_profile": "everything"})[0] == 400
    assert req(srv, "POST", "/v1/settings", {"model": "huge"})[0] == 400
    assert req(srv, "POST", "/v1/settings", {"nonsense": 1})[0] == 400


# -- models -----------------------------------------------------------------------------------------------
def test_models_list(srv):
    code, m = req(srv, "GET", "/v1/models")
    assert code == 200
    names = [x["name"] for x in m["models"]]
    assert names == ["nano", "mini", "base"]
    nano = m["models"][0]
    assert nano["downloaded"] is True and nano["included"] is True
    assert [x for x in m["models"] if x["recommended"]][0]["name"] == "base"
    assert all(x["size_mb"] > 0 for x in m["models"])
    assert m["current"] == "nano"


def test_choosing_a_model_not_downloaded_is_refused(srv, tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_MASK_CACHE", str(tmp_path / "empty-cache"))
    code, body = req(srv, "POST", "/v1/settings", {"model": "base"})
    assert code == 409 and "download" in body["error"]


def test_model_download_reports_progress_and_switches(srv, tmp_path, monkeypatch):
    """A fake download (no network): the route runs it in the background and reports bytes, then switches."""
    from katip_engine import models
    monkeypatch.setenv("KATIP_MASK_CACHE", str(tmp_path / "cache"))

    def fake(name, progress):
        for i in range(3):
            progress(i + 1, 3)
            time.sleep(0.05)
        return tmp_path / "cache" / name

    monkeypatch.setattr(models, "_fetch", fake)
    monkeypatch.setattr(models, "downloaded", lambda name, verify=False: name == "nano" or (tmp_path / "cache" / name).exists())
    code, body = req(srv, "POST", "/v1/models/download", {"name": "mini", "use": True})
    assert code == 202 and body["download"]["name"] == "mini"
    (tmp_path / "cache" / "mini").mkdir(parents=True)
    for _ in range(100):
        d = req(srv, "GET", "/v1/models")[1]
        if d["download"] and d["download"]["state"] == "done":
            break
        time.sleep(0.05)
    assert d["download"]["state"] == "done" and d["download"]["done"] == d["download"]["total"]
    assert req(srv, "GET", "/v1/settings")[1]["model"] == "mini"
    assert os.environ["KATIP_MODEL"] == "mini"


def test_model_download_failure_is_reported_plainly(srv, monkeypatch):
    from katip_engine import models

    def boom(name, progress):
        raise OSError("offline")

    monkeypatch.setattr(models, "_fetch", boom)
    req(srv, "POST", "/v1/models/download", {"name": "base"})
    for _ in range(100):
        d = req(srv, "GET", "/v1/models")[1]["download"]
        if d and d["state"] != "running":
            break
        time.sleep(0.05)
    assert d["state"] == "failed" and d["error"] == "OSError"
    assert req(srv, "GET", "/v1/settings")[1]["model"] == "nano"


# -- case list --------------------------------------------------------------------------------------------
def test_matters_are_listed_encrypted_and_forgotten(srv):
    req(srv, "POST", "/v1/mask", {"text": TEXT, "matter": "2026/123"})
    req(srv, "POST", "/v1/mask", {"text": TEXT, "matter": "2026/456"})
    code, m = req(srv, "GET", "/v1/matters")
    assert code == 200
    labels = [x["matter"] for x in m["matters"]]
    assert set(labels) == {"2026/123", "2026/456"} and all(x["last_used"] for x in m["matters"])
    from katip_engine import matters
    assert b"2026/123" not in matters.path().read_bytes()  # labels can be names: kept encrypted
    req(srv, "POST", "/v1/forget", {"matter": "2026/123"})
    assert [x["matter"] for x in req(srv, "GET", "/v1/matters")[1]["matters"]] == ["2026/456"]


# -- Claude connection ------------------------------------------------------------------------------------
def test_claude_status_when_nothing_is_installed(srv):
    code, c = req(srv, "GET", "/v1/claude")
    assert code == 200
    assert c["desktop"]["connected"] is False and c["code"]["installed"] is False


def test_connect_claude_desktop_merges_and_backs_up(srv, tmp_path):
    cfg = tmp_path / "claude" / "claude_desktop_config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x", "env": {"TOKEN": "s3cret"}}}, "theme": "dark"}))
    cfg.chmod(0o600)
    code, r = req(srv, "POST", "/v1/claude/connect", {"app": "desktop"})
    assert code == 200 and r["connected"] is True and r["restart_needed"] is True
    new = json.loads(cfg.read_text())
    assert new["theme"] == "dark" and "other" in new["mcpServers"]
    k = new["mcpServers"]["katip"]
    assert k["args"][-1] == "mcp" and k["env"]["KATIP_AUTO_DEPS"] == "0"
    assert "KATIP_EMSAL_ONLINE" not in k["env"]  # settings are read live, never frozen into Claude's config
    assert (cfg.parent / "claude_desktop_config.json.katip-backup").exists()
    assert oct(cfg.stat().st_mode & 0o777) == "0o600"  # other servers' tokens stay private
    assert req(srv, "GET", "/v1/claude")[1]["desktop"]["connected"] is True
    code, r = req(srv, "POST", "/v1/claude/disconnect", {"app": "desktop"})
    assert "katip" not in json.loads(cfg.read_text())["mcpServers"] and "other" in json.loads(cfg.read_text())["mcpServers"]


def test_connect_claude_desktop_refuses_a_broken_settings_file(srv, tmp_path):
    cfg = tmp_path / "claude" / "claude_desktop_config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("{not json")
    code, r = req(srv, "POST", "/v1/claude/connect", {"app": "desktop"})
    assert code == 409 and cfg.read_text() == "{not json"


@pytest.mark.skipif(sys.platform == "win32", reason="the fake Claude CLI is a shell script")
def test_connect_claude_code_runs_its_cli(srv, tmp_path, monkeypatch):
    log = tmp_path / "calls.txt"
    fake = tmp_path / "claude-bin"
    cc = tmp_path / "claude.json"
    fake.write_text(f"#!/bin/sh\necho \"$@\" >> {log}\n"
                    "case \"$*\" in *'mcp add'*) printf '{\"mcpServers\": {\"katip\": {\"command\": \"/bin/sh\"}}}' > " + str(cc) + ";; esac\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("KATIP_CLAUDE_BIN", str(fake))
    assert req(srv, "GET", "/v1/claude")[1]["code"] == {"installed": True, "connected": False, "stale": False}
    code, r = req(srv, "POST", "/v1/claude/connect", {"app": "code"})
    assert code == 200 and r["connected"] is True
    calls = log.read_text()
    assert "mcp add --scope user katip" in calls and " mcp" in calls


def test_mcp_command_points_at_this_engine():
    from katip_engine import claude
    cmd = claude.mcp_command()
    assert cmd["args"][-1] == "mcp" and Path(cmd["command"]).exists()


def test_a_moved_app_shows_as_stale(srv, tmp_path):
    cfg = tmp_path / "claude" / "claude_desktop_config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"mcpServers": {"katip": {"command": "/Applications/Gone.app/engine", "args": ["mcp"]}}}))
    d = req(srv, "GET", "/v1/claude")[1]["desktop"]
    assert d["connected"] is False and d["stale"] is True


def test_mcp_mode_follows_the_settings_live(tmp_path):
    from katip_engine import settings
    settings.save({"emsal_online": False, "include_downloads": False})
    settings.apply(folders=True)
    assert os.environ["KATIP_EMSAL_ONLINE"] == "0"
    assert str(Path.home() / "Downloads") not in os.environ["KATIP_ALLOWED_DIRS"]
    settings.follow(interval=0.05)
    settings.save({"emsal_online": True})
    for _ in range(100):
        if os.environ["KATIP_EMSAL_ONLINE"] == "1":
            break
        time.sleep(0.05)
    assert os.environ["KATIP_EMSAL_ONLINE"] == "1"
    os.environ.pop("KATIP_ALLOWED_DIRS", None)
