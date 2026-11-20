"""Train the linear document-type classifier and write it as an int8 language pack.

    python lab/doctype/train.py --train full --out connector/katip_kalkan/doctype_packs   # shipped model
    python lab/doctype/train.py --train train --out lab/doctype/runs/family_split         # held-out experiment

Input: any JSONL(.gz) with {"text", "label"}; labels must be ids in <lang>.pack.json. Nothing here is
Turkish-specific: a Dutch run is `--lang nl --train <dutch jsonl>`.
Features come from katip_kalkan.doctype.featurize, the same function the connector runs, so train and
serve can't drift. Model: multinomial logistic regression, Adam, L2, a few epochs (numpy only).
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "connector"))
from katip_kalkan import doctype as D  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"


def load(name: str) -> list[dict]:
    p = Path(name) if Path(name).exists() else DATA / f"{name}.jsonl.gz"
    op = gzip.open if p.suffix == ".gz" else open
    with op(p, "rt", encoding="utf-8") as fh:
        return [json.loads(l) for l in fh]


def vectorise(rows, dim, kinds=D.KINDS):
    """-> CSR-ish lists (indices, values, offsets) built with the connector's featurize."""
    idx, val, off = [], [], [0]
    for r in rows:
        v = D.featurize(r["text"], dim, kinds)
        idx.extend(v.keys()); val.extend(v.values()); off.append(len(idx))
    return np.array(idx, np.int64), np.array(val, np.float32), np.array(off, np.int64)


def dense(batch, idx, val, off, dim):
    X = np.zeros((len(batch), dim), np.float32)
    for j, i in enumerate(batch):
        a, b = off[i], off[i + 1]
        X[j, idx[a:b]] = val[a:b]
    return X


def train(rows, labels, dim=2 ** 14, epochs=10, lr=0.05, l2=1e-6, bs=128, seed=0, log=print, kinds=D.KINDS, vecs=None):
    lab = {l: i for i, l in enumerate(labels)}
    y = np.array([lab[r["label"]] for r in rows])
    t0 = time.time()
    idx, val, off = vecs or vectorise(rows, dim, kinds)
    log(f"features: {len(rows)} docs in {time.time() - t0:.1f}s, {len(idx) / len(rows):.0f} non-zeros/doc")
    C = len(labels)
    rng = np.random.default_rng(seed)
    W = np.zeros((dim, C), np.float32); b = np.zeros(C, np.float32)
    mW, vW, mb, vb = (np.zeros_like(W), np.zeros_like(W), np.zeros_like(b), np.zeros_like(b))
    step = 0
    for ep in range(epochs):
        order = rng.permutation(len(rows)); loss = 0.0
        for s in range(0, len(rows), bs):
            bi = order[s:s + bs]
            X = dense(bi, idx, val, off, dim)
            Z = X @ W + b
            Z -= Z.max(1, keepdims=True)
            P = np.exp(Z); P /= P.sum(1, keepdims=True)
            loss += -np.log(P[np.arange(len(bi)), y[bi]] + 1e-12).sum()
            P[np.arange(len(bi)), y[bi]] -= 1
            gW = X.T @ P / len(bi) + l2 * W
            gb = P.mean(0)
            step += 1
            for p, g, m, v in ((W, gW, mW, vW), (b, gb, mb, vb)):
                m *= .9; m += .1 * g
                v *= .999; v += .001 * g * g
                p -= lr * (m / (1 - .9 ** step)) / (np.sqrt(v / (1 - .999 ** step)) + 1e-8)
        log(f"epoch {ep + 1}: loss {loss / len(rows):.4f}")
    return W, b


def fit_temperature(W, b, rows, labels, dim, kinds):
    ci, cv, co = vectorise(rows, dim, kinds)
    Z = dense(range(len(rows)), ci, cv, co, dim) @ W + b
    y = np.array([labels.index(r["label"]) for r in rows])
    def nll(t):
        z = Z / t; z = z - z.max(1, keepdims=True)
        return float(-(z[np.arange(len(y)), y] - np.log(np.exp(z).sum(1))).mean())
    return float(min(np.arange(0.05, 3.0, 0.01), key=nll))


