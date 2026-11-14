"""How a name the on-device model finds is merged with the rules: lone first names inside a sentence,
names the model returns word by word, and the guards that keep ordinary words readable.

  python src/tests/test_lone_names.py [docs/katip_py.zip]
"""
import sys, tempfile, zipfile
from pathlib import Path

zp = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parents[2] / "docs/katip_py.zip")
tmp = tempfile.mkdtemp()
zipfile.ZipFile(zp).extractall(tmp)
sys.path.insert(0, tmp)
import local_detect  # noqa: E402


def people(text, spans, trust=0.5):
    """spans: (word, score) the model "found"; returns the PERSON texts Katip masks."""
    extra = [(text.index(w), text.index(w) + len(w), sc) for w, sc in spans]
    return [s["text"] for s in local_detect.detect(text, extra=extra, trust=trust) if s["entity_type"] == "PERSON"]


def test_lone_foreign_first_name_mid_sentence():
    # "Peter" is in the subtitle-based common-word list; a very sure model still masks it inside a sentence
    assert people("Sonunda Peter ile birlikte kaçtı.", [("Peter", 0.99)]) == ["Peter"]


def test_lone_unknown_name_mid_sentence():
    assert people("Dosyayı müvekkil Zaroui ile birlikte inceledik.", [("Zaroui", 0.7)]) == ["Zaroui"]


def test_model_words_joined_into_one_name():
    assert people("Filmin yapımcısı Jim Jonsin oldu.", [("Jim", 0.56), ("Jonsin", 0.54)]) == ["Jim Jonsin"]


def test_sentence_start_needs_a_known_name():
    # an ordinary word opening a sentence is not taken from the model alone
    assert people("Selam verip ayrıldı.", [("Selam", 0.99)]) == []


def test_stop_words_never_lone_names():
    assert people("Davalı Hazine vekili itiraz etti.", [("Hazine", 0.99)]) == []
    assert people("Dosya Barolar Birliğine gönderildi.", [("Barolar", 0.99)]) == []


def test_all_caps_and_roman_numerals_never_lone_names():
    assert people("Davacının TALEBİ reddedildi.", [("TALEBİ", 0.99)]) == []
    assert people("Dosya III. kez incelendi.", [("III", 0.99)]) == []


def test_unsure_common_word_stays_readable():
    # an ordinary word the model is not very sure of stays readable inside a sentence
    assert people("Bu konuda Tüm tarafların onayı alındı.", [("Tüm", 0.6)]) == []


def test_surname_repeated_alone_is_masked():
    t = "Davacı Ayşe Vardar ile görüşüldü. Vardar'ın beyanı dosyadadır."
    assert "Vardar" in people(t, [("Ayşe Vardar", 0.9)])


def test_name_word_inside_a_law_title_stays_readable():
    t = "Davacı Ahmet Türk, Türk Medenî Kanunu uyarınca başvurdu."
    assert people(t, [("Ahmet Türk", 0.9)]) == ["Ahmet Türk"]


if __name__ == "__main__":
    fails = 0
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            try:
                f(); print("ok  ", n)
            except AssertionError as e:
                fails += 1; print("FAIL", n, e)
    sys.exit(1 if fails else 0)
