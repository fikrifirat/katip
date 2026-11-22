"""Ticaret Sicili Gazetesi through the lawyer's own login, in a browser on their computer.

Why: www.ticaretsicil.gov.tr shows notices only after login (e-Devlet, or a member account
whose form has a captcha). The lawyer logs in themselves in the window this opens; Katip
never types credentials and never touches a captcha. Then it searches the site's own
"İlan Görüntüleme" form for ONE named target and saves the free gazette page of a few notices.

The login is bounded. The lawyer logs in once in a visible window (a new, empty browser profile
in a temporary folder, deleted right after). Katip keeps only the site's session cookies,
encrypted with Katip's own key (AES-256-GCM, key in the macOS Keychain), for ``keep_hours``
(default 8, ``KATIP_TSG_SESSION_HOURS``; 0 = log out after every run). Searches and downloads
run headless, so no window opens again while the session lasts. When it expires, the next run
logs out on the site and deletes it; ``katip-kalkan dd gazette-logout`` does that at once.

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


# Court districts that are not registry offices of their own: the company is registered in the city.
_COURT_CITY = {"BAKIRKÖY": "İSTANBUL", "ANADOLU": "İSTANBUL", "KARTAL": "İSTANBUL",
               "KÜÇÜKÇEKMECE": "İSTANBUL", "BÜYÜKÇEKMECE": "İSTANBUL", "GAZİOSMANPAŞA": "İSTANBUL",
               "ÇATALCA": "İSTANBUL", "SİLİVRİ": "İSTANBUL", "ŞİLE": "İSTANBUL", "BATI": "ANKARA"}


def resolve_office(office: str, options: list[str]) -> str:
    """The site's label for a registry office, or "" if it is not on the list.

    Takes the office as typed, or the city of an Istanbul/Ankara court district (Bakırköy → İSTANBUL).
    """
    want = tr_upper(office).strip()
    labels = {tr_upper(o).strip(): o for o in options if o.strip()}
    if want in labels:
        return labels[want]
    for word in want.split():
        city = _COURT_CITY.get(word)
        if city and city in labels:
            return labels[city]
    return ""


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


class _Playwright:
    """One Playwright for the run: a visible Chrome for the login, headless contexts after it."""

    def __init__(self, executable_path: str | None = None, headless_login: bool = False, sandbox: bool = True):
        from playwright.sync_api import sync_playwright

        self.pw = sync_playwright().start()
        self.exe, self.headless_login, self.browser, self.sandbox = executable_path, headless_login, None, sandbox

    def _opts(self, headless: bool) -> dict:
        o = {"headless": headless, "chromium_sandbox": self.sandbox}  # Playwright adds --no-sandbox otherwise
        return {**o, "executable_path": self.exe} if self.exe else {**o, "channel": "chrome"}

    def visible(self, profile: str):
        try:
            return self.pw.chromium.launch_persistent_context(profile, locale="tr-TR", **self._opts(self.headless_login))
        except Exception:  # noqa: BLE001 - no Google Chrome: Playwright's own Chromium
            return self.pw.chromium.launch_persistent_context(profile, locale="tr-TR", headless=self.headless_login,
                                                              chromium_sandbox=self.sandbox)

    def headless(self, state: dict):
        if self.browser is None:
            try:
                self.browser = self.pw.chromium.launch(**self._opts(True))
            except Exception:  # noqa: BLE001
                self.browser = self.pw.chromium.launch(headless=True, chromium_sandbox=self.sandbox)
        return self.browser.new_context(storage_state=state, locale="tr-TR")

    def stop(self) -> None:
        try:
            if self.browser:
                self.browser.close()
        finally:
            self.pw.stop()


# -- the kept session: cookies only, encrypted, with an expiry --------------------------------
_AAD = b"katip-tsg-session"


def _session_file() -> Path:
    from ..store import home
    return home() / "tsg" / "session.bin"


def keep_hours_default() -> float:
    import os
    try:
        return float(os.environ.get("KATIP_TSG_SESSION_HOURS", "8"))
    except ValueError:
        return 8.0


def session_save(state: dict, hours: float) -> float | None:
    """Encrypt the site's cookies with Katip's key; returns the expiry time, or None if not kept."""
    import json
    import os
    import secrets

    from ... import vault
    if hours <= 0 or vault.AESGCM is None:
        return None
    exp = time.time() + hours * 3600
    nonce = secrets.token_bytes(12)
    blob = vault.AESGCM(vault._key()).encrypt(nonce, json.dumps({"expires": exp, "state": state}).encode(), _AAD)
    f = _session_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(nonce + blob)
    tmp.replace(f)
    return exp


def session_read() -> dict | None:
    """The kept session (expired or not), or None."""
    import json

    from ... import vault
    f = _session_file()
    if not f.exists() or vault.AESGCM is None:
        return None
    raw = f.read_bytes()
    try:
        return json.loads(vault.AESGCM(vault._key()).decrypt(raw[:12], raw[12:], _AAD))
    except Exception:  # noqa: BLE001 - other key or damaged: useless, forget it
        f.unlink(missing_ok=True)
        return None


def session_delete() -> None:
    _session_file().unlink(missing_ok=True)


def _logout_proof(ctx, base: str) -> bool:
    """Log out on the site, then prove it: the search page must send us to the login page."""
    pg = ctx.new_page() if not ctx.pages else ctx.pages[0]
    pg.goto(base + "/view/menu/cikis.php", wait_until="domcontentloaded", timeout=30000)
    pg.goto(base + "/view/hizlierisim/ilangoruntuleme.php", wait_until="domcontentloaded", timeout=30000)
    return "girisyap.php" in _live_url(pg)


def logout(*, browser=None, base: str = BASE) -> dict:
    """End the kept session on the site and delete it (``katip-kalkan dd gazette-logout``)."""
    sess = session_read()
    if not sess:
        session_delete()
        return {"status": "ok", "had_session": False}
    b = browser or _Playwright()
    out = {"status": "ok", "had_session": True, "logged_out": False}
    try:
        ctx = b.headless(sess["state"])
        out["logged_out"] = _logout_proof(ctx, base)
        ctx.close()
    except Exception as e:  # noqa: BLE001
        out["error"] = repr(e)[:200]
    finally:
        session_delete()
        b.stop()
    return out


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


def _visible_login(b, base: str, login_timeout: float, poll: float, say) -> dict | None:
    """Visible window on a fresh profile; the lawyer logs in. Returns the site's cookies, or None."""
    login, search = base + "/view/hizlierisim/girisyap.php", base + "/view/hizlierisim/ilangoruntuleme.php"
    profile = tempfile.mkdtemp(prefix="katip-tsg-")
    ctx = None
    try:
        ctx = b.visible(profile)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(login, wait_until="domcontentloaded", timeout=90000)
        say("Log in with e-Devlet in the Chrome window that just opened. Katip notices the login by itself "
            f"(or press Enter here once you are in). It waits up to {int(login_timeout // 60)} min.")
        t0 = last = time.time()
        while not _logged_in(ctx, base):
            if _enter_pressed():
                pg = ctx.pages[-1]
                pg.goto(search, wait_until="domcontentloaded", timeout=90000)
                if "girisyap.php" not in _live_url(pg):
                    break
                say("  the site still shows its login page; finish the login in the Chrome window")
            if time.time() - t0 > login_timeout:
                say(f"  no login after {int(login_timeout // 60)} min; open tabs: {', '.join(_tabs(ctx)) or '-'}")
                return None
            if time.time() - last > 15:
                last = time.time()
                say(f"  waiting for the login... open tabs: {', '.join(_tabs(ctx)) or '-'}")
            _wait(ctx, poll)
        _wait(ctx, 1)
        return ctx.storage_state()
    finally:
        if ctx is not None:
            try:
                ctx.close()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(profile, ignore_errors=True)


