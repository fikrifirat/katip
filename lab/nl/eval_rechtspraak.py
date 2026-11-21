"""False-positive check on real Dutch court text.

Published decisions on rechtspraak.nl are pseudonymised by the courts ([eiser], [adres], [geboortedatum]),
while judges', clerks' and lawyers' names, court addresses and P.O. boxes stay in. So on this text:
  - every PERSON hit should be a professional's real name (a true name, which the "keep professionals"
    option will later leave readable),
  - every other hit is either an organisation's address or a false positive worth fixing.
Prints counts per type and examples with context. Only ECLI numbers and a date filter are sent.

  python lab/nl/eval_rechtspraak.py --n 60 --since 2026-09-01
"""
from __future__ import annotations

import argparse
import collections
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from katip_nl.recognizers import detect  # noqa: E402

CACHE = Path.home() / ".cache" / "katip-nl" / "rechtspraak-xml"
UA = "katip-nl/0.1 (+https://github.com/fikrifirat/katip)"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        return r.read().decode("utf-8")


def decisions(n, since):
    CACHE.mkdir(parents=True, exist_ok=True)
    feed = get(f"https://data.rechtspraak.nl/uitspraken/zoeken?max={n}&return=DOC&type=Uitspraak&date={since}")
    for ecli in re.findall(r"<id>(ECLI:[^<]+)</id>", feed):
        f = CACHE / (ecli.replace(":", "_") + ".xml")
        if not f.exists():
            f.write_text(get(f"https://data.rechtspraak.nl/uitspraken/content?id={ecli}"), encoding="utf-8")
            time.sleep(0.5)
        x = f.read_text(encoding="utf-8")
        i = x.find("<uitspraak")
        if i >= 0:
            t = html.unescape(re.sub(r"<[^>]+>", "\n", x[i:]))
            yield ecli, re.sub(r"\n\s*\n+", "\n", t)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=60)
    p.add_argument("--since", default="2026-09-01")
    p.add_argument("--examples", type=int, default=12)
    a = p.parse_args()
    cnt, ex, words, docs = collections.Counter(), collections.defaultdict(list), 0, 0
    for ecli, t in decisions(a.n, a.since):
        docs += 1
        words += len(t.split())
        for s in detect(t):
            cnt[s["entity_type"]] += 1
            ex[s["entity_type"]].append((s["text"], t[max(0, s["start"] - 45):s["end"] + 20].replace("\n", " "), ecli))
    print(f"{docs} decisions, {words:,} words")
    for k, n in cnt.most_common():
        print(f"\n== {k}: {n} ({n / words * 1000:.2f} per 1,000 words)")
        for v, ctx, e in ex[k][:a.examples]:
            print(f"   {v!r:40} | {ctx}")


if __name__ == "__main__":
    main()
