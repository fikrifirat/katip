# Vendored from docs/katip_py.zip (katip_redact/recognizers.py) by sdk/tools/sync_engine.py. Do not edit here:
# change the engine at its source and re-run the sync, so the SDK, the demo and Kalkan stay identical.
"""Turkish PII recognizers.

Each recognizer is a Presidio ``EntityRecognizer`` so it can be dropped into any
Presidio deployment, and so we can add Presidio's built-ins or a transformer NER
recognizer next to ours without changing the pipeline.

Design rule: anything with a checksum (TCKN, VKN, IBAN, card) is validated, so
a random 11-digit number never gets masked as a TC kimlik no. Anything without
a checksum (phone, plate, name, address) needs either a strict shape or a
context word.
"""
from __future__ import annotations

import re
from typing import Iterable

from katip_mask._engine._presidio_shim import EntityRecognizer, RecognizerResult

from .textutil import (TR_LETTER, TR_LOWER, TR_UPPER, fold, is_all_caps,
                       is_capitalised, wordlist)

# ---------------------------------------------------------------- entity types
ENTITY_LABELS_TR = {
    "TCKN": "T.C. Kimlik No",
    "VKN": "Vergi Kimlik No",
    "IBAN": "IBAN",
    "CREDIT_CARD": "Kredi Kartı",
    "PHONE": "Telefon",
    "EMAIL": "E-posta",
    "PLATE": "Araç Plakası",
    "PERSON": "Ad Soyad",
    "ADDRESS": "Adres",
    "BIRTH_DATE": "Doğum Tarihi",
    "IP_ADDRESS": "IP Adresi",
    "YKN": "Yabancı Kimlik No",
    "PASSPORT": "Pasaport No",
    "FOREIGN_ID": "Yabancı Ülke Kimlik No",
    "UETS": "UETS (e-Tebligat) Adresi",
}
ALL_ENTITIES = list(ENTITY_LABELS_TR)


def _context_before(text: str, start: int, window: int = 60) -> str:
    return fold(text[max(0, start - window):start])


def _fold_keep(s: str) -> str:
    """fold() one character at a time, so offsets into the result are offsets into the original."""
    return "".join((fold(c) or c)[0] for c in s)


def _has_context(text: str, start: int, words: Iterable[str], window: int = 60) -> bool:
    ctx = _context_before(text, start, window)
    return any(w in ctx for w in words)


class _Base(EntityRecognizer):
    ENTITY = ""
    NAME = ""

    def __init__(self):
        super().__init__(supported_entities=[self.ENTITY], name=self.NAME,
                         supported_language="tr")

    def load(self):  # presidio hook
        pass

    def _r(self, start, end, score, why=""):
        r = RecognizerResult(self.ENTITY, start, end, score)
        r.recognition_metadata = {
            RecognizerResult.RECOGNIZER_NAME_KEY: self.NAME,
            "explanation": why,
        }
        return r


# ---------------------------------------------------------------- checksums
def tckn_valid(d: str) -> bool:
    if len(d) != 11 or not d.isdigit() or d[0] == "0":
        return False
    n = [int(c) for c in d]
    d10 = ((n[0] + n[2] + n[4] + n[6] + n[8]) * 7 - (n[1] + n[3] + n[5] + n[7])) % 10
    return d10 == n[9] and sum(n[:10]) % 10 == n[10]


def vkn_valid(d: str) -> bool:
    if len(d) != 10 or not d.isdigit():
        return False
    total = 0
    for i in range(9):
        tmp = (int(d[i]) + (9 - i)) % 10
        v = (tmp * 2 ** (9 - i)) % 9
        if tmp != 0 and v == 0:
            v = 9
        total += v
    return (10 - total % 10) % 10 == int(d[9])


def iban_valid(s: str) -> bool:
    s = re.sub(r"\s", "", s).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    if s.startswith("TR") and len(s) != 26:
        return False
    num = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(num) % 97 == 1


def luhn_valid(d: str) -> bool:
    d = re.sub(r"\D", "", d)
    if not 13 <= len(d) <= 19:
        return False
    s, alt = 0, False
    for c in reversed(d):
        x = int(c)
        if alt:
            x *= 2
            if x > 9:
                x -= 9
        s += x
        alt = not alt
    return s % 10 == 0


# ---------------------------------------------------------------- recognizers
class TCKNRecognizer(_Base):
    """TCKN, and the foreigner's ID number (Yabancı Kimlik No, YKN): 11 digits starting with 99, same checksum."""
    ENTITY, NAME = "TCKN", "tckn_checksum"
    YKN_CTX = ("yabanci kimlik", "ykn", "y.k.n", "gecici koruma", "yabanci", "ikamet", "uyruklu")
    # a number after these is a home-country ID or passport, not a TCKN (ForeignIDRecognizer / PassportRecognizer)
    NOT_TC = ("pasaport", "passport", "ulusal", "national", "melli", "tazkira", "tezkire", "personal no", "kisisel",
              "ssn", "social security", "sosyal guvenlik no", "amka", "ausweis", "cni", "dni", "bsn", "fin")

    def __init__(self):
        super().__init__()
        self.supported_entities = ["TCKN", "YKN"]

    def _r(self, start, end, score, why="", entity=None):
        r = super()._r(start, end, score, why)
        if entity: r.entity_type = entity
        return r
    # 11 digits, optionally spaced; or grouped 3-3-3-2 with dots or dashes ("532.830.965.12", "614-371-928-12")
    RE = re.compile(r"(?<!\d)([1-9](?:[ ]?\d){10}(?!\d)|(?<![.-])[1-9]\d\d\.\d{3}\.\d{3}\.\d\d(?!\d|[.,]\d)|(?<![.-])[1-9]\d\d-\d{3}-\d{3}-\d\d(?!\d|-\d))")
    CTX = ("kimlik", "tckn", "t.c", "tc no", "tc:", "vatandaslik")
    LABELLED = re.compile(r"(?:[Kk]imlik\s*(?:No|no|Numaras[ıi]|numaras[ıi])|KİMLİK\s*(?:NO|NUMARASI)|TCKN|YKN|T\.?C\.?\s*No|TC\s*No)\s*[:.]?\s*([0-9OoIl]{10,13})(?![\d])")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RE.finditer(text):
            digits = re.sub(r"\D", "", m.group(1))
            if tckn_valid(digits) and digits.startswith("99"):
                score = 0.95 if _has_context(text, m.start(), self.YKN_CTX + self.CTX) else 0.85
                out.append(self._r(m.start(1), m.end(1), score, "11 digits from 99, TCKN checksum ok: foreigner ID (YKN)", "YKN"))
            elif tckn_valid(digits):
                score = 0.95 if _has_context(text, m.start(), self.CTX) else 0.85
                out.append(self._r(m.start(1), m.end(1), score, "11 digits, TCKN checksum ok"))
        # OCR can drop, add or swap a digit; right after a TCKN label, mask any 10-13 digit number anyway
        for m in self.LABELLED.finditer(text):
            if "vergi" in fold(text[max(0, m.start() - 8):m.start()]):   # "Vergi Kimlik No": a tax ID (VKNRecognizer)
                continue
            if _has_context(text, m.start(1), self.NOT_TC, 40) and not _has_context(text, m.start(1), ("yabanci kimlik",), 30):
                continue
            if not any(r.start <= m.start(1) < r.end for r in out):
                ykn = _has_context(text, m.start(1), ("yabanci kimlik", "ykn", "y.k.n", "gecici koruma"), 30) or m.group(1).startswith("99")
                out.append(self._r(m.start(1), m.end(1), 0.7, "number after an ID label (checksum failed, likely OCR)", "YKN" if ykn else None))
        return out


# ---------------------------------------------------------------- foreign clients: passports and home-country IDs
def iran_melli_valid(d: str) -> bool:
    """Iran's 10-digit national code (kod-e melli): the last digit is a mod-11 check digit."""
    if len(d) != 10 or not d.isdigit() or len(set(d)) == 1:
        return False
    s = sum(int(d[i]) * (10 - i) for i in range(9)) % 11
    return int(d[9]) == (s if s < 2 else 11 - s)


_ID_VALUE = r"([A-Z0-9][A-Z0-9 -]{4,15}[A-Z0-9])"


def _trim(text, s, e):
    """Cut the value at a word that is clearly not part of it (a trailing ' tarihli', ' numaralı')."""
    v = text[s:e]
    m = re.search(r"\s+(?=[A-Z]?[a-zçğıöşü]{2,})", v)
    if m: e = s + m.start()
    while e > s and text[e - 1] in " -": e -= 1
    return e


class PassportRecognizer(_Base):
    """Passport numbers. No country's number carries a checksum we can use alone, so a passport cue is required:
    'Pasaport No: U12345678', 'U12345678 numaralı pasaportu', 'Passport No.: C01X00T47'. Also the
    machine-readable zone of a scanned passport page (the two '<<<' lines)."""
    ENTITY, NAME = "PASSPORT", "passport_cue"
    AFTER = re.compile(r"(?i:pasaport(?:u|unun)?|passport|pasaport\s+bilgileri)(?:\s+(?i:no|numaras[ıi]|numara|number|nr|sayısı|seri\s*no))?\.?\s*[:.]?\s*"
                       + r"(?:\([A-Z]{2,3}\)\s*|[A-Z]{3}\s+(?=[A-Z0-9]))?" + _ID_VALUE)
    BEFORE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{0,3}[ ]?\d[A-Z0-9 ]{4,12}[A-Z0-9])\s+(?:numaral[ıi]|sayıl[ıi]|no\.?lu|nolu)\s+(?i:pasaport)")
    MRZ1 = re.compile(r"(?m)^P[A-Z<][A-Z<]{3}([A-Z<]{2,}<<[A-Z<]+)\s*$")
    MRZ2 = re.compile(r"(?m)^([A-Z0-9<]{9})\d[A-Z<]{3}\d{6}\d[MF<]\d{6}\d[A-Z0-9<]{14}\d\d\s*$")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for rx in (self.AFTER, self.BEFORE):
            for m in rx.finditer(text):
                s, e = m.start(1), _trim(text, m.start(1), m.end(1))
                v = text[s:e]
                core = re.sub(r"[ -]", "", v)
                if 6 <= len(core) <= 12 and sum(c.isdigit() for c in core) >= 5 and not re.fullmatch(r"\d{4}/\d+", v):
                    out.append(self._r(s, e, 0.9, "number after a passport cue"))
        for m in self.MRZ2.finditer(text):
            out.append(self._r(m.start(), m.end(), 0.95, "passport machine-readable zone, line 2 (number, birth date)"))
        for m in self.MRZ1.finditer(text):
            r = self._r(m.start(1), m.end(1), 0.95, "passport machine-readable zone, line 1 (name)")
            r.entity_type = "PERSON"
            out.append(r)
        return out


