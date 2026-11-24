"""EU personal-data rules (GDPR) for the "eu" profile, on top of the Turkish (KVKK) engine.

Standard library only. Adds what the Turkish rules don't know: national ID numbers of EU countries (each checked
with its own checksum), EU VAT ids, IBANs of every SEPA country, phone numbers with EU country codes, passport and
ID-card numbers after a cue, dates of birth after a cue in six languages, street addresses written the European
way, and non-Turkish names (after a title such as Herr, Mme, Sig., Sra., dhr.; in a form field; under a closing
such as "Kind regards"; or starting with a common European first name).

National IDs (all checksummed):
  NL BSN (11-proef), DE Steuer-ID (ISO 7064 MOD 11,10 + digit rule), FR NIR (mod 97 key), IT codice fiscale
  (check letter), ES DNI / NIE (mod 23 letter), BE national number (mod 97, before and after 2000), PL PESEL.
A number after an ID cue whose checksum fails (a typo, an OCR slip) is still masked: fail closed.

What this does not do: licence plates, national formats of phone numbers without a cue, addresses without a
street word (a bare "10115 Berlin" stays readable), names that have no title, cue, closing or known first name.
The guarantee is the same as for KVKK: every value that is detected is masked and checked before the text leaves
the computer. Values that are not detected are not covered.
"""
from __future__ import annotations

import os
import re

# ---------------------------------------------------------------- labels

LABELS_TR = {"NATIONAL_ID": "Ulusal Kimlik No", "VAT_ID": "KDV/VAT No", "ID_DOCUMENT": "Kimlik Belgesi No"}
LABELS_EN = {"NATIONAL_ID": "National ID", "VAT_ID": "VAT ID", "ID_DOCUMENT": "ID Document No",
             "PERSON": "Name", "ADDRESS": "Address", "PHONE": "Phone", "EMAIL": "E-mail", "IBAN": "IBAN",
             "BIRTH_DATE": "Date of Birth", "PASSPORT": "Passport No"}
# types this module adds to the engine's own
ENTITIES = ("NATIONAL_ID", "VAT_ID", "ID_DOCUMENT")
# types it can produce (engine types too); an id type wins an overlap with a name or an address
OWN = ("NATIONAL_ID", "VAT_ID", "ID_DOCUMENT", "PASSPORT", "IBAN", "PHONE", "BIRTH_DATE", "ADDRESS", "PERSON")
ID_TYPES = {"NATIONAL_ID", "VAT_ID", "ID_DOCUMENT", "PASSPORT", "IBAN", "TCKN", "YKN", "FOREIGN_ID", "PHONE",
            "EMAIL", "CREDIT_CARD", "VKN"}


def _span(typ, a, b, text, score, rec, why=""):
    return {"entity_type": typ, "start": a, "end": b, "text": text[a:b], "score": score,
            "recognizer": rec, "explanation": why}


def _digits(s):
    return re.sub(r"\D", "", s)


def _before(text, a, n=40):
    return text[max(0, a - n):a].lower()


# ---------------------------------------------------------------- checksums

def bsn_valid(s: str) -> bool:
    """NL BSN, 11-proef: digits weighted 9..2 and -1, sum divisible by 11."""
    d = _digits(s)
    if len(d) == 8:
        d = "0" + d
    if len(d) != 9 or d == "0" * 9:
        return False
    return (sum(int(c) * w for c, w in zip(d, (9, 8, 7, 6, 5, 4, 3, 2, -1)))) % 11 == 0


def steuer_id_valid(s: str) -> bool:
    """DE Steuerliche Identifikationsnummer: 11 digits, no leading 0, ISO 7064 MOD 11,10 check digit, and in the
    first ten digits exactly one digit appears twice or three times while at least one digit is missing."""
    d = _digits(s)
    if len(d) != 11 or d[0] == "0":
        return False
    counts = [d[:10].count(c) for c in set(d[:10])]
    if not (sorted(counts, reverse=True)[0] in (2, 3) and sum(1 for c in counts if c > 1) == 1):
        return False
    if re.search(r"(\d)\1\1", d[:10]):
        return False  # a digit may not appear three times in a row
    product = 10
    for c in d[:10]:
        s_ = (int(c) + product) % 10 or 10
        product = (s_ * 2) % 11
    check = (11 - product) % 10
    return check == int(d[10])


def nir_valid(s: str) -> bool:
    """FR numéro de sécurité sociale: 13 characters + 2-digit key = 97 - (number mod 97); Corsica 2A/2B."""
    s = re.sub(r"[\s.]", "", s).upper()
    if not re.fullmatch(r"[1-478]\d{4}(?:\d{2}|2A|2B)\d{6}\d{2}", s):
        return False
    body = s[:13].replace("2A", "19").replace("2B", "18")
    return 97 - int(body) % 97 == int(s[13:])


_CF_ODD = dict(zip("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                   [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8,
                    12, 14, 16, 10, 22, 25, 24, 23]))


def cf_valid(s: str) -> bool:
    """IT codice fiscale: 16 characters, the last one a check letter over odd/even position tables."""
    s = s.upper()
    if not re.fullmatch(r"[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]", s):
        return False
    total = 0
    for i, c in enumerate(s[:15]):
        total += _CF_ODD[c] if i % 2 == 0 else (int(c) if c.isdigit() else ord(c) - 65)
    return chr(65 + total % 26) == s[15]


_DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"


def dni_valid(s: str) -> bool:
    """ES DNI (8 digits + letter) or NIE (X/Y/Z + 7 digits + letter): letter = table[number mod 23]."""
    s = re.sub(r"[\s.-]", "", s).upper()
    m = re.fullmatch(r"([XYZ]?)(\d{7,8})([A-Z])", s)
    if not m or (m.group(1) and len(m.group(2)) != 7) or (not m.group(1) and len(m.group(2)) != 8):
        return False
    n = int("XYZ".index(m.group(1)).__str__() + m.group(2)) if m.group(1) else int(m.group(2))
    return _DNI_LETTERS[n % 23] == m.group(3)


def be_nn_valid(s: str) -> bool:
    """BE rijksregisternummer / numéro national: 9 digits + check = 97 - (n mod 97); born 2000+ prefix 2."""
    d = _digits(s)
    if len(d) != 11:
        return False
    body, check = int(d[:9]), int(d[9:])
    return 97 - body % 97 == check or 97 - int("2" + d[:9]) % 97 == check


def hetu_valid(s: str) -> bool:
    """FI henkilötunnus DDMMYY[-+A-FU-Y]NNNC: check character = table[DDMMYYNNN mod 31]."""
    m = re.fullmatch(r"(\d{6})[-+A-FU-Y](\d{3})([0-9A-Y])", s.upper())
    return bool(m) and "0123456789ABCDEFHJKLMNPRSTUVWXY"[int(m.group(1) + m.group(2)) % 31] == m.group(3)


def nss_es_valid(s: str) -> bool:
    """ES número de la Seguridad Social: 12 digits, the last two = first ten mod 97."""
    d = _digits(s)
    return len(d) == 12 and int(d[:10]) % 97 == int(d[10:])


def rvnr_shape(s: str) -> bool:
    """DE Rentenversicherungsnummer: area 2 digits, birth date DDMMYY, initial letter, serial 2 digits, check digit."""
    m = re.fullmatch(r"(\d{2})\s?(\d{2})(\d{2})(\d{2})\s?([A-Z])\s?(\d{3})", s.upper())
    return bool(m) and 1 <= int(m.group(2)) <= 31 and 1 <= int(m.group(3)) <= 12


def pesel_valid(s: str) -> bool:
    d = _digits(s)
    if len(d) != 11:
        return False
    total = sum(int(c) * w for c, w in zip(d, (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)))
    month = int(d[2:4]) % 20
    return (10 - total % 10) % 10 == int(d[10]) and 1 <= month <= 12


# SEPA countries and their IBAN lengths
IBAN_LEN = {"AD": 24, "AT": 20, "BE": 16, "BG": 22, "CH": 21, "CY": 28, "CZ": 24, "DE": 22, "DK": 18, "EE": 20,
            "ES": 24, "FI": 18, "FR": 27, "GB": 22, "GI": 23, "GR": 27, "HR": 21, "HU": 28, "IE": 22, "IS": 26,
            "IT": 27, "LI": 21, "LT": 20, "LU": 20, "LV": 21, "MC": 27, "MT": 31, "NL": 18, "NO": 15, "PL": 28,
            "PT": 25, "RO": 24, "SE": 24, "SI": 19, "SK": 24, "SM": 27, "VA": 22, "TR": 26}


def iban_valid(s: str) -> bool:
    s = re.sub(r"\s", "", s).upper()
    if IBAN_LEN.get(s[:2]) != len(s) or not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", s):
        return False
    return int("".join(str(int(c, 36)) for c in s[4:] + s[:4])) % 97 == 1


# ---------------------------------------------------------------- national ids

# cue words, lower case, in the languages of the countries covered
ID_CUES = ("bsn", "burgerservicenummer", "sofinummer", "steuer-id", "steuerid", "steuer-idnr", "steuerliche identifikationsnummer",
           "identifikationsnummer", "idnr", "steuer-identifikationsnummer", "sécurité sociale", "securite sociale",
           "nir", "n° ss", "insee", "codice fiscale", "cod. fisc", "c.f.", "dni", "nie", "nif", "rijksregisternummer",
           "rijksregister", "registre national", "numéro national", "national number", "niss", "insz", "pesel",
           "national id", "national identification", "personal number", "personal id", "personnummer",
           "social security", "ssn", "tax id", "tin", "id number", "identity number", "citizen service number",
           "henkilötunnus", "hetu", "personal identity code", "rentenversicherungsnummer", "sozialversicherungsnummer",
           "rv-nr", "seguridad social", "nss", "naf", "steuernummer", "tc kimlik", "kimlik no", "yabancı kimlik",
           "cnp", "cod numeric personal", "isikukood", "egn", "егн", "oib", "ppsn", "pps number", "amka", "αμκα", "afm",
           "αφμ", "krankenversicherungsnummer", "versichertennummer", "kvnr", "tessera sanitaria", "codice sanitario",
           "rodné číslo", "rodne cislo", "emšo", "emso", "asmens kodas", "personas kods", "henkilötunnus",
           "sozialversicherung", "svnr", "personnummer", "cpr", "cpr-nr", "fødselsnummer", "nif", "niss", "cc n.º",
           "cartão de cidadão", "numéro fiscal", "steuer-nr")

_ID_RES = [
    # BE first: its dotted form is distinctive (85.07.30-033.28)
    ("be", re.compile(r"(?<![\w.])(\d{2}\.\d{2}\.\d{2}[-\s]?\d{3}\.\d{2})(?![\w])"), be_nn_valid),
    ("nir", re.compile(r"(?<![\w])(?<!\d[\s.])([1-478][\s.]?\d{2}[\s.]?\d{2}[\s.]?(?:\d{2}|2[AB])[\s.]?\d{3}[\s.]?\d{3}[\s.]?\d{2})(?![\w])(?![\s.]\d)"),
     nir_valid),
    ("cf", re.compile(r"(?<![\w])([A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z])(?![\w])",
                      re.I), cf_valid),
    ("dni", re.compile(r"(?<![\w])((?:[XYZ][-\s]?\d{7}|\d{8})[-\s]?[A-Z])(?![\w])"), dni_valid),
    ("steuer", re.compile(r"(?<![\w.])(?<!\d\s)([1-9]\d[\s]?\d{3}[\s]?\d{3}[\s]?\d{3}|[1-9]\d{10})(?![\w])(?![\s.]\d)"), steuer_id_valid),
    ("pesel", re.compile(r"(?<![\w.])(\d{11})(?![\w])"), pesel_valid),
    ("hetu", re.compile(r"(?<![\w-])(\d{6}[-+A][0-9]{3}[0-9A-Y])(?![\w])"), hetu_valid),
    ("rvnr", re.compile(r"(?<![\w])(\d{2}\s?\d{6}\s?[A-Z]\s?\d{3})(?![\w])"), rvnr_shape),
    ("nss", re.compile(r"(?<![\w])(\d{2}[\s/]?\d{8}[\s/]?\d{2})(?![\w])"), nss_es_valid),
    ("bsn", re.compile(r"(?<![\w./-])(?<!\d\s)(\d{4}\.\d{2}\.\d{3}|\d{3}[.\s]\d{3}[.\s]\d{3}|\d{9})(?![\w/-]|[.\s]\d)"), bsn_valid),
]
# a number right after an ID cue: masked even when no checksum fits (fail closed)
_CUED = re.compile(r"(?i)\b(?:" + "|".join(re.escape(c) for c in sorted(ID_CUES, key=len, reverse=True)) +
                   r")(?!\w)[^\d\n]{0,30}?"
                   r"(?-i:((?=[A-Z0-9 ./-]{6,24}(?![\w]))(?<![\w])[A-Z0-9](?:[ ./-]?[A-Z0-9]){5,19}))(?![\w])")


def find_national_ids(text):
    out, taken = [], []
    for name, rx, ok in _ID_RES:
        for m in rx.finditer(text):
            a, b = m.span(1)
            if any(x < b and a < y for x, y in taken):
                continue
            cue = any(c in _before(text, a) for c in ID_CUES)
            if name in ("bsn", "pesel") and not cue:  # "needs the BSN of Dirk\n[18:05] Charlotte: it's 273849153"
                cue = any(re.search(rf"\b{re.escape(c)}\b", _before(text, a, 120)) for c in ("bsn", "pesel", "burgerservicenummer"))
            if name == "bsn" and len(_digits(m.group(1))) == 9 and not cue and not re.search(r"[.\s]", m.group(1)):
                # a bare 9-digit number passes the 11-proef one time in 11: only with a cue
                continue
            if name == "pesel" and not cue:
                continue  # 11 bare digits: PESEL's checksum passes one time in 10
            if ok(m.group(1)):
                out.append(_span("NATIONAL_ID", a, b, text, 0.95 if cue else 0.85, f"eu_{name}", f"{name} checksum ok"))
                taken.append((a, b))
    for m in _CUED.finditer(text):
        a, b = m.span(1)
        if any(x < b and a < y for x, y in taken) or not re.search(r"\d", m.group(1)):
            continue
        if re.fullmatch(r"[ABCDEFGHJNPQRSUVW]-?\d{7}-?[0-9A-J]", m.group(1)):
            continue  # a Spanish company tax number (CIF), not a person's
        out.append(_span("NATIONAL_ID", a, b, text, 0.7, "eu_id_cue", "number after an ID cue (no checksum fits)"))
        taken.append((a, b))
    return out


# ---------------------------------------------------------------- VAT ids

VAT_SHAPES = {"AT": r"U\d{8}", "BE": r"[01]\d{9}", "BG": r"\d{9,10}", "CY": r"\d{8}[A-Z]", "CZ": r"\d{8,10}",
              "DE": r"\d{9}", "DK": r"\d{8}", "EE": r"\d{9}", "EL": r"\d{9}", "ES": r"[A-Z0-9]\d{7}[A-Z0-9]",
              "FI": r"\d{8}", "FR": r"[A-HJ-NP-Z0-9]{2}\d{9}", "HR": r"\d{11}", "HU": r"\d{8}",
              "IE": r"\d{7}[A-W][A-I]?|\d[A-Z+*]\d{5}[A-W]", "IT": r"\d{11}", "LT": r"\d{9}|\d{12}", "LU": r"\d{8}",
              "LV": r"\d{11}", "MT": r"\d{8}", "NL": r"\d{9}B\d{2}", "PL": r"\d{10}", "PT": r"\d{9}",
              "RO": r"\d{2,10}", "SE": r"\d{12}", "SI": r"\d{8}", "SK": r"\d{10}", "XI": r"\d{9}|\d{12}"}
