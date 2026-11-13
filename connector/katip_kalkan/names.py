"""File names can be personal data ("Ayşe Kaya - epikriz.pdf"), and detection on a short name misses
foreign names, so the model only ever gets *safe* names: words from a small legal vocabulary and
numbers stay, every other word becomes "…". Files are referred to by an id instead of a path."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

# Words safe to show, compared without Turkish diacritics. Stems of 5+ letters also match with a suffix
# ("dilekçesi"); shorter words and words that are also given names ("Miras") must match exactly.
STEMS = """dilekce kontrat sozlesme vekalet epikriz rapor bilirkisi ihtar karar tutanak vatandas bosanma
nafaka velayet iflas fatura makbuz dekont ihbar sikayet savunma beyan cevap itiraz istinaf temyiz
bozma durusma kesif tensip gerekce hukum tebligat mahkeme noter tazminat alacak senet protesto ipotek
haciz tahliye mulkiyet veraset vasiyet tereke nufus kayit ornek kimlik pasaport ikamet calisma
oturma sigorta bordro ihale teklif sartname protokol ibraname taahhut belge evrak tarama fotograf
sayfa taslak nihai kopya maskeli imzali onayli dosya notlar muvekkil bilgi basvuru delil liste suret
hakkinda takip""".split()
EXACT = set("""dava davasi kira kirasi icra tapu tapusu ceza hukuk is isci borc cek ek ekler eki
yeni eski not form formu foto scan imza ozet yazi talep sgk ve ile icin hk""".split())
FOLD = str.maketrans("çğıöşüâîûÇĞİIÖŞÜÂÎÛ", "cgiosuaiuCGIIOSUAIU")


def _fold(w: str) -> str:
    return unicodedata.normalize("NFC", w).translate(FOLD).lower()


def safe_title(stem: str) -> str:
    out = []
    for tok in re.split(r"(\W+)", unicodedata.normalize("NFC", stem.replace("_", " "))):
        if not tok or re.fullmatch(r"\W+", tok) or re.fullmatch(r"[\d.]+|v\d+", tok, re.I):
            out.append(tok)
        elif _fold(tok) in EXACT or (len(tok) <= 20 and any(_fold(tok).startswith(s) for s in STEMS)):
            out.append(tok)
        else:
            out.append("…")
    return re.sub(r"(…\s*)+…", "…", "".join(out)).strip()


def file_id(p: Path) -> str:
    return "f-" + hashlib.sha256(unicodedata.normalize("NFC", str(p)).encode()).hexdigest()[:10]