class ForeignIDRecognizer(_Base):
    """A foreign client's home-country ID number after a cue: 'Ulusal Kimlik No', 'National ID', 'Kod-e Melli',
    'Tazkira No', 'Personal No', 'SSN', 'AMKA', 'Personalausweis-Nr.', 'Codice Fiscale', 'DNI', 'BSN', 'FİN'.
    Iran's national code is checksum-validated, so a weak cue ('İran', 'melli', 'kod') is enough for it."""
    ENTITY, NAME = "FOREIGN_ID", "foreign_id_cue"
    CUES = (r"ulusal\s+kimlik(?:\s+kart[ıi])?\s*(?:no|numaras[ıi]|kodu)?|ulusal\s+numara(?:s[ıi])?|national\s+(?:id|no|code|number)(?:\s+no)?|"
            r"kod-?e\s*melli|melli\s*kod|tazkira\s*no|tezkire\s*no|e-tazkira\s*no|personal\s+no|ki[şs]isel\s+(?:no|numaras[ıi])|"
            r"sosyal\s+kart\s+no|kamu\s+hizmet\s+numaras[ıi]|kimlik\s+kart[ıi]\s+no|id\s+kart\s+no|id\s*(?:no|number)|"
            r"i[çc]\s+pasaport\s+no|rusya\s+kimlik\s+no|ukrayna\s+kimlik\s+no|rnokpp|ssn|social\s+security\s+(?:no|number)|"
            r"sosyal\s+g[üu]venlik\s+no|amka|personalausweis-?nr\.?|ausweisnummer|n°\s*cni|cni|num[ée]ro\s+de\s+s[ée]curit[ée]\s+sociale|"
            r"national\s+insurance\s+no|ni\s+no|codice\s+fiscale|dni|nie|bsn|burgerservicenummer|f[İi]n\s*(?:kod)?|[şs][əe]xsiyy[əe]t\s+v[əe]siq[əe]si\s+f[İi]n")
    RX = re.compile(r"(?i:(?:" + CUES + r"))(?:\s*\([^)]{1,25}\))?\s*[:.]?\s*([A-Z0-9][A-Z0-9 -]{4,18}[A-Z0-9])")
    MELLI = re.compile(r"(?<![0-9])(\d{3}-?\d{6}-?\d)(?![0-9])")
    # 'FIN', 'NIE', 'DNI', 'CNI', 'SSN', 'BSN' are short: only as whole words
    SHORT = re.compile(r"(?i)^(?:fin|f[İi]n|nie|dni|cni|ssn|bsn|ni\s+no|amka)\b")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RX.finditer(text):
            cue = text[m.start():m.start(1)]
            if self.SHORT.match(cue.strip()) and m.start() > 0 and text[m.start() - 1].isalnum():
                continue
            s, e = m.start(1), _trim(text, m.start(1), m.end(1))
            core = re.sub(r"[ -]", "", text[s:e])
            fin = bool(re.match(r"(?i)f[İi]n|[şs][əe]xsiyy", cue.strip()))   # Azerbaijani FİN: 7 letters/digits
            ok = (len(core) == 7 and sum(c.isdigit() for c in core) >= 1) if fin else \
                (6 <= len(core) <= 16 and sum(c.isdigit() for c in core) >= 5)
            if ok and not re.fullmatch(r"\d{4}/\d+", text[s:e]):
                out.append(self._r(s, e, 0.85, f"number after a foreign ID cue ({cue.strip(' :.')})"))
        for m in self.MELLI.finditer(text):
            d = m.group(1).replace("-", "")
            if iran_melli_valid(d) and _has_context(text, m.start(), ("iran", "melli", "kod", "ulusal", "national"), 50):
                out.append(self._r(m.start(1), m.end(1), 0.9, "Iranian national code, check digit ok"))
        return out


class UETSRecognizer(_Base):
    """UETS (Ulusal Elektronik Tebligat Sistemi) addresses: 15 digits, usually written 5-5-5
    ("UETS: 16013-10288-73541"). The address belongs to one person or firm, so it identifies a lawyer as surely as
    the name: wherever names are masked, it is masked too. The 5-5-5 shape is distinctive enough alone; 15 plain
    digits need a UETS / e-Tebligat cue."""
    ENTITY, NAME = "UETS", "uets"
    SHAPED = re.compile(r"(?<![\d/-])(\d{5}[ -]\d{5}[ -]\d{5})(?![\d/-])")
    CUED = re.compile(r"(?i:uets|e-?\s?tebligat|elektronik\s+tebligat)(?:\s+(?i:adresi|adres|no|numaras[ıi]))?\s*[:.]?\s*(\d{15})(?!\d)")
    CTX = ("uets", "tebligat", "kep")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.SHAPED.finditer(text):
            cue = _has_context(text, m.start(1), self.CTX, 40)
            out.append(self._r(m.start(1), m.end(1), 0.95 if cue else 0.8,
                               "UETS e-Tebligat address" + (" after a UETS cue" if cue else " (5-5-5 digits)")))
        for m in self.CUED.finditer(text):
            out.append(self._r(m.start(1), m.end(1), 0.95, "15 digits after a UETS / e-Tebligat cue"))
        return out


class VKNRecognizer(_Base):
    ENTITY, NAME = "VKN", "vkn_checksum_context"
    RE = re.compile(r"(?<!\d)(\d{10})(?!\d)")
    CTX = ("vergi", "vkn", "v.k.n", "vd.", "v.d", "vergi no", "vergi kimlik")
    # right after a tax-number label any 10 digits are masked: a typo'd tax ID is still one
    LABELLED = re.compile(r"(?:[Vv]ergi\s+(?:[Kk]imlik\s+)?(?:[Nn]o|[Nn]umaras[ıi])|VERGİ\s+(?:KİMLİK\s+)?(?:NO|NUMARASI)|VKN)\s*[:.]?\s*(\d{10})(?!\d)")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RE.finditer(text):
            if vkn_valid(m.group(1)) and _has_context(text, m.start(), self.CTX, 50):
                out.append(self._r(m.start(1), m.end(1), 0.8, "10 digits, VKN checksum + tax context"))
        for m in self.LABELLED.finditer(text):
            if not any(r.start <= m.start(1) < r.end for r in out):
                out.append(self._r(m.start(1), m.end(1), 0.7, "10 digits after a tax ID label (checksum failed)"))
        return out


class IBANRecognizer(_Base):
    ENTITY, NAME = "IBAN", "iban_mod97"
    RE = re.compile(r"\b([A-Z]{2}\d{2}(?:[ \n]?[A-Z0-9]){10,30})\b")  # wrapped IBANs span a line break
    DASHED = re.compile(r"\b(TR\d{2}(?:-[0-9]{4}){5}-[0-9]{2})(?![\d-])")  # "TR83-6711-7308-8707-7284-3701-92"
    # scans: "TR6O 0001 ...", "TRO9 ...": Turkish IBANs with letters OCR'd into the digit groups
    OCR_RE = re.compile(r"\bTR[0-9OoIl]{2}(?:[ \n]?[0-9OoIlB]){20,24}\b")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RE.finditer(text):
            cand = m.group(1)
            # trim trailing groups until mod-97 holds (IBAN followed by other caps text)
            parts = re.split(r"([ \n])", cand)
            for k in range(len(parts), 0, -2):
                c = "".join(parts[:k])
                if iban_valid(c):
                    out.append(self._r(m.start(1), m.start(1) + len(c), 0.95, "IBAN mod-97 ok"))
                    break
        for m in self.DASHED.finditer(text):
            if iban_valid(m.group(1).replace("-", "")) and not any(r.start <= m.start() < r.end for r in out):
                out.append(self._r(m.start(1), m.end(1), 0.95, "IBAN mod-97 ok (dashed groups)"))
        for m in self.OCR_RE.finditer(text):
            if any(r.start <= m.start() < r.end for r in out):
                continue
            fixed = "TR" + m.group()[2:].translate(str.maketrans("OoIlB", "00118"))
            digits = re.sub(r"\s", "", fixed)
            ok = iban_valid(fixed)
            if ok or len(digits) in (25, 26, 27):
                out.append(self._r(m.start(), m.end(), 0.9 if ok else 0.65,
                                   "IBAN after OCR fix" if ok else "TR IBAN shape (OCR, checksum failed)"))
        return out


class CreditCardRecognizer(_Base):
    ENTITY, NAME = "CREDIT_CARD", "card_luhn"
    RE = re.compile(r"(?<!\d)(\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{1,7})(?!\d)")
    LABELLED = re.compile(r"(?:[Kk]art(?:\s+(?:[Nn]o|[Nn]umaras[ıi]))?|KART(?:\s+(?:NO|NUMARASI))?|[Kk]redi\s+[Kk]art[ıi]|KRED[İI]\s+KARTI)\s*[:.]?\s*(\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4})(?!\d)")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RE.finditer(text):
            d = re.sub(r"\D", "", m.group(1))
            # 3-6: Amex, Visa, Mastercard, Discover/UnionPay; 9792: TROY, Turkey's domestic card scheme (BKM)
            if luhn_valid(d) and (d[0] in "3456" or d.startswith("9792")) and not tckn_valid(d):
                out.append(self._r(m.start(1), m.end(1), 0.8, "Luhn ok"))
        for m in self.LABELLED.finditer(text):
            if not any(r.start <= m.start(1) < r.end for r in out):
                out.append(self._r(m.start(1), m.end(1), 0.7, "16 digits after a card label (Luhn failed)"))
        return out


class EmailRecognizer(_Base):
    ENTITY, NAME = "EMAIL", "email_regex"
    RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
    # scans: OCR reads '@' as ©, ®, &, 'G', 'g' or 'ö'; accepted only before a known mail domain
    PROVIDERS = r"(?:gmail|hotmail|outlook|yandex|yahoo|icloud|windowslive|live|msn|mynet|ttmail|superonline)"
    OCR_RE = re.compile(r"\b([\w.+-]*[\w])\s?(?:[©®&]{1,2}|[Gg6]ö?|ö)\s?(" + PROVIDERS + r"\.(?:com\.tr|com|net))\b")
    OCR_SYM = re.compile(r"\b([\w.+-]*[\w])\s?[©®]{1,2}\s?([\w-]+(?:\.[\w-]+)+)\b")
    # written out to dodge scrapers: "ali.kaya [at] proton [dot] me", "ali(at)gmail(nokta)com"
    SPELLED = re.compile(r"\b[\w.+-]*\w\s*[\[(]\s*(?:at|AT|et)\s*[\])]\s*[\w-]+(?:\s*[\[(]\s*(?:dot|DOT|nokta|NOKTA)\s*[\])]\s*[\w-]+)+")
    # institutional role mailboxes are not personal data; scored below the default threshold
    ROLE = re.compile(r"^(?:kvkk|info|bilgi|iletisim|destek|support|muhasebe|hukuk|basvuru|kep|noreply|no-reply|"
                      r"insankaynaklari|ik|satis|sales|contact|admin|webmaster|sekreterya|consulate\.[a-z]+)@", re.I)

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RE.finditer(text):
            role = bool(self.ROLE.match(m.group()))
            out.append(self._r(m.start(), m.end(), 0.35 if role else 0.95, "role mailbox" if role else "email shape"))
        for rx in (self.OCR_RE, self.OCR_SYM):
            for m in rx.finditer(text):
                if "@" in m.group() or any(r.start <= m.start() < r.end for r in out):
                    continue
                out.append(self._r(m.start(), m.end(), 0.8, "e-mail with OCR-garbled @"))
        for m in self.SPELLED.finditer(text):
            out.append(self._r(m.start(), m.end(), 0.85, "e-mail with @ and dots written out"))
        return out