_VAT = re.compile(r"(?<![\w])(" + "|".join(VAT_SHAPES) + r")[\s.-]?([A-Z0-9](?:[\s.]?[A-Z0-9+*]){6,13})(?![\w])")


def find_vat(text):
    out = []
    for m in _VAT.finditer(text):
        body = re.sub(r"[\s.]", "", m.group(2))
        if re.fullmatch(VAT_SHAPES[m.group(1)], body) and re.search(r"\d{6}", body):
            if m.group(1) + body[:2] in IBAN_LEN and iban_valid(m.group(0)):
                continue
            out.append(_span("VAT_ID", m.start(), m.end(), text, 0.85, "eu_vat", f"{m.group(1)} VAT id shape"))
    return out


# ---------------------------------------------------------------- IBAN, phone, documents, birth dates

_IBAN = re.compile(r"(?<![\w])([A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30})(?![\w])")


def find_iban(text):
    out = []
    for m in _IBAN.finditer(text):
        parts = re.split(r"( )", m.group(1))
        for k in range(len(parts), 0, -2):  # longest prefix that is a valid IBAN (text may follow)
            c = "".join(parts[:k])
            if iban_valid(c):
                out.append(_span("IBAN", m.start(1), m.start(1) + len(c), text, 0.97, "eu_iban", "IBAN mod-97 ok"))
                break
    return out


# +31 / +49 / 0049 ... every country code from +30 to +49 and +350 to +389, +420 to +423
_PHONE_INTL = re.compile(r"(?<![\w+])((?:\+|00)(?:3[0-469]|3[5-8]\d|4[0-13-9]|42[0-3])[\s./-]?(?:\(0\)[\s./-]?)?"
                         r"\(?\d{1,4}\)?(?:[\s./-]?\d){5,11})(?![\w])")
_PHONE_CUE = re.compile(r"(?i)\b(?:tel|tél|telefon|telephone|téléphone|telefono|teléfono|telefoon|phone|mobile|mobil|"
                        r"handy|portable|cellulare|cell|móvil|movil|gsm|fax|mob)\b\.?\s*(?:\([^)]{1,12}\)\s*)?[:.]?\s*"
                        r"(0\d(?:[\s./-]?\(?\d\)?){6,12})(?![\w])")


_PHONE_NATIONAL = re.compile(
    r"(?<![\w+/.-])("
    r"0[1-9](?:[ .]\d{2}){4}"                       # FR 02 98 44 71 20
    r"|06[- ]?\d{8}|06(?:[ -]\d{2}){4}"            # NL mobile 06-41837265
    r"|01[5-7]\d[ /-]?\d{6,8}"                     # DE mobile 0171/2293847
    r"|3[2-9]\d[ ]?\d{6,7}"                        # IT mobile 347 2210983
    r"|0\d{1,4}[ /-]\d{2,4}[ -]?\d{3,5}(?=\s*(?:$|\n|[,;)]|–|-\s))"  # landline at the end of a contact line
    r"|0\d{1,4}(?:[ /-]\d{2,6}){1,4}"              # grouped national numbers: 0475 12 84 56, 087 412 9930, 07700 900418
    r"|[67]\d{2}(?: \d{2}){3}|[5-8]\d{2} \d{3} \d{3}|3\d{2} \d{3} \d{4}"  # ES 612 48 39 07, PL 512 384 907, IT 347 218 9043
    r"|\d{2}(?: \d{2}){3}(?=\s*,\s*[\w.+-]+@)"       # DK 28 41 77 30, then an e-mail
    r")(?![\w/-])(?!\.\w)")


def find_phones(text):
    out = [_span("PHONE", *m.span(1), text, 0.9, "eu_phone", "international number") for m in _PHONE_INTL.finditer(text)]
    out += [_span("PHONE", *m.span(1), text, 0.85, "eu_phone_cue", "number after a phone cue")
            for m in _PHONE_CUE.finditer(text)]
    for m in _PHONE_NATIONAL.finditer(text):
        n = len(re.sub(r"\D", "", m.group(1)))
        if re.search(r"(?:^|\D)(?:19|20)\d{2}(?:\D|$)", m.group(1)) and re.search(r"\d[-./]\d", m.group(1)):
            continue  # "03-11-2026 21:20": a date, not a number
        if not 8 <= n <= 12 or re.search(r"(?i)(?:€|eur|euro|tl|try|usd|gbp|chf|pln|dkk|sek|£|\$|§|art\.?|iban|kvk|kbo|"
                                          r"btw|vat|rsin|krs|regon|nip|cvr|siren|siret|cg|fn|hrb?|rcs|cif|n°|nº)\s*[:.]?\s*$",
                                          text[max(0, m.start() - 12):m.start()]) or \
                re.search(r"(?i)\b(?:RCS|registre|register|registry|Firmenbuch|Handelsregister|Cg)\b[^\n\d]{0,25}$",
                          text[max(0, m.start() - 40):m.start()]):
            continue
        if re.match(r"(?:19|20)\d{2}\b", m.group(1)) or re.search(r"(?i)(?:az\.|aktenzeichen|case|no\.|nr\.|r\.?g\.?)\s*$",
                                                                   text[max(0, m.start() - 20):m.start()]):
            continue
        out.append(_span("PHONE", *m.span(1), text, 0.75, "eu_phone_national", "national phone format"))
    return out


_DOC = re.compile(
    r"(?i)\b(passport|reisepass|pass(?:nummer|-nr|\s?nr\.?)|paspoortnummer|paspoort\s?nr\.?|passeport|passaporto|pasaporte|paspoort|paszport|"
    r"personalausweis|perso-?\s?nr\.?|ausweis(?:nummer)?|carte d'identité|carte nationale d'identité|cni|carta d'identità|"
    r"documento de identidad|identiteitskaart|id-kaart|dowód osobisty|identity card|id card|driving licen[cs]e|"
    r"driver's license|führerschein|permis de conduire|patente|permiso de conducir|rijbewijs|document number|"
    r"residence permit|aufenthaltstitel|titre de séjour|verblijfsvergunning|documentnummer|pasaport|kimlik kartı|"
    r"ehliyet|oturma izni|passport copies)(?!\w)[^\d\n]{0,25}?(?-i:(?<![\w])([A-Z0-9](?:[ -]?[A-Z0-9]){5,13}))(?![\w])")


def find_documents(text):
    out = []
    for m in _DOC.finditer(text):
        if not re.search(r"\d", m.group(2)) or not re.search(r"[A-Z]|\d{6}", m.group(2)) and len(_digits(m.group(2))) < 6:
            continue
        typ = "PASSPORT" if re.match(r"(?i)pas|reisepass", m.group(1)) else "ID_DOCUMENT"
        out.append(_span(typ, *m.span(2), text, 0.9, "eu_document", f"number after '{m.group(1)}'"))
    return out


MONTHS = ("january|february|march|april|may|june|july|august|september|october|november|december|"
          "januar|jänner|februar|märz|mai|juni|juli|oktober|dezember|"
          "janvier|février|fevrier|mars|avril|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre|"
          "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|dicembre|"
          "enero|febrero|abril|mayo|junio|julio|septiembre|octubre|noviembre|diciembre|"
          "januari|februari|maart|mei|augustus|stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|"
          "września|października|listopada|grudnia")
_MON_SHORT = "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|okt|nov|dec|dez"
_DATE = rf"(?:(?:the\s)?\d{{1,2}}(?:st|nd|rd|th)?\s(?:of\s)?(?:{MONTHS}|(?:{_MON_SHORT})\.?),?\s(?:19|20)\d{{2}}|\d{{1,2}}[./-]\d{{1,2}}[./-](?:19|20)?\d{{2}}|(?:19|20)\d{{2}}-\d{{2}}-\d{{2}}|\d{{1,2}}(?:er|º)?\.? (?:de )?(?:{MONTHS}) (?:de )?(?:19|20)\d{{2}}|(?:{MONTHS}) \d{{1,2}},? (?:19|20)\d{{2}})"
_DOB = re.compile(r"(?i)\b(?:born(?: on)?|date of birth|d\.?o\.?b\.?|birth ?date|geboren(?: am)?|geb\.|geburtsdatum|"
                  r"née? le|né\(e\) le|née?|date de naissance|nato il|nata il|nato a \w+ il|nata a \w+ il|"
                  r"data di nascita|nacid[oa] el|nacid[oa] en \w+ el|fecha de nacimiento|geboortedatum|"
                  r"nací el|nací en \w+ el|urodzon[ya]|urodził(?:em|am|a)? się|ur\.|data urodzenia|född|født|fødselsdato|födelsedatum|syntymäaika|doğum tarihi)(?!\w)[^\w\n]{0,4}"
                  r"(?:(?:te|in|à|a|en|w|zu)\s+[A-ZÀ-ÞŁŚŻ][\w'’-]+(?:[ -][A-ZÀ-Þ][\w'’-]+)?,?\s+)?"
                  r"(?:(?:on|am|op|le|il|el|en|den)\s+)?(" + _DATE + r")", re.I)


# "der am 11.02.1949 in Kayseri geborene", "11.02.1949 Kayseri doğumlu", "nato a Prato il ..." (date first)
_DOB_BEFORE = re.compile(r"(?i)(?:\bam\s+)?(" + _DATE + r")[ \t]+(?:in[ \t]+)?(?:[A-ZÀ-ÞÇĞİÖŞÜ][\w'’-]+[ \t,]*(?:\([^)]{1,25}\)[ \t]*)?){0,3}"
                         r"\b(?:geboren(?:e[nrs]?)?|doğumlu|born|né(?:e)?|nat[oa]|nacid[oa])\b")


def find_birth_dates(text):
    return [_span("BIRTH_DATE", *m.span(1), text, 0.9, "eu_birth_date", "date after a birth cue")
            for m in _DOB.finditer(text)] + \
        [_span("BIRTH_DATE", *m.span(1), text, 0.85, "eu_birth_date", "date before a birth word (geboren, doğumlu)")
         for m in _DOB_BEFORE.finditer(text)]


# ---------------------------------------------------------------- addresses

_W = r"[^\W\d_][\w'’.-]*"  # a word (letters first)
_STREET = re.compile(
    "|".join([
        # DE / AT / CH / NL compounds: Hauptstraße 5, Keizersgracht 123-III, Am Markt 3
        rf"(?:\b(?:[A-ZÄÖÜ][\w'’-]*(?:er|e|en)\s)?[A-ZÄÖÜ][\w'’-]*(?:straße|strasse|str\.|weg|platz|allee|gasse|ring|damm|ufer|chaussee|steig|"
        rf"straat|laan|gracht|plein|kade|singel|dijk|steeg|haven|hof|markt|pad|wal|dreef|baan|veld|erf|plantsoen|park))\s+\d{{1,4}}(?:\s?[a-zA-Z]\b|-\w{{1,4}})?",
        # DE / AT separate word: Venloer Straße 389, Schweizer Str. 77; Nordic: Vasagatan 41, Strandvejen 5
        rf"\b(?:[A-ZÄÖÜ][\w'’-]+\s){{1,2}}(?:Straße|Strasse|Str\.|Weg|Platz|Allee|Gasse|Ring|Damm)\s+\d{{1,4}}"
        rf"(?:\s?[a-zA-Z]\b|-\d{{1,4}})?",
        rf"\b[A-ZÅÄÖØÆ][\w'’-]*(?:gatan|vägen|gränd|torget|gade|vej|veien|gata|katu|tie|kuja)\s+\d{{1,4}}(?:\s?[A-Za-z]\b)?",
        # PL: ul. Marszałkowska 12/4; NL: Laan van Meerdervoort 210
        rf"\b(?:ul\.|al\.|pl\.|os\.)\s?[A-ZŁŚŻŹĆ][\w'’-]+(?:\s[A-ZŁŚŻŹĆ][\w'’-]+)?\s+\d{{1,4}}(?:/\d{{1,4}})?[a-zA-Z]?",
        rf"\bLaan van [A-Z][\w'’-]+\s+\d{{1,4}}[a-zA-Z]?",
        rf"\b(?:Strada|Bulevardul|Calea|Ulica)\s+[A-ZȘȚĂÂÎ][\w'’-]+(?:\s[A-ZȘȚĂÂÎ][\w'’-]+)?\s+(?:nr\.\s?)?\d{{1,4}}",
        # DE: Am Rosengarten 5, An der Alster 12, Im Tal 3
        rf"\b(?:Am|An der|An den|Im|In der|Auf der|Auf dem|Zum|Zur|Unter den|Hinter der)\s+[A-ZÄÖÜ][\w'’-]+\s+\d{{1,4}}"
        rf"(?:\s?[a-zA-Z]\b)?",
        # IT / ES / PT / CA: Via Roma 12, Calle Mayor, 5; Avenida da Liberdade 110
        rf"\b(?:Via|Viale|Piazza|Piazzale|Corso|Largo|Vicolo|Calle|C/|Avenida|Avda\.|Plaza|Paseo|Carrer|Rua|"
        rf"Travessa|Ronda|Camino)\s+(?:{_W}\s+){{0,4}}?{_W},?\s+(?:n\.?\s?|nº\s?)?\d{{1,4}}(?:\s?[a-zA-Z]\b|/\w+)?",
        # HU: Andrássy út 52
        rf"\b[A-ZÁÉÍÓÖŐÚÜŰ][\w'’-]+\s(?:út|utca|u\.|tér|körút|krt\.)\s+\d{{1,4}}(?:/[A-Za-z0-9]+)?",
        # FR: 12 rue de la Paix, 5 bis avenue Foch
        rf"\b\d{{1,4}}(?:\s?(?:bis|ter|[a-z]\b))?,?\s+(?:rue|avenue|av\.|boulevard|bd|place|chemin|allée|allee|"
        rf"impasse|quai|cours|route|square|promenade|esplanade|résidence|lieu-dit)\s+(?:(?:de|du|des|la|le|l['’]|d['’])\s*)*[A-ZÀ-Þ][\w'’-]*"
        rf"(?:\s+(?:(?:de|du|des|la|le|l['’]|d['’])\s*)*[A-ZÀ-Þ][\w'’-]*){{0,3}}",
        # EN: 221B Baker Street, 10 Downing St.
        rf"(?:\b(?:Flat|Apt\.?|Apartment|Unit|Suite)\s+\d{{1,4}}[A-Za-z]?,?\s+)?\b\d{{1,4}}[A-Za-z]?,?\s+(?:[A-Z][\w'’-]*\s+){{1,3}}(?:Street|St\.|Road|Rd\.|Avenue|Ave\.|Lane|Drive|"
        rf"Close|Way|Place|Square|Crescent|Terrace|Gardens|Row|Mews|Hill|Park|Villas|Grove|Strand|Walk|Court|Rise|View|Green|"
        rf"Parade|Quay|Wharf|Embankment|Circus|Vale|Heights|Gate|Yard|Boulevard|Broadway|Promenade|Mansions|House|Hall|Lodge|"
        rf"Buildings|Cottages|Apartments|Tower)\b",
    ]))
