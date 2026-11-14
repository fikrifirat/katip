"""Fill the anonymised slots of a Turkish court decision with realistic synthetic PII and keep them as gold spans.

Courts publish decisions with personal data removed: "davacı ... vekili", "sanık A.K.'nın", "T.C. Kimlik
No: ***", "adresi ...". We find each slot, guess its type from the words around it, put a synthetic value
of that type there and record the span. Every inserted value is fake, so the output contains no real
person's data. See lab/legal/DESIGN.md, section 3.2.

  find_slots(text)            -> [Slot(start, end, kind, suffix)]
  fill(text, rng, pool)       -> {"text", "spans": [[a, b, TYPE]], "n_slots", "by_type"}

Types follow Katip's entity names: PERSON, TCKN, PHONE, EMAIL, IBAN, PLATE, BIRTH_DATE, ADDRESS.
Slots that hold a place or an institution ("... 3. Asliye Hukuk Mahkemesi") are filled with a province
and kept as LOC_ORG spans: not PII, but tracked so a detector that masks them is counted separately.
"""
from __future__ import annotations

import random, re, sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import suffix as S  # noqa: E402

import katiplab as K  # noqa: E402  (unpacks the Pyodide bundle into the temp folder on import)
_DATA = K._bundle / "katip_redact" / "data"
UP = "A-ZÇĞİÖŞÜ"
LO = "a-zçğıöşü"

def upper_tr(s): return s.replace("i", "İ").replace("ı", "I").upper()
def lower_tr(s): return s.replace("I", "ı").replace("İ", "i").lower()
def title_tr(s): return " ".join(upper_tr(w[:1]) + lower_tr(w[1:]) for w in s.split())

# ------------------------------------------------------------------------------------- slot finding
# "(...)" and "[...]" are quotation omissions, not anonymisation.
_DOTS = r"(?<![\(\[])(?:\.{3,}|…+)(?![\)\]])"
_STARS = r"\*{3,}"
_XS = rf"(?<![{UP}{LO}])X{{1,4}}(?![{UP}{LO}])"
_INIT = rf"(?<![{UP}{LO}.])(?:[{UP}]\.\s?){{1,3}}(?=[\s,;:'’)]|$)"
SLOT_RE = re.compile(rf"(?:{_DOTS}|{_STARS}|{_XS}|{_INIT})")
_APOS = re.compile(rf"^\s?(['’])([{LO}]+)")

# Initials that are abbreviations, never people.
NOT_INITIALS = {"T.C.", "E.", "K.", "T.", "S.", "No.", "A.Ş.", "Ş.", "M.", "Md.", "Bkz.", "vs.", "Dr.", "Av.", "Prof.",
                "Doç.", "Yrd.", "Öğr.", "Gör.", "Sn.", "C.", "D.", "İ.", "H.", "B.", "TC.", "A.", "Y."}
PERSON_CUES = ("davacı", "davalı", "sanık", "başvurucu", "müşteki", "mağdur", "katılan", "tanık", "vekil", "av.",
               "avukat", "bilirkişi", "şüpheli", "müdahil", "temsilci", "eşi", "oğlu", "kızı", "annesi", "babası",
               "murisi", "mirasçı", "alacaklı", "borçlu", "hakim", "hâkim", "üye", "başkan", "savcı", "katip",
               "kâtip", "müdafi", "itiraz eden", "ihbar olunan", "adı", "isimli", "adlı", "kişi", "çocuk")
TYPE_CUES = [  # (type, words just before the slot)
    ("TCKN", ("kimlik no", "kimlik numara", "tckn", "t.c. no", "tc no", "t.c. kimlik")),
    ("PHONE", ("tel", "telefon", "gsm", "cep")),
    ("IBAN", ("iban", "hesap no", "hesap numara")),
    ("PLATE", ("plaka",)),
    ("EMAIL", ("e-posta", "eposta", "e-mail", "mail")),
    ("BIRTH_DATE", ("doğum tarihi", "doğumlu", "d.t.", "d.tarihi")),
    ("ADDRESS", ("adres", "ikamet", "mukim", "oturan", "yerleşim yeri")),
]
ORG_AFTER = re.compile(rf"^\s*(?:\d+\s*\.\s*)?(?:[{UP}][{LO}]+\s+)?(?:AŞ|A\.Ş|San\b|Tic\b|Organize|Yapı|Taahhüt|Holding|Kooperatif|Derneği|Vakfı|firma|şirket|Esas\b|Karar\b|Asliye|Ağır|Sulh|İcra|Aile|İş|Tüketici|Ticaret|Mahkemesi|"
                       rf"Cumhuriyet|Noterliği|Belediye|Valiliği|Kaymakamlığı|Müdürlüğü|Bakanlığı|Başkanlığı|Ltd|A\.Ş|Şirketi|"
                       rf"Bölge|Vergi|İdare|Tapu|Nüfus|Hastanesi|Üniversitesi|Barosu|ili\b|ilçesi|Köyü)")
