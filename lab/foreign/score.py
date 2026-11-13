"""Score detectors on the foreign-client sets (lab/foreign/build.py). No training.

  python lab/foreign/score.py                              # Rules and the published Katip Tiny
  python lab/foreign/score.py runs/tiny_r:0.5 runs/tiny_f:0.5 ml/berturk/out:0.5   # plus model folders (:trust)
  python lab/foreign/score.py --tag before                 # results file suffix (lab/results/foreign_<tag>.json)

Model folders given on the command line are compared in pairs, in order (1st vs 2nd, 3rd vs 4th ...): paired
document bootstrap and McNemar on the same foreign-name slots. Put the control first, the new model second.

What is measured
  Foreign names    recall on court-foreign (real Yargıtay prose, held-out foreign names), by origin group, with a
                   document-level bootstrap 95% CI; the same slots with unseen Turkish names (court-turkish) as the
                   reference, and a McNemar test on the paired slots.
  Foreign IDs      on petition-foreign: share of YKN / passport / home-country ID numbers left readable (masked
                   under any label counts as masked), and share masked under the right label.
  False alarms     false names and false IDs per 1,000 words on negatives-foreign (Hakim, Emir, Halep, Tahran,
                   UYAP file numbers ...) and on Katip's own name-free legal prose (negatives).
"""
from __future__ import annotations

import json, math, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import katiplab as K  # noqa: E402
import build as B  # noqa: E402

ID_TYPES = ("YKN", "PASSPORT", "FOREIGN_ID")

def detectors(argv):
    out = [("Rules", K.rules())]
    tg = K.Tagger(K.TINY); out.append(("Katip Tiny v1 (published)", K.pipeline(tg)))
    for a in argv:
        d, _, t = a.partition(":"); d = Path(d)
        if not (d / "config.json").exists(): print("skip", d); continue
        tg = K.Tagger(d); out.append((f"{d.name} @ {t or 'default'}", K.pipeline(tg, trust=float(t) if t else None)))
    return out

def _doc(i): return i.split("#")[0]

def names_rows(docs, det, foreign_only=False):
    gold, spans, _ = K.score(docs, det)
    for r in gold + spans: r["doc"] = _doc(r["doc"])
    if foreign_only: gold = [r for r in gold if r["text"] not in B.TR_LAWYERS]
    return gold, spans

def group_of_rows(docs):
    """Origin group of each gold PERSON span, in K.score's order."""
    return [g for d in docs for (a, b, t), g in zip(d["spans"], d["span_groups"]) if t == "PERSON"]

def ids_score(docs, det):
    n = defaultdict(lambda: [0, 0, 0])   # type -> [gold, masked any label, masked right label]
    for d in docs:
        text = d["text"]; found = det(text)
        for a, b, t in d["spans"]:
            if t not in ID_TYPES: continue
            n[t][0] += 1
            cov = [(s, e, ft) for s, e, ft in found if s <= a + 1 and e >= b - 1]
            n[t][1] += bool(cov); n[t][2] += any(ft == t for *_, ft in cov)
    return {t: {"gold": g, "masked": m / g, "right_label": r / g} for t, (g, m, r) in sorted(n.items())}

def false_alarms(docs, det):
    words = sum(len(d["text"].split()) for d in docs); fp = defaultdict(list)
    for d in docs:
        for s, e, t in det(d["text"]):
            if t in ("PERSON",) + ID_TYPES + ("TCKN",): fp[t].append(d["text"][s:e])
    return {"words": words, **{t: {"per_1k_words": 1000 * len(v) / words, "n": len(v), "examples": sorted(set(v))[:25]} for t, v in fp.items()}}

def mcnemar(a, b):
    only_b = sum(y and not x for x, y in zip(a, b)); only_a = sum(x and not y for x, y in zip(a, b)); n = only_a + only_b
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(only_a, only_b) + 1)) / 2 ** n) if n else 1.0
    return {"only_turkish_found": only_a, "only_foreign_found": only_b, "p": p}

def main(argv):
    tag = "baseline"
    if "--tag" in argv: i = argv.index("--tag"); tag = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    S = B.get(); neg = K.load_synth("negatives")
    res, rows = {}, {}
    for name, det in detectors(argv):
        r = {}
        gf, sf = names_rows(S["court-foreign"], det); gt, st = names_rows(S["court-turkish"], det)
        r["court-foreign"] = {**K.summary(gf, sf), **K.bootstrap_ci(gf, sf)}
        r["court-turkish"] = {**K.summary(gt, st), **K.bootstrap_ci(gt, st)}
        r["foreign_vs_turkish"] = mcnemar([x["found"] for x in gt], [x["found"] for x in gf])
        groups = group_of_rows(S["court-foreign"]); by = defaultdict(lambda: [0, 0])
        for g, row in zip(groups, gf): by[g][0] += 1; by[g][1] += row["found"]
        r["by_group"] = {g: {"gold": n, "recall": f / n} for g, (n, f) in sorted(by.items())}
        gp, spp = names_rows(S["petition-foreign"], det, foreign_only=True)
        r["petition-foreign names"] = {**K.summary(gp, spp), **K.bootstrap_ci(gp, spp)}
        r["petition-foreign ids"] = ids_score(S["petition-foreign"], det)
        r["negatives-foreign"] = false_alarms(S["negatives-foreign"], det)
        r["negatives"] = false_alarms(neg, det)
        r["_missed_examples"] = sorted({x["text"] for x in gf if not x["found"]})[:40]
        res[name] = r; rows[name] = gf
        cf, ct = r["court-foreign"], r["court-turkish"]
        ci = lambda x: f"{100 * x['recall']:5.1f}% [{100 * x['recall_ci'][0]:4.1f}–{100 * x['recall_ci'][1]:4.1f}]"
        ids = " ".join(f"{t}: {100 * (1 - v['masked']):4.1f}% readable / {100 * v['right_label']:4.1f}% right label" for t, v in r["petition-foreign ids"].items())
        nf = r["negatives-foreign"].get("PERSON", {"per_1k_words": 0})["per_1k_words"]
        print(f"\n{name}\n  foreign names (court) {ci(cf)}  prec {100 * cf['precision']:5.1f}%   Turkish names, same slots {ci(ct)}  "
              f"McNemar p={r['foreign_vs_turkish']['p']:.2g}\n  by group: " + ", ".join(f"{g} {100 * v['recall']:.0f}% (n={v['gold']})" for g, v in r["by_group"].items())
              + f"\n  petition foreign names {ci(r['petition-foreign names'])}\n  IDs: {ids}\n  false names /1k words: foreign traps {nf:.2f}, "
              f"Katip negatives {r['negatives'].get('PERSON', {'per_1k_words': 0})['per_1k_words']:.2f}", flush=True)
    cli = list(rows)[2:]                          # the model folders, in command-line order
    for a, b in zip(cli[0::2], cli[1::2]):
        pb = K.paired_bootstrap(rows[a], rows[b])
        res[f"{b} vs {a}"] = pb
        print(f"\n{b} vs {a}: foreign-name recall {100 * pb['diff']:+.1f} points [{100 * pb['ci'][0]:+.1f}, {100 * pb['ci'][1]:+.1f}], "
              f"McNemar p={pb['p_mcnemar']:.2g} (found only by new {pb['only_b']}, only by control {pb['only_a']})")
    out = K.RESULTS / f"foreign_{tag}.json"; out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    print("\nwrote", out)
    return res

if __name__ == "__main__":
    main(sys.argv[1:])
