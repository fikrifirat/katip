"""Court-filing feedback from a practising lawyer (Nov 2026). Synthetic text only: every name, number and address is made up.

1. A lawyer's UETS (e-Tebligat) address identifies the lawyer as surely as the name: when names are masked, it is masked too.
2. Addresses have a role. A party's own address (under "Şüpheli", "Davacı", "Müdafi", "Adres:", "... adresinde ikamet eden")
   is masked whole in the court profile. The address of the property the case is about (the leased flat, the parcel)
   is evidence and stays readable in the court profile. Other addresses keep the street-level rule.
   The AI and anonymous profiles ("full") still mask every address.

  python src/tests/test_court_filing.py [docs/katip_py.zip]
"""
import sys, tempfile, zipfile
from pathlib import Path

zp = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parents[2] / "docs/katip_py.zip")
tmp = tempfile.mkdtemp()
zipfile.ZipFile(zp).extractall(tmp)
sys.path.insert(0, tmp)
import local_detect  # noqa: E402


def spans(text, **kw):
    return local_detect.detect(text, **kw)


def readable(text, needle, **kw):
    """True when no masked span touches `needle`."""
    a = text.index(needle)
    b = a + len(needle)
    return not any(s["start"] < b and a < s["end"] for s in spans(text, **kw))


def masked(text, needle, **kw):
    """True when every letter and digit of `needle` is inside a masked span."""
    a = text.index(needle)
    sp = spans(text, **kw)
    return all(any(s["start"] <= i < s["end"] for s in sp) for i in range(a, a + len(needle)) if text[i].isalnum())


HEADER = ("Dosya No\t\t: 2025/41 Sorgu\n"
          "Şüpheli\t\t: Tuncay ERDEMLİ (TC: 10000000146)\n"
          "\t\t Yeşilova Mah. Gürgen Sok. No:14 D:3 Etimesgut/ANKARA\n\n"
          "Müdafi\t\t: Av. Seda KORUKÇU (UETS: 18452-30917-66204)\n"
          "\t\t Atatürk Bulvarı Lale Apt. No:120 K:4 Çankaya/ANKARA\n")


def test_uets_masked_with_lawyer_name():
    assert masked(HEADER, "18452-30917-66204")
    assert any(s["entity_type"] == "UETS" for s in spans(HEADER))


def test_uets_variants():
    for t, v in (("e-Tebligat adresi: 11223-44556-77889 olan vekil", "11223-44556-77889"),
                 ("UETS Adresi : 99887 66554 33221", "99887 66554 33221"),
                 ("Vekil (UETS 123456789012345)", "123456789012345")):
        assert masked(t, v), t


def test_uets_not_case_numbers():
    t = "Ankara 3. Asliye Hukuk Mahkemesi 2024/12345 E. 2025/678 K. sayılı dosya"
    assert not any(s["entity_type"] == "UETS" for s in spans(t))


def test_party_address_masked_whole_in_court_profile():
    for addr in ("Yeşilova Mah. Gürgen Sok. No:14 D:3 Etimesgut", "Atatürk Bulvarı Lale Apt. No:120 K:4 Çankaya"):
        assert masked(HEADER, addr, address_detail="street"), addr


def test_label_and_prose_residence_masked_whole():
    t = "Davalı Kemal Sarıgöl, Adres: Kocatepe Mah. Menekşe Cad. No:7 Daire:2 Keçiören/ANKARA\n"
    assert masked(t, "Kocatepe Mah. Menekşe Cad.", address_detail="street")
    t = "Müvekkil, Bahçelievler Mah. Ilgaz Sok. No:22 D:6 Çankaya/ANKARA adresinde ikamet etmektedir."
    assert masked(t, "Bahçelievler Mah. Ilgaz Sok.", address_detail="street")


def test_addressee_block_and_moved_residence_masked_whole():
    t = "SAYIN\nNurten KAPLANOĞLU\nÇamlık Mah. Defne Sok. No:9 D:2 Pamukkale/DENİZLİ\n"
    assert masked(t, "Çamlık Mah. Defne Sok.", address_detail="street")
    t = "Artık Yıldırım Mah. Kartal Cad. No:61 D:4 Osmangazi/BURSA adresinde oturduğunu belirtti."
    assert masked(t, "Yıldırım Mah. Kartal Cad.", address_detail="street")


def test_leased_property_address_readable_in_court_profile():
    t = ("Davalı kiracı, Kavaklıdere Mah. Esat Cad. No:41 D:9 Çankaya/ANKARA adresindeki taşınmazı "
         "01.03.2022 tarihli kira sözleşmesi ile kiralamıştır.\n")
    assert readable(t, "Kavaklıdere Mah. Esat Cad. No:41 D:9", address_detail="street")
    t = "Kiralananın Adresi: Cumhuriyet Mah. Fidan Sok. No:5 D:11 Yenimahalle/ANKARA\n"
    assert readable(t, "Cumhuriyet Mah. Fidan Sok. No:5 D:11", address_detail="street")
    t = "Dava konusu taşınmaz: Gazi Mah. Şehit Polis Sok. No:18 Kat:2 Yenimahalle/ANKARA\n"
    assert readable(t, "Gazi Mah. Şehit Polis Sok. No:18", address_detail="street")


def test_case_number_repeat_and_citation_in_ai_profile():
    t = ("Dosya No\t: 2025/41 Sorgu\n"
         "Konusu\t: Sulh Ceza Hakimliğinin 2025/41 \t\t Sorgu No'lu kararına itirazımızdır.\n"
         "Nitekim Yargıtay Ceza Genel Kurulu'nın 2017/378 E. 2018/618 K. sayılı kararı uyarınca ...\n")
    kw = dict(entities=list(local_detect.ALL_ENTITIES) + ["CASE_NO", "BAR_NO"], address_detail="full")
    assert sum(s["text"] == "2025/41" for s in spans(t, **kw)) == 2
    assert readable(t, "2017/378 E. 2018/618 K.", **kw)


def test_full_profiles_still_mask_every_address():
    t = ("Davalı kiracı, Kavaklıdere Mah. Esat Cad. No:41 D:9 Çankaya/ANKARA adresindeki taşınmazı "
         "kira sözleşmesi ile kiralamıştır.\n")
    assert masked(t, "Kavaklıdere Mah. Esat Cad. No:41 D:9", address_detail="full")
    assert masked(HEADER, "Yeşilova Mah. Gürgen Sok. No:14 D:3", address_detail="full")


def test_other_addresses_keep_street_rule():
    t = "Olay, Kızılay Mah. Gazi Mustafa Kemal Bulvarı No:33 Çankaya/ANKARA önünde meydana gelmiştir.\n"
    assert readable(t, "Kızılay Mah.", address_detail="street")
    assert masked(t, "No:33", address_detail="street")


if __name__ == "__main__":
    bad = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            try:
                f()
                print("ok  ", k)
            except AssertionError as e:
                bad += 1
                print("FAIL", k, e)
    sys.exit(1 if bad else 0)
