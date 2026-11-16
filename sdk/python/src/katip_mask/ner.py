"""On-device name model (Katip Mask Mini / Nano / Base) with ONNX Runtime.

Same decoding as the browser demo (src/ner.js) and Katip Kalkan: each word's first sub-token decides its
BIO label, B/I runs of one type are merged (names across spaces and commas; addresses also across line
breaks and . / : -), and a Turkish case suffix after an apostrophe is dropped from a name (Ahmet'in ->
Ahmet). Tokenisation is a small pure-Python WordPiece that follows the model's tokenizer.json, so the
`tokenizers` package is not needed. Needs `onnxruntime` and `numpy` (pip install "katip-mask[model]").
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from pathlib import Path

WORD = re.compile(r"[^\W_](?:[^\W_]|['’.-])*")
TYPES = {"PER": "PERSON", "PERSON": "PERSON", "ADDR": "ADDRESS", "ADDRESS": "ADDRESS", "HEALTH": "HEALTH"}
_GLUE = {"ADDRESS": re.compile(r"[ \t,\n./:-]*")}
_GLUE_DEFAULT = re.compile(r"[ \t,]*")


def _is_punct(ch: str) -> bool:
    cp = ord(ch)
    if 33 <= cp <= 47 or 58 <= cp <= 64 or 91 <= cp <= 96 or 123 <= cp <= 126:
        return True
    return unicodedata.category(ch).startswith("P")


def _is_cjk(cp: int) -> bool:
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF or 0x2A700 <= cp <= 0x2B73F
            or 0x2B740 <= cp <= 0x2B81F or 0x2B820 <= cp <= 0x2CEAF or 0xF900 <= cp <= 0xFAFF or 0x2F800 <= cp <= 0x2FA1F)


class WordPiece:
    """BERT WordPiece as configured in a tokenizer.json (BertNormalizer or NFC, BertPreTokenizer)."""

    def __init__(self, tok: dict):
        m = tok["model"]
        if m["type"] != "WordPiece":
            raise ValueError(f"unsupported tokenizer model {m['type']}")
        self.vocab: dict[str, int] = m["vocab"]
        self.prefix = m.get("continuing_subword_prefix", "##")
        self.max_chars = m.get("max_input_chars_per_word", 100)
        self.unk = self.vocab[m.get("unk_token", "[UNK]")]
        self.cls, self.sep = self.vocab["[CLS]"], self.vocab["[SEP]"]
        norm = tok.get("normalizer") or {}
        kinds = [n["type"] for n in norm.get("normalizers", [])] if norm.get("type") == "Sequence" else [norm.get("type")]
        self.nfc = "NFC" in kinds
        bert = norm if norm.get("type") == "BertNormalizer" else {}
        self.chinese = bool(bert.get("handle_chinese_chars", False))
        self.lower = bool(bert.get("lowercase", False)) or "Lowercase" in kinds
        self.strip_accents = bert.get("strip_accents")
        if self.strip_accents is None:
            self.strip_accents = self.lower
        self.clean = bool(bert.get("clean_text", False))

    def _normalize(self, w: str) -> str:
        if self.nfc:
            w = unicodedata.normalize("NFC", w)
        if self.clean:
            w = "".join(" " if c in "\t\n\r" or unicodedata.category(c) == "Zs" else c for c in w
                        if not (ord(c) in (0, 0xFFFD) or (unicodedata.category(c).startswith("C") and c not in "\t\n\r")))
        if self.chinese:
            w = "".join(f" {c} " if _is_cjk(ord(c)) else c for c in w)
        if self.lower:
            w = w.lower()
        if self.strip_accents:
            w = "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")
        return w

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
        ids: list[int] = []
        for piece in self._pieces(self._normalize(word)):
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


class NameModel:
    def __init__(self, folder: Path, name: str | None = None, threads: int | None = None):
        try:
            import numpy as np
            import onnxruntime as ort
        except ImportError as e:  # pragma: no cover - depends on the environment
            raise ImportError('the Katip Mask models need onnxruntime and numpy: pip install "katip-mask[model]"') from e
        self.np = np
        self.folder = Path(folder)
        self.name = name or self.folder.name
        self.config = json.loads((self.folder / "config.json").read_text(encoding="utf-8"))
        self.id2label = {int(k): v for k, v in self.config["id2label"].items()}
        self.tok = WordPiece(json.loads((self.folder / "tokenizer.json").read_text(encoding="utf-8")))
        onnx = self.folder / "onnx" / "model_quantized.onnx"
        if not onnx.exists():
            onnx = self.folder / "onnx" / "model.onnx"
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads or int(os.environ.get("KATIP_MASK_THREADS", "0")) or 0
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(str(onnx), so, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.sess.get_inputs()}
        self.max_tokens = int((self.config.get("katip") or {}).get("max_tokens", 500))

    def spans(self, text: str, min_score: float = 0.5) -> list[tuple[int, int, float, str]]:
        """(start, end, score, type) of the names (and, for Base, addresses and health terms) the model finds."""
        np = self.np
        words = [(m.start(), m.end(), self.tok.encode(m.group(0)) or [self.tok.unk]) for m in WORD.finditer(text)]
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
                row = [float(x) for x in logits[pos]]
                best = max(range(len(row)), key=lambda c: (row[c], -c))
                total = 0.0
                for x in row:  # a plain left-to-right sum, like the JS SDK (sum() is compensated in 3.12+)
                    total += math.exp(x - row[best])
                p = 1.0 / total
                labels[w0 + j] = (self.id2label.get(best, "O"), p)
            w0 = w
        spans, cur = [], None
        for i, (s, e, _) in enumerate(words):
            lab, p = labels[i]
            typ = None if lab == "O" else TYPES.get(re.sub(r"^[BI]-", "", lab))
            gap = text[words[i - 1][1]:s] if i else ""
            if typ and cur and cur["t"] == typ and lab.startswith("I-") and _GLUE.get(typ, _GLUE_DEFAULT).fullmatch(gap):
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
            score = 0.0
            for p in c["ps"]:
                score += p
            score /= len(c["ps"])
            if score >= min_score and k:
                out.append((c["s"], c["s"] + k, score, c["t"]))
        return out


_loaded: dict[str, NameModel] = {}


def load(model: str | os.PathLike, progress=None) -> NameModel:
    """A cached NameModel for "mini" / "nano" / "base" (downloaded and verified) or a local model folder."""
    from .models import MODELS, model_path
    key = str(model)
    if key not in _loaded:
        if key in MODELS:
            _loaded[key] = NameModel(model_path(key, progress=progress), name=f"{key}@{MODELS[key]['revision'][:7]}")
        else:
            folder = Path(model).expanduser()
            if not (folder / "config.json").exists():
                raise FileNotFoundError(f"{folder} is not a model folder (config.json, tokenizer.json, onnx/)")
            _loaded[key] = NameModel(folder)
    return _loaded[key]