# what may follow a street on the same line: a postcode and the town
_POSTCODE_TOWN = re.compile(r",?\s{1,3}(?:(?:[A-Z]{1,2}-)?(?:\d{5}|\d{4}-\d{3}|\d{4}\s?[A-Z]{2}|\d{6}|\d{3}\s\d{2}|\d{4}|\d{2}-\d{3}|[A-Z]{1,2}\d[A-Z\d]?\s\d[A-Z]{2}|[AC-FHKNPRTV-Y]\d[\dW]\s?[\dAC-FHKNPRTV-Y]{4})"
                            r"(?:\s+(?:['’][st][- ])?[A-ZÀ-Þ][\w'’-]+(?:[ \t-][A-ZÀ-Þ][\w'’-]+){0,2}(?:[ \t][A-ZØÆÅ](?![\w]))?)?"
                            # UK / IE: town first, then a district number or a postcode
                            r"|(?:['’][st][- ])?[A-ZÀ-Þ][a-zà-ÿ'’-]+(?:\s(?:\d{1,2}(?!\d)|[A-Z]{1,2}\d[A-Z\d]?\s\d[A-Z]{2}))?(?=[\s,.;)]|$))")


# "Molenstraat 18, 2513 BL", "Pembridge Villas 4, W11 3EP": a street-like run, a house number and a postcode
_PC_ANCHORED = re.compile(
    r"(?<![\w'’-])((?:[A-ZÀ-ÞØÆÅ][\w'’.-]+[ \t]){0,3}[A-ZÀ-ÞØÆÅ][\w'’.-]+[ \t]\d{1,4}(?:[ \t]?[A-Za-z]{1,2}\b|-\w{1,4}|/\w{1,4})?)"
    r",?[ \t\n]{1,3}(?=(?:\d{4}\s?(?!SA|SD|SS)[A-Z]{2}|[A-Z]{1,2}\d[A-Z\d]?\s\d[A-Z]{2}|[AC-FHKNPRTV-Y]\d[\dW]\s?[\dAC-FHKNPRTV-Y]{4})(?![\w]))")


# after the house number: door, floor and flat ("4/II/7", "214 bus 3", "14 m. 2", "44, 2. th.", "31 lgh 1102",
# "27, 3º B", "6, 2º izq.", "58, 2. OG links")
_UNIT = re.compile(r"(?:/[\wIVX]{1,4}){1,3}|,?[ \t](?:bus|bte|b|m\.|lgh|apt\.?|app\.?|st\.|whg\.?|top)[ \t]?\d{1,4}\w?"
                   r"|,?[ \t]\d{1,2}\.[ \t]?(?:th|tv|mf|sal|OG|Stock|Etage|et|ét|piętro|vån)\.?(?:[ \t](?:links|rechts|li\.|re\.|"
                   r"Mitte))?|,?[ \t]\d{1,2}[º°ª][ \t]?(?:[A-Z]\b|izq(?:da)?\.?|dcha\.?|dch\.?|int\.?)")
# a line holding only a postcode and a town, under a street line ("1050 Wien", "116 21 Stockholm", "D06 W2K7")
_PC_LINE = re.compile(r"[ \t]*,?[ \t]*\n[ \t]*((?:[A-Z]{1,2}-)?(?:\d{4,5}|\d{3}[ ]\d{2}|\d{2}-\d{3}|\d{4}[ ]?[A-Z]{2}|"
                      r"[A-Z]{1,2}\d[A-Z\d]?[ ]\d[A-Z]{2}|[AC-FHKNPRTV-Y]\d[\dW][ ]?[\dAC-FHKNPRTV-Y]{4})"
                      r"(?:[ \t]+(?:['’][st][- ])?[A-ZÀ-ÞØÆÅ][\w'’-]+(?:[ \t-](?:[A-ZÀ-ÞØÆÅ][\w'’-]*|im|am|an der|sur|upon)){0,3})?"
                      r"(?:,[ \t]*[A-ZÀ-Þ][\w'’-]+)?)[ \t]*,?[ \t]*(?=\n|$)")
# "Address: …", "wohnhaft …", "Domicilio: …": the rest of the line, and the address lines under it
_ADDR_CUE = re.compile(r"(?im)(?:\b(?:address(?: was)?|home address|residential address|adresse|anschrift|wohnhaft(?: in)?|"
                       r"wohnung|wonende te|woonachtig te|wohnort|demeurant(?: au| à)?|domicilié(?:e)? (?:au|à)|"
                       r"residente in|domicilio|domiciliad[oa] en|adres(?: zamieszkania)?|zamieszkał[ay]|zam\.|bosatt|"
                       r"bopæl)\b)[ \t]*[:,]?[ \t]*\n?[ \t]*(?=\S)")
_BE_STREET = re.compile(r"\b(?:Rue|Avenue|Chaussée|Boulevard|Place|Quai|Square|Drève|Clos)\s+(?:(?:de|du|des|la|le|l['’]|d['’])\s*)*"
                        r"[A-ZÀ-Þ][\w'’-]*(?:\s+(?:(?:de|du|des|la|le|l['’]|d['’])\s*)*[A-ZÀ-Þ][\w'’-]*){0,3}\s+\d{1,4}[a-zA-Z]?\b")


def _address_lines(text, b, max_lines=3):
    """Extend an address over the short address lines under it ("Orwell Road", "Rathgar, Dublin 6", "D06 W2K7")."""
    for _ in range(max_lines):
        m = re.match(r"[ \t]*,?[ \t]*\n[ \t]*([^\n:]{2,45}?)[ \t]*,?[ \t]*(?=\n|$)", text[b:])
        if not m:
            break
        line = m.group(1)
        pc = _PC_LINE.match(text, b)
        if pc:
            b = pc.end(1)
            continue
        if re.fullmatch(r"(?:[A-ZÀ-ÞØÆÅ][\w'’.-]*|of|de|la|le|van|von|the|\d{1,4}\w?)(?:[ ,]+(?:[A-ZÀ-ÞØÆÅ][\w'’.-]*|\d{1,3}|"
                        r"of|de|la|le|van|von|the))*", line) and not re.search(r"(?i)\b(?:tel|phone|e-?mail|dob|born|"
                                                                               r"passport|ausweis|mobil)\b", line):
            b += m.end(1)
            continue
        break
    return b


# Company and office addresses stay readable; a sole trader's business address is his home address, so it is masked.
_SOLE_TRADER = re.compile(r"(?i)\b(?:e\.\s?K\.|e\.\s?Kfm|eenmanszaak|sole trader|trading as|t/a|einzelunternehm\w*|"
                          r"entreprise individuelle|auto-?entrepreneur|micro-?entrepreneur|ditta individuale|autónomo|"
                          r"şahıs şirketi|enkeltmandsvirksomhed|enskild firma)\b")
_OFFICE_WORDS = (r"(?:Advokatpartnerselskab|Advokatfirma|Advokatbyrå|Rechtsanwälte|Rechtsanwaltskanzlei|Anwaltskanzlei|"
                 r"Kanzlei|Notariat|Notariaat|Advocaten|Avocats|Studio Legale|Despacho|Abogados|Solicitors|Chambers|"
                 r"Hukuk Bürosu|Bank|Hospital|Krankenhaus|Universit\w+|Gericht|Rechtbank|Tribunal|Court|Ministry|Ministerium)")
_PERSONAL_CUE = re.compile(r"(?i)\b(?:wohnhaft|wohnt|wonende|woonachtig|domicili\w*|resident|residing|living at|lives at|"
                           r"demeurant|residente|bosatt|bor på|zam\.|zamieszka\w*|ikamet\w*|home|privat\w*|"
                           r"C\.F\.|codice fiscale|PESEL|DNI|NIE|BSN|NIF|geb\.|geboren|born|née?|nato|nata)(?![\w])")
_OFFICE_CUE = re.compile(r"(?i)(?:Amtssitz in [^,\n]{2,30}|kantoor (?:te|aan|houdende)|advoca(?:at|te|ten) te [^,\n]{2,30}|"
                         r"cabinet|studio in|office(?:s)? at|registered office|seat at|zetel|Sitz|Geschäftsadresse|"
                         r"siège social|sede legale|domicilio social|ticaret sicil\w*)[ \t,:]*$")


def _business_address(text, a):
    """True when the address at `a` belongs to a company or an office: it follows the company's name on the same
    line ("Fennor Capital DAC, 2 Grand Canal Square"), on the line above (a letterhead), or an office cue
    ("öffentliche Notarin mit dem Amtssitz in Wien, Wipplingerstraße 12")."""
    ls = text.rfind("\n", 0, a) + 1
    line = text[ls:a]
    if _PERSONAL_CUE.search(line) or _SOLE_TRADER.search(line):
        return False
    company = COMPANY_FORMS + r"\)?|" + _OFFICE_WORDS
    if re.search(r"(?:" + company + r")[ \t]*[,·|–-]?[ \t]*$", line) or \
            re.search(r"(?<![\w.])(?:SAS|SARL|SA|GmbH|AG|BV|NV|SpA|Srl|SL)(?:[ \t]+[A-ZÀ-Þ][\w'’-]*){1,4}[ \t]*,[ \t]*$", line):
        return True
    if _OFFICE_CUE.search(line):
        return True
    if not line.strip():  # letterhead: the line above is the company's name
        prev = text[text.rfind("\n", 0, max(ls - 1, 0)) + 1:max(ls - 1, 0)]
        if re.search(r"(?:" + company + r")[ \t]*$", prev) and not _SOLE_TRADER.search(prev) and len(prev) < 80:
            return True
    return False


def find_addresses(text):
    out = []
    for m in _ADDR_CUE.finditer(text):
        line = re.match(r"[^\n]{3,90}", text[m.end():])
        if not line:
            continue
        val = re.split(r"\s+[–—]\s+|;|,\s+(?=(?:verzoeker|verzoekster|ausgewiesen|geboren|born|tel|phone|nacid|"
                       r"nato|nata|née?|e-?mail|dni|nie|passport)\b)|\.\s+(?=[A-Z])", line.group(0), maxsplit=1)[0]
        pc = re.search(r"(?<![\w-])(?:\d{4,5}|\d{2}-\d{3}|\d{4}-\d{3}|\d{3} \d{2})(?:[ \t][A-Z]{2})?[ \t]+[A-ZÀ-Þ'][\w'’-]+", val)
        if pc and "," in val[pc.end():]:  # "Corso Vercelli 301, 10155 Torino, a comparire …": the address ends at the town
            val = val[:pc.end() + val[pc.end():].index(",")]
        val = val.rstrip(" ,.")
        a, b = m.end(), m.end() + len(val)
        if not (val[:1].isupper() or val[:1].isdigit()) or not re.search(r"\d", text[a:_address_lines(text, b)]) \
                or len(val) < 3 or "@" in val:
            continue
        b = _address_lines(text, b)
        out.append(_span("ADDRESS", a, b, text, 0.8, "eu_address_cue", "after an address word (Address:, wohnhaft, Domicilio:)"))
    for m in list(_STREET.finditer(text)) + list(_PC_ANCHORED.finditer(text)) + list(_BE_STREET.finditer(text)):
        a, b = m.span()
        u = _UNIT.match(text, b)
        if u:
            b = u.end()
        for _ in range(3):  # "Merrion Square, Dublin 2, D02 X285", "Schweizer Str. 77, 60594 Frankfurt am Main"
            t = _POSTCODE_TOWN.match(text, b)
            if not t or t.end() <= b:
                break
            b = t.end()
            am = re.match(r"\s(?:am|an der|im|sur|upon|bei)\s[A-ZÀ-Þ][\w'’-]+", text[b:])
            if am:
                b += am.end()
        b = _address_lines(text, b, 2) if _PC_LINE.match(text, b) else b
        c = re.match(r"[ \t]*/[ \t]*[A-ZÇĞİÖŞÜ]{3,}(?![\w])", text[b:])
        if c:  # "... 3074 AM Rotterdam / HOLLANDA" in a Turkish petition
            b += c.end()
        if _business_address(text, a):
            continue  # a company's or an office's address is public business data: kept readable (fikri, 24 Nov 2026)
        if any(o["start"] <= a and o["end"] >= b for o in out):
            continue
        out.append(_span("ADDRESS", a, b, text, 0.85, "eu_street", "street and house number"))
    return out


# ---------------------------------------------------------------- names

TITLES = ("Mr", "Mrs", "Ms", "Miss", "Mx", "Dr", "Prof", "Sir", "Dame", "Lord", "Lady", "Herr", "Herrn", "Frau", "Hr", "Fr",
          "M", "Mme", "Mlle", "MM", "Me", "Maître", "Sig", "Sig.ra", "Sig.na", "Sigg", "Dott", "Dott.ssa", "Avv",
          "Ing", "Sr", "Sra", "Srta", "D", "Dª", "Dña", "Don", "Doña", "dhr", "mevr", "mw", "Dhr", "Mevr", "Mw",
          "De heer", "Mevrouw", "Pan", "Pani", "mr", "Mag", "Dipl.-Ing", "RA", "RAin", "Rechtsanwalt", "Rechtsanwältin",
          "Notar", "Notarin", "pani", "pan", "Avocat", "Avocate", "Abogado", "Abogada", "Avvocato", "Advocaat", "Sayın", "Sn", "Bay",
          "Bayan", "Av", "Messrs", "Mgr", "Kyrios", "Kyria", "D.ª", "Dña.", "drs", "ir", "ing", "mr.", "mevrouw",
          "Herr Dr", "Frau Dr", "κ", "κα", "Κ", "Κα", "κύριος", "κυρία", "Κύριος", "Κυρία", "κ.κ")
_TITLE = re.compile(r"(?<![\w.])(?:" + "|".join(re.escape(t) for t in sorted(TITLES, key=len, reverse=True)) +
                    r")(?:\.|\b)\s+(?=[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ])")
PARTICLES = {"von", "van", "der", "den", "de", "del", "della", "degli", "di", "da", "dos", "das", "do", "du", "des",
             "la", "le", "y", "i", "zu", "ter", "ten", "af", "av", "bin", "al", "el", "'t", "op", "lo", "li"}
