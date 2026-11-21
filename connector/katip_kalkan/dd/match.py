"""Fuzzy name matching over listed records and over free-text notices.

Score in [0, 1]. Built from token similarities so word order, dropped middle names,
Turkish diacritics and common transliterations do not hide a match.

  token_sim:  1.0 identical, 0.93 same phonetic skeleton, else Jaro-Winkler
  name score: mean best similarity per query token, minus a small penalty per
              candidate token the query did not cover; a one-word query is capped,
              because one word is never enough to say "this is the listed person".
  ID numbers: an exact TCKN/VKN/passport match scores 1.0 regardless of the name.
  Birth year: a different year lowers the score (x0.85) and is shown as a reason.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .normalize import EQUIV, mask_ids, canon, fold, id_tokens, skeleton, tokens

TOKEN_MIN = 0.85
MATCH = 0.93   # tuned on the dev split in eval_dd.py, reported on the test split
REVIEW = 0.86


def jaro_winkler(a: str, b: str) -> float:
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if not la or not lb:
        return 0.0
    rng = max(la, lb) // 2 - 1
    am, bm = [False] * la, [False] * lb
    m = 0
    for i, ch in enumerate(a):
        lo, hi = max(0, i - rng), min(i + rng + 1, lb)
        for j in range(lo, hi):
            if not bm[j] and b[j] == ch:
                am[i] = bm[j] = True
                m += 1
                break
    if not m:
        return 0.0
    t, k = 0, 0
    for i in range(la):
        if am[i]:
            while not bm[k]:
                k += 1
            if a[i] != b[k]:
                t += 1
            k += 1
    t /= 2
    jaro = (m / la + m / lb + (m - t) / m) / 3
    p = 0
    for x, y in zip(a[:4], b[:4]):
        if x != y:
            break
        p += 1
    return jaro + p * 0.1 * (1 - jaro)


def token_sim(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if a in EQUIV and EQUIV.get(b) == EQUIV[a]:
        return 0.97
    for x, y in ((a, b), (b, a)):  # "alshawakh" vs "shawakh": particle glued on
        if len(x) > 6 and x[:2] in ("al", "el") and x[2:] == y:
            return 0.97
    if min(len(a), len(b)) >= 3 and canon(a) == canon(b):
        return 0.97
    if len(a) == 1 or len(b) == 1:  # initials
        return 0.7 if a[0] == b[0] else 0.0
    sa, sb = skeleton(a), skeleton(b)
    jw = jaro_winkler(a, b)
    # same consonant skeleton = likely transliteration (Mohammed/Muhammad). Guarded by JW,
    # because short Turkish names share skeletons too (Hasan/Hüseyin, Turan/Tören).
    if min(len(a), len(b)) >= 4 and len(sa) >= 3 and sa == sb and jw >= 0.8:
        return max(jw, 0.93)
    ratio = min(len(a), len(b)) / max(len(a), len(b))
    if ratio < 0.75:  # "abdul" is a prefix of "abdulbaset", not the same name
        jw *= 0.6 + 0.4 * ratio
    return jw


def name_score(q: list[str], c: list[str]) -> float:
    if not q or not c:
        return 0.0
    pairs = sorted(((token_sim(x, y), i, j) for i, x in enumerate(q) for j, y in enumerate(c)), reverse=True)
    used_q, used_c, total = set(), set(), 0.0
    for s, i, j in pairs:
        if s < TOKEN_MIN:  # a different surname counts as no match at all, not as "80% similar"
            break
        if i in used_q or j in used_c:
            continue
        used_q.add(i)
        used_c.add(j)
        total += 1 - 2 * (1 - s)  # stretch: a 0.91 surname is a different name more often than a typo
    score = total / len(q)
    score *= max(0.7, 1 - 0.08 * (len(c) - len(used_c)))
    # glued vs split spellings: "ABDELBASSED" vs "ABD AL-BASET"
    jq, jc = "".join(q), "".join(c)
    if len(q) != len(c) and min(len(jq), len(jc)) >= 6 and min(len(jq), len(jc)) / max(len(jq), len(jc)) >= 0.8:
        jw = jaro_winkler(jq, jc)
        if jw >= 0.95:
            score = max(score, round(0.97 * jw, 4))
    if len(q) == 1 and len(c) > 1:
        score = min(score, 0.8)
    return round(min(score, 1.0), 4)


def _year(s: str) -> str | None:
    m = re.findall(r"(?:18|19|20)\d\d", s or "")
    return m[0] if len(m) == 1 else None  # "a)1970 b)1971" is ambiguous -> no penalty


@dataclass
class Hit:
    score: float
    band: str
    matched: str
    record: dict
    reasons: list = field(default_factory=list)


def band(score: float) -> str:
    return "match" if score >= MATCH else "review" if score >= REVIEW else "weak"


class ListIndex:
    """Index over structured list records (MASAK). Each record has ``names``: [primary, *aliases]."""

    def __init__(self, records: list[dict]):
        self.records = records
        self.variants = []  # (record_idx, text, toks)
        self.block = defaultdict(set)
        self.ids = defaultdict(set)
        for ri, r in enumerate(records):
            for name in r.get("names", []):
                toks = tokens(name)
                if not toks:
                    continue
                vi = len(self.variants)
                self.variants.append((ri, name, toks))
                for t in toks:
                    for k in self._keys(t):
                        self.block[k].add(vi)
            for i in r.get("ids", []):
                for d in id_tokens(i):
                    self.ids[d].add(ri)

    @staticmethod
    def _keys(t: str):
        yield "p:" + t[:2]
        yield "s:" + skeleton(t)[:3]

    def search(self, query: str, *, id_no: str = "", birth: str = "", limit: int = 10, floor: float = 0.75) -> list[Hit]:
        best: dict[int, Hit] = {}
        for d in id_tokens(id_no):
            for ri in self.ids.get(d, ()):
                best[ri] = Hit(1.0, "match", f"ID {d}", self.records[ri], ["ID number identical"])
        q = tokens(query)
        cand = set()
        for t in q:
            for k in self._keys(t):
                cand |= self.block.get(k, set())
        qy = _year(birth)
        for vi in cand:
            ri, text, toks = self.variants[vi]
            s = name_score(q, toks)
            if s < floor:
                continue
            reasons = []
            ry = _year(self.records[ri].get("birth", ""))
            if qy and ry:
                if qy == ry:
                    reasons.append(f"birth year {ry} matches")
                else:
                    s = round(s * 0.85, 4)
                    reasons.append(f"birth year differs ({ry} on list)")
            if ri not in best or s > best[ri].score:
                if ri in best and best[ri].matched.startswith("ID"):
                    continue
                best[ri] = Hit(s, band(s), text, self.records[ri], reasons)
        return sorted(best.values(), key=lambda h: -h.score)[:limit]


class TextIndex:
    """Mentions of a name inside free-text notices (ilan.gov.tr, Ticaret Sicili Gazetesi).

    Finds a window of consecutive words that matches the query tokens, in any order,
    with at most two extra words in between ("ABC İNŞAAT TURİZM SANAYİ VE TİCARET A.Ş.").
    """

    def __init__(self, docs: list[dict]):
        self.docs = docs
        self.toks = []
        self.block = defaultdict(set)
        for di, d in enumerate(docs):
            toks = fold(d.get("text", "")).split()
            self.toks.append(toks)
            for pos, t in enumerate(toks):
                self.block["p:" + t[:2]].add((di, pos))

    def search(self, query: str, *, limit: int = 10, floor: float = 0.86) -> list[Hit]:
        q = tokens(query)
        if not q:
            return []
        hits: dict[int, Hit] = {}
        anchors = self.block.get("p:" + q[0][:2], set())
        for di, pos in anchors:
            toks = self.toks[di]
            if token_sim(q[0], toks[pos]) < 0.8:
                continue
            for lo in range(max(0, pos - len(q) - 1), pos + 1):
                window = toks[lo: lo + len(q) + 2]
                wt = tokens(" ".join(window)) or window
                # only score the part of the window that the query can cover
                s = name_score(q, wt[: len(q) + 1]) if wt else 0.0
                if s >= floor and (di not in hits or s > hits[di].score):
                    start = max(0, lo - 8)
                    # mask 11-digit numbers (TCKN/VKN) of other people named in the notice
                    snippet = mask_ids(" ".join(toks[start: lo + len(q) + 10]))
                    notes = [f"…{snippet}…"]
                    if self.docs[di].get("full_text") is False:
                        notes.append("title/summary only: notice page was not opened, check the full notice")
                    span = window[: len(q)] if name_score(q, (tokens(" ".join(window[: len(q)])) or window)[: len(q)]) >= s else window[: len(q) + 1]
                    hits[di] = Hit(s, band(s), " ".join(span), self.docs[di], notes)
        return sorted(hits.values(), key=lambda h: -h.score)[:limit]
