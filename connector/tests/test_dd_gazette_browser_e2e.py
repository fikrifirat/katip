"""Gazette lookup against a fake ticaretsicil site in a real (headless) Chromium.

The fake login opens e-Devlet in a NEW tab that lands on /index.php after two redirects, the
way fikri saw it on 22 Nov 2026, while the first tab stays on the login page. Skipped when
Playwright or a Chromium is not installed.
"""
from __future__ import annotations

import os
import time
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
pw = pytest.importorskip("playwright.sync_api")

from katip_kalkan.dd.sources import gazette_browser as gb  # noqa: E402

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
CHROME = next((p for p in [os.environ.get("KATIP_TEST_CHROMIUM", ""), "/opt/pw-browsers/chromium-1243/chrome-linux/chrome",
                           "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"] if p and Path(p).exists()), None)


SANDBOX = getattr(os, "geteuid", lambda: 1)() != 0  # Chrome's sandbox refuses to run as root (CI containers)


class Site(BaseHTTPRequestHandler):
    log = []
    new_tab = True

    def log_message(self, *a):
        pass

    def _send(self, body, ctype="text/html; charset=utf-8", code=200, headers=()):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):  # noqa: N802
        p, logged = self.path, "logged=1" in (self.headers.get("Cookie") or "")
        Site.log.append(p)
        if p.startswith("/view/hizlierisim/girisyap.php"):
            go = "window.open('/edevlet','_blank')" if Site.new_tab else "location='/edevlet'"
            return self._send(f"<a id=ed href='/edevlet'>e-Devlet</a><script>setTimeout(()=>{go},800)</script>")
        if p.startswith("/edevlet"):
            return self._send("<meta http-equiv=refresh content='1;url=/back'>e-Devlet...")
        if p.startswith("/back"):
            return self._send("", code=302, headers=[("Location", "/index.php"), ("Set-Cookie", "logged=1; Path=/")])
        if p.startswith("/index.php"):
            return self._send("<a href='/view/menu/cikis.php'>ÇIKIŞ</a>" if logged else "<a>GİRİŞ</a>")
        if p.startswith("/view/hizlierisim/ilangoruntuleme.php"):
            if not logged:
                return self._send("", code=302, headers=[("Location", "/view/hizlierisim/girisyap.php")])
            table = ""
            if "TicaretUnvani=KUZEY" in p:
                table = ("<table><tr><th>Müdürlük</th><th>Sicil No</th><th>Unvan</th><th>Yayın Tarihi</th><th>Sayı</th>"
                         "<th>Sayfa</th><th>İlan Türü</th><th>Gazete</th><th>Sepete Ekle</th></tr>"
                         "<tr><td>BURSA</td><td>1</td><td>KUZEYRÜZGARI A.Ş.</td><td>19.11.2026</td><td>11712</td><td>101</td>"
                         "<td>Konkordato</td><td><a href='pdf_goster.php?Guid=a'>Gazete</a></td>"
                         "<td><a href='#' onclick='location=\"/cart\"'>Sepete Ekle</a></td></tr>"
                         # a second notice on the same gazette page: the page is fetched once
                         "<tr><td>BURSA</td><td>2</td><td>KUZEYRÜZGARI GIDA A.Ş.</td><td>19.11.2026</td><td>11712</td>"
                         "<td>101</td><td>Genel Kurul</td><td><a href='pdf_goster.php?Guid=b'>Gazete</a></td>"
                         "<td>Sepete Ekle</td></tr></table>")
            return self._send("<a href='/view/menu/cikis.php'>ÇIKIŞ</a><form id=FormIlanGoruntuleme method=get>"
                              "<select id=SicilMudurluguId name=SicilMudurluguId><option value=0>Seçiniz</option>"
                              "<option value=40>BURSA</option></select><input id=TicSicNo name=TicSicNo>"
                              "<input id=TicaretUnvani name=TicaretUnvani><input type=checkbox id=BagliIlan name=BagliIlan>"
                              "<button type=submit>Sorgula</button></form>" + table)
        if p.startswith("/view/hizlierisim/pdf_goster.php"):
            return self._send("<embed src=\"/tmp_gazete/x1.pdf\" type=\"application/pdf\" />")
        if p.startswith("/tmp_gazete/"):
            return self._send(PDF, "application/pdf")
        if p.startswith("/view/menu/cikis.php"):
            return self._send("", code=302, headers=[("Location", "/index.php"), ("Set-Cookie", "logged=0; Path=/")])
        if p.startswith("/cart"):
            raise AssertionError("the paid cart must never be touched")
        return self._send("not found", code=404)


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path / "dd"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    Site.log = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


