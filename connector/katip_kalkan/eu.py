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
           "social security", "ssn", "tax id", "tin", "id number", "identity number", "citizen service number")

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
    ("bsn", re.compile(r"(?<![\w./-])(?<!\d\s)(\d{4}\.\d{2}\.\d{3}|\d{3}[.\s]\d{3}[.\s]\d{3}|\d{9})(?![\w/-]|[.\s]\d)"), bsn_valid),
]
# a number right after an ID cue: masked even when no checksum fits (fail closed)
_CUED = re.compile(r"(?i)\b(?:" + "|".join(re.escape(c) for c in sorted(ID_CUES, key=len, reverse=True)) +
                   r")(?!\w)[^\d\n]{0,30}?"
                   r"(?-i:((?=[A-Z0-9 .-]{6,24}(?![\w]))(?<![\w])[A-Z0-9](?:[ .-]?[A-Z0-9]){5,19}))(?![\w])")


def find_national_ids(text):
    out, taken = [], []
    for name, rx, ok in _ID_RES:
        for m in rx.finditer(text):
            a, b = m.span(1)
            if any(x < b and a < y for x, y in taken):
                continue
            cue = any(c in _before(text, a) for c in ID_CUES)
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


def find_phones(text):
    out = [_span("PHONE", *m.span(1), text, 0.9, "eu_phone", "international number") for m in _PHONE_INTL.finditer(text)]
    out += [_span("PHONE", *m.span(1), text, 0.85, "eu_phone_cue", "number after a phone cue")
            for m in _PHONE_CUE.finditer(text)]
    return out


_DOC = re.compile(
    r"(?i)\b(passport|reisepass|pass(?:nummer|-nr)|passeport|passaporto|pasaporte|paspoort|paszport|"
    r"personalausweis|ausweis(?:nummer)?|carte d'identité|carte nationale d'identité|cni|carta d'identità|"
    r"documento de identidad|identiteitskaart|id-kaart|dowód osobisty|identity card|id card|driving licen[cs]e|"
    r"driver's license|führerschein|permis de conduire|patente|permiso de conducir|rijbewijs|document number|"
    r"residence permit|aufenthaltstitel|titre de séjour)\b[^\w\n]{0,4}(?:(?:(?:no|nr|number|nummer|numéro|numero|número|"
    r"num)\b\.?|n[°º]|n\.º?)[^\w\n]{0,4})?([A-Z0-9](?:[ -]?[A-Z0-9]){5,13})(?![\w])")


def find_documents(text):
    out = []
    for m in _DOC.finditer(text):
        if not re.search(r"\d", m.group(2)):
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
_DATE = rf"(?:\d{{1,2}}[./-]\d{{1,2}}[./-](?:19|20)?\d{{2}}|(?:19|20)\d{{2}}-\d{{2}}-\d{{2}}|\d{{1,2}}(?:er|º)?\.? (?:de )?(?:{MONTHS}) (?:de )?(?:19|20)\d{{2}}|(?:{MONTHS}) \d{{1,2}},? (?:19|20)\d{{2}})"
_DOB = re.compile(r"(?i)\b(?:born(?: on)?|date of birth|d\.?o\.?b\.?|birth ?date|geboren(?: am)?|geb\.|geburtsdatum|"
                  r"née? le|né\(e\) le|née?|date de naissance|nato il|nata il|nato a \w+ il|nata a \w+ il|"
                  r"data di nascita|nacid[oa] el|nacid[oa] en \w+ el|fecha de nacimiento|geboortedatum|"
                  r"urodzon[ya]|data urodzenia)(?!\w)[^\w\n]{0,4}(?:(?:on|am|op|le|il|el|en)\s+)?(" + _DATE + r")", re.I)


def find_birth_dates(text):
    return [_span("BIRTH_DATE", *m.span(1), text, 0.9, "eu_birth_date", "date after a birth cue")
            for m in _DOB.finditer(text)]


# ---------------------------------------------------------------- addresses