def write_pack(W, b, labels, out: Path, lang: str, version: str, info: dict, kinds=D.KINDS):
    """int8 per class: w_int = round(w / scale_c), scale_c = max|w_c| / 127."""
    out.mkdir(parents=True, exist_ok=True)
    scale = np.abs(W).max(0) / 127.0
    scale[scale == 0] = 1.0
    Wq = np.clip(np.round(W / scale), -127, 127).astype(np.int8)
    (out / f"{lang}.model.bin").write_bytes(Wq.tobytes(order="C"))      # row-major: feature, then class
    meta = {"lang": lang, "version": version, "dim": int(W.shape[0]), "labels": labels,
            "scale": [float(x) for x in scale], "bias": [float(x) for x in b], "weights": f"{lang}.model.bin", "kinds": list(kinds),
            "features": "katip_kalkan.doctype.tokens v1 (FNV-1a 32, signed, log1p, L2)", **info}
    (out / f"{lang}.model.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return out / f"{lang}.model.bin"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="tr")
    ap.add_argument("--train", default="full", nargs="+")
    ap.add_argument("--out", default=str(ROOT / "connector/katip_kalkan/doctype_packs"))
    ap.add_argument("--dim", type=int, default=2 ** 14)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--l2", type=float, default=1e-4)
    ap.add_argument("--version", default="tr-0.1")
    ap.add_argument("--calib", nargs="*", default=["cross"], help="'cross' = fit the temperature across writing families (see code)")
    ap.add_argument("--kinds", default="wbc", help="feature kinds (w words, b bigrams, c char 3-4 grams, l line starts, h title)")
    ap.add_argument("--other-bias", type=float, default=1.0, help="subtracted from the 'other' class logit (tune.py)")
    a = ap.parse_args()
    rows = [r for n in a.train for r in load(n)]
    labels = D.Pack(a.lang, model_root=Path("/nonexistent")).labels
    unknown = {r["label"] for r in rows} - set(labels)
    assert not unknown, f"labels not in {a.lang}.pack.json: {unknown}"
    kinds = tuple(a.kinds)
    W, b = train(rows, labels, a.dim, a.epochs, a.lr, a.l2, kinds=kinds)
    other = "diger" if "diger" in labels else "overig" if "overig" in labels else None
    if other:
        b[labels.index(other)] -= a.other_bias
    T = 1.0
    if a.calib == ["cross"]:
        # Temperature from writing styles the fold never saw: train without family f, fit T on family f.
        # In-distribution data is separable (T -> 0, always confident), which would make abstaining useless.
        fams = sorted({r.get("family") for r in rows if r.get("family", -1) >= 0})
        ts = []
        for f in fams:
            tr = [r for r in rows if r.get("family", -1) not in (f, -1)]
            va = [r for r in rows if r.get("family") == f][::4]
            Wf, bf = train(tr, labels, a.dim, a.epochs, a.lr, a.l2, kinds=kinds, log=lambda *_: None)
            if other:
                bf[labels.index(other)] -= a.other_bias
            ts.append(fit_temperature(Wf, bf, va, labels, a.dim, kinds))
            print(f"  fold without family {f}: T = {ts[-1]:.2f}")
        T = float(np.mean(ts))
        print(f"temperature {T:.2f} (mean over {len(ts)} cross-family folds)")
        W, b = W / T, b / T
    p = write_pack(W, b, labels, Path(a.out), a.lang, a.version,
                   {"trained_on": a.train, "n_docs": len(rows), "epochs": a.epochs, "l2": a.l2, "other_bias": a.other_bias, "temperature": float(T), "calibrated_on": a.calib}, kinds)
    print("wrote", p, f"{p.stat().st_size / 1024:.0f} KB")
