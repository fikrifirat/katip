"""Features panel and Models panel: what each feature needs, what Claude may see, and model management.

Synthetic data only. The DD store, browser folders and Claude files are all in tmp_path; nothing goes online
(MASAK fetches and the browser download are replaced by fakes).
"""
from __future__ import annotations

import io
import json
import sys
import threading
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from test_engine import req  # noqa: E402


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path / "dd"))
    monkeypatch.setenv("KATIP_CHROME_APP", str(tmp_path / "no-chrome"))      # no Google Chrome on this "Mac"
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "browsers"))  # and no Chromium yet
    monkeypatch.setenv("KATIP_CLAUDE_DESKTOP_CONFIG", str(tmp_path / "claude" / "claude_desktop_config.json"))
    monkeypatch.setenv("KATIP_CLAUDE_BIN", str(tmp_path / "no-claude"))
    monkeypatch.setenv("KATIP_CLAUDE_CODE_CONFIG", str(tmp_path / "claude.json"))
    for k in ("KATIP_EMSAL_ONLINE", "KATIP_MODEL", "KATIP_PROFILE", "KATIP_TSG_SESSION_HOURS"):
        monkeypatch.delenv(k, raising=False)
    from katip_engine import features
    features._jobs.clear()


@pytest.fixture
def srv():
    from katip_engine.server import Server
    s = Server(0, "t0k3n", idle_exit=None)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s
    s.shutdown()
    s.server_close()


def by_id(listing: dict) -> dict:
    return {f["id"]: f for f in listing["features"]}


def fake_chromium(tmp_path: Path) -> None:
    from katip_engine import features
    rev = features.chromium_revision() or "9999"
    exe = tmp_path / "browsers" / f"chromium-{rev}" / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)


def wait_job(srv, fid: str) -> dict:
    for _ in range(100):
        f = by_id(req(srv, "GET", "/v1/features")[1])[fid]
        if not f["job"] or f["job"]["state"] != "running":
            return f
        time.sleep(0.05)
    raise AssertionError("job never finished")


# -- the catalogue --------------------------------------------------------------------------------------
def test_defaults_statutes_on_everything_online_off(srv):
    code, out = req(srv, "GET", "/v1/features")
    assert code == 200
    f = by_id(out)
    assert set(f) == {"mevzuat", "emsal", "dd_masak", "dd_ilan", "dd_gazette"}
    assert f["mevzuat"]["enabled"] and f["mevzuat"]["state"] == "ready" and not f["mevzuat"]["online"]
    for fid in ("emsal", "dd_masak", "dd_ilan", "dd_gazette"):
        assert not f[fid]["enabled"] and f[fid]["state"] == "off" and f[fid]["online"]
    assert out["browser"] == {"kind": None, "path": None}


def test_precedent_search_is_the_emsal_online_switch(srv):
    code, out = req(srv, "POST", "/v1/features", {"id": "emsal", "enabled": True})
    assert code == 200 and by_id(out)["emsal"]["state"] == "ready"
    assert req(srv, "GET", "/v1/settings")[1]["emsal_online"] is True
    import os
    assert os.environ["KATIP_EMSAL_ONLINE"] == "1"


def test_masak_needs_its_lists_and_switching_on_downloads_them(srv, monkeypatch):
    from katip_kalkan.dd import service
    calls = []

    def fake_update(source="masak", **kw):
        calls.append(source)
        st = service.Store()
        st.replace_source("masak", [{"rid": "6415-7-1", "name": "ÖRNEK KİŞİ", "list": "6415-7"}], {"lists": 1},
                          service.now())
        return {"source": source, "status": "ok"}

    monkeypatch.setattr(service, "update", fake_update)
    code, out = req(srv, "POST", "/v1/features", {"id": "dd_masak", "enabled": True})
    assert code == 200 and by_id(out)["dd_masak"]["enabled"]
    f = wait_job(srv, "dd_masak")
    assert calls == ["masak"] and f["state"] == "ready" and f["detail"]["records"] == 1
    assert f["detail"]["data_as_of"]


def test_masak_failed_download_is_a_problem_not_ready(srv, monkeypatch):
    from katip_kalkan.dd import service
    monkeypatch.setattr(service, "update", lambda source="masak", **kw: {"status": "blocked", "error": "403"})
    req(srv, "POST", "/v1/features", {"id": "dd_masak", "enabled": True})
    f = wait_job(srv, "dd_masak")
    assert f["state"] == "problem" and f["job"]["state"] == "failed"


def test_browser_features_need_a_browser(srv, tmp_path):
    req(srv, "POST", "/v1/features", {"id": "dd_ilan", "enabled": True})
    f = by_id(req(srv, "GET", "/v1/features")[1])
    assert f["dd_ilan"]["state"] == "needs_setup" and f["dd_ilan"]["needs"] == "browser"
    fake_chromium(tmp_path)
    out = req(srv, "GET", "/v1/features")[1]
    assert out["browser"]["kind"] == "chromium" and by_id(out)["dd_ilan"]["state"] == "ready"