_W = r"[^\W\d_][\w'’.-]*"  # a word (letters first)
_STREET = re.compile(
    "|".join([
        # DE / AT / CH / NL compounds: Hauptstraße 5, Keizersgracht 123-III, Am Markt 3
        rf"(?:\b[A-ZÄÖÜ][\w'’-]*(?:straße|strasse|str\.|weg|platz|allee|gasse|ring|damm|ufer|chaussee|steig|"
        rf"straat|laan|gracht|plein|kade|singel|dijk|steeg))\s+\d{{1,4}}(?:\s?[a-zA-Z]\b|-\w{{1,4}})?",
        # DE: Am Rosengarten 5, An der Alster 12, Im Tal 3
        rf"\b(?:Am|An der|An den|Im|In der|Auf der|Auf dem|Zum|Zur|Unter den|Hinter der)\s+[A-ZÄÖÜ][\w'’-]+\s+\d{{1,4}}"
        rf"(?:\s?[a-zA-Z]\b)?",
        # IT / ES / PT / CA: Via Roma 12, Calle Mayor, 5; Avenida da Liberdade 110
        rf"\b(?:Via|Viale|Piazza|Piazzale|Corso|Largo|Vicolo|Calle|C/|Avenida|Avda\.|Plaza|Paseo|Carrer|Rua|"
        rf"Travessa|Ronda|Camino)\s+(?:{_W}\s+){{0,4}}?{_W},?\s+(?:n\.?\s?|nº\s?)?\d{{1,4}}(?:\s?[a-zA-Z]\b|/\w+)?",
        # FR: 12 rue de la Paix, 5 bis avenue Foch
        rf"\b\d{{1,4}}(?:\s?(?:bis|ter|[a-z]\b))?,?\s+(?:rue|avenue|av\.|boulevard|bd|place|chemin|allée|allee|"
        rf"impasse|quai|cours|route|square)\s+(?:(?:de|du|des|la|le|l['’]|d['’])\s*)*[A-ZÀ-Þ][\w'’-]*"
        rf"(?:\s+(?:(?:de|du|des|la|le|l['’]|d['’])\s*)*[A-ZÀ-Þ][\w'’-]*){{0,3}}",
        # EN: 221B Baker Street, 10 Downing St.
        rf"(?:\b(?:Flat|Apt\.?|Apartment|Unit|Suite)\s+\d{{1,4}}[A-Za-z]?,?\s+)?\b\d{{1,4}}[A-Za-z]?,?\s+(?:[A-Z][\w'’-]*\s+){{1,3}}(?:Street|St\.|Road|Rd\.|Avenue|Ave\.|Lane|Drive|"
        rf"Close|Way|Place|Square|Crescent|Terrace|Gardens|Row|Mews|Hill|Park)\b",
    ]))
# what may follow a street on the same line: a postcode and the town
_POSTCODE_TOWN = re.compile(r",?\s{1,3}(?:(?:[A-Z]{1,2}-)?(?:\d{5}|\d{4}\s?[A-Z]{2}|\d{4}|\d{2}-\d{3}|[A-Z]{1,2}\d[A-Z\d]?\s\d[A-Z]{2})"
                            r"(?:\s+[A-ZÀ-Þ][\w'’-]+(?:[\s-][A-ZÀ-Þ][\w'’-]+){0,2})?"
                            # UK / IE: town first, then a district number or a postcode
                            r"|[A-ZÀ-Þ][a-zà-ÿ'’-]+(?:\s(?:\d{1,2}(?!\d)|[A-Z]{1,2}\d[A-Z\d]?\s\d[A-Z]{2}))?(?=[\s,.;)]|$))")


def find_addresses(text):
    out = []
    for m in _STREET.finditer(text):
        a, b = m.span()
        t = _POSTCODE_TOWN.match(text, b)
        if t and t.end() > b:
            b = t.end()
        out.append(_span("ADDRESS", a, b, text, 0.85, "eu_street", "street and house number"))
    return out


# ---------------------------------------------------------------- names

TITLES = ("Mr", "Mrs", "Ms", "Miss", "Mx", "Dr", "Prof", "Sir", "Dame", "Lord", "Lady", "Herr", "Herrn", "Frau", "Hr", "Fr",
          "M", "Mme", "Mlle", "MM", "Me", "Maître", "Sig", "Sig.ra", "Sig.na", "Sigg", "Dott", "Dott.ssa", "Avv",
          "Ing", "Sr", "Sra", "Srta", "D", "Dª", "Dña", "Don", "Doña", "dhr", "mevr", "mw", "Dhr", "Mevr", "Mw",
          "De heer", "Mevrouw", "Pan", "Pani", "mr", "Mag", "Dipl.-Ing", "RA", "RAin", "Rechtsanwalt", "Rechtsanwältin",
          "Notar", "Notarin", "Avocat", "Avocate", "Abogado", "Abogada", "Avvocato", "Advocaat")
_TITLE = re.compile(r"(?<![\w.])(?:" + "|".join(re.escape(t) for t in sorted(TITLES, key=len, reverse=True)) +
                    r")(?:\.|\b)\s+(?=[A-ZÀ-ÞŁŚŻŹĆŃŠŽČŘ])")
