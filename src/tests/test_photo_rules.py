"""Rules for photographed, hand-filled forms, on synthetic text (OCR-like where it says so).

  python src/tests/test_photo_rules.py [docs/katip_py.zip]
"""
import sys, tempfile, zipfile
from pathlib import Path

zp = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parents[2] / "docs/katip_py.zip")
tmp = tempfile.mkdtemp()
zipfile.ZipFile(zp).extractall(tmp)
sys.path.insert(0, tmp)
import local_detect  # noqa: E402


def found(text, ocr=False, **kw):
    return [(s["entity_type"], s["text"]) for s in local_detect.detect(text, threshold=0.7, ocr_ranges=[(0, len(text))] if ocr else (), **kw)]


FORM = """Kiraya verenin
Adı soyadı Hüsnü KARABULUT
Kiraya verenin T.C. Kimlik No. 12345678950 Vergi Nosu
Kiraya verenin Ege Mah. Alparslan Türkeş Cad. 707 Sk. Trend Royal-1 A Blok D:25 Kuşadası/AYDIN
Kiracının
Muylafa YAVAS
"""


def test_street_names_stay_visible():
    f = found(FORM)
    assert ("ADDRESS", "Trend Royal-1 A Blok D:25") in f, f
    assert not any("Alparslan" in t or "Ege" == t for _, t in f), f
    assert ("ADDRESS", "No: 12") in found("Adres: Atatürk Bulvarı No: 12 Çankaya/ANKARA")
    assert found("Fevzi Çakmak Caddesi üzerinde yürüdü.") == []  # a street alone is not personal data


def test_full_address_mode():
    f = found(FORM, address_detail="full")
    assert ("ADDRESS", "Ege Mah. Alparslan Türkeş Cad. 707 Sk. Trend Royal-1 A Blok D:25 Kuşadası/AYDIN") in f, f


def test_names_after_form_labels():
    assert ("PERSON", "Muylafa YAVAS") in found(FORM)
    assert ("PERSON", "Hüsnü KARABULUT") in found(FORM)


def test_ocr_tckn_checksum_failed():
    t = "Kiracının\nFEümiK no, 54709112308 Yergi Nosu"
    assert ("TCKN", "54709112308") in found(t, ocr=True)
    assert ("TCKN", "54709112308") not in found(t)  # born-digital text: an invalid 11-digit number is not an ID
    assert not any(e == "TCKN" for e, _ in found("UYAP 12345678901 numaralı dosya", ocr=True))
    iban = "TR33 0006 1005 1978 6457 8413 26"
    assert not any(e == "TCKN" for e, _ in found(f"IBAN {iban}", ocr=True))


def test_ocr_name_repeats():
    t = "Kiraya verenin\nMuylafa YAVAS\nKiracı Kiraya Veren\nmb7 YAVAŞ\n"
    f = found(t, ocr=True)
    assert ("PERSON", "YAVAŞ") in f, f


def test_amount_in_words_is_not_a_name():
    assert not any(e == "PERSON" for e, _ in found("Yazı İle Ali Yaz Bia TL", ocr=True))


def test_ocr_misread_street_word():
    f = found("İkametgahı Ege Meh. Alpecslan Tückes Cad. 707 Sk. Tend Fopl-1 A Blok D:5 Kuşadası/AYDIN", ocr=True)
    assert not any(t.startswith("Ege") for _, t in f), f


if __name__ == "__main__":
    fails = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_"):
            try:
                fn(); print("ok  ", k)
            except AssertionError as e:
                fails += 1; print("FAIL", k, e)
    sys.exit(1 if fails else 0)
