"""On-device name model (Katip Mask Nano / Base), the Python twin of src/ner.js.

Optional: needs `onnxruntime` and a model folder (config.json, tokenizer.json,
onnx/model_quantized.onnx). Without either, the connector runs on rules only and
says so in katip_status.

Model folder lookup: $KATIP_MODEL, then ~/.katip/models/<name>/ (installed with
`katip-kalkan install-model`), then the bundled katip_kalkan/models/<name>/.
KATIP_MODEL=none turns the model off. A model folder may carry katip.json with
{"trust": 0.5}, the same per-model setting as src/models/registry.json.

Same decoding as the browser: word-level BIO from each word's first sub-token,
B/I runs merged with the same glue rules, Turkish suffix after an apostrophe
dropped from names. Tokenisation is a small pure-Python WordPiece so we don't
need the `tokenizers` wheel.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORD = re.compile(r"[^\W_](?:[^\W_]|['’.-])*")
TYPES = {"PER": "PERSON", "PERSON": "PERSON", "ADDR": "ADDRESS", "ADDRESS": "ADDRESS", "HEALTH": "HEALTH"}
_cache: dict[str, "Model | None"] = {}


def _is_punct(ch: str) -> bool:
    cp = ord(ch)
    if 33 <= cp <= 47 or 58 <= cp <= 64 or 91 <= cp <= 96 or 123 <= cp <= 126:
        return True
    return unicodedata.category(ch).startswith("P")


class WordPiece:
    def __init__(self, tok: dict):
        m = tok["model"]
        assert m["type"] == "WordPiece", m["type"]
        self.vocab: dict[str, int] = m["vocab"]
        self.prefix = m.get("continuing_subword_prefix", "##")
        self.max_chars = m.get("max_input_chars_per_word", 100)
        self.unk = self.vocab[m.get("unk_token", "[UNK]")]
        norm = tok.get("normalizer") or {}
        self.lower = bool(norm.get("lowercase")) or norm.get("type") == "Lowercase"
        self.cls, self.sep = self.vocab.get("[CLS]", 2), self.vocab.get("[SEP]", 3)

    def _pieces(self, word: str):
        cur = ""
        for ch in word:
            if ch.isspace():
                if cur:
                    yield cur
                cur = ""
            elif _is_punct(ch):
                if cur:
                    yield cur
                cur = ""
                yield ch
            else:
                cur += ch
        if cur:
            yield cur

    def encode(self, word: str) -> list[int]:
        word = unicodedata.normalize("NFC", word)
        if self.lower:
            word = word.lower()
        ids: list[int] = []
        for piece in self._pieces(word):
            if len(piece) > self.max_chars:
                ids.append(self.unk)
                continue
            start, sub = 0, []
            while start < len(piece):
                end, hit = len(piece), None
                while start < end:
                    s = piece[start:end] if start == 0 else self.prefix + piece[start:end]
                    if s in self.vocab:
                        hit = self.vocab[s]
                        break
                    end -= 1
                if hit is None:
                    sub = [self.unk]
                    break
                sub.append(hit)
                start = end
            ids.extend(sub)
        return ids


class Model:
    def __init__(self, folder: Path):
        import numpy as np
        import onnxruntime as ort
        self.np = np
        self.folder = folder
        self.config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        self.id2label = {int(k): v for k, v in self.config["id2label"].items()}
        self.tok = WordPiece(json.loads((folder / "tokenizer.json").read_text(encoding="utf-8")))
        onnx = folder / "onnx" / "model_quantized.onnx"
        if not onnx.exists():
            onnx = folder / "onnx" / "model.onnx"
        so = ort.SessionOptions()
        so.intra_op_num_threads = int(os.environ.get("KATIP_MODEL_THREADS", 2))
        self.sess = ort.InferenceSession(str(onnx), so, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.sess.get_inputs()}
        self.max_tokens = (self.config.get("katip") or {}).get("max_tokens", 500)
        self.name = self.config.get("_name_or_path") or folder.name

    def spans(self, text: str, min_score: float = 0.5) -> list[tuple[int, int, float, str]]:
        np = self.np
        words = []
        for m in WORD.finditer(text):
            ids = self.tok.encode(m.group(0)) or [self.tok.unk]
            words.append((m.start(), m.end(), ids))
        labels: list[tuple[str, float]] = [("O", 1.0)] * len(words)
        w0 = 0
        while w0 < len(words):
            ids, first, w = [self.tok.cls], [], w0
            while w < len(words) and len(ids) + len(words[w][2]) < self.max_tokens - 1:
                first.append(len(ids))
                ids.extend(words[w][2])
                w += 1
            if w == w0:  # a single word longer than the window
                w0 += 1
                continue
            ids.append(self.tok.sep)
            arr = np.array([ids], dtype=np.int64)
            feed = {"input_ids": arr, "attention_mask": np.ones_like(arr)}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(arr)
            logits = self.sess.run(None, feed)[0][0]
            for j, pos in enumerate(first):
                row = logits[pos]
                best = int(row.argmax())
                p = 1.0 / float(np.exp(row - row[best]).sum())
                labels[w0 + j] = (self.id2label.get(best, "O"), p)
            w0 = w
        spans, cur = [], None
        for i, (s, e, _) in enumerate(words):
            lab, p = labels[i]
            typ = None if lab == "O" else TYPES.get(re.sub(r"^[BI]-", "", lab))
            gap = text[words[i - 1][1]:s] if i else ""
            glue = r"[ \t,\n./:-]*" if typ == "ADDRESS" else r"[ \t,]*"
            if typ and cur and cur["t"] == typ and lab.startswith("I-") and re.fullmatch(glue, gap):
                cur["e"] = e
                cur["ps"].append(p)
            else:
                if cur:
                    spans.append(cur)
                cur = {"s": s, "e": e, "ps": [p], "t": typ} if typ else None
        if cur:
            spans.append(cur)
        out = []
        for c in spans:
            t = text[c["s"]:c["e"]]
            k = len(t)
            if c["t"] == "PERSON":
                k = min([t.index(q) for q in ("'", "’") if q in t] + [len(t)])
            score = sum(c["ps"]) / len(c["ps"])
            if score >= min_score and k:
                out.append((c["s"], c["s"] + k, score, c["t"]))
        return out


def _folder() -> Path | None:
    env = os.environ.get("KATIP_MODEL")
    if env:
        return None if env.lower() in ("none", "off", "rules") else Path(env).expanduser()
    from .vault import katip_home
    for root in (katip_home() / "models", HERE / "models"):
        if root.is_dir():
            for d in sorted(root.iterdir()):
                if (d / "config.json").exists() and (d / "onnx").is_dir():
                    return d
    return None


def get() -> Model | None:
    folder = _folder()
    key = str(folder)
    if key not in _cache:
        try:
            _cache[key] = Model(folder) if folder else None
        except ImportError:
            _cache[key] = None  # onnxruntime not installed: rules only
    return _cache[key]


def describe() -> str:
    m = get()
    if not m:
        return "rules only (install onnxruntime and a Katip Mask model for better name recall)"
    return f"rules + {m.folder.name} (on this device)"


def trust() -> float | None:
    v = os.environ.get("KATIP_TRUST")
    if v:
        return float(v)
    m = get()
    if not m:
        return None
    side = m.folder / "katip.json"
    if side.exists():
        return json.loads(side.read_text()).get("trust")
    return (m.config.get("katip") or {}).get("trust")

