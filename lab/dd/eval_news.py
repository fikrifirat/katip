"""News-inspired end-to-end evaluation of Katip DD on real public sources, run on your own computer.

Companies (never private individuals) reported in the Turkish press in 2025-2026 as having
applied for konkordato, plus invented decoys. For each company:

1. ilan.gov.tr: one site search for the short name (``ilan-lookup``, at most ``--ilan-ads``
   notice pages opened, 5 s apart);
2. Ticaret Sicili Gazetesi (``--gazette``): one search per company with the registry office
   taken from the case (or from the court named in its ilan.gov.tr notices), at most
   ``--gazette-pages`` pages; the lawyer logs in once, later searches reuse the login;
3. ``dd_screen`` with the short name a lawyer would type (lower case, no legal form).

Ground truth is the source text itself, not the news: a stored notice is "about" a company when
its folded text contains the company's full distinctive phrase. That lets us count, per source:

* recall: notices about the company that ``dd_screen`` returns at "review" or better;
* precision: ``dd_screen`` hits that are really about that company;
* decoys: hits for invented companies (should be none).

Only company names, notice ids/links, scores and counts go into the results file. People named
in notices are not written out.

    python lab/dd/eval_news.py --ilan                 # ilan.gov.tr part (needs Playwright)
    python lab/dd/eval_news.py --gazette              # + Gazette part (you log in once)
    python lab/dd/eval_news.py --screen-only          # only re-score what is already stored
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "connector"))

from katip_kalkan.dd import service  # noqa: E402
from katip_kalkan.dd.match import REVIEW  # noqa: E402
from katip_kalkan.dd.normalize import fold  # noqa: E402
from katip_kalkan.dd.store import Store  # noqa: E402

# query = what a lawyer types; phrase = distinctive words that must be in a notice about it;
# office = Ticaret Sicili Müdürlüğü if known ("" = take it from the court in ilan.gov.tr notices).
# Sources for the selection: Endeks24 (borsa companies with konkordato mühlet, 2026), Forbes
# Türkiye (first half 2026), CNBC-e / NTV (CBF Tekstil), Diken (Mavi Ay Yatak), Manşet Haber.
CASES = [
    {"query": "Türk İlaç", "phrase": "türk ilaç", "office": "ANKARA"},
    {"query": "Barem Ambalaj", "phrase": "barem ambalaj", "office": ""},
    {"query": "Uşak Seramik", "phrase": "uşak seramik", "office": "UŞAK"},
    {"query": "Ral Yatırım", "phrase": "ral yatırım", "office": ""},
    {"query": "Alves Kablo", "phrase": "alves kablo", "office": ""},
    {"query": "CBF Tekstil", "phrase": "cbf tekstil", "office": ""},
    {"query": "Flament Tekstil", "phrase": "flament tekstil", "office": "GAZİANTEP"},
    {"query": "Mavi Ay Yatak", "phrase": "mavi ay yatak", "office": ""},
    {"query": "Metro Trafik Ekipmanları", "phrase": "metro trafik", "office": ""},
    {"query": "Ertona Tekstil", "phrase": "ertona tekstil", "office": "BURSA"},
]
DECOYS = ["Kuzeyrüzgarı Tekstil", "Güneyrüzgarı Gıda", "Batırüzgarı Lojistik", "Mavişafak Seramik",
          "Turna Ambalaj Plastik", "Ceylanpınarı Kablo"]

_COURT = re.compile(r"T\.?\s?C\.?\s+([A-ZÇĞİIÖŞÜ]{3,})\s+(?:\d+\.\s*)?(?:ASL[İI]YE\s+T[İI]CARET|[İI]CRA|[İI]FLAS)", re.I)


def about(doc: dict, phrase: str) -> bool:
    return fold(phrase) in fold(" ".join([doc.get("title", ""), doc.get("text", "")]))


def office_from_ilan(st: Store, phrase: str) -> str:
    for d in st.records("ilan"):
        if about(d, phrase):
            m = _COURT.search(d.get("text", ""))
            if m:
                return m.group(1).upper()
    return ""


def score(st: Store) -> dict:
    out = {"cases": [], "decoys": []}
    docs = {s: st.records(s) for s in ("ilan", "gazette")}
    for c in CASES:
        row = {"query": c["query"], "phrase": c["phrase"]}
        res = service.screen(c["query"], sources=["ilan", "gazette"], limit=50, store=st)
        hit_ids = {h["record_id"] for h in res["hits"] if h["score"] >= REVIEW}
        for s in ("ilan", "gazette"):
            truth = {d["rid"] for d in docs[s] if about(d, c["phrase"])}
            got = {r for r in hit_ids if r.split(":", 1)[0] == s}
            row[s] = {"notices_about_it": len(truth), "found": len(truth & got), "hits": len(got),
                      "wrong_hits": sorted(got - truth),
                      "missed": sorted(truth - got),
                      "best": max([h["score"] for h in res["hits"] if h["source"] == s] or [0])}
        out["cases"].append(row)
    for name in DECOYS:
        res = service.screen(name, sources=["masak", "ilan", "gazette"], limit=20, store=st)
        out["decoys"].append({"query": name, "hits": [{"record_id": h["record_id"], "score": h["score"], "band": h["band"]}
                                                      for h in res["hits"]]})
    tot = lambda s, k: sum(r[s][k] for r in out["cases"])  # noqa: E731
    out["summary"] = {s: {"notices_about_targets": tot(s, "notices_about_it"), "found": tot(s, "found"),
                          "hits": tot(s, "hits"), "wrong_hits": sum(len(r[s]["wrong_hits"]) for r in out["cases"]),
                          "recall": round(tot(s, "found") / tot(s, "notices_about_it"), 3) if tot(s, "notices_about_it") else None,
                          "precision": round(tot(s, "found") / tot(s, "hits"), 3) if tot(s, "hits") else None}
                      for s in ("ilan", "gazette")}
    out["summary"]["decoy_hits"] = sum(len(d["hits"]) for d in out["decoys"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ilan", action="store_true")
    ap.add_argument("--gazette", action="store_true")
    ap.add_argument("--screen-only", action="store_true")
    ap.add_argument("--resume", action="store_true", help="skip ilan.gov.tr searches that already succeeded")
    ap.add_argument("--ilan-ads", type=int, default=5)
    ap.add_argument("--gazette-pages", type=int, default=2)
    ap.add_argument("--out", default=str(Path(__file__).with_name("results") / "eval_news.json"))
    a = ap.parse_args()
    st = Store()
    log = {"ilan": [], "gazette": []}
    if a.ilan and not a.screen_only:
        done = {x["query"] for x in json.loads(Path(a.out).read_text()).get("fetch_log", {}).get("ilan", [])
                if x.get("status") == "ok"} if a.resume and Path(a.out).exists() else set()
        for c in CASES:
            if c["query"] in done:
                continue
            print(f"ilan.gov.tr: {c['query']}", flush=True)
            try:
                r = service.ilan_lookup(c["query"], max_ads=a.ilan_ads, store=st)
            except Exception as e:  # noqa: BLE001 - one company failing must not lose the others
                r = {"status": "error", "error": repr(e)[:200]}
            log["ilan"].append({"query": c["query"], **{k: r.get(k) for k in ("status", "results_on_site", "kept",
                                                                             "opened_full_text", "error")}})
            time.sleep(5)
    if a.gazette and not a.screen_only:
        for c in CASES:
            office = c["office"] or office_from_ilan(st, c["phrase"])
            if not office:
                log["gazette"].append({"query": c["query"], "status": "skipped", "why": "registry office unknown"})
                continue
            stop = next((x["blocked"] for x in log["gazette"] if x.get("blocked") in
                         ("not logged in within the time limit", "security code asked")), None)
            if stop:  # never retry past a captcha or a missed login: stop the run
                log["gazette"].append({"query": c["query"], "status": "skipped", "why": stop})
                continue
            print(f"Gazette: {c['query']} ({office})", flush=True)
            try:
                r = service.gazette_lookup(c["query"], office, max_pages=a.gazette_pages, store=st)
            except Exception as e:  # noqa: BLE001
                r = {"status": "error", "error": repr(e)[:200]}
            log["gazette"].append({"query": c["query"], "office": office,
                                   **{k: r.get(k) for k in ("status", "results_on_site", "saved_pages", "notices",
                                                            "login", "blocked", "error")}})
    res = score(st)
    res["fetch_log"] = log
    res["run_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({"summary": res["summary"], "fetch_log": log}, ensure_ascii=False, indent=1))
    for r in res["cases"]:
        print(f"{r['query']:28} ilan {r['ilan']['found']}/{r['ilan']['notices_about_it']} (hits {r['ilan']['hits']})"
              f"  gazette {r['gazette']['found']}/{r['gazette']['notices_about_it']} (hits {r['gazette']['hits']})")


if __name__ == "__main__":
    main()
