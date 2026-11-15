"""Write the expected outputs (from the Python SDK) that the JavaScript SDK must reproduce exactly.

    python sdk/parity/golden.py [--fuzz 300] [--extra-dir DIR] > cases.jsonl
    node --test sdk/js/test/parity.test.mjs   (reads KATIP_PARITY_CASES, default sdk/parity/cases.jsonl)

Each case runs the full Masker pipeline (rules, model-span merging, ID context, propagation, the leak
check and placeholder rendering) under one configuration. Model spans are synthesised from the text, so the
merge rules are covered without running a model; real model parity is a separate test (test_models).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "python" / "src"))
sys.path.insert(0, str(HERE))

from corpus import corpus  # noqa: E402
from katip_mask import LeakError, Masker  # noqa: E402

TOK = re.compile(r"[^\W_]+")


def fake_model_spans(text: str, rng: random.Random) -> list[list]:
    """Model-like spans on word boundaries: single capitalised words, pairs, runs, typed spans."""
    words = list(TOK.finditer(text))
    out = []
    for _ in range(rng.randint(0, min(12, len(words)))):
        i = rng.randrange(len(words))
        j = min(len(words) - 1, i + rng.choice([0, 0, 1, 1, 2, 3]))
        s, e = words[i].start(), words[j].end()
        typ = rng.choice(["PERSON"] * 6 + ["ADDRESS", "HEALTH", None])
        score = rng.choice([0.51, 0.7, 0.75, 0.86, 0.9, 0.99, rng.random()])
        out.append([s, e, score] + ([typ] if typ else []))
    return out


def configs(rng: random.Random, text: str):
    words = [m.group() for m in TOK.finditer(text)]
    yield {"profile": "court"}
    yield {"profile": "ai", "threshold": 0.5}
    yield {"profile": "anon", "style": "block", "ocr": True}
    yield {"profile": rng.choice(["court", "ai", "anon"]), "threshold": rng.choice([0.3, 0.6, 0.7, 0.9]),
           "extra": fake_model_spans(text, rng), "trust": rng.choice([None, 0.5, 0.85]),
           "allow": rng.sample(words, min(2, len(words))) if words and rng.random() < 0.5 else [],
           "deny": rng.sample(words, min(2, len(words))) if words and rng.random() < 0.5 else [],
           "address_detail": rng.choice([None, "street", "full"]), "ocr": rng.random() < 0.3}


def run(text: str, cfg: dict) -> dict:
    m = Masker(cfg["profile"], **({"threshold": cfg["threshold"]} if "threshold" in cfg else {}), allow=cfg.get("allow", ()), deny=cfg.get("deny", ()),
               style=cfg.get("style", "label"), address_detail=cfg.get("address_detail"))
    m._trust = cfg.get("trust")
    ocr = [(0, len(text))] if cfg.get("ocr") else ()
    try:
        r = m._mask(text, ocr, [list(x) for x in cfg.get("extra", [])])
        return {"text": r.text, "spans": [s.to_dict() for s in r.spans], "mapping": r.mapping}
    except LeakError as e:
        return {"error": {"kinds": e.kinds, "lines": e.lines}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuzz", type=int, default=300)
    ap.add_argument("--extra-dir", help="also use every .txt under this folder (local corpora not in the repo)")
    a = ap.parse_args()
    docs = corpus(a.fuzz)
    if a.extra_dir:
        docs += [(str(p), p.read_text(encoding="utf-8", errors="replace")) for p in sorted(Path(a.extra_dir).rglob("*.txt"))]
    rng = random.Random(7)
    n = 0
    for name, text in docs:
        for cfg in configs(rng, text):
            sys.stdout.write(json.dumps({"name": name, "input": text, "cfg": cfg, "expect": run(text, cfg)}, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} cases from {len(docs)} documents", file=sys.stderr)


if __name__ == "__main__":
    main()
