"""ilan.gov.tr through a real browser on the lawyer's own computer.

Why a browser: the site's API refuses plain clients (HTTP 403 from the site's own server),
and our cloud machine cannot open the site at all. A person can search it in a browser,
so we do exactly that: open the site, type the DD target's name into the site's own
search box, and keep the notices the page itself loads. Nothing is forged, no captcha is
solved, and the pace is human (several seconds between pages).

Rules this module keeps:
- one named DD target per run, never bulk harvesting;
- at most ``max_ads`` notice pages opened per run (default 20);
- robots.txt disallows ``/*tebligat``: those pages are never opened and their search
  results are dropped;
- if a captcha, login wall or block page appears, the run stops and says so.

Needs Playwright: ``pip install playwright`` and either Google Chrome installed or
``python -m playwright install chromium``.
"""
from __future__ import annotations

import json
import re
import time

from ..normalize import fold

BASE = "https://www.ilan.gov.tr"
SEARCH_BOX = ["input[type=search]", "input[placeholder*='Ara']", "input[placeholder*='ara']",
              "input[name*='search']", "input[formcontrolname]"]
STOP_WORDS = ["captcha", "robot olmadığınızı", "erişim engellendi", "access denied", "request blocked"]


def _launch(p, headed: bool):
    try:
        return p.chromium.launch(channel="chrome", headless=not headed)
    except Exception:
        return p.chromium.launch(headless=not headed)


def _ad_to_doc(ad: dict, detail: dict | None) -> dict:
    d = detail or {}
    title = d.get("title") or ad.get("title") or ad.get("adTitle") or ""
    content = d.get("content") or ad.get("content") or ad.get("description") or ""
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(content)))
    url = ad.get("urlStr") or ad.get("url") or d.get("urlStr") or ""
    if url and not url.startswith("http"):
        url = BASE + "/" + url.lstrip("/")
    rid = str(ad.get("id") or d.get("id") or abs(hash(title + text)))
    return {"rid": f"ilan:{rid}", "source": "ilan", "kind": "notice", "title": title, "names": [title],
            "text": f"{title}\n{ad.get('advertiserName', d.get('advertiserName', ''))}\n{text}",
            "date": ad.get("publishStartDate") or d.get("publishStartDate") or "", "url": url,
            "category": ad.get("categoryName") or d.get("categoryName") or "", "raw_keys": sorted(ad)[:40],
            "full_text": bool(detail)}


def search(target: str, *, max_ads: int = 20, pause: float = 5.0, headed: bool = False) -> tuple[list[dict], dict]:
    from playwright.sync_api import sync_playwright

    lists, details, log = [], {}, []

    def on_response(r):
        u = r.url
        if "/api/" not in u:
            return
        log.append({"status": r.status, "url": u.split("?")[0][-80:]})
        try:
            if "AdsByFilter" in u and r.status == 200:
                lists.append(r.json())
            elif "GetAdDetail" in u and r.status == 200:
                j = r.json()
                res = j.get("result", j)
                details[str(res.get("id", len(details)))] = res
        except Exception:
            pass

    info = {"target": target, "blocked": None}
    with sync_playwright() as p:
        b = _launch(p, headed)
        page = b.new_page(locale="tr-TR")
        page.on("response", on_response)
        page.goto(BASE + "/", wait_until="networkidle", timeout=90000)
        time.sleep(pause)
        body = fold(page.inner_text("body"))
        if any(fold(w) in body for w in STOP_WORDS):
            info["blocked"] = "block or captcha page on the home page"
            b.close()
            return [], {**info, "log": log}
        box = None
        for sel in SEARCH_BOX:
            if page.locator(sel).count():
                box = page.locator(sel).first
                break
        if box is None:
            info["blocked"] = "search box not found; the site layout changed"
            b.close()
            return [], {**info, "log": log}
        box.click()
        box.type(target, delay=120)  # typed, not injected
        box.press("Enter")
        page.wait_for_load_state("networkidle", timeout=90000)
        time.sleep(pause)
        info["results_url"] = page.url
        # collect ads from the page's own search responses
        ads = []
        for j in lists:
            res = j.get("result", j)
            ads += res.get("ads") or res.get("items") or []
        info["ads_in_results"] = len(ads)
        opened = 0
        for ad in ads:
            url = ad.get("urlStr") or ad.get("url") or ""
            if "tebligat" in url.lower() or "tebligat" in fold(str(ad.get("categoryName", ""))):
                continue
            if opened >= max_ads or not url:
                continue
            page.goto(url if url.startswith("http") else BASE + "/" + url.lstrip("/"), wait_until="networkidle", timeout=90000)
            opened += 1
            time.sleep(pause)
        info["opened"] = opened
        b.close()
    by_id = {str(d.get("id")): d for d in details.values()}
    docs = []
    for ad in ads:
        url = (ad.get("urlStr") or ad.get("url") or "").lower()
        if "tebligat" in url or "tebligat" in fold(str(ad.get("categoryName", ""))):
            continue
        docs.append(_ad_to_doc(ad, by_id.get(str(ad.get("id")))))
    info["kept"] = len(docs)
    info["log"] = log[-40:]
    return docs, info
