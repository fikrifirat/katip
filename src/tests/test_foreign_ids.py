"""Rules for foreign clients: YKN, passports, home-country IDs, and law titles that are not names. Synthetic text only.

  python src/tests/test_foreign_ids.py [docs/katip_py.zip]
"""
import sys, tempfile, zipfile
from pathlib import Path

zp = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parents[2] / "docs/katip_py.zip")
tmp = tempfile.mkdtemp()
zipfile.ZipFile(zp).extractall(tmp)
sys.path.insert(0, tmp)
import local_detect  # noqa: E402


def found(text, **kw):
    return [(s["entity_type"], s["text"]) for s in local_detect.detect(text, **kw)]


def test_ykn_is_labelled_as_foreigner_id():
    assert ("YKN", "99104332124") in found("Davacı : Ali Rıza Karimi (Yabancı Kimlik No: 99104332124)")


def test_tckn_stays_tckn():
    assert ("TCKN", "12345678950") in found("Davalı Ahmet Kaya (T.C. Kimlik No: 12345678950)")


def test_passport_after_and_before_cue():
    assert ("PASSPORT", "U12345678") in found("Pasaport No: U12345678 ile giriş yapmıştır.")
    assert ("PASSPORT", "K12345678") in found("K12345678 numaralı pasaportu ile")
    assert ("PASSPORT", "QC0888422") in found("(Pasaport Numarası: QC0888422)")


def test_passport_mrz():
    f = found("P<IRNKARIMI<<ALI<REZA<<<<<<<<<<<<<<<<<<<<<<<<\nK123456780IRN9001014M3001019<<<<<<<<<<<<<<02")
    assert any(t == "PASSPORT" for t, _ in f) and any(t == "PERSON" for t, _ in f), f


def test_foreign_national_ids():
    assert ("FOREIGN_ID", "1400-0101-12345") in found("Tazkira No: 1400-0101-12345")
    assert ("FOREIGN_ID", "123-45-6789") in found("SSN: 123-45-6789")
    assert ("FOREIGN_ID", "5ZK3J9A") in found("FİN Kod: 5ZK3J9A")
    assert ("FOREIGN_ID", "0012345679") in found("Kod-e Melli 0012345679 olan müvekkil")   # Iranian check digit ok


def test_file_numbers_are_not_ids():
    assert not found("Esas No: 2023/12345 Karar No: 2024/55. Pasaportun süresi dolmuştur.")


def test_law_titles_are_not_names():
    f = found("5091 sayılı Türk Vatandaşlığı Kanunu ve 4721 sayılı Türk Medenî Kanununa göre davacı Ahmet Türk")
    assert ("PERSON", "Ahmet Türk") in f and all(t != "PERSON" or n == "Ahmet Türk" for t, n in f), f


def test_foreign_cities_are_not_names():
    assert not any(t == "PERSON" for t, _ in found("Müvekkil Halep doğumludur. Tiflis Büyükelçiliği ve Tahran Başkonsolosluğu ile yazışılmıştır."))



def test_ikamet_paragraph_is_not_a_form_address():
    t = "\tİkamet şartına bakıldığında, müvekkilimin başvuru tarihinde yaklaşık yedi senedir ülkede ikamet ettiği anlaşılmaktadır."
    assert not any(e == "ADDRESS" for e, _ in found(t)), found(t)
    assert any(e == "ADDRESS" for e, _ in found("İkametgahı  Trend Royal-1 A Blok D:25 Kuşadası/AYDIN"))


if __name__ == "__main__":
    fails = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_"):
            try:
                fn(); print("ok  ", k)
            except AssertionError as e:
                fails += 1; print("FAIL", k, e)
    sys.exit(1 if fails else 0)
