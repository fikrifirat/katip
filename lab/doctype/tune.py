"""Pick hyper-parameters without touching family 2: train on family 0, validate on family 1, and the
reverse; average. Family 2 (the held-out test) is never generated here.

    python lab/doctype/tune.py
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen  # noqa: E402
import train as TR  # noqa: E402


def predict(W, b, rows, dim, vecs):
    idx, val, off = vecs
    Z = TR.dense(range(len(rows)), idx, val, off, dim) @ W + b
    return Z


def score(Z, y, labels, diger_bias):
    Z = Z.copy(); Z[:, labels.index("diger")] -= diger_bias
    P = np.exp(Z - Z.max(1, keepdims=True)); P /= P.sum(1, keepdims=True)
    pred = P.argmax(1)
    acc = (pred == y).mean()
    f1 = []
    for c in range(len(labels)):
        tp = ((pred == c) & (y == c)).sum(); fp = ((pred == c) & (y != c)).sum(); fn = ((pred != c) & (y == c)).sum()
        f1.append(2 * tp / max(1, 2 * tp + fp + fn))
    return acc, float(np.mean(f1))


if __name__ == "__main__":
    labels = TR.D.Pack("tr", model_root=Path("/nonexistent")).labels
    drop = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    A = gen.make([0], 200, 11, aug=True, drop=drop)
    B = gen.make([1], 200, 12, aug=True, drop=drop)
    VA = gen.make([0], 100, 13, aug=True)       # validation never has dropout
    VB = gen.make([1], 100, 14, aug=True)
    KS = [("w", "b", "c", "l", "h"), ("w", "b", "c")]
    grid = list(itertools.product([1e-4, 3e-4], [2, 3], [2 ** 14], KS))
    out = []
    cache = {}
    for l2, ep, dim, kinds in grid:
        if kinds not in cache:
            cache[kinds] = [TR.vectorise(x, dim, kinds) for x in (A, B, VA, VB)]
        vA, vB, vVA, vVB = cache[kinds]
        res = {}
        for tr, va, vt, vv, tag in ((A, VB, vA, vVB, "0->1"), (B, VA, vB, vVA, "1->0")):
            W, b = TR.train(tr, labels, dim, ep, 0.05, l2, log=lambda *_: None, kinds=kinds, vecs=vt)
            Z = predict(W, b, va, dim, vv)
            y = np.array([labels.index(r["label"]) for r in va])
            res[tag] = {db: score(Z, y, labels, db) for db in (0.0, 0.5, 1.0, 2.0)}
        for db in (0.0, 0.5, 1.0, 2.0):
            acc = np.mean([res[t][db][0] for t in res]); f1 = np.mean([res[t][db][1] for t in res])
            out.append({"kinds": "".join(kinds), "l2": l2, "epochs": ep, "dim": dim, "diger_bias": db, "acc": round(acc * 100, 1), "macro_f1": round(f1 * 100, 1)})
        print(max(out[-4:], key=lambda r: r["macro_f1"]), flush=True)
    best = max(out, key=lambda r: r["macro_f1"])
    print("best", best)
    (HERE / "runs").mkdir(exist_ok=True)
    (HERE / f"runs/tune_drop{drop}.json").write_text(json.dumps({"grid": out, "best": best}, indent=1))
