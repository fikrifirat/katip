"""Ticaret Sicili Gazetesi through the lawyer's own login, in a browser on their computer.

Why: www.ticaretsicil.gov.tr shows notices only after login (e-Devlet, or a member account
whose form has a captcha). The lawyer logs in themselves in the window this opens; Katip
never types credentials and never touches a captcha. Then it searches the site's own
"İlan Görüntüleme" form for ONE named target and saves the free gazette page of a few notices.

The login must not outlive the run. Each run uses a new, empty browser profile in a temporary
folder; at the end, also when the run fails, it logs out on the site (which ends the session on
the site's side) and deletes the profile.

Rules: one target per run, at most ``max_pages`` gazette pages (default 3), several seconds
between page loads, never the "Sepete Ekle" (paid copy) button, stop at any captcha or block.
Search needs the registry office (e.g. BURSA) and at least the first 5 letters of the name.
"""
from __future__ import annotations

import base64
import re
import shutil
import tempfile
import time
from pathlib import Path

BASE = "https://www.ticaretsicil.gov.tr"
LOGIN = BASE + "/view/hizlierisim/girisyap.php"
SEARCH = BASE + "/view/hizlierisim/ilangoruntuleme.php"
LOGOUT = BASE + "/view/menu/cikis.php"

_TXT = "async (u) => { const r = await fetch(u, {credentials: 'include'}); return await r.text(); }"
_BIN = """async (u) => { const r = await fetch(u, {credentials: 'include'});
  const b = new Uint8Array(await r.arrayBuffer()); let s = '';
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
  return {status: r.status, ct: r.headers.get('content-type'), b64: btoa(s)}; }"""


