"""Gazette lookup against a fake ticaretsicil site in a real (headless) Chromium.

The fake login opens e-Devlet in a NEW tab that lands on /index.php after two redirects, the
way fikri saw it on 22 Nov 2026, while the first tab stays on the login page. Skipped when
Playwright or a Chromium is not installed.
"""
from __future__ import annotations

import os
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
                         "<td><a href='#' onclick='location=\"/cart\"'>Sepete Ekle</a></td></tr></table>")
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


@pytest.mark.skipif(CHROME is None, reason="no Chromium binary")
@pytest.mark.parametrize("new_tab", [True, False], ids=["login-in-new-tab", "login-in-same-tab"])
def test_lookup_end_to_end(tmp_path, new_tab):
    Site.new_tab, Site.log = new_tab, []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    profiles = []

    def launcher(profile):
        profiles.append(Path(profile))
        p = pw.sync_playwright().start()
        ctx = p.chromium.launch_persistent_context(profile, executable_path=CHROME, headless=True)
        ctx._katip_pw = p
        return ctx

    lines = []
    try:
        saved, info = gb.lookup("Kuzeyrüzgarı", "Bursa", out_dir=tmp_path, launcher=launcher, pause=0.2,
                                login_timeout=30, poll=0.3, base=base, say=lines.append)
    finally:
        srv.shutdown()
    assert info["blocked"] is None, (info, lines)
    assert [p.name for p in saved] == ["tsg_2026-11-19_11712_p101.pdf"] and saved[0].read_bytes() == PDF
    assert info["logged_out"] is True
    assert not profiles[0].exists()
    assert "/cart" not in Site.log and any(x.startswith("/view/menu/cikis.php") for x in Site.log)
