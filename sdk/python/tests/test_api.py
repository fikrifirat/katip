import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import katip_mask as km
from katip_mask import LeakError, Masker, ModelError, mask, restore
from katip_mask import safety
from katip_mask._engine.recognizers import ALL_ENTITIES

ROOT = Path(__file__).resolve().parents[3]
DOC = ("Davacı Ahmet YILMAZ (T.C. Kimlik No: 10000000146) Kızılay Mah. Atatürk Cad. No:12 D:3 Çankaya/ANKARA adresinde oturur.\n"
       "Tel: 0532 123 45 67, e-posta ahmet.yilmaz@gmail.com. Ankara 3. Asliye Hukuk Mahkemesi 2023/145 E. sayılı dosya.\n"
       "Ahmet YILMAZ 12.03.2024 tarihinde ödedi. Depresyon tedavisi görüyor.")


def test_court_profile_keeps_street_case_number_and_date():
    r = Masker("court").mask(DOC)
    assert "Ahmet" not in r.text and "10000000146" not in r.text and "0532" not in r.text
    assert "Kızılay Mah. Atatürk Cad." in r.text and "Çankaya/ANKARA" in r.text
    assert "2023/145" in r.text and "12.03.2024" in r.text
    assert r.text.count("[AD SOYAD-1]") == 2  # same person, same placeholder


def test_ladder_each_profile_masks_more():
    court, ai, anon = (Masker(p).mask(DOC) for p in ("court", "ai", "anon"))
    assert "2023/145" not in ai.text and "Atatürk" not in ai.text
    assert "12.03.2024" not in anon.text and "Mahkemesi" not in anon.text
    for weaker, stronger in ((court, ai), (ai, anon)):  # nothing masked by a weaker profile is readable in a stronger one
        for sp in weaker.spans:
            assert sp.text not in stronger.text


def test_profiles_match_kalkan_and_demo():
    """Same ladder as connector/katip_kalkan/engine.py PROFILES and src/app.js PROFILES."""
    case, anon = ["CASE_NO", "BAR_NO"], ["DATE", "PLACE", "INSTITUTION"]
    p = km.PROFILES
    assert p["court"]["entities"] == [e for e in ALL_ENTITIES if e != "CRIMINAL_RECORD"] and p["court"]["address_detail"] == "street"
    assert p["ai"]["entities"] == ALL_ENTITIES + case and p["ai"]["address_detail"] == "full"
    assert p["anon"]["entities"] == ALL_ENTITIES + case + anon and p["anon"]["address_detail"] == "full"


def test_restore_round_trip_and_mapping():
    r = mask(DOC, "ai")
    assert r.restore(r.text) == DOC  # every placeholder maps back to the exact original
    assert restore("[AD SOYAD-1] haklıdır.", r.mapping) == "Ahmet YILMAZ haklıdır."
    assert json.loads(json.dumps(r.to_dict()))["mapping"] == r.mapping


def test_block_style_has_no_mapping():
    r = mask(DOC, "court", style="block")
    assert "██████" in r.text and r.mapping == {}


def test_allow_and_deny():
    text = "Müvekkil Ayşe Kaya ile Katip Hukuk Bürosu çalışanı Zeynep görüştü."
    assert "Zeynep" not in mask(text, deny=["Zeynep"]).text
    assert "Ayşe Kaya" in mask(text, allow=["Ayşe Kaya"]).text


def test_turkish_case_insensitive_cues():
    # Python's re.I treats i/İ/ı/I as one letter; the JS SDK is held to the same behaviour
    assert "10000000146" not in mask("KİMLİK NO 10000000146").text


def test_propagation_and_id_context():
    r = mask("Kimlik: 99123456789 (YKN). Ayrıca 99123456789 yazıldı.", "court")
    assert "99123456789" not in r.text
    spans = safety.id_numbers("TCKN: 12345678901", [])
    assert spans and spans[0]["entity_type"] == "TCKN"