def lookup(name: str, office: str, *, out_dir: Path, max_pages: int = 3, court: bool = False, pause: float = 6.0,
           login_timeout: float = 360, browser=None, say=print, poll: float = 3.0, base: str = BASE,
           keep_hours: float | None = None) -> tuple[list[Path], dict]:
    if len(name.strip()) < 5:
        raise ValueError("the site needs at least the first 5 letters of the name")
    keep = keep_hours_default() if keep_hours is None else keep_hours
    search = base + "/view/hizlierisim/ilangoruntuleme.php"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    info = {"target": name, "office": office, "blocked": None}
    saved: list[Path] = []
    b = browser or _Playwright()
    ctx = None
    try:
        sess = session_read()
        if sess and sess["expires"] < time.time():
            say("The saved Gazette login expired; logging it out on the site...")
            try:
                c = b.headless(sess["state"])
                _logout_proof(c, base)
                c.close()
            except Exception:  # noqa: BLE001
                pass
            session_delete()
            sess = None
        page = None
        if sess:
            ctx = b.headless(sess["state"])
            page = ctx.new_page()
            page.goto(search, wait_until="domcontentloaded", timeout=90000)
            if "girisyap.php" in _live_url(page):
                say("The site ended the saved login; please log in again.")
                ctx.close()
                ctx, page = None, None
                session_delete()
                sess = None
            else:
                info["session"] = "reused saved login"
        if page is None:
            state = _visible_login(b, base, login_timeout, poll, say)
            if state is None:
                info["blocked"] = "not logged in within the time limit"
                return saved, info
            exp = session_save(state, keep)
            info["session"] = (f"login kept until {time.strftime('%H:%M', time.localtime(exp))}" if exp
                               else "login not kept")
            ctx = b.headless(state)
            page = ctx.new_page()
            time.sleep(pause)
            page.goto(search, wait_until="domcontentloaded", timeout=90000)
            if "girisyap.php" in _live_url(page):
                info["blocked"] = "the site did not accept the login in the background window"
                return saved, info
        say("Searching the gazette in the background (a few seconds between pages)...")
        options = page.eval_on_selector_all("#SicilMudurluguId option", "os => os.map(o => o.textContent.trim())")
        label = resolve_office(office, options)
        if not label:
            info["blocked"] = f"registry office {tr_upper(office)!r} is not on the site's list"
            return saved, info
        info["office"] = label
        page.select_option("#SicilMudurluguId", label=label)
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
        if ctx is not None and keep <= 0:
            for _ in range(3):  # the login must not outlive the run when nothing is kept
                try:
                    info["logged_out"] = _logout_proof(ctx, base)
                    info.pop("logout_error", None)
                    break
                except Exception as e:  # noqa: BLE001
                    info["logout_error"] = repr(e)[:200]
                    time.sleep(1)
            session_delete()
        if ctx is not None:
            try:
                ctx.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            b.stop()
        except Exception:  # noqa: BLE001
            pass
