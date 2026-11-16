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

DETECT_KW = {"address_detail": "full"}   # the photo track switches this to what Katip Yerel uses on scans (see run_photo)

def _katip(model_dir, trust):
    tg = K.Tagger(model_dir)
    det = lambda text: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(text, extra=tg(text), trust=trust, **DETECT_KW)]
    return det, {"size_mb": round(tg.size_mb + 0.3, 1), "params": _onnx_params(tg.onnx_file), "runs_locally": True, "runs_in_browser": True,
                 "size_note": "int8 ONNX the browser downloads + 0.3 MB rules"}

def _trust_file(d):
    """Trust chosen on dev by lab/mini/train_mini.py, stored next to the model as katip_trust.json."""
    f = Path(d) / "katip_trust.json"
    return json.loads(f.read_text())["trust"] if f.exists() else 0.5


def _hf_snapshot(repo, revision=None):
    from huggingface_hub import snapshot_download
    return snapshot_download(repo, revision=revision, allow_patterns=["config.json", "tokenizer*", "vocab.txt", "onnx/model_quantized.onnx"])

def _gliner2_katip(path, trust=0.5):
    """Katip rules + a GLiNER2 model fine-tuned on Base v2's data (ml/gliner2/train_gliner2.py), passed to the rules
    like the Katip tagger: PERSON, ADDRESS and HEALTH spans with their scores, case suffix after an apostrophe dropped."""
    from gliner2 import GLiNER2
    m = GLiNER2.from_pretrained(str(path)); m.eval()
    inv = {"person": "PERSON", "address": "ADDRESS", "health condition": "HEALTH"}
    def extra(text):
        r = m.extract_entities(text, list(inv), threshold=0.3, include_spans=True, include_confidence=True)
        out = []
        for t, es in (r.get("entities") or {}).items():
            for e in es:
                s, e_ = e["start"], e["end"]; span = text[s:e_]
                if inv.get(t) == "PERSON":
                    e_ = s + min([span.find(c) for c in "'\u2019" if c in span] or [len(span)])
                out.append((s, e_, float(e.get("confidence", 0.9)), inv[t]))
        return out
    det = lambda text: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(text, extra=extra(text), trust=trust, **DETECT_KW)]
    n = sum(p.numel() for p in m.parameters())
    return det, {"params": int(n), "size_mb": round(sum(p.numel() * p.element_size() for p in m.parameters()) / 1e6 + 0.3, 1),
                 "runs_locally": True, "runs_in_browser": False, "size_note": "weights as loaded + 0.3 MB rules"}

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
    det = lambda text: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(text, extra=extra(text), trust=trust, **DETECT_KW)]
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
    "rules": ("Katip Rules v0.2", lambda: (lambda t: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(t, extra=[], **DETECT_KW)],
                                           {"size_mb": 0.3, "params": 0, "runs_locally": True, "runs_in_browser": True})),
    "kvkk-pii": ("kvkk-pii 0.2 (regex library, MIT)", lambda: (lambda t: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect_baseline(t)],
                                                               {"params": 0, "size_mb": 0.1, "runs_locally": True, "runs_in_browser": False})),
    "tiny": ("Katip Tiny: rules + katip-tr-name-tagger-tiny", lambda: _katip(K.TINY, None)),
    "tiny-f": ("Katip Tiny-F: rules + tiny tagger retrained with foreign names", lambda: _katip(HERE / "bench" / "models" / "katip-tiny-foreign", 0.5)),
    "mini": ("Katip Mask Mini: rules + Mini tagger (distilled from Base)", lambda: _katip(HERE / "bench" / "models" / "katip-mask-mini", _trust_file(HERE / "bench" / "models" / "katip-mask-mini"))),
    "xlmr": ("Katip XLM-R: rules + XLM-R base tagger trained in Colab", lambda: _katip(HERE / "bench" / "models" / "katip-xlmr", _trust_file(HERE / "bench" / "models" / "katip-xlmr"))),
    "mini-v2": ("Katip Mask Mini v2: rules + Mini v2 tagger (DistilBERTurk L3, 12k vocab, distilled from Base)", lambda: _katip(HERE / "bench" / "models" / "katip-mask-mini-v2", _trust_file(HERE / "bench" / "models" / "katip-mask-mini-v2"))),
    "nano-v2": ("Katip Mask Nano v2: rules + Nano retrained, distilled from Base", lambda: _katip(HERE / "bench" / "models" / "katip-mask-nano-v2", _trust_file(HERE / "bench" / "models" / "katip-mask-nano-v2"))),
    "berturk-v2": ("Katip BERTurk v2: rules + f1k/katip-tr-pii-berturk", lambda: _katip(_hf_snapshot("f1k/katip-tr-pii-berturk"), 0.5)),
    "berturk-clean": ("Katip BERTurk clean: rules + BERTurk trained on synthetic + public legal web text (no real decisions)",
                      lambda: _katip(HERE.parent.parent / "ml" / "berturk" / "out_clean", 0.5)),
    "berturk-v1": ("Katip BERTurk v1 (synthetic only, internal reference): rules + f1k/katip-tr-pii-berturk@a107b87",
                   lambda: _katip(_hf_snapshot("f1k/katip-tr-pii-berturk", "a107b872080d28967eb8e57fcdc14127f54c3cb1"), 0.5)),
    "presidio": ("Presidio + spaCy xx (vanilla)", lambda: _baseline("presidio")),
    "savasy": ("savasy/bert-base-turkish-ner-cased", lambda: _baseline("savasy")),
    "gliner2-katip": ("Katip rules + GLiNER2 PII multi fine-tuned on Base v2's data (Colab)", lambda: _gliner2_katip(HERE / "bench" / "models" / "katip-gliner2" / "model")),
    "gliner2-pii+rules": ("Katip rules + GLiNER2 PII multi off the shelf (same harness as gliner2-katip, no fine-tuning)", lambda: _gliner2_katip("fastino/gliner2-privacy-filter-PII-multi")),
    "akdeniz+rules": ("Katip rules + akdeniz27/xlm-roberta-base-turkish-ner (PERSON)", lambda: _akdeniz_rules(0.5)),
    "akdeniz": ("akdeniz27/xlm-roberta-base-turkish-ner", lambda: _baseline("akdeniz")),
    "gliner": ("urchade/gliner_multi_pii-v1 (person)", lambda: _baseline("gliner")),
    "cosmos-pii": ("ytu-ce-cosmos/modernbert-tr-pii-ner", lambda: _baseline("cosmos-pii")),
    "kvkk-pii-ner": ("ersanbil/kvkk-pii-ner (model only)", lambda: _baseline("kvkk-pii-ner")),
    "openmed-tr": ("OpenMed PII Turkish 335M", lambda: _baseline("openmed-tr")),
    "qwen-1.5b": ("Qwen2.5-1.5B-Instruct, prompted to list personal data", lambda: _baseline("qwen-1.5b")),
    "openai-pf": ("openai/privacy-filter", lambda: _baseline("openai-pf")),
    "openmed-pf-v2": ("OpenMed/privacy-filter-multilingual-v2", lambda: _baseline("openmed-pf-v2")),
    "openmed-pf": ("OpenMed/privacy-filter-multilingual", lambda: _baseline("openmed-pf")),
    "gliner2-pii": ("fastino/gliner2-privacy-filter-PII-multi (person)", lambda: _baseline("gliner2-pii")),
    "newmind-mursit-kvkk": ("newmindai/gliner2.5-mursit-kvkk-tr-v1 (stack21 labels)", lambda: _baseline("newmind-mursit-kvkk")),
    "newmind-kvkk-v2": ("newmindai/gliner2.5-kvkk-tr-v2 (stack21 labels)", lambda: _baseline("newmind-kvkk-v2")),
    "gliner2-pii-full": ("fastino/gliner2-privacy-filter-PII-multi (full labels)", lambda: _baseline("gliner2-pii-full")),
    "openmed-tr-33m": ("OpenMed/OpenMed-PII-Turkish-ClinicalE5-Small-33M-v1", lambda: _baseline("openmed-tr-33m")),
    "xlmr-conll": ("FacebookAI/xlm-roberta-large-finetuned-conll03-english", lambda: _baseline("xlmr-conll")),
    "piiranha": ("iiiorg/piiranha-v1-detect-personal-information", lambda: _baseline("piiranha")),
    "piilot": ("ParkJunSeong/PIILOT_NER_Model", lambda: _baseline("piilot")),
    "openmed-sc-44m": ("OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1", lambda: _baseline("openmed-sc-44m")),
    "openmed-sc-434m": ("OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1", lambda: _baseline("openmed-sc-434m")),
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