class PhoneRecognizer(_Base):
    ENTITY, NAME = "PHONE", "tr_phone"
    SEP = r"(?:[ \-.]|\n)?"  # allow a line break inside wrapped numbers
    # +90 / 0090 / 0 prefix, area code 2xx-5xx or 850, 7 digits in 3-2-2 or 3-4 groups
    RE = re.compile(
        r"(?<![\d\w])((?:(?:\+|#|\*|4-|\+-)\s?90|0090)" + SEP + r"\(?0?[2-58]\d{2}\)?|0" + SEP + r"\(?[2-58]\d{2}\)?|\(0?[2-58]\d{2}\))"
        + SEP + r"(\d{3})" + SEP + r"(\d{2}" + SEP + r"\d{2}|\d{4})(?!\d)")
    BARE = re.compile(r"(?<![\d\w])(5\d{2}" + SEP + r"\d{3}" + SEP + r"\d{2}" + SEP + r"\d{2})(?!\d)")
    CTX = ("tel", "gsm", "cep", "telefon", "phone", "faks", "fax", "irtibat")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RE.finditer(text):
            out.append(self._r(m.start(), m.end(), 0.85, "TR phone with prefix"))
        for m in self.BARE.finditer(text):
            if _has_context(text, m.start(), self.CTX, 30):
                out.append(self._r(m.start(1), m.end(1), 0.7, "bare mobile number + phone context"))
        return out


class PlateRecognizer(_Base):
    ENTITY, NAME = "PLATE", "tr_plate"
    RE = re.compile(r"(?<![\w\d])(0[1-9]|[1-7]\d|8[01])[ ]?([A-PR-VYZ]{1,3})[ ]?(\d{2,5})(?![\w\d])")
    BAD_LETTERS = {"TL", "TRY", "USD", "EUR", "KDV", "AS", "NO", "MD", "HD", "CD", "E", "K", "T", "M", "S"}
    CTX = ("plaka", "arac", "araç", "plakali", "plakalı", "vasita", "otomobil")
    # next to a plate label any letters and digit count: "Araç plakası 07 PRB 5627", "34czy444 plakalı"
    LABELLED = re.compile(r"(?:[Pp]laka(?:s[ıi])?|PLAKA(?:SI)?)[ \t]*[:.]?[ \t]*((?:0[1-9]|[1-7]\d|8[01])[ ]?[A-Za-z]{1,3}[ ]?\d{2,5})(?![\w\d])")
    BEFORE_LABEL = re.compile(r"(?<![\w\d])((?:0[1-9]|[1-7]\d|8[01])[ ]?[A-Za-z]{1,3}[ ]?\d{2,5})[ \t]+(?:plakal[ıi]|PLAKALI)")

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RE.finditer(text):
            letters, digits = m.group(2), m.group(3)
            ok = ((len(letters) == 1 and len(digits) in (4, 5)) or
                  (len(letters) == 2 and len(digits) in (3, 4)) or
                  (len(letters) == 3 and len(digits) in (2, 3)))
            if not ok:
                continue
            ctx = _has_context(text, m.start(), self.CTX, 60) or any(
                c in fold(text[m.end():m.end() + 25]) for c in self.CTX)
            if letters in self.BAD_LETTERS and not ctx:
                continue
            out.append(self._r(m.start(), m.end(), 0.9 if ctx else 0.65, "TR plate shape"))
        for rx in (self.LABELLED, self.BEFORE_LABEL):
            for m in rx.finditer(text):
                if not any(r.start <= m.start(1) < r.end for r in out):
                    out.append(self._r(m.start(1), m.end(1), 0.8, "plate next to a plate label"))
        return out


class IPRecognizer(_Base):
    ENTITY, NAME = "IP_ADDRESS", "ipv4"
    RE = re.compile(r"(?<![\d.])((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?![\d.])")

    def analyze(self, text, entities, nlp_artifacts=None):
        return [self._r(m.start(1), m.end(1), 0.6, "IPv4") for m in self.RE.finditer(text)]


class BirthDateRecognizer(_Base):
    ENTITY, NAME = "BIRTH_DATE", "birth_date_context"
    RE = re.compile(r"(?<!\d)(\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}|(?:19|20)\d{2}-\d{2}-\d{2}|"
                    r"\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık|"
                    r"OCAK|ŞUBAT|MART|NİSAN|MAYIS|HAZİRAN|TEMMUZ|AĞUSTOS|EYLÜL|EKİM|KASIM|ARALIK)\s+(?:19|20)\d{2}|"
                    r"(?:19|20)\d{2}(?=\s*doğumlu))(?!\d)")
    CTX = ("dogum tarihi", "d.tarihi", "dogum t", "d. tarihi", "dogumlu", "d.t.", "dogum yeri ve tarihi")
    AFTER = re.compile(r"^\s*(?:dogumlu|tarihinde dog|tarihli dog|dogum)|^['’]?(?:te|de|ta|da)\s+dog")
    BEFORE = re.compile(r"\bdogum\s*[:(]?\s*$")   # "doğum 09.06.1983", "(doğum: 09.06.1983)": the date right after the word

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in self.RE.finditer(text):
            after = fold(text[m.end():m.end() + 25])
            before = fold(text[max(0, m.start() - 12):m.start()])
            if _has_context(text, m.start(), self.CTX, 35) or self.AFTER.match(after) or self.BEFORE.search(before):
                out.append(self._r(m.start(1), m.end(1), 0.85, "date + birth context"))
        return out


class SpelledNumberRecognizer(_Base):
    """An ID, card, tax, phone or IBAN number read out digit by digit ("tc dokuz dokuz yedi yedi bir ..."), as in
    call transcripts and dictated statements. Seven digits or more; the type comes from the label just before it,
    and without a label only a phone-length number (10-11 digits) is taken. Amounts ("altı yüz bin") never match:
    yüz, bin and milyon are not in the word list."""
    ENTITY, NAME = "PHONE", "spelled_number"
    DIGIT = ("sifir", "bir", "iki", "uc", "dort", "bes", "alti", "yedi", "sekiz", "dokuz")
    TENS = ("on", "yirmi", "otuz", "kirk", "elli", "altmis", "yetmis", "seksen", "doksan")
    RUN = re.compile(r"(?<![a-z0-9])(?:(?:sifir|bir|iki|uc|dort|bes|alti|yedi|sekiz|dokuz|on|yirmi|otuz|kirk|elli|altmis|yetmis|seksen|doksan)"
                     r"(?:[ \t]+|[ \t]*[-,][ \t]*)){2,}(?:sifir|bir|iki|uc|dort|bes|alti|yedi|sekiz|dokuz|on|yirmi|otuz|kirk|elli|altmis|yetmis|seksen|doksan)(?![a-z0-9])")
    WORD = re.compile(r"[a-z]+")
    LABELS = (("TCKN", ("tc", "t.c", "kimlik", "tckn")), ("CREDIT_CARD", ("kart",)), ("VKN", ("vergi", "vkn")),
              ("IBAN", ("iban", "tr")), ("PHONE", ("tel", "telefon", "gsm", "cep", "numaram", "numarasi", "numarami", "ara")))

    def __init__(self):
        super().__init__()
        self.supported_entities = ["PHONE", "TCKN", "CREDIT_CARD", "VKN", "IBAN"]

    def analyze(self, text, entities, nlp_artifacts=None):
        f, out = _fold_keep(text), []
        for m in self.RUN.finditer(f):
            n, prev_tens = 0, False
            for w in self.WORD.findall(m.group()):
                n += 0 if (prev_tens and w in self.DIGIT) else (2 if w in self.TENS else 1)
                prev_tens = w in self.TENS
            if n < 7:
                continue
            before = self.WORD.findall(f[max(0, m.start() - 25):m.start()])[-3:]
            ent = next((e for e, ws in self.LABELS if any(w in ws for w in before)), None)
            if ent is None and n not in (10, 11):
                continue
            r = self._r(m.start(), m.end(), 0.7, f"{n} digits read out as words")
            r.entity_type = ent or "PHONE"
            out.append(r)
        return out


# ---------------------------------------------------------------- person names
TOKEN_RE = re.compile(rf"[{TR_LETTER}]+(?:\.(?=[{TR_LETTER}]))?[{TR_LETTER}]*")

PERSON_CUES = (
    "davaci", "davali", "davacilar", "davalilar", "vekili", "vekilleri", "av.", "avukat",
    "sayin", "sn.", "hakim", "katip", "uye", "baskan", "bay ", "bayan", "adi soyadi",
    "ad soyad", "adi-soyadi", "kiraci", "kiraya veren", "alici", "satici", "isci",
    "isveren vekili", "muvekkil", "vekil eden", "vekalet veren", "borclu", "alacakli",
    "musteki", "magdur", "sanik", "supheli", "tanik", "murisi", "muris", "mirasci",
    "basvurucu", "basvuran", "ihtar eden", "muhatap", "kefil", "veli", "vasi",
    "ilgili kisi", "hasta", "calisan", "personel", "imza", "duzenleyen", "teslim alan",
    "teslim eden", "katip", "zabit", "bilirkisi", "arabulucu", "noter", "sorumlu",
    "cocugu", "cocuklari", "esi", "annesi", "babasi", "kardesi", "mirascisi", "yetkili", "ihtar eden", "kefil",
    # correspondence, minutes and medical headers
    "kimden", "kime", "gonderen", "alici:", "bilgi:", "cc:", "from:", "to:", "katilimcilar", "katilanlar",
    "hazirlayan", "merhaba", "sevgili", "degerli", "dr.", "prof.", "doc.", "uzm.", "refakatci", "hekim",
    "karsi taraf", "dinlenen", "yakini", "ogretmen", "sofor", "surucu",
)
LEGAL_TITLE = ("kanun", "vatandaslig", "yonetmeli", "medeni", "borclar", "kazanilmas", "uygulanmas", "tuzug",
               "genelge", "anayasa", "mevzuat", "yasasi", "yasasin", "teskilat", "telekom", "lirasi", "hava yollari",
               "silahli", "milleti", "devleti", "ceza kanun", "ticaret kanun")
CUE_RE = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(c.strip()) for c in PERSON_CUES)
                    + r")(?:(?<=[a-z])(?:si|su|i|u|leri|lari|ler|lar|miz|niz|nin|nun|in|un))?(?![a-z])")
# words that, right after a capitalised run, mark it as a person
PERSON_AFTER = re.compile(
    r"^\s*(?:hanım|bey|hanımefendi|beyefendi|hn\.|bey'|hanım'|geldi|gelmedi|dinlendi|dinlenmiştir|"
    r"ile görüş|adına|tarafından|ifadesinde|ifadesi|beyanında|beyanı|diye biri|yer aldı|imzal[ıi]|"
    r"e-imzal[ıi]|vekaleten|asaleten|doğumlu|oğlu|kızı|eşi|isimli|adlı|adındaki)", re.I)
