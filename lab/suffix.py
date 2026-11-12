"""Turkish case suffixes after a masked name: what they reveal, and how to re-inflect them.

Turkish writes a case suffix on a proper name after an apostrophe: Ahmet'in, Ayşe'nin, Öztürk'ün,
Kaya'ya, Demir'e, Yılmaz'da, Ahmet'te. The suffix agrees with the name it follows:

  * vowel harmony: its vowel copies the backness (a/e) or backness + rounding (ı/i/u/ü) of the
    name's last vowel,
  * buffer letters: n, y or s appear when the name ends in a vowel (Ayşe'nin, Kaya'ya),
  * consonant assimilation: d becomes t after a voiceless consonant (Ahmet'te, Yılmaz'da).

So when a redaction keeps the suffix, the suffix keeps part of the name. This module turns a surface
suffix into an abstract one (archiphonemes) and realises it again for any host word. With that we can:

  * compatible(suffix, names): which candidate names would produce exactly this suffix (the leak),
  * reinflect(suffix, host):   rewrite the suffix to agree with a placeholder such as "AD SOYAD".
"""
from __future__ import annotations

import math, re

BACK, FRONT = set("aıouAIOU"), set("eiöüEİÖÜ")
VOWELS = set("aeıioöuüAEIİOÖUÜâîûÂÎÛ")
VOICELESS = set("çfhkpsştÇFHKPSŞT")
_LOW = {"I": "ı", "İ": "i"}

def lower(s: str) -> str:
    return "".join(_LOW.get(c, c) for c in s).lower()

def last_vowel(word: str) -> str | None:
    for c in reversed(lower(word)):
        if c in "aeıioöuüâîû": return {"â": "a", "î": "i", "û": "u"}.get(c, c)
    return None

def abstract(suffix: str) -> list[str] | None:
    """Surface suffix (without the apostrophe) -> archiphonemes, or None if it is not a regular
    harmonising suffix. A = a/e, I = ı/i/u/ü, D = d/t, C = c/ç, (n)/(y)/(s) = buffer letters that
    appear only after a vowel. Example: 'nin' -> ['(n)', 'I', 'n'],  'te' -> ['D', 'A']."""
    s = lower(suffix)
    if not s or not re.fullmatch(r"[a-zçğıöşü]+", s): return None
    out = []
    for i, c in enumerate(s):
        if i == 0 and c in "nys" and len(s) > 1 and (s[1] in "aeıiuü" or s[:2] == "yl"): out.append(f"({c})")
        elif c in "ae": out.append("A")
        elif c in "ıiuü": out.append("I")
        elif c in "dt" and i == 0: out.append("D")
        elif c in "cç" and i == 0: out.append("C")
        elif c in "oö": return None          # -yor, -ken etc.: not case suffixes on names
        else: out.append(c)
    # A suffix written without its buffer letter tells us the name ends in a consonant. Put the
    # buffer back in abstract form so that a vowel-final name does not look compatible.
    if out[0] in ("A", "I"):
        out.insert(0, "(n)" if out[0] == "I" and out[1:2] == ["n"] else "(y)")
    elif out[:2] == ["l", "A"]:
        out.insert(0, "(y)")
    return out

def realise(arch: list[str], host: str) -> str:
    """Archiphonemes -> surface form after `host` (the word the suffix attaches to)."""
    h = lower(host).rstrip(".")
    v = last_vowel(h) or "e"                 # digits/abbreviations: front default
    prev = h[-1] if h else "e"
    out = ""
    for a in arch:
        ctx_vowel = last_vowel(out) or v
        ends_vowel = (out[-1] if out else prev) in "aeıioöuüâîû"
        if a in ("(n)", "(y)", "(s)"):
            if ends_vowel: out += a[1]
        elif a == "A": out += "a" if ctx_vowel in "aıou" else "e"
        elif a == "I": out += {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "i": "i", "ö": "ü", "ü": "ü"}[ctx_vowel]
        elif a in ("D", "C"):
            last = out[-1] if out else prev
            voiceless = last in "çfhkpsşt"
            out += ("t" if voiceless else "d") if a == "D" else ("ç" if voiceless else "c")
        else: out += a
    return out

def compatible(suffix: str, candidates) -> list[str]:
    """Candidate names (last word) that would take exactly this surface suffix."""
    arch = abstract(suffix)
    if arch is None: return list(candidates)
    s = lower(suffix)
    return [c for c in candidates if realise(arch, c) == s]

def leak_bits(suffix: str, candidates) -> float:
    """How many bits the suffix reveals about the hidden name, with every candidate equally likely:
    log2(all candidates / candidates that fit)."""
    k = len(compatible(suffix, candidates))
    return math.log2(len(candidates) / k) if k else float("nan")

def reinflect(suffix: str, host: str) -> str:
    """Rewrite `suffix` to agree with `host` (e.g. the placeholder 'SOYAD'): leaks 0 bits, stays grammatical."""
    arch = abstract(suffix)
    return suffix if arch is None else realise(arch, host)

_APOS = re.compile(r"^(['’])([a-zçğıöşüA-ZÇĞIİÖŞÜ]+)")
def suffix_after(text: str, end: int) -> str | None:
    """The apostrophe suffix right after position `end`, if any ("'nın" -> "nın")."""
    m = _APOS.match(text[end:end + 12])
    return m.group(2) if m else None

def apply_mask(text: str, spans, placeholder: str = "[AD SOYAD]", mode: str = "keep") -> str:
    """Replace each (start, end) name span with `placeholder`.
    mode='keep'       : suffix left as written (today's behaviour, leaks)
    mode='reinflect'  : suffix rewritten to agree with the placeholder's last word
    mode='drop'       : suffix removed together with the name"""
    host = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ ]", "", placeholder).split()[-1] if placeholder.strip("[] ") else "X"
    out, last = [], 0
    for s, e in sorted(spans):
        out.append(text[last:s]); out.append(placeholder); last = e
        suf = suffix_after(text, e)
        if suf and mode != "keep":
            last = e + 1 + len(suf)
            if mode == "reinflect": out.append("'" + reinflect(suf, host))
    out.append(text[last:])
    return "".join(out)
