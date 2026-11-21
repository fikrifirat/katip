"""ilan.gov.tr (Basın İlan Kurumu) notices: bankruptcy, concordat, enforcement sales.

Status on 21 Nov 2026, from a cloud machine outside Türkiye:
- the site loads and robots.txt allows everything except ``/*tebligat``. We never fetch
  tebligat (service-of-process) notices, even though they are the ones that name individuals.
- the search endpoint the site itself uses (``/api/api/services/app/Ad/AdsByFilter``) answered
  our plain, honestly labelled request with HTTP 403. We do not imitate a browser to get past
  that. ``fetch`` therefore raises ``Blocked`` there, and the store keeps no ilan rows.
- the sitemaps listed in robots.txt return 404.

What would unblock it, in order of preference: a data-sharing agreement or feed from Basın
İlan Kurumu; the same request from a Turkish connection (to test whether the 403 is
geographic); notices the lawyer saves from the site, imported with ``import_saved``.
The request body below follows the site's front-end code and is untested against a 200.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ..net import Blocked
from ..normalize import fold

SOURCE = "ilan"
BASE = "https://www.ilan.gov.tr"
API = BASE + "/api/api/services/app/Ad/AdsByFilter"
# DD-relevant keywords. Tebligat is deliberately absent.
KEYWORDS = ["konkordato", "iflas", "iflasın açılması", "tasfiye", "icra satış", "alacaklılar toplantısı"]
PAGE = 50


def _doc(ad: dict) -> dict:
    title = ad.get("title") or ad.get("adTitle") or ""
    text = re.sub(r"<[^>]+>", " ", ad.get("content") or ad.get("adContent") or ad.get("description") or "")
    url = ad.get("urlStr") or ad.get("url") or ""
    if url and not url.startswith("http"):
        url = BASE + "/ilan/" + url.lstrip("/")
    rid = str(ad.get("id") or ad.get("adNo") or hashlib.sha1((title + text).encode()).hexdigest()[:12])
    return {"rid": f"ilan:{rid}", "source": SOURCE, "kind": "notice", "title": title, "names": [title],
            "text": f"{title}\n{ad.get('advertiserName', '')}\n{text}",
            "date": ad.get("publishStartDate") or ad.get("publishDate") or "", "url": url,
            "advertiser": ad.get("advertiserName", "")}


def fetch(client) -> tuple[list[dict], dict]:
    docs, detail = {}, {"keywords": {}}
    for kw in KEYWORDS:
        body = {"keys": {"q": [kw]}, "skipCount": 0, "maxResultCount": PAGE}
        r = client.post_json(API, body, headers={"Accept": "application/json"})  # raises Blocked on 403
        data = r.json()
        result = data.get("result", data)
        ads = result.get("ads") or result.get("items") or []
        detail["keywords"][kw] = {"received": len(ads), "total": result.get("numFound") or result.get("totalCount")}
        for ad in ads:
            if "tebligat" in fold(json.dumps(ad.get("categories", ""), ensure_ascii=False)):
                continue
            d = _doc(ad)
            docs[d["rid"]] = d
    if not docs:
        raise Blocked("ilan.gov.tr answered but returned no notices; response shape may have changed")
    return list(docs.values()), detail


def import_saved(paths: list[Path]) -> list[dict]:
    """Notices the lawyer saved from ilan.gov.tr as .html or .txt (one notice per file)."""
    out = []
    for p in paths:
        raw = p.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))
        out.append({"rid": f"ilan:file:{hashlib.sha1(raw.encode()).hexdigest()[:12]}", "source": SOURCE,
                    "kind": "notice", "title": p.stem, "names": [p.stem], "text": text, "date": "", "url": str(p)})
    return out
