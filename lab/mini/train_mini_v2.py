"""Katip Mask Mini v2: start from a model that already reads Turkish, shrink it, let Base teach it.

Mini v1 (trained from scratch, 29 MB) reached only ~55% of names on real Wikipedia text: ~15k training documents
are not enough to learn Turkish from nothing. Here the student starts from DistilBERTurk (dbmdz, MIT; 6 layers,
pretrained on general Turkish), then:
  1. vocabulary pruning: keep only the word pieces our text actually uses (plus every single character, so no
     word ever becomes [UNK]); the 32k x 768 embedding table is most of the model's size;
  2. layer dropping: keep some of the 6 transformer layers;
  3. knowledge distillation from Katip Mask Base, on the same training text as Mini v1.
Candidates are chosen on dev (Wiki NER dev + synthetic heldout); test sets are scored once at the end.

  MODE=smoke python mini/train_mini_v2.py      # 5 min
  python mini/train_mini_v2.py                 # ~1-1.5 h on a T4
"""
import json, math, os, random, sys, time
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import katiplab as K  # noqa: E402
import distill as D  # noqa: E402

MODE = os.environ.get("MODE", "full")
INIT = os.environ.get("INIT", "dbmdz/distilbert-base-turkish-cased")
TEACHER = os.environ.get("TEACHER", "f1k/katip-mask-base")
NAME = os.environ.get("NAME", "katip-mask-mini-v2")
# name: (layers kept, vocabulary size). Sizes are int8 estimates.
CANDS = {"L3-V12k": ([0, 2, 5], 12000),     # ~31 MB
         "L2-V12k": ([0, 5], 12000),        # ~24 MB
         "L3-V8k": ([0, 2, 5], 8000)}       # ~28 MB
if os.environ.get("CANDS"): CANDS = {k: v for k, v in CANDS.items() if k in os.environ["CANDS"].split(",")}
if MODE == "smoke": CANDS = dict(list(CANDS.items())[:1])
EPOCHS = int(os.environ.get("EPOCHS", 4 if MODE != "smoke" else 1))
LR = float(os.environ.get("LR", "1e-4"))
OUT = HERE / ("runs" if MODE != "smoke" else "runs_smoke"); OUT.mkdir(exist_ok=True)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("tm", HERE / "train_mini.py")
# reuse the exact training text of Mini v1 (without running its training)
src = (HERE / "train_mini.py").read_text().split("# 2 · teacher")[0]
ns = {"__file__": str(HERE / "train_mini.py"), "__name__": "mini_text"}
os.environ.setdefault("MODE", MODE)
exec(compile(src, "train_mini.py", "exec"), ns)
docs = ns["docs"]
log(f"{len(docs)} training documents")

# teacher
if TEACHER == "none":
    soft = None
else:
    tdir = TEACHER if Path(TEACHER).is_dir() else __import__("huggingface_hub").snapshot_download(
        TEACHER, allow_patterns=["config.json", "tokenizer*", "vocab.txt", "special_tokens_map.json", "*.safetensors"])
    soft = D.soft_labels(tdir, docs, device="auto", bs=64, log=log)

import torch, torch.nn.functional as F  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402
from transformers import AutoModelForTokenClassification, AutoTokenizer, PreTrainedTokenizerFast  # noqa: E402

idir = INIT if Path(INIT).is_dir() else __import__("huggingface_hub").snapshot_download(INIT)
base_tok = AutoTokenizer.from_pretrained(idir)
base_json = json.loads(base_tok.backend_tokenizer.to_str())
old_vocab = base_json["model"]["vocab"]                       # token -> id
specials = [t for t in ("[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]") if t in old_vocab]

# token frequencies over the training text + dev (dev is not labels, only which word pieces exist)
freq = Counter()
dev_sets = {"wiki dev": K.load_wiki("dev"), "heldout": K.load_synth("heldout")}
if MODE == "smoke": dev_sets = {k: v[:100] for k, v in dev_sets.items()}
for d in docs + [x for v in dev_sets.values() for x in v]:
    for m in D.WORD.finditer(d["text"]):
        freq.update(base_tok.convert_ids_to_tokens(base_tok.encode(m.group(), add_special_tokens=False)))
