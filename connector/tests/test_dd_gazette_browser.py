"""Gazette lookup through the lawyer's own TSG login: the login must never outlive the run."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from katip_kalkan.dd.sources import gazette_browser as gb  # noqa: E402


class FakePage:
    def __init__(self, fail_at=None):
        self.visited, self.fail_at, self.content_html = [], fail_at, "<a href='/view/menu/cikis.php'>ÇIKIŞ</a>"
        self.url = ""

    def goto(self, url, **kw):
        self.visited.append(url)
        self.url = url.replace("view/hizlierisim/girisyap.php", "index.php")  # the person logs in at once
        if self.fail_at and self.fail_at in url:
            raise RuntimeError("network down")

    def evaluate(self, js, *a):
        return self.url

    def content(self):
        return self.content_html

    def wait_for_timeout(self, ms):
        pass


class FakeContext:
    def __init__(self, page):
        self.page, self.closed = page, False
        self.pages = [page]

    def new_page(self):
        return self.page

    def storage_state(self):
        return {"cookies": [{"name": "PHPSESSID", "value": "x"}]}

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, page):
        self.page, self.profiles, self.states, self.stopped = page, [], [], False

    def visible(self, profile):
        self.profiles.append(Path(profile))
        assert Path(profile).exists()
        return FakeContext(self.page)

    def headless(self, state):
        self.states.append(state)
        return FakeContext(self.page)

    def stop(self):
        self.stopped = True


@pytest.fixture(autouse=True)
def katip_home(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path / "dd"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")


def test_failed_run_deletes_login_profile_and_logs_out_when_nothing_is_kept(tmp_path):
    page = FakePage(fail_at="ilangoruntuleme")
    b = FakeBrowser(page)
    with pytest.raises(RuntimeError):
        gb.lookup("Kuzeyrüzgarı Tekstil", "BURSA", out_dir=tmp_path, browser=b, pause=0, login_timeout=1, poll=0,
                  keep_hours=0)
    assert not b.profiles[0].exists() and b.stopped
    assert any(v.endswith("/view/menu/cikis.php") for v in page.visited)
    assert gb.session_read() is None


def test_session_is_encrypted_and_expires(tmp_path):
    exp = gb.session_save({"cookies": [{"name": "PHPSESSID", "value": "secret-cookie"}]}, hours=8)
    raw = gb._session_file().read_bytes()
    assert b"secret-cookie" not in raw
    if os.name == "posix":  # Windows has no POSIX file modes
        assert oct(gb._session_file().stat().st_mode)[-3:] == "600"
    assert gb.session_read()["expires"] == exp
    assert gb.session_save({"cookies": []}, hours=0) is None  # 0 hours: nothing kept


def test_tr_upper_and_rows():
    assert gb.tr_upper("kuzeyrüzgarı tekstil ii") == "KUZEYRÜZGARI TEKSTİL İİ"
    rows = [["Müdürlük", "Sicil No", "Unvan", "Yayın Tarihi", "Sayı", "Sayfa", "İlan Türü", "Gazete"],
            ["BURSA", "69921", "KUZEYRÜZGARI TEKSTİL A.Ş.", "19.11.2026", "11712", "101", "Konkordato", ""]]
    links = ["pdf_goster.php?Guid=abc"]
    got = gb.parse_results(rows, links)
    assert got == [{"office": "BURSA", "unvan": "KUZEYRÜZGARI TEKSTİL A.Ş.", "date": "2026-11-19", "issue": "11712",
                    "page": "101", "type": "Konkordato", "href": "pdf_goster.php?Guid=abc",
                    "file": "tsg_2026-11-19_11712_p101.pdf"}]


def test_service_ingests_saved_pages_and_reports_logout(tmp_path, monkeypatch):
    from katip_kalkan.dd import service
    from katip_kalkan.dd.store import Store
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path))
    pdf = tmp_path / "tsg" / "tsg_2026-11-19_11712_p101.pdf"

    def fake_lookup(name, office, *, out_dir, max_pages, court, **kw):
        assert Path(out_dir) == tmp_path / "tsg"
        return [pdf], {"results": 29, "logged_out": True, "blocked": None}
    monkeypatch.setattr(gb, "lookup", fake_lookup)
    monkeypatch.setattr(service, "add_gazette", lambda paths, use_ocr=False, store=None: {"status": "ok", "notices": 3})
    out = service.gazette_lookup("Kuzeyrüzgarı", "Bursa", store=Store())
    assert out["status"] == "ok" and out["saved_pages"] == 1 and out["logged_out"] is True and out["notices"] == 3


def test_kalkan_has_gazette_lookup_tool():
    from katip_kalkan import local_server
    tools = {t["name"]: t for t in local_server.build().handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]}
    t = tools["dd_gazette_lookup"]
    assert t["annotations"]["openWorldHint"] is True and set(t["inputSchema"]["required"]) == {"target", "office"}


def test_login_wait_survives_navigation(tmp_path):
    """e-Devlet redirects while we poll: page.content() raises 'page is navigating'."""
    class Navigating(FakePage):
        def __init__(self):
            super().__init__(fail_at="ilangoruntuleme")
            self.calls = 0

        def content(self):
            self.calls += 1
            if self.calls <= 2:
                raise RuntimeError("Page.content: Unable to retrieve content because the page is navigating")
            return self.content_html

    page = Navigating()
    with pytest.raises(RuntimeError, match="network down"):  # got past the login wait to the search page
        gb.lookup("Kuzeyrüzgarı Tekstil", "BURSA", out_dir=tmp_path, browser=FakeBrowser(page), pause=0,
                  login_timeout=30, poll=0, keep_hours=0)
    assert page.calls >= 3


def test_registry_office_from_court_district():
    opts = ["Seçiniz", "ANKARA", "BURSA", "İSTANBUL", "İZMİR"]
    assert gb.resolve_office("Bursa", opts) == "BURSA"
    assert gb.resolve_office("izmir", opts) == "İZMİR"
    assert gb.resolve_office("BAKIRKÖY", opts) == "İSTANBUL"  # a court district, registered in Istanbul
    assert gb.resolve_office("İstanbul Anadolu", opts) == "İSTANBUL"
    assert gb.resolve_office("Ankara Batı", opts) == "ANKARA"
    assert gb.resolve_office("Narnia", opts) == ""


def test_no_chrome_gives_a_plain_install_hint(monkeypatch):
    from katip_kalkan.dd import service

    def boom(*a, **k):
        raise RuntimeError("BrowserType.launch: Executable doesn't exist at /x/chrome")
    monkeypatch.setattr(gb, "lookup", boom)
    out = service.gazette_lookup("Kuzeyrüzgarı", "BURSA")
    assert out["status"] == "no_browser" and "google.com/chrome" in out["error"]