# ---- photo track (v0.1.3): phone photos of hand-filled forms, scored on boxes, not on text
# OCR ran once (lab/legal/bench/photos/ocr_dump.mjs, Katip's "Otomatik" OCR); every system gets the same OCR text,
# its spans become boxes the way the browser does it (engine.attachBoxes), and a gold value counts as
#   leaked       if less than 70% of its box is covered by masks;
#   over-masked  a street / mahalle name that must stay readable and is more than 30% covered.
# Katip rows also get the masks Katip draws from pen ink alone (engine.unreadSpans: handwriting in an ID / name row,
# unreadable handwriting next to a personal-data label); "+ ink masks" in the name says so.
PH = HERE / "bench" / "photos"
KATIP_KEYS = {"rules", "tiny", "tiny-f", "mini", "mini-v2", "nano-v2", "xlmr", "berturk-v2", "berturk-clean", "berturk-v1", "akdeniz+rules", "gliner2-katip", "gliner2-pii+rules"}

def _attach_boxes(page, s, e, typ):
    """Port of engine.attachBoxes: span offsets -> one box per OCR line, grown over touching pen ink."""
    import re
    by_line = {}
    for w in page["words"]:
        if w["end"] <= s or w["start"] >= e: continue
        x0, y0, x1, y1 = w["bbox"]; n = max(1, len(w["text"]))
        a, b = max(s, w["start"]) - w["start"], min(e, w["end"]) - w["start"]
        if not re.search(r"[^\W_]", w["text"][:a]): a = 0
        if not re.search(r"[^\W_]", w["text"][b:]): b = n
        cw = (x1 - x0) / n
        cx0, cx1 = x0 + cw * a - (cw / 2 if a else 0), x0 + cw * b + (cw / 2 if b < n else 0)
        k = round((y0 + y1) / 2 / 4)
        q = by_line.get(k, [cx0, y0, cx1, y1])
        by_line[k] = [min(q[0], cx0), min(q[1], y0), max(q[2], cx1), max(q[3], y1)]
    boxes = list(by_line.values())
    if page["ocr"] and page["pen"] and typ != "ADDRESS":
        grown = []
        for x0, y0, x1, y1 in boxes:
            h = y1 - y0
            for q in page["pen"]:
                vo, gap = min(y1, q[3]) - max(y0, q[1]), max(x0, q[0]) - min(x1, q[2])
                if q[3] - q[1] <= 2 * h and vo > 0.5 * min(h, q[3] - q[1]) and gap < 0.8 * h:
                    x0, y0, x1, y1 = min(x0, q[0]), min(y0, q[1]), max(x1, q[2]), max(y1, q[3])
            grown.append([x0, y0, x1, y1])
        boxes = grown
    return boxes

