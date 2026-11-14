"""Fine-tune BERTurk (or any BERT-style model) as Katip's on-device tagger for names, addresses and
KVKK art. 6 health terms, then export it for the browser (ONNX fp32 + int8, transformers.js layout).

Runs on a Mac (Apple GPU via MPS), an NVIDIA GPU or CPU. Training data ships in ./data (synthetic
Turkish legal documents; the blind set's names never appear in training).

  python train_berturk.py                       # full run, ~30-60 min on an M1/M2/M3
  python train_berturk.py --limit 300 --epochs 1   # 3-minute smoke test
  python train_berturk.py --push <hf-user>/katip-mask-base   # also upload (after `hf auth login`)
  python train_berturk.py --real-text           # v2: also learn names from 17,967 real Turkish sentences
  python train_berturk.py --real-text --extra ../../lab/data/foreign/train_berturk_foreign.jsonl   # v3: + foreign clients

--real-text downloads Turkish Wiki NER (Altinok 2023, CC BY-SA 4.0) once into data/wikiner/ and mixes its
sentences into training, eight to a pseudo-document. Only its PERSON labels are used. On real text this
took BERTurk from 41% to 90% of names found (lab/04_distill_berturk.ipynb).

Labels are word-level BIO on each word's first sub-token, with the same word split the browser
uses (src/ner.js), so predicted spans map back to exact character offsets.
"""
import argparse, gzip, json, math, random, re, sys, time
from collections import defaultdict
from pathlib import Path

import regex, torch
from transformers import AutoModelForTokenClassification, AutoTokenizer, get_linear_schedule_with_warmup

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--base", default="dbmdz/bert-base-turkish-cased", help="Hugging Face id or local folder")
ap.add_argument("--types", default="PERSON,ADDRESS,HEALTH", help="Katip entity types to learn")
ap.add_argument("--out", default=str(HERE / "out"))
ap.add_argument("--epochs", type=int, default=3)
ap.add_argument("--bs", type=int, default=16)
ap.add_argument("--lr", type=float, default=3e-5)
ap.add_argument("--max-tokens", type=int, default=256)
ap.add_argument("--limit", type=int, default=0, help="use only the first N training docs (smoke test)")
ap.add_argument("--device", default="auto", help="auto | mps | cuda | cpu")
ap.add_argument("--no-onnx", action="store_true")
ap.add_argument("--real-text", action="store_true", help="mix in Turkish Wiki NER's real sentences (PERSON labels only)")
ap.add_argument("--extra", default="", help="extra training documents, JSONL {text, spans} (v3: lab/data/foreign/train_berturk_foreign.jsonl)")
ap.add_argument("--push", default="", help="Hugging Face model repo to upload to, e.g. you/katip-mask-base")
a = ap.parse_args()

