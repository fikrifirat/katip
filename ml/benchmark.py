"""Accuracy benchmark for the README: every data type, rules + name tagger (the demo's default),
run with the exact browser detection code (Pyodide bundle) and an onnxruntime port of ner.js.

  KATIP_MODEL=hf/model python ml/benchmark.py <katip-redact>/eval [tiny|rules|vanilla] > metrics/accuracy.json
  KATIP_MODEL=ml/berturk/out python ml/benchmark.py ml/berturk/data berturk > metrics/accuracy-berturk.json

<eval> is either a folder of sets with *.txt + *.gold.json, or ml/berturk/data (the same sets as *.jsonl.gz).
"tiny" and "berturk" both mean rules + the model in KATIP_MODEL; "rules" skips the model.

A gold value counts as found when a detected span of the same type covers it (same matching
rule as eval_system.py). Precision counts detected spans that match no gold value of any type.
"""
import gzip, json, os, sys, time
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
if sys.argv[2:3] in (["rules"], ["vanilla"]): os.environ.setdefault("KATIP_MODEL", str(Path(__file__).parents[1] / "hf" / "model"))
import eval_system as E  # noqa: E402  (loads the bundle and the model from KATIP_MODEL)

root = Path(sys.argv[1]); mode = sys.argv[2] if len(sys.argv) > 2 else "tiny"; out = {"model": mode, "sets": {}}
def run(text):
    if mode == "vanilla": return E.local_detect.detect_baseline(text)
    return E.local_detect.detect(text, extra=E.ner(text) if mode in ("tiny", "berturk") else [])
def docs_of(name):
    if (root / f"{name}.jsonl.gz").exists():
        for l in gzip.open(root / f"{name}.jsonl.gz", "rt", encoding="utf-8"):
            d = json.loads(l); yield d["text"], [{"entity_type": t, "text": d["text"][a:b]} for a, b, t in d["spans"]]
    for f in sorted((root / name).glob("*.txt")):
        gf = f.with_suffix(".gold.json")
        yield f.read_text(encoding="utf-8"), json.loads(gf.read_text()) if gf.exists() else []
if mode != "vanilla": out["model_dir"] = Path(os.environ.get("KATIP_MODEL", "")).name if mode != "rules" else ""
for name in ("blind", "heldout", "synthetic", "negatives"):
    per = defaultdict(lambda: {"gold": 0, "found": 0, "spans": 0, "false": 0})
    docs, ms = 0, 0.0
    for text, gold in docs_of(name):
        t0 = time.time(); spans = run(text); ms += (time.time() - t0) * 1000; docs += 1
        for g in gold:
            t = per[g["entity_type"]]; t["gold"] += 1
            t["found"] += any(s["entity_type"] == g["entity_type"] and E.matches(s["text"], g["text"]) for s in spans)
        for s in spans:
            t = per[s["entity_type"]]; t["spans"] += 1
            t["false"] += not any(E.matches(s["text"], g["text"]) or E.matches(g["text"], s["text"]) for g in gold)
    if not docs: continue
    tot = {k: sum(v[k] for v in per.values()) for k in ("gold", "found", "spans", "false")}
    out["sets"][name] = {"docs": docs, "ms_per_doc": round(ms / max(1, docs), 1), "types": dict(sorted(per.items())), "total": tot}
json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
