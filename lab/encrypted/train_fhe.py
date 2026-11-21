"""Distil Katip Mask Nano into an FHE-friendly Nano ("Nano-FHE").

Same architecture, same tokenizer, initialised from Nano's own weights. Only the non-linearities change
(fhe_ops.PolyFHE) and attention is limited to +-WINDOW tokens. Loss: KL to Nano's output distribution on
every token + cross-entropy on gold word labels. Data: Katip's synthetic train set + Turkish Wiki NER train
(packed 8 sentences per document), the same sources Nano was trained on. No bench data is used.

  python lab/encrypted/train_fhe.py out_dir [epochs]
"""
from __future__ import annotations

import json, math, random, sys, time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import katiplab as K  # noqa: E402
from nano_torch import load_nano, nano_dir  # noqa: E402
from fhe_ops import PolyFHE  # noqa: E402

WINDOW = 16
SEED = 0

def sequences(tagger, docs):
    """Token windows exactly as Tagger.word_labels builds them, with word-level PERSON labels on first sub-tokens."""
    out = []
    for d in docs:
        text = d["text"]; spans = [s for s in d["spans"] if s[2] == "PERSON"]
        words = [(m.start(), m.end(), tagger.tok.encode(m.group(), add_special_tokens=False).ids or [tagger.UNK]) for m in tagger.word.finditer(text)]
        lab = []
        for s, e, _ in words:
            l = 0
            for a, b, _t in spans:
                if s < b and e > a: l = 1 if s <= a else 2; break
            lab.append(l)
        w0 = 0
        while w0 < len(words):
            ids, labs, w = [tagger.CLS], [-100], w0
            while w < len(words) and len(ids) + len(words[w][2]) < tagger.maxtok - 1:
                labs += [lab[w]] + [-100] * (len(words[w][2]) - 1); ids += words[w][2]; w += 1
            if w == w0: w0 += 1; continue
            out.append((ids + [tagger.SEP], labs + [-100])); w0 = w
    return out

def batches(seqs, bs, shuffle=True):
    order = list(range(len(seqs)))
    if shuffle: random.shuffle(order)
    for k in range(0, len(order), bs):
        ch = [seqs[o] for o in order[k:k + bs]]; n = max(len(c[0]) for c in ch)
        ids = torch.zeros((len(ch), n), dtype=torch.long); labs = torch.full((len(ch), n), -100); mask = torch.zeros((len(ch), n), dtype=torch.long)
        for r, (a, b) in enumerate(ch):
            ids[r, :len(a)] = torch.tensor(a); labs[r, :len(b)] = torch.tensor(b); mask[r, :len(a)] = 1
        yield ids, mask, labs

def main(out, epochs=3, lr=1e-4, bs=32, kd_w=1.0, ce_w=1.0, wiki_x=1, singles=True):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.set_num_threads(4)
    tagger = K.Tagger(nano_dir())
    teacher = load_nano()
    student = load_nano(ops=PolyFHE(), window=WINDOW).train()
    wiki = K.load_wiki("train"); random.Random(SEED).shuffle(wiki)
    docs = list(K.load_synth("train")) + K.pack(wiki) * wiki_x
    if singles:   # also single sentences: Nano's behaviour depends on context length, and the bench's prose track is single sentences
        docs += wiki
    seqs = sequences(tagger, docs)
    steps = epochs * math.ceil(len(seqs) / bs)
    opt = torch.optim.AdamW(student.parameters(), lr=lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps + 10, pct_start=0.1)
    print(f"{len(docs)} docs, {len(seqs)} windows, {steps} steps", flush=True)
    t0 = time.time(); step = 0
    for ep in range(epochs):
        for ids, mask, labs in batches(seqs, bs):
            with torch.no_grad(): tl = teacher(ids, mask)
            sl = student(ids, mask)
            m = mask.bool()
            kd = F.kl_div(F.log_softmax(sl[m], -1), F.softmax(tl[m], -1), reduction="batchmean")
            ce = F.cross_entropy(sl.reshape(-1, 3), labs.reshape(-1), ignore_index=-100)
            loss = kd_w * kd + ce_w * ce
            loss.backward(); torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0); opt.step(); opt.zero_grad(); sched.step(); step += 1
            if step % 200 == 0: print(f"  ep {ep + 1} step {step}/{steps} kd {kd.item():.4f} ce {ce.item():.4f} ({time.time() - t0:.0f}s)", flush=True)
    student.eval()
    torch.save(student.state_dict(), out / "nano_fhe.pt")
    (out / "train_info.json").write_text(json.dumps({"teacher": "f1k/katip-mask-nano (dequantized)", "window": WINDOW, "ops": "PolyFHE",
        "epochs": epochs, "lr": lr, "bs": bs, "kd_w": kd_w, "ce_w": ce_w, "wiki_x": wiki_x, "singles": singles, "docs": len(docs), "windows": len(seqs), "seconds": round(time.time() - t0)}, indent=1))
    print("saved", out, f"{time.time() - t0:.0f}s")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-4); ap.add_argument("--ce", type=float, default=1.0); ap.add_argument("--wiki-x", type=int, default=1)
    a = ap.parse_args()
    main(a.out, a.epochs, a.lr, ce_w=a.ce, wiki_x=a.wiki_x)
