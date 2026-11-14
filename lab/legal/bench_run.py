"""Run systems on KVKK-Bench and write leaderboard rows (bench/results/<system>.json).

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
EXAMPLES = ["court-foreign-court-test-0#0", "tlner-legal-unseen-33", "gen-mesaj_01", "gen-icra_04"]   # public documents shown before/after on the leaderboard

def _onnx_params(f):
    import onnx
    from onnx import numpy_helper
    m = onnx.load(str(f), load_external_data=False)
    return int(sum(numpy_helper.to_array(t).size for t in m.graph.initializer if t.data_type in (1, 2, 3, 10)))  # float, uint8, int8, fp16 weights

def _katip(model_dir, trust):
    tg = K.Tagger(model_dir)
    det = lambda text: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(text, extra=tg(text), trust=trust)]
    return det, {"size_mb": round(tg.size_mb + 0.3, 1), "params": _onnx_params(tg.onnx_file), "runs_locally": True, "runs_in_browser": True,
                 "size_note": "int8 ONNX the browser downloads + 0.3 MB rules"}

def _hf_snapshot(repo, revision=None):
    from huggingface_hub import snapshot_download
    return snapshot_download(repo, revision=revision, allow_patterns=["config.json", "tokenizer*", "vocab.txt", "onnx/model_quantized.onnx"])

def _akdeniz_rules(trust):
    """Hybrid: Katip rules + akdeniz27 XLM-R Turkish NER, PERSON spans only, passed to the rules the way
    _katip passes the Katip tagger (case suffix after an apostrophe dropped, score kept so trust applies)."""
    import baselines as BL
    ak = BL.BASELINES["akdeniz"][1]()
    def extra(text):
        out = []
        for s, e, t, sc in ak(text, scores=True):
            if t != "PERSON":
                continue
            span = text[s:e]
            out.append((s, s + min([span.find(c) for c in "'\u2019" if c in span] or [len(span)]), sc, "PERSON"))
        return out
    det = lambda text: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(text, extra=extra(text), trust=trust)]
    return det, {"params": int(ak.params), "size_mb": round(ak.size_mb + 0.3, 1), "runs_locally": True, "runs_in_browser": False,
                 "size_note": "XLM-R weights as loaded (fp32) + 0.3 MB rules"}

def _baseline(key):
    import baselines as BL
    det = BL.BASELINES[key][1]()
    meta = {"runs_locally": True, "runs_in_browser": False}
    if hasattr(det, "params"): meta.update(params=int(det.params), size_mb=det.size_mb, size_note="weights as loaded (fp32)" if key != "qwen-1.5b" else ("fp16 checkpoint, run in fp32 on CPU" if os.environ.get("KATIP_DEVICE") == "cpu" else "fp16 weights"))
    if key == "presidio": meta.update(params=None, size_mb=None, size_note="spaCy xx_ent_wiki_sm (~11 MB) + Presidio")
    return det, meta

SYSTEMS = {
    "rules": ("Katip Rules v0.2", lambda: (lambda t: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(t, extra=[])],
                                           {"size_mb": 0.3, "params": 0, "runs_locally": True, "runs_in_browser": True})),
    "kvkk-pii": ("kvkk-pii 0.2 (regex library, MIT)", lambda: (lambda t: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect_baseline(t)],
                                                               {"params": 0, "size_mb": 0.1, "runs_locally": True, "runs_in_browser": False})),
    "tiny": ("Katip Tiny: rules + katip-tr-name-tagger-tiny", lambda: _katip(K.TINY, None)),
    "tiny-f": ("Katip Tiny-F: rules + tiny tagger retrained with foreign names", lambda: _katip(HERE / "bench" / "models" / "katip-tiny-foreign", 0.5)),
    "berturk-v2": ("Katip BERTurk v2: rules + f1k/katip-tr-pii-berturk", lambda: _katip(_hf_snapshot("f1k/katip-tr-pii-berturk"), 0.5)),
    "berturk-v1": ("Katip BERTurk v1 (synthetic only, internal reference): rules + f1k/katip-tr-pii-berturk@a107b87",
                   lambda: _katip(_hf_snapshot("f1k/katip-tr-pii-berturk", "a107b872080d28967eb8e57fcdc14127f54c3cb1"), 0.5)),
    "presidio": ("Presidio + spaCy xx (vanilla)", lambda: _baseline("presidio")),
    "savasy": ("savasy/bert-base-turkish-ner-cased", lambda: _baseline("savasy")),
    "akdeniz+rules": ("Katip rules + akdeniz27/xlm-roberta-base-turkish-ner (PERSON)", lambda: _akdeniz_rules(0.5)),
    "akdeniz": ("akdeniz27/xlm-roberta-base-turkish-ner", lambda: _baseline("akdeniz")),
    "gliner": ("urchade/gliner_multi_pii-v1 (person)", lambda: _baseline("gliner")),
    "cosmos-pii": ("ytu-ce-cosmos/modernbert-tr-pii-ner", lambda: _baseline("cosmos-pii")),
    "kvkk-pii-ner": ("ersanbil/kvkk-pii-ner (model only)", lambda: _baseline("kvkk-pii-ner")),
    "openmed-tr": ("OpenMed PII Turkish 335M", lambda: _baseline("openmed-tr")),
    "qwen-1.5b": ("Qwen2.5-1.5B-Instruct, prompted to list personal data", lambda: _baseline("qwen-1.5b")),
}

def run(key, split="public"):
    name, make = SYSTEMS[key]
    det, meta = make()
    gold = [r for p in sorted((BB.OUT / split).glob("*.jsonl")) for r in BB.load(p)]
    for r in gold[:20]: det(r["text"])  # warm-up, not timed
    t0 = time.time(); pred = []
    for r in gold:
        pred.append({"id": r["id"], "spans": [list(x[:3]) for x in det(r["text"])]})
    secs = time.time() - t0
    words = sum(len(r["text"].split()) for r in gold)
    import platform
    row = {"system": key, "name": name, "split": split, "version": BB.VERSION, **meta,
           "ms_per_doc": round(1000 * secs / max(1, len(gold)), 1), "words_per_s": round(words / secs, 0),
           "ms_per_page": round(1000 * secs / words * 500, 0),   # a page = 500 words
           "machine": f"{platform.machine()} {platform.system()}, {os.cpu_count()} CPUs", **BS.score(gold, pred)}
    RES.mkdir(parents=True, exist_ok=True)
    if split == "public":   # keep raw predictions on the public split, so a scorer fix can re-score without re-running models
        pd = HERE / "bench" / "preds"; pd.mkdir(exist_ok=True)
        (pd / f"{key}.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pred))
    if split == "public":
        ex = HERE / "bench" / "examples"; ex.mkdir(exist_ok=True)
        (ex / f"{key}.json").write_text(json.dumps({p["id"]: p["spans"] for p in pred if p["id"] in EXAMPLES}, ensure_ascii=False))
    (RES / f"{key}{'' if split == 'public' else '_' + split}.json").write_text(json.dumps(row, indent=1, default=float))
    return row

def rescore(key):
    """Re-score saved public predictions with the current scorer (keeps timing and size from the last run)."""
    row = json.loads((RES / f"{key}.json").read_text())
    gold = [r for p in sorted((BB.OUT / "public").glob("*.jsonl")) for r in BB.load(p)]
    pred = [json.loads(l) for l in (HERE / "bench" / "preds" / f"{key}.jsonl").read_text().splitlines()]
    row.update(BS.score(gold, pred)); row["version"] = BB.VERSION
    (RES / f"{key}.json").write_text(json.dumps(row, indent=1, default=float))
    return row

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("systems", nargs="+"); ap.add_argument("--split", default="public")
    ap.add_argument("--rescore", action="store_true", help="re-score saved predictions instead of running the models")
    a = ap.parse_args()
    for k in a.systems:
        try: r = rescore(k) if a.rescore else run(k, a.split)
        except Exception as e: print(f"skip {k}: {type(e).__name__}: {str(e)[:150]}"); continue
        print(f"{r['name']:55} KVKK-F2 {100 * r['KVKK-F2']:5.1f}  leak {100 * r['leak_rate']:5.2f}%  " +
              "  ".join(f"{t}:{100 * x['recall']:.0f}/{100 * x['precision']:.0f}" for t, x in r["tracks"].items() if x["recall"] == x["recall"]), flush=True)