ORG_TAIL = ("a.s", "a.ş", "ltd", "sti", "şti", "limited", "anonim", "sirketi", "şirketi", "sanayi", "san.",
            "ticaret", "tic.", "insaat", "lojistik", "yazilim", "teknoloji", "turizm", "gida", "enerji",
            "holding", "bankasi", "bankası", "vakfi", "derneği", "dernegi", "kooperatifi",
            "universitesi", "belediyesi", "mahkemesi", "bakanligi", "baskanligi", "hastanesi", "noterligi",
            "mudurlugu", "dairesi", "barosu", "grubu", "group", "inc", "gmbh")
KINSHIP = re.compile(r"^\s*(?:oğlu|kızı|oglu|kizi|eşi|esi)\b", re.I)
# common Turkish surname endings (Soyadı Kanunu era surnames are mostly compounds)
SURNAME_SUFFIX = re.compile(
    r"(?:oglu|ogullari|gil|soy|han|kaya|tepe|tas|demir|dag|turk|can|gul|li|lu|ci|cu|kan|alp|kilic|biyik|yildiz|"
    r"oz|er|ar|men|dere|bag|arslan|aslan|kurt|ay|sever|veren|verdi|dogan|kol|kus|baş|bas|ok|tekin|ekin|el|"
    r"yurt|yol|kok|cam|cakir|kara|ozturk|tan|bay|beyli|zade|giller|lar|ler|dal|gun|yigit|cin|in|un|ka|ce|ca)$")
APOS_SUFFIX = re.compile(r"^['’][a-zçğıöşü]{1,5}\b")
CHAT_SPEAKER = re.compile(
    rf"^(?:[\[(]?\d{{1,2}}[./]\d{{1,2}}[./]\d{{2,4}},?\s+)?[\[(]?\d{{1,2}}[:.]\d{{2}}(?::\d{{2}})?[\])]?\s*-?\s*"
    rf"([{TR_UPPER}][{TR_LETTER}]+(?:[ ][{TR_UPPER}][{TR_LETTER}]+){{0,2}})\s*:", re.M)
EMAIL_LOCAL = re.compile(r"\b([\w.+-]+)@[\w-]+(?:\.[\w-]+)+")
# inflection endings (folded) stripped to find the dictionary form of a capitalised word
_INFL = sorted({"larinin", "lerinin", "larin", "lerin", "larina", "lerine", "larindan", "lerinden", "larinda", "lerinde", "lari", "leri",
                "lar", "ler", "sinin", "sunun", "sina", "sine", "suna", "sinda", "sinde", "sindan", "sinden", "si", "su",
                "nin", "nun", "na", "ne", "nda", "nde", "ndan", "nden", "in", "un", "i", "u", "a", "e", "da", "de",
                "dan", "den", "ta", "te", "tan", "ten", "ya", "ye", "yi", "yu", "yla", "yle", "la", "le", "ca", "ce",
                "cilik", "lik", "luk", "li", "lu", "siz", "suz", "dir", "tir", "dur", "tur", "ki", "daki", "deki",
                "inda", "inde", "indan", "inden", "ina", "ine", "imiz", "iniz", "umuz", "unuz", "ligi", "lugu",
                "ligin", "lugun", "ligine", "lugune", "ligini", "lugunu", "ini", "unu", "dik", "tik", "duk", "tuk",
                "digi", "tigi", "dugu", "tugu", "digindan", "tigindan", "dugundan", "tugundan", "ilan", "ilen",
                "im", "um", "imiz", "umuz", "imizin", "umuzun", "imize", "umuza", "ime", "uma"},
               key=len, reverse=True)
_MUTATE = {"d": "t", "g": "k", "b": "p", "c": "c"}


def _inflected_common(f: str) -> bool:
    common = wordlist("common_words.txt")
    for suf in _INFL:
        if f.endswith(suf) and len(f) - len(suf) >= 3:
            stem = f[:-len(suf)]
            if stem in common or (stem[-1] in _MUTATE and stem[:-1] + _MUTATE[stem[-1]] in common):
                return True
    return False


def is_lexical(tok: str) -> bool:
    """True when a capitalised token is an ordinary Turkish word (or an inflected
    form of one), e.g. "Bayramı", "Uyuşmazlıkların", "Hizmetleri". Names in our
    gazetteers are never lexical, so "Emine" or "Yıldırım" stay names."""
    f = fold(tok)
    if f in wordlist("first_names.txt") or f in wordlist("last_names.txt"):
        return False
    if f in wordlist("common_words.txt") or f in wordlist("stopwords_caps.txt"):
        return True
    return _inflected_common(f)


def _acronym(tok: str) -> bool:
    """'BBVA', 'THY', 'SGK': short capitals that are neither a word nor a known name ('USLU', 'KOÇ' are not)."""
    f = fold(tok)
    return (is_all_caps(tok) and len(tok) <= 4 and f not in wordlist("common_words.txt")
            and f not in wordlist("last_names.txt") and f not in wordlist("first_names.txt"))


NAME_LIST_SEP = re.compile(r"^(?:\s*,\s*|\s+ve\s+|\s*;\s*)$")


