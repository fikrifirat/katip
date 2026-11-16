"""Parity corpus: real sample documents plus deterministic fuzz.

The fuzz is aimed at the places where Python and JavaScript differ by default: Turkish dotted/dotless
i under case-insensitive matching, Unicode digits and spaces, CRLF and line separators, characters
outside the BMP (emoji), combining marks, ID numbers with and without valid checksums, wrapped IBANs and
phone numbers, addresses, OCR-style garbling, and every rule's context words.
"""
from __future__ import annotations

import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FIRST = ["Ahmet", "Ayşe", "Mehmet", "Fatma", "Esila", "Ilgın", "İsmail", "Işıl", "Özge", "Çağrı", "Şule", "Ümit", "Emine",
         "Peter", "Madeleine", "Jim", "Olena", "Reza", "Zümra", "Asel", "Kezban", "Elvin", "Irmak", "Can", "Deniz"]
LAST = ["Yılmaz", "YILMAZ", "Kaya", "KAYA", "Boztepe", "Aufschnaiter", "Jonsin", "Topçu", "USLU", "Ülker", "ÇANKAYA",
        "Demir", "Öztürk", "Karaoğlu", "Yiğitalp", "Vardar", "İNCE", "Işık", "Türk", "Şahin"]
CUES = ["Davacı", "Davalı", "Av.", "Sayın", "Müvekkil", "Kiracı", "Tanık", "Sanık", "Kimden:", "Merhaba", "Dr.", "Bilirkişi",
        "Katılımcılar:", "Hazırlayan:", "Vekili", "Alıcı:", "Adı Soyadı:", ""]
AFTER = [" Hanım", " Bey", "'ın", "'e", " tarafından", " adına", " geldi", " oğlu", " ifadesinde", "", "", ""]
STREETS = ["Kızılay Mah.", "Atatürk Cad.", "Gazi Mustafa Kemal Bulvarı", "Fevzi Çakmak Mahallesi", "Alparslan Türkeş Caddesi",
           "1453. Sokak", "Cumhuriyet Mh.", "Bağdat Cd.", "Menekşe Sk."]
PLACES = ["Çankaya/ANKARA", "Kadıköy/İSTANBUL", "Kuşadası/AYDIN", "Konak / İzmir", "Nilüfer BURSA", "Ilgın/KONYA"]
WEIRD = [" ", " ", "　", "\r\n", " ", "\t", "😀", "👩‍⚖️", "𝐀", "é", "i̇", "İ", "ı", "ſ", "K",
         "٣", "１", "ß", "Σ", "ς", "“", "’", "​", "﻿"]
TEMPLATES = [
    "{cue} {name}{after} {date} tarihinde {addr} adresinde ikamet etmektedir.",
    "T.C. Kimlik No: {tckn}\nAdı Soyadı: {name}\nAdres: {addr}\nTel: {phone}\nE-posta: {email}",
    "{name}, {tckn} TC kimlik numaralı, {birth} doğumlu; IBAN: {iban}.",
    "Sayın {name},\n{case} sayılı dosya hk. {plate} plakalı araç.",
    "Yabancı kimlik no {ykn}, Pasaport No: {passport}, Ulusal Kimlik No: {foreign}.",
    "Vergi No: {vkn} Vergi Dairesi: Kavaklıdere; kart {card}; IP {ip}.",
    "Yargıtay 3. Ceza Dairesi'nin 12.03.2019 tarih ve {case} sayılı kararı; {name} ve {name2} dinlendi.",
    "[10:42] {first}: Merhaba {first2}!\n[10:43] {first2}: {first} Hanım, epikriz ve depresyon tedavisi raporu ekte.",
    "İkametgahı  {addr}\nKİMLİK NO {tckn_bad}\nAdı soyadı {name}",
    "Katılımcılar: {name}, {name2} ve {name3}.\n{last} daha sonra {first}'in evine gitti.",
    "Alevi; sendika üyesi; HIV; adli sicil kaydı; parmak izi; cinsel yönelim; Kürt kökenli; parti üyesi.",
    "{name} ({email}) {phone2} numaralı telefondan aradı. UYAP 12345678901 dosya.",
    "ANKARA {n}. ASLİYE HUKUK MAHKEMESİ\nESAS NO: {case}\nDAVACI : {name_caps}\nVEKİLİ : Av. {name}\nBaro Sicil No: 12345",
]