def test_google_chrome_counts_as_the_browser(srv, tmp_path, monkeypatch):
    app = tmp_path / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome"
    app.parent.mkdir(parents=True)
    app.write_text("")
    monkeypatch.setenv("KATIP_CHROME_APP", str(tmp_path / "Google Chrome.app"))
    assert req(srv, "GET", "/v1/features")[1]["browser"]["kind"] == "chrome"


def test_browser_install_runs_playwright_and_reports(srv, tmp_path, monkeypatch):
    from katip_engine import features
    monkeypatch.setattr(features, "_install_chromium", lambda: fake_chromium(tmp_path))
    monkeypatch.setattr(features, "_test_browser", lambda: None)
    # no download before the lawyer switched the feature on (that is the consent to go online)
    assert req(srv, "POST", "/v1/features/action", {"id": "dd_ilan", "action": "install_browser"})[0] == 400
    req(srv, "POST", "/v1/features", {"id": "dd_ilan", "enabled": True})
    code, out = req(srv, "POST", "/v1/features/action", {"id": "dd_ilan", "action": "install_browser"})
    assert code == 200
    f = wait_job(srv, "dd_ilan")
    assert f["job"]["state"] == "done"
    assert req(srv, "GET", "/v1/features")[1]["browser"]["kind"] == "chromium"


def test_browser_test_reports_a_browser_that_wont_start(srv, tmp_path, monkeypatch):
    from katip_engine import features
    fake_chromium(tmp_path)

    def broken():
        raise RuntimeError("crashed")

    monkeypatch.setattr(features, "_test_browser", broken)
    req(srv, "POST", "/v1/features", {"id": "dd_gazette", "enabled": True})
    req(srv, "POST", "/v1/features/action", {"id": "dd_gazette", "action": "test_browser"})
    f = wait_job(srv, "dd_gazette")
    assert f["job"] == {**f["job"], "state": "failed", "error": "RuntimeError", "action": "test_browser"}


def test_gazette_session_hours_and_logout(srv, monkeypatch):
    code, out = req(srv, "POST", "/v1/settings", {"tsg_session_hours": 0})
    assert code == 200
    import os
    assert os.environ["KATIP_TSG_SESSION_HOURS"] == "0"
    assert req(srv, "POST", "/v1/settings", {"tsg_session_hours": 99})[0] == 400
    from katip_kalkan.dd import service
    monkeypatch.setattr(service, "gazette_logout", lambda: {"logged_out": True})
    code, out = req(srv, "POST", "/v1/features/action", {"id": "dd_gazette", "action": "logout"})
    assert code == 200 and out["result"] == {"logged_out": True}
    g = by_id(out)["dd_gazette"]
    assert g["detail"]["session_until"] is None and g["detail"]["session_hours"] == 0


def test_unknown_feature_or_action_refused(srv):
    assert req(srv, "POST", "/v1/features", {"id": "everything", "enabled": True})[0] == 400
    assert req(srv, "POST", "/v1/features", {"id": "emsal", "enabled": "yes"})[0] == 400
    assert req(srv, "POST", "/v1/features/action", {"id": "emsal", "action": "install_browser"})[0] == 400