class PersonRecognizer(_Base):
    """Gazetteer + context + Turkish-casing heuristics.

    A candidate is a run of 1-4 capitalised (or ALL-CAPS) tokens that are not
    legal/business stop words. Evidence for "this is a person":
      * gazetteer: first token a known first name, or last token a known surname
      * court casing "Ahmet YILMAZ" (title-case then all-caps surname)
      * a cue before it (Davacı, Av., Sayın, Kimden:, Katılımcılar:, Merhaba ...)
      * a cue after it (Hanım/Bey, geldi, adına, tarafından, ifadesinde, 'ın ...)
      * its tokens appear in an e-mail address in the same document
      * it is a chat speaker ("[10:42] Ayaz: ...")
      * a typical surname ending (-oğlu, -soy, -kaya, -tepe ...)
    Gazetteer or court casing alone accept a 2+ token run; the weaker signals need
    two of them. Tokens of accepted names are remembered so later bare mentions
    ("davalı Yılmaz", "Kazadan sonra Esila") in the same document are caught, and
    comma lists that contain a name are filled in ("Katılımcılar: A B, C D, E F").
    A firm's own dictionary (client and counter-party names) is matched exactly
    on top, see ``CustomTermsRecognizer``.
    """
    ENTITY, NAME = "PERSON", "tr_person_gazetteer"
    # "Anne Kızlık Soyadı: Özdemir", "annemin kızlık soyadı Turan": a surname even when no gazetteer knows it
    FORM_COLON = re.compile(r"(?:[ \t]+[a-zçğıöşü]+){0,2}[ \t]?[:：]")
    WORDS = re.compile(rf"[{TR_LETTER}]+")
    MAIDEN = re.compile(r"(?:[Kk]ızlık|KIZLIK)\s+(?:[Ss]oyad[ıi]|SOYADI)\s*[:：]?[ \t]*([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:-[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?|[A-ZÇĞİÖŞÜ]{2,}(?:-[A-ZÇĞİÖŞÜ]{2,})?)(?![\w])")

    def __init__(self):
        super().__init__()
        self.first = wordlist("first_names.txt")
        self.last = wordlist("last_names.txt")
        cue_words = {c.strip(" .:") for c in PERSON_CUES if " " not in c.strip()}
        self.stop = (wordlist("stopwords_caps.txt") | wordlist("provinces.txt") | wordlist("districts.txt")
                     | frozenset(cue_words))
        self.ambiguous = wordlist("ambiguous_first.txt")

    def _tokens(self, text):
        return [(m.start(), m.end(), m.group()) for m in TOKEN_RE.finditer(text)]

    def _nameish(self, tok: str) -> bool:
        if not is_capitalised(tok) or len(tok) < 2:
            return False
        f = fold(tok.rstrip("."))
        if f in self.stop:
            return False
        if "." in tok:  # initials like "A." are handled separately
            return False
        return True

    def _place_surname(self, prev, tok) -> bool:
        """'Emal YILDIRIM', 'Ali Çankaya': a district name that is also a surname, right after a first name."""
        t = tok[2]
        f = fold(t)
        return (len(t) >= 3 and is_capitalised(t) and f in self.last and f in wordlist("districts.txt")
                and f not in wordlist("provinces.txt") and fold(prev[2]) in self.first)

    def _email_parts(self, text):
        parts = set()
        for m in EMAIL_LOCAL.finditer(text):
            for p in re.split(r"[._+\-\d]+", m.group(1)):
                if len(p) > 2:
                    parts.add(fold(p))
        return parts

    def _form_label(self, text, r):
        """A capitalised run alone at the start of a line and followed by a colon is a field label ("Kayıt Saati:",
        "Poliçe Durumu:"), unless one of its words is a known first name (a chat speaker, "Ayşe Kaya:")."""
        line = text.rfind("\n", 0, r.start) + 1
        if text[line:r.start].strip(" \t|-•*") or not self.FORM_COLON.match(text[r.end:r.end + 30]):
            return False
        return not any(fold(w) in self.first for w in self.WORDS.findall(text[r.start:r.end]))

    def analyze(self, text, entities, nlp_artifacts=None):
        toks = self._tokens(text)
        self._emails = self._email_parts(text)
        self._speakers = {m.start(1) for m in CHAT_SPEAKER.finditer(text)}
        out, seen_names, runs = [], set(), []
        i = 0
        while i < len(toks):
            if not self._nameish(toks[i][2]):
                i += 1
                continue
            j = i
            # same-line run of name-ish tokens, separated only by spaces
            while (j + 1 < len(toks) and j - i < 3 and (self._nameish(toks[j + 1][2]) or self._place_surname(toks[j], toks[j + 1]))
                   and re.fullmatch(r"[ \t]{1,2}", text[toks[j][1]:toks[j + 1][0]])):
                j += 1
            run = toks[i:j + 1]
            # "Müvekkilim Ayşe YILMAZ": an inflected ordinary word at the front is not part of the name
            res = None
            if len(run) > 2 and is_lexical(run[0][2]) and fold(run[0][2]) not in self.first:
                res = self._score_run(text, run[1:])
                if res:
                    run = run[1:]
            res = res or self._score_run(text, run)
            if res is None and len(run) > 2:
                # a capitalised word glued to a name: "Sayın Ahmet Kaya", "Ahmet Kaya Protokol"
                for sub in (run[1:], run[:-1], run[1:-1], run[2:], run[:-2]):
                    if len(sub) >= 2:
                        res = self._score_run(text, sub)
                        if res:
                            run = sub
                            break
            if res:
                s, e, score, why = res
                out.append(self._r(s, e, score, why))
                for _, _, t in run:
                    seen_names.add(fold(t))
            else:
                runs.append(toks[i:j + 1])
            i = j + 1
        out.extend(self._fill_lists(text, runs, out, seen_names))
        out.extend(self._second_pass(text, toks, seen_names, out))
        out = [r for r in out if not self._form_label(text, r)]
        for m in self.MAIDEN.finditer(text):
            if not any(r.start <= m.start(1) < r.end for r in out):
                out.append(self._r(m.start(1), m.end(1), 0.85, "surname after a maiden-name label"))
        return out

    @staticmethod
    def _org_follows(text, end):
        """'Ege Yapı Malzemeleri Ltd. Şti.': a company suffix within the next few words."""
        # a dash ends the name too: "Av. Ayşe Kaya - İstanbul Barosu" is a lawyer and her bar, not a company
        seg = re.split(r"[,;:()\n]|\s[-–—]\s", text[end:end + 45])[0]
        return any(w.startswith(o) for w in fold(seg).split()[:4] for o in ORG_TAIL)

    def _score_run(self, text, run):
        start, end = run[0][0], run[-1][1]
        words = [fold(t) for _, _, t in run]
        if any(w.startswith(LEGAL_TITLE) for w in words) or (words[0] in ("turk", "turkiye") and
                                                             fold(text[end:end + 30]).lstrip().startswith(LEGAL_TITLE)):
            return None  # a law, regulation or office title, not a person
        if self._org_follows(text, end):
            return None  # company name: legal persons are out of KVKK scope
        ctx = _context_before(text, start, 30)
        gap = text[max(0, start - 30):start]
        cut = gap.rfind("\n\n")
        if cut >= 0 and ":" in gap[:cut]:
            ctx = fold(gap[cut + 2:])   # a form row's cue does not reach past a blank line ("Yetkili no: 8\n\nOnay durumu")
        cue = bool(CUE_RE.search(ctx[-30:]))
        after = text[end:end + 25]
        cue_after = bool(PERSON_AFTER.match(after))
        apos = bool(APOS_SUFFIX.match(after))
        kin = bool(KINSHIP.match(text[end:end + 8]))
        first_hit = words[0] in self.first and (words[0] not in self.ambiguous or len(words) >= 2)
        last_hit = words[-1] in self.last
        # "Ahmet Yılmaz", "AHMET YILMAZ" and court style "Ahmet YILMAZ" all count
        caps_style = all(is_all_caps(t) or (t[0].isupper() and t[1:].islower()) for _, _, t in run if len(t) > 1)
        court_style = (len(run) >= 2 and caps_style and not is_all_caps(run[0][2]) and is_all_caps(run[-1][2])
                       and len(run[-1][2]) >= 3)
        email = sum(w in self._emails for w in words)
        speaker = start in self._speakers
        surname_shape = len(words[-1]) >= 4 and bool(SURNAME_SUFFIX.search(words[-1]))
        # a whole line in capitals without any other evidence is a heading, not a name
        line_s = text.rfind("\n", 0, start) + 1
        line_e = text.find("\n", end)
        line = text[line_s: len(text) if line_e < 0 else line_e].strip()
        heading = is_all_caps(run[0][2]) and line == text[start:end]
        lex = [is_lexical(t) for _, _, t in run]
        acronym = _acronym(run[-1][2])
        # weak evidence needs a surname-like last token (not an ordinary word, not an acronym) and a
        # first token that is a name or at least not an ordinary word; a strong cue only needs one
        # token that is not an ordinary word ("Asel USLU": uslu is also an adjective)
        plausible = not lex[-1] and not acronym and (not lex[0] or first_hit)
        some_name = not acronym and (not all(lex) or first_hit or last_hit)
        if len(run) >= 2 and first_hit and caps_style and (not lex[-1] or last_hit or cue):
            return start, end, 0.85 + 0.1 * (last_hit or cue), "first-name gazetteer"
        if len(run) >= 2 and last_hit and any(w in self.first for w in words[:-1]):
            return start, end, 0.85, "first+last gazetteer"
        if cue and court_style and not acronym:
            return start, end, 0.75, "person cue + court casing"
        if cue and caps_style and (len(run) >= 2 or words[0] in self.first or words[0] in self.last) and len(words[-1]) >= 3 \
                and some_name:
            return start, end, 0.75, "person cue before capitalised run"
        if speaker and len(run) <= 3:
            return start, end, 0.8, "chat speaker"
        if email and caps_style and (len(run) >= 2 or len(words[0]) >= 3) and (email >= 2 or not all(lex)):
            return start, end, 0.8, "matches an e-mail address in the document"
        if len(run) >= 2 and court_style and len(run) <= 4 and not lex[-1] and not acronym \
                and (not lex[0] or first_hit or fold(run[-1][2]) not in wordlist("common_words.txt")):
            return start, end, 0.75, "court casing Ad SOYAD"
        if len(run) >= 2 and caps_style and not heading and ((some_name and cue_after) or
                                                             (plausible and apos and surname_shape)):
            return start, end, 0.7, "person word after capitalised run"
        if len(run) in (2, 3) and caps_style and not heading and plausible and surname_shape and (apos or cue_after or first_hit):
            return start, end, 0.65, "surname shape + context"
        if kin and words[0] in self.first:
            return start, end, 0.7, "X oğlu/kızı"
        if len(run) == 1 and first_hit and words[0] not in self.ambiguous and (cue or cue_after):
            return start, end, 0.7, "single first name + cue"
        if len(run) == 1 and len(words[0]) >= 3 and not lex[0] and re.search(r"(?:merhaba|sevgili|degerli|sayin|dear|hi|selam)[ ]*$", ctx) \
                and re.match(r"^\s*[,!\n]", after):
            return start, end, 0.7, "greeting + name"
        if len(run) in (2, 3) and caps_style and not heading and apos and plausible and not lex[0]:
            return start, end, 0.6, "capitalised run with a case suffix ('in, 'a)"
        if len(run) == 1 and caps_style and len(words[0]) >= 3 and re.match(r"^\s*(?:hanım|bey)\b", after, re.I):  # "Irmak Hanım"
            return start, end, 0.7, "name + Hanım/Bey"
        return None

    def _fill_lists(self, text, runs, found, seen):
        """'Katılımcılar: Zümra TOPÇU, Asel USLU, Kezban ÜLKER': a 2-3 token run
        next to an accepted name in a comma/"ve" list is a name too."""
        spans = sorted((r.start, r.end) for r in found)
        extra, changed = [], True
        pending = [r for r in runs if 2 <= len(r) <= 3]
        while changed and pending:
            changed = False
            for run in list(pending):
                s, e = run[0][0], run[-1][1]
                caps_style = all(is_all_caps(t) or (t[0].isupper() and t[1:].islower()) for _, _, t in run)
                if not caps_style or self._org_follows(text, e):
                    continue
                lex = [is_lexical(t) for _, _, t in run]
                if all(lex) or _acronym(run[-1][2]):
                    continue
                if any(NAME_LIST_SEP.match(text[pe:s]) or NAME_LIST_SEP.match(text[e:ps]) for ps, pe in spans):
                    extra.append(self._r(s, e, 0.7, "in a list of names"))
                    spans = sorted(spans + [(s, e)])
                    seen.update(fold(t) for _, _, t in run)
                    pending.remove(run)
                    changed = True
        return extra

    def _second_pass(self, text, toks, seen, already):
        """Bare surname / first-name repeats of names seen earlier in the document."""
        covered = [(r.start, r.end) for r in already]
        extra = []
        strong = {w for w in seen if w not in self.ambiguous and w not in self.stop and len(w) > 2
                  and (w in self.first or w in self.last or not is_lexical(w))}
        k = 0
        while k < len(toks):
            s, e, t = toks[k]
            if fold(t) in strong and is_capitalised(t) and not any(a <= s < b for a, b in covered):
                # take the neighbouring surname too ("Elvin Bozdemir" when only "Elvin" was known)
                while (k + 1 < len(toks) and self._nameish(toks[k + 1][2])
                       and re.fullmatch(r"[ \t]{1,2}", text[e:toks[k + 1][0]])
                       and not any(a <= toks[k + 1][0] < b for a, b in covered)):
                    k += 1
                    e = toks[k][1]
                if not any(fold(x).startswith(LEGAL_TITLE) for x in text[s:e].split()[1:]) and \
                        not fold(text[e:e + 30]).lstrip().startswith(LEGAL_TITLE):
                    extra.append(self._r(s, e, 0.6, "repeat of a name found earlier"))
            k += 1
        return extra


# ---------------------------------------------------------------- addresses
ADDR_ANCHOR = re.compile(
    r"\b(?:Mahallesi|Mah\.|Mh\.|MAHALLESİ|MAH\.|Caddesi|Cad\.|Cd\.|CADDESİ|CAD\.|Sokağı|Sokak|Sok\.|Sk\.|SOKAK|SOK\.|"
    r"Bulvarı|Blv\.|BULVARI|Apartmanı|Apt\.|APT\.|Sitesi|SİTESİ|Köyü|KÖYÜ)",
)
ADDR_LABEL = re.compile(r"(?:Adres(?:i)?|ADRES(?:İ)?|İkametgah|İkamet Adresi|Tebligat Adresi|Yazışma Adresi)\s*[:：]\s*", re.I)
ADDR_FORM_ROW = re.compile(r"(?m)^[ \t|]*(?:İkametgah[ıi]?|İKAMETGAHI|İkamet(?:gâh)?|Adresi|ADRESİ|İkamatgah[ıi]?)[ \t]+(?=\S)")
ADDR_TOKEN = re.compile(
    rf"(?:No\s*[:.]?\s*\d+[/A-Za-z0-9-]*|Daire\s*[:.]?\s*\d+|D\s*[:.]\s*\d+|Kat\s*[:.]?\s*\d+|K\s*[:.]\s*\d+|[{TR_UPPER}][{TR_LETTER}'’]*\.?|"
    rf"\d+[./]?\d*\s*(?:Sok\.?|Sk\.?|Cad\.?|Cd\.?)|\d{{5}}|\d+[A-Za-z]?|[/,\-]|[{TR_LOWER}]{{1,4}}\.)"
)