STREET_AFTER = re.compile(rf"^\s*(?:Mahallesi|Mah\.|Sokak|Sok\.|Sk\.|Caddesi|Cad\.|Cd\.|Bulvarı|Blv\.|Apt|No\s*:?\s*\d)")
DATE_NEAR = re.compile(r"^\s*[/.]\s*\d|^\d")

@dataclass
class Slot:
    start: int
    end: int
    kind: str           # PERSON, TCKN, ..., STREET (part of an address), LOC_ORG, DATE_PART, or SKIP
    suffix: str | None  # case suffix after a person slot ("nın")

def _kind(text: str, a: int, b: int, token: str, prev_end: int = 0) -> str:
    before = lower_tr(text[max(0, a - 40):a])
    near = lower_tr(text[max(prev_end, a - 22):a])  # cue words only since the previous slot
    after = text[b:b + 40]
    if DATE_NEAR.match(after) or re.search(r"\d\s*[/.]\s*$", text[max(0, a - 4):a]): return "DATE_PART"
    if ORG_AFTER.match(after): return "LOC_ORG"
    if STREET_AFTER.match(after): return "STREET"
    for typ, cues in TYPE_CUES:
        if any(c in near for c in cues): return typ
    is_init = token[:1].isupper() and token not in ("X", "XX", "XXX", "XXXX")
    if is_init:
        if token.replace(" ", "") in NOT_INITIALS: return "SKIP"
        return "PERSON" if any(c in before[-30:] for c in PERSON_CUES) or _APOS.match(after) else "SKIP"
    return "PERSON"

def find_slots(text: str) -> list[Slot]:
    out, prev = [], 0
    for m in SLOT_RE.finditer(text):
        a, b = m.span()
        k = _kind(text, a, b, m.group(0).strip(), prev); prev = b
        if k == "SKIP": continue
        sm = _APOS.match(text[b:b + 14])
        out.append(Slot(a, b, k, sm.group(2) if sm and k == "PERSON" else None))
    return out

# ------------------------------------------------------------------------------------- value makers
def _lines(name):
    p = _DATA / name
    return [w.strip() for w in p.read_text(encoding="utf-8").split("\n") if w.strip()] if p.exists() else []

def tckn(rng):
    d = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(8)]
    d10 = ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
    d11 = (sum(d) + d10) % 10
    return "".join(map(str, d + [d10, d11]))

def iban(rng):
    bban = f"{rng.randint(0, 99999):05d}0" + "".join(str(rng.randint(0, 9)) for _ in range(16))
    num = int("".join(str(int(c, 36)) for c in bban + "TR00"))
    chk = 98 - num % 97
    s = f"TR{chk:02d}{bban}"
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4)) if rng.random() < .6 else s

def phone(rng):
    n = f"5{rng.randint(30, 59)}{rng.randint(0, 9999999):07d}"
    return rng.choice([f"0{n[:3]} {n[3:6]} {n[6:8]} {n[8:]}", f"0{n}", f"+90 {n[:3]} {n[3:6]} {n[6:]}", f"({n[:3]}) {n[3:6]} {n[6:]}"])

PLATE_CODES = list(range(1, 82))
def plate(rng):
    L = "ABCDEFGHJKLMNPRSTUVYZ"
    return f"{rng.choice(PLATE_CODES):02d} {''.join(rng.choice(L) for _ in range(rng.randint(1, 3)))} {rng.randint(10, 9999)}"

def birth_date(rng):
    return f"{rng.randint(1, 28):02d}{rng.choice('./')}{rng.randint(1, 12):02d}{rng.choice('./')}{rng.randint(1940, 2005)}"