singles = [t for t in old_vocab if len(t) == 1 or (t.startswith("##") and len(t) == 3)]
log(f"base vocabulary {len(old_vocab)}, pieces used {len(freq)}, single characters {len(singles)}")


def pruned(vsize):
    keep = list(dict.fromkeys(specials + singles + [t for t, _ in freq.most_common()]))[:vsize]
    keep = list(dict.fromkeys(specials + singles + keep))           # never drop specials/characters
    new = {t: i for i, t in enumerate(keep)}
    tj = json.loads(json.dumps(base_json)); tj["model"]["vocab"] = new
    for at in tj.get("added_tokens", []): at["id"] = new.get(at["content"], at["id"])
    if tj.get("post_processor") and "special_tokens" in tj["post_processor"]:
        for k, v in tj["post_processor"]["special_tokens"].items(): v["ids"] = [new[k]]
    return Tokenizer.from_str(json.dumps(tj)), [old_vocab[t] for t in keep]


def build(layers, vsize):
    tok, rows = pruned(vsize)
    model = AutoModelForTokenClassification.from_pretrained(idir, num_labels=3, id2label=dict(enumerate(D.LABELS)),
                                                            label2id={l: i for i, l in enumerate(D.LABELS)})
    emb = model.get_input_embeddings()
    new = torch.nn.Embedding(len(rows), emb.weight.shape[1]); new.weight.data = emb.weight.data[rows].clone()
    model.set_input_embeddings(new); model.config.vocab_size = len(rows)
    body = model.base_model
    tl = body.transformer.layer if hasattr(body, "transformer") else body.encoder.layer
    kept = torch.nn.ModuleList([tl[i] for i in layers])
    if hasattr(body, "transformer"): body.transformer.layer = kept; model.config.n_layers = len(layers)
    else: body.encoder.layer = kept; model.config.num_hidden_layers = len(layers)
    return tok, model