class AddressRecognizer(_Base):
    """Turkish postal addresses.

    Two signals: an explicit label ("Adres:", "Tebligat Adresi:") takes the rest of
    the line (and the next line if it continues the address), and street anchors
    (Mahallesi / Caddesi / Sokak / No: / Daire ...) grow a span left and right
    over address-shaped tokens, ending at a province/district or line end.
    """
    ENTITY, NAME = "ADDRESS", "tr_address"
    DOOR = re.compile(r"(?<![\w])(?:[Dd]aire|DAİRE|[Kk]ap[ıi]|KAPI)[ \t]+(?:[Nn]o|NO|[Nn]umaras[ıi]|NUMARASI)[ \t]*[:.]?[ \t]*(\d{1,4}(?:[/-]?[A-Za-z])?)(?![\w/])")

    def __init__(self):
        super().__init__()
        self.places = wordlist("provinces.txt") | wordlist("districts.txt")

    def analyze(self, text, entities, nlp_artifacts=None):
        spans = []
        for m in ADDR_LABEL.finditer(text):
            s = m.end()
            e = text.find("\n", s)
            e = len(text) if e < 0 else e
            nxt_end = text.find("\n", e + 1)
            nxt = text[e + 1: nxt_end if nxt_end > 0 else len(text)]
            if text[s:e].rstrip().endswith((",", "-")) or (ADDR_ANCHOR.search(nxt) and ":" not in nxt[:15]) or re.search(r"\bNo\s*[:.]?\s*\d", nxt):
                e = nxt_end if nxt_end > 0 else len(text)
            seg = text[s:e].rstrip(" .;")
            if len(seg.strip()) >= 8 and (ADDR_ANCHOR.search(seg) or re.search(r"\bNo\s*[:.]?\s*\d", seg) or self._has_place(seg)):
                spans.append((s, s + len(seg), 0.9, "address label"))
        # form rows: "İkametgahı  Trend Royal-1 A Blok D:25 Kuşadası/AYDIN" (label cell, no colon)
        for m in ADDR_FORM_ROW.finditer(text):
            s, e = m.end(), text.find("\n", m.end())
            e = len(text) if e < 0 else e
            seg = text[s:e].rstrip(" .;|")
            # the value starts like an address (capital or digit) and is row-sized: "İkamet şartına bakıldığında ..."
            # or "İkamet izni ..." opening a paragraph is prose, not a form row
            if (len(re.findall(rf"[{TR_LETTER}0-9]+", seg)) >= 2 and re.match(rf"[{TR_UPPER}0-9]", seg)
                    and len(seg.split()) <= 14):
                spans.append((s, s + len(seg), 0.8, "address row of a form"))
        for m in ADDR_ANCHOR.finditer(text):
            s, e = self._grow(text, m.start(), m.end())
            if e - s >= 12:
                spans.append((s, e, 0.75, "street anchor"))
        # a flat or door number on its own: "daire no 28", "Kapı No: 14" (building and door numbers are always masked)
        for m in self.DOOR.finditer(text):
            if not any(a <= m.start(1) < b for a, b, _, _ in spans):
                spans.append((m.start(1), m.end(1), 0.75, "flat or door number"))
        return [self._r(s, e, sc, why) for s, e, sc, why in _merge(spans)]

    def _has_place(self, seg):
        return any(fold(w) in self.places for w in re.findall(rf"[{TR_LETTER}]+", seg))

    def _grow(self, text, s, e):
        line_start = text.rfind("\n", 0, s) + 1
        # left: up to 5 capitalised/number tokens on the same line
        left = text[line_start:s]
        toks = list(re.finditer(rf"([{TR_UPPER}0-9][{TR_LETTER}0-9.'’]*)\s*$", left))
        k = 0
        while toks and k < 5:
            m = toks[-1]
            word = m.group(1)
            if fold(word) in ("adres", "adresi", "ikametgah") or word.endswith(":"):
                break
            s = line_start + m.start(1)
            left = text[line_start:s]
            toks = list(re.finditer(rf"([{TR_UPPER}0-9][{TR_LETTER}0-9.'’]*)\s*$", left))
            k += 1
        # right: address tokens until a place name, sentence end, or line end (+1 line allowed)
        pos, lines, steps, last_good = e, 0, 0, e
        while pos < len(text) and steps < 30:
            ws = re.match(r"[ \t]*(\n)?[ \t]*", text[pos:])
            if ws.group(1):
                lines += 1
                if lines > 1:
                    break
                nxt = text[pos + ws.end(): pos + ws.end() + 40]
                if not (ADDR_ANCHOR.search(nxt[:30]) or re.match(r"(?:No|Daire|Kat|D\s*:|\d{5}|[A-ZÇĞİÖŞÜ]+\s*/)", nxt)):
                    break
            p2 = pos + ws.end()
            t = ADDR_TOKEN.match(text, p2)
            if not t:
                break
            word = t.group()
            if fold(word.strip(".")) in ("tel", "telefon", "gsm", "e-posta", "vergi", "tc", "t.c", "iban", "konu", "vekili"):
                break
            pos = t.end()
            if word not in ",-":
                last_good = pos
            steps += 1
            if fold(word) in self.places and text[pos:pos + 1] not in ("/",) and not re.match(r"\s*/", text[pos:]):
                # "Çankaya/ANKARA": stop after the province
                if re.search(r"/\s*$", text[p2 - 3:p2]) or fold(word) in wordlist("provinces.txt"):
                    break
        return s, last_good


def _merge(spans):
    spans = sorted(spans, key=lambda x: (x[0], -x[1]))
    out = []
    for s, e, sc, why in spans:
        if out and s <= out[-1][1]:
            ps, pe, psc, pwhy = out[-1]
            out[-1] = (ps, max(pe, e), max(psc, sc), pwhy if psc >= sc else why)
        else:
            out.append((s, e, sc, why))
    return out




# ---------------------------------------------------------------- KVKK Article 6
# Special-category data (özel nitelikli kişisel veri). Lexicon based so it runs
# on CPU with no model; each hit carries the matched term so a reviewer can
# accept/reject it, and those decisions are what tells us which terms to keep.
SPECIAL_LEXICON = {
    "HEALTH": [
        r"rahats[ıi]zl[ıi]ğ[ıi]",
        r"sağl[ıi]k raporu", r"heyet raporu", r"engellilik oran[ıi]",
        r"engelli", r"psikiyatri(?:k)?", r"depresyon", r"anksiyete", r"bipolar", r"şizofreni",
        r"kanser", r"tümör", r"diyabet", r"hiv", r"aids", r"hepatit", r"epilepsi", r"gebelik", r"hamile(?:lik)?",
        r"kürtaj", r"alkol bağ[ıi]ml[ıi]l[ıi]ğ[ıi]", r"madde bağ[ıi]ml[ıi]l[ıi]ğ[ıi]",
        r"kan grubu", r"epikriz", r"yoğun bakım", r"felç", r"kalp krizi", r"covid(?:-19)?",
    ],
    "RELIGION": [
        r"din bilgisi", r"dini inanc[ıi]", r"dini inanç", r"mezhe(?:b|p)(?:i)?", r"alevi", r"sünni", r"hristiyan", r"müslüman", r"yahudi",
        r"ateist", r"deist", r"süryani", r"ezidi", r"başörtü(?:sü|lü)?", r"türban", r"cemevi", r"kilise(?:ye)?",
        r"namaz k[ıi]l", r"oruç tut", r"din değiştir",
    ],
    "POLITICAL": [r"parti üyesi", r"partisi üyesi", r"siyasi görüş", r"siyasi düşünce", r"partili", r"il başkan[ıi]"],
    "UNION": [r"sendika üyesi", r"sendikaya üye", r"sendika üyeliği", r"sendikal faaliyet", r"[A-ZÇĞİÖŞÜ][a-zçğıöşü-]*-?[Ss]en üyesi"],
    "ETHNICITY": [r"etnik köken", r"ırk[ıi]", r"kürt kökenli", r"roman vatandaş", r"çingene"],
    "SEXUAL_LIFE": [r"cinsel yaşam(?: bilgisi)?", r"cinsel yönelim", r"eşcinsel", r"cinsel hayat", r"cinsel ilişki", r"lgbt"],
    "BIOMETRIC_GENETIC": [r"parmak izi (?:şablonu|kayd[ıi]|verisi)", r"parmak izi", r"genetik test", r"dna testi", r"dna analizi", r"retina", r"yüz tanıma"],
    "CRIMINAL_RECORD": [r"mahk[uû]miyet kayd[ıi]", r"adli sicil kayd[ıi]", r"sab[ıi]ka kayd[ıi]", r"mahkumiyet(?:i|ine)?", r"mahkûmiyet(?:i|ine)?",
                        r"hapis cezas[ıi]", r"güvenlik tedbir(?:i|leri)"],
}
SPECIAL_ENTITIES = list(SPECIAL_LEXICON)
ENTITY_LABELS_TR.update({
    "HEALTH": "Sağlık Verisi", "RELIGION": "Din/İnanç", "POLITICAL": "Siyasi Görüş",
    "UNION": "Sendika Üyeliği", "ETHNICITY": "Irk/Etnik Köken", "SEXUAL_LIFE": "Cinsel Hayat",
    "BIOMETRIC_GENETIC": "Biyometrik/Genetik", "CRIMINAL_RECORD": "Ceza Mahkumiyeti",
})
ALL_ENTITIES.extend(SPECIAL_ENTITIES)


# A special-category field and its value: "Tıbbi tanı: Orta dereceli atopik dermatit", "din hanesi Musevi",
# "köken bilgisi Kürt". The value is the personal data; the label alone says nothing about the person.
# Patterns are matched on fold()ed text (one character for one character, see _fold_keep).
SPECIAL_FIELDS = {
    "HEALTH": r"(?:tibbi )?tani|teshis(?:i)?|saglik (?:durumu(?:/tani)?|notu|bilgisi|sorunu)|kronik hastalik(?:lari)?|"
              r"engel(?:lilik)? (?:durumu|orani)|maluliyet (?:durumu|orani)|kullanilan ilac(?:lar)?|ilac (?:bilgisi|kullanimi)|"
              r"(?:uygulanan )?cerrahi islem|alerji(?:si|leri)?|(?:verilen |kullanilan )?ilac(?:lar)?|(?:uygulanan )?tibbi islem|"
              r"tedavi(?: islemi)?|(?:on|kesin|ayirici) tani",
    "RELIGION": r"din(?:i)? (?:hanesi|bilgisi)|dini inanci|mezhebi|din",
    "ETHNICITY": r"etnik koken(?:i)?(?: (?:alani|bilgisi))?|koken bilgisi|irki",
    "UNION": r"sendika (?:bilgisi|uyeligi)",
    "BIOMETRIC_GENETIC": r"biyometrik (?:veri(?:si)?(?: referansi)?|kaydi|bilgisi)|genetik (?:test sonucu|bilgisi|verisi)",
    "CRIMINAL_RECORD": r"adli sicil(?: (?:kaydi|bilgisi))?|adli kaydi|sabika kaydi|ceza kaydi",
    "SEXUAL_LIFE": r"cinsel yonelim(?:i)?",
    "POLITICAL": r"siyasi gorusu|parti uyeligi",
}
FIELD_RES = tuple(re.compile(r"(?<![a-z0-9])(?:" + v + r")(?![a-z0-9])") for v in SPECIAL_FIELDS.values())
# a value without a colon ends at the first of these (folded) words: "etnik köken alanı Ermeni yazılmış"
FIELD_STOP = frozenset("ve ile olarak ise icin yazilmis yazmis gorunuyor goruyorum var yok bulunuyor bulundugu mevcut eslesmiyor "
                       "kayitli mi mu bu olan oldugu degil icerir tutuldugu nedeniyle sebebiyle hakkinda diye kesintisi neden ibaresi "
                       "alani hanesi".split())
# without a colon the label must end in a field noun ("adli sicil kaydı X"; "adli sicil kaydının okunması" is prose)
FIELD_NOUN = ("kaydi", "bilgisi", "hanesi", "alani", "notu", "durumu", "referansi", "verisi", "orani", "uyeligi", "sonucu")
# ... and the value must not be a predicate ("kaydı bulunmamaktadır", "bilgisi yoktur")
FIELD_VERB = ("dir", "dur", "tir", "tur", "yor", "mis", "mus", "mistir", "mustur")