random.seed(0); torch.manual_seed(0)
dev_name = a.device if a.device != "auto" else ("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
device = torch.device(dev_name)
TYPES = a.types.split(",")
SHORT = {"PERSON": "PER", "ADDRESS": "ADDR", "HEALTH": "HEALTH", "ORG": "ORG"}
LABELS = ["O"] + [f"{p}-{SHORT.get(t, t)}" for t in TYPES for p in ("B", "I")]
L2I = {l: i for i, l in enumerate(LABELS)}
WORD_RE = r"[\p{L}\p{N}][\p{L}\p{N}'’.-]*"
WORD = regex.compile(WORD_RE)
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

def load(name):
    with gzip.open(HERE / "data" / f"{name}.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f]
WIKINER_URL = "https://raw.githubusercontent.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset/main/Turkish-Wiki-NER-Dataset/{split}.conll"
NOSPACE = set(".,;:!?)]}%'’\"")

def wikiner(split):
    """Turkish Wiki NER sentences as {"text", "spans"} with PERSON spans only (the same conversion as lab/katiplab.py)."""
    raw = HERE / "data" / "wikiner" / f"{split}.conll"
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
    """Eight real sentences per pseudo-document, so they train like Katip's documents."""
    out_ = []
    for i in range(0, len(sents), k):
        text, spans = "", []
        for d in sents[i:i + k]:
            if text: text += "\n"
            o = len(text); text += d["text"]; spans += [[x + o, y + o, t] for x, y, t in d["spans"]]
        out_.append({"text": text, "spans": spans})
    return out_

train, dev = load("train"), load("dev")
if a.limit: train = train[:a.limit]; dev = dev[: max(40, a.limit // 10)]
tests = {n: load(n) for n in ("blind", "heldout", "negatives")}
if a.real_text:
    real = wikiner("train"); random.Random(0).shuffle(real)
    real = pack(real[: a.limit * 8] if a.limit else real)
    print(f"+ {len(real)} real pseudo-documents from Turkish Wiki NER ({sum(len(d['spans']) for d in real)} names)", flush=True)
    train = train + real
    tests["wiki dev"] = wikiner("dev")[: (200 if a.limit else None)]

if a.extra:
    extra = [json.loads(l) for l in open(a.extra, encoding="utf-8") if l.strip()]
    extra = [{"text": d["text"], "spans": [x for x in d["spans"] if x[2] in TYPES]} for d in extra]
    if a.limit: extra = extra[:a.limit]
    print(f"+ {len(extra)} extra documents from {a.extra} ({sum(len(d['spans']) for d in extra)} spans)", flush=True)
    train = train + extra

print(f"device {dev_name} · base {a.base} · labels {LABELS} · {len(train)} train docs", flush=True)
tok = AutoTokenizer.from_pretrained(a.base)
CLS, SEP, PAD, UNK = tok.cls_token_id, tok.sep_token_id, tok.pad_token_id, tok.unk_token_id
_cache = {}
def word_ids(w):
    if w not in _cache: _cache[w] = tok.encode(w, add_special_tokens=False) or [UNK]
    return _cache[w]

def words_of(text): return [(m.start(), m.end(), m.group()) for m in WORD.finditer(text)]

def word_labels(words, spans):
    lab = [0] * len(words)
    for s, e, t in spans:
        if t not in TYPES: continue
        first = True
        for i, (ws, we, _) in enumerate(words):
            if ws < e and we > s:
                lab[i] = L2I[("B-" if first else "I-") + SHORT.get(t, t)]; first = False
    return lab

def windows(words, labs=None, jitter=False):
    """Split a document into model inputs of at most max_tokens; returns (ids, label_ids, first_positions, word_range)."""
    out_, i = [], (random.randrange(0, 40) if jitter and len(words) > 80 else 0)
    i = min(i, max(0, len(words) - 1))
    while i < len(words):
        ids, ls, first, j = [CLS], [-100], [], i
        while j < len(words):
            wi = word_ids(words[j][2])
            if len(ids) + len(wi) >= a.max_tokens - 1: break
            first.append(len(ids)); ls += [labs[j] if labs else 0] + [-100] * (len(wi) - 1); ids += wi; j += 1
        if j == i: i += 1; continue
        ids.append(SEP); ls.append(-100)
        out_.append((ids, ls, first, (i, j))); i = j
    return out_

def collate(chunk):
    n = max(len(c[0]) for c in chunk)
    ids = torch.full((len(chunk), n), PAD); labs = torch.full((len(chunk), n), -100); mask = torch.zeros((len(chunk), n), dtype=torch.long)
    for r, c in enumerate(chunk):
        ids[r, :len(c[0])] = torch.tensor(c[0]); labs[r, :len(c[1])] = torch.tensor(c[1]); mask[r, :len(c[0])] = 1
    return ids.to(device), mask.to(device), labs.to(device)

model = AutoModelForTokenClassification.from_pretrained(
    a.base, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id=L2I, ignore_mismatched_sizes=True).to(device)
print("params", sum(p.numel() for p in model.parameters()), flush=True)

# ---------- inference + scoring (same merge rule as src/ner.js: B starts, I continues across spaces/commas)
@torch.no_grad()
def predict(text):
    model.eval()
    words = words_of(text); labels = ["O"] * len(words); probs = [1.0] * len(words)
    for ids, _, first, (i, j) in windows(words):
        x = torch.tensor([ids], device=device)
        lg = model(input_ids=x, attention_mask=torch.ones_like(x)).logits[0].float().softmax(-1).cpu()
        for k, pos in enumerate(first):
            p, c = lg[pos].max(0); labels[i + k] = LABELS[int(c)]; probs[i + k] = float(p)
    spans, cur = [], None
    for i, (s, e, _) in enumerate(words):
        l = labels[i]; typ = l[2:] if l != "O" else None
        gap = text[words[i - 1][1]:s] if i else ""
        if typ and cur and cur[3] == typ and l.startswith("I-") and re.fullmatch(r"[ \t,\n./:-]*" if typ == "ADDR" else r"[ \t,]*", gap):
            cur[1] = e; cur[2].append(probs[i])
        else:
            if cur: spans.append(cur)
            cur = [s, e, [probs[i]], typ] if typ else None
    if cur: spans.append(cur)
    inv = {v: k for k, v in SHORT.items()}
    res = []
    for s, e, ps, typ in spans:
        t = text[s:e]
        if typ == "PER":  # drop a Turkish case suffix after an apostrophe (Ahmet'in -> Ahmet)
            k = min([t.find(c) for c in "'’" if c in t] or [len(t)]); e = s + k
        res.append({"entity_type": inv.get(typ, typ), "start": s, "end": e, "text": text[s:e], "score": sum(ps) / len(ps)})
    return res

sq = lambda s: re.sub(r"\s+", "", s).casefold()
def matches(x, y): x, y = sq(x), sq(y); return y in x or (x in y and len(x) >= max(3, len(y) * 0.5))

def score(docs):
    per = defaultdict(lambda: {"gold": 0, "found": 0, "spans": 0, "false": 0}); t0 = time.time()
    for d in docs:
        pred = predict(d["text"]); gold = [(s, e, t) for s, e, t in d.get("spans", [])]
        for s, e, t in gold:
            if t not in TYPES: continue
            g = d["text"][s:e]; per[t]["gold"] += 1
            per[t]["found"] += any(p["entity_type"] == t and matches(p["text"], g) for p in pred)
        for p in pred:
            per[p["entity_type"]]["spans"] += 1
            per[p["entity_type"]]["false"] += not any(matches(p["text"], d["text"][s:e]) or matches(d["text"][s:e], p["text"]) for s, e, _ in gold)
    return {"docs": len(docs), "ms_per_doc": round((time.time() - t0) * 1000 / max(1, len(docs)), 1), "types": dict(per)}

def show(name, r):
    parts = [f"{t} {v['found']}/{v['gold']} ({v['found'] / max(1, v['gold']):.1%}), {v['false']} extra" for t, v in sorted(r["types"].items())]
    print(f"  {name:9} " + " · ".join(parts) + f"  [{r['ms_per_doc']} ms/doc]", flush=True)

# ---------- training
dev_seqs = None
steps_per_epoch = math.ceil(sum(len(windows(words_of(d["text"]))) for d in train) / a.bs)
opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps_per_epoch * a.epochs), steps_per_epoch * a.epochs)
t0 = time.time()
for ep in range(a.epochs):
    model.train()
    seqs = []
    for d in train:
        w = words_of(d["text"]); seqs += windows(w, word_labels(w, d.get("spans", [])), jitter=True)
    random.shuffle(seqs)
    for k in range(0, len(seqs), a.bs):
        ids, mask, labs = collate(seqs[k:k + a.bs])
        loss = model(input_ids=ids, attention_mask=mask, labels=labs).loss
        loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step(); opt.zero_grad()
        if (k // a.bs) % 50 == 0:
            print(f"epoch {ep + 1} step {k // a.bs}/{math.ceil(len(seqs) / a.bs)} loss {loss.item():.4f} ({time.time() - t0:.0f}s)", flush=True)
    print(f"epoch {ep + 1} done ({time.time() - t0:.0f}s)"); show("dev", score(dev))

results = {"base": a.base, "labels": LABELS, "real_text": a.real_text, "extra": a.extra, "epochs": a.epochs, "train_docs": len(train), "device": dev_name,
           "train_seconds": round(time.time() - t0), "sets": {}}
print("final scores (model alone, no rules):")
for n, docs in tests.items():
    r = score(docs); results["sets"][n] = r; show(n, r)
(out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))

# ---------- save for transformers.js: config.json + tokenizer at the root, ONNX under onnx/
model.eval().to("cpu")
model.save_pretrained(out); tok.save_pretrained(out)
cfg = json.loads((out / "config.json").read_text())
cfg["katip"] = {"word_regex": WORD_RE, "max_tokens": a.max_tokens, "labels": "word-level BIO on first sub-token", "types": TYPES}
(out / "config.json").write_text(json.dumps(cfg, indent=1, ensure_ascii=False))
if not a.no_onnx:
    (out / "onnx").mkdir(exist_ok=True)
    class Wrap(torch.nn.Module):
        def __init__(s, m): super().__init__(); s.m = m
        def forward(s, input_ids, attention_mask, token_type_ids):
            return s.m(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids).logits
    x = torch.tensor([[CLS, 10, 11, SEP]])
    torch.onnx.export(Wrap(model), (x, torch.ones_like(x), torch.zeros_like(x)), str(out / "onnx/model.onnx"),
                      input_names=["input_ids", "attention_mask", "token_type_ids"], output_names=["logits"],
                      dynamic_axes={k: {0: "batch", 1: "seq"} for k in ("input_ids", "attention_mask", "token_type_ids", "logits")},
                      opset_version=17, dynamo=False)
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(str(out / "onnx/model.onnx"), str(out / "onnx/model_quantized.onnx"), weight_type=QuantType.QInt8)
    print("onnx", {p.name: f"{p.stat().st_size / 1e6:.1f} MB" for p in (out / "onnx").iterdir()})

if a.push:
    from huggingface_hub import HfApi
    api = HfApi(); api.create_repo(a.push, repo_type="model", exist_ok=True)
    card = HERE / "MODEL_CARD.md"
    if card.exists() and not (out / "README.md").exists(): (out / "README.md").write_text(card.read_text())
    api.upload_folder(repo_id=a.push, folder_path=str(out), repo_type="model", commit_message=f"fine-tune of {a.base}" + (" with real text" if a.real_text else "") + (" + foreign clients (v3)" if a.extra else ""))
    print(f"uploaded: https://huggingface.co/{a.push}")
print(f"done in {time.time() - t0:.0f}s → {out}")
