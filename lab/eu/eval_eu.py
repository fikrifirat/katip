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


SPECIAL = {"HEALTH", "CRIMINAL", "CRIMINAL_RECORD", "RELIGION", "UNION", "POLITICAL", "SEXUAL_LIFE", "ETHNICITY",
           "BIOMETRIC_GENETIC"}


def _visible(text, spans):
    out, pos = [], 0
    for s in sorted(spans, key=lambda s: (s["start"], -s["end"])):
        if s["start"] < pos:
            continue
        out.append(text[pos:s["start"]] + " _ ")
        pos = s["end"]
    return "".join(out) + text[pos:]


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
    neg_path = Path(neg_path or Path(path).with_name("eu_negatives.jsonl"))
    if not neg_path.exists():
        neg_path = Path(__file__).parent / "data" / "eu_negatives.jsonl"
    negs = [json.loads(x)["text"] for x in neg_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    report = {"set": Path(path).name, "docs": len(docs), "negatives": len(negs), "profiles": {}}
    for profile in ("ai", "eu"):
        by = defaultdict(lambda: [0, 0])
        full_docs = 0
        misses = []
        keep, overmasked = [0, 0], []
        for d in docs:
            sp = spans_for(d["text"], profile)
            all_ok = True
            for g in d["gold"]:
                ok = covered(sp, g)
                keys = [("type", g["type"]), ("lang", d.get("lang", "?"))]
                if d.get("doc_type"):
                    keys.append(("doc_type", d["doc_type"]))
                if g["type"] == "PERSON" and "setting" in d:
                    keys += [("name_setting", d["setting"]), ("name_pool", d["pool"])]
                if g["type"] == "NATIONAL_ID" and "id_typo" in d:
                    keys += [("id", "typo" if d["id_typo"] else "valid")]
                for k in keys + [("all", "values")]:
                    by[k][0] += ok
                    by[k][1] += 1
                if g["type"] in SPECIAL:  # keyword-level rules: count a clause as flagged when any of it is masked
                    any_hit = any(s["start"] < g["end"] and g["start"] < s["end"] for s in sp)
                    by[("special_flagged", g["type"])][0] += any_hit
                    by[("special_flagged", g["type"])][1] += 1
                if not ok:
                    all_ok = False
                    if len(misses) < 60:
                        misses.append({"lang": d.get("lang"), "doc": d.get("id") or d.get("doc_type"), "type": g["type"],
                                       "text": g["text"], "setting": d.get("setting")})
            full_docs += all_ok
            # strings the document must keep readable (court names, case numbers, statutes, the firm's own name)
            vis = _visible(d["text"], sp)
            for k in d.get("keep", []):
                keep[1] += 1
                if k in vis:
                    keep[0] += 1
                elif len(overmasked) < 60:
                    overmasked.append({"doc": d.get("id") or d.get("doc_type"), "text": k})
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
               "keep_readable": {"kept": keep[0], "of": keep[1]}, "over_masked": overmasked,
               "first_misses": misses}
        report["profiles"][profile] = res
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
