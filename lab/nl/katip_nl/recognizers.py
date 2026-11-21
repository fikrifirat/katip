"""Dutch personal-data rules (AVG/GDPR) for Katip.

Standard library only, so the same file can run in the browser (Pyodide), in Kalkan and on the command line.
detect() returns spans in the same shape as Katip's Turkish engine (src/py/local_detect.py), so the
masking, restore and UI code can take either.

What is masked by default: BSN, IBAN, postcode + house number, phone, e-mail, licence plate, ID-document
numbers (passport, ID card, driving licence), V-number, date of birth, VAT id (btw-id), names.
What stays readable on purpose: ECLI numbers, case and roll numbers, article citations (art. 7:611 BW),
court names, ordinary dates, street names and towns (only the house number and postcode are masked in
"street" mode, the same choice the Turkish lawyers asked for).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

LETTER = "A-Za-zÀ-ÖØ-öø-ÿĳĲ"
MONTHS_NL = "januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december"
UP = "A-ZÀ-ÖØ-ÞĲ"


@dataclass
class Span:
    entity_type: str
    start: int
    end: int
    score: float
    recognizer: str
    explanation: str = ""
    ref: str = ""  # for a repeated surname: the full name it belongs to


# ---------------------------------------------------------------- checksums

def bsn_valid(d: str) -> bool:
    """11-proef for BSN (and RSIN): 9 digits, sum(d_i * w_i) with weights 9..2 and -1, divisible by 11."""
    d = re.sub(r"\D", "", d)
    if len(d) == 8:
        d = "0" + d
    if len(d) != 9 or d == "000000000":
        return False
    s = sum(int(c) * w for c, w in zip(d[:8], range(9, 1, -1))) - int(d[8])
    return s % 11 == 0


def iban_valid(s: str) -> bool:
    s = re.sub(r"\s", "", s).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    if s.startswith("NL") and not re.fullmatch(r"NL\d{2}[A-Z]{4}\d{10}", s):
        return False
    n = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(n) % 97 == 1


def btw_valid(s: str) -> bool:
    """Dutch VAT id NL#########B##. Since 2020 the 9 digits pass mod-97 with 'NL' in front (sole traders);
    older ids pass the 11-proef. Accept either."""
    m = re.fullmatch(r"NL(\d{9})B(\d{2})", re.sub(r"[\s.]", "", s).upper())
    if not m:
        return False
    if bsn_valid(m.group(1)):
        return True
    n = "".join(str(int(c, 36)) for c in "NL" + m.group(1) + "B" + m.group(2))
    return int(n) % 97 == 1


# ---------------------------------------------------------------- helpers

def _before(text, start, window=50):
    return text[max(0, start - window):start].lower()


def _has(text, start, words, window=50):
    b = _before(text, start, window)
    return any(w in b for w in words)


BSN_CUES = ("bsn", "burgerservicenummer", "sofinummer", "sofi-nummer", "sofi nummer", "persoonsnummer",
            "citizen service number", "social security number")
RSIN_CUES = ("rsin", "fiscaal nummer", "fiscaalnummer")
KVK_CUES = ("kvk", "kamer van koophandel", "handelsregister", "chamber of commerce")
DOB_CUES = ("geboren", "geb.", "geboortedatum", "date of birth", "born", "geb ")
DOC_CUES = ("paspoort", "identiteitskaart", "id-kaart", "id kaart", "documentnummer", "rijbewijs",
            "verblijfsdocument", "verblijfspas", "passport", "identity card", "document number", "driving licence")
VNR_CUES = ("v-nummer", "v-nr", "vreemdelingennummer", "v nummer")


# ---------------------------------------------------------------- recognizers

NUM9 = re.compile(r"(?<![\d./-])(\d{4}[.\s]?\d{2}[.\s]?\d{3}|\d{3}[.\s]\d{3}[.\s]\d{3}|\d{8,9})(?![\d/-]|\.\d)")


def find_bsn(text):
    out = []
    for m in NUM9.finditer(text):
        raw = m.group(1)
        digits = re.sub(r"\D", "", raw)
        if len(digits) not in (8, 9):
            continue
        cue = _has(text, m.start(), BSN_CUES)
        if _has(text, m.start(), RSIN_CUES + KVK_CUES, 30) and not cue:
            continue  # RSIN / KvK are handled below
        if bsn_valid(digits) and (len(digits) == 9 or cue):
            out.append(Span("BSN", m.start(1), m.end(1), 0.95 if cue else 0.75, "bsn_11proef",
                            "11-proef ok" + (" + BSN cue" if cue else "")))
        elif cue and len(digits) == 9:
            out.append(Span("BSN", m.start(1), m.end(1), 0.6, "bsn_cue", "BSN cue, 11-proef failed (typo or scan?)"))
    return out


IBAN_RE = re.compile(r"\b([A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){10,30})\b")


def find_iban(text):
    out = []
    for m in IBAN_RE.finditer(text):
        parts = re.split(r"( )", m.group(1))
        for k in range(len(parts), 0, -2):
            c = "".join(parts[:k])
            if iban_valid(c):
                out.append(Span("IBAN", m.start(1), m.start(1) + len(c), 0.97, "iban_mod97", "IBAN mod-97 ok"))
                break
    return out


# 1234 AB; SA, SD, SS are never issued
POSTCODE_RE = re.compile(r"(?<![\w/-])([1-9]\d{3}) ?(?!SA|SD|SS)([A-Z]{2})(?![\w])")
# kept to suffixes that are (almost) only street names: "oord", "ring", "berg" etc. also end ordinary words
# ("Antwoord 5", "Vordering 2"), so they are left out
STREET_SUFFIX = (r"(?:straat|straatweg|weg|laan|plein|gracht|kade|singel|dijk|pad|steeg|dreef|"
                 r"boulevard|plantsoen|burgwal|dwarsstraat|hof|markt|kanaal|haven|wal|dam|vliet|allee|brink)")
# "Keizersgracht 123-III", "Van Baerlestraat 12A", "Laan van Meerdervoort 5 bis", "Postbus 1234"
STREET_RE = re.compile(
    rf"\b((?:[{UP}][{LETTER}'’.-]*\s(?:(?:van|de|der|den|het|ten|ter|op|in|aan)\s)*)*"
    rf"[{UP}][{LETTER}'’.-]*{STREET_SUFFIX}|Laan van [{UP}][{LETTER}]+)"
    rf"\s+(\d{{1,5}}(?!\d)(?:(?:[A-Z]{{1,2}}|[a-z])\b|\s[A-Z]\b|-(?:[IVX]+|\d{{1,3}}(?:hg|h|bg)?|[A-Za-z]{{1,3}})\b|\s(?:bis|hs|hg|bg|zw)\b)?)"
    rf"(?!\s?(?:%|euro|jaar|maanden|dagen|uur|{MONTHS_NL})\b)")


CITIES_LIKE_STREETS = {"Amsterdam", "Rotterdam", "Schiedam", "Zaandam", "Edam", "Volendam", "Monnickendam",
                       "Leidschendam", "Spaarndam", "Wijk bij Duurstede", "Oosterhout", "Dordrecht"}


def find_address(text, detail="street"):
    """detail="street": mask house number and postcode only. detail="full": mask the whole line."""
    out = []
    for m in STREET_RE.finditer(text):
        if m.group(1) in CITIES_LIKE_STREETS:
            continue  # "Rb. Amsterdam 26 juli 2018"
        if detail == "full":
            out.append(Span("ADDRESS", m.start(1), m.end(2), 0.85, "nl_street", "street + house number"))
        else:
            out.append(Span("HOUSE_NUMBER", m.start(2), m.end(2), 0.85, "nl_street",
                            f"house number after '{m.group(1)}'"))
    for m in POSTCODE_RE.finditer(text):
        # 1234 AB must look like a postcode, not "2023 BV" in a company name: require a town or address nearby
        after = text[m.end():m.end() + 40]
        before = text[max(0, m.start() - 60):m.start()]
        town_after = re.match(rf"\s{{1,3}}[{UP}][{LETTER}'’-]{{2,}}", after) is not None
        addressy = STREET_RE.search(before) is not None or "postcode" in before.lower()
        if not (town_after or addressy):
            continue
        if m.group(2) in ("BV", "NV", "VOF", "CV") and not addressy:
            continue
        if "postbus" in before[-25:].lower():
            continue  # P.O. boxes belong to organisations (courts, the tax office), not to a person
        out.append(Span("POSTCODE", m.start(1), m.end(2), 0.9, "nl_postcode", "Dutch postcode"))
    return out


PHONE_RE = re.compile(
    r"(?<![\w+])((?:\+|00)31[\s-]?(?:\(0\))?[\s-]?[1-9](?:[\s-]?\d){8}"      # +31 6 1234 5678, +31 (0)20 ...
    r"|0[1-9](?:[\s-]?\d){8}"                                               # 06-12345678, 020 123 4567
    r"|\(0\d{2,3}\)[\s-]?\d(?:[\s-]?\d){5,6}"                               # (020) 123 45 67
    r"|\+(?!31)[1-9]\d{0,2}(?:[\s-]?\d){6,12})(?![\w])")                    # foreign numbers


def find_phone(text):
    out = []
    for m in PHONE_RE.finditer(text):
        s = m.group(1)
        digits = re.sub(r"\D", "", s)
        if s.startswith("0") and not re.search(r"[\s-]", s) and len(digits) == 10 and not _has(
                text, m.start(), ("tel", "telefoon", "mobiel", "phone", "gsm", "bel", "nummer")):
            # bare 10-digit run: could be a V-number or an account; only with a cue
            continue
        out.append(Span("PHONE", m.start(1), m.end(1), 0.85, "nl_phone", "phone number"))
    return out


EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")


def find_email(text):
    return [Span("EMAIL", m.start(), m.end(), 0.97, "email") for m in EMAIL_RE.finditer(text)]


# Dutch kenteken side codes, written with dashes
_P = [r"[A-Z]{2}-\d{2}-\d{2}", r"\d{2}-\d{2}-[A-Z]{2}", r"\d{2}-[A-Z]{2}-\d{2}", r"[A-Z]{2}-\d{2}-[A-Z]{2}",
      r"[A-Z]{2}-[A-Z]{2}-\d{2}", r"\d{2}-[A-Z]{2}-[A-Z]{2}", r"\d{2}-[A-Z]{3}-\d", r"\d-[A-Z]{3}-\d{2}",
      r"[A-Z]{2}-\d{3}-[A-Z]", r"[A-Z]-\d{3}-[A-Z]{2}", r"[A-Z]{3}-\d{2}-[A-Z]", r"[A-Z]-\d{2}-[A-Z]{3}",
      r"\d-[A-Z]{2}-\d{3}", r"\d{3}-[A-Z]{2}-\d"]
PLATE_RE = re.compile(r"(?<![\w-])(" + "|".join(_P) + r")(?![\w-])")


def find_plate(text):
    out = []
    for m in PLATE_RE.finditer(text):
        cue = _has(text, m.start(), ("kenteken", "voertuig", "auto", "licence plate", "registration"))
        out.append(Span("PLATE", m.start(1), m.end(1), 0.9 if cue else 0.7, "nl_kenteken", "Dutch licence plate"))
    return out


# passport / ID card: 2 letters, 6 letters-or-digits, 1 digit; letter O is never used
DOC_RE = re.compile(r"(?<![\w])([A-NP-Z]{2}[A-NP-Z0-9]{6}\d)(?![\w])")
DIGITS10 = re.compile(r"(?<![\d.])(\d{10})(?![\d])")


def find_documents(text):
    out = []
    for m in DOC_RE.finditer(text):
        if _has(text, m.start(), DOC_CUES, 60) or re.search(r"\d", m.group(1)[2:8]):
            if re.fullmatch(r"[A-Z]+\d", m.group(1)) and not _has(text, m.start(), DOC_CUES, 60):
                continue  # ALLCAPSWORD1
            out.append(Span("ID_DOCUMENT", m.start(1), m.end(1), 0.85, "nl_document_number",
                            "passport / ID-card number shape"))
    for m in DIGITS10.finditer(text):
        if _has(text, m.start(), VNR_CUES, 40):
            out.append(Span("V_NUMBER", m.start(1), m.end(1), 0.9, "nl_vnummer", "V-number (IND)"))
        elif _has(text, m.start(), ("rijbewijs", "driving licence", "driver's licence"), 40):
            out.append(Span("ID_DOCUMENT", m.start(1), m.end(1), 0.85, "nl_rijbewijs", "driving licence number"))
    return out


BTW_RE = re.compile(r"\b(NL\s?\d{4}\.?\d{2}\.?\d{3}\.?B\.?\d{2})\b", re.I)
KVK_RE = re.compile(r"(?<![\d.])(\d{8})(?![\d])")


def find_business(text):
    out = []
    for m in BTW_RE.finditer(text):
        ok = btw_valid(m.group(1))
        out.append(Span("VAT_ID", m.start(1), m.end(1), 0.9 if ok else 0.7, "nl_btw",
                        "VAT id (identifies sole traders)" + ("" if ok else ", checksum failed")))
    for m in KVK_RE.finditer(text):
        if _has(text, m.start(), KVK_CUES, 40):
            out.append(Span("KVK", m.start(1), m.end(1), 0.8, "nl_kvk", "KvK number (personal data for sole traders)"))
    for m in NUM9.finditer(text):
        if _has(text, m.start(), RSIN_CUES, 30) and bsn_valid(m.group(1)):
            out.append(Span("RSIN", m.start(1), m.end(1), 0.8, "nl_rsin", "RSIN / fiscal number (11-proef ok)"))
    return out


MONTHS = ("januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december|"
          "january|february|march|may|june|july|august|october|jan|feb|mrt|apr|jun|jul|aug|sep|sept|okt|oct|nov|dec")
DATE_RE = re.compile(rf"(?<![\d])(\d{{1,2}}[-/.]\d{{1,2}}[-/.](?:19|20)\d{{2}}|\d{{1,2}} (?:{MONTHS})\.? (?:19|20)\d{{2}})(?![\d])",
                     re.I)


def find_birth_dates(text):
    out = []
    for m in DATE_RE.finditer(text):
        before = re.split(r"[.;]\s|\n", _before(text, m.start(), 30))[-1]  # same sentence / line only
        if any(c in before for c in DOB_CUES):
            out.append(Span("BIRTH_DATE", m.start(1), m.end(1), 0.9, "nl_birth_date", "date after a birth cue"))
    return out


# ---------------------------------------------------------------- names

TUSSEN = r"(?:van der|van den|van de|van 't|van het|in 't|in het|op den|op de|uit den|uit de|ten|ter|te|van|de|den|der|het|'t|d'|la|le|du|da|di|el|al)"
INITIALS = rf"(?:(?:[{UP}]|Th|Chr|Joh|Ph|IJ)\.(?:\s?(?:[{UP}]|Th|Chr|Joh|Ph|IJ)\.){{0,5}})"
LOW = "a-zà-öø-ÿĳ\u0101-\u017f'’"  # incl. ć, š, ł ... (Pavićević, Mikołajczyk)
NAMEWORD = rf"[{UP}\u0100-\u017e][{LOW}]+(?:-[{UP}][{LOW}]+)?"
SURNAME = rf"(?:{TUSSEN} )?{NAMEWORD}(?:-(?:{TUSSEN} )?{NAMEWORD})?"  # "Brokers-van Dijk"
TITLES = (r"(?:de heer|heer|mevrouw|mevr\.|mw\.|dhr\.|hr\.|mr\.|dr\.|drs\.|ir\.|ing\.|prof\.|bc\.|"
          r"Mr\.|Dr\.|Drs\.|Ir\.|Ing\.|Prof\.|Dhr\.|Mevr\.|Mw\.|De heer|Mevrouw|Mr|Mrs|Ms|Miss|Dhr|Mevr)")
TITLED_RE = re.compile(rf"\b{TITLES}\s+(?:{TITLES}\s+)*((?:{INITIALS} ?)?(?:{NAMEWORD} )?{SURNAME})")
INITIALS_RE = re.compile(rf"(?<![\w.])({INITIALS} ?{SURNAME})")
ROLE_RE = re.compile(
    r"(?im)^\s*(?:naam|name|achternaam|voornaam|voornamen|surname|first name|cliënt|client|werknemer|werkgever|"
    r"huurder|verhuurder|eiser|eiseres|gedaagde|verzoeker|verzoekster|verweerder|verweerster|getuige|"
    r"contactpersoon|ondergetekende|belanghebbende)\s*[:]\s*(.+?)\s*$")
SIGN_RE = re.compile(r"(?i)(?:met vriendelijke groet|hoogachtend|kind regards|best regards|groet(?:en)?)[,.]?\s*\n+\s*"
                     rf"((?:{TITLES}\s+)?(?:{INITIALS}\s?|{NAMEWORD}\s)(?:{SURNAME}))")

# words that look like names after a title but aren't
NOT_NAMES = {"Rechtbank", "Gerechtshof", "Hoge", "Raad", "Staat", "Gemeente", "Belastingdienst", "Minister",
             "Staatssecretaris", "Kantonrechter", "Advocaat", "Voorzitter", "College", "Burgemeester", "Ministerie",
             "Inspecteur", "Directeur", "Notaris", "Officier", "Justitie", "Openbaar", "Ministerie", "Wet", "Artikel",
             "Boek", "Titel", "Afdeling", "The", "Court", "State", "Bijlage", "Hoofdstuk", "Paragraaf", "Deel",
             "Bijlagen", "Annex", "Eiser", "Eiseres", "Eisers", "Gedaagde", "Gedaagden", "Verweerder", "Verweerster",
             "Verzoeker", "Verzoekster", "Appellant", "Appellante", "Verdachte", "Belanghebbende", "Werkgever",
             "Werknemer", "Huurder", "Verhuurder", "Cliënt", "Client", "Partijen", "Rechtbank", "Kantonrechter", "Punt", "Onderdeel", "Productie", "Grief", "Middel", "Rov", "Zie", "Vgl"}


# capitalised function words that start sentences and headings ("I. Het proces-verbaal", "V. De opname")
STOP = {"Het", "De", "Een", "Dit", "Deze", "Die", "Dat", "Er", "Ook", "Op", "In", "Bij", "Voor", "Na", "Met", "Zo",
        "Als", "Nu", "Wel", "Niet", "Geen", "Hij", "Zij", "Ik", "Wij", "U", "Uw", "Zijn", "Haar", "Hun", "Om", "Over",
        "Aan", "Tot", "Uit", "Door", "Onder", "Naar", "Ter", "Van", "En", "Of", "Maar", "Dan", "Daarom", "Daarbij",
        "Wat", "Wie", "Waar", "Hoe", "Ten", "Te", "Den", "Der"}


# surnames that are also ordinary words in court text: mask them where found, but don't sweep the document for them
REPEAT_STOP = {"Hof", "Raad", "Staat", "Recht", "Wet", "Zaak", "Man", "Lam", "Klein", "Prijs", "Post", "Arts", "Oranje"}


def _clean_name(text, s, e):
    v = text[s:e]
    v = re.split(r" te (?=[A-Z])", v)[0]  # "mr. P. Oskam te Amsterdam": the town is not part of the name
    v = re.sub(r"(?:[\s,.;:]+(?:van|de|der|den|ten|ter|te|het))*[\s,.;:]*$", "", v)
    if re.fullmatch(r"(?:I{1,3}|IV|V|VI{1,3}|IX|X)\. ?\S+", v) and re.search(r"(?:^|\n|[.:;)]\s*)$", text[max(0, s - 3):s]):
        return None  # "I. Verlenging", "V. Hierdoor": a Roman-numbered heading, not an initial
    words = [w.strip(".,") for w in v.split()]
    if not v or any(w in NOT_NAMES for w in words) or words[-1] in STOP:
        return None
    return s, s + len(v)


def find_names(text, known=()):
    out = []
    for rx, why, sc in ((TITLED_RE, "after a title (dhr., mevr., mr. ...)", 0.85),
                        (INITIALS_RE, "initials + surname", 0.75),
                        (SIGN_RE, "under a closing (met vriendelijke groet ...)", 0.8)):
        for m in rx.finditer(text):
            r = _clean_name(text, m.start(1), m.end(1))
            if r:
                out.append(Span("PERSON", r[0], r[1], sc, "nl_name_rules", why))
    for m in ROLE_RE.finditer(text):
        v = m.group(1)
        if re.match(rf"[{UP}]", v) and len(v.split()) <= 6 and not any(w in NOT_NAMES for w in v.split()) \
                and not re.search(r"\d", v):
            out.append(Span("PERSON", m.start(1), m.end(1), 0.8, "nl_name_rules", "form field (naam:, eiser: ...)"))
    # repeats: a surname found once is masked everywhere it reappears ("Van der Berg" after "J.P. van der Berg"),
    # and points back at the full name so both get the same placeholder
    surnames = {k: k for k in known}
    tail = re.compile(rf"(?:{TUSSEN}\s)*{NAMEWORD}$", re.I)
    for sp in out:
        full = text[sp.start:sp.end]
        m = tail.search(full)
        if m and len(m.group().split()[-1]) >= 3 and m.group().split()[-1] not in STOP | REPEAT_STOP:
            surnames.setdefault(m.group(), full)
    for name, full in surnames.items():
        rx = re.escape(name).replace(r"\ ", r"\s+")
        for m in re.finditer(rf"(?<![\w-]){rx}(?![\w-])", text, re.I):
            if not text[m.start()].isupper() and not text[m.end() - 1].isupper() and not m.group()[-1].isalpha():
                continue
            if not m.group().split()[-1][0].isupper():
                continue  # "berg" in lower case is a word, not the name
            sp = Span("PERSON", m.start(), m.end(), 0.7, "nl_name_repeat", "name seen elsewhere in the document")
            sp.ref = full
            out.append(sp)
    return out


# ---------------------------------------------------------------- keep readable

KEEP_RES = [
    re.compile(r"\bECLI:[A-Z]{2}:[A-Z0-9]{1,7}:\d{4}:[A-Z0-9.]{1,25}"),
    re.compile(r"(?i)\b(?:zaaknummer|zaak-?nr\.?|rolnummer|rolnr\.?|kenmerk|parketnummer|registratienummer|case number)\s*[:.]?\s*[\w/ .-]{3,40}"),
    re.compile(r"\b[A-Z]{1,3}/\d{2}/\d{3,7}(?:\s?/\s?[A-Z]{2}\s?[A-Z]{2}\s?\d{2}[-/]\d{1,5})?"),  # C/13/123456 / HA ZA 23-123
    re.compile(r"\b\d{3}\.\d{3}\.\d{3}(?:/\d{2})?\b(?=\s*(?:\(|$|\n|,))"),  # 200.123.456/01 (hof)
    re.compile(r"(?i)\b(?:art(?:ikel|\.)?)\s*\d+[a-z]?(?::\d+[a-z]?)?(?:\s+lid\s+\d+)?(?:\s+(?:sub|onder)\s+[a-z0-9]+)?"),
    re.compile(r"\bBWBR\d{7}\b"),
    re.compile(r"\b(?:Stb|Stcrt|Trb)\.\s?\d{4}[,/ -]\s?\d+"),
]


def keep_ranges(text):
    return [(m.start(), m.end()) for rx in KEEP_RES for m in rx.finditer(text)]


# ---------------------------------------------------------------- main entry

ENTITIES = ("BSN", "IBAN", "POSTCODE", "HOUSE_NUMBER", "ADDRESS", "PHONE", "EMAIL", "PLATE", "ID_DOCUMENT", "V_NUMBER",
            "VAT_ID", "KVK", "RSIN", "BIRTH_DATE", "PERSON")
# priority when spans overlap: checksummed ids beat shapes, shapes beat names
PRIORITY = {"BSN": 10, "IBAN": 10, "VAT_ID": 9, "RSIN": 9, "EMAIL": 9, "V_NUMBER": 8, "ID_DOCUMENT": 8, "PHONE": 7,
            "PLATE": 7, "KVK": 6, "BIRTH_DATE": 6, "POSTCODE": 5, "ADDRESS": 5, "HOUSE_NUMBER": 5, "PERSON": 4}
FLAG_ONLY = {"KVK", "RSIN"}  # business numbers: shown for review, not masked unless the user turns them on


def detect(text, threshold=0.5, entities=None, extra=(), address_detail="street", mask_terms=(), allow_terms=()):
    """extra: spans from an on-device model (GLiNER, RobBERT NER) as (start, end, score[, type])."""
    ents = set(entities or ENTITIES)
    spans = (find_bsn(text) + find_iban(text) + find_address(text, address_detail) + find_phone(text)
             + find_email(text) + find_plate(text) + find_documents(text) + find_business(text)
             + find_birth_dates(text))
    names = find_names(text)
    for x in extra:
        typ = x[3] if len(x) > 3 and x[3] else "PERSON"
        names.append(Span(typ, x[0], x[1], float(x[2]), "model", "on-device model"))
    for term in mask_terms:
        for m in re.finditer(rf"(?<![\w]){re.escape(term)}(?![\w])", text, re.I):
            names.append(Span("PERSON", m.start(), m.end(), 0.99, "local_dictionary", "term in the local dictionary"))
    spans += names
    allow = {t.strip().lower() for t in allow_terms if t.strip()}
    keep = keep_ranges(text)

    def protected(sp):
        if sp.entity_type in ("BSN", "IBAN", "EMAIL") and sp.score >= 0.9:
            return False  # a checksummed id with a cue wins even inside a "kenmerk:" line
        return any(a <= sp.start and sp.end <= b for a, b in keep)

    spans = [s for s in spans if s.entity_type in ents and s.score >= threshold and not protected(s)
             and text[s.start:s.end].strip().lower() not in allow]
    spans.sort(key=lambda s: (-PRIORITY.get(s.entity_type, 0), -s.score, -(s.end - s.start)))
    taken, chosen = [], []
    for s in spans:
        if any(not (s.end <= a or s.start >= b) for a, b in taken):
            continue
        taken.append((s.start, s.end))
        chosen.append(s)
    chosen.sort(key=lambda s: s.start)
    return [{"id": f"s{i:04d}", "entity_type": s.entity_type, "start": s.start, "end": s.end,
             "text": text[s.start:s.end], "score": round(s.score, 3), "recognizer": s.recognizer,
             "explanation": s.explanation, "flag_only": s.entity_type in FLAG_ONLY, "ref": s.ref}
            for i, s in enumerate(chosen)]