def test_fail_closed_repairs_or_raises():
    text = "ali veli ali veli"
    spans = [{"id": "s0000", "entity_type": "PERSON", "start": 0, "end": 8, "text": "ali veli", "score": 1.0}]
    assert safety.leaks(text, spans) == ["s0000"]
    masked, fixed, _ = safety.mask_safely(text, spans, "label", km.LABELS_TR)
    assert "ali" not in masked and len(fixed) == 2
    with pytest.raises(LeakError) as e:
        orig = safety.repair
        try:
            safety.repair = lambda t, s, l: s  # a repair that does nothing must end in LeakError, not leaked text
            safety.mask_safely(text, spans, "label", km.LABELS_TR)
        finally:
            safety.repair = orig
    assert e.value.kinds == ["PERSON"] and "ali" not in str(e.value)


def test_bad_options():
    with pytest.raises(ValueError):
        Masker("everything")
    with pytest.raises(ValueError):
        Masker(entities=["NAME"])
    with pytest.raises(ValueError):
        Masker(style="stars")


def test_offsets_are_code_points():
    text = "😀 Davacı Ahmet YILMAZ"
    s = Masker().detect(text)[0]
    assert text[s.start:s.end] == "Ahmet YILMAZ" == s.text


def test_model_download_rejects_wrong_hash(tmp_path, monkeypatch):
    info = km.MODELS["nano"]
    src = tmp_path / "mirror" / info["repo"] / "resolve" / info["revision"]
    (src / "onnx").mkdir(parents=True)
    for f in ("config.json", "tokenizer.json", "onnx/model_quantized.onnx"):
        (src / f).write_bytes(b"x" * info["files"][f]["size"])
    monkeypatch.setenv("KATIP_MASK_ENDPOINT", (tmp_path / "mirror").as_uri())
    monkeypatch.setenv("KATIP_MASK_CACHE", str(tmp_path / "cache"))
    with pytest.raises(ModelError, match="SHA-256"):
        km.model_path("nano")
    assert not list((tmp_path / "cache").rglob("config.json"))  # nothing unverified is kept


def test_offline_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_MASK_CACHE", str(tmp_path))
    monkeypatch.setenv("KATIP_MASK_OFFLINE", "1")
    with pytest.raises(ModelError, match="not downloaded"):
        km.model_path("mini")


def test_cli(tmp_path):
    f = tmp_path / "d.txt"
    f.write_text(DOC, encoding="utf-8")
    out = subprocess.run([sys.executable, "-m", "katip_mask", "mask", str(f), "--profile", "ai", "--json"],
                         capture_output=True, text=True, check=True).stdout
    res = json.loads(out)
    assert "Ahmet" not in res["text"] and res["mapping"]
    (tmp_path / "m.json").write_text(out, encoding="utf-8")
    (tmp_path / "a.txt").write_text("[AD SOYAD-1] haklı.", encoding="utf-8")
    back = subprocess.run([sys.executable, "-m", "katip_mask", "restore", str(tmp_path / "a.txt"), "--mapping", str(tmp_path / "m.json")],
                          capture_output=True, text=True, check=True).stdout
    assert back == "Ahmet YILMAZ haklı."


@pytest.mark.skipif(not (ROOT / "docs" / "katip_py.zip").exists(), reason="outside the repository")
def test_vendored_engine_is_the_demo_and_kalkan_engine():
    subprocess.run([sys.executable, str(ROOT / "sdk" / "tools" / "sync_engine.py"), "--check"], check=True)


@pytest.mark.skipif(os.environ.get("KATIP_MASK_TEST_MODELS") != "1", reason="set KATIP_MASK_TEST_MODELS=1 (downloads models)")
@pytest.mark.parametrize("name", ["nano", "mini"])
def test_models_find_names_the_rules_miss(name):
    text = "Toplantıya Peter Aufschnaiter ve Madeleine Okonkwo da katıldı."
    r = Masker("court", model=name).mask(text)
    assert "Peter" not in r.text and r.model.startswith(name)
    assert "Peter" in Masker("court").mask(text).text  # the rules alone miss this foreign name
    if name == "mini":
        assert "Aufschnaiter" not in r.text
