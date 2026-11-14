"""Knowledge distillation for Katip's name tagger: a big teacher (BERTurk) teaches a tiny student.

  train_teacher()  fine-tune BERTurk (or any BERT-style model) for names on synthetic + real text
  soft_labels()    run the teacher over the training texts and keep its per-word beliefs (logits)
  train_student()  train a small BERT from scratch on gold labels + the teacher's beliefs

Every model folder this writes works both with Hugging Face (`from_pretrained(folder)`) and with
`katiplab.Tagger(folder)` (config.json with the `katip` block, tokenizer.json, onnx/model_quantized.onnx).

Why distillation can help (Hinton et al., 2015): a gold label says only "name" or "not a name". The
teacher's probabilities also say *how* name-like a word is ("Deniz" 0.6, "önemli" 0.001), which is
more information per example than the label, so a small student learns more from the same text.
"""
from __future__ import annotations

import json, math, os, random, time
from pathlib import Path

import numpy as np
import regex

import katiplab as K

LABELS = ["O", "B-PER", "I-PER"]
WORD = regex.compile(K.WORD_RE)

ARCH = {  # name: (hidden, layers, heads, intermediate); vocab 16k unless train_student gets another
    "tiny":  (128, 2, 2, 512),     # today's katip-tr-name-tagger-tiny, ~2.6 MB int8
    "mini":  (192, 3, 3, 768),     # ~4.6 MB
    "small": (256, 4, 4, 1024),    # ~7.6 MB
    "mini-a": (384, 4, 6, 1536),   # Katip Mask Mini candidates (15-30 MB int8 with a 32k vocab)
    "mini-b": (384, 6, 6, 1536),
    "mini-c": (512, 4, 8, 2048),
}


def _device(name="auto"):
    import torch
    if name != "auto": return torch.device(name)
    return torch.device("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")


def _word_labels(doc):
    text = doc["text"]; spans = [s for s in doc["spans"] if s[2] == "PERSON"]
    words = [(m.start(), m.end(), m.group()) for m in WORD.finditer(text)]
    lab = []
    for s, e, _ in words:
        l = 0
        for a, b, _t in spans:
            if s < b and e > a: l = 1 if s <= a else 2; break
        lab.append(l)
    return words, lab


def _windows(words, encode, maxtok, start=0):
    """Split a document's words into windows of < maxtok sub-tokens. Yields (first word, last word + 1, ids, first-subtoken positions)."""
    i = start
    while i < len(words):
        ids, first, j = [], [], i
        while j < len(words):
            wi = encode(words[j][2])
            if len(ids) + len(wi) + 2 >= maxtok: break
            first.append(len(ids) + 1); ids += wi; j += 1
        if j == i: i += 1; continue
        yield i, j, ids, first
        i = j


def _export(model, out, cls_id, sep_id, maxtok, extra):
    """config.json with the katip block + ONNX fp32 + int8 (same layout as the browser expects)."""
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic
    model = model.to("cpu").eval()
    cfg = model.config.to_dict(); cfg["architectures"] = [type(model).__name__]
    cfg["katip"] = {"word_regex": K.WORD_RE, "max_tokens": maxtok, "labels": "word-level BIO on first sub-token", "lab": extra}
    (out / "config.json").write_text(json.dumps(cfg, indent=1, default=str))

    import inspect
    takes_tt = "token_type_ids" in inspect.signature(model.forward).parameters   # DistilBERT has no segment ids

    class Wrap(torch.nn.Module):
        def __init__(s, m): super().__init__(); s.m = m
        def forward(s, input_ids, attention_mask, token_type_ids=None):
            kw = {"token_type_ids": token_type_ids} if takes_tt else {}
            return s.m(input_ids=input_ids, attention_mask=attention_mask, **kw).logits
    (out / "onnx").mkdir(exist_ok=True)
    x = torch.tensor([[cls_id, 10, 11, sep_id]])
    names = ["input_ids", "attention_mask"] + (["token_type_ids"] if takes_tt else [])
    args = (x, torch.ones_like(x)) + ((torch.zeros_like(x),) if takes_tt else ())
    torch.onnx.export(Wrap(model), args, str(out / "onnx/model.onnx"), input_names=names, output_names=["logits"],
                      dynamic_axes={k: {0: "batch", 1: "seq"} for k in names + ["logits"]}, opset_version=17, dynamo=False)
    import logging; logging.getLogger().setLevel(logging.ERROR)
    quantize_dynamic(str(out / "onnx/model.onnx"), str(out / "onnx/model_quantized.onnx"), weight_type=QuantType.QInt8)
    return round((out / "onnx/model_quantized.onnx").stat().st_size / 1e6, 2)


