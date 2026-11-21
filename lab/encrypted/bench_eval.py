"""Score a Nano variant on KVKK-Bench (public split) with the bench's own scorer.

Two views: "pipeline" (Katip rules + model, trust 0.5: what the demo runs) and "model" (model names only).
The encrypted part of the system is the model, so the "model" view isolates what encryption changes.
"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "legal")]
import katiplab as K  # noqa: E402
import local_detect  # noqa: E402
import bench_build as BB  # noqa: E402
import bench_score as BS  # noqa: E402

def gold(tracks=None):
    rows = []
    for f in sorted((BB.OUT / "public").glob("*.jsonl")):
        rows += [r for r in BB.load(f) if tracks is None or r["track"] in tracks]
    return rows

def run(tagger, docs, mode="pipeline", trust=0.5):
    preds, t0 = [], time.time()
    for d in docs:
        ex = tagger(d["text"])
        if mode == "model":
            sp = [[s, e, t] for s, e, _, t in ex]
        else:
            sp = [[x["start"], x["end"], x["entity_type"]] for x in local_detect.detect(d["text"], extra=ex, trust=trust, address_detail="full")]
        preds.append({"id": d["id"], "spans": sp})
    return preds, time.time() - t0

def summary(row):
    t = row["tracks"]
    g = lambda k, m="f2": round(100 * t[k][m], 2) if k in t else None
    return {"KVKK-F2": round(100 * row["KVKK-F2"], 2), "generated": round(100 * row["F2 generated"], 2), "leak%": round(100 * row["leak_rate"], 2),
            "court-filled F2": g("court-filled"), "prose F2": g("prose"),
            "court-filled R/P": (g("court-filled", "recall"), g("court-filled", "precision")), "prose R/P": (g("prose", "recall"), g("prose", "precision"))}

def evaluate(tagger, mode="pipeline", tracks=None, docs=None):
    docs = docs or gold(tracks)
    preds, secs = run(tagger, docs, mode)
    row = BS.score(docs, preds)
    return {**summary(row), "secs": round(secs, 1)}, preds

def label_agreement(ref_preds, preds):
    """Share of documents whose predicted spans are identical."""
    R = {p["id"]: p["spans"] for p in ref_preds}
    return sum(R[p["id"]] == p["spans"] for p in preds) / len(preds)

def dev_docs():
    """Choice set (never the bench): Turkish Wiki NER dev (real prose) + Katip's held-out synthetic documents."""
    wiki = [{"id": f"wikidev-{d['id']}", "track": "prose", "text": d["text"], "spans": [s for s in d["spans"] if s[2] == "PERSON"]} for d in K.load_wiki("dev")]
    held = [{"id": f"held-{d['id']}", "track": "petition", "text": d["text"], "spans": d["spans"]} for d in K.load_synth("heldout")]
    return wiki + held
