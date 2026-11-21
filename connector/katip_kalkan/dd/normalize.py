"""Name normalisation for Turkish public-list screening.

Three layers, each used by the matcher:

1. ``fold``      Turkish-aware lower case, diacritics removed, punctuation to spaces.
                 "ŞAHİN İnşaat A.Ş." -> "sahin insaat a s"
2. ``tokens``    fold, then split, drop company legal forms ("a s", "ltd sti", "llc") and
                 name particles that transliterate inconsistently ("al", "el", "bin", "ibn").
3. ``skeleton``  a rough phonetic key per token for transliterated Arabic, Persian and Russian
                 names: Mohammed / Muhammad / Muhammed / Mohamad all give "mhmd".

Only the standard library is used, so the module runs anywhere Katip runs.
"""
from __future__ import annotations

import re
import unicodedata

# Turkish dotted/dotless i must be handled before generic lower(): Python maps "I" -> "i",
# which is wrong for Turkish ("ILGAZ" is "ılgaz"). After folding both end up as "i" anyway,
# but we keep the right order so "İ" never becomes "i̇" (i + combining dot).
_TR_UPPER = str.maketrans({"İ": "i", "I": "ı"})
_FOLD = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "â": "a", "î": "i", "û": "u", "ê": "e", "ô": "o",
    "ß": "ss", "æ": "ae", "ø": "o", "đ": "d", "ł": "l",
})

# Company forms and filler words. Matching is on tokens after fold().
_LEGAL_FORMS = {
    "a", "s", "as", "aş", "ltd", "sti", "limited", "sirketi", "anonim", "sirket", "ortakligi",
    "kollektif", "komandit", "kooperatifi", "koop", "ve", "tic", "ticaret", "san", "sanayi",
    "ith", "ihr", "ithalat", "ihracat", "pazarlama", "llc", "inc", "co", "corp", "corporation",
    "company", "gmbh", "ag", "sa", "srl", "bv", "nv", "plc", "fze", "fzco", "jsc", "ojsc", "cjsc",
    "ooo", "zao", "pjsc", "and", "the", "of",
}
# Particles in transliterated names. Dropped from scoring, because sources disagree on them
# ("ABD AL-BASET" / "ABDELBASSED" / "ABDUL BASET").
_PARTICLES = {"al", "el", "ul", "ad", "ed", "as", "es", "an", "en", "bin", "ibn", "bint", "abu", "ebu", "bn", "b"}


def fold(text: str) -> str:
    """Turkish-aware lower case, strip diacritics, keep letters and digits only."""
    if not text:
        return ""
    s = text.translate(_TR_UPPER).lower().translate(_FOLD)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_LONG_FORMS = [f for f in _LEGAL_FORMS if len(f) >= 6]


def _near_form(t: str) -> bool:
    """'şriketi', 'limitet': a misspelt legal form is still a legal form."""
    if len(t) < 6:
        return False
    from difflib import SequenceMatcher

    return any(SequenceMatcher(None, t, f).ratio() >= 0.85 for f in _LONG_FORMS)


def tokens(text: str, *, company: bool | None = None) -> list[str]:
    """Folded tokens without legal forms and particles.

    ``company=None`` drops legal forms only when at least one other token stays, so the
    name "Sanayi" on its own is not emptied.
    """
    toks = [t for t in fold(text).split() if t]
    toks = [t for t in toks if t not in _PARTICLES] or toks
    if company is not False:
        kept = [t for t in toks if t not in _LEGAL_FORMS and not _near_form(t)]
        if kept:
            toks = kept
    return toks


_SKEL_RULES = [
    ("sch", "s"), ("tch", "c"), ("ch", "c"), ("sh", "s"), ("zh", "j"), ("kh", "h"), ("gh", "g"),
    ("ph", "f"), ("th", "t"), ("dh", "d"), ("ou", "u"), ("ee", "i"), ("oo", "u"), ("ck", "k"),
    ("q", "k"), ("w", "v"), ("x", "ks"), ("y", "i"), ("j", "c"), ("ts", "s"),
]
_VOWELS = set("aeiou")

