"""Synthetic identity numbers of foreign clients, with the phrases Turkish petitions put around them.

Every value is generated (random digits with the right shape and, where one exists, a valid checksum); none
belongs to a real person.

  YKN          Yabancı Kimlik No: 11 digits starting with 99, TCKN checksum (residence permit, work permit,
               temporary protection)
  PASSPORT     passport numbers in the shape each country issues (approximate; good enough to test cue-based
               detection, not to validate a document)
  FOREIGN_ID   home-country national ID numbers (Iran's kod-e melli has a check digit; others are shape only)

  ykn(rng) -> "99123456782"
  passport(rng, country) -> "U12345678"
  national_id(rng, country) -> ("Kod-e Melli", "0012345679")
  id_phrase(rng, group) -> (text, [(start, end, TYPE)])   e.g. "Pasaport No: U12345678"
"""
from __future__ import annotations

import random, string

D = string.digits
U = string.ascii_uppercase

def _digits(rng, n): return "".join(rng.choice(D) for _ in range(n))

def tckn_checksum(first9: str) -> str:
    n = [int(c) for c in first9]
    d10 = ((n[0] + n[2] + n[4] + n[6] + n[8]) * 7 - (n[1] + n[3] + n[5] + n[7])) % 10
    d11 = (sum(n) + d10) % 10
    return first9 + str(d10) + str(d11)

def ykn(rng) -> str:
    return tckn_checksum("99" + _digits(rng, 7))

def iran_melli(rng) -> str:
    d = _digits(rng, 9)
    s = sum(int(d[i]) * (10 - i) for i in range(9)) % 11
    return d + str(s if s < 2 else 11 - s)

def luhn_complete(d: str) -> str:
    for c in D:
        x = d + c; s, alt = 0, False
        for ch in reversed(x):
            v = int(ch)
            if alt:
                v *= 2
                if v > 9: v -= 9
            s += v; alt = not alt
        if s % 10 == 0: return x
    return d + "0"

# country -> passport shape. L = letter, D = digit, A = letter or digit
PASSPORT_SHAPE = {
    "Suriye": ["DDDDDDDDD", "NDDDDDDDD"], "Irak": ["LDDDDDDDD"], "İran": ["LDDDDDDDD"], "Afganistan": ["PDDDDDDD", "ODDDDDDD"],
    "Gürcistan": ["DDLLDDDDD"], "Ermenistan": ["LLDDDDDDD"], "Yunanistan": ["LLDDDDDDD"], "Rusya Federasyonu": ["DDDDDDDDD", "DD DDDDDDD"],
    "Ukrayna": ["LLDDDDDD"], "Azerbaycan": ["CDDDDDDDD"], "Amerika Birleşik Devletleri": ["DDDDDDDDD", "ADDDDDDDD"],
    "Almanya": ["CAAAAAAAA"], "Fransa": ["DDLLDDDDD"], "İngiltere": ["DDDDDDDDD"], "İtalya": ["LLDDDDDDD"], "İspanya": ["LLLDDDDDD"],
    "Hollanda": ["LLAAAAAAD"], "Ürdün": ["LDDDDDD"], "Lübnan": ["LRDDDDDDD"], "Mısır": ["ADDDDDDDD"], "Suudi Arabistan": ["LDDDDDDD"],
    "Libya": ["DDDDDDDD"], "Filistin": ["DDDDDDDD"],
}
_PASS_LETTERS = "CFGHJKLMNPRTVWXYZ"

def passport(rng, country: str) -> str:
    shape = rng.choice(PASSPORT_SHAPE.get(country, ["LDDDDDDDD"]))
    out = []
    for c in shape:
        if c == "D": out.append(rng.choice(D))
        elif c == "L": out.append(rng.choice(U))
        elif c == "A": out.append(rng.choice(_PASS_LETTERS + D))
        else: out.append(c)                        # literal (N, P, C, R ...)
    s = "".join(out)
    while sum(ch.isdigit() for ch in s) < 5:   # IDs carry digits; turn a random letter (not the first) into one
        k = rng.choice([i for i, ch in enumerate(s) if i and not ch.isdigit()]); s = s[:k] + rng.choice(D) + s[k + 1:]
    return s