def tr_upper(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


def _iso(d: str) -> str:
    m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", d.strip())
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""


def parse_results(rows: list[list[str]], links: list[str]) -> list[dict]:
    """Result table rows (header first) + the 'Gazete' links in row order -> notices to fetch."""
    if not rows:
        return []
    head = [h.lower() for h in rows[0]]

    def col(name):
        return next((i for i, h in enumerate(head) if name in h), None)

    ix = {k: col(k) for k in ("müdürlük", "unvan", "tarih", "sayı", "sayfa", "tür")}
    out = []
    for r, href in zip([r for r in rows[1:] if len(r) >= len(head) - 2], links):
        g = lambda k: r[ix[k]].strip() if ix[k] is not None and ix[k] < len(r) else ""  # noqa: E731
        date, issue, page = _iso(g("tarih")), g("sayı"), g("sayfa")
        out.append({"office": g("müdürlük"), "unvan": g("unvan"), "date": date, "issue": issue, "page": page,
                    "type": g("tür"), "href": href, "file": f"tsg_{date}_{issue}_p{page}.pdf"})
    return out


def _chrome(profile: str):
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    try:
        ctx = pw.chromium.launch_persistent_context(profile, channel="chrome", headless=False, locale="tr-TR",
                                                    chromium_sandbox=True)  # Playwright adds --no-sandbox otherwise
    except Exception:
        ctx = pw.chromium.launch_persistent_context(profile, headless=False, locale="tr-TR", chromium_sandbox=True)
    ctx._katip_pw = pw  # stopped in _close
    return ctx


def _close(ctx) -> None:
    try:
        ctx.close()
    finally:
        pw = getattr(ctx, "_katip_pw", None)
        if pw:
            pw.stop()


_LOGOUT_MARK = re.compile(r"cikis\.php|ÇIKIŞ|Çıkış", re.I)


def _live_url(pg) -> str:
    """The tab's address now. Playwright's ``page.url`` only updates while Playwright is called,
    so ask the page itself."""
    try:
        return pg.evaluate("location.href")
    except Exception:  # noqa: BLE001 - navigating or closed
        return str(getattr(pg, "url", "") or "")


def _tabs(ctx) -> list[str]:
    return [_live_url(pg) for pg in list(getattr(ctx, "pages", []))]


def _logged_in(ctx, base: str = BASE) -> bool:
    """True once any tab on the site, other than the login page, shows the logout link. While
    e-Devlet redirects, a tab is navigating and reading it raises; that just means "not yet"."""
    host = base.split("//", 1)[-1]
    for pg in list(getattr(ctx, "pages", [])):
        try:
            url = _live_url(pg) or base
            if host in url and "girisyap.php" not in url and _LOGOUT_MARK.search(pg.content()):
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _wait(ctx, seconds: float) -> None:
    """Sleep while letting Playwright process browser events (new tabs, navigations)."""
    try:
        ctx.pages[0].wait_for_timeout(seconds * 1000)
    except Exception:  # noqa: BLE001
        time.sleep(seconds)


def _enter_pressed() -> bool:
    try:
        import select
        import sys
        if not sys.stdin.isatty():
            return False
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            sys.stdin.readline()
            return True
    except Exception:  # noqa: BLE001 - no select on this platform
        pass
    return False


def lookup(name: str, office: str, *, out_dir: Path, max_pages: int = 3, court: bool = False, pause: float = 6.0,
           login_timeout: float = 360, launcher=None, say=print, poll: float = 3.0,
           base: str = BASE) -> tuple[list[Path], dict]:
    if len(name.strip()) < 5:
        raise ValueError("the site needs at least the first 5 letters of the name")
    login, search, logout = (base + "/view/hizlierisim/girisyap.php", base + "/view/hizlierisim/ilangoruntuleme.php",
                             base + "/view/menu/cikis.php")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="katip-tsg-")
    info = {"target": name, "office": office, "blocked": None, "logged_out": False}
    saved: list[Path] = []
    ctx = None
    try:
        ctx = (launcher or _chrome)(profile)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(login, wait_until="domcontentloaded", timeout=90000)
        say("Log in with e-Devlet in the Chrome window that just opened. Katip notices the login by itself "
            f"(or press Enter here once you are in). It waits up to {int(login_timeout // 60)} min, and logs out "
            "and forgets the login when done.")
        t0 = last = time.time()
        while not _logged_in(ctx, base):
            if _enter_pressed():
                pg = ctx.pages[-1]
                pg.goto(search, wait_until="domcontentloaded", timeout=90000)
                if "girisyap.php" not in _live_url(pg):
                    break
                say("  the site still shows its login page; finish the login in the Chrome window")
            if time.time() - t0 > login_timeout:
                info["blocked"] = "not logged in within the time limit"
                info["tabs"] = _tabs(ctx)
                return saved, info
            if time.time() - last > 15:
                last = time.time()
                say(f"  waiting for the login... open tabs: {', '.join(_tabs(ctx)) or '-'}")
            _wait(ctx, poll)
        say("Logged in. Searching the gazette (a few seconds between pages)...")
        host = base.split("//", 1)[-1]
        page = next((pg for pg in reversed(ctx.pages) if host in (_live_url(pg) or host)), page)
        try:
            page.wait_for_load_state("domcontentloaded")
        except Exception:  # noqa: BLE001
            pass
        time.sleep(pause)
        page.goto(search, wait_until="domcontentloaded", timeout=90000)
        if "girisyap.php" in page.url:
            info["blocked"] = "login was not accepted"
            return saved, info
        page.select_option("#SicilMudurluguId", label=tr_upper(office))
        if court:
            page.check("#BagliIlan")
        page.fill("#TicaretUnvani", tr_upper(name))
        page.click("#FormIlanGoruntuleme button[type=submit]")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(pause)
        rows = page.eval_on_selector_all("table tr", "rs => rs.map(r => [...r.cells].map(c => c.innerText.trim()))")
        links = page.eval_on_selector_all("a[href*='pdf_goster.php']", "els => els.map(e => e.getAttribute('href'))")
        rows = [r for r in rows if r]
        hits = parse_results(next((rows[i:] for i, r in enumerate(rows) if any("Unvan" in c for c in r)), []), links)
        info["results"] = len(hits)
        say(f"{len(hits)} notices on the site; saving up to {max_pages} gazette pages...")
        info["notices"] = [{k: h[k] for k in ("date", "issue", "page", "type", "unvan")} for h in hits]
        for h in hits[:max_pages]:
            html = page.evaluate(_TXT, "/view/hizlierisim/" + h["href"].lstrip("/"))
            m = re.search(r'(?:src|data)="(/tmp_gazete/[^"]+\.pdf)"', html)
            if not m:
                info["blocked"] = "security code asked" if "FormGuvenlikKodu" in html else "gazette page not found"
                break
            time.sleep(pause)
            res = page.evaluate(_BIN, m.group(1))
            body = base64.b64decode(res["b64"])
            if not body.startswith(b"%PDF"):
                info["blocked"] = f"not a PDF ({res.get('ct')})"
                break
            p = out_dir / h["file"]
            p.write_bytes(body)
            saved.append(p)
            say(f"  saved {p.name}")
            time.sleep(pause)
        return saved, info
    finally:
        if ctx is not None:
            for attempt in range(3):  # the page may still be navigating; the logout must happen
                try:
                    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                    pg.goto(logout, wait_until="domcontentloaded", timeout=30000)
                    pg.goto(search, wait_until="domcontentloaded", timeout=30000)  # proof: the site sends us to login
                    info["logged_out"] = "girisyap.php" in _live_url(pg)
                    info.pop("logout_error", None)
                    break
                except Exception as e:  # noqa: BLE001
                    info["logout_error"] = repr(e)[:200]
                    time.sleep(1)
            try:
                _close(ctx)
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(profile, ignore_errors=True)
