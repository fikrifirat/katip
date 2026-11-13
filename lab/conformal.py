"""Certified recall for redaction with conformal risk control (Angelopoulos et al., 2022, arXiv:2208.02814).

Idea in one paragraph. Every word gets a score: 1.0 if Katip's rules mark it as part of a name,
otherwise the tagger's probability that it is part of a name. We mask every word scoring at or above a
threshold λ. The *loss* of a document is the share of its name words left readable. Lower λ masks more,
so the loss can only go down as λ goes down. Conformal risk control picks λ from a calibration set of
n documents so that, for a new document drawn from the same source,

        expected share of name words left readable  ≤  α          (for any model, any α)

as long as the calibration documents and the new document are exchangeable (come from the same mix).
The price is over-masking: ordinary words above λ get masked too, or, in the product, sent for review.
"""
from __future__ import annotations

import numpy as np

import katiplab as K

GRID = np.unique(np.round(np.concatenate([np.linspace(0, 1, 201), np.geomspace(1e-4, 5e-3, 15)]), 5))  # λ candidates, finer near 0


def word_person_probs(tagger: K.Tagger, text: str):
    """[(start, end, P(word is part of a name))] with the browser's windowing; P = P(B-PER) + P(I-PER)."""
    words = [(m.start(), m.end(), tagger.tok.encode(m.group(), add_special_tokens=False).ids or [tagger.UNK])
             for m in tagger.word.finditer(text)]
    per = [i for i, l in tagger.id2label.items() if l.endswith("PER") or l.endswith("PERSON")]
    out, w0 = [], 0
    while w0 < len(words):
        ids, first, w = [tagger.CLS], [], w0
        while w < len(words) and len(ids) + len(words[w][2]) < tagger.maxtok - 1:
            first.append(len(ids)); ids += words[w][2]; w += 1
        if w == w0: out.append((words[w0][0], words[w0][1], 0.0)); w0 += 1; continue
        ids.append(tagger.SEP); a = np.array([ids], dtype=np.int64)
        feed = {"input_ids": a, "attention_mask": np.ones_like(a), "token_type_ids": np.zeros_like(a)}
        lg = tagger.sess.run(["logits"], {k: v for k, v in feed.items() if k in tagger.inputs})[0][0]
        for j, pos in enumerate(first):
            z = lg[pos] - lg[pos].max(); p = np.exp(z) / np.exp(z).sum()
            out.append((words[w0 + j][0], words[w0 + j][1], float(p[per].sum())))
        w0 = w
    return out


def word_scores(docs, tagger, use_rules: bool = True):
    """One (is_name, score) array per document that contains at least one name."""
    rules = K.rules()
    out = []
    for d in docs:
        text = d["text"]; gold = [(a, b) for a, b, t in d["spans"] if t == "PERSON"]
        if not gold: continue
        ruled = [(s, e) for s, e, t in rules(text) if t == "PERSON"] if use_rules else []
        rows = []
        for s, e, p in (word_person_probs(tagger, text) if tagger else
                        [(m.start(), m.end(), 0.0) for m in K.regex.finditer(K.WORD_RE, text)]):
            if not any(c.isalpha() for c in text[s:e]): continue
            is_name = any(s < b and e > a for a, b in gold)
            hit = any(s < b and e > a for a, b in ruled)
            rows.append((is_name, 1.0 if hit else p))
        out.append(np.array(rows, dtype=float))
    return out


def loss_cost(scores):
    """loss[i, j]: share of name words of doc i left readable at λ = GRID[j];
       cost[i, j]: share of the other words of doc i masked at λ = GRID[j]."""
    L = np.zeros((len(scores), len(GRID))); C = np.zeros_like(L)
    for i, a in enumerate(scores):
        name, sc = a[:, 0].astype(bool), a[:, 1]
        masked = sc[:, None] >= GRID[None, :]
        L[i] = (~masked[name]).mean(0) if name.any() else 0
        C[i] = masked[~name].mean(0) if (~name).any() else 0
    return L, C


def calibrate(L_cal: np.ndarray, alpha: float, B: float = 1.0) -> float:
    """Conformal risk control: the largest λ with (n·R̂(λ) + B) / (n + 1) ≤ α. Returns λ̂ (0 = mask everything)."""
    n = len(L_cal)
    ok = (n * L_cal.mean(0) + B) / (n + 1) <= alpha
    return float(GRID[ok].max()) if ok.any() else 0.0


def naive(L_cal: np.ndarray, alpha: float) -> float:
    """The tempting shortcut: the largest λ whose calibration miss rate is ≤ α (no finite-sample correction)."""
    ok = L_cal.mean(0) <= alpha
    return float(GRID[ok].max()) if ok.any() else 0.0


def trials(L, C, alpha, n_cal=None, reps: int = 1000, seed: int = 0, method=calibrate):
    """Random calibration/test splits. Returns arrays (λ̂, test loss, test cost) over `reps` splits."""
    rng = np.random.default_rng(seed); n = len(L); n_cal = n_cal or n // 2
    lam, loss, cost = [], [], []
    for _ in range(reps):
        idx = rng.permutation(n); cal, test = idx[:n_cal], idx[n_cal:]
        l = method(L[cal], alpha); j = int(np.searchsorted(GRID, l))
        lam.append(l); loss.append(L[test, j].mean()); cost.append(C[test, j].mean())
    return np.array(lam), np.array(loss), np.array(cost)


def transfer(L_cal, L_test, C_test, alpha, method=calibrate):
    """Calibrate on one source, apply to another (to show what happens when the sources differ)."""
    l = method(L_cal, alpha); j = int(np.searchsorted(GRID, l))
    return l, float(L_test[:, j].mean()), float(C_test[:, j].mean())
