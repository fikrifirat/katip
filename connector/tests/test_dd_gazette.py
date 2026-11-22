"""Ticaret Sicili Gazetesi layout: a scanned page holds several notices, each a narrow field box
(office, İlan Sıra No, Mersis, Sicil No, Ticaret Unvanı + name) left of a wide body. OCR boxes on
one row cross both columns, so reading row by row mixes them. Company names are invented.

Run:  cd connector && python -m pytest -q tests/test_dd_gazette.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from katip_kalkan.dd.sources import gazette  # noqa: E402

W = 2339


def col(x, y0, lines):
    return [(y0 + 30 * i, x + (200 if t.isupper() and len(t) < 45 else 0), 28, 600, t) for i, t in enumerate(lines)]


# Real layout (21 Nov 2026 pages): two page columns split at the middle; each notice is a stacked
# block (office heading, İlan Sıra No, Mersis, Sicil No, "Ticaret Unvani:", name, body) and often
# runs on at the top of the next column. Row by row, left and right columns would mix.
HEADER = [(272, 889, 33, 568, "TÜRKİYE TİCARET SİCİLİ GAZETESİ"), (272, 1940, 33, 181, "SAYFA: 843"),
          (274, 194, 33, 369, "7 EKİM 2026 SAYI:11682")]
LEFT = col(194, 344, [
    "önceki sayfadan devam eden metin, yönetim kurulu kararı ile",
    "T.C. BURSA TİCARET SİCİLİ MÜDÜRLÜĞÜ'NDEN", "İlan Sıra No: 18185", "Mersis No: 0123456789000017",
    "Ticaret Sicil/Dosya No: 69921", "Ticaret Unvani:", "KUZEYRÜZGARI TEKSTİL ANONİM ŞİRKETİ",
    "Bursa 2. Asliye Ticaret Mahkemesinin kararı ile konkordato", "geçici mühleti uzatılmıştır.",
    "(21230770)",
    "T.C. BURSA TİCARET SİCİLİ MÜDÜRLÜĞÜ'NDEN", "Ílan Sıra No: 220515", "Mersis No: 0987654321000011",
    "Ticaret Sicil/Dosya No: 1234", "Ticaret Unvani:", "GÜNEYRÜZGARI MAĞAZACILIK", "ANONİM ŞİRKETİ",
    "Şirketin amaç ve konusu aşağıdaki gibidir:"])
RIGHT = col(1211, 344, [
    "I. Her türlü kıymetli eşya ve mücevherat alım satımı,", "J. saat servis ve montaj hizmetleri.",
    "(21230771)",
    "T.C. İSTANBUL TİCARET SİCİLİ MÜDÜRLÜĞÜ", "İlan Sıra No: 145510", "Mersis No: 0815121072100001",
    "Ticaret Sicil/Dosya No: 1142256", "Ticaret Unvani:", "TASFİYE HALİNDE BATIRÜZGARI SAĞLIK HİZMETLERİ LİMİTED ŞİRKETİ",
    "1. İLAN", "Alacaklıların şirkete başvurmaları ilan olunur."])
PAGE = HEADER + LEFT + RIGHT


def test_layout_reads_columns_in_order_and_follows_run_ons():
    ns = gazette.layout_notices(PAGE, W)
    titles = [n["title"] for n in ns]
    assert titles[1:] == ["KUZEYRÜZGARI TEKSTİL ANONİM ŞİRKETİ", "GÜNEYRÜZGARI MAĞAZACILIK ANONİM ŞİRKETİ",
                          "TASFİYE HALİNDE BATIRÜZGARI SAĞLIK HİZMETLERİ LİMİTED ŞİRKETİ"]
    head, a, b, c = ns
    assert head["continuation"] and "önceki sayfadan" in head["text"]
    assert [a["sira"], b["sira"], c["sira"]] == ["18185", "220515", "145510"]  # Í read by OCR still anchors
    assert "kıymetli eşya" in b["text"] and "kıymetli eşya" not in a["text"]  # run-on to the next column
    assert "konkordato" in a["text"] and "konkordato" not in b["text"]
    assert "Alacaklıların" in c["text"] and "kıymetli" not in c["text"]
    blob = " ".join(n["text"] for n in ns)
    assert "SAYFA" not in blob and "SAYI:11682" not in blob and "GAZETESİ" not in blob


def test_text_split_ignores_office_in_body():
    text = ("BURSA TİCARET SİCİLİ MÜDÜRLÜĞÜ'NDEN\nTicaret Unvanı: KUZEYRÜZGARI TEKSTİL A.Ş.\nkararı ile mühlet verilmiş, bu durum\n"
            "18.11.2026 tarihinde Ticaret Sicili Müdürlüğünce tescil edilmiştir.\n"
            "Ankara Ticaret Sicili Müdürlüğü\nTicaret Unvanı: GÜNEYRÜZGARI GIDA A.Ş. sermaye artırımı")
    parts = gazette.split_notices(text)
    assert len(parts) == 2 and "tescil edilmiştir" in parts[0]


def test_title_with_dotless_i_and_name_on_next_line():
    assert gazette.title_of("BURSA TİCARET SİCİLİ MÜDÜRLÜĞÜ'NDEN\nTicaret Unvani:\nERTUNA ÖRNEK ANONİM ŞİRKETİ\nbody") \
        == "ERTUNA ÖRNEK ANONİM ŞİRKETİ"


def test_issue_date_page_from_file_name():
    assert gazette.meta_from_name("tsg_2026-11-19_11712_p101.pdf") == {"date": "2026-11-19", "issue": "11712", "gazette_page": "101"}
    assert gazette.meta_from_name("anything.pdf") == {}


def test_add_gazette_says_what_is_missing(tmp_path, monkeypatch):
    import builtins
    from katip_kalkan.dd import service
    from katip_kalkan.dd.store import Store
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path))
    real = builtins.__import__

    def no_pdf(name, *a, **k):
        if name in ("fitz", "pdfplumber"):
            raise ImportError(name=name)
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", no_pdf)
    f = tmp_path / "tsg_2026-11-19_11712_p101.pdf"
    f.write_bytes(b"%PDF-1.4")
    out = service.add_gazette([f], store=Store())
    assert out["status"] == "unavailable" and "pip install" in out["error"]


def test_re_adding_a_file_replaces_its_notices(tmp_path, monkeypatch):
    """Same file saved again with other bytes (new digest): its old notices must go, others stay."""
    from katip_kalkan.dd import service
    from katip_kalkan.dd.store import Store
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path))
    st = Store()
    f = str(tmp_path / "tsg_2026-11-19_11712_p101.pdf")
    st.replace_source("gazette", [{"rid": "gazette:olddigest:1:0", "title": "old", "text": "x", "url": f + "#page=1"},
                                  {"rid": "gazette:olddigest:1:7", "title": "stale", "text": "y", "url": f + "#page=1"},
                                  {"rid": "gazette:zzz:1:0", "title": "other file", "text": "z", "url": "/x/other.pdf#page=1"}],
                      {}, "t0")
    monkeypatch.setattr(gazette, "ingest", lambda files, ocr=False: [{"rid": "gazette:newdigest:1:0", "title": "new",
                                                                       "text": "n", "url": f + "#page=1"}])
    service.add_gazette([tmp_path], store=st)
    assert sorted(r["title"] for r in st.records("gazette")) == ["new", "other file"]
