"""Build the synthetic document-type sets from templates_tr.py.

    python lab/doctype/gen.py            # -> lab/doctype/data/{train,dev,test_family}.jsonl.gz

Splits (seed 20261120):
  train        families 0 and 1, N_TRAIN per type, augmented
  dev          families 0 and 1, new seed, for picking the threshold and epochs (never for the headline)
  test_family  family 2 only: a writing style the model never saw. This is the held-out synthetic score.
  full         families 0, 1 and 2 (the shipped model trains on this; it is then scored only on the
               independent sets in eval.py, which share no template with this file)

Augmentation mimics what a real folder looks like: OCR noise, ASCII-typed Turkish, ALL CAPS, missing
title line (a scan that starts on page 2), a short first page only, a page from the middle.
"""
from __future__ import annotations

import gzip
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fill import Fill, upper_tr  # noqa: E402
from templates_tr import T  # noqa: E402

OUT = HERE / "data"
SEED = 20261120
N_TRAIN, N_DEV, N_TEST = 400, 60, 120
DROP, MIX = 0.3, 0.3        # line dropout on half the training docs; 30% of training docs mix two families

ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
OCR_SWAP = {"ı": "i", "i": "ı", "l": "1", "O": "0", "rn": "m", "m": "rn", "ş": "s", "e": "c", "ü": "u", "ğ": "g"}


def ocr_noise(r: random.Random, s: str, rate: float) -> str:
    out = []
    i = 0
    while i < len(s):
        if r.random() < rate:
            k = r.random()
            two = s[i:i + 2]
            if two in OCR_SWAP and k < .3:
                out.append(OCR_SWAP[two]); i += 2; continue
            if s[i] in OCR_SWAP and k < .7:
                out.append(OCR_SWAP[s[i]])
            elif k < .85:
                pass                       # dropped character
            else:
                out.append(s[i] + " ")     # split word
        else:
            out.append(s[i])
        i += 1
    return "".join(out)


def augment(r: random.Random, text: str, drop: float = 0.0) -> tuple[str, list[str]]:
    tags = []
    lines = text.split("\n")
    if drop and len(lines) > 4:                         # line dropout: no single line can carry the label
        kept = [l for l in lines if r.random() > drop]
        lines = kept if len(kept) >= 3 else lines; tags.append("drop")
    if r.random() < .15 and len(lines) > 6:            # scan starts after the title block
        cut = r.randint(1, min(4, len(lines) // 3))
        lines = lines[cut:]; tags.append("no_title")
    text = "\n".join(lines)
    if r.random() < .1 and len(text) > 600:            # a middle page only
        a = r.randint(0, len(text) // 3)
        text = text[a:a + r.randint(300, 900)]; tags.append("middle")
    elif r.random() < .1 and len(text) > 500:          # only the top of the first page
        text = text[:r.randint(250, 500)]; tags.append("top")
    if r.random() < .15:
        text = text.translate(ASCII); tags.append("ascii")
    if r.random() < .08:
        text = upper_tr(text); tags.append("caps")
    if r.random() < .25:
        text = ocr_noise(r, text, r.choice([.01, .03, .06])); tags.append("ocr")
    if r.random() < .2:                                # PDF text extraction: lines glued or re-wrapped
        text = text.replace("\n", " ") if r.random() < .5 else "\n".join(
            text[i:i + 70] for i in range(0, len(text), 70)); tags.append("rewrap")
    return text, tags


def mix(r: random.Random, a: str, b: str) -> str:
    """Interleave the lines of two documents of the same type written in different families."""
    la, lb = a.split("\n"), b.split("\n")
    out = []
    while la or lb:
        src = la if (la and (not lb or r.random() < .5)) else lb
        out.append(src.pop(0))
    return "\n".join(out)


def make(families: list[int], n: int, seed: int, aug: bool, drop: float = 0.0, mix_p: float = 0.0) -> list[dict]:
    r = random.Random(seed)
    f = Fill(r)
    rows = []
    for label, fams in T.items():
        for i in range(n):
            fi = families[i % len(families)]
            text = fams[fi](f).strip()
            if mix_p and len(families) > 1 and r.random() < mix_p:
                other = r.choice([x for x in families if x != fi])
                text = mix(r, text, fams[other](f).strip()); fi = -1
            tags: list[str] = []
            if aug:
                text, tags = augment(r, text, drop if r.random() < .5 else 0.0)
            rows.append({"text": text, "label": label, "family": fi, "aug": tags})
    r.shuffle(rows)
    return rows


def save(name: str, rows: list[dict]):
    OUT.mkdir(exist_ok=True)
    with gzip.open(OUT / f"{name}.jsonl.gz", "wt", encoding="utf-8") as fh:
        for x in rows:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"{name}: {len(rows)} docs")


if __name__ == "__main__":
    save("train", make([0, 1], N_TRAIN, SEED, aug=True, drop=DROP, mix_p=MIX))
    save("dev", make([0, 1], N_DEV, SEED + 1, aug=True))
    save("test_family", make([2], N_TEST, SEED + 2, aug=True))
    save("test_family_clean", make([2], N_TEST // 2, SEED + 3, aug=False))
    save("full", make([0, 1, 2], N_TRAIN, SEED + 4, aug=True, drop=DROP, mix_p=MIX))