# Common given names whose spellings vary by transliteration. Same group = same name.
# Deliberately NOT merged: Mehmet with Muhammad, Hasan with Hüseyin (different names in Turkish).
_EQUIV_GROUPS = [
    "muhammad mohammed mohamed muhammed mohammad mohamad muhamad mohamud muhamed mohamet mohd",
    "ahmad ahmed ahmet",
    "hussein husayn hussain husain huseyin hussien",
    "hassan hasan hasen",
    "abdallah abdullah abdulla abdellah",
    "abd abdul abdel abdal abdil abdoul",
    "yusuf yousef youssef yousif yusef yosef",
    "omar umar omer",
    "osama usama usame oussama",
    "ali aly",
    "mahmoud mahmud mahmut",
    "ibrahim ebrahim ibraheem",
    "mustafa mostafa moustafa mustapha",
    "khalid khaled halid halit",
    "said saeed sayed sayyid seyit seyyid",
    "abdulrahman abdurrahman abdelrahman abdalrahman abdourahmane",
    "abdulaziz abdelaziz abdulaziz",
    "jamal cemal gamal",
    "salah salih saleh",
    "yasin yassin yaseen",
]
EQUIV = {w: i for i, g in enumerate(_EQUIV_GROUPS) for w in g.split()}


def canon(token: str) -> str:
    """Transliteration-normalised spelling, vowels kept: wali -> vali, yar -> iar, hwi -> hvi."""
    t = token
    for a, b in _SKEL_RULES:
        t = t.replace(a, b)
    out = []
    for ch in t:
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)


def skeleton(token: str) -> str:
    """Rough consonant key for one folded token. Keeps the first letter, drops vowels,
    collapses repeats. Two tokens with the same skeleton are treated as transliterations."""
    t = token
    for a, b in _SKEL_RULES:
        t = t.replace(a, b)
    if not t:
        return ""
    out = [t[0]]
    for ch in t[1:]:
        if ch in _VOWELS or ch == "h":
            continue
        if out[-1] != ch:
            out.append(ch)
    return "".join(out)


def digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def split_aliases(raw: str) -> list[str]:
    """Split the free-text alias fields MASAK publishes:
    "a) Office #39b) Office No. 39c) Bureau 39", "X,Y,Z", "X - Y - < Z >", newline lists."""
    if not raw:
        return []
    s = raw.replace("\r", "\n")
    # "a)", "b)" ... enumerations, also glued to the previous word ("#39b)")
    s = re.sub(r"(?:(?<=\s)|(?<=^)|(?<=[0-9#.]))[a-zçğıöşü]\)\s*", "\n", s)
    parts = re.split(r"[\n,;]| - |\s<\s|\s>\s|[<>]", s)
    out = []
    for p in parts:
        p = p.strip(" .-:\t")
        if len(fold(p)) >= 3 and fold(p) not in {"isminin ilk harfleri"}:
            out.append(p)
    # keep order, drop duplicates after folding
    seen, uniq = set(), []
    for p in out:
        k = fold(p)
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def id_tokens(text: str) -> list[str]:
    """ID-like tokens (TCKN, VKN, YKN, passport) from a free-text field such as
    "76501031676/0471903308" or "Yemen pasaport 00385937". Upper-case alphanumerics,
    at least 6 characters and at least 5 digits."""
    out = []
    for t in re.split(r"[\s/,;:]+", (text or "").upper()):
        t = re.sub(r"[^0-9A-Z]", "", t)
        if len(t) >= 6 and sum(ch.isdigit() for ch in t) >= 5:
            out.append(t)
    return out


_NUM = re.compile(r"\b\d{10,11}\b")
_VKN_LABEL = re.compile(r"(vergi|v\.?\s?k\.?\s?n|vkn)[^\d]{0,25}$", re.I)


def vkn_ok(s: str) -> bool:
    """Turkish 10-digit tax number (VKN) checksum, as published by the Revenue Administration."""
    if not re.fullmatch(r"\d{10}", s or ""):
        return False
    d, tot = [int(c) for c in s], 0
    for i in range(9):
        t = (d[i] + 9 - i) % 10
        v = (t * 2 ** (9 - i)) % 9
        tot += 9 if t and not v else v
    return (10 - tot % 10) % 10 == d[9]


def mask_ids(text: str, label: str = "[kimlik no]") -> str:
    """Mask 10-11 digit numbers that could identify a person (TCKN, YKN, phone).

    A 10-digit number is kept only when it passes the VKN checksum and the words just before it
    name it as a tax number (vergi no, VKN): a company's tax number is not personal data and helps
    DD. Every 11-digit number is masked: TCKN and YKN are 11 digits.
    """
    def sub(m):
        n = m.group(0)
        if len(n) == 10 and vkn_ok(n) and _VKN_LABEL.search(text[max(0, m.start() - 40): m.start()]):
            return n
        return label
    return _NUM.sub(sub, text or "")