def _tckn(rng: random.Random, valid: bool = True, start: str | None = None) -> str:
    while True:
        d = [int(start)] if start else [rng.randint(1, 9)]
        d += [rng.randint(0, 9) for _ in range(9 - len(d))]
        if start == "99":
            d = [9, 9] + [rng.randint(0, 9) for _ in range(7)]
        d10 = ((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10
        d.append(d10)
        d.append(sum(d) % 10)
        s = "".join(map(str, d))
        if valid:
            return s
        bad = s[:10] + str((d[10] + 1) % 10)
        return bad


def _iban(rng: random.Random) -> str:
    bban = "".join(str(rng.randint(0, 9)) for _ in range(22))
    num = int("".join(str(int(c, 36)) for c in bban + "TR00"))
    chk = 98 - num % 97
    s = f"TR{chk:02d}{bban}"
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4)) if rng.random() < 0.6 else s


def _luhn(rng: random.Random) -> str:
    d = [4] + [rng.randint(0, 9) for _ in range(14)]
    total = 0
    for i, x in enumerate(reversed(d)):
        y = x * 2 if i % 2 == 0 else x
        total += y - 9 if y > 9 else y
    d.append((10 - total % 10) % 10)
    s = "".join(map(str, d))
    return " ".join(s[i:i + 4] for i in range(0, 16, 4))


def _vkn(rng: random.Random) -> str:
    while True:
        d = [rng.randint(0, 9) for _ in range(9)]
        total = 0
        for i in range(9):
            tmp = (d[i] + (9 - i)) % 10
            v = (tmp * 2 ** (9 - i)) % 9
            if tmp != 0 and v == 0:
                v = 9
            total += v
        return "".join(map(str, d)) + str((10 - total % 10) % 10)


def fuzz_doc(rng: random.Random) -> str:
    def name():
        return rng.choice(FIRST) + " " + rng.choice(LAST)
    parts = []
    for _ in range(rng.randint(2, 6)):
        t = rng.choice(TEMPLATES)
        parts.append(t.format(
            cue=rng.choice(CUES), name=name(), name2=name(), name3=name(), name_caps=name().upper(),
            first=rng.choice(FIRST), first2=rng.choice(FIRST), last=rng.choice(LAST), after=rng.choice(AFTER),
            date=f"{rng.randint(1, 28):02d}.{rng.randint(1, 12):02d}.20{rng.randint(10, 26)}",
            birth=f"{rng.randint(1, 28)}/{rng.randint(1, 12)}/19{rng.randint(50, 99)}",
            addr=f"{rng.choice(STREETS)} {rng.choice(STREETS)} No:{rng.randint(1, 120)} D:{rng.randint(1, 30)} {rng.choice(PLACES)}",
            tckn=_tckn(rng), tckn_bad=_tckn(rng, valid=False), ykn=_tckn(rng, start="99"),
            phone=rng.choice(["0532 123 45 67", "+90 (212) 555 12 34", "0 312 444\n12 12", "5321234567", "0090 532-111-22-33"]),
            phone2=rng.choice(["532 123 45 67", "0532 1234567"]),
            email=rng.choice(["ahmet.yilmaz@gmail.com", "info@firma.com.tr", "esila_boztepe85@hotmail.com", "a.kaya ® outlook.com"]),
            iban=_iban(rng), plate=rng.choice(["06 ABC 123", "34 AB 1234", "35 K 12345", "06 TL 100"]),
            case=f"20{rng.randint(10, 26)}/{rng.randint(1, 9999)} E.", passport=rng.choice(["U12345678", "C01X00T47"]),
            foreign=rng.choice(["AB1234567", "123-456789-0"]), vkn=_vkn(rng), card=_luhn(rng),
            ip=f"192.168.{rng.randint(0, 255)}.{rng.randint(0, 255)}", n=rng.randint(1, 30)))
    text = "\n\n".join(parts)
    # sprinkle troublemakers
    chars = list(text)
    for _ in range(rng.randint(0, 8)):
        chars.insert(rng.randrange(len(chars) + 1), rng.choice(WEIRD))
    text = "".join(chars)
    if rng.random() < 0.3:
        text = text.upper() if rng.random() < 0.5 else text.lower()
    return text


def mutate(text: str, rng: random.Random) -> str:
    """A real document with small edits: case flips, swapped characters, inserted troublemakers."""
    chars = list(text)
    for _ in range(max(1, len(chars) // 400)):
        i = rng.randrange(len(chars))
        op = rng.random()
        if op < 0.3:
            chars[i] = chars[i].upper() if chars[i].islower() else chars[i].lower()
        elif op < 0.6:
            chars.insert(i, rng.choice(WEIRD))
        elif op < 0.8 and i + 1 < len(chars):
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
        else:
            del chars[i]
    return "".join(chars)


def corpus(n_fuzz: int = 300, seed: int = 20261115) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    docs = [(p.name, p.read_text(encoding="utf-8")) for p in sorted((ROOT / "docs" / "samples").glob("*.txt"))]
    out = list(docs)
    for name, t in docs:
        out.append((name + "~mut", mutate(t, rng)))
    for i in range(n_fuzz):
        out.append((f"fuzz-{i:04d}", fuzz_doc(rng)))
    return out