# capitalised words that are not names (sentence starts, legal words, months, closings, German nouns after a name)
NOT_NAMES = set("""The This That These Those A An And Or But If In On At For To Of By With From As Is Was Be Are Were
Dear Kind Best Regards Yours Sincerely Faithfully Thanks Thank Cordialement Bien Cordiali Distinti Saluti Atentamente
Saludos Mit Freundlichen Grüßen Viele Liebe Met Vriendelijke Groet Hoogachtend Pozdrawiam Poważaniem
Court Tribunal Gericht Landgericht Amtsgericht Oberlandesgericht Bundesgerichtshof Cour Corte Tribunale Juzgado Audiencia
Rechtbank Gerechtshof Sąd Article Artikel Art Article Articolo Artículo Regulation Directive Verordnung Richtlinie
Règlement Directive Regolamento Reglamento Verordening Richtlijn GDPR DSGVO RGPD AVG UE EU Union European Europe
Commission Council Parliament Board Authority Agency Ministry Ministerium Ministère Ministero Ministerio Ministerie
Company Limited Ltd GmbH AG SE SA SAS SARL SpA Srl SL BV NV Inc LLC Bank Group Holding
Klage Vertrag Antrag Urteil Beschluss Datum Kläger Klägerin Beklagte Beklagter Mandant Mandantin Partei Anlage
Plaintiff Defendant Claimant Respondent Applicant Appellant Witness Client Employee Employer Controller Processor
Demandeur Défendeur Requérant Attore Convenuto Ricorrente Demandante Demandado Eiser Gedaagde Verzoeker
Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September
October November December Januar Februar März Juni Juli Oktober Dezember
Street Road Avenue Lane Straße Strasse Platz Rue Via Calle Plaza
Raad Hoge Garante EuGH BGH Abs Art Paris Berlin Rome Roma Madrid Amsterdam Brussels Bruxelles Brussel Vienna Wien Lisbon Lisboa Warsaw Warszawa
Munich München Hamburg Frankfurt Cologne Köln Milan Milano Barcelona Lyon Marseille Rotterdam Antwerp Dublin London
Istanbul Ankara Izmir Turkey Türkiye Germany Deutschland France Italy Italia Spain España Netherlands Nederland Belgium
Poland Polska Austria Österreich Portugal Ireland Greece Sweden Denmark Finland
Ich Wir Sie Officer Protection Medical Claims Travel Present Signed Patient Exa Excelência Kollegin Kollege
Your Our Ihre Ihr Unsere Unser Die Der Das Le La Les Il Lo Gli El Los Las De Het Votre Notre Vostro Nostro Su Uw Ons
Anwalt Anwältin Rechtsanwalt Medien Ausgeschlossen Notaio Notario Notaire Domicilio Teléfono Telefono Doğum
Dirección Indirizzo Adresse Adres No Nr Number Page Seite Annex Schedule Section Chapter Part Data Subject Personal Name Address Phone Email""".split())
_TOK = re.compile(r"[^\W\d_](?:[^\W\d_]|['’-](?=[^\W\d_]))*\.?|[^\S\n]+|.", re.S)


def _is_cap(w):
    w = w.rstrip(".")
    if re.match(r"[dl]['’][A-ZÀ-Þ]", w):  # d'Aubigny, l'Estrange
        w = w[2:]
    return len(w) >= 2 and w[0].isupper() and (w[1:].islower() or w.isupper() or "-" in w or "'" in w or "’" in w
                                               or re.fullmatch(r"(?:Mc|Mac|Fitz)[A-Z][a-z]+", w) is not None) \
        and w not in NOT_NAMES


def _is_initial(w):
    return re.fullmatch(r"(?:[A-ZÀ-Þ]|Th|Chr|Ch|Ph|Joh|Wm)\.(?:-?[A-ZÀ-Þ]\.)*", w) is not None


def _name_at(text, pos, need_cap_first=True, max_words=5):
    """The name that starts at pos: initials, particles and capitalised words on one line. (start, end) or None."""
    words, end, i = [], None, pos
    while i < len(text) and len(words) < max_words + 2:
        m = _TOK.match(text, i)
        tok = m.group()
        if tok.isspace():
            if not words or len(tok) > 2 or "\n" in tok:
                break
            i = m.end()
            continue
        w = tok
        if _is_initial(w):
            words.append(w)
        elif w.rstrip(".").lower() in PARTICLES and words or (w.lower() in PARTICLES and not need_cap_first) or \
                (w in ("Ó", "Ní", "Nic", "Ua", "Uí", "Mac", "Mc", "Ó'") and re.match(r"\s+[A-ZÀ-Þ]", text[m.end():])):
            words.append(w)
        elif _is_cap(w):
            words.append(w)
            end = i + len(w.rstrip(".")) if w.endswith(".") and not _is_initial(w) else i + len(w)
            if w.endswith(".") and not w.rstrip(".").isupper():
                break  # a sentence ends after the name
        else:
            break
        i = m.end()
    if end is None:
        return None
    return pos, end


# The given names added on 24 Nov 2026 (UK/Irish/Welsh, Dutch, German, French, Italian, Spanish, Polish) leave out
# the unlisted and blind name pools of lab/eu/synth_eu.py, so that eval keeps measuring names that are on no list.
FIRST_NAMES = set("""
James John Robert Michael William David Richard Joseph Thomas Charles Christopher Daniel Matthew Anthony Andrew Paul
Mark Steven Kevin Brian George Edward Timothy Jason Ryan Jacob Gary Nicholas Eric Jonathan Stephen Larry Justin Scott
Benjamin Samuel Gregory Alexander Patrick Jack Dennis Peter Henry Oliver Harry Charlie Thomas Oscar Leo Noah Liam Lucas
Mary Patricia Jennifer Linda Elizabeth Barbara Susan Jessica Sarah Karen Nancy Lisa Margaret Sandra Ashley Emily Donna
Michelle Carol Amanda Melissa Deborah Stephanie Rebecca Laura Sharon Cynthia Kathleen Amy Shirley Angela Helen Anna
Emma Olivia Sophie Sophia Charlotte Amelia Isla Ava Mia Ella Chloe Lucy Hannah Grace Alice Eleanor Rachel Victoria Kate
Jonas Lukas Leon Finn Paul Felix Maximilian Max Elias Ben Luis Moritz Jan Tim Niklas Julian Fabian Tobias Stefan Florian
Andreas Markus Matthias Christian Sebastian Michael Wolfgang Klaus Jürgen Dieter Uwe Günter Helmut Manfred Werner Heinz
Hans Karl Friedrich Johannes Philipp Simon Dominik Patrick Sven Torsten Jens Kai Lars Dirk Holger Ralf Frank Bernd
Sabine Petra Monika Ursula Renate Andrea Claudia Birgit Susanne Karin Gabriele Heike Martina Stefanie Katrin Julia
Lena Lea Leonie Marie Laura Lara Johanna Katharina Sarah Hanna Mia Emilia Clara Greta Ida Frieda Paula Annika Jana
Jean Pierre Michel Philippe Alain Nicolas Christophe François Francois Laurent Patrice Bernard Daniel Olivier Thierry
Sébastien Julien Guillaume Antoine Mathieu Maxime Hugo Louis Gabriel Arthur Raphaël Jules Théo Mathis Nathan Clément
Marie Nathalie Isabelle Sylvie Catherine Françoise Valérie Sandrine Christine Véronique Céline Aurélie Camille Manon
Chloé Léa Inès Jade Louise Juliette Margaux Pauline Mathilde Élise Elise Amélie Hélène Claire Agnès Brigitte Monique
Giuseppe Giovanni Antonio Mario Luigi Francesco Angelo Vincenzo Pietro Salvatore Carlo Franco Domenico Bruno Paolo
Michele Giorgio Aldo Sergio Luciano Marco Andrea Stefano Roberto Alessandro Matteo Lorenzo Davide Simone Riccardo
Federico Luca Gabriele Tommaso Edoardo Filippo Giulio Emanuele Massimo Fabio Enrico Alberto Claudio Leonardo Nicola
Maria Anna Giuseppina Rosa Angela Giovanna Teresa Lucia Carmela Caterina Francesca Antonietta Carla Elena Concetta
Rita Margherita Franca Paola Giulia Chiara Sara Martina Alessia Sofia Aurora Beatrice Ginevra Alice Valentina Federica
José Jose Juan Manuel Francisco Luis Javier Miguel Carlos Jesús Jesus Alejandro Rafael Pedro Ángel Pablo Fernando
Jorge Alberto Sergio Diego Adrián Adrian Álvaro Alvaro Raúl Raul Enrique Ramón Ramon Vicente Iván Ivan Rubén Ruben
Óscar Andrés Andres Joaquín Joaquin Santiago Eduardo Víctor Victor Roberto Jaime Mario Ignacio Alfonso Salvador Gonzalo
Carmen Josefa Isabel Dolores Pilar Teresa Ana Laura Cristina Marta Lucía Lucia Mercedes Rosario Paula Elena Raquel
Manuela Concepción Beatriz Nuria Silvia Julia Patricia Irene Rocío Rocio Montserrat Alba Andrea Claudia Natalia
Daan Sem Levi Bram Luuk Thijs Jesse Ruben Stijn Lars Niels Pieter Joost Bas Koen Wouter Sander Maarten Jeroen Dirk
Henk Kees Gerrit Willem Hendrik Cornelis Johan Jacobus Arjen Erik Rik Tom Joris Hugo Floris Teun Gijs Mees Siem
Sanne Lotte Fleur Femke Anouk Eva Sara Lisa Iris Noa Tess Saar Julia Esther Ingrid Marieke Annemieke Willemijn Inge
Piotr Krzysztof Andrzej Tomasz Paweł Pawel Michał Michal Marcin Grzegorz Józef Jozef Marek Łukasz Lukasz Adam Zbigniew
Jerzy Tadeusz Mateusz Dariusz Mariusz Wojciech Kamil Jakub Agnieszka Barbara Ewa Krystyna Małgorzata Malgorzata
Joanna Katarzyna Magdalena Monika Dorota Aleksandra Zofia Natalia Karolina
João Joao António Manuel Francisco Rui Tiago Pedro Miguel Bruno Ricardo Nuno Afonso Duarte Rodrigo Gonçalo Goncalo
Mariana Beatriz Inês Leonor Matilde Carolina Joana Rita Catarina Margarida
Lars Anders Johan Karl Nils Erik Per Mikael Jonas Henrik Mats Magnus Björn Bjorn Sven Olof Gustav Axel Oskar Emil
Ingrid Kristina Astrid Karin Elsa Ebba Maja Freja Saga Linnea Signe Sofie Mette Hanne Kirsten Birgitte Camilla
Seán Sean Ciarán Ciaran Niamh Aoife Siobhán Siobhan Saoirse Cian Oisín Oisin Darragh Eoin Aisling Róisín Roisin
Georgios Dimitrios Konstantinos Ioannis Nikolaos Panagiotis Vasileios Christos Eleni Aikaterini Vasiliki Sofia
Jiří Jiri Petr Tomáš Tomas Martin Lukáš Jakub Ondřej Lenka Jana Petra Tereza Eszter Zsófia Zsofia László Laszlo
Gábor Gabor Zoltán Zoltan István Istvan Ion Andrei Alexandru Mihai Ioana Elena Andreea Ivana Ana Marko Luka Matej
Sergei Sergey Dmitry Dmitri Igor Oleg Olena Olga Yulia Iryna Natalia Tetiana Oksana Andriy Mykola Vladimir Alexei
Aleksandr Mindaugas Rūta Ruta Agnė Eglė Jānis Ilze Kristaps Andres Kadri Olle Annika
Ahmed Mohammed Mohamed Mehmet Ali Fatima Aisha Yusuf Omar Hassan Karim Leila Amina Youssef Ibrahim Moussa Mamadou
Ionuț Ionut Bogdan Florin Radu Sorin Cristian Valentin Bianca Alina Roxana Dorin Vlad
Harriet Gareth Duncan Callum Rosalind Fiona Angus Hamish Eilidh Morag Rhys Dylan Owen Gethin Bethan Cerys Ffion Siân
Ciara Fergus Seamus Padraig Bridget Deirdre Colm Ruairi Ewan Graeme Craig Stuart Kirsty Lindsay Matilda Phoebe
Penelope Jasper Toby Tristan Giles Nigel Clive Malcolm Trevor Derek Graham Howard Geoffrey Rodney Keith Neil Gordon
Ian Iain Wendy Gillian Maureen Brenda Sheila Annelies Noortje Maartje Jorien Ilse Hanneke Bart Bastiaan Niek Pim
Rutger Twan Klaas Rien Sietse Annegret Friederike Ulrike Hildegard Irmgard Dörte Anke Antje Frauke Gesine Mareike
Svenja Kerstin Dagmar Roswitha Gisela Waltraud Henning Gerd Horst Reinhard Ulf Jörg Sönke Malte Ole Arne Konstantin
Leonhard Ludwig Wilhelm Gottfried Clémence Apolline Capucine Ludivine Gaëlle Maëlle Romane Océane Bertrand Gaspard
Thibault Grégoire Amaury Ludovic Gwenaël Arianna Fabrizio Gianluca Pierluigi Gianfranco Begoña Inmaculada Íñigo Gorka
Jordi Arnau Grażyna Bożena Przemysław Jarosław
""".split())
# given names that are also everyday words: only with a title or a cue
AMBIGUOUS_FIRST = {"Mark", "Grace", "Rose", "Will", "May", "Bill", "Art", "Bruno", "Tom", "Max", "Rita", "Ben",
                   "Jack", "Iris", "Paula", "Saga", "Alba", "Rosa", "Teresa", "Martin", "Victoria", "Carmen",
                   "Florence", "Hazel", "Heather"}
_FIRST = re.compile(r"(?<![\w.'’-])(" + "|".join(sorted(FIRST_NAMES - AMBIGUOUS_FIRST, key=len, reverse=True)) +
                    r")(?=[\s-]+(?:(?:" + "|".join(sorted(PARTICLES - {"i", "y"}, key=len, reverse=True)) +
                    r")\s+)*[A-ZÀ-Þ])")
_FIELD = re.compile(
    r"(?im)^[ \t]*(?:full name|name|surname|first name|last name|given names?|family name|nom|prénom|nom de famille|"
    r"name des|nachname|vorname|geburtsname|nome|cognome|nombre|apellidos?|naam|achternaam|voornaam|imię|nazwisko|"
    r"data subject|employee|employer|client|customer|patient|tenant|landlord|claimant|applicant|respondent|witness|"
    r"nombre y apellidos|kunde|klient|klant|cliente|kund|asiakas|"
    r"contact person|signed|signatory|mandant(?:in)?|kläger(?:in)?|beklagte[rn]?|zeuge|zeugin|demandeur|défendeur|"
    r"témoin|attore|convenuto|ricorrente|testimone|demandante|demandado|testigo|eiser|gedaagde|getuige|"
    r"ονοματεπώνυμο|όνομα|επώνυμο|πατρώνυμο|imię i nazwisko|nume|prenume|nome completo|namn)"
    r"[ \t]*:[ \t]*\n?[ \t]*(?=\S)")
_CLOSING = re.compile(
    r"(?im)(?:kind regards|best regards|warm regards|regards|yours sincerely|yours faithfully|sincerely|"
    r"mit freundlichen grüßen|mit freundlichen gruessen|viele grüße|beste grüße|freundliche grüße|cordialement|"
    r"bien à vous|bien cordialement|salutations distinguées|cordiali saluti|distinti saluti|un cordiale saluto|"
    r"atentamente|un saludo|saludos cordiales|met vriendelijke groet(?:en)?|hoogachtend|pozdrawiam|z poważaniem|"
    r"com os melhores cumprimentos|atenciosamente|best wishes|many thanks|thanks|thank you|all the best|"
    r"(?:met )?(?:hartelijke|vriendelijke) groet(?:en)?|groeten|groetjes|danke und grüße|danke|liebe grüße|"
    r"herzliche grüße|bonne journée|merci|grazie|saluti|gracias|dziękuję)[,.!]?[ \t]*\n+[ \t]*(?=\S)")