def _coverage(box, masks, N=24):
    x0, y0, x1, y1 = box; hit = 0
    for i in range(N):
        for j in range(N):
            x, y = x0 + (i + .5) * (x1 - x0) / N, y0 + (j + .5) * (y1 - y0) / N
            hit += any(a - 1 <= x <= c + 1 and b - 1 <= y <= d + 1 for a, b, c, d in masks)
    return hit / N / N

def _overlaps(m, b): return m[0] < b[2] and m[2] > b[0] and m[1] < b[3] and m[3] > b[1]

def run_photo(key, ink=None):
    global DETECT_KW
    name, make = SYSTEMS[key]
    default_ink = key in KATIP_KEYS
    ink = default_ink if ink is None else ink
    docs = [json.loads(l) for l in (PH / "ocr.jsonl").read_text().splitlines()]
    det, meta = make()
    tot, over, false_masks, t0 = {}, [0, 0], 0, time.time()
    for d in docs:
        gold = json.loads((PH / "keys" / f"{d['id']}.gold.json").read_text())
        ocr_ranges = [(p["start"], p["end"]) for p in d["pages"] if p["ocr"]]
        DETECT_KW = {"address_detail": "street", "ocr_ranges": ocr_ranges, "threshold": 0.7}   # as Katip Yerel on scans
        masks = []
        for s, e, typ in det(d["text"]):
            page = next((p for p in d["pages"] if p["start"] <= s < p["end"]), None)
            if page and page["number"] == 0: masks += _attach_boxes(page, s, e, typ)
        if ink: masks += [m["box"] for m in d["ink_masks"] if m["page"] == 0]
        for g in gold["entities"]:
            t = tot.setdefault(g["entity_type"] + (" (signature)" if g.get("part") == "signature block" else ""), [0, 0])
            t[0] += 1; t[1] += _coverage(g["box"], masks) < 0.7
        for v in gold["visible"]:
            over[0] += 1; over[1] += _coverage(v["box"], masks) > 0.3
        gb = [g["box"] for g in gold["entities"] + gold["visible"]]
        false_masks += sum(not any(_overlaps(m, b) for b in gb) for m in masks)
    DETECT_KW = {"address_detail": "full"}
    n_ent, n_leak = sum(t[0] for t in tot.values()), sum(t[1] for t in tot.values())
    row = {"system": key, "name": name + (" + ink masks" if ink else ""), "track": "photo", "set": "photo v0.1.3 (60 synthetic phone photos, seed 3011)",
           "ocr": "Katip Otomatik (PaddleOCR PP-OCRv5 on handwriting, Tesseract tur otherwise), run once",
           "ink_masks": ink, "docs": len(docs), "leak_rate": n_leak / n_ent,
           "per_type": {k: {"n": n, "leaked": l} for k, (n, l) in tot.items()},
           "streets_over_masked": over[1], "streets": over[0], "false_masks_per_page": false_masks / len(docs),
           "detect_ms_per_page": round(1000 * (time.time() - t0) / len(docs), 0)}
    (RES / "photo").mkdir(parents=True, exist_ok=True)
    suffix = "" if ink == default_ink else ("+ink" if ink else "-noink")
    (RES / "photo" / f"{key}{suffix}.json").write_text(json.dumps(row, indent=1))
    return row