def national_id(rng, country: str):
    """(name of the number as written in a Turkish petition, value)"""
    r = rng.random
    if country == "İran": return rng.choice(["Kod-e Melli", "İran Ulusal Kimlik No", "Ulusal Kimlik Kodu", "National Code"]), iran_melli(rng)
    if country == "Suriye": return rng.choice(["Suriye Ulusal Numarası", "Ulusal Numara", "National No"]), _digits(rng, 11)
    if country == "Irak": return rng.choice(["Irak Ulusal Kimlik No", "Ulusal Kimlik Kartı No"]), _digits(rng, 12)
    if country == "Afganistan": return rng.choice(["Tazkira No", "Tezkire No", "e-Tazkira No"]), f"{_digits(rng, 4)}-{_digits(rng, 4)}-{_digits(rng, 5)}"
    if country == "Gürcistan": return rng.choice(["Kişisel Numarası (Personal No)", "Personal No", "Gürcistan Kişisel No"]), _digits(rng, 11)
    if country == "Ermenistan": return rng.choice(["Sosyal Kart No", "Kamu Hizmet Numarası", "Ermenistan Kimlik Kartı No"]), _digits(rng, 10)
    if country == "Yunanistan": return rng.choice([("AMKA", luhn_complete(_digits(rng, 10))), ("Kimlik Kartı No", f"{rng.choice('ABEZHIKMNOPTYX')}{rng.choice('ABEZHIKMNOPTYX')} {_digits(rng, 6)}")])
    if country == "Rusya Federasyonu": return rng.choice(["İç Pasaport No", "Rusya Kimlik No"]), f"{_digits(rng, 2)} {_digits(rng, 2)} {_digits(rng, 6)}"
    if country == "Ukrayna": return rng.choice(["Vergi Kimlik No (RNOKPP)", "Ukrayna Kimlik No", "ID Kart No"]), _digits(rng, 10 if r() < .5 else 9)
    if country == "Azerbaycan": return rng.choice(["FİN Kod", "FIN", "Şəxsiyyət vəsiqəsi FİN"]), "".join(rng.choice(U + D) for _ in range(7))
    if country == "Amerika Birleşik Devletleri": return rng.choice(["SSN", "Sosyal Güvenlik No (SSN)", "Social Security No"]), f"{rng.randint(100, 899)}-{_digits(rng, 2)}-{_digits(rng, 4)}"
    if country == "Almanya": return rng.choice(["Personalausweis-Nr.", "Kimlik Kartı No", "Ausweisnummer"]), "".join(rng.choice(_PASS_LETTERS + D) for _ in range(9))
    if country == "Fransa": return rng.choice(["Kimlik Kartı No (CNI)", "N° CNI", "Numéro de sécurité sociale"]), _digits(rng, 12)
    if country == "İngiltere": return rng.choice(["National Insurance No", "NI No"]), f"{rng.choice('ABCEGHJKLMNOPRSTWXYZ')}{rng.choice('ABCEGHJKLMNPRSTWXYZ')} {_digits(rng, 2)} {_digits(rng, 2)} {_digits(rng, 2)} {rng.choice('ABCD')}"
    if country == "İtalya": return "Codice Fiscale", "".join(rng.choice(U) for _ in range(6)) + _digits(rng, 2) + rng.choice(U) + _digits(rng, 2) + rng.choice(U) + _digits(rng, 3) + rng.choice(U)
    if country == "İspanya": return rng.choice(["DNI", "NIE"]), _digits(rng, 8) + rng.choice("TRWAGMYFPDXBNJZSQVHLCKE")
    if country == "Hollanda": return rng.choice(["BSN", "Burgerservicenummer"]), _digits(rng, 9)
    return rng.choice(["Ulusal Kimlik No", "National ID No", "Kimlik Kartı No"]), _digits(rng, rng.choice([9, 10, 12]))

def id_phrase(rng, country: str):
    """One identity statement for a foreign person, with gold spans. Returns (text, [(a, b, TYPE)])."""
    r = rng.random()
    if r < .45:
        v = ykn(rng)
        t = rng.choice(["Yabancı Kimlik No: {v}", "YKN: {v}", "Y.K.N.: {v}", "{v} yabancı kimlik numaralı", "Yabancı Kimlik Numarası {v}",
                        "Geçici Koruma Kimlik No: {v}", "Yabancı Kimlik No:{v}", "Kimlik No: {v}"]); typ = "YKN"
    elif r < .8:
        v = passport(rng, country)
        t = rng.choice(["Pasaport No: {v}", "{v} numaralı pasaport", "Pasaport Numarası: {v}", "pasaport no {v}", "Passport No: {v}",
                        "{c} Pasaportu No: {v}", "Pasaport No.: {v}", "{v} sayılı pasaportu"]); typ = "PASSPORT"
    else:
        name, v = national_id(rng, country)
        t = rng.choice(["{n}: {v}", "{n} {v}", "{c} {n}: {v}" if not name.startswith(country) else "{n}: {v}"]); typ = "FOREIGN_ID"
        t = t.replace("{n}", name)
    t = t.replace("{c}", country)
    a = t.index("{v}"); text = t.replace("{v}", v)
    return text, [(a, a + len(v), typ)]
