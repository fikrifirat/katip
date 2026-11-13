"""Run systems on KVKK-Bench-TR and write leaderboard rows (bench/results/<system>.json).

  python lab/legal/bench_run.py rules tiny presidio kvkk-pii           # what runs anywhere (CPU, no Hugging Face)
  python lab/legal/bench_run.py berturk-v2 cosmos-pii kvkk-pii-ner openmed-tr gliner savasy akdeniz   # needs HF access
  python lab/legal/bench_run.py --split hidden ...                     # maintainers only

Each system is a function text -> [(start, end, TYPE)]. Katip models run with the browser's own code
(rules + model, at the trust chosen on dev). Every system gets the same input and the same scorer.
"""
from __future__ import annotations

import argparse, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import katiplab as K  # noqa: E402
import local_detect  # noqa: E402
import bench_build as BB  # noqa: E402
import bench_score as BS  # noqa: E402

RES = HERE / "bench" / "results"

def _katip(model_dir, trust):
    tg = K.Tagger(model_dir)
    det = lambda text: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(text, extra=tg(text), trust=trust)]
    return det, {"size_mb": round(tg.size_mb, 1), "runs_locally": True}

def _hf_snapshot(repo):
    from huggingface_hub import snapshot_download
    return snapshot_download(repo, allow_patterns=["config.json", "tokenizer*", "vocab.txt", "onnx/model_quantized.onnx"])

def _baseline(key):
    import baselines as BL
    det = BL.BASELINES[key][1]()
    return det, {"runs_locally": True}

SYSTEMS = {
    "rules": ("Katip Rules v0.2", lambda: (lambda t: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(t, extra=[])],
                                           {"size_mb": 0.3, "runs_locally": True})),
    "kvkk-pii": ("kvkk-pii 0.2 (regex library, MIT)", lambda: (lambda t: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect_baseline(t)],
                                                               {"runs_locally": True})),
    "tiny": ("Katip Tiny: rules + katip-tr-name-tagger-tiny", lambda: _katip(K.TINY, None)),
    "berturk-v2": ("Katip BERTurk v2: rules + f1k/katip-tr-pii-berturk", lambda: _katip(_hf_snapshot("f1k/katip-tr-pii-berturk"), 0.5)),
    "presidio": ("Presidio + spaCy xx (vanilla)", lambda: _baseline("presidio")),
    "savasy": ("savasy/bert-base-turkish-ner-cased", lambda: _baseline("savasy")),
    "akdeniz": ("akdeniz27/xlm-roberta-base-turkish-ner", lambda: _baseline("akdeniz")),
    "gliner": ("urchade/gliner_multi_pii-v1 (person)", lambda: _baseline("gliner")),
    "cosmos-pii": ("ytu-ce-cosmos/modernbert-tr-pii-ner", lambda: _baseline("cosmos-pii")),
    "kvkk-pii-ner": ("ersanbil/kvkk-pii-ner (model only)", lambda: _baseline("kvkk-pii-ner")),
    "openmed-tr": ("OpenMed PII Turkish 335M", lambda: _baseline("openmed-tr")),
}

def run(key, split="public"):
    name, make = SYSTEMS[key]
    det, meta = make()
    gold = [r for p in sorted((BB.OUT / split).glob("*.jsonl")) for r in BB.load(p)]
    t0 = time.time(); pred = []
    for r in gold:
        pred.append({"id": r["id"], "spans": [list(x[:3]) for x in det(r["text"])]})
    secs = time.time() - t0
    row = {"system": key, "name": name, "split": split, "version": BB.VERSION, **meta,
           "ms_per_doc": round(1000 * secs / max(1, len(gold)), 1), **BS.score(gold, pred)}
    RES.mkdir(parents=True, exist_ok=True)
    (RES / f"{key}{'' if split == 'public' else '_' + split}.json").write_text(json.dumps(row, indent=1, default=float))
    return row

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("systems", nargs="+"); ap.add_argument("--split", default="public")
    a = ap.parse_args()
    for k in a.systems:
        try: r = run(k, a.split)
        except Exception as e: print(f"skip {k}: {type(e).__name__}: {str(e)[:150]}"); continue
        print(f"{r['name']:55} KVKK-F2 {100 * r['KVKK-F2']:5.1f}  leak {100 * r['leak_rate']:5.2f}%  " +
              "  ".join(f"{t}:{100 * x['recall']:.0f}/{100 * x['precision']:.0f}" for t, x in r["tracks"].items() if x["recall"] == x["recall"]), flush=True)