# -- what Claude sees -------------------------------------------------------------------------------------
def rpc(gate, method, params=None, mid=1):
    return gate.handle({"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}})


def tool_names(gate) -> set:
    return {t["name"] for t in rpc(gate, "tools/list")["result"]["tools"]}


def test_claude_sees_only_features_that_are_on_and_ready(tmp_path):
    from katip_engine import mcp, settings
    gate = mcp.Gate(io.StringIO())
    init = rpc(gate, "initialize", {"protocolVersion": "2025-06-18"})["result"]
    assert init["capabilities"]["tools"]["listChanged"] is True
    names = tool_names(gate)
    assert {"mask_file", "list_files", "restore_to_file", "mevzuat_bak", "katip_status"} <= names
    assert not names & {"emsal_ara", "geri_bildirim", "dd_screen", "dd_update", "dd_ilan_lookup", "dd_gazette_lookup"}
    out = rpc(gate, "tools/call", {"name": "dd_screen", "arguments": {"name": "x"}})["result"]
    assert out["isError"] and "Katip" in out["content"][0]["text"]

    settings.save({"emsal_online": True, "features": {"dd_masak": True, "mevzuat": False}})
    assert "dd_screen" not in tool_names(gate)  # MASAK is on but its lists aren't here yet
    from katip_kalkan.dd import service
    service.Store().replace_source("masak", [{"rid": "6415-7-1", "name": "ÖRNEK KİŞİ"}], {}, service.now())
    names = tool_names(gate)
    assert {"emsal_ara", "geri_bildirim", "dd_screen", "dd_record", "dd_sources", "dd_update"} <= names
    assert "mevzuat_bak" not in names and "dd_ilan_lookup" not in names  # no browser yet

    fake_chromium(tmp_path)
    settings.save({"features": {"dd_ilan": True, "dd_gazette": True}})
    assert {"dd_ilan_lookup", "dd_gazette_lookup", "dd_gazette_logout"} <= tool_names(gate)


def test_a_failing_feature_check_never_takes_masking_down(monkeypatch):
    from katip_engine import features, mcp

    def boom(names):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(features, "visible_tools", boom)
    gate = mcp.Gate(io.StringIO())
    names = tool_names(gate)
    assert "mask_file" in names and not names & features.GATED
    out = rpc(gate, "tools/call", {"name": "katip_status", "arguments": {}})["result"]
    assert out["isError"] is False


def test_switching_the_gazette_off_logs_out(srv, monkeypatch):
    from katip_kalkan.dd import service
    done = threading.Event()
    monkeypatch.setattr(service, "gazette_logout", lambda: done.set() or {"logged_out": True})
    req(srv, "POST", "/v1/features", {"id": "dd_gazette", "enabled": True})
    req(srv, "POST", "/v1/features", {"id": "dd_gazette", "enabled": False})
    assert done.wait(5)


def test_gate_tells_a_running_claude_when_its_tools_change():
    from katip_engine import mcp, settings
    out = io.StringIO()
    gate = mcp.Gate(out)
    rpc(gate, "initialize", {"protocolVersion": "2025-06-18"})
    tool_names(gate)
    assert gate.check() is False and out.getvalue() == ""  # nothing changed, nothing sent
    settings.save({"emsal_online": True})
    assert gate.check() is True
    msg = json.loads(out.getvalue().splitlines()[-1])
    assert msg == {"jsonrpc": "2.0", "method": "notifications/tools/list_changed"}


# -- models ---------------------------------------------------------------------------------------------
def fake_model(folder: Path) -> Path:
    (folder / "onnx").mkdir(parents=True)
    (folder / "config.json").write_text("{}")
    (folder / "tokenizer.json").write_text("{}")
    (folder / "onnx" / "model_quantized.onnx").write_bytes(b"\0" * 2048)
    return folder


def test_add_use_and_remove_a_model_folder(srv, tmp_path):
    folder = fake_model(tmp_path / "my-model")
    code, out = req(srv, "POST", "/v1/models/custom", {"path": str(folder)})
    assert code == 200
    mine = [m for m in out["models"] if m["custom"]]
    assert len(mine) == 1 and mine[0]["name"] == str(folder) and mine[0]["downloaded"]
    assert req(srv, "POST", "/v1/settings", {"model": str(folder)})[0] == 200
    import os
    assert os.environ["KATIP_MODEL"] == str(folder)
    # the one in use can't be removed; after switching back it can
    assert req(srv, "POST", "/v1/models/custom/remove", {"path": str(folder)})[0] == 409
    req(srv, "POST", "/v1/settings", {"model": "nano"})
    code, out = req(srv, "POST", "/v1/models/custom/remove", {"path": str(folder)})
    assert code == 200 and not [m for m in out["models"] if m["custom"]]
    assert folder.exists()  # the lawyer's folder itself is never deleted


def test_not_a_model_folder_or_unlisted_path_refused(srv, tmp_path):
    (tmp_path / "empty").mkdir()
    assert req(srv, "POST", "/v1/models/custom", {"path": str(tmp_path / "empty")})[0] == 400
    assert req(srv, "POST", "/v1/models/custom", {"path": "relative/path"})[0] == 400
    assert req(srv, "POST", "/v1/settings", {"model": str(tmp_path / "elsewhere")})[0] == 400


def test_delete_a_downloaded_model(srv, tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_MASK_CACHE", str(tmp_path / "cache"))
    from katip_engine import models
    from katip_mask import models as sdk
    info = sdk.MODELS["mini"]
    folder = sdk.cache_dir() / "mini" / info["revision"]
    for f, w in info["files"].items():
        (folder / f).parent.mkdir(parents=True, exist_ok=True)
        (folder / f).write_bytes(b"\0" * w["size"])
    assert models.downloaded("mini")
    assert req(srv, "POST", "/v1/models/delete", {"name": "nano"})[0] == 400  # included, can't go
    code, out = req(srv, "POST", "/v1/models/delete", {"name": "mini"})
    assert code == 200 and not models.downloaded("mini")
    assert not [m for m in out["models"] if m["name"] == "mini"][0]["downloaded"]


def test_model_in_use_cant_be_deleted(srv, monkeypatch):
    from katip_engine import models
    monkeypatch.setattr(models, "downloaded", lambda name, verify=False: True)
    req(srv, "POST", "/v1/settings", {"model": "base"})
    assert req(srv, "POST", "/v1/models/delete", {"name": "base"})[0] == 409