class Pool:
    """First names and surnames for one split. 'train' and 'test' pools are disjoint."""
    def __init__(self, split: str, seed: int = 0):
        first, last = _lines("first_names.txt"), _lines("last_names.txt")
        rng = random.Random(1234)  # the split itself is fixed, whatever seed fills it
        rng.shuffle(first); rng.shuffle(last)
        cut_f, cut_l = int(len(first) * .7), int(len(last) * .7)
        self.first = [title_tr(w) for w in (first[:cut_f] if split == "train" else first[cut_f:])]
        self.last = [title_tr(w) for w in (last[:cut_l] if split == "train" else last[cut_l:])]
        self.provinces = [title_tr(w) for w in _lines("provinces.txt")]
        self.districts = [title_tr(w) for w in _lines("districts.txt")]

    def person(self, rng):
        f = rng.choice(self.first)
        if rng.random() < .15: f += " " + rng.choice(self.first)
        l = rng.choice(self.last); r = rng.random()
        return f"{f} {l}" if r < .4 else f"{f} {upper_tr(l)}" if r < .8 else upper_tr(f"{f} {l}")

    def email(self, rng):
        f, l = lower_tr(rng.choice(self.first)), lower_tr(rng.choice(self.last))
        tr = str.maketrans("çğıöşü", "cgiosu")
        return f"{f.translate(tr)}{rng.choice(['.', '_', ''])}{l.translate(tr)}@{rng.choice(['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com'])}"

    def address(self, rng):
        mah = rng.choice(self.last) + " Mahallesi"
        street = f"{rng.choice(self.first)} {rng.choice(['Sokak', 'Caddesi', 'Sk.', 'Cad.'])}"
        return f"{mah} {street} No: {rng.randint(1, 180)}/{rng.randint(1, 30)} {rng.choice(self.districts)}/{rng.choice(self.provinces)}"

def value(kind: str, rng, pool: Pool) -> str:
    return {"PERSON": lambda: pool.person(rng), "TCKN": lambda: tckn(rng), "PHONE": lambda: phone(rng),
            "IBAN": lambda: iban(rng), "PLATE": lambda: plate(rng), "EMAIL": lambda: pool.email(rng),
            "BIRTH_DATE": lambda: birth_date(rng), "ADDRESS": lambda: pool.address(rng),
            "LOC_ORG": lambda: rng.choice(pool.provinces), "STREET": lambda: rng.choice(pool.last), "DATE_PART": lambda: f"{rng.randint(1, 28):02d}"}[kind]()

# ------------------------------------------------------------------------------------------- filling
PII = {"PERSON", "TCKN", "PHONE", "EMAIL", "IBAN", "PLATE", "BIRTH_DATE", "ADDRESS"}

def fill(text: str, rng: random.Random, pool: Pool) -> dict:
    """Replace every slot; return the new text and gold spans (PII types + LOC_ORG)."""
    out, spans, pos, by_type = [], [], 0, {}
    n = 0
    for s in find_slots(text):
        if s.start < pos: continue
        out.append(text[pos:s.start]); cur = sum(map(len, out))
        v = value(s.kind, rng, pool)
        out.append(v)
        kind = "ADDRESS" if s.kind == "STREET" else s.kind
        if kind in PII or kind == "LOC_ORG":
            spans.append([cur, cur + len(v), kind]); by_type[kind] = by_type.get(kind, 0) + 1
        pos = s.end; n += 1
        if s.suffix:  # re-inflect the following case suffix so it agrees with the new name
            m = _APOS.match(text[pos:pos + 14])
            out.append(m.group(1) + S.reinflect(m.group(2), v)); pos += m.end()
    out.append(text[pos:])
    t = "".join(out)
    t2 = re.sub(r" {2,}", " ", t)
    if t2 != t:  # keep offsets valid if we collapse spaces: recompute spans by search order
        t2, spans = _recompute(t, spans)
    return {"text": t2, "spans": spans, "n_slots": n, "by_type": by_type}

def _recompute(t, spans):
    # collapse runs of spaces and shift offsets
    keep, mapping = [], []
    prev_space = False
    for i, ch in enumerate(t):
        sp = ch == " "
        if sp and prev_space: mapping.append(len(keep)); continue
        mapping.append(len(keep)); keep.append(ch); prev_space = sp
    mapping.append(len(keep))
    return "".join(keep), [[mapping[a], mapping[b], k] for a, b, k in spans]
