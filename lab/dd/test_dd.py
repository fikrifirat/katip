"""Offline tests for Katip DD. All names below are invented.

    python lab/dd/test_dd.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "connector"))

from katip_kalkan.dd.match import MATCH, REVIEW, ListIndex, TextIndex, name_score, token_sim  # noqa: E402
from katip_kalkan.dd.normalize import fold, id_tokens, split_aliases, tokens  # noqa: E402
from katip_kalkan.dd.sources import gazette, masak  # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL", msg)


# -- normalisation ------------------------------------------------------------------------
check(fold("ŞAHİN İnşaat A.Ş.") == "sahin insaat a s", fold("ŞAHİN İnşaat A.Ş."))
check(fold("ILGAZ IŞIK") == "ilgaz isik", fold("ILGAZ IŞIK"))
check(tokens("Kuzeyrüzgarı Tekstil San. ve Tic. Ltd. Şti.") == ["kuzeyruzgari", "tekstil"], tokens("Kuzeyrüzgarı Tekstil San. ve Tic. Ltd. Şti."))
check(tokens("Kuzeyrüzgarı Tekstil Limited Şriketi") == ["kuzeyruzgari", "tekstil"], "misspelt legal form")
check(tokens("ABD AL-BASET ZORLUOĞLU") == ["abd", "baset", "zorluoglu"], tokens("ABD AL-BASET ZORLUOĞLU"))
check(split_aliases("a) Office #12b) Office No. 12c) Bureau 12") == ["Office #12", "Office No. 12", "Bureau 12"],
      split_aliases("a) Office #12b) Office No. 12c) Bureau 12"))
check(split_aliases("X ONE,X TWO - Y THREE - < Z FOUR >") == ["X ONE", "X TWO", "Y THREE", "Z FOUR"],
      split_aliases("X ONE,X TWO - Y THREE - < Z FOUR >"))
check(id_tokens("12345678901/0471900000") == ["12345678901", "0471900000"], "id split")
check(id_tokens("Yemen pasaport 00385937") == ["00385937"], "passport in text")

# -- token and name similarity -------------------------------------------------------------
check(token_sim("mohammed", "muhammad") >= 0.93, "translit group")
check(token_sim("wali", "vali") >= 0.93, "w/v")
check(token_sim("hasan", "huseyin") < 0.85, "Hasan is not Hüseyin")
check(token_sim("mehmet", "muhammad") < 0.85, "Mehmet is not Muhammad")
check(token_sim("abdul", "abdulbaset") < 0.85, "prefix is not the name")
check(name_score(["ozlem", "arik"], ["ozlem", "tanrikulu"]) < REVIEW, "different surname")
check(name_score(["ayse", "kocabey"], ["kocabey", "ayse"]) == 1.0, "order")
check(REVIEW <= name_score(["ali", "aslan"], ["dursun", "ali", "aslan"]) < MATCH, "extra middle name -> review")
check(name_score(["yildirim"], ["ayse", "yildirim"]) <= 0.8, "one word is never a match")

# -- list index ---------------------------------------------------------------------------
RECS = [
    {"rid": "1", "names": ["AYŞE NUR KOCABEY", "A. N. KOCABEY"], "ids": ["12345678901"], "birth": "4/13/1978", "list": "t"},
    {"rid": "2", "names": ["KUZEYRÜZGARI TEKSTİL SANAYİ VE TİCARET LİMİTED ŞİRKETİ"], "ids": [""], "birth": "", "list": "t"},
    {"rid": "3", "names": ["ABD AL-RAHIM ZORLUOGLU", "ABDURRAHIM ZORLUOĞLU"], "ids": ["P1234567"], "birth": "1966", "list": "t"},
]
idx = ListIndex(RECS)
h = idx.search("ayse nur kocabey")
check(h and h[0].record["rid"] == "1" and h[0].band == "match", "ascii exact")
h = idx.search("Ayşe Kocabey")
check(h and h[0].record["rid"] == "1" and h[0].band in ("match", "review"), "middle name dropped")
h = idx.search("Ayşe Kocabey", birth="1980")
check(h and any("differs" in r for r in h[0].reasons), "birth year differs is shown")
h = idx.search("Kuzeyrüzgarı Tekstil Ltd. Şti.")
check(h and h[0].record["rid"] == "2" and h[0].band == "match", "company legal form")
h = idx.search("Nobody Here", id_no="P1234567")
check(h and h[0].record["rid"] == "3" and h[0].score == 1.0, "passport id match")
check(not idx.search("Mehmet Yılmaz"), "unrelated common name")

# -- free text (gazette / ilan) -------------------------------------------------------------
docs = [{"rid": "g1", "text": "İstanbul Ticaret Sicili Müdürlüğü Ticaret Sicil No: 99999 Ticaret Unvanı: KUZEYRÜZGARI "
                              "TEKSTİL SANAYİ VE TİCARET LİMİTED ŞİRKETİ Şirketin tasfiyesine karar verilmiştir."},
        {"rid": "g2", "text": "Ankara Ticaret Sicili Müdürlüğü Ticaret Unvanı: GÜNEYRÜZGARI GIDA A.Ş. sermaye artırımı"}]
t = TextIndex(docs)
h = t.search("Kuzeyruzgari Tekstil Ltd Sti")
check(h and h[0].record["rid"] == "g1", "mention in notice")
check(not [x for x in h if x.record["rid"] == "g2"], "no hit on the other company")
t2 = TextIndex([{"rid": "g3", "text": "Konkordato: ERTUNA ÖRNEK ANONİM ŞİRKETİ ile müşterek talepçi 12345678901 TC kimlik nolu kişi"}])
h = t2.search("Ertuna Örnek")
check(h and "12345678901" not in " ".join(h[0].reasons), "kimlik numbers masked in snippet")
check(h and h[0].matched == "ertuna ornek", f"matched span {h and h[0].matched}")

# -- gazette splitting and PDF ingest ---------------------------------------------------------
parts = gazette.split_notices(docs[0]["text"] + "\n" + docs[1]["text"])
check(len(parts) == 2, f"split notices: {len(parts)}")
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    font = next((p for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial Unicode.ttf"] if Path(p).exists()), None)
    if font:
        pdfmetrics.registerFont(TTFont("U", font))
        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d) / "tsg-test.pdf"
            c = canvas.Canvas(str(pdf), pagesize=A4)
            c.setFont("U", 9)
            y = 800
            for line in ["TÜRKİYE TİCARET SİCİLİ GAZETESİ Sayı : 11234 21/11/2026",
                         "İstanbul Ticaret Sicili Müdürlüğü", "Ticaret Sicil No: 99999",
                         "Ticaret Unvanı: KUZEYRÜZGARI TEKSTİL SANAYİ VE TİCARET LİMİTED ŞİRKETİ",
                         "Şirketin tasfiyesine karar verilmiştir.", "Ankara Ticaret Sicili Müdürlüğü",
                         "Ticaret Unvanı: GÜNEYRÜZGARI GIDA A.Ş.", "Sermaye artırımı tescil edilmiştir."]:
                c.drawString(40, y, line)
                y -= 14
            c.save()
            notices = gazette.ingest([pdf])
            check(len(notices) == 2, f"pdf notices {len(notices)}")
            check(notices and notices[0]["issue"] == "11234", "issue number")
            h = TextIndex(notices).search("Kuzeyrüzgarı Tekstil")
            check(h and "page=1" in h[0].record["url"], "pdf hit links to page")
except ImportError:
    print("skip pdf test (reportlab missing)")

# -- MASAK row mapping and CSV parsing (invented rows) ---------------------------------------
row = {"sira_no": 7, "ad_soyad_unvan": "AYŞE NUR KOCABEY", "diger_adlari": "A. N. KOCABEY,AYSE KOCABEY",
       "tckn_vkn": "12345678901", "uyrugu": "TÜRKİYE", "diger_uyruk": "TÜRKİYE", "anne_adı": "X", "baba_adı": "Y",
       "dogum_tarihi": "4/13/1978", "karar_sayisi": "2021-04-07 / 31447", "orgutu": "TEST", "yaptirim_turu": "T"}
r = masak.to_record(row, "6415-m7-ic", "https://example.invalid")
check(r["kind"] == "person" and len(r["names"]) == 3, "masak record")
check(r["gazette_url"].endswith("/2021/04/20210407.htm"), r["gazette_url"])
body = ("Başlık;;;\n;AD-SOYAD/ÜNVANI;TCKN;KULLANDIĞI BİLİNEN DİĞER İSİMLERİ;DOĞUM TARİHİ\n"
        "1;AYŞE NUR KOCABEY;12345678901;\"A. N. KOCABEY\";1978\n2;KUZEYRÜZGARI TEKSTİL;;;\n").encode("cp1254")
rows = masak.parse_csv_rows(body)
check([x["name"] for x in rows] == ["AYŞE NUR KOCABEY", "KUZEYRÜZGARI TEKSTİL"], rows)

print("all ok" if not FAILS else f"{len(FAILS)} failed")
sys.exit(1 if FAILS else 0)
