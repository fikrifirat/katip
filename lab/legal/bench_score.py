"""Score a KVKK-Bench-TR submission (see lab/legal/LEADERBOARD.md).

  python lab/legal/bench_score.py gold.jsonl predictions.jsonl [--name my-model] [--out row.json]

gold.jsonl         {"id", "track", "text", "spans": [[start, end, TYPE], ...]}
predictions.jsonl  {"id", "spans": [[start, end, TYPE], ...]}     (offsets into the gold "text")

Prints one leaderboard row: per track and per type recall / precision / F2, the leak rate (share of gold PII
characters left readable) and the clean-document rate, and the ranking score KVKK-F2 (macro F2 over tracks).
Matching follows Katip's rule (lab/katiplab.matches): a prediction covers the gold value, or is at least half
of it and 3+ characters; the type must match. Strict exact-offset scores are reported next to it.
"""
from __future__ import annotations

import argparse, json, re
from collections import defaultdict

import numpy as np

GENERAL = ["PERSON", "TCKN", "VKN", "YKN", "PASSPORT", "FOREIGN_ID", "PHONE", "EMAIL", "IBAN", "CREDIT_CARD", "ADDRESS", "PLATE", "BIRTH_DATE", "IP_ADDRESS"]
SPECIAL = ["HEALTH", "RELIGION", "ETHNICITY", "POLITICAL", "UNION", "SEXUAL_LIFE", "CRIMINAL_RECORD", "BIOMETRIC_GENETIC",
           "PHILOSOPHICAL", "ASSOCIATION", "DRESS"]   # KVKK art. 6 special categories
TYPES = GENERAL + SPECIAL
# Ranking uses real text only. Generated documents come from the same generator family Katip trains on,
# so they are shown as a regression check, never ranked on.
REAL_TRACKS = {"court", "court-real", "court-filled", "court-turkish", "court-foreign", "prose", "scan"}

_sq = lambda s: re.sub(r"\s+", "", s).casefold()
def matches(a, b):
    x, y = _sq(a), _sq(b)
    return y in x or (x in y and len(x) >= max(3, len(y) * 0.5))

def true_span(text, a, b, golds):
    """A predicted span is correct when it touches a gold value of its type AND at least half of its letters and
    digits are inside such values. Without the second test a mask over the whole document would score 100% precision."""
    if not any(s < b and a < e for s, e in golds): return False
    keep = [i for i in range(max(0, a), min(len(text), b)) if text[i].isalnum()]
    if not keep: return False
    inside = sum(any(s <= i < e for s, e in golds) for i in keep)
    return inside >= 0.5 * len(keep)

def f2(p, r): return 5 * p * r / (4 * p + r) if p + r else 0.0

def score(gold, pred):
    P = {d["id"]: d.get("spans", []) for d in pred}
    missing = [d["id"] for d in gold if d["id"] not in P]
    cnt = defaultdict(lambda: defaultdict(lambda: np.zeros(5)))   # track -> type -> [gold, found, spans, true, exact]
    leak = defaultdict(lambda: [0, 0, 0, 0])                       # track -> [gold chars, readable chars, docs, clean docs]
    for d in gold:
        t, text, ps = d.get("track", "all"), d["text"], P.get(d["id"], [])
        masked = np.zeros(len(text), bool)
        for s, e, _ in ps: masked[max(0, s):min(len(text), e)] = True
        left = 0
        for s, e, typ in d["spans"]:
            if typ not in TYPES: continue
            c = cnt[t][typ]; c[0] += 1
            c[1] += any(pt == typ and matches(text[a:b], text[s:e]) for a, b, pt in ps)
            c[4] += any(pt == typ and a == s and b == e for a, b, pt in ps)
            leak[t][0] += e - s; left += int((~masked[s:e]).sum())
        leak[t][1] += left
        if any(typ in TYPES for _, _, typ in d["spans"]): leak[t][2] += 1; leak[t][3] += left == 0
        for a, b, pt in ps:
            if pt not in TYPES: continue
            c = cnt[t][pt]; c[2] += 1
            c[3] += true_span(text, a, b, [(s, e) for s, e, gt in d["spans"] if gt == pt])
    row = {"tracks": {}, "missing_predictions": len(missing)}
    for t, by in sorted(cnt.items()):
        tr = {}
        for typ, (g, f, s, ok, ex) in by.items():
            r = f / g if g else float("nan"); p = ok / s if s else (1.0 if g == 0 else 0.0)
            tr[typ] = {"gold": int(g), "recall": r, "precision": p, "f2": f2(p, r) if g else float("nan"), "exact_recall": ex / g if g else float("nan")}
        G = sum(v[0] for v in by.values()); F = sum(v[1] for v in by.values()); Sx = sum(v[2] for v in by.values()); T = sum(v[3] for v in by.values())
        mr, mp = F / G if G else float("nan"), T / Sx if Sx else 0.0
        spec = [by[x] for x in SPECIAL if x in by]
        sr = sum(v[1] for v in spec) / sum(v[0] for v in spec) if spec and sum(v[0] for v in spec) else float("nan")
        lk = leak[t]
        words = sum(len(d["text"].split()) for d in gold if d.get("track", "all") == t)
        row["tracks"][t] = {"types": tr, "recall": mr, "precision": mp, "f2": f2(mp, mr) if G else float("nan"), "special_category_recall": sr,
                            "false_per_1k_words": 1000 * (Sx - T) / max(1, words),
                            "leak_rate": lk[1] / lk[0] if lk[0] else float("nan"), "clean_doc_rate": lk[3] / lk[2] if lk[2] else float("nan")}
    v = [x["f2"] for x in row["tracks"].values() if x["f2"] == x["f2"]]   # tracks with gold values only
    real = [x["f2"] for t, x in row["tracks"].items() if t in REAL_TRACKS and x["f2"] == x["f2"]]
    gen = [x["f2"] for t, x in row["tracks"].items() if t not in REAL_TRACKS and x["f2"] == x["f2"]]
    row["KVKK-F2"] = float(np.mean(real)) if real else float("nan")          # the ranking score: real text only
    row["F2 generated"] = float(np.mean(gen)) if gen else float("nan")      # regression check on generated documents
    row["F2 all tracks"] = float(np.mean(v)) if v else float("nan")
    row["leak_rate"] = float(np.nanmean([x["leak_rate"] for x in row["tracks"].values()])) if v else float("nan")
    return row

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("gold"); ap.add_argument("pred")
    ap.add_argument("--name", default="submission"); ap.add_argument("--out", default="")
    a = ap.parse_args()
    load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    row = {"name": a.name, **score(load(a.gold), load(a.pred))}
    print(f"{a.name}: KVKK-F2 {100 * row['KVKK-F2']:.1f}   leak rate {100 * row['leak_rate']:.2f}%   missing {row['missing_predictions']}")
    for t, x in row["tracks"].items():
        print(f"  {t:22} recall {100 * x['recall']:5.1f}  precision {100 * x['precision']:5.1f}  F2 {100 * x['f2']:5.1f}  "
              f"art.6 recall {100 * x['special_category_recall']:5.1f}  clean docs {100 * x['clean_doc_rate']:5.1f}%  false/1k words {x['false_per_1k_words']:.2f}")
    if a.out: open(a.out, "w").write(json.dumps(row, indent=1, default=float))