# ---------------------------------------------------------------------------------------------- teacher
def train_teacher(out, base="dbmdz/bert-base-turkish-cased", real_docs=(), synth_docs=None, epochs=2, bs=16, lr=3e-5,
                  maxtok=256, device="auto", seed=0, log=print) -> dict:
    """Fine-tune a pretrained BERT (default BERTurk) to tag names, on synthetic + real documents."""
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer, get_linear_schedule_with_warmup
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    random.seed(seed); torch.manual_seed(seed); dev = _device(device)
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForTokenClassification.from_pretrained(base, num_labels=3, id2label=dict(enumerate(LABELS)),
                                                            label2id={l: i for i, l in enumerate(LABELS)}, ignore_mismatched_sizes=True).to(dev)
    CLS, SEP, PAD, UNK = tok.cls_token_id, tok.sep_token_id, tok.pad_token_id, tok.unk_token_id
    cache = {}
    def enc(w):
        if w not in cache: cache[w] = tok.encode(w, add_special_tokens=False) or [UNK]
        return cache[w]
    docs = list(K.load_synth("train") if synth_docs is None else synth_docs) + list(real_docs)
    seqs = []
    for d in docs:
        words, lab = _word_labels(d)
        for i, j, ids, first in _windows(words, enc, maxtok):
            y = [-100] * (len(ids) + 2)
            for k, pos in enumerate(first): y[pos] = lab[i + k]
            seqs.append(([CLS] + ids + [SEP], y))
    steps = epochs * math.ceil(len(seqs) / bs)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    log(f"teacher {base} on {dev}: {len(docs)} docs, {len(seqs)} windows, {steps} steps")
    t0 = time.time(); model.train(); step = 0
    for ep in range(epochs):
        random.shuffle(seqs)
        for k in range(0, len(seqs), bs):
            chunk = seqs[k:k + bs]; n = max(len(a) for a, _ in chunk)
            ids = torch.full((len(chunk), n), PAD); y = torch.full((len(chunk), n), -100); m = torch.zeros((len(chunk), n), dtype=torch.long)
            for r, (a, b) in enumerate(chunk): ids[r, :len(a)] = torch.tensor(a); y[r, :len(b)] = torch.tensor(b); m[r, :len(a)] = 1
            loss = model(input_ids=ids.to(dev), attention_mask=m.to(dev), labels=y.to(dev)).loss
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step(); opt.zero_grad(); step += 1
            if step % 200 == 0: log(f"  step {step}/{steps}  loss {loss.item():.4f}  ({time.time() - t0:.0f}s)")
        log(f"  epoch {ep + 1}/{epochs} done ({time.time() - t0:.0f}s)")
    model.save_pretrained(out); tok.save_pretrained(out)
    mb = _export(model, out, CLS, SEP, maxtok, {"role": "fine-tuned", "base": str(base), "real_docs": len(real_docs), "epochs": epochs})
    info = {"dir": str(out.relative_to(K.ROOT)) if out.is_relative_to(K.ROOT) else str(out), "base": str(base),
            "params": sum(p.numel() for p in model.parameters()), "seconds": round(time.time() - t0), "int8_mb": mb}
    (out / "train_info.json").write_text(json.dumps(info, indent=1)); log(f"  saved {out.name}: int8 {mb} MB, {info['seconds']} s")
    return info