def train(name, layers, vsize):
    out = OUT / f"{NAME}-{name}"; out.mkdir(exist_ok=True)
    random.seed(0); np.random.seed(0); torch.manual_seed(0)
    tok, model = build(layers, vsize)
    dev = D._device("auto"); model.to(dev)
    CLS, SEP, PAD, UNK = (tok.token_to_id(t) for t in ("[CLS]", "[SEP]", "[PAD]", "[UNK]"))
    cache = {}
    def enc(w):
        if w not in cache: cache[w] = tok.encode(w, add_special_tokens=False).ids or [UNK]
        return cache[w]
    prepared = [(*D._word_labels(d), None if soft is None else soft[i]) for i, d in enumerate(docs)]
    def sequences(jitter):
        seqs = []
        for words, lab, sl in prepared:
            start = random.randrange(0, 40) if jitter and len(words) > 80 else 0
            for i, j, ids, first in D._windows(words, enc, 256, min(start, max(0, len(words) - 1))):
                y = [-100] * (len(ids) + 2); t = np.zeros((len(ids) + 2, 3), dtype=np.float32); has = np.zeros(len(ids) + 2, dtype=bool)
                for k, pos in enumerate(first):
                    y[pos] = lab[i + k]
                    if sl is not None: t[pos] = sl[i + k]; has[pos] = True
                seqs.append(([CLS] + ids + [SEP], y, t, has))
        return seqs
    BS = 32; steps = EPOCHS * math.ceil(len(sequences(False)) / BS)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=steps + 50, pct_start=0.1)
    log(f"{name}: {sum(p.numel() for p in model.parameters()):,} params, layers {layers}, vocab {len(tok.get_vocab())}, {steps} steps")
    t0, step, T = time.time(), 0, 2.0; model.train()
    for ep in range(EPOCHS):
        seqs = sequences(True); random.shuffle(seqs)
        for k in range(0, len(seqs), BS):
            ch = seqs[k:k + BS]; n = max(len(c[0]) for c in ch)
            ids = torch.full((len(ch), n), PAD); y = torch.full((len(ch), n), -100); m = torch.zeros((len(ch), n), dtype=torch.long)
            tl = torch.zeros((len(ch), n, 3)); has = torch.zeros((len(ch), n), dtype=torch.bool)
            for r, (a, b, t, hs) in enumerate(ch):
                ids[r, :len(a)] = torch.tensor(a); y[r, :len(b)] = torch.tensor(b); m[r, :len(a)] = 1
                tl[r, :len(a)] = torch.from_numpy(t); has[r, :len(a)] = torch.from_numpy(hs)
            ids, y, m, tl, has = ids.to(dev), y.to(dev), m.to(dev), tl.to(dev), has.to(dev)
            logits = model(input_ids=ids, attention_mask=m).logits
            loss = F.cross_entropy(logits.reshape(-1, 3), y.reshape(-1), ignore_index=-100)
            if soft is not None and has.any():
                kd = F.kl_div(F.log_softmax(logits[has] / T, -1), F.softmax(tl[has] / T, -1), reduction="batchmean") * T * T
                loss = 0.5 * loss + 0.5 * kd
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); opt.zero_grad()
            if step < steps + 49: sched.step()
            step += 1
        log(f"  epoch {ep + 1}/{EPOCHS} loss {loss.item():.4f} ({time.time() - t0:.0f}s)")
    model = model.cpu().eval(); model.save_pretrained(out)
    tok.save(str(out / "tokenizer.json"))
    PreTrainedTokenizerFast(tokenizer_file=str(out / "tokenizer.json"), cls_token="[CLS]", sep_token="[SEP]", pad_token="[PAD]",
                            unk_token="[UNK]", mask_token="[MASK]", model_max_length=256).save_pretrained(out)
    tok.save(str(out / "tokenizer.json"))
    extra = {"role": "mini-v2", "init": INIT, "layers": layers, "vocab": len(tok.get_vocab()), "teacher": TEACHER, "epochs": EPOCHS}
    mb = D._export(model, out, CLS, SEP, 256, extra)
    return out, mb, round(time.time() - t0)


cands = []
for name, (layers, vsize) in CANDS.items():
    out, mb, secs = train(name, layers, vsize)
    trust, row = D.choose_trust(D.dev_table(K.Tagger(out), dev_sets))
    cands.append({"name": name, "dir": str(out), "int8_mb": mb, "seconds": secs, "trust": trust,
                  **{k: row[k] for k in ("wiki dev f2", "wiki dev recall", "wiki dev precision", "heldout recall")}})
    (out / "katip_trust.json").write_text(json.dumps({"trust": trust}))
    log(json.dumps(cands[-1]))

ok = [c for c in cands if c["int8_mb"] <= 35] or cands
best = max(c["wiki dev f2"] for c in ok)
win = sorted([c for c in ok if c["wiki dev f2"] >= best - 0.005], key=lambda c: c["int8_mb"])[0]
log("winner:", win["name"], win["int8_mb"], "MB, trust", win["trust"])
tg = K.Tagger(Path(win["dir"]))
test_sets = {"wiki test": K.load_wiki("test"), "blind": K.load_synth("blind"), "negatives": K.load_synth("negatives")}
if MODE == "smoke": test_sets = {k: v[:100] for k, v in test_sets.items()}
res = K.evaluate("mini-v2", K.pipeline(tg, trust=win["trust"]), test_sets)
summary = {k: {m: v for m, v in r.items() if not m.startswith("_")} for k, r in res.items()}
(OUT / f"{NAME}_results.json").write_text(json.dumps({"mode": MODE, "init": INIT, "teacher": TEACHER, "candidates": cands,
                                                      "winner": win, "test": summary}, indent=1, default=float))
log(json.dumps(summary, default=float)[:600])
