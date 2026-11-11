"""Accuracy benchmark for the README: every data type, rules + name tagger (the demo's default),
run with the exact browser detection code (Pyodide bundle) and an onnxruntime port of ner.js.

  KATIP_MODEL=hf/model python ml/benchmark.py <katip-redact>/eval > metrics/accuracy.json

A gold value counts as found when a detected span of the same type covers it (same matching
rule as eval_system.py). Precision counts detected spans that match no gold value of any type.
"""
import json, os, sys, time
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import eval_system as E  # noqa: E402  (loads the bundle and the model from KATIP_MODEL)

root = Path(sys.argv[1]); out = {"sets": {}}
for name in ("blind", "heldout", "synthetic", "negatives"):
    d = root / name
    per = defaultdict(lambda: {"gold": 0, "found": 0, "spans": 0, "false": 0})
    docs, ms = 0, 0.0
    for f in sorted(d.glob("*.txt")):
        text = f.read_text(encoding="utf-8"); gf = f.with_suffix(".gold.json")
        gold = json.loads(gf.read_text()) if gf.exists() else []
        t0 = time.time(); spans = E.local_detect.detect(text, extra=E.ner(text)); ms += (time.time() - t0) * 1000; docs += 1
        for g in gold:
            t = per[g["entity_type"]]; t["gold"] += 1
            t["found"] += any(s["entity_type"] == g["entity_type"] and E.matches(s["text"], g["text"]) for s in spans)
        for s in spans:
            t = per[s["entity_type"]]; t["spans"] += 1
            t["false"] += not any(E.matches(s["text"], g["text"]) or E.matches(g["text"], s["text"]) for g in gold)
    tot = {k: sum(v[k] for v in per.values()) for k in ("gold", "found", "spans", "false")}
    out["sets"][name] = {"docs": docs, "ms_per_doc": round(ms / max(1, docs), 1), "types": dict(sorted(per.items())), "total": tot}
json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