def soft_labels(teacher_dir, docs, device="auto", bs=32, maxtok=256, log=print) -> list[np.ndarray]:
    """The teacher's log-probabilities over [O, B-PER, I-PER] for every word of every doc (one array per doc).
    Teachers with more labels (e.g. ADDR, HEALTH) are collapsed: everything that is not B-/I-PER counts as O."""
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    dev = _device(device)
    tok = AutoTokenizer.from_pretrained(teacher_dir)
    model = AutoModelForTokenClassification.from_pretrained(teacher_dir).to(dev).eval()
    id2l = model.config.id2label
    b = [i for i, l in id2l.items() if l in ("B-PER", "B-PERSON")]; ii = [i for i, l in id2l.items() if l in ("I-PER", "I-PERSON")]
    cache = {}
    def enc(w):
        if w not in cache: cache[w] = tok.encode(w, add_special_tokens=False) or [tok.unk_token_id]
        return cache[w]
    jobs, outs = [], []
    for di, d in enumerate(docs):
        words = [(m.start(), m.end(), m.group()) for m in WORD.finditer(d["text"])]
        outs.append(np.zeros((len(words), 3), dtype=np.float32))
        for i, j, ids, first in _windows(words, enc, maxtok): jobs.append((di, i, [tok.cls_token_id] + ids + [tok.sep_token_id], first))
    jobs.sort(key=lambda j: len(j[2]))   # similar lengths together: less padding
    t0 = time.time()
    with torch.no_grad():
        for k in range(0, len(jobs), bs):
            chunk = jobs[k:k + bs]; n = max(len(j[2]) for j in chunk)
            ids = torch.full((len(chunk), n), tok.pad_token_id); m = torch.zeros((len(chunk), n), dtype=torch.long)
            for r, j in enumerate(chunk): ids[r, :len(j[2])] = torch.tensor(j[2]); m[r, :len(j[2])] = 1
            p = model(input_ids=ids.to(dev), attention_mask=m.to(dev)).logits.float().softmax(-1).cpu().numpy()
            for r, (di, i, _, first) in enumerate(chunk):
                pb, pi = p[r, first][:, b].sum(-1), p[r, first][:, ii].sum(-1)
                three = np.stack([np.clip(1 - pb - pi, 1e-6, 1), np.clip(pb, 1e-6, 1), np.clip(pi, 1e-6, 1)], -1)
                outs[di][i:i + len(first)] = np.log(three)
            if (k // bs) % 200 == 0: log(f"  teacher labels: {k}/{len(jobs)} windows ({time.time() - t0:.0f}s)")
    return outs


# ---------------------------------------------------------------------------------------------- student
def train_student(out, docs, soft=None, arch="tiny", kd_weight=0.5, temperature=2.0, epochs=5, seed=0, maxtok=256,
                  vocab=16000, log=print, device="cpu", lr=1e-3, bs=32) -> dict:
    """Train a BERT tagger from scratch, like ml/train.py. With `soft` (teacher log-probs per doc, from soft_labels;
    None entries allowed), the loss is (1 - kd_weight) * cross-entropy(gold) + kd_weight * T² * KL(teacher_T || student_T).
    kd_weight=0 reproduces plain training."""
    import torch, torch.nn.functional as F
    from tokenizers import Tokenizer, decoders, models, normalizers, pre_tokenizers, processors, trainers
    from transformers import BertConfig, BertForTokenClassification, PreTrainedTokenizerFast

    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.set_num_threads(min(8, os.cpu_count() or 4))
    tok = Tokenizer(models.WordPiece(unk_token="[UNK]"))
    tok.normalizer = normalizers.NFC(); tok.pre_tokenizer = pre_tokenizers.BertPreTokenizer(); tok.decoder = decoders.WordPiece()
    tok.train_from_iterator((d["text"] for d in docs), trainers.WordPieceTrainer(
        vocab_size=vocab, min_frequency=2, special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]))
    CLS, SEP, PAD, UNK = (tok.token_to_id(t) for t in ("[CLS]", "[SEP]", "[PAD]", "[UNK]"))
    tok.post_processor = processors.TemplateProcessing(single="[CLS] $A [SEP]", special_tokens=[("[CLS]", CLS), ("[SEP]", SEP)])
    cache = {}
    def enc(w):
        if w not in cache: cache[w] = tok.encode(w, add_special_tokens=False).ids or [UNK]
        return cache[w]

    prepared = []
    for di, d in enumerate(docs):
        words, lab = _word_labels(d)
        prepared.append((words, lab, None if soft is None else soft[di]))

    def sequences(jitter):
        seqs = []
        for words, lab, sl in prepared:
            start = random.randrange(0, 40) if jitter and len(words) > 80 else 0
            for i, j, ids, first in _windows(words, enc, maxtok, min(start, max(0, len(words) - 1))):
                y = [-100] * (len(ids) + 2); t = np.zeros((len(ids) + 2, 3), dtype=np.float32); has = np.zeros(len(ids) + 2, dtype=bool)
                for k, pos in enumerate(first):
                    y[pos] = lab[i + k]
                    if sl is not None: t[pos] = sl[i + k]; has[pos] = True
                seqs.append(([CLS] + ids + [SEP], y, t, has))
        return seqs

    h, L, H, I = ARCH[arch] if isinstance(arch, str) else arch
    cfg = BertConfig(vocab_size=tok.get_vocab_size(), hidden_size=h, num_hidden_layers=L, num_attention_heads=H, intermediate_size=I,
                     max_position_embeddings=maxtok, num_labels=3, id2label=dict(enumerate(LABELS)), label2id={l: i for i, l in enumerate(LABELS)})
    dev = _device(device)
    model = BertForTokenClassification(cfg).to(dev)
    BS = bs; n_seqs = len(sequences(False)); steps = epochs * math.ceil(n_seqs / BS)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps + 50, pct_start=0.1)
    log(f"student {arch}: {sum(p.numel() for p in model.parameters()):,} params · {len(docs)} docs · {n_seqs} windows · "
        f"KD weight {kd_weight if soft is not None else 0} · T {temperature}")
    t0, step = time.time(), 0; model.train(); T = temperature
    for ep in range(epochs):
        seqs = sequences(True); random.shuffle(seqs)
        for k in range(0, len(seqs), BS):
            chunk = seqs[k:k + BS]; n = max(len(c[0]) for c in chunk)
            ids = torch.full((len(chunk), n), PAD); y = torch.full((len(chunk), n), -100); m = torch.zeros((len(chunk), n), dtype=torch.long)
            tl = torch.zeros((len(chunk), n, 3)); has = torch.zeros((len(chunk), n), dtype=torch.bool)
            for r, (a, b, t, hs) in enumerate(chunk):
                ids[r, :len(a)] = torch.tensor(a); y[r, :len(b)] = torch.tensor(b); m[r, :len(a)] = 1
                tl[r, :len(a)] = torch.from_numpy(t); has[r, :len(a)] = torch.from_numpy(hs)
            ids, y, m, tl, has = ids.to(dev), y.to(dev), m.to(dev), tl.to(dev), has.to(dev)
            logits = model(input_ids=ids, attention_mask=m).logits
            ce = F.cross_entropy(logits.reshape(-1, 3), y.reshape(-1), ignore_index=-100)
            if soft is not None and kd_weight > 0 and has.any():
                s_log = F.log_softmax(logits[has] / T, -1); t_prob = F.softmax(tl[has] / T, -1)
                kd = F.kl_div(s_log, t_prob, reduction="batchmean") * T * T
                loss = (1 - kd_weight) * ce + kd_weight * kd
            else:
                loss = ce
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); opt.zero_grad()
            if step < steps + 49: sched.step()
            step += 1
        log(f"  epoch {ep + 1}/{epochs}  loss {loss.item():.4f}  ({time.time() - t0:.0f}s)")
    model = model.cpu().eval(); model.save_pretrained(out)
    tok.save(str(out / "tokenizer.json"))
    PreTrainedTokenizerFast(tokenizer_file=str(out / "tokenizer.json"), cls_token="[CLS]", sep_token="[SEP]", pad_token="[PAD]",
                            unk_token="[UNK]", mask_token="[MASK]", model_max_length=maxtok).save_pretrained(out)
    tok.save(str(out / "tokenizer.json"))   # keep the plain tokenizers file the browser and Tagger read
    extra = {"role": "student", "arch": arch, "kd_weight": kd_weight if soft is not None else 0, "temperature": T,
             "docs": len(docs), "seed": seed, "epochs": epochs}
    mb = _export(model, out, CLS, SEP, maxtok, extra)
    info = {**extra, "dir": str(out.relative_to(K.ROOT)) if out.is_relative_to(K.ROOT) else str(out),
            "seconds": round(time.time() - t0), "int8_mb": mb}
    (out / "train_info.json").write_text(json.dumps(info, indent=1)); log(f"  saved {out.name}: int8 {mb} MB, {info['seconds']} s")
    return info


