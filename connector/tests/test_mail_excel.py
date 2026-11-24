"""Excel (.xlsx) and e-mail (.eml, Outlook .msg) through Kalkan: the text Claude gets and the masked copy.

Fixtures are synthetic (made-up people): src/tests/make_mail_excel_fixtures.py writes them and the answer key.
Every "mask" value in the key must be unreadable in what leaves the tools: the masked text, and every part of the
masked file (cells, shared strings, formulas, notes, sheet names, document properties, mail headers), and every
"keep" phrase must still be there, so a reader that silently drops content can't pass.

Run:  cd connector && python -m pytest -q tests/test_mail_excel.py
"""
from __future__ import annotations

import email
import io
import json
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from email import policy
from pathlib import Path

import pytest

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
FIX = ROOT.parent / "src" / "tests" / "fixtures" / "mail_excel"
KEY = json.loads((FIX / "answer_key.json").read_text(encoding="utf-8"))
squash = lambda s: re.sub(r"\s+", "", s).casefold()


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "katip"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    monkeypatch.setenv("KATIP_FOLDER", str(tmp_path))
    monkeypatch.setenv("KATIP_DOWNLOADS", "0")
    return tmp_path


def readable(text: str, values: list[str]) -> list[str]:
    t = squash(text)
    return [v for v in values if squash(v) in t]


@pytest.mark.parametrize("name", sorted(KEY))
def test_masked_text_and_copy(name, home):
    from katip_kalkan import core, engine
    src = home / name
    shutil.copyfile(FIX / name, src)
    gold, keep = KEY[name]["mask"], KEY[name]["keep"]
    res = core.mask_file(str(src), "m-" + name)
    assert res["kind"] == engine.KINDS[src.suffix]
    assert readable(res["masked_text"], gold) == []
    assert readable(res["masked_text"], keep) == keep  # the rest of the content is still there

    w = core.write_redacted(str(src), "w-" + name)
    out = src.with_name(src.stem + ".maskeli" + (".eml" if src.suffix == ".msg" else src.suffix))
    assert w["name"].endswith(out.suffix) and out.exists()
    data = out.read_bytes()
    _, fmt = engine.load()
    if out.suffix == ".xlsx":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n in z.namelist():
                if n.endswith((".xml", ".rels")):
                    ET.fromstring(z.read(n))  # still well-formed
        assert readable(fmt.leak_text("xlsx", data), gold) == []
        assert readable(fmt.extract("xlsx", data), keep) == keep
    else:
        m = email.message_from_bytes(data, policy=policy.default)
        assert m.get_content_type() == "text/plain"
        assert m["Message-ID"] is None and m["Received"] is None and m["Reply-To"] is None
        assert readable(data.decode("utf-8", "replace") + fmt.extract("eml", data), gold) == []
        assert readable(fmt.extract("eml", data), keep) == keep


def test_msg_reader_matches_the_file():
    """The stdlib compound-file reader finds the Outlook fields (subject, sender, recipients, attachment name)."""
    from katip_kalkan import engine
    _, fmt = engine.load()
    text = fmt.extract("msg", (FIX / "vekalet.msg").read_bytes())
    assert text.startswith("Kimden: Mehmet Ali Karakoç <makarakoc@ornekposta.net>\nKime: Hüseyin Çelikkaya")
    assert "Bilgi: Elif Şahinoğlu" in text and "Konu: Tapu iptal davası" in text
    assert "Ekler: vekaletname-Mehmet Ali Karakoç.pdf" in text


def test_xlsx_labels_keep_the_workbook_usable(home):
    """Label style: a sheet named after a person is renamed (no [ ] in sheet names) and formulas follow it."""
    from katip_kalkan import engine
    _, fmt = engine.load()
    data = (FIX / "personel.xlsx").read_bytes()
    text = fmt.extract("xlsx", data)
    spans = engine.detect(text)
    out = fmt.redact("xlsx", data, json.dumps(spans), "label")
    with zipfile.ZipFile(io.BytesIO(out)) as z:
        wb = z.read("xl/workbook.xml").decode()
        sheet = z.read("xl/worksheets/sheet1.xml").decode()
    names = re.findall(r'<sheet\b[^>]*\bname="([^"]*)"', wb)
    assert names[0] == "Personel" and "Zeynep" not in names[1] and not re.search(r"[\[\]:*?/\\]", names[1])
    assert f"'{names[1]}'!A2" in sheet.replace("&apos;", "'")
