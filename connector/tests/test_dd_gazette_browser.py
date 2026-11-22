"""Gazette lookup through the lawyer's own TSG login: the login must never outlive the run."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from katip_kalkan.dd.sources import gazette_browser as gb  # noqa: E402


class FakePage:
    def __init__(self, fail_at=None):
        self.visited, self.fail_at, self.content_html = [], fail_at, "<a href='/view/menu/cikis.php'>ÇIKIŞ</a>"

    def goto(self, url, **kw):
        self.visited.append(url)
        if self.fail_at and self.fail_at in url:
            raise RuntimeError("network down")

    def content(self):
        return self.content_html


class FakeContext:
    def __init__(self, page):
        self.page, self.closed = page, False
        self.pages = [page]

    def close(self):
        self.closed = True


def test_profile_is_deleted_and_logout_tried_even_when_the_run_fails(tmp_path):
    page = FakePage(fail_at="ilangoruntuleme")
    seen = {}

    def launcher(profile):
        seen["profile"] = Path(profile)
        assert seen["profile"].exists()
        return FakeContext(page)

    with pytest.raises(RuntimeError):
        gb.lookup("Kuzeyrüzgarı Tekstil", "BURSA", out_dir=tmp_path, launcher=launcher, pause=0, login_timeout=1)
    assert not seen["profile"].exists()
    assert page.visited[-1].endswith("/view/menu/cikis.php")


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
        gb.lookup("Kuzeyrüzgarı Tekstil", "BURSA", out_dir=tmp_path, launcher=lambda p: FakeContext(page), pause=0,
                  login_timeout=30, poll=0)
    assert page.calls >= 3 and page.visited[-1].endswith("/view/menu/cikis.php")