# ---------------------------------------------------------------------------------------------- selection
TRUSTS = [None, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]

def dev_table(tagger, dev_sets, trusts=TRUSTS) -> list[dict]:
    """Pipeline scores on the dev sets for every trust setting (plus the model alone)."""
    rows = []
    uses = [("model only", None, K.model_only(tagger))] + [("pipeline", t, K.pipeline(tagger, trust=t)) for t in trusts]
    for use, t, det in uses:
        r = K.evaluate(use, det, dev_sets)
        rows.append({"use": use, "trust": "off" if t is None else t,
                     **{f"{s} {m}": r[s][m] for s in dev_sets for m in ("recall", "precision", "f2")}})
    return rows

def choose_trust(rows, min_heldout=0.965):
    """Notebook 2's rule: heldout recall >= 96.5%, best Wiki dev F2, ties (0.5 pt) -> stricter trust."""
    ok = [r for r in rows if r["use"] == "pipeline" and r["heldout recall"] >= min_heldout] or [r for r in rows if r["use"] == "pipeline"]
    best = max(r["wiki dev f2"] for r in ok)
    tied = [r for r in ok if r["wiki dev f2"] >= best - 0.005]
    r = sorted(tied, key=lambda r: 0 if r["trust"] == "off" else -float(r["trust"]))[0]
    return (None if r["trust"] == "off" else float(r["trust"])), r
