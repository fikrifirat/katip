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

W = 1754


def notice(y0, office, sira, name_lines, body_lines):
    """Boxes (y, x, h, w, text) for one notice: fields at x=60, body at x=560."""
    fields = [office, f"İlan Sıra No: {sira}", "Mersis No: 0123456789000017", "Ticaret Sicil/Dosya No: 69921",
              "Ticaret Unvani:", *name_lines]
    boxes = [(y0 + 30 * i, 60, 20, 420, t) for i, t in enumerate(fields)]
    boxes += [(y0 + 30 * i, 560, 20, 1100, t) for i, t in enumerate(body_lines)]
    return boxes


PAGE = (notice(100, "BURSA TİCARET SİCİLİ MÜDÜRLÜĞÜ'NDEN", 13033, ["KUZEYRÜZGARI TEKSTİL", "ANONİM ŞİRKETİ"],
               ["Bursa 2. Asliye Ticaret Mahkemesinin kararı ile konkordato", "kesin mühlet verilmiştir.",
                "Yukarıdaki bilgilerin 18.11.2026 tarihinde Ticaret Sicili Müdürlüğünce", "tescil edildiği ilan olunur."])
        + notice(400, "BURSA TİCARET SİCİLİ MÜDÜRLÜĞÜ'NDEN", 13034, ["GÜNEYRÜZGARI GIDA SANAYİ", "LİMİTED ŞİRKETİ"],
                 ["Şirketin sermayesi 500.000 TL'ye artırılmıştır.", "türlü inşaat taahhüt işleri ile konut"])
        + [(1150, 700, 20, 300, "T.C."), (20, 600, 20, 600, "TÜRKİYE TİCARET SİCİLİ GAZETESİ")])


def test_layout_keeps_columns_apart():
    ns = gazette.layout_notices(PAGE, W)
    assert len(ns) == 2
    a, b = ns
    assert a["title"] == "KUZEYRÜZGARI TEKSTİL ANONİM ŞİRKETİ"
    assert b["title"] == "GÜNEYRÜZGARI GIDA SANAYİ LİMİTED ŞİRKETİ"
    assert "sermayesi" not in a["text"] and "konkordato" not in b["text"]
    assert "KUZEYRÜZGARI TEKSTİL ANONİM ŞİRKETİ" in a["text"]  # name on one line, not split by body text
    assert a["sira"] == "13033"
    assert "T.C." not in b["text"].split() and "GAZETESİ" not in a["text"]


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
    from katip_kalkan.dd import service
    from katip_kalkan.dd.store import Store
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path))
    st = Store()
    st.replace_source("gazette", [{"rid": "gazette:abc:1:0", "title": "old", "text": "x"},
                                  {"rid": "gazette:abc:1:7", "title": "stale", "text": "y"},
                                  {"rid": "gazette:zzz:1:0", "title": "other file", "text": "z"}], {}, "t0")
    monkeypatch.setattr(gazette, "ingest", lambda files, ocr=False: [{"rid": "gazette:abc:1:0", "title": "new", "text": "n"}])
    service.add_gazette([tmp_path], store=st)
    assert sorted(r["title"] for r in st.records("gazette")) == ["new", "other file"]