def find_names(text):
    out = []

    def add(pos, why, score, need_cap_first=True):
        t = _TITLE.match(text, pos)
        while t:  # "Name: Herr Dr. Jonas Becker": the titles are not part of the name
            pos = t.end()
            t = _TITLE.match(text, pos)
        r = _name_at(text, pos, need_cap_first)
        if not r:
            return
        a, b = r
        val = text[a:b]
        if not any(_is_cap(w) for w in val.split()) or len(val.rstrip(".")) < 3:
            return
        out.append(_span("PERSON", a, b, text, score, "eu_name", why))

    for m in _TITLE.finditer(text):
        add(m.end(), "after a title (Herr, Mme, Sig., Sra., dhr. ...)", 0.85)
    for m in _FIELD.finditer(text):
        add(m.end(), "form field (Name:, Nom :, Kläger: ...)", 0.8)
    for m in _CLOSING.finditer(text):
        add(m.end(), "under a closing (Kind regards, Mit freundlichen Grüßen ...)", 0.8)
    for m in _FIRST.finditer(text):
        r = _name_at(text, m.start(1))
        if r and len(text[r[0]:r[1]].split()) >= 2 and text[r[0]:r[1]].split()[-1].lower() not in PARTICLES:
            out.append(_span("PERSON", r[0], r[1], text, 0.75, "eu_name", "known first name + capitalised word"))
    # a surname found once is masked wherever it appears again on its own ("Becker" after "Herr Jonas Becker")
    seen = {}
    for sp in out:
        last = sp["text"].split()[-1].rstrip(".")
        if len(last) >= 3 and last not in NOT_NAMES and not _is_initial(last) and last.lower() not in PARTICLES:
            seen.setdefault(last, sp["text"])
    for last in seen:
        for m in re.finditer(rf"(?<![\w-]){re.escape(last)}(?![\w-])", text):
            out.append(_span("PERSON", m.start(), m.end(), text, 0.7, "eu_name_repeat", "surname seen elsewhere"))
    return out


# Common surnames of EU countries (and of people from Turkey, the Maghreb and the Levant living there), used only as
# "capitalised word + known surname", so an unknown first name is still caught ("Hidde Hoekstra").
SURNAMES = set("""
Smith Jones Williams Brown Taylor Davies Evans Wilson Thomas Johnson Roberts Walker Wright Robinson Thompson White
Hughes Edwards Green Hall Wood Harris Lewis Martin Jackson Clarke Clark Turner Hill Scott Cooper Morris Ward Moore King
Watson Baker Harrison Morgan Patel Young Allen Mitchell James Anderson Phillips Lee Bell Parker Davis Murphy Kelly
O'Sullivan Walsh O'Brien Byrne Ryan O'Connor O'Neill Reilly Doyle McCarthy Gallagher Doherty Kennedy Lynch Murray Quinn
Moore McLaughlin Carroll Connolly Daly Connell Brennan Burke Collins Campbell Clarke Johnston Hughes Farrell Fitzgerald
Müller Mueller Schmidt Schneider Fischer Weber Meyer Meier Wagner Becker Schulz Hoffmann Schäfer Koch Bauer Richter Klein
Wolf Schröder Neumann Schwarz Zimmermann Braun Krüger Hofmann Hartmann Lange Schmitt Werner Schmitz Krause Meier Lehmann
Schmid Schulze Maier Köhler Herrmann König Walter Mayer Huber Kaiser Fuchs Peters Lang Scholz Möller Weiß Weiss Jung Hahn
Schubert Vogel Friedrich Keller Günther Frank Berger Winkler Roth Beck Lorenz Baumann Franke Albrecht Schuster Simon
Ludwig Böhm Winter Kraus Martin Schumacher Krämer Vogt Stein Jäger Otto Sommer Groß Seidel Heinrich Brandt Haas Schreiber
Graf Schulte Dietrich Ziegler Kuhn Kühn Pohl Engel Horn Busch Bergmann Thomas Voigt Sauer Arnold Wolff Pfeiffer Gruber
Martin Bernard Dubois Thomas Robert Richard Petit Durand Leroy Moreau Simon Laurent Lefebvre Lefèvre Michel Garcia David
Bertrand Roux Vincent Fournier Morel Girard André Lefèvre Mercier Dupont Lambert Bonnet François Martinez Legrand
Garnier Faure Rousseau Blanc Guerin Guérin Muller Henry Roussel Nicolas Perrin Morin Mathieu Clément Gauthier Dumont
Lopez Fontaine Chevalier Robin Masson Sanchez Gerard Gérard Nguyen Boyer Denis Lemaire Duval Joly Gautier Roger Roche
Roy Noel Noël Meyer Lucas Meunier Jean Perez Marchand Dufour Blanchard Marie Barbier Brun Dumas Brunet Schmitt Leroux
Colin Fernandez Pierre Renard Arnaud Rolland Caron Aubert Giraud Leclerc Vidal Bourgeois Renaud Lemoine Picard Gaillard
Philippe Leclercq Lacroix Fabre Dupuis Olivier Rodriguez Da Silva Hubert Louis Charles Guillot Rivière Le Gall Guillaume
Rossi Russo Ferrari Esposito Bianchi Romano Colombo Ricci Marino Greco Bruno Gallo Conti De Luca Mancini Costa Giordano
Rizzo Lombardi Moretti Barbieri Fontana Santoro Mariani Rinaldi Caruso Ferrara Galli Martini Leone Longo Gentile Martinelli
Vitale Lombardo Serra Coppola De Santis D'Angelo Marchetti Parisi Villa Conte Ferraro Ferri Fabbri Bianco Marini Grasso
Valentini Messina Sala De Angelis Gatti Pellegrini Palumbo Sanna Farina Rizzi Monti Cattaneo Morelli Amato Silvestri
Mazza Testa Grassi Pellegrino Carbone Giuliani Benedetti Barone Rossetti Caputo Montanari Guerra Palmieri Bernardi
Martino Fiore De Rosa Ferretti Bellini Basile Riva Donati Piras Vitali Battaglia Sartori Neri Costantini Milani
García González Rodríguez Fernández López Martínez Sánchez Pérez Gómez Martín Jiménez Ruiz Hernández Díaz Moreno Muñoz
Álvarez Romero Alonso Gutiérrez Navarro Torres Domínguez Vázquez Ramos Gil Ramírez Serrano Blanco Molina Morales Suárez
Ortega Delgado Castro Ortiz Rubio Marín Sanz Núñez Iglesias Medina Garrido Cortés Castillo Santos Lozano Guerrero Cano
Prieto Méndez Cruz Calvo Gallego Vidal León Márquez Herrera Peña Flores Cabrera Campos Vega Fuentes Carrasco Diez Díez
Caballero Reyes Nieto Aguilar Pascual Santana Herrero Lorenzo Montero Hidalgo Giménez Ibáñez Ferrer Durán Santiago
Benítez Mora Vicente Vargas Arias Carmona Crespo Román Pastor Soto Sáez Velasco Moya Soler Parra Esteban Bravo Gallardo
Rojas Etxeberria Agirre Garaikoetxea Zubizarreta Goikoetxea Arrieta Urrutia Elizondo Iturbe Larrañaga Mendizabal
Silva Santos Ferreira Pereira Oliveira Costa Rodrigues Martins Jesus Sousa Fernandes Gonçalves Gomes Lopes Marques Alves
Almeida Ribeiro Pinto Carvalho Teixeira Moreira Correia Mendes Nunes Soares Vieira Monteiro Cardoso Rocha Raposo Neves
Jansen Janssen Visser Smit Meijer Bakker Mulder Bos Vos Peters Hendriks Dekker Brouwer Dijkstra Smits Koster Willems
Verhoeven Kok Jacobs Haan Vermeulen Schouten Hoekstra Prins Huisman Boer Postma Kuipers Veenstra Kramer Kuiper Wouters
Peeters Maes Claes Goossens Wuyts Mertens Willems Dubois Lambert Dupont Martens Pauwels Michiels Desmet Hermans Verstraeten
Nowak Kowalski Kowalska Wiśniewski Wiśniewska Wójcik Kowalczyk Kamiński Kamińska Lewandowski Lewandowska Zieliński
Zielińska Szymański Szymańska Woźniak Dąbrowski Dąbrowska Kozłowski Kozłowska Jankowski Mazur Kwiatkowski Krawczyk
Piotrowski Grabowski Nowakowski Pawłowski Michalski Nowicki Adamczyk Dudek Zając Wieczorek Jabłoński Król Majewski
Olszewski Jaworski Wróbel Malinowski Pawlak Witkowski Walczak Stępień Górski Rutkowski Michalak Sikora Ostrowski Baran
Papadopoulos Papadopoulou Georgiou Dimitriou Nikolaou Konstantinou Ioannou Christodoulou Pappas Vlachos Oikonomou
Popescu Popa Pop Radu Dumitru Stan Stoica Gheorghe Matei Ciobanu Ionescu Rusu Constantin Munteanu Florea Moldovan Nagy
Kovács Tóth Szabó Horváth Varga Kiss Molnár Németh Farkas Balogh Novák Svoboda Novotný Dvořák Černý Procházka Kučera
Johansson Andersson Karlsson Nilsson Eriksson Larsson Olsson Persson Svensson Gustafsson Pettersson Jonsson Jensen
Nielsen Hansen Pedersen Andersen Christensen Larsen Sørensen Rasmussen Jørgensen Petersen Madsen Kristensen Olsen
Korhonen Virtanen Mäkinen Nieminen Mäkelä Hämäläinen Laine Heikkinen Koskinen Järvinen Horvat Kovačević Babić Marić
Novak Kovačič Krajnc Zupančič Ivanov Petrov Georgiev Dimitrov Kazlauskas Jankauskas Bērziņš Kalniņš Tamm Saar Sepp
Borg Camilleri Vella Farrugia Zammit Galea Micallef Grech Attard Spiteri Azzopardi Georgiou Hadjiantoniou
Yılmaz Kaya Demir Şahin Çelik Yıldız Yıldırım Öztürk Aydın Özdemir Arslan Doğan Kılıç Aslan Çetin Kara Koç Kurt Özkan
Benali Haddad Khalil Hassan Mansour Saleh Nasser Ibrahim Rahman Ahmadi Hosseini Mohammadi Rezaei Karimi Haidari Hussaini
Berg Vries Meer Dijk Graaf Leeuwen Heuvel Linden Wal Brink Beek Veen Bosch Velde Horst Hoek Wijk Laan Berge Broek Steen
Luca Santis Rosa Angelis Silva Souza Gall Goff Roux Bois Costa Sousa
""".split())
_SURNAME_PAIR = re.compile(r"(?<![\w'’.-])([A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][a-zà-ÿłśżźćńšžčřđőűąęėįųūāēīō'’-]+)\s+"
                           r"((?:(?i:" + "|".join(sorted(PARTICLES - {"i", "y", "el", "al", "op", "'t"}, key=len, reverse=True)) +
                           r")\s+)*(?:" + "|".join(re.escape(n) for n in sorted(SURNAMES, key=len, reverse=True)) +
                           r"))(?![\w'’-])")

_SURNAME_ENDING = re.compile(
    r"(?<![\w'’.-])([A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][a-zà-ÿłśżźćńšžčřđőűąęėįųūāēīō'’-]{1,14})\s+"
    r"([A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][a-zà-ÿłśżźćńšžčřđőűąęėįųūāēīō'’-]*(?:ov|ova|ev|eva|enko|chuk|czuk|uk|yk|ski|ska|sky|ský|ská|"
    r"cki|cka|wicz|vić|ović|ević|ić|escu|eanu|auskas|iauskas|ienė|aitė|ytė|ūtė|onis|aitis|poulos|poulou|akis|idis|"
    r"opoulos|oğlu|sson|sdóttir|dóttir|ström|qvist|kvist|ainen|äinen|ovič|evič))(?![\w'’-])")


# a role or an act that is followed by a person's name ("vertreten durch", "UBO:", "Geschäftsführer")
_BEFORE_CUE = re.compile(
    r"(?i)\b(?:represented by|on behalf of|we act for|acting for|act for|our client|signed by|attn\.?|attention|c/o|"
    r"for the attention of|vertreten durch|im namen von|für unseren? mandant(?:in|en)?|unser(?:e[rn]?)? mandant(?:in)?|"
    r"wir vertreten|z\. ?hd\.?|zu händen(?: von)?|nous représentons|représentée? par|pour le compte de|"
    r"à l'attention de|au nom de|assistiamo|rappresentat[oa] da|per conto di|alla c\.a\.|all'attenzione di|"
    r"in nome di|representamos a|representad[oa] por|en nombre de|a la atención de|a la att\.|wij staan|"
    r"vertegenwoordigd door|namens|t\.a\.v\.|ten behoeve van|in my name|in the name of|account holder|"
    r"op naam van|ten name van|t\.n\.v\.|rekeninghouder|(?:konto)?inhaber(?:in)?|au nom de|intestat[oa] a|a nombre de|"
    r"titular de la cuenta|na nazwisko|müvekkil(?:imiz)?|vekili|"
    r"directors?|managing director|non-executive director|chief executive officer|ceo|cfo|coo|chairman|chairwoman|"
    r"shareholders?|ubos?|beneficial owners?|ultimate beneficial owners?|partners?|employee|tenant|landlord|"
    r"geschäftsführer(?:in)?|vorstand|vorstandsvorsitzende[r]?|gesellschafter(?:in)?|prokurist(?:in)?|"
    r"wirtschaftlich berechtigte[rn]?|arbeitnehmer(?:in)?|mieter(?:in)?|vermieter(?:in)?|gérante?|président(?:e)?|"
    r"directeur général|directrice générale|actionnaires?|bénéficiaires? effectifs?|salariée?|locataire|bailleur|"
    r"amministratore(?: unico| delegato)?|presidente|soci[oa]?|titolare effettivo|dipendente|lavoratore|lavoratrice|"
    r"administrador(?:a)?(?: únic[oa])?|consejero delegado|titular real|trabajador(?:a)?|arrendatari[oa]|"
    r"bestuurder|directeur|aandeelhouders?|uiteindelijk belanghebbende|werknemer|huurder|verhuurder|"
    r"yönetim kurulu üyesi|ortak|pay sahibi|advokat|advocaat|lawyer|solicitor|counsel|attorney|notary|"
    r"pracownik(?:a|iem)?|świadek|sąsiad(?:ka|ki)?|arv efter|estate of|nachlass (?:von|nach)|succession de|"
    r"eredità di|herencia de|nalatenschap van|doğum soyadı|kızlık soyadı|geburtsname|nom de naissance|"
    r"apellido de soltera|bror|søster|syster|hustru|datter|dotter|"
    r"my (?:husband|wife|son|daughter|partner|brother|sister|father|mother)|mein(?:e)? (?:mann|frau|sohn|tochter|"
    r"bruder|schwester|vater|mutter|partner(?:in)?)|mijn (?:man|vrouw|zoon|dochter|partner)|mon (?:mari|fils|frère|père)|"
    r"ma (?:femme|fille|sœur|mère)|mio (?:marito|figlio|fratello|padre)|mia (?:moglie|figlia|sorella|madre)|"
    r"mi (?:marido|esposa|mujer|hijo|hija|hermano|hermana)|mój (?:mąż|syn|brat)|moja (?:żona|córka|siostra))\b(?:\s*\([^)]{1,30}\))?[ \t]*[:,]?[ \t]+(?=[A-ZÀ-ÞŁŚŻ])")