PARTICLES = {"von", "van", "der", "den", "de", "del", "della", "degli", "di", "da", "dos", "das", "do", "du", "des",
             "la", "le", "y", "i", "zu", "ter", "ten", "af", "av", "bin", "al", "el", "'t", "op"}
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
Your Our Ihre Ihr Unsere Unser Die Der Das Le La Les Il Lo Gli El Los Las De Het Votre Notre Vostro Nostro Su Uw Ons
No Nr Number Page Seite Annex Schedule Section Chapter Part Data Subject Personal Name Address Phone Email""".split())
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
            if not words or len(tok) > 2:
                break
            i = m.end()
            continue
        w = tok
        if _is_initial(w):
            words.append(w)
        elif w.rstrip(".").lower() in PARTICLES and words or (w.lower() in PARTICLES and not need_cap_first):
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
""".split())
# given names that are also everyday words: only with a title or a cue
AMBIGUOUS_FIRST = {"Mark", "Grace", "Rose", "Will", "May", "Bill", "Art", "Bruno", "Tom", "Max", "Rita", "Ben",
                   "Jack", "Iris", "Paula", "Saga", "Alba", "Rosa", "Teresa", "Martin", "Victoria", "Carmen"}
_FIRST = re.compile(r"(?<![\w.'’-])(" + "|".join(sorted(FIRST_NAMES - AMBIGUOUS_FIRST, key=len, reverse=True)) +
                    r")(?=[\s-]+(?:(?:" + "|".join(sorted(PARTICLES - {"i", "y"}, key=len, reverse=True)) +
                    r")\s+)*[A-ZÀ-Þ])")
_FIELD = re.compile(
    r"(?im)^[ \t]*(?:full name|name|surname|first name|last name|given names?|family name|nom|prénom|nom de famille|"
    r"name des|nachname|vorname|geburtsname|nome|cognome|nombre|apellidos?|naam|achternaam|voornaam|imię|nazwisko|"
    r"data subject|employee|employer|client|customer|patient|tenant|landlord|claimant|applicant|respondent|witness|"
    r"contact person|signed|signatory|mandant(?:in)?|kläger(?:in)?|beklagte[rn]?|zeuge|zeugin|demandeur|défendeur|"
    r"témoin|attore|convenuto|ricorrente|testimone|demandante|demandado|testigo|eiser|gedaagde|getuige)"
    r"[ \t]*:[ \t]*(?=\S)")
_CLOSING = re.compile(
    r"(?im)(?:kind regards|best regards|warm regards|regards|yours sincerely|yours faithfully|sincerely|"
    r"mit freundlichen grüßen|mit freundlichen gruessen|viele grüße|beste grüße|freundliche grüße|cordialement|"
    r"bien à vous|bien cordialement|salutations distinguées|cordiali saluti|distinti saluti|un cordiale saluto|"
    r"atentamente|un saludo|saludos cordiales|met vriendelijke groet(?:en)?|hoogachtend|pozdrawiam|z poważaniem|"
    r"com os melhores cumprimentos|atenciosamente)[,.]?[ \t]*\n+[ \t]*(?=\S)")


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


# ---------------------------------------------------------------- entry points

def detect(text: str) -> list[dict]:
    """Every EU span this module finds; overlaps between them are left to merge()."""
    return (find_iban(text) + find_vat(text) + find_national_ids(text) + find_documents(text) + find_phones(text)
            + find_birth_dates(text) + find_addresses(text) + find_names(text))


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
    if turkish_text or s.get("recognizer") != "name_tagger" or any(_turkish_name(w) for w in words):
        return False
    # "DSGVO, EuGH", "Hoge Raad": an abbreviation or a legal word inside the guess
    return len(words) == 1 or any(w in NOT_NAMES or (w.isupper() and len(w) >= 2) for w in words)


def merge(text: str, spans: list[dict], extra: list[dict] | None = None) -> list[dict]:
    """Add EU spans to the engine's spans so that nothing is left half-covered: a span overlapping others is
    merged with them into one span. The merged span takes the id type when one is involved (an IBAN beats the
    name the Turkish rules saw in it), else the type of the longest span."""
    extra = detect(text) if extra is None else extra
    tr = _looks_turkish(text)
    base = [s for s in spans if not _drop_engine_name(s, tr)]
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
    for i, s in enumerate(sorted(out, key=lambda s: s["start"])):
        s.setdefault("id", f"eu{i:04d}")
    return sorted(out, key=lambda s: s["start"])
