"""Katip DD: screen a person or company against Turkish public lists, on this computer.

    python lab/dd/dd.py update                 # fetch all sources that work (polite, rate limited)
    python lab/dd/dd.py update --source masak
    python lab/dd/dd.py search "Abdi Yıldırım" [--birth 1978] [--id 12345678901] [--json]
    python lab/dd/dd.py status                 # what is in the store, how fresh, what failed
    python lab/dd/dd.py check-masak            # coverage: JSON endpoint vs the CSV files
    python lab/dd/dd.py add-gazette ~/Documents/katip/tsg [--ocr]   # Gazete PDFs you saved (files or a folder)
    python lab/dd/dd.py ilan-lookup "ACME İnşaat A.Ş." [--headed] # ilan.gov.tr in a real browser, one target

Data is stored in ~/.katip/dd (KATIP_DD_HOME). Searches never leave the computer.
A result is a lead for a lawyer to check against the linked official source, not a finding.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from match import REVIEW, ListIndex, TextIndex  # noqa: E402
from net import Blocked, PoliteClient  # noqa: E402
from sources import gazette, ilan, masak  # noqa: E402
from store import Store, now  # noqa: E402

FETCHERS = {"masak": masak.fetch, "ilan": ilan.fetch}
TEXT_SOURCES = ("ilan", "gazette")


def cmd_update(a):
    st, client = Store(), PoliteClient(min_interval=a.interval)
    for name in ([a.source] if a.source else FETCHERS):
        started = now()
        try:
            records, detail = FETCHERS[name](client)
            stats = st.replace_source(name, records, detail, started)
            print(f"{name}: {stats['n']} records (+{stats['added']} / -{stats['removed']} since last run)")
        except Blocked as e:
            st.log_failure(name, started, "blocked", {"error": str(e), "log": client.log[-5:]})
            print(f"{name}: BLOCKED, {e}. Nothing was changed for this source.")
        except Exception as e:
            st.log_failure(name, started, "error", {"error": repr(e)[:500], "log": client.log[-5:]})
            print(f"{name}: ERROR, {e!r}")


def run_search(st: Store, query: str, birth: str = "", id_no: str = "", limit: int = 10, floor: float = REVIEW):
    out = []
    lists = st.records("masak")
    if lists:
        out += [("masak", h) for h in ListIndex(lists).search(query, birth=birth, id_no=id_no, limit=limit, floor=floor)]
    for src in TEXT_SOURCES:
        docs = st.records(src)
        if docs:
            out += [(src, h) for h in TextIndex(docs).search(query, limit=limit, floor=max(floor, REVIEW))]
    return sorted(out, key=lambda x: -x[1].score)


def cmd_search(a):
    st = Store()
    hits = run_search(st, a.query, a.birth, a.id, a.limit, 0.75 if a.all else REVIEW)
    fresh = {s: (st.last_ok(s) or {}).get("finished") for s in ("masak", *TEXT_SOURCES)}
    if a.json:
        print(json.dumps({
            "query": a.query, "checked_at": now(), "sources_as_of": fresh,
            "hits": [{"source": s, "score": h.score, "band": h.band, "matched": h.matched, "reasons": h.reasons,
                      **{k: v for k, v in h.record.items() if k != "raw"}} for s, h in hits],
        }, ensure_ascii=False, indent=1))
        return
    print(f"Query: {a.query}   checked {now()}")
    for s, f in fresh.items():
        print(f"  {s:8s} data as of {f or 'never fetched'}")
    if not hits:
        print("\nNo candidates above the review threshold.")
        print("This means no listed name came close in the sources above, as of the dates shown. It is not a clearance.")
        return
    for s, h in hits:
        r = h.record
        print(f"\n[{h.band.upper():6s} {h.score:.2f}] {s} / {r.get('list', r.get('kind', ''))}")
        print(f"  listed as : {r.get('names', [r.get('title', '')])[0]}")
        if h.matched and h.matched != r.get("names", [""])[0]:
            print(f"  matched on: {h.matched}")
        for k in ("birth", "nationality", "organisation", "decision", "date"):
            if r.get(k):
                print(f"  {k:10s}: {' '.join(str(r[k]).split())}")
        for x in h.reasons:
            print(f"  note      : {x}")
        if r.get("csv_only"):
            print("  note      : only in the CSV file, not in MASAK's search data; check the file")
        print(f"  source    : {r.get('url', '')}")
        if r.get("gazette_url"):
            print(f"  gazette   : {r['gazette_url']}")


def cmd_status(a):
    st = Store()
    print(f"store: {st.path}")
    for s in ("masak", *TEXT_SOURCES):
        last = st.last_ok(s)
        n = len(st.records(s))
        if last:
            age = datetime.now(timezone.utc) - datetime.strptime(last["finished"], "%Y-%m-%dT%H:%M:%S%z")
            print(f"{s:8s} {n:6d} records, fetched {last['finished']} ({age.days} d ago)")
            d = json.loads(last["detail"] or "{}")
            for lab, info in (d.get("lists") or {}).items():
                print(f"   {lab:16s} reported {info.get('reported')} received {info.get('received')}"
                      f"  page changed {info.get('page_modified', '-')}  newest decision {info.get('newest_decision', '-')}")
        else:
            print(f"{s:8s} {n:6d} records, never fetched successfully")
    print("\nlast runs:")
    for r in st.runs(8):
        print(f"  {r['finished']}  {r['source']:8s} {r['status']:8s} n={r['n']}  {json.loads(r['detail'] or '{}').get('error', '')[:120]}")


def cmd_check_masak(a):
    st, client = Store(), PoliteClient(min_interval=a.interval)
    last = st.last_ok("masak")
    if not last:
        sys.exit("run `dd.py update --source masak` first")
    print(json.dumps(masak.crosscheck(client, st.records("masak"), json.loads(last["detail"])), ensure_ascii=False, indent=1))


def _merge(st: Store, source: str, new: list[dict], detail: dict, started: str) -> dict:
    keep = {d["rid"]: d for d in st.records(source)}
    keep.update({d["rid"]: d for d in new})
    return st.replace_source(source, list(keep.values()), detail, started)


def cmd_ilan_lookup(a):
    """Look up one DD target on ilan.gov.tr in a real browser on this computer, then search."""
    from sources import ilan_browser

    st, started = Store(), now()
    try:
        docs, info = ilan_browser.search(a.target, max_ads=a.max_ads, headed=a.headed)
    except ImportError:
        sys.exit("Playwright is missing: pip install playwright  (and Google Chrome, or: python -m playwright install chromium)")
    if info.get("blocked"):
        st.log_failure("ilan", started, "blocked", info)
        print(f"ilan: stopped, {info['blocked']}")
        return
    stats = _merge(st, "ilan", docs, info, started)
    print(f"ilan: {info.get('ads_in_results')} results for the target, kept {len(docs)} "
          f"(tebligat dropped), opened {info.get('opened')} notice pages; store now {stats['n']}")
    a.query, a.birth, a.id, a.limit, a.json, a.all = a.target, "", "", 10, False, False
    cmd_search(a)


def cmd_add_gazette(a):
    st = Store()
    started = now()
    paths = []
    for p in map(Path, a.pdfs):
        paths += sorted(p.glob("*.pdf")) if p.is_dir() else [p]
    docs = st.records("gazette")
    new = gazette.ingest(paths, ocr=a.ocr)
    keep = {d["rid"]: d for d in docs}
    keep.update({d["rid"]: d for d in new})
    stats = st.replace_source("gazette", list(keep.values()), {"files": [str(p) for p in a.pdfs]}, started)
    print(f"gazette: {len(new)} notices from {len(paths)} file(s); store now {stats['n']}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("update"); u.add_argument("--source", choices=list(FETCHERS)); u.add_argument("--interval", type=float, default=2.0)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--birth", default=""); s.add_argument("--id", default="")
    s.add_argument("--limit", type=int, default=10); s.add_argument("--all", action="store_true", help="also show weak candidates"); s.add_argument("--json", action="store_true")
    sub.add_parser("status")
    c = sub.add_parser("check-masak"); c.add_argument("--interval", type=float, default=2.0)
    g = sub.add_parser("add-gazette", help="PDF files or a folder of them"); g.add_argument("pdfs", nargs="+"); g.add_argument("--ocr", action="store_true")
    il = sub.add_parser("ilan-lookup", help="one DD target on ilan.gov.tr, in a real browser on this computer")
    il.add_argument("target"); il.add_argument("--headed", action="store_true"); il.add_argument("--max-ads", type=int, default=20)
    a = p.parse_args(argv)
    {"update": cmd_update, "search": cmd_search, "status": cmd_status,
     "check-masak": cmd_check_masak, "add-gazette": cmd_add_gazette, "ilan-lookup": cmd_ilan_lookup}[a.cmd](a)


if __name__ == "__main__":
    main()