_LIST_SEP = re.compile(r"\s*(?:,|;|\band\b|\bund\b|\bet\b|\be\b|\by\b|\ben\b|\boraz\b|\bve\b|&)\s*(?=[A-ZÀ-ÞŁŚŻ])")
# a name right before an apposition ("Anna Kowalski, born ...", "Jan Visser (the Employee)")
_AFTER_CUE = re.compile(
    r"(?i)(?:,\s*|\s*\(\s*)(?:born|b\.|geb\.|geboren|née?|nat[oa]|nacid[oa]|residing|resident|domiciled|"
    r"wohnhaft|demeurant|domicilié(?:e)?|residente|con domicilio|domiciliad[oa]|wonende|woonachtig|"
    r"the [\"“”']?(?:employee|client|tenant|seller|buyer|guarantor|data subject)|hereinafter|nachfolgend|"
    r"ci-après|di seguito|en adelante|hierna|doğum|ikamet|tc kimlik|passport|reisepass|passeport|"
    r"date of birth|\d{4}\s*[-–]\s*\)|\*\s?\d)")
# e-mail headers: "From: Anna Kowalski <anna@...>"
_MAIL_HEADER = re.compile(r"(?im)^[ \t]*(?:from|to|cc|bcc|von|an|de|à|a|da|van|aan|kimden|kime)[ \t]*:[ \t]*"
                          r"(?=[^<\n]{3,60}<)")
_EMAIL_NAME = re.compile(r"(?<![\w.+-])([A-Za-zÀ-ÿ]{2,})[._]([A-Za-zÀ-ÿ]{2,}(?:-[A-Za-zÀ-ÿ]{2,})?)@[\w-]+(?:\.[\w-]+)+")
_NAME_BEFORE = re.compile(r"((?:[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][\w'’-]*\.?\s+(?:(?:" +
                          "|".join(sorted(PARTICLES - {"i", "y"}, key=len, reverse=True)) +
                          r")\s+)*){1,3}[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][\w'’-]+)$")


def _fold(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def find_names_context(text):
    """Names found by what surrounds them rather than by a word list: after a role or act ("vertreten durch",
    "UBO:", "Geschäftsführer"), lists after such a role, before an apposition ("…, born", "… (the Employee)"),
    in e-mail headers, names spelled out in an e-mail address (anna.kowalski@ -> "Anna Kowalski"), and
    a capitalised word followed by a common surname."""
    out = []

    def take(pos, why, score):
        t = _TITLE.match(text, pos)
        while t:
            pos = t.end()
            t = _TITLE.match(text, pos)
        r = _name_at(text, pos, max_words=4)
        if not r:
            return None
        a, b = r
        words = text[a:b].split()
        if len(words) < 2 and not (len(words) == 1 and _is_cap(words[0]) and words[0].rstrip(".") in SURNAMES):
            return None  # one capitalised word after a role is too often a company or a place
        if words[-1].lower() in PARTICLES:
            return None
        out.append(_span("PERSON", a, b, text, score, "eu_name_context", why))
        return b

    for m in _BEFORE_CUE.finditer(text):
        end = take(m.end(), "after a role or act (vertreten durch, UBO:, director ...)", 0.8)
        while end is not None:  # "Directors: Anna Kowalski, Jan Visser and Marie Dubois"
            sep = _LIST_SEP.match(text, end)
            if not sep:
                break
            end = take(sep.end(), "in a list of people after a role", 0.75)
    for m in _MAIL_HEADER.finditer(text):
        take(m.end(), "e-mail header", 0.85)
    for m in _AFTER_CUE.finditer(text):
        head = text[max(0, m.start() - 80):m.start()]
        n = _NAME_BEFORE.search(head)
        if not n:
            continue
        a = m.start() - len(n.group(1))
        # keep only the capitalised run right before the cue, and never across a sentence start like "The"
        words = n.group(1).split()
        while words and (words[0].rstrip(".") in NOT_NAMES or words[0].rstrip(".") in TITLES):
            a += len(text[a:].split(words[0], 1)[0]) + len(words[0])
            a = len(text) - len(text[a:].lstrip())
            words = words[1:]
        if len(words) >= 3 and words[0] not in FIRST_NAMES and not _is_initial(words[0]):
            a += len(words[0]) + len(text[a + len(words[0]):]) - len(text[a + len(words[0]):].lstrip())
            words = words[1:]  # "Assistiamo Gennaro Caruso, residente": the verb before the name
        if len(words) >= 2 and all(_is_cap(w) or w.lower() in PARTICLES or _is_initial(w) for w in words):
            out.append(_span("PERSON", a, m.start(), text, 0.8, "eu_name_context", "before an apposition (…, born; …, wohnhaft)"))
    for m in _EMAIL_NAME.finditer(text):
        first, last = _fold(m.group(1)), _fold(m.group(2))
        if first in {"info", "contact", "office", "mail", "kanzlei", "legal", "privacy", "dpo", "hr", "support", "no"}:
            continue
        for w in re.finditer(r"(?<![\w'’-])([^\W\d_][\w'’-]+)\s+((?:[a-zà-ÿ]+\s+)*[^\W\d_][\w'’-]+)(?![\w'’-])", text):
            if _fold(w.group(1)) == first and _fold(w.group(2).split()[-1]) == last and w.group(1)[0].isupper():
                out.append(_span("PERSON", w.start(), w.end(), text, 0.9, "eu_name_email", "name spelled out in an e-mail address"))
    for m in _SURNAME_ENDING.finditer(text):
        first = m.group(1)
        if first in NOT_NAMES or first in TITLES or first in _DETERMINERS or first in _FIELD_WORDS or \
                first in _COMPANY_WORDS or _COMPANY_AFTER.match(text, m.end(2)):
            continue
        out.append(_span("PERSON", m.start(1), m.end(2), text, 0.75, "eu_name_surname", "capitalised word + typical surname ending"))
    for m in _SURNAME_PAIR.finditer(text):
        first = m.group(1)
        if first in NOT_NAMES or first in TITLES or first.rstrip(".").lower() in PARTICLES or first in SURNAMES and \
                m.start() > 0 and text[m.start() - 1] not in " \n\t(\"“":
            continue
        r = _name_at(text, m.start(1), max_words=4)  # "Amaia García López": take the second surname too
        end = max(m.end(2), r[1] if r else 0)
        out.append(_span("PERSON", m.start(1), end, text, 0.75, "eu_name_surname", "capitalised word + common surname"))
    return out


_INITIAL_NAME = re.compile(r"(?<![\w.])((?:[A-ZÀ-ÞŁŚŻ]\.[ -]?){1,3}[ \t]?(?:(?i:" +
                           "|".join(sorted(PARTICLES - {"i", "y", "'t"}, key=len, reverse=True)) +
                           r")[ \t]+)*[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘŞÇĞÖÜİ][a-zà-ÿłśżźćńšžčřđőűąęėįųūāēīōışğçöü'’-]{2,}"
                           r"(?:-[A-ZÀ-Þ][a-zà-ÿ'’-]+)?)(?![\w'’])")
# chat lines: "[22/10/2026, 18:03] Ahmed Al-Masri: ...", "Jule: ...", "Carmen 10:14: ..."
_CHAT = re.compile(r"(?m)^[ \t]*(?:\[[^\]\n]{4,25}\][ \t]*|\d{1,2}[:.]\d{2}[ \t]+)?"
                   r"((?:[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][\w'’-]+)(?:[ \t]+(?:[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][\w'’-]+|[a-z]{1,3}|[A-Z]\.)){0,3})"
                   r"(?:[ \t]+\d{1,2}[:.]\d{2})?[ \t]*:[ \t]+\S")


_FIRST_FOLD = None
_HANDLE = re.compile(r"(?<![\w.@/-])@?([a-zà-ÿ]{2,}[._][a-zà-ÿ]{2,}(?:-[a-zà-ÿ]+)?)(?![\w@-]|\.[a-z])")


def _handles(text):
    """Chat handles first.last (@lucia.moretti) whose first part is a known first name."""
    global _FIRST_FOLD
    if _FIRST_FOLD is None:
        _FIRST_FOLD = {_fold(n) for n in FIRST_NAMES}
    return [_span("PERSON", *m.span(1), text, 0.8, "eu_name_handle", "user handle first.last")
            for m in _HANDLE.finditer(text) if _fold(re.split(r"[._]", m.group(1))[0]) in _FIRST_FOLD]


def find_names_shapes(text):
    """Initials + surname ("J. Müller", "P. van der Heijden") and chat speakers (two or more chat-style lines)."""
    out = []
    for m in _INITIAL_NAME.finditer(text):
        last = m.group(1).split()[-1]
        before = text[max(0, m.start() - 6):m.start()]
        if last.rstrip(".") in NOT_NAMES or last in _DETERMINERS or len(last) > 15 or \
                re.search(r"(?i)(?:art|abs|nr|no|lit|s|para?)\.?\s*$|\b[a-z]\.\s?$", before):
            continue
        if re.fullmatch(r"(?:[A-Z]\.\s?){2,3}", m.group(1).rsplit(" ", 1)[0] + " ") and last.isupper():
            continue  # "U.S. GAAP"
        out.append(_span("PERSON", m.start(1), m.end(1), text, 0.8, "eu_name_initials", "initials + surname"))
    cands = [m for m in _CHAT.finditer(text)
             if m.group(1).split()[0] not in NOT_NAMES and m.group(1).split()[0] not in _FIELD_WORDS
             and not m.group(1).isupper() and not any(w in _LABEL_WORDS for w in m.group(1).split())]
    from collections import Counter
    times = Counter(m.group(1) for m in cands)
    # "Anwesend:", "Protokoll:", "DAVACI:" are labels, each once; a chat speaker has a time stamp or speaks twice
    speakers = [m for m in cands if times[m.group(1)] >= 2 or re.match(r"[ \t]*(?:\[|\d{1,2}[:.]\d{2})", text[m.start():m.start(1)])
                or re.match(r"[ \t]+\d{1,2}[:.]\d{2}", text[m.end(1):])]
    if len(speakers) >= 2:
        for m in speakers:
            out.append(_span("PERSON", *m.span(1), text, 0.8, "eu_name_chat", "chat speaker"))
        # in a chat people are called by first name alone ("¿has hablado con Pablo?")
        for m in re.finditer(r"(?<![\w'’-])([A-ZÀ-ÞŁŚŻ][\w'’-]+)(?![\w-])", text):
            if m.group(1) in FIRST_NAMES and m.group(1) not in AMBIGUOUS_FIRST:
                out.append(_span("PERSON", *m.span(1), text, 0.7, "eu_name_chat", "first name in a chat"))
    return out


_LABEL_WORDS = set("""Present Anwesend Abwesend Gäste Protokoll Protokollführer Zeugen Sachverhalt Signed Getekend
Aanwezig Afwezig Notulist Patient Anschrift Diagnosen Diagnose Verantwortlicher Ansprechpartner Beschreibung Betroffene
Daten Maßnahmen Organisatie Contactpersoon Titolare Responsabile Présents Absents Secrétaire Presenti Assenti Presentes
Ausentes Secretario Attendees Apologies Minutes Chair Chairman Secretary Agenda Tagesordnung Ordre Ordine Orden
Agenda Konu Davacı Davalı Vekili Deliller Suç Şüpheli Müşteki Mağdur Tanık Sonuç Talep Açıklamalar Hukuki Nedenler""".split())
_FIELD_WORDS = set("""Name Surname Address Phone Tel Email E-mail Date Subject Re Betreff Objet Oggetto Asunto Betreft
Client Mandant From To Cc Von An De Da Van Aan Note Notes Status Result Action Purpose Category Categories Recipient
Recipients Retention Legal Basis Controller Processor Source Answer Request Response Q A Step Ergebnis Hinweis Datum
Adresse Telefon Nom Prénom Nome Nombre Naam Adres Kimden Kime Konu Tarih Not Sonuç Role Function Funktion Fonction
Ruolo Función Functie Requester Antragsteller Demandeur Richiedente Solicitante Verzoeker Total Amount Betrag IBAN BIC
Bank VAT USt TVA IVA Ref Reference Az Aktenzeichen Case Matter Project Deadline Owner Hash Risk Match Score""".split())


# ---------------------------------------------------------------- tables (CSV exports, customer lists)
_COL_TYPES = [
    ("PERSON", r"(?:full ?name|name|vorname|nachname|surname|first ?name|last ?name|given ?names?|family ?name|nom|prénom|"
               r"nome|cognome|nombre|apellidos?|naam|voornaam|achternaam|imię|nazwisko|namn|förnamn|efternamn|"
               r"customer|kunde|kundin|client|cliente|klant|employee|mitarbeiter|patient|ad|soyad|ad soyad|όνομα|επώνυμο)"),
    ("BIRTH_DATE", r"(?:dob|date of birth|birth ?date|geburtsdatum|geb\.?|date de naissance|data di nascita|"
                   r"fecha de nacimiento|geboortedatum|data urodzenia|födelsedatum|doğum tarihi)"),
    ("NATIONAL_ID", r"(?:steuer-?id|tax ?id|tin|bsn|nir|codice fiscale|cf|dni|nie|nif|pesel|cnp|personnummer|"
                    r"national ?id|id ?number|ssn|amka|tc ?kimlik|tckn)"),
    ("ADDRESS", r"(?:address|street|anschrift|straße|strasse|adresse|indirizzo|dirección|direccion|adres|straat|"
                r"ulica|adress|gatuadress)"),
    ("PHONE", r"(?:phone|tel\.?|telefon|téléphone|telefono|teléfono|telefoon|mobile|handy)"),
]


def find_table_cells(text):
    """A delimited table (header row + rows, split by ; , tab or |): cells under a name, birth-date, ID, address or
    phone header are masked whatever they look like."""
    out = []
    lines = [(m.start(), m.group()) for m in re.finditer(r"[^\n]+", text)]
    i = 0
    while i < len(lines):
        start, line = lines[i]
        sep = max(";\t|,", key=line.count) if any(c in line for c in ";\t|,") else None
        if sep is None or line.count(sep) < 2:
            i += 1
            continue
        heads = [re.sub(r"[_-]+", " ", h.strip().strip('"').lower()) for h in line.split(sep)]
        kinds = [next((t for t, rx in _COL_TYPES if re.fullmatch(rx, h)), None) for h in heads]
        if not any(kinds):
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j][1].count(sep) == line.count(sep):
            rs, row = lines[j]
            pos = rs
            for k, cell in enumerate(row.split(sep)):
                c = cell.strip().strip('"')
                if k < len(kinds) and kinds[k] and c and c not in ("-", "–", "n/a", "N/A"):
                    a = pos + cell.find(c)
                    out.append(_span(kinds[k], a, a + len(c), text, 0.8, "eu_table", f"table column '{heads[k]}'"))
                pos += len(cell) + 1
            j += 1
        i = j
    return out


