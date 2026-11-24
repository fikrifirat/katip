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
    if min(len(a), len(b)) >= 3 and (a.startswith(b) or b.startswith(a)) and (a in SECTOR or b in SECTOR):
        return 0.95  # "teks" / "tekstil", "ith" / "ithalat": a sector word written short
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


# Descriptive words of a Turkish trade name ("ALSULTAN KUYUMCULUK ELEKTRONİK GIDA İTH. İHR. LTD. ŞTİ."): the
# distinctive part is "Alsultan", the rest says what the company does. A listed name's sector words that the query
# leaves out cost less than a missing distinctive word, so "Alsultan Kuyumculuk" reaches review.
SECTOR = set("""elektronik gida insaat turizm tekstil teks medikal kuyumculuk otomotiv lojistik nakliyat nakliye petrol
urunleri urun pazarlama ithalat ihracat ticaret sanayi yapi madencilik enerji tarim hizmetleri hizmet danismanlik yazilim bilisim emlak gayrimenkul
giyim mobilya kimya plastik metal ambalaj dis disticaret yayinevi yayincilik matbaacilik saglik egitim tasimacilik
gida otomotiv akaryakit doviz kuyum mucevherat sarrafiye international trading""".split())
# Generic words a lawyer adds to an organisation's name ("Embrace Relief Foundation") that the list may not carry.
ORG_EXTRA = set("""foundation vakfi vakif dernegi dernek association group grubu holding organization organisation
international""".split())


def _glue(q: list[str], c: list[str]) -> list[str]:
    """'kuzey ruzgari' vs 'kuzeyruzgari': join two query words when the joined word is a candidate word."""
    cs = set(c)
    out, i = [], 0
    while i < len(q):
        if i + 1 < len(q) and q[i] + q[i + 1] in cs:
            out.append(q[i] + q[i + 1])
            i += 2
        else:
            out.append(q[i])
            i += 1
    return out


def name_score(q: list[str], c: list[str]) -> float:
    if not q or not c:
        return 0.0
    gq, gc = _glue(q, c), _glue(c, q)
    base = _name_score(q, c)
    return max(base, _name_score(gq, gc)) if (gq, gc) != (q, c) else base


def _name_score(q: list[str], c: list[str]) -> float:
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
    extra_q = sum(1 for i, t in enumerate(q) if i not in used_q and t in ORG_EXTRA)
    score = total / max(1, len(q) - extra_q) if len(q) - extra_q >= 2 else total / len(q)
    missing = [t for j, t in enumerate(c) if j not in used_c]
    score *= max(0.7, 1 - 0.08 * sum(t not in SECTOR for t in missing) - 0.03 * sum(t in SECTOR for t in missing))
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


# Turkish words of the names Turkish courts, MASAK's own organisation field and the press use for UN-listed groups,
# mapped to the list's spelling ("El-Kaide" -> "Al-Qaida", "DEAŞ Horasan" -> "ISIL Khorasan"). Used as a second
# query; a hit through it says so in its reasons.
TR_EN = {"kaide": "qaida", "kaida": "qaida", "deas": "isil", "daes": "isil", "isid": "isil", "ișid": "isil",
         "horasan": "khorasan", "dogu": "eastern", "islami": "islamic", "hareketi": "movement", "cephesi": "front",
         "lesker": "lashkar", "leskeri": "lashkar", "tayyibe": "tayyiba", "tayyibe": "tayyiba", "irak": "iraq",
         "devleti": "state", "islam": "islamic", "orgutu": "organization", "tugayi": "brigade", "tugaylari": "brigades",
         "nusra": "nusrah", "taliban": "taliban", "pakistan": "pakistan", "yemen": "yemen", "arap": "arabian",
         "yarimadasi": "peninsula", "magrip": "maghreb", "kuzey": "north"}


def translated(q: list[str]) -> list[str]:
    out = [TR_EN.get(t, t) for t in q if not (len(t) == 1 and t in "ie")]
    return out if out != q and any(t in TR_EN for t in q) else []


class ListIndex:
    """Index over structured list records (MASAK). Each record has ``names``: [primary, *aliases]."""

    def __init__(self, records: list[dict]):
        self.records = records
        self.variants = []  # (record_idx, text, toks)
        self.block = defaultdict(set)
        self.ids = defaultdict(set)
        for ri, r in enumerate(records):
            names = list(r.get("names", []))
            for name in r.get("names", []):  # "BANK SEPAH AND BANK SEPAH INTERNATIONAL": two names in one row
                parts = re.split(r"\s+(?:AND|And|and|VE|Ve|ve|&)\s+", name)
                if len(parts) == 2 and all(len(tokens(p)) >= 2 for p in parts) and \
                        tokens(parts[0])[0] == tokens(parts[1])[0]:
                    names += parts
            for name in names:
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
        q0 = tokens(query)
        qy = _year(birth)
        for q in [q0] + ([translated(q0)] if translated(q0) else []):
            self._score(q, q0, qy, floor, best)
        return sorted(best.values(), key=lambda h: -h.score)[:limit]

    def _score(self, q, q0, qy, floor, best):
        cand = set()
        for t in q:
            for k in self._keys(t):
                cand |= self.block.get(k, set())
        for vi in cand:
            ri, text, toks = self.variants[vi]
            s = name_score(q, toks)
            if s < floor:
                continue
            reasons = [] if q == q0 else ["Turkish name matched through its list spelling (" + " ".join(q) + ")"]
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
        self._search(q, floor, hits)
        if len(q) >= 2:  # "Kuzey Rüzgarı" written as one word in the notice ("KUZEYRÜZGARI")
            self._search([q[0] + q[1]] + q[2:], floor, hits)
        return sorted(hits.values(), key=lambda h: -h.score)[:limit]

    def _search(self, q, floor, hits):
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