class SpecialCategoryRecognizer(EntityRecognizer):
    """Flags KVKK Art. 6 terms. The span is the matched term widened to the
    preceding word when that word is a qualifier ("tip 2 diyabet", "kronik böbrek")."""
    # the blood group itself ("0 Rh-", "AB Rh pozitif"), health data under KVKK art. 6
    HEALTH_TAIL = re.compile(r"[ \t]+(?:tedavi(?:si|sini)?|tan[ıi]s[ıi]|teşhisi|hastal[ıi]ğ[ıi]|ameliyat[ıi]|ilac[ıi])(?![\w])", re.I)
    FIELD_SEP = re.compile(r"[ \t]*(?:[:=][ \t]*|(?:alani|hanesi)[ \t]+)?")
    FIELD_WORD = re.compile(r"[^\s,;.]+(?:\.\d+)?")
    BLOOD = re.compile(r"(?<![\w])(?:0|A|B|AB)\s?(?:Rh|RH)\s?(?:\+|-|[Pp]ozitif|[Nn]egatif|POZİTİF|NEGATİF)(?![\w+-])")

    def __init__(self):
        self._res = {k: re.compile(r"(?<![\w])(?:" + "|".join(v) + r")(?![\w])", re.I)
                     for k, v in SPECIAL_LEXICON.items()}
        super().__init__(supported_entities=SPECIAL_ENTITIES, name="kvkk_art6_lexicon", supported_language="tr")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for ent, rx in self._res.items():
            if entities and ent not in entities:
                continue
            for m in rx.finditer(text):
                end = m.end()
                if ent == "HEALTH":
                    t = self.HEALTH_TAIL.match(text, end)
                    end = t.end() if t else end
                r = RecognizerResult(ent, m.start(), end, 0.7)
                r.recognition_metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                                          "explanation": f"Art. 6 term '{m.group()}'"}
                out.append(r)
        out.extend(self._fields(text, entities))
        if not entities or "HEALTH" in entities:
            for m in self.BLOOD.finditer(text):
                r = RecognizerResult("HEALTH", m.start(), m.end(), 0.75)
                r.recognition_metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: self.name, "explanation": "blood group"}
                out.append(r)
        # a term hit that is only the label of a value found above says nothing on its own: keep the value
        vals = [r for r in out if r.recognition_metadata.get("explanation", "").startswith(("value after", "blood group"))]
        return [r for r in out if r in vals or not any(v.entity_type == r.entity_type and 0 <= v.start - r.end <= 25 for v in vals)]

    def _fields(self, text, entities):
        f, out = _fold_keep(text), []
        for ent, rx in zip(SPECIAL_FIELDS, FIELD_RES):
            if entities and ent not in entities:
                continue
            out.extend(self._field_values(text, f, ent, rx))
        return out

    def _field_values(self, text, f, ent, rx):
        out = []
        for m in rx.finditer(f):
            sep = self.FIELD_SEP.match(f, m.end())
            colon = ":" in sep.group() or "=" in sep.group()
            if not colon and not m.group().endswith(FIELD_NOUN) and not sep.group().strip():
                continue                      # "Din: İslam", "Tanı: ...": a bare label needs its colon
            pos, end, n = sep.end(), None, 0
            for w in self.FIELD_WORD.finditer(f, pos):
                gap = f[pos if end is None else end:w.start()]
                if "\n" in gap or gap.strip():
                    break
                if not colon and (w.group() in FIELD_STOP or n == 4 or (n == 0 and w.group().endswith(FIELD_VERB))):
                    break
                if n == 10:
                    break
                end, n = w.end(), n + 1
            if end is None:
                continue
            r = RecognizerResult(ent, pos, end, 0.75)
            r.recognition_metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: self.name, "explanation": f"value after '{text[m.start():m.end()]}'"}
            out.append(r)
        return out


# ---------------------------------------------------------------- post-processing shared by server and browser
# Names inside addresses are place names, not people: "Alparslan Türkeş Caddesi", "Fevzi Çakmak Mah.".
PLACE_WORD = (r"(?:Mahallesi|Mahalle|Mah\.?|Mh\.?|Caddesi|Cadde|Cad\.?|Cd\.?|Sokağı|Sokak|Sok\.?|Sk\.?|Bulvarı|Bulvar|Blv\.?|Bulv\.?|"
              r"Meydanı|Yolu|Parkı|Köyü|Mevkii|Sitesi|Apartmanı|Apt\.?|Plaza|Camii|Hastanesi|Okulu|Lisesi|Üniversitesi|"
              r"Havalimanı|Stadı|Köprüsü|Kampüsü|Konutları|Evleri)")
PLACE_AFTER = re.compile(rf"^[ \t]{{0,2}}(?:{PLACE_WORD}|{PLACE_WORD.upper()})(?![{TR_LETTER}])")
# "Altı Yüz Bin TL": an amount written in words (OCR'd handwriting makes them look like names)
MONEY_AFTER = re.compile(r"^[ \t]{0,2}(?:TL|TRY|₺|Türk Lirası|lira|Lira|LİRA|EUR|Euro|USD|Dolar)\b")


def drop_place_names(text, results):
    """Drop PERSON spans that are part of an address or are followed by a street/mahalle/building word.
    Run before overlap resolution, so a model or rule PERSON inside an address never wins over it and,
    with street-visible addresses, never masks the street name either."""
    addrs = [(r.start, r.end) for r in results if r.entity_type == "ADDRESS"]
    out = []
    for r in results:
        if r.entity_type == "PERSON" and (PLACE_AFTER.match(text[r.end:r.end + 16]) or MONEY_AFTER.match(text[r.end:r.end + 14])
                                          or any(a < r.end and r.start < b for a, b in addrs)):
            continue
        out.append(r)
    return out


# street-visible addresses: which parts of an address stay readable
_STREET_KEYS = frozenset(fold(w) for w in (
    "Mahallesi", "Mahalle", "Mah", "Mh", "Caddesi", "Cadde", "Cad", "Cd", "Sokağı", "Sokak", "Sok", "Sk", "Bulvarı",
    "Bulvar", "Blv", "Bulv", "Meydanı", "Yolu", "Köyü", "Mevkii", "Parkı"))
_OCR_STREET = {"meh", "moh", "mah", "nah", "mab", "cod", "ced", "cadi", "cadı", "5k", "sk", "s.k", "5ok", "sek", "blu", "biv"}


