# Vendored from docs/katip_py.zip (katip_redact/textutil.py) by sdk/tools/sync_engine.py. Do not edit here:
# change the engine at its source and re-run the sync, so the SDK, the demo and Kalkan stay identical.
"""Turkish-aware text helpers."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data"

TR_UPPER = "A-ZÇĞİÖŞÜÂÎÛ"
TR_LOWER = "a-zçğıöşüâîû"
TR_LETTER = f"{TR_UPPER}{TR_LOWER}"
WORD_RE = re.compile(rf"[{TR_LETTER}]+(?:\.[{TR_LETTER}]+)*\.?")


def tr_lower(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def tr_upper(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


def normalize(s: str) -> str:
    """NFC + drop stray combining dot (seen in copy-pasted Turkish text)."""
    return unicodedata.normalize("NFC", s).replace("̇", "")


def fold(s: str) -> str:
    """Lower-case and strip Turkish diacritics; used for gazetteer lookups so
    OCR output like 'YILMAZ'/'Yilmaz'/'Yılmaz' all match."""
    s = tr_lower(normalize(s))
    return s.translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))


@lru_cache(maxsize=None)
def wordlist(name: str) -> frozenset[str]:
    out = set()
    for line in (DATA / name).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(fold(line))
    return frozenset(out)


def is_capitalised(tok: str) -> bool:
    return bool(tok) and tok[0].isupper()


def is_all_caps(tok: str) -> bool:
    letters = [c for c in tok if c.isalpha()]
    return len(letters) >= 2 and all(c.isupper() for c in letters)
