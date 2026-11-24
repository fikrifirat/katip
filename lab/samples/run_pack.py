"""Run the Katip sample pack against the current code and write results/pack_results.json + results/SCORES.md.

Three parts, all offline except the DD part, which needs a local MASAK snapshot (`python lab/dd/dd.py update`):

  eu    16 cross-border documents (data/eu_docs.jsonl): masking recall per value, strings kept readable,
        documents masked in full. Profiles: ai (Turkish rules), eu (ai + eu.py).
  dd    screening queries (data/dd_cases.json): what a lawyer types for a listed company or organisation,
        decoys that must not match, and Gazette/ilan notice texts (data/notices.json) for the free-text index.
  uyum  questionnaire changes modelled on real enforcement decisions (data/uyum_cases.json): the finding
        Katip Uyum must raise, and what the regulator found that a questionnaire cannot show.

    KATIP_SDK=0 python lab/samples/run_pack.py [--part eu|dd|uyum] [--no-dd]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "connector"))
sys.path.insert(0, str(ROOT / "lab" / "uyum"))
os.environ.setdefault("KATIP_HOME", tempfile.mkdtemp())


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


def pct(k, n):
    return round(100 * k / n, 1) if n else None


# ------------------------------------------------------------------------------------------------ eu
def run_eu(name="eu_docs.jsonl"):
    from katip_kalkan import engine, eu

    def spans(text, profile):
        types, addr = engine.profile_types(profile)
        sp = engine.detect(text, 0.5, types, address_detail=addr)
        if engine.PROFILES[profile].get("eu"):
            sp = eu.merge(text, sp)
        return sp

    def covered(sp, g):
        cov = set()
        for s in sp:
            cov.update(range(max(s["start"], g["start"]), min(s["end"], g["end"])))
        return set(range(g["start"], g["end"])) <= cov

    docs = [json.loads(x) for x in (HERE / "data" / name).read_text(encoding="utf-8").splitlines() if x.strip()]
    out = {"docs": len(docs), "values": sum(len(d["gold"]) for d in docs), "profiles": {}}
    for profile in ("ai", "eu"):
        by_type, by_doc, misses, keep, over, extra = defaultdict(lambda: [0, 0]), [], [], [0, 0], [], []
        name_split = {"listed": [0, 0], "not_listed": [0, 0]}
        for d in docs:
            sp = spans(d["text"], profile)
            ok_doc = True
            caught = 0
            for g in d["gold"]:
                hit = covered(sp, g)
                by_type[g["type"]][1] += 1
                by_type[g["type"]][0] += hit
                caught += hit
                if g["type"] == "PERSON":
                    first = g["text"].split()[0].strip(".,")
                    key = "listed" if first in eu.FIRST_NAMES else "not_listed"
                    name_split[key][1] += 1
                    name_split[key][0] += hit
                if not hit:
                    ok_doc = False
                    misses.append({"doc": d["id"], "type": g["type"], "text": g["text"]})
            for sp_ in sp:  # masked spans that touch no gold value: over-masking beyond the keep list
                if not any(sp_["start"] < g["end"] and g["start"] < sp_["end"] for g in d["gold"]):
                    extra.append({"doc": d["id"], "type": sp_.get("entity_type"), "text": d["text"][sp_["start"]:sp_["end"]]})
            kept_doc = 0
            for k in d["keep"]:
                i = d["text"].find(k)
                hit = any(s["start"] < i + len(k) and s["end"] > i for s in sp)
                keep[1] += 1
                keep[0] += not hit
                kept_doc += not hit
                if hit:
                    over.append({"doc": d["id"], "kept_string": k,
                                 "masked": [d["text"][s["start"]:s["end"]] for s in sp if s["start"] < i + len(k) and s["end"] > i]})
            by_doc.append({"doc": d["id"], "case": d.get("case", d["id"]), "title": d.get("title", ""), "caught": caught, "of": len(d["gold"]),
                           "clean": ok_doc, "kept": kept_doc, "keep_of": len(d["keep"])})
        k = sum(v[0] for v in by_type.values())
        n = sum(v[1] for v in by_type.values())
        out["profiles"][profile] = {
            "recall": pct(k, n), "ci95": wilson(k, n), "caught": k, "of": n,
            "by_type": {t: {"caught": v[0], "of": v[1], "recall": pct(*v)} for t, v in sorted(by_type.items())},
            "names_first_name_listed": {kk: {"caught": v[0], "of": v[1], "recall": pct(*v)} for kk, v in name_split.items()},
            "docs_fully_masked": sum(r["clean"] for r in by_doc),
            "keep_readable": {"kept": keep[0], "of": keep[1]},
            "by_doc": by_doc, "misses": misses, "over_masked": over,
            "spans_without_gold": len(extra), "spans_without_gold_list": extra}
    return out


# ------------------------------------------------------------------------------------------------ dd
def run_dd():
    from katip_kalkan.dd.match import MATCH, REVIEW, ListIndex, TextIndex
    from katip_kalkan.dd.store import Store

    cases = json.loads((HERE / "data" / "dd_cases.json").read_text(encoding="utf-8"))
    st = Store()
    recs = st.records("masak")
    if not recs:
        return {"skipped": "no local MASAK snapshot: run `python lab/dd/dd.py update` first"}
    ix = ListIndex(recs)
    asof = (st.last_ok("masak") or {}).get("finished")
    rows = []
    for c in cases["list_queries"]:
        hits = ix.search(c["query"], limit=5, floor=0.75)
        top = hits[0] if hits else None
        right = None
        if c.get("expect_listed"):
            for h in hits:
                if any(c["expect_listed"].lower() in n.lower() for n in h.record.get("names", [])):
                    right = h
                    break
        got = right.band if right else "none"
        if c["expect"] == "report":
            got = top.band if top else "none"
            ok = None
        elif c["expect"] in ("none", "no_match"):
            got = top.band if top else "none"
            ok = got in (("none", "weak") if c["expect"] == "none" else ("none", "weak", "review"))
        else:
            ok = got in ({"match"} if c["expect"] == "match" else {"match", "review"})
        rows.append({"id": c["id"], "group": c["group"], "query": c["query"], "expect": c["expect"], "got": got,
                     "score": round((right or top).score, 3) if (right or top) else None,
                     # a listed person's name is never written to the results (list data stays local)
                     "top_listed_name": ((top.record.get("names") or [""])[0] if top.record.get("kind") != "person"
                                         else f"[listed person, {top.record.get('list')}]") if top and not right else None,
                     "ok": ok, "why": c["why"]})
    notices = json.loads((HERE / "data" / "notices.json").read_text(encoding="utf-8"))
    tix = TextIndex([{"rid": n["id"], "text": n["text"]} for n in notices["notices"]])
    nrows = []
    for q in notices["queries"]:
        hits = {h.record["rid"]: h for h in tix.search(q["query"], limit=20, floor=REVIEW)}
        exp = set(q["expect_in"])
        found = {rid for rid, h in hits.items()}
        nrows.append({"id": q["id"], "query": q["query"], "expect_in": sorted(exp), "found": sorted(found),
                      "missed": sorted(exp - found), "extra": sorted(found - exp),
                      "bands": {rid: h.band for rid, h in hits.items()}, "ok": exp == found, "why": q["why"]})
    groups = defaultdict(lambda: [0, 0, []])
    for r in rows:
        if r["ok"] is None:
            groups[r["group"]][2] = groups[r["group"]][2] + [r["got"]]
            continue
        groups[r["group"]][1] += 1
        groups[r["group"]][0] += r["ok"]
    from katip_kalkan.dd.service import HOW_TO_READ
    return {"masak_as_of": asof, "how_to_read_names_other_lists": any(w in HOW_TO_READ for w in ("OFAC", "EU list", "UK")), "masak_rows": len(recs), "thresholds": {"match": MATCH, "review": REVIEW},
            "list_queries": rows, "by_group": {g: ({"ok": v[0], "of": v[1]} if v[1] else {"bands": {b: v[2].count(b) for b in sorted(set(v[2]))}})
                                for g, v in groups.items()},
            "notice_queries": nrows, "notices_ok": sum(r["ok"] for r in nrows), "notices_of": len(nrows)}


# ------------------------------------------------------------------------------------------------ uyum
def run_uyum():
    from katip_uyum.rules import analyse  # noqa: F401  (import check)
    sys.path.insert(0, str(ROOT / "lab" / "uyum" / "eval"))
    import eval_uyum as ev

    cases = json.loads((HERE / "data" / "uyum_cases.json").read_text(encoding="utf-8"))
    rows = []
    for c in cases:
        q = ev.apply_patch(copy.deepcopy(ev.EXAMPLE), c.get("patch", {}))
        an = analyse(q)
        got = {f.id: f.severity for f in an.findings}
        missed = [e for e in c["expect"] if not ev._match(e, got)]
        alarms = [f for f in c.get("forbid", []) if ev._match(f, got)]
        rows.append({"id": c["id"], "source": c["source"], "regulator_found": c["regulator_found"],
                     "expect": c["expect"], "missed": missed, "false_alarms": alarms,
                     "ok": not missed and not alarms, "beyond_questionnaire": c.get("beyond_questionnaire", "")})
    return {"cases": rows, "ok": sum(r["ok"] for r in rows), "of": len(rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["eu", "heldout", "dd", "uyum"])
    ap.add_argument("--no-dd", action="store_true")
    ap.add_argument("--out", default=str(HERE / "results" / "pack_results.json"))
    a = ap.parse_args()
    parts = [a.part] if a.part else [p for p in ("eu", "heldout", "dd", "uyum") if not (p == "dd" and a.no_dd)]
    res = {}
    for p in parts:
        res[p] = {"eu": run_eu, "heldout": lambda: run_eu("eu_heldout.jsonl"), "dd": run_dd, "uyum": run_uyum}[p]()
    old = json.loads(Path(a.out).read_text(encoding="utf-8")) if Path(a.out).exists() else {}
    old.update(res)
    Path(a.out).write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    for part in ("eu", "heldout"):
        if part not in res:
            continue
        for prof, v in res[part]["profiles"].items():
            print(f"{part}/{prof}: {v['recall']}% {v['ci95']} ({v['caught']}/{v['of']}), docs clean {v['docs_fully_masked']}/{res[part]['docs']}, "
                  f"kept {v['keep_readable']['kept']}/{v['keep_readable']['of']}, masked spans with no gold value {v['spans_without_gold']}")
            print("   ", {t: f"{x['caught']}/{x['of']}" for t, x in v["by_type"].items()}, v["names_first_name_listed"])
    if "dd" in res and "skipped" not in res["dd"]:
        print("dd:", res["dd"]["by_group"], f"notices {res['dd']['notices_ok']}/{res['dd']['notices_of']}")
    if "uyum" in res:
        print(f"uyum: {res['uyum']['ok']}/{res['uyum']['of']}")


if __name__ == "__main__":
    main()
