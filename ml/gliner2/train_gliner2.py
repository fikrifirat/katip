"""Fine-tune a GLiNER2 model on Katip Mask Base v2's training data, so the only difference from Base is the model.

Same data as ml/berturk/train_berturk.py --real-text: Katip's 8,000 synthetic legal documents plus Turkish Wiki NER
train (PERSON only, 8 sentences per pseudo-document), same entity types (PERSON, ADDRESS, HEALTH; Katip's rules
handle IDs, phones, IBANs). GLiNER2 learns from mention strings, so spans become {"person": [...], ...}; a type
with no mention is a negative. Model-alone scores on Base v2's own test sets (blind, heldout, wiki dev) use the
same lenient match as train_berturk.py, so the two runs print comparable numbers.

  python train_gliner2.py --base fastino/gliner2-privacy-filter-PII-multi --out out_gliner2 [--limit 300 --epochs 1]
"""
import argparse, gzip, json, random, sys, time
from pathlib import Path

HERE = Path(__file__).parent
BERT = HERE.parent / "berturk"
sys.path.insert(0, str(BERT))

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="fastino/gliner2-privacy-filter-PII-multi")
ap.add_argument("--out", default=str(HERE / "out_gliner2"))
ap.add_argument("--epochs", type=int, default=3)
ap.add_argument("--bs", type=int, default=8)
ap.add_argument("--encoder-lr", type=float, default=1e-5)
ap.add_argument("--task-lr", type=float, default=5e-4)
ap.add_argument("--limit", type=int, default=0, help="smoke test: first N docs")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--no-real-text", action="store_true")
ap.add_argument("--prepare-only", action="store_true", help="write the training JSONL and stop (no torch needed)")
a = ap.parse_args()

TYPES = {"PERSON": "person", "ADDRESS": "address", "HEALTH": "health condition"}
DESC = {"person": "a person's name (first name, surname or full name)",
        "address": "a postal address or part of one (street, building, door or flat number, district, city)",
        "health condition": "an illness, diagnosis, disability, treatment or other health information about a person"}

