"""Score Kalkan's detection on the synthetic EU set: "ai" (KVKK rules only) vs "eu" (KVKK + eu.py).

A gold value counts as caught when the masked spans cover every one of its characters (part of a name left
readable is a miss). Reports recall per type, per language, per name setting and name pool, the share of documents
where every value was caught, and the characters masked in the negatives (name-free legal prose).

  python lab/eu/synth_eu.py --seed 2611 --n 300
  KATIP_SDK=0 python lab/eu/eval_eu.py lab/eu/data/eu_synth_seed2611.jsonl
"""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "connector"))
os.environ.setdefault("KATIP_HOME", tempfile.mkdtemp())
from katip_kalkan import engine, eu  # noqa: E402


def spans_for(text, profile):
    types, addr = engine.profile_types(profile)
    sp = engine.detect(text, 0.5, types, address_detail=addr)
    if engine.PROFILES[profile].get("eu"):
        sp = eu.merge(text, sp)
    return sp


def covered(sp, g):
    cov = set()
    for s in sp:
        cov.update(range(max(s["start"], g["start"]), min(s["end"], g["end"])))
    need = {i for i in range(g["start"], g["end"])}
    return need <= cov


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def main(path, neg_path=None):
    docs = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    neg_path = neg_path or Path(path).with_name("eu_negatives.jsonl")
    negs = [json.loads(x)["text"] for x in Path(neg_path).read_text(encoding="utf-8").splitlines() if x.strip()]
    report = {"set": Path(path).name, "docs": len(docs), "negatives": len(negs), "profiles": {}}
    for profile in ("ai", "eu"):
        by = defaultdict(lambda: [0, 0])
        full_docs = 0
        misses = []
        for d in docs:
            sp = spans_for(d["text"], profile)
            all_ok = True
            for g in d["gold"]:
                ok = covered(sp, g)
                keys = [("type", g["type"]), ("lang", d["lang"])]
                if g["type"] == "PERSON":
                    keys += [("name_setting", d["setting"]), ("name_pool", d["pool"])]
                if g["type"] == "NATIONAL_ID":
                    keys += [("id", "typo" if d["id_typo"] else "valid")]
                for k in keys + [("all", "values")]:
                    by[k][0] += ok
                    by[k][1] += 1
                if not ok:
                    all_ok = False
                    if len(misses) < 40:
                        misses.append({"lang": d["lang"], "type": g["type"], "text": g["text"], "setting": d["setting"]})
            full_docs += all_ok
        neg_chars = neg_spans = 0
        neg_examples = []
        for t in negs:
            sp = spans_for(t, profile)
            neg_spans += len(sp)
            neg_chars += sum(s["end"] - s["start"] for s in sp)
            neg_examples += [f'{s["entity_type"]}: {s["text"]}' for s in sp]
        res = {"recall": {f"{a}={b}": {"caught": k, "of": n, "pct": round(100 * k / n, 1),
                                       "ci95": [round(x, 1) for x in wilson(k, n)]}
                          for (a, b), (k, n) in sorted(by.items())},
               "docs_fully_masked_pct": round(100 * full_docs / len(docs), 1),
               "negatives": {"spans": neg_spans, "chars_masked": neg_chars,
                             "chars_total": sum(len(t) for t in negs), "examples": neg_examples},
               "first_misses": misses}
        report["profiles"][profile] = res
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
