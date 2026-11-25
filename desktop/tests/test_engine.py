"""The Katip engine on the connector's synthetic fixtures (never real client documents).

Run:  cd desktop && python -m pytest -q tests/test_engine.py
"""
from __future__ import annotations

import http.client
import json
import sys
import threading
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
FIX = HERE.parent.parent / "connector" / "tests" / "fixtures"
TEXT = (FIX / "dilekce_01.txt").read_text(encoding="utf-8")
GOLD = json.loads((FIX / "dilekce_01.gold.json").read_text(encoding="utf-8"))
HARD = [g["text"] for g in GOLD if g["entity_type"] in ("TCKN", "PHONE", "EMAIL", "IBAN")]
NAMES = sorted({g["text"] for g in GOLD if g["entity_type"] == "PERSON"})


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    monkeypatch.delenv("KATIP_EMSAL_ONLINE", raising=False)


@pytest.fixture
def srv():
    from katip_engine.server import Server
    s = Server(0, "t0k3n", idle_exit=None)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s
    s.shutdown()
    s.server_close()


def req(s, method, path, body=None, token="t0k3n", headers=None):
    c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=60)
    h = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {}), **(headers or {})}
    c.request(method, path, None if body is None else json.dumps(body).encode(), h)
    r = c.getresponse()
    return r.status, json.loads(r.read() or b"{}")


def test_health_needs_no_token(srv):
    assert req(srv, "GET", "/healthz", token=None) == (200, {"ok": True})


def test_token_required(srv):
    assert req(srv, "GET", "/v1/status", token=None)[0] == 401
    assert req(srv, "GET", "/v1/status", token="wrong")[0] == 401
    assert req(srv, "POST", "/v1/mask", {"text": TEXT}, token=None)[0] == 401


def test_web_pages_refused(srv):
    code, body = req(srv, "POST", "/v1/mask", {"text": TEXT}, headers={"Origin": "https://evil.example"})
    assert code == 403 and "web pages" in body["error"]
    assert req(srv, "GET", "/v1/status", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403


def test_wrong_host_refused(srv):  # DNS rebinding: a page on evil.example resolving to 127.0.0.1
    assert req(srv, "GET", "/v1/status", headers={"Host": f"evil.example:{srv.port}"})[0] == 403


def test_status(srv):
    code, st = req(srv, "GET", "/v1/status")
    assert code == 200 and st["engine"] == "katip-engine"
    assert st["sources"]["emsal"]["on"] is False and st["sources"]["mevzuat"]["network"] is False


def test_mask_hides_values_and_restore_brings_them_back(srv):
    code, m = req(srv, "POST", "/v1/mask", {"text": TEXT, "profile": "ai", "matter": "t1"})
    assert code == 200, m
    out = m["masked_text"]
    for v in HARD + NAMES:
        assert v not in out, v
    assert m["placeholders"] and m["entity_counts"]
    code, r = req(srv, "POST", "/v1/restore", {"text": out, "matter": "t1"})
    assert code == 200 and r["placeholders_restored"] >= len(m["placeholders"])
    for v in NAMES:
        assert v in r["text"]


def test_same_matter_same_placeholders(srv):
    a = req(srv, "POST", "/v1/mask", {"text": TEXT, "matter": "t2"})[1]["masked_text"]
    b = req(srv, "POST", "/v1/mask", {"text": TEXT, "matter": "t2"})[1]["masked_text"]
    assert a == b


def test_mask_file(srv):
    code, m = req(srv, "POST", "/v1/mask_file", {"path": str(FIX / "dilekce_01.txt"), "matter": "t3"})
    assert code == 200, m
    assert all(v not in m["masked_text"] for v in HARD)


def test_precedent_search_off_by_default(srv):
    code, body = req(srv, "POST", "/v1/sources/emsal", {"queries": ["kira tespit"]})
    assert code == 403


def test_errors_carry_no_document_text(srv):
    code, body = req(srv, "POST", "/v1/mask", {"nottext": TEXT})
    assert code == 400 and TEXT[:20] not in json.dumps(body)


def test_idle_exit(tmp_path):
    from katip_engine.server import Server
    s = Server(0, "x", idle_exit=0.4)
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    t.join(timeout=10)
    s.server_close()
    assert not t.is_alive()


def test_serve_writes_private_state_file(tmp_path):
    from katip_engine import server
    t = threading.Thread(target=server.serve, kwargs={"port": 0, "idle_exit": 1.0, "quiet": True}, daemon=True)
    t.start()
    sf = server.state_file()
    for _ in range(100):
        if sf.exists():
            break
        time.sleep(0.05)
    st = json.loads(sf.read_text())
    assert st["token"] and st["port"]
    if sys.platform != "win32":  # Windows has no owner-only file modes; the folder ACL applies there
        assert oct(sf.stat().st_mode & 0o777) == "0o600"
    t.join(timeout=15)
    assert not sf.exists()  # removed when the engine exits


def test_agent_plist_passes_settings_on(monkeypatch):
    from katip_engine import cli
    pl = cli.agent_plist(60)
    assert pl["RunAtLoad"] is False and pl["KeepAlive"] is False
    assert pl["ProgramArguments"][-4:] == ["serve", "--idle-exit", "60", "--quiet"]
    assert pl["EnvironmentVariables"]["KATIP_NO_KEYCHAIN"] == "1"  # set by the env fixture
    assert "KATIP_EMSAL_ONLINE" not in pl["EnvironmentVariables"]


def test_install_waits_for_launchd_and_retries(monkeypatch, tmp_path):
    """Reinstalling right after a bootout: launchd answers error 5 until the old agent is gone."""
    from katip_engine import cli
    calls = []
    state = {"loaded_polls": 2, "bootstrap_fails": 2}

    class R:
        def __init__(self, rc): self.returncode, self.stderr = rc, "Bootstrap failed: 5" if rc else ""

    def fake(*args):
        calls.append(args[0])
        if args[0] == "print":
            state["loaded_polls"] -= 1
            return R(0 if state["loaded_polls"] >= 0 else 113)
        if args[0] == "bootstrap":
            state["bootstrap_fails"] -= 1
            return R(5 if state["bootstrap_fails"] >= 0 else 0)
        return R(0)

    monkeypatch.setattr(cli, "_launchctl", fake)
    monkeypatch.setattr(cli, "plist_path", lambda: tmp_path / "agent.plist")
    monkeypatch.setattr(cli, "LOG", tmp_path / "engine.log")
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    monkeypatch.setattr(cli.sys, "platform", "darwin")
    r = cli.install(60)
    assert r["ok"] is True
    assert calls.count("bootstrap") == 3 and calls.index("bootstrap") > calls.index("print")


def test_status_names_its_binary(srv):
    # a source run reports no binary; the frozen engine reports its real path, so the app can spot a foreign engine
    st = req(srv, "GET", "/v1/status")[1]
    assert "exe" in st and st["exe"] is None