class Counting(gb._Playwright):
    def __init__(self):
        super().__init__(executable_path=CHROME, headless_login=True, sandbox=SANDBOX)
        self.logins = 0

    def visible(self, profile):
        self.logins += 1
        self.profile = Path(profile)
        return super().visible(profile)


def run(base, tmp_path, **kw):
    b = Counting()
    saved, info = gb.lookup("Kuzeyrüzgarı", "Bursa", out_dir=tmp_path / "out", browser=b, pause=0.1,
                            login_timeout=30, poll=0.3, base=base, say=lambda *_: None, **kw)
    return b, saved, info


pytestmark = pytest.mark.skipif(CHROME is None, reason="no Chromium binary")


@pytest.mark.parametrize("new_tab", [True, False], ids=["login-in-new-tab", "login-in-same-tab"])
def test_login_once_then_headless_until_logout(site, tmp_path, new_tab):
    Site.new_tab = new_tab
    b, saved, info = run(site, tmp_path, keep_hours=8)
    assert info["blocked"] is None, info
    assert [p.name for p in saved] == ["tsg_2026-11-19_11712_p101.pdf"] and saved[0].read_bytes() == PDF
    assert info["results"] == 2 and sum("pdf_goster.php" in u for u in Site.log) == 1
    assert b.logins == 1 and not b.profile.exists() and gb.session_read() is not None
    b2, saved2, info2 = run(site, tmp_path, keep_hours=8)  # second run: no window, saved login
    assert b2.logins == 0 and info2["session"] == "reused saved login" and saved2
    out = gb.logout(browser=gb._Playwright(executable_path=CHROME, sandbox=SANDBOX), base=site)
    assert out["logged_out"] is True and gb.session_read() is None
    assert "/cart" not in Site.log


def test_nothing_kept_means_logged_out_after_the_run(site, tmp_path):
    Site.new_tab = False
    b, saved, info = run(site, tmp_path, keep_hours=0)
    assert saved and info["logged_out"] is True and gb.session_read() is None


def test_expired_login_is_logged_out_then_asked_again(site, tmp_path):
    Site.new_tab = False
    run(site, tmp_path, keep_hours=8)
    sess = gb.session_read()
    gb.session_save(sess["state"], hours=1)
    f = gb._session_file()
    import json
    from katip_kalkan import vault
    raw = f.read_bytes()
    data = json.loads(vault.AESGCM(vault._key()).decrypt(raw[:12], raw[12:], gb._AAD))
    data["expires"] = 0
    nonce = os.urandom(12)
    f.write_bytes(nonce + vault.AESGCM(vault._key()).encrypt(nonce, json.dumps(data).encode(), gb._AAD))
    Site.log = []
    b, saved, info = run(site, tmp_path, keep_hours=8)
    assert b.logins == 1 and saved  # asked to log in again
    assert Site.log.index("/view/menu/cikis.php") < Site.log.index("/view/hizlierisim/girisyap.php")


def test_unknown_registry_office_stops_without_a_30_second_wait(site, tmp_path):
    Site.new_tab = False
    b = Counting()
    t = time.time()
    saved, info = gb.lookup("Kuzeyrüzgarı", "Narnia", out_dir=tmp_path / "out", browser=b, pause=0.1,
                            login_timeout=30, poll=0.3, base=site, say=lambda *_: None, keep_hours=0)
    assert not saved and "not on the site's list" in info["blocked"] and time.time() - t < 25