def _edit1(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def _street_key(tok):
    """Street/mahalle keyword, tolerant of OCR misreads inside an already-detected address
    ("Meh." for "Mah.", "Cod." for "Cad.", "Mahalesi")."""
    f = fold(tok.rstrip(".,:"))
    if f in _STREET_KEYS or f in _OCR_STREET:
        return True
    return len(f) >= 5 and any(len(k) >= 5 and _edit1(f, k) for k in _STREET_KEYS)


_ADDR_TOK = re.compile(rf"[{TR_LETTER}0-9][{TR_LETTER}0-9'’.:-]*")
_HOUSE = re.compile(rf"^(?:No|NO|Daire|DAİRE|D|Kat|KAT|K|Blok|BLOK|Apt|APT|Apartmanı|Sitesi|SİTESİ|Plaza|İş\s*Merkezi)\b", re.I)


def address_parts(text, start, end):
    """Split an address span into the parts to mask: building, site/block, door, floor and flat.
    Mahalle, street, avenue, boulevard, village, district, province and postcode stay visible.
    Returns a list of (start, end) ranges; an empty list means only public place names were found."""
    seg = text[start:end]
    toks = [(m.start() + start, m.end() + start, m.group()) for m in _ADDR_TOK.finditer(seg)]
    provinces = wordlist("provinces.txt")
    places = provinces | wordlist("districts.txt")
    visible = [False] * len(toks)
    n = len(toks)
    for i, (_, _, t) in enumerate(toks):
        bare = t.rstrip(".,:")
        if _street_key(bare):
            visible[i] = True
            # the name before the keyword: up to 4 tokens back, stopping at a house token or an earlier keyword
            k = i - 1
            while k >= 0 and i - k <= 4 and not visible[k] and not _HOUSE.match(toks[k][2]) \
                    and not re.search(r"[:]", toks[k][2]) and "\n" not in text[toks[k][1]:toks[k + 1][0]] \
                    and "," not in text[toks[k][1]:toks[k + 1][0]]:
                visible[k] = True
                k -= 1
        f = fold(bare)
        if f in places or re.fullmatch(r"\d{5}", bare) or fold(bare) in ("turkiye", "tr"):
            visible[i] = True
            # "Kuşadası/AYDIN", "Kuşadası AYDIN": the word before a province is its district
            if f in provinces and i > 0 and not visible[i - 1] and not _HOUSE.match(toks[i - 1][2]) \
                    and re.fullmatch(rf"[{TR_UPPER}][{TR_LETTER}]+", toks[i - 1][2]) \
                    and re.fullmatch(r"[ \t]*/?[ \t]*", text[toks[i - 1][1]:toks[i][0]]):
                visible[i - 1] = True
    parts, cur = [], None
    for (s, e, t), v in zip(toks, visible):
        if v:
            if cur:
                parts.append(cur)
            cur = None
        else:
            cur = (cur[0], e) if cur else (s, e)
    if cur:
        parts.append(cur)
    return parts


# Address roles (court filings). A party's own address is personal data and is masked whole; the address of the
# property a case is about (the leased flat, the parcel, the building in dispute) is evidence the court must read.
_PROPERTY = (r"kiralanan\w*|kira\s+konusu|mecur\w*|ta[şs][ıi]nmaz\w*|gayrimenkul\w*|tapu\w*|ba[ğg][ıi]ms[ıi]z\s+b[öo]l[üu]m\w*|"
             r"dava\s+konusu|tahliye\w*|ada\s+\d+\s+parsel|\d+\s+ada\b")
_PROPERTY_NOUN = r"ta[şs][ıi]nmaz|daire|d[üu]kkan|i[şs]yeri|mesken|bina|arsa|ba[ğg][ıi]ms[ıi]z\s+b[öo]l[üu]m|kiralanan|mecur|gayrimenkul|konut"
PROPERTY_BEFORE = re.compile(rf"(?i:{_PROPERTY})[^\n.;]{{0,60}}$")
PROPERTY_AFTER = re.compile(rf"^[ \t,]*(?i:adres(?:inde|indeki|li|teki)?)\s*(?i:(?:bulunan|kain|kâin|yer\s+alan|mevcut)\s+)?"
                            rf"[^\n.;]{{0,30}}?(?i:{_PROPERTY_NOUN})")
_PARTY = (r"[şs][üu]pheli|san[ıi]k|m[üu][şs]teki|ma[ğg]dur|kat[ıi]lan|m[üu]dafi|vekil(?:i|leri)?|davac[ıi]|daval[ıi]|"
          r"bor[çc]lu|alacakl[ıi]|ihtar\s+eden|muhatap|ta[ns][ıi]k|itiraz\s+eden|ba[şs]vurucu|ba[şs]vuran|talep\s+eden|"
          r"m[üu]vekkil|kirac[ıi]|kiraya\s+veren|mal\s+sahibi|i[şs][çc]i|i[şs]veren|hasta|veli|vasi")
PARTY_LINE = re.compile(rf"(?im)^[ \t]*(?:{_PARTY})(?:[ \t]+(?:{_PARTY}))?[ \t]*(?:\([^)\n]*\))?[ \t]*[:：]")
# a form row with the address right after the party's label, no colon: "Kiraya verenin Ege Mah. ...", "Kiracının adresi ..."
PARTY_LABEL_ONLY = re.compile(rf"(?i)^[ \t|]*(?:{_PARTY})(?:n[ıi]n|[ıi]n|nin|n[ıi]n\s+adresi|[ıi]n\s+adresi)?[ \t]*[:：]?[ \t|]*$")
RESIDENCE_BEFORE = re.compile(r"(?i:ikamet\w*|yerle[şs]im\s+yeri\w*|oturdu[ğg]u|mukim|adres(?:i|leri)?\s*[:：])[^\n.;]{0,25}$")
RESIDENCE_AFTER = re.compile(r"^[ \t,]*(?i:adres(?:inde|indeki)?)\s*(?i:ikamet\w*|otur\w*|mukim|yerle[şs]\w*|sakin\w*)")


def address_role(text, start, end):
    """'property' (evidence: keep readable in a court copy), 'party' (someone's own address: mask whole) or None.
    Property cues win: "Kiralananın Adresi:" is a label too, but it names the leased flat, not a home."""
    line = text.rfind("\n", 0, start) + 1
    before = text[max(line, start - 90):start]
    after = text[end:end + 80]
    if PROPERTY_BEFORE.search(before) or PROPERTY_AFTER.match(after):
        return "property"
    if RESIDENCE_BEFORE.search(before) or RESIDENCE_AFTER.match(after):
        return "party"
    # the address sits under (or on) a party's line: "Şüpheli : Ad Soyad (TC: ...)" then the address on the next line
    if PARTY_LINE.match(text[line:start]) or PARTY_LABEL_ONLY.match(text[line:start]):
        return "party"
    if not text[line:start].strip():
        prev_end = line - 1
        prev = text.rfind("\n", 0, max(prev_end, 0)) + 1
        if prev_end > 0 and PARTY_LINE.match(text[prev:prev_end]):
            return "party"
    return None


def _under_a_name(text, start, results):
    """The address opens its line and the line before it is just a person's name."""
    line = text.rfind("\n", 0, start) + 1
    if text[line:start].strip(" \t|") or line == 0:
        return False
    prev = text.rfind("\n", 0, line - 1) + 1
    a, b = prev, line - 1
    while a < b and text[a] in " \t|":
        a += 1
    while b > a and text[b - 1] in " \t|,":
        b -= 1
    return b > a and any(r.entity_type == "PERSON" and r.start <= a and r.end >= b for r in results)


def split_addresses(text, results, make):
    """Street-visible mode (the court profile): an address is handled by its role (see address_role).
    A party's own address is masked whole; a property in dispute stays readable; any other address keeps
    only its house-level parts masked (see address_parts).
    make(entity, start, end, score, why, name=...) builds a result of the caller's type."""
    out = []
    for r in results:
        if r.entity_type != "ADDRESS":
            out.append(r)
            continue
        role = address_role(text, r.start, r.end)
        if role is None and _under_a_name(text, r.start, results):
            role = "party"  # an addressee block: "SAYIN | Ad SOYAD | <address>"
        name = (r.recognition_metadata or {}).get(RecognizerResult.RECOGNIZER_NAME_KEY, "tr_address")
        if role == "party":
            out.append(make("ADDRESS", r.start, r.end, r.score, "a party's own address (masked whole)", name=name))
            continue
        if role == "property":
            continue  # the address of the property the case is about: evidence, left readable
        for s, e in address_parts(text, r.start, r.end):
            out.append(make("ADDRESS", s, e, r.score, "building, door or flat of an address (street left visible)", name=name))
    return out


def ocr_name_repeats(text, ranges, results):
    """On OCR'd pages a name written by hand is read differently each time ("YAVAŞ", "YAVAS", "YAVAŞ"
    in the signature block). Mask capitalised tokens in OCR ranges that equal, or are one edit away from
    (5+ letters), a token of a name already found. Unlike the rule second pass, ordinary words are allowed
    here (YAVAŞ is also an adjective), but only in OCR'd text and only as a repeat of an accepted name."""
    names = {fold(m.group()) for r in results if r.entity_type == "PERSON"
             for m in TOKEN_RE.finditer(text[r.start:r.end]) if len(m.group()) >= 4}
    names -= wordlist("stopwords_caps.txt")
    if not names:
        return []
    covered = [(r.start, r.end) for r in results]
    out = []
    for a, b in ranges:
        for m in TOKEN_RE.finditer(text, a, b):
            t = m.group()
            if len(t) < 4 or not t[0].isupper() or any(x <= m.start() < y for x, y in covered):
                continue
            f = fold(t)
            if f in names or (len(f) >= 5 and any(len(n) >= 5 and _edit1(f, n) for n in names)):
                out.append((m.start(), m.end(), 0.75, "repeat of a name found on an OCR'd page (handwriting read differently)"))
    return out


# Form rows on OCR'd pages: "T.C. Kimlik No.  <handwriting>" and "Adı soyadı  <handwriting>". OCR often
# turns handwritten digits into letters ("ÇAKAKLATA"), so the checksum and name rules cannot see them;
# the printed label is read reliably, and what follows it on the row is the value, whatever it reads as.
FORM_TCKN_LABEL = re.compile(r"(?:t\.?\s?c\.?\s*)?k[il1|]?m[il1|]?[il1|]?k\s*n[o0]\b\.?[:;,.]?|\btckn\b[:.]?|\bt\.?\s?c\.?\s*n[o0]\b\.?:?")
FORM_NAME_LABEL = re.compile(r"\bad[i1]?\.?\s*[-/]?\s*soy\s?ad[i1]?\b\.?:?|\bad\s+soyad\b:?")
FORM_ADDR_LABEL = re.compile(r"\b(?:ikamet(?:gah|gahi|gah[i1]|atgah[i1]?)?|ikamatgah[i1]?|adres[i1]?)\b\.?:?")
FORM_ANY_LABEL = re.compile(r"kimlik|soyad|ikamet|adres|kirac|kiraya|kefil|vergi|kira |dairesi|mahallesi|sokag|banka|muddet|baslangic")
FORM_STOP = re.compile(r" {3,}|\bvergi\b|\bv\.?\s?d\.?\b|\bsicil\b", re.I)


def ocr_form_values(text, ranges):
    found = []
    for a, b in ranges:
        pos = a
        while pos < b:
            e = text.find("\n", pos, b)
            e = b if e < 0 else e
            line, f = text[pos:e], fold(text[pos:e])  # fold keeps one char per char for these letters
            m = FORM_ADDR_LABEL.search(f) if len(f) == len(line) else None
            if m:
                # the address written after the label, and the next line when it carries no label of its own
                seg_s = pos + m.end()
                seg_e = e
                n_end = text.find("\n", e + 1, b)
                n_end = b if n_end < 0 else n_end
                nxt = text[e + 1:n_end]
                if e < b and len(re.findall(rf"[{TR_LETTER}0-9]+", nxt)) >= 2 and not FORM_ANY_LABEL.search(fold(nxt)):
                    seg_e = n_end
                seg = text[seg_s:seg_e]
                toks = list(re.finditer(rf"[{TR_LETTER}0-9][{TR_LETTER}0-9'’.:/-]*", seg))
                if len(toks) >= 2:
                    found.append(("ADDRESS", seg_s + toks[0].start(), seg_s + toks[-1].end(), 0.8,
                                  "address written in a form row labelled İkametgahı/Adresi on an OCR'd page"))
            for lab, typ in ((FORM_TCKN_LABEL, "TCKN"), (FORM_NAME_LABEL, "PERSON")):
                m = lab.search(f) if len(f) == len(line) else None
                if not m:
                    continue
                rest_s = m.end()
                stop = FORM_STOP.search(line, rest_s)
                rest_e = stop.start() if stop else len(line)
                seg = line[rest_s:rest_e]
                base = pos + rest_s
                toks = list(re.finditer(rf"[{TR_LETTER}0-9][{TR_LETTER}0-9'’.:/-]*", seg))
                if not toks and e < b:
                    # label alone on its line (two-line label cell): the value is the start of the next line
                    n_end = text.find("\n", e + 1, b)
                    n_end = b if n_end < 0 else n_end
                    nxt = text[e + 1:n_end]
                    if not FORM_ANY_LABEL.search(fold(nxt)[:12]):
                        stop = FORM_STOP.search(nxt)
                        seg, base = nxt[:stop.start() if stop else len(nxt)], e + 1
                        toks = list(re.finditer(rf"[{TR_LETTER}0-9][{TR_LETTER}0-9'’.:/-]*", seg))
                if not toks or (typ == "PERSON" and len(toks) > 4):
                    continue
                if typ == "TCKN" and sum(len(t.group()) for t in toks) < 5:
                    continue
                s0, e0 = base + toks[0].start(), base + toks[-1].end()
                found.append((typ, s0, e0, 0.8, "value of a form row labelled " + ("T.C. Kimlik No" if typ == "TCKN" else "Adı soyadı")
                              + " on an OCR'd page"))
            pos = e + 1
    return found


# OCR'd text: handwritten digits are often misread, so an 11-digit number that fails the TCKN checksum
# is still masked as a probable TCKN. Only inside OCR'd pages: in born-digital text an invalid 11-digit
# number is a UYAP or file number, not an ID.
OCR_DIGIT = str.maketrans("OoDIl|SsBZz", "00011155822")
OCR_TCKN = re.compile(r"(?<![0-9A-Za-z])([1-9IlSB](?:[ ]?[0-9OoDIl|SsBZz]){9,12})(?![0-9A-Za-z])")
_NOT_ID = ("uyap", "esas", "karar no", "dosya", "sicil", "mersis", "fatura", "seri", "sira no", "barkod")


def ocr_tckn(text, ranges):
    found = []
    for a, b in ranges:
        for m in OCR_TCKN.finditer(text, a, b):
            raw = m.group(1)
            digits = raw.translate(OCR_DIGIT).replace(" ", "")
            if sum(c.isdigit() for c in raw) < 9 or tckn_valid(digits):
                continue  # valid ones are found by TCKNRecognizer
            if len(digits) != 11 and not _has_context(text, m.start(), ("kimlik", "kimlk", "kımlık", "tckn", "t.c", "tc no"), 40):
                continue  # 10 or 12-13 digits: only right after an ID label
            if re.search(r"\d[ ]?$", text[max(0, m.start() - 2):m.start()]) or re.match(r"^[ ]?\d", text[m.end():m.end() + 2]):
                continue  # a piece of a longer number (IBAN, card)
            if _has_context(text, m.start(), _NOT_ID, 25):
                continue
            found.append((m.start(1), m.end(1), 0.75, "11 digits on an OCR'd page, checksum failed (likely misread), masked to be safe"))
    return found


def default_recognizers():
    return [TCKNRecognizer(), PassportRecognizer(), ForeignIDRecognizer(), UETSRecognizer(), VKNRecognizer(), IBANRecognizer(), CreditCardRecognizer(),
            EmailRecognizer(), PhoneRecognizer(), PlateRecognizer(), IPRecognizer(),
            BirthDateRecognizer(), PersonRecognizer(), AddressRecognizer(), SpecialCategoryRecognizer(), SpelledNumberRecognizer()]