def load(name):
    with gzip.open(BERT / "data" / f"{name}.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f]

WIKINER_URL = "https://raw.githubusercontent.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset/main/Turkish-Wiki-NER-Dataset/{split}.conll"
NOSPACE = set(".,;:!?)]}%'’\"")

def wikiner(split):
    """Same conversion as train_berturk.py: PERSON spans only."""
    raw = BERT / "data" / "wikiner" / f"{split}.conll"
    if not raw.exists():
        import urllib.request
        raw.parent.mkdir(parents=True, exist_ok=True); urllib.request.urlretrieve(WIKINER_URL.format(split=split), raw)
    sents, cur = [], []
    for line in raw.open(encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            if cur: sents.append(cur); cur = []
            continue
        cur.append(line.split("\t") if "\t" in line else line.rsplit(" ", 1))
    if cur: sents.append(cur)
    docs = []
    for s_ in sents:
        text, spans, span = "", [], None
        for w, t in s_:
            if text and w not in NOSPACE: text += " "
            b0 = len(text); text += w
            if t.startswith("B-") or (t.startswith("I-") and not (span and span[2] == t[2:])):
                if span: spans.append(span)
                span = [b0, len(text), t[2:]]
            elif t.startswith("I-"): span[1] = len(text)
            else:
                if span: spans.append(span)
                span = None
        if span: spans.append(span)
        docs.append({"text": text, "spans": [[x, y, "PERSON"] for x, y, t in spans if t in ("PERSON", "PER")]})
    return docs

def pack(sents, k=8):
    out_ = []
    for i in range(0, len(sents), k):
        text, spans = "", []
        for d in sents[i:i + k]:
            if text: text += "\n"
            o = len(text); text += d["text"]; spans += [[x + o, y + o, t] for x, y, t in d["spans"]]
        out_.append({"text": text, "spans": spans})
    return out_

def record(d):
    ents = {v: [] for v in TYPES.values()}
    for s, e, t in d.get("spans", []):
        if t in TYPES:
            m = d["text"][s:e].strip()
            if m and m not in ents[TYPES[t]]: ents[TYPES[t]].append(m)
    return {"input": d["text"], "output": {"entities": ents, "entity_descriptions": DESC}}

random.seed(a.seed)
train, dev = load("train"), load("dev")
if a.limit: train, dev = train[:a.limit], dev[:max(40, a.limit // 10)]
tests = {n: load(n) for n in ("blind", "heldout")}
if not a.no_real_text:
    real = wikiner("train"); random.Random(a.seed).shuffle(real)
    real = pack(real[: a.limit * 8] if a.limit else real)
    print(f"+ {len(real)} real pseudo-documents from Turkish Wiki NER ({sum(len(d['spans']) for d in real)} names)", flush=True)
    train = train + real
    tests["wiki dev"] = wikiner("dev")[: (200 if a.limit else None)]
random.shuffle(train)
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
for name, docs in (("train", train), ("dev", dev)):
    with open(out / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for d in docs: f.write(json.dumps(record(d), ensure_ascii=False) + "\n")
print(f"{len(train)} train docs, {len(dev)} dev docs -> {out}/train.jsonl", flush=True)
if a.prepare_only:
    sys.exit(0)

import torch
from gliner2 import GLiNER2
from gliner2.training.trainer import GLiNER2Trainer, TrainingConfig

model = GLiNER2.from_pretrained(a.base)
cfg = TrainingConfig(output_dir=str(out / "ckpt"), num_epochs=a.epochs, batch_size=a.bs, eval_batch_size=8,
                     encoder_lr=a.encoder_lr, task_lr=a.task_lr, eval_strategy="epoch", save_best=True,
                     logging_steps=50, seed=a.seed, num_workers=2, fp16=torch.cuda.is_available())
t0 = time.time()
GLiNER2Trainer(model=model, config=cfg).train(train_data=str(out / "train.jsonl"), eval_data=str(out / "dev.jsonl"))
secs = round(time.time() - t0)

# reload the best checkpoint (falls back to the final one) and score the model alone, like train_berturk.py
best = next((p for p in (out / "ckpt" / "best", out / "ckpt" / "final") if p.exists()), None)
model = GLiNER2.from_pretrained(str(best)) if best else model
model.eval()
labels = list(TYPES.values()); inv = {v: k for k, v in TYPES.items()}

def predict(text):
    r = model.extract_entities(text, labels, threshold=0.5, include_spans=True)
    return [(e["start"], e["end"], inv[t]) for t, es in (r.get("entities") or {}).items() for e in es if t in inv]

def sq(x): return " ".join(x.split()).casefold()
def matches(x, y): x, y = sq(x), sq(y); return y in x or (x in y and len(x) >= max(3, len(y) * 0.5))

def score(docs):
    r = {}
    for t in TYPES:
        tp = fn = fp = 0
        for d in docs:
            gold = [d["text"][s:e] for s, e, tt in d.get("spans", []) if tt == t]
            pred = [d["text"][s:e] for s, e, tt in predict(d["text"]) if tt == t]
            tp += sum(any(matches(p, g) for p in pred) for g in gold); fn += sum(not any(matches(p, g) for p in pred) for g in gold)
            fp += sum(not any(matches(p, g) for g in gold) for p in pred)
        if tp + fn: r[t] = {"recall": round(tp / (tp + fn), 4), "precision": round(tp / max(1, tp + fp), 4), "gold": tp + fn}
    return r

results = {"base": a.base, "epochs": a.epochs, "train_docs": len(train), "train_seconds": secs,
           "checkpoint": str(best), "sets": {n: score(docs) for n, docs in tests.items()}}
(out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
print(json.dumps(results["sets"], indent=1), flush=True)
final = out / "model"
model.save_pretrained(str(final))
print("saved", final, flush=True)
