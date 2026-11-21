"""Document-type classifier (Katip Algıla): spec, packs, privacy split, Kalkan wiring.

Run:  cd connector && python -m pytest -q tests/test_doctype.py
Accuracy is measured in lab/doctype/eval.py; here we only check behaviour that must never change.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
ROOT = HERE.parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from katip_kalkan import doctype as D  # noqa: E402

SAMPLES = REPO / "docs" / "samples"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "katip"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    monkeypatch.setenv("KATIP_FOLDER", str(tmp_path))
    monkeypatch.setenv("KATIP_DOWNLOADS", "0")
    return tmp_path


def test_hash_spec_is_stable():
    # FNV-1a 32-bit: these values are part of the format (JS/Swift ports must match byte for byte)
    assert D.fnv1a("") == 0x811C9DC5
    assert D.fnv1a("a") == 0xE40C292C
    assert D.fnv1a("w:odeme") == D.fnv1a("w:odeme")
    assert D.normalise("ÖDEME EMRİ ıIİi") == "odeme emri iiii"


def test_featurize_is_unit_length_and_ignores_numbers():
    v = D.featurize("Borçlu 12.345,00 TL ödeme emri", 2 ** 14)
    assert abs(sum(x * x for x in v.values()) - 1) < 1e-6
    assert D.featurize("Borçlu 12.345,00 TL ödeme emri", 2 ** 14) == D.featurize("Borçlu 98.111,55 TL ödeme emri", 2 ** 14)


def test_packs_load_and_every_type_has_an_english_name():
    assert {"tr", "nl"} <= set(D.languages())
    for lang in D.languages():
        p = D.Pack(lang)
        for t in p.meta["types"]:
            assert t["name"]["local"] and t["name"]["en"], (lang, t["id"])
            for s in t["steps"]:
                assert s["where"] in ("device", "network"), (lang, t["id"], s)


def test_model_matches_pack_labels():
    p = D.pack("tr")
    assert p.model is not None and p.classes == p.labels


@pytest.mark.parametrize("stem,label", [("ihtarname_01", "ihtarname"), ("vekaletname_01", "vekaletname"),
                                        ("kira_sozlesmesi_01", "kira_sozlesmesi"), ("fatura_01", "fatura"),
                                        ("epikriz_01", "saglik_raporu"), ("karar_01", "karar")])
def test_classifies_independent_samples(stem, label):
    r = D.classify((SAMPLES / f"{stem}.txt").read_text(encoding="utf-8"))
    assert r["lang"] == "tr" and r["type"] == label, r


def test_short_or_foreign_text_abstains():
    assert D.classify("Merhaba")["abstained"]
    r = D.classify("De huurder betaalt de huur per maand vooruit op de rekening van de verhuurder. " * 3)
    assert r["lang"] == "nl" and r["abstained"] and "no trained model" in r["reason"]


def test_language_detection():
    assert D.detect_language("Davacı vekili dava dilekçesinde özetle; müvekkilin alacağının ödenmediğini") == "tr"
    assert D.detect_language("De werkgever is verplicht het loon te betalen aan de werknemer en de") == "nl"
    assert D.detect_language("The tenant shall pay the rent to the landlord on the first day of the month") == "en"


def test_network_steps_are_only_suggested():
    plan = D.next_steps({"type": "odeme_emri", "lang": "tr"}, "İİK md. 62 uyarınca itiraz")
    kinds = {s["tool"]: s for s in plan["steps"]}
    assert kinds["mask"]["run"] == "auto" and kinds["emsal"]["run"] == "suggest"
    assert "İİK md. 62" in plan["cited_in_document"]
    assert any(m["ref"] == "İİK md. 62" for m in plan["mevzuat"])
    plan = D.next_steps({"type": "odeme_emri", "lang": "tr"}, settings={"auto_network": True, "off": ["emsal"]})
    assert "emsal" not in {s["tool"] for s in plan["steps"]}


def test_cited_finds_statute_references():
    t = "TBK md. 117 ve HMK m. 119 ile 6698 sayılı Kişisel Verilerin Korunması Kanunu'nun 11. maddesi"
    got = D.cited(t)
    assert "TBK md. 117" in got and "HMK md. 119" in got and any(g.startswith("6698") for g in got)


def test_scan_reports_types_without_text(tmp_path):
    for stem in ("ihtarname_02", "fatura_02", "vekaletname_02"):
        (tmp_path / f"{stem}.txt").write_text((SAMPLES / f"{stem}.txt").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "bos.txt").write_text("", encoding="utf-8")
    rows = D.scan(tmp_path, read=lambda p: p.read_text(encoding="utf-8"))
    by = {r["path"]: r for r in rows}
    assert by["ihtarname_02.txt"]["type"] == "ihtarname" and by["fatura_02.txt"]["type"] == "fatura"
    assert by["bos.txt"]["abstained"]
    assert all("text" not in r for r in rows)


def test_mask_file_carries_type_and_no_document_values(home):
    from katip_kalkan import core
    src = (SAMPLES / "ihtarname_01.txt").read_text(encoding="utf-8")
    (home / "ihtar.txt").write_text(src, encoding="utf-8")
    doc = core.mask_file(str(home / "ihtar.txt"))
    assert doc["document_type"]["type"] == "ihtarname"
    blob = json.dumps(doc["next_steps"], ensure_ascii=False)
    gold = json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
    values = [g["text"] for m in gold if m["id"] == "ihtarname_01" for g in m["gold"]]
    assert values and not [v for v in values if v in blob]


def test_scan_documents_tool(home):
    from katip_kalkan import core
    (home / "Kira sözleşmesi.txt").write_text((SAMPLES / "kira_sozlesmesi_01.txt").read_text(encoding="utf-8"), encoding="utf-8")
    out = core.scan_documents()
    assert out["files"] and out["files"][0]["type"] == "kira_sozlesmesi"
    assert "masked_text" not in out["files"][0] and "text" not in out["files"][0]


@pytest.mark.parametrize("mode,net_ok,device_run,net_run", [
    ("device", True, "auto", "suggest"),
    ("ask", True, "suggest", "suggest"),
    ("auto", True, "auto", "auto"),
    ("auto", False, "auto", "suggest"),   # precedent search off: nothing leaves on its own
    ("nonsense", True, "auto", "suggest"),  # unknown value falls back to the safe default
])
def test_autonomy_modes(mode, net_ok, device_run, net_run):
    plan = D.next_steps({"type": "odeme_emri", "lang": "tr"}, settings={"mode": mode, "network_ok": net_ok})
    runs = {s["where"]: s["run"] for s in plan["steps"]}
    assert runs["device"] == device_run and runs["network"] == net_run
    assert plan["autonomy"]["mode"] in ("ask", "device", "auto")


def test_autonomy_from_settings(monkeypatch):
    from katip_kalkan import core
    monkeypatch.setenv("KATIP_AUTONOMY", "auto")
    monkeypatch.setenv("KATIP_STEPS_OFF", "emsal, draft")
    monkeypatch.delenv("KATIP_EMSAL_ONLINE", raising=False)
    a = core.autonomy()
    assert a == {"mode": "auto", "off": ["emsal", "draft"], "network_ok": False}
    plan = D.next_steps({"type": "odeme_emri", "lang": "tr"}, settings=a)
    assert not {s["tool"] for s in plan["steps"]} & {"emsal", "draft"}
    assert all(s["run"] == "suggest" for s in plan["steps"] if s["where"] == "network")
