"""False positives on real legal text: the GDPR itself, all 99 articles in English and German.

The text has no personal data, so every masked span is a false positive. The pages are fetched from
gdpr-info.eu and dsgvo-gesetz.de into a local cache (not committed: the site's rendering, not ours) and scored
with the "ai" (KVKK only) and "eu" profiles.

  KATIP_SDK=0 python lab/eu/fp_gdpr_text.py [cache_dir]
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "connector"))
os.environ.setdefault("KATIP_HOME", tempfile.mkdtemp())
from katip_kalkan import engine, eu  # noqa: E402

URLS = {"en": "https://gdpr-info.eu/art-{i}-gdpr/", "de": "https://dsgvo-gesetz.de/art-{i}-dsgvo/"}


def article_text(page: str) -> str:
    m = re.search(r'<div class="entry-content">(.*?)</div>\s*(?:<div|<footer)', page, re.S)
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>|<sup[^>]*>.*?</sup>", "", m.group(1) if m else "", flags=re.S)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()


def main(cache=None):
    cache = Path(cache or Path(tempfile.gettempdir()) / "katip-gdpr-cache")
    cache.mkdir(parents=True, exist_ok=True)
    docs = []
    for lang, url in URLS.items():
        for i in range(1, 100):
            f = cache / f"{lang}_{i}.html"
            if not f.exists():
                req = urllib.request.Request(url.format(i=i), headers={"User-Agent": "katip-eval"})
                f.write_bytes(urllib.request.urlopen(req, timeout=30).read())
                time.sleep(0.2)
            t = article_text(f.read_text(encoding="utf-8", errors="ignore"))
            if len(t) > 200:
                docs.append((f"{lang}_{i}", t))
    total = sum(len(t) for _, t in docs)
    out = {"articles": len(docs), "chars": total, "profiles": {}}
    for prof in ("ai", "eu"):
        spans, chars, ex = 0, 0, Counter()
        for _, t in docs:
            types, addr = engine.profile_types(prof)
            sp = engine.detect(t, 0.5, types, address_detail=addr)
            if engine.PROFILES[prof].get("eu"):
                sp = eu.merge(t, sp)
            spans += len(sp)
            chars += sum(s["end"] - s["start"] for s in sp)
            ex.update(f'{s["entity_type"]}: {s["text"]}' for s in sp)
        out["profiles"][prof] = {"false_spans": spans, "chars_masked": chars,
                                 "per_10k_chars": round(1e4 * spans / total, 2), "top": ex.most_common(15)}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