# ---------------------------------------------------------------- special categories (GDPR Art. 9 and 10)
# keyword level, like the Turkish HEALTH rules: the medical word is masked, the sentence around it stays
_SPECIAL = {
    "HEALTH": r"""diabetes|diabetic|diabète|diabetico|diabético|suikerziekte|cancer|krebs|tumou?r|tumeur|tumore|leukaemia|
        leukemia|hiv|aids|hepatitis|depression|depressione|depresión|depressie|dépression|burn-?out|anxiety|angststörung|
        schizophreni\w*|bipolar\w*|psychiatri\w*|psychotherap\w*|epilep\w*|asthma|dementia|demenz|démence|alzheimer|
        parkinson|multiple sclerosis|multiple sklerose|sclérose en plaques|stroke|schlaganfall|infarct\w*|heart attack|
        herzinfarkt|bandscheibe\w*|slipped disc|herniated disc|hernie discale|ernia del disco|hernia discal|hernia de disco|
        hernia|rückenleiden|pregnan\w*|schwanger\w*|enceinte|grossesse|incinta|gravidanza|embarazad\w*|zwanger\w*|
        disabilit\w*|behinderung|schwerbehindert\w*|handicap\w*|disabilità|invalidità|discapacidad|minusval\w*|
        sick leave|sick note|krankgeschrieben|arbeitsunfähig\w*|krankmeldung|arrêt maladie|arrêt de travail|
        malattia|baja médica|incapacidad temporal|ziekteverlof|ziekgemeld|arbeidsongeschikt\w*|bedrijfsarts|
        occupational physician|diagnos\w*|diagnose|diagnostic|diagnosi|diagnóstico|medication|medikament\w*|
        médicament\w*|farmac\w*|therapy|therapie|thérapie|terapia|surgery|operation am|chirurgie|intervento chirurgico|
        cirugía|operatie|hospitali[sz]\w*|krankenhaus\w*|ospedale|ricovero|hospitalización|ziekenhuisopname|
        burns?|verbrennung\w*|brûlure\w*|ustion\w*|quemadura\w*|brandwond\w*|skin graft|hauttransplantation|
        fracture\w*|fraktur|frattura|fractura|breuk|addiction|sucht|alcoholism|alkoholabhängig\w*|drug use|
        hypoglyc\w*|hypoglyk\w*|insulin\w*|chemotherap\w*|dialys\w*|rehabilita\w*|reintegrat\w*|wiedereingliederung|
        trauma\w*|traumatisme\w*|whiplash|schleudertrauma|latigazo|esguince|contusi[oó]n\w*|contusion\w*|prellung\w*|
        kneuzing\w*|commotio\w*|gehirnerschütterung|concussion|kırı[gğ]\w*|kırık\w*|fonksiyon kaybı|iş göremezli\w*|
        maluliyet\w*|engellilik|ameliyat\w*|teşhis\w*|kanser\w*|diyabet\w*|felç\w*|travma\w*|hastalı[gğ]\w*""",
    "RELIGION": r"""muslim\w*|islam\w*|christian\w*|catholic\w*|katholisch\w*|catholique|cattolic\w*|católic\w*|
        katholiek\w*|protestant\w*|evangelisch\w*|jewish|jüdisch\w*|juif|juive|ebreo|ebrea|judío|judía|joods|
        buddhist\w*|hindu\w*|atheist\w*|athée|ateo|atea|kirchensteuer|church tax|religious affiliation|konfession""",
    "UNION": r"""trade union member\w*|union member\w*|gewerkschaftsmitglied\w*|mitglied der gewerkschaft|syndiqué\w*|
        membre d'un syndicat|iscritt[oa] al sindacato|afiliad[oa] (?:a|al) sindicato|vakbondslid|lid van de vakbond""",
    "POLITICAL": r"""party member(?:ship)?|parteimitglied\w*|membre du parti|iscritt[oa] al partito|afiliad[oa] al partido|
        partijlid""",
    "SEXUAL_LIFE": r"""homosexual\w*|gay|lesbian|lesbisch\w*|bisexual\w*|transgender|sexual orientation|sexuelle orientierung|
        orientation sexuelle|orientamento sessuale|orientación sexual|seksuele geaardheid""",
    "BIOMETRIC_GENETIC": r"""fingerprints?|fingerabdr\w*|empreintes? digitales?|impronte digitali|huellas dactilares|
        vingerafdruk\w*|genetic test\w*|gentest\w*|dna[- ]test\w*|test génétique|facial recognition|gesichtserkennung""",
    "CRIMINAL_RECORD": r"""criminal record|vorstrafe\w*|vorbestraft|casier judiciaire|casellario giudiziale|antecedentes penales|
        strafblad|convicted|verurteilt|condamné\w*|condannat\w*|condenad\w*|veroordeeld|investigation for|
        ermittlungsverfahren""",
}
# only the line breaks of the lists are dropped: multi-word entries ("sick leave", "criminal record") keep their space
_SPECIAL_RE = {k: re.compile(r"(?i)(?<![\w-])(?:" + re.sub(r"\s*\n\s*", "", v) + r")(?![\w-])") for k, v in _SPECIAL.items()}


# "6,000,000" and "18 742,30" are numbers, "(ICD-10 G35.1)" a code, "CHU de Limoges" an institution: all stay readable
_CLAUSE_END = re.compile(r"[;:\n]|,(?!\d)|(?<![\d\s])\.(?=\s|$)|(?<=\d)\.(?=\s+[A-ZÀ-Þ])|\s[–—]\s|"
                         r"[ \t]?\((?=[A-Z]{2,}[\w-]*[ -]?\d)")
_INSTITUTION_NEXT = re.compile(r"[ \t](?=(?:au|im|in|en|at|al|nel|a|im|in der|ins)?[ \t]?(?:CHU|CHR|AP-HP|Hospital|Hôpital|"
                         r"Krankenhaus|Klinikum|Klinik|Clinic|Clinique|Clínica|Ospedale|Policlinico|Ziekenhuis|UMC|"
                         r"Universit\w+|Hastane\w*)\b)")


def _health_phrase(text, a, b, cap=140):
    """Widen a health keyword to its clause: "fracture ouverte du tiers distal du tibia gauche avec plaie contuse
    de 6 cm", "diabète de type 2 sous metformine", "Chemotherapie wegen Brustkrebs" (fikri, 24 Nov 2026: mask
    the whole health phrase, not only the medical word). Clauses end at , ; : a line end or a sentence full stop."""
    left = a
    while left > 0 and not _CLAUSE_END.match(text, left - 1) and a - left < cap:
        left -= 1
    inst = list(re.finditer(r"(?i)\b(?:CHU|CHR|Hospital|Hôpital|Krankenhaus|Klinikum|Klinik|Clinic|Clinique|Clínica|"
                            r"Ospedale|Policlinico|Ziekenhuis|UMC|Hastane\w*)\b", text[left:a]))
    if inst:  # "Maltepe Üniversitesi Hastanesi raporunda %32 …": the hospital's name stays readable
        left += inst[-1].end()
    m = _CLAUSE_END.search(text, b)
    right = m.start() if m else len(text)
    i = _INSTITUTION_NEXT.search(text, b, right)
    right = i.start() if i else right
    if right - left > cap:  # a long sentence: keep the widening near the medical word
        left = max(left, a - 50)
        right = min(right, b + 70)
        left = text.find(" ", left) + 1 if left < a and " " in text[left:a] else left
        sp = text.rfind(" ", b, right)
        right = sp if right < len(text) and sp > b and _CLAUSE_END.match(text, right) is None else right
    while left < a and text[left] in " \t'’\"(":
        left += 1
    while right > b and text[right - 1] in " \t\"":
        right -= 1
    return left, right


def find_special(text):
    tr = _looks_turkish(text)
    out = []
    for k, rx in _SPECIAL_RE.items():
        if tr and k != "HEALTH":
            continue  # the Turkish engine has its own lists; health phrases are widened for both
        for m in rx.finditer(text):
            if re.match(r"(?:[ \t]+[A-ZÀ-Þ][\w&.'’-]*){0,3}[ \t]+" + COMPANY_FORMS + r"(?![\w])", text[m.end():]):
                continue  # "Shannon Diagnostics Ltd" is a company
            a, b = _health_phrase(text, *m.span()) if k == "HEALTH" else m.span()
            out.append(_span(k, a, b, text, 0.7, "eu_special", "special category (GDPR Art. 9/10)"))
    return out


# ---------------------------------------------------------------- optional multilingual model

_NER = None


def _ner():
    """GLiNER multi-PII as an extra name layer, only when KATIP_EU_NER=gliner and the gliner package is installed
    (it brings PyTorch and a ~1.1 GB model, downloaded once from Hugging Face; Apache-2.0). Off by default."""
    global _NER
    if _NER is None:
        _NER = False
        if os.environ.get("KATIP_EU_NER", "").lower() == "gliner":
            try:
                from gliner import GLiNER
                _NER = GLiNER.from_pretrained(os.environ.get("KATIP_EU_NER_MODEL", "urchade/gliner_multi_pii-v1"))
            except Exception as e:  # noqa: BLE001 - the rules still run
                import logging
                logging.getLogger("katip").warning("EU name model not loaded: %s", type(e).__name__)
    return _NER or None


def _chunks(text, size=900):
    """Pieces of at most ~size characters, cut at a line or sentence end (the model reads ~384 tokens)."""
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            cut = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if cut > start + size // 3:
                end = cut + 1
        yield start, text[start:end]
        start = end


_DETERMINERS = set("""Each Every Any All Such Other Jeder Jede Jedes Jedem Jeden Dem Den Des Einer Eines Einem Ein Eine
Chaque Tout Toute Tous Ogni Cada Elke Ieder Iedere Vorsitz Mitglied Mitglieder""".split())


def find_names_model(text):
    model = _ner()
    if not model:
        return []
    thr = float(os.environ.get("KATIP_EU_NER_THRESHOLD", "0.5"))
    out = []
    for off, piece in _chunks(text):
        for e in model.predict_entities(piece, ["person"], threshold=thr):
            a, b = off + e["start"], off + e["end"]
            words = [w.strip(".,;:()") for w in text[a:b].split()]
            # the model also tags role nouns ("controller", "data subject", "der Verantwortliche"): a name here
            # must be capitalised, must not start with an article or a stop word, and a single word must be a
            # known first name or surname
            if not words or not words[0][:1].isupper() or words[0] in NOT_NAMES or words[0] in _DETERMINERS:
                continue
            if any(len(w) > 15 for w in words):
                continue  # "Datenschutzbeauftragten": German compound nouns, not names
            if any(not (w[:1].isupper() or w.lower() in PARTICLES or _is_initial(w + ".")) for w in words):
                continue
            if len(words) == 1 and words[0] not in FIRST_NAMES and words[0] not in SURNAMES:
                continue
            out.append(_span("PERSON", a, b, text, round(float(e["score"]), 3), "eu_gliner", "multilingual name model"))
    return out


# ---------------------------------------------------------------- entry points

# a name followed by the office of its holder ("Overbeck, Rechtspflegerin", "Íñigo Arrizabalaga, Notario")
_ROLE_AFTER = re.compile(
    r"(?<![\w'’.-])((?:[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][\w'’.-]*[ \t]+){0,3}[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ][\w'’-]+),[ \t]+(?:Rechtspfleger(?:in)?|"
    r"Richter(?:in)?|Notar(?:in)?|Notaio|Notaia|Notario|Notaria|Notaris|notaris|[Gg]riffier|[Rr]echter|"
    r"Urkundsbeamt\w*|Geschäftsführer(?:in)?|Greffi(?:er|ère)|Cancelliere|Letrad[oa]|[Ss]ędzia|[Nn]otariusz|"
    r"[Ii]ncident [Ll]ead|DPO|[Dd]irector|[Mm]anaging [Dd]irector|Yeminli Tercüman|[Tt]ranslator)\b")


_KIN = re.compile(r"(?i)\b(?:my (?:husband|wife|son|daughter|brother|sister)|mein(?:e)? (?:mann|frau|sohn|tochter|bruder|"
                  r"schwester)|mijn (?:man|vrouw|zoon|dochter)|mon (?:mari|fils|frère)|ma (?:femme|fille|sœur)|"
                  r"mio (?:marito|figlio|fratello)|mia (?:moglie|figlia|sorella)|mi (?:marido|esposa|mujer|hijo|hija)|"
                  r"mój (?:mąż|syn|brat)|moja (?:żona|córka|siostra)|eşim|oğlum|kızım|his (?:wife|husband|son|daughter)|"
                  r"her (?:husband|wife|son|daughter)|hendes (?:bror|søster|mand)|hans (?:kone|hustru|bror))[ \t]*,?[ \t]+(?=[A-ZÀ-ÞŁŚŻ])")


_PEOPLE_LIST = re.compile(r"(?im)^[ \t]*(?:present|in attendance|attendees|apologies|absent|anwesend|abwesend|teilnehmer|"
                          r"aanwezig|afwezig|présents?|excusés?|presenti|assenti|asistentes|ausentes|obecni|nieobecni|"
                          r"tilstede|närvarande|katılanlar|hazır bulunanlar)[ \t]*:[ \t]*([^\n]+)")


def find_names_roles(text):
    out = []
    for m in _PEOPLE_LIST.finditer(text):
        pos = m.start(1)
        for part in re.split(r"(,|;|\band\b|\bund\b|\ben\b|\bet\b|\be\b|\by\b|\bve\b)", m.group(1)):
            seg = re.sub(r"\s*\([^)]*\)?\s*$", "", part)
            lead = len(seg) - len(seg.lstrip())
            seg = seg.strip()
            words = seg.split()
            a = pos + lead
            t = _TITLE.match(text, a)
            while t:
                a = t.end()
                t = _TITLE.match(text, a)
            r = _name_at(text, a, max_words=5)
            if r and 1 <= len(text[r[0]:r[1]].split()) <= 5 and not any(w.strip(".,") in _COMPANY_WORDS for w in words):
                out.append(_span("PERSON", r[0], r[1], text, 0.8, "eu_name_list", "in a list of people (Present:, Apologies:)"))
            pos += len(part)
    for m in _KIN.finditer(text):  # "Mein Mann Rüdiger kommt": one word is enough after a family word
        r = _name_at(text, m.end(), max_words=3)
        if r and _is_cap(text[r[0]:r[1]].split()[0]):
            out.append(_span("PERSON", r[0], r[1], text, 0.8, "eu_name_kin", "name after a family word (my husband …)"))
    for m in _ROLE_AFTER.finditer(text):
        a, b = m.span(1)
        words = text[a:b].split()
        while words and not (_is_cap(words[0]) or _is_initial(words[0])):  # "Ante mí, ..." / sentence words
            a += len(words[0]) + (len(text[a:b]) - len(text[a:b].lstrip()) or 1)
            a = b - len(" ".join(words[1:])) if len(words) > 1 else b
            words = words[1:]
        if not words or any(w.strip(".,") in _COMPANY_WORDS for w in words):
            continue
        out.append(_span("PERSON", a, b, text, 0.8, "eu_name_role", "name before an office (…, Notario / Rechtspflegerin)"))
    return out