# ---- forms-id track: synthetic petitions / applications on re-typed public layouts (lab/legal/forms_build.py)
FORMS = HERE.parent / "data" / "bench" / "forms-id" / "public" / "forms-id.jsonl"

def run_forms(key):
    name, make = SYSTEMS[key]
    det, meta = make()
    gold = BB.load(FORMS if FORMS.exists() else HERE / "bench" / "forms" / "forms-id.jsonl")
    for r in gold[:10]: det(r["text"])
    t0 = time.time(); pred = [{"id": r["id"], "spans": [list(x[:3]) for x in det(r["text"])]} for r in gold]
    secs = time.time() - t0
    row = {"system": key, "name": name, "track": "forms-id", "set": "forms-id v0.1 (102 templates, 306 docs, seed 20261114)", **meta,
           "ms_per_doc": round(1000 * secs / len(gold), 1), **BS.score(gold, pred)}
    for d in ("results", "preds"): (HERE / "bench" / d / "forms").mkdir(parents=True, exist_ok=True)
    (HERE / "bench" / "preds" / "forms" / f"{key}.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pred))
    (RES / "forms" / f"{key}.json").write_text(json.dumps(row, indent=1, default=float))
    return row

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("systems", nargs="+"); ap.add_argument("--split", default="public")
    ap.add_argument("--rescore", action="store_true", help="re-score saved predictions instead of running the models")
    ap.add_argument("--track", default="text", choices=["text", "photo", "forms"], help="photo: score masks on the photo set (bench/photos)")
    ap.add_argument("--no-ink", action="store_true", help="photo track: leave out Katip's pen-ink masks")
    a = ap.parse_args()
    if a.track == "photo":
        for k in a.systems:
            try: r = run_photo(k, ink=False if a.no_ink else None)
            except Exception as e: print(f"skip {k}: {type(e).__name__}: {str(e)[:150]}"); continue
            print(f"{r['name']:60} leak {100 * r['leak_rate']:5.1f}%  " + "  ".join(f"{t} {x['leaked']}/{x['n']}" for t, x in r["per_type"].items()) +
                  f"  streets over-masked {r['streets_over_masked']}/{r['streets']}  false masks/page {r['false_masks_per_page']:.1f}", flush=True)
        sys.exit(0)
    if a.track == "forms":
        for k in a.systems:
            try: r = run_forms(k)
            except Exception as e: print(f"skip {k}: {type(e).__name__}: {str(e)[:150]}"); continue
            x = r["tracks"]["forms-id"]
            print(f"{r['name']:60} F2 {100 * x['f2']:5.1f}  R {100 * x['recall']:5.1f}  P {100 * x['precision']:5.1f}  leak {100 * x['leak_rate']:5.2f}%  " +
                  "  ".join(f"{t}:{100 * v['recall']:.0f}" for t, v in x["types"].items()), flush=True)
        sys.exit(0)
    for k in a.systems:
        try: r = rescore(k) if a.rescore else run(k, a.split)
        except Exception as e: print(f"skip {k}: {type(e).__name__}: {str(e)[:150]}"); continue
        print(f"{r['name']:55} KVKK-F2 {100 * r['KVKK-F2']:5.1f}  leak {100 * r['leak_rate']:5.2f}%  " +
              "  ".join(f"{t}:{100 * x['recall']:.0f}/{100 * x['precision']:.0f}" for t, x in r["tracks"].items() if x["recall"] == x["recall"]), flush=True)