def detect(text: str) -> list[dict]:
    """Every EU span this module finds; overlaps between them are left to merge()."""
    return (find_iban(text) + find_vat(text) + find_national_ids(text) + find_documents(text) + find_phones(text)
            + find_birth_dates(text) + find_addresses(text) + find_names(text) + find_names_context(text)
            + find_names_shapes(text) + find_names_roles(text) + _handles(text) + find_names_model(text) + find_special(text) + find_table_cells(text))


_RANK = {t: i for i, t in enumerate(("PERSON", "ADDRESS", "BIRTH_DATE", "PHONE", "ID_DOCUMENT", "PASSPORT",
                                     "VAT_ID", "NATIONAL_ID", "IBAN"))}


_TR_NAMES = None


def _turkish_name(word: str) -> bool:
    """In the Turkish first- or last-name lists of the engine (a Turkish client in a German letter keeps its name)."""
    global _TR_NAMES
    if _TR_NAMES is None:
        _TR_NAMES = set()
        try:
            from pathlib import Path
            import katip_redact
            d = Path(katip_redact.__file__).parent / "data"
            for f in ("first_names.txt", "last_names.txt"):
                _TR_NAMES |= {w.strip() for w in (d / f).read_text(encoding="utf-8").splitlines() if w.strip()}
        except Exception:  # noqa: BLE001 - without the lists every one-word tagger name is kept
            _TR_NAMES = None
            return True
    from katip_redact.textutil import tr_lower
    return tr_lower(word) in _TR_NAMES


_TR_WORDS = re.compile(r"(?i)(?<!\w)(?:ve|ile|bir|bu|için|olarak|olan|veya|göre|ancak|davacı|davalı|"
                       r"mahkemesi|tarihli|sayılı|madde|hakkında|tarafından|nedeniyle|şekilde)(?!\w)")


def _looks_turkish(text: str) -> bool:
    """At least 2% of the words are common Turkish function or legal words, or at least 1% of the letters are
    ı, ğ, ş or İ (rare outside Turkish)."""
    words = max(1, len(text.split()))
    letters = max(1, sum(c.isalpha() for c in text))
    return (len(_TR_WORDS.findall(text)) / words >= 0.02
            or sum(text.count(c) for c in "ığşİĞŞ") / letters >= 0.01)


def _drop_engine_name(s: dict, turkish_text: bool) -> bool:
    """Engine names that are not names in EU text: EU stop words and abbreviations ("BGH", "NL"); and, in a text
    that is not Turkish, guesses of the Turkish name tagger with no Turkish name in them that are one word
    ("Schaden", "Invoice") or hold an abbreviation or a legal word ("DSGVO, EuGH"). In Turkish text every tagger
    name is kept ("Lavin", "Ada")."""
    if s["entity_type"] != "PERSON":
        return False
    words = [w.strip(".,") for w in s["text"].split()]
    if all(w in NOT_NAMES or (w.isupper() and len(w) <= 3) for w in words):
        return True
    if turkish_text or s.get("recognizer") not in ("name_tagger", "tr_person_gazetteer") or \
            any(_turkish_name(w) for w in words):
        return False
    # "DSGVO, EuGH", "Hoge Raad": an abbreviation or a legal word inside the guess
    return len(words) == 1 or any(w in NOT_NAMES or (w.isupper() and len(w) >= 2) or len(w) > 15 for w in words)


def merge(text: str, spans: list[dict], extra: list[dict] | None = None) -> list[dict]:
    """Add EU spans to the engine's spans so that nothing is left half-covered: a span overlapping others is
    merged with them into one span. The merged span takes the id type when one is involved (an IBAN beats the
    name the Turkish rules saw in it), else the type of the longest span."""
    extra = detect(text) if extra is None else extra
    tr = _looks_turkish(text)
    base = [s for s in spans if not _drop_engine_name(s, tr)
            and not (s["entity_type"] == "PLATE" and re.match(r"/\d", text[s["end"]:s["end"] + 2]))]
    out = [dict(s) for s in base]
    for e in sorted(extra, key=lambda s: (s["start"], -(s["end"] - s["start"]))):
        hit = [s for s in out if s["start"] < e["end"] and e["start"] < s["end"]]
        if any(s["start"] <= e["start"] and s["end"] >= e["end"] for s in hit):
            continue  # already covered as a whole
        group = hit + [e]
        a, b = min(s["start"] for s in group), max(s["end"] for s in group)
        ids = [s for s in group if s["entity_type"] in ID_TYPES]
        pick = max(ids or group, key=lambda s: (s["end"] - s["start"], _RANK.get(s["entity_type"], 0)))
        out = [s for s in out if s not in hit]
        out.append({**pick, "id": e.get("id") or f"eu{len(out):04d}", "start": a, "end": b, "text": text[a:b]})
    out = [s for s in out if not (s["entity_type"] == "ADDRESS" and _business_address(text, s["start"]))]
    out = _drop_companies_and_acts(text, out)
    out = _spread_names(text, out)
    out = _widen_names(text, out)
    for i, s in enumerate(sorted(out, key=lambda s: s["start"])):
        s.setdefault("id", f"eu{i:04d}")
    return sorted(out, key=lambda s: s["start"])


COMPANY_FORMS = (r"(?:GmbH(?:\s&\sCo\.\sKG)?|AG|SE|KG|KGaA|OHG|e\.V\.|B\.V\.|BV|N\.V\.|NV|S\.A\.S?|SA|SAS|SARL|S\.à\s?r\.l\.|"
                 r"S\.r\.l\.|Srl|S\.p\.A\.|SpA|S\.L\.U?\.?|SL|S\.A\.U\.|Lda\.?|Ltd\.?|Limited|plc|PLC|LLP|LLC|Inc\.?|"
                 r"ICAV|DAC|UAB|AB|ASA|AS|A/S|ApS|P/S|I/S|Advokatpartnerselskab|Advokatfirma|Oy|Oyj|Sp\.\sz\so\.o\.|s\.r\.o\.|a\.s\.|Kft\.?|Zrt\.?|A\.Ş\.|Ltd\.\sŞti\.)")
_COMPANY_AFTER = re.compile(r"[ \t]*,?[ \t]*(?:(?:&[ \t]*|(?:a|de|del|of|and|ve|und|et|e|y)[ \t]+)?[A-ZÀ-Þ][\w'’&.-]*[ \t]+){0,4}" + COMPANY_FORMS + r"(?![\w])")
_COMPANY_WORDS = set("""Mutua Mutual Mutuelle Seguros Assurances Assicurazioni Verzekeringen Bank Group Holding Holdings Trading Export Import Energy Fund Services Solutions Partners Capital
Logistics Consulting Systems Technologies Software Retail Industries Investments Properties Immobilien Verwaltung
Beteiligungen Arredamenti Tessuti Cerámicas Boulangeries Frères Agro Timber Port Otomotiv Insurance Versicherung
Kanzlei Studio Despacho Cabinet Advocaten Notariaat Stiftung Foundation Fondation Fondazione Fundación Stichting
Verein Association Associazione Asociación Vereniging Universität University Université Università Universidad
Klinik Clinic Hospital Krankenhaus Hôpital Ospedale Hotel Restaurant Café Market Markt Supermarkt
Hukuk Bürosu Barosu Mahkemesi Mahkeme Noterliği Müdürlüğü Dairesi Başsavcılığı Kimlik Şerhi Emlak İnşaat Yapı Ticaret
Izba Izby Izbie Adwokackiej Foro Ordine Colegio Kammer Rechtsanwaltskammer Partner Partners
HUKUK SULH MAHKEMESİ BÜROSU BAROSU NOTERLİĞİ MÜDÜRLÜĞÜ DAİRESİ Tereke TEREKE""".split())
_ACT_BEFORE = re.compile(r"(?i)(?:regulation|directive|decision|implementing decision|verordnung|richtlinie|beschluss|"
                         r"durchführungsbeschluss|règlement|directive|décision|regolamento|direttiva|decisione|"
                         r"reglamento|directiva|decisión|verordening|richtlijn|besluit|uitvoeringsbesluit|"
                         r"d\.\s?lgs\.|d\.\s?l\.|d\.\s?p\.\s?r\.|legge|l\.|law|gesetz|ley|loi|wet|"
                         r"\((?:eu|ue|eg|ce|eu)\)|no\.?|nr\.?)\s*(?:\((?:eu|ue|eg|ce)\)\s*)?(?:no\.?|nr\.?|n[°º.])?\s*$")


def _drop_companies_and_acts(text, spans):
    """A name directly followed by a company form ("Rossi Tessuti S.r.l.", "Deutsche Bank AG") or holding a company
    word is a company, which a DD report needs to read. An EU act number ("Decision (EU) 2021/914") is not a case
    number of the client."""
    out = []
    for s in spans:
        if s["entity_type"] == "PERSON":
            # "Serkan Yıldızhan van Ege Emlak", "Kerem Dalkılıç del Foro": the person ends before "van/del" + institution
            parts = s["text"].split()
            for i in range(2, len(parts)):
                if parts[i].lower() in ("van", "von", "del", "de", "della", "di", "of", "from", "des", "du") and \
                        any(w.strip(".,()") in _COMPANY_WORDS for w in parts[i + 1:i + 4]):
                    cut = s["text"].find(" " + parts[i] + " ")
                    s = {**s, "end": s["start"] + cut, "text": s["text"][:cut]}
                    break
            words = [w.strip(".,()") for w in s["text"].split()]
            if _COMPANY_AFTER.match(text, s["end"]) or any(w in _COMPANY_WORDS for w in words) or \
                    re.search(COMPANY_FORMS + r"$", s["text"]):
                continue
        if s["entity_type"] == "CASE_NO" and _ACT_BEFORE.search(text[max(0, s["start"] - 45):s["start"]]):
            continue
        out.append(s)
    return out


_TR_SUFFIX = r"(?:['’][a-zçğıöşü]{1,6})?"


def _widen_names(text, spans):
    """A masked name never stays half readable: the capitalised name words right after it, and a known first name or
    an initial right before it, join the span ("Wiebke [P]" -> "[P]")."""
    out = []
    for s in sorted(spans, key=lambda s: s["start"]):
        if s["entity_type"] == "PERSON":
            a, b = s["start"], s["end"]
            for _ in range(3):
                m = re.match(r"[ \t]+((?:(?i:" + "|".join(sorted(PARTICLES - {"i", "y", "'t", "e", "et"}, key=len, reverse=True)) +
                             r")[ \t]+)*[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘŞÇĞÖÜİĐΑ-Ω][\w'’-]+)", text[b:])
                if not m or not _is_cap(m.group(1).split()[-1]) or m.group(1).split()[-1] in _FIELD_WORDS or \
                        m.group(1).split()[-1] in _COMPANY_WORDS or m.group(1).split()[-1] in _LABEL_WORDS or \
                        _COMPANY_AFTER.match(text, b + m.end()) or \
                        (len(m.group(1).split()) > 1 and re.match(r"[ \t]+(?:[A-ZÀ-Þ][\w'’-]+[ \t]+){0,2}(?:" +
                                                                   "|".join(_COMPANY_WORDS) + r")\b", text[b + m.end():])):
                    break
                b += m.end()
            g = re.match(r"[ \t]+(?:geb\.|geborene?|née?|z domu|born)[ \t]+([A-ZÀ-ÞŁŚŻŞÇĞÖÜİ][\w'’-]+)", text[b:])
            if g:  # "Gülizar Kaplanoğlu geb. Sert": the birth name is the person too
                b += g.end()
            m = re.search(r"(?<![\w'’-])([A-ZÀ-ÞŁŚŻ][\w'’-]+|[A-ZÀ-Þ]\.)[ \t]+$", text[max(0, a - 30):a])
            if m and (m.group(1) in FIRST_NAMES or _is_initial(m.group(1))):
                a -= len(m.group(0))
            if (a, b) != (s["start"], s["end"]):
                s = {**s, "start": a, "end": b, "text": text[a:b]}
        out.append(s)
    # widening can make spans overlap: join them
    out.sort(key=lambda s: (s["start"], -s["end"]))
    joined = []
    for s in out:
        if joined and s["start"] < joined[-1]["end"]:
            if s["end"] > joined[-1]["end"]:
                if joined[-1]["entity_type"] == "PERSON" and s["entity_type"] == "PERSON":
                    joined[-1] = {**joined[-1], "end": s["end"], "text": text[joined[-1]["start"]:s["end"]]}
                else:
                    joined.append(s)
            continue
        joined.append(s)
    return joined


def _spread_names(text, spans):
    """Every later mention of a masked name is masked too: the full name, the surname alone (also with particles,
    "Van der Heijden", and with a Turkish suffix, "Brennan'ın"), the first name alone, and initial + surname. A
    part that is followed by more capitalised words is widened to the whole name ("Ulrike" -> "Ulrike Oberhuber")."""
    names = [s for s in spans if s["entity_type"] == "PERSON"]
    parts = set()
    for s in names:
        words = [w.strip(".,;:()") for w in s["text"].split()]
        words = [w for w in words if w and w not in TITLES]
        for i, w in enumerate(words):
            if len(w) >= 3 and w[0].isupper() and w not in NOT_NAMES and w not in _DETERMINERS and w not in _FIELD_WORDS \
                    and not _is_initial(w + ".") and w not in AMBIGUOUS_FIRST:
                parts.add(w)
            if w.lower() in PARTICLES and i + 1 < len(words):  # "van der Heijden" as a unit
                j = i
                while j < len(words) and words[j].lower() in PARTICLES:
                    j += 1
                if j < len(words):
                    parts.add(" ".join(words[i:j + 1]))
    if not parts:
        return spans
    out = list(spans)
    covered = lambda a, b: any(x["start"] <= a and x["end"] >= b for x in out)  # noqa: E731
    for part in sorted(parts, key=len, reverse=True):
        pat = re.compile(r"(?<![\w'’-])" + r"\s+".join(re.escape(w) if not w.lower() in PARTICLES else f"(?i:{re.escape(w)})"
                                                     for w in part.split()) + r"(?![\w-])" + _TR_SUFFIX)
        for m in pat.finditer(text):
            a = m.start()
            b = m.start() + len(m.group(0).split("'")[0].split("’")[0])
            if covered(a, b) or _COMPANY_AFTER.match(text, b) or re.match(
                    r"\s+(?:[A-ZÀ-Þ][\w'’-]+\s+){0,2}(?:" + "|".join(_COMPANY_WORDS) + r")\b", text[b:]):
                continue  # "Ferraro Arredamenti S.r.l.": the company keeps its name
            ini = re.search(r"(?:[A-ZÀ-Þ]\.\s?){1,3}$", text[max(0, a - 8):a])
            if ini:
                a -= len(ini.group(0))
            r = _name_at(text, b + 1, max_words=2) if text[b:b + 1] == " " else None
            if r and all(_is_cap(w) for w in text[r[0]:r[1]].split()) and not _COMPANY_AFTER.match(text, r[1]):
                b = r[1]
            hit = [x for x in out if x["start"] < b and a < x["end"]]
            if any(x["entity_type"] != "PERSON" for x in hit):
                continue
            a = min([a] + [x["start"] for x in hit])
            b = max([b] + [x["end"] for x in hit])
            out = [x for x in out if x not in hit]
            out.append({"entity_type": "PERSON", "start": a, "end": b, "text": text[a:b], "score": 0.7,
                        "recognizer": "eu_name_spread", "explanation": f"mention of a masked name ({part})"})
    return out
