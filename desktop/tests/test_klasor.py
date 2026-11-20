"""Katip Klasör end to end, on the synthetic fixtures of the connector (never real client documents).

Run:  cd desktop && python -m pytest -q
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
FIX = HERE.parent.parent / "connector" / "tests" / "fixtures"
GOLD = json.loads((FIX / "dilekce_01.gold.json").read_text(encoding="utf-8"))
HARD = [g["text"] for g in GOLD if g["entity_type"] in ("TCKN", "PHONE", "EMAIL", "IBAN")]
NAMES = sorted({g["text"] for g in GOLD if g["entity_type"] == "PERSON"})
CASE = "2026-114 Boşanma"


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KATIP_KLASOR_DIR", str(tmp_path / "Katip"))
    monkeypatch.setenv("KATIP_MODEL_FIXED", "1")  # whatever model the test machine has; settings default is base
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")


@pytest.fixture
def k():
    from katip_klasor import layout, pipeline, store
    root = layout.ensure(store.folder())
    return root, layout, pipeline, store


def drop(root, layout, name, dst=None, case=CASE):
    d = root / layout.INBOX / case
    d.mkdir(parents=True, exist_ok=True)
    p = d / (dst or name)
    shutil.copy(FIX / name, p)
    return p


def text_pdf(path: Path) -> Path:
    import pymupdf
    txt = (FIX / "dilekce_01.txt").read_text(encoding="utf-8")
    doc = pymupdf.open()
    doc.new_page().insert_htmlbox(pymupdf.Rect(50, 50, 545, 800),
                                  f"<pre style='font-family:sans-serif;font-size:9px;white-space:pre-wrap'>{html.escape(txt[:2200])}</pre>")
    doc.set_metadata({"author": NAMES[0]})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


def release_all(root, pipeline, store, case=CASE):
    s = store.load_settings()
    out = []
    for key, j in store.load_jobs(case).items():
        if j["status"] in ("review", "ready"):
            out.append(pipeline.release(root, case, key, s, who="test"))
    return out


def out_text(name: str, blob: bytes) -> str:
    from katip_klasor import pipeline
    return pipeline._out_text(name, blob)


# ---------------------------------------------------------------- folder layout
def test_folders_and_readme(k):
    root, layout, _, _ = k
    for f in layout.FOLDERS:
        assert (root / f).is_dir()
    assert "1 Gelen" in (root / "OKU-BENİ.txt").read_text(encoding="utf-8")


def test_synced_folder_warning(tmp_path):
    from katip_klasor import layout
    assert layout.synced_warning(tmp_path / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Katip")
    assert layout.synced_warning(tmp_path / "OneDrive - Büro" / "Katip")
    assert layout.synced_warning(tmp_path / "Documents" / "Katip") is None


def test_safe_name_hides_client_names():
    from katip_klasor import layout
    assert layout.safe_name(Path("dilekce.udf")) == "dilekce"
    s = layout.safe_name(Path("Ayşe Kaya vekaletname.pdf"))
    assert "Ayşe" not in s and "Kaya" not in s and s.startswith("vekaletname")


# ---------------------------------------------------------------- mask + release
@pytest.mark.parametrize("name,expect", [("dilekce_01.txt", [".maskeli.txt"]), ("dilekce_01.docx", [".maskeli.docx"]),
                                         ("dilekce_01.udf", [".maskeli.udf", ".maskeli.docx"])])
def test_mask_release_formats(k, name, expect):
    root, layout, pipeline, store = k
    src = drop(root, layout, name)
    before = hashlib.sha256(src.read_bytes()).hexdigest()
    job = pipeline.process(root, src, store.load_settings())
    assert job["status"] in ("review", "ready"), job.get("error")
    (rel,) = release_all(root, pipeline, store)
    assert rel["status"] == "released", rel.get("error")
    assert [o[len("dilekce_01"):] for o in rel["outputs"]] == expect
    for o in rel["outputs"]:
        t = out_text(o, (root / layout.OUT / CASE / o).read_bytes())
        for v in HARD + NAMES:
            assert v.casefold() not in t.casefold(), (o, v)
        if not o.endswith(".udf"):
            assert "[AD SOYAD-1]" in t  # the AI copy carries the case's placeholders
    assert hashlib.sha256(src.read_bytes()).hexdigest() == before  # the original is never touched


def test_same_label_across_files_of_a_case(k):
    root, layout, pipeline, store = k
    for n in ("dilekce_01.txt", "dilekce_01.docx"):
        pipeline.process(root, drop(root, layout, n), store.load_settings())
    release_all(root, pipeline, store)
    a = (root / layout.OUT / CASE / "dilekce_01.maskeli.txt").read_text(encoding="utf-8")
    b = out_text("x.docx", (root / layout.OUT / CASE / "dilekce_01.maskeli.docx").read_bytes())
    lab = lambda t: t[t.index("DAVACI"):].split("]")[0]  # noqa: E731
    assert lab(a) == lab(b)


def test_text_pdf_is_really_redacted(k, tmp_path):
    root, layout, pipeline, store = k
    src = text_pdf(root / layout.INBOX / CASE / "dilekce.pdf")
    job = pipeline.process(root, src, store.load_settings())
    assert job["kind"] == "pdf" and not job["ocr"]
    (rel,) = release_all(root, pipeline, store)
    (name,) = rel["outputs"]
    import pymupdf
    with pymupdf.open(root / layout.OUT / CASE / name) as d:
        t = "\n".join(p.get_text() for p in d)
        assert not d.metadata.get("author")
    for v in HARD + NAMES:
        assert v.casefold() not in t.casefold(), v
    for keep in ("evlenmiştir", "Boşanma", "MAHKEMESİ"):  # text around the boxes survives
        assert keep in t


def test_scan_becomes_masked_text_with_ocr_flag(k):
    root, layout, pipeline, store = k
    from katip_kalkan import ocr
    if not ocr.available():
        pytest.skip("no OCR engine on this machine")
    job = pipeline.process(root, drop(root, layout, "kira_foto_01.pdf"), store.load_settings())
    assert job["ocr"] and any(f["kind"] == "ocr" for f in job["flags"]) and job["status"] == "review"
    (rel,) = release_all(root, pipeline, store)
    assert rel["outputs"] == ["kira_foto_01.maskeli.docx"]
    t = out_text("x.docx", (root / layout.OUT / CASE / rel["outputs"][0]).read_bytes())
    assert t.startswith("Bu metin bir taramadan")


# ---------------------------------------------------------------- review decisions
def _flagged_job(root, layout, pipeline, store, text):
    d = root / layout.INBOX / CASE
    d.mkdir(parents=True, exist_ok=True)
    (d / "not.txt").write_text(text, encoding="utf-8")
    return pipeline.process(root, d / "not.txt", store.load_settings())


def test_keep_decision_leaves_value_readable_and_is_audited(k):
    root, layout, pipeline, store = k
    job = _flagged_job(root, layout, pipeline, store,
                       "Davacı Elvin Sözeri, T.C. Kimlik No: 10000000146, ile görüşüldü. Sonra Ahmet aradı.\n")
    f = next(f for f in job["flags"] if f["kind"] == "lone")
    assert f["value"] == "Ahmet" and f["decision"] == "mask"
    pipeline.set_decision(CASE, job["key"], f["id"], "keep")
    rel = pipeline.release(root, CASE, job["key"], store.load_settings(), who="test")
    out = (root / layout.OUT / CASE / rel["outputs"][0]).read_text(encoding="utf-8")
    assert f["value"] in out
    assert "10000000146" not in out
    assert "1 açık bırakıldı" in store.audit_rows(CASE)[-1]["detail"]


def test_always_mask_term(k):
    root, layout, pipeline, store = k
    s = store.load_settings()
    s["terms"] = {CASE: {"mask": ["Mavi Kuğu"], "keep": []}}
    store.save_settings(s)
    job = _flagged_job(root, layout, pipeline, store, "Taraflar mavi kuğu projesini konuştu.\n")
    rel = pipeline.release(root, CASE, job["key"], store.load_settings(), who="test")
    out = (root / layout.OUT / CASE / rel["outputs"][0]).read_text(encoding="utf-8")
    assert "kuğu" not in out and "[GİZLİ-1]" in out


def test_changed_file_is_not_released(k):
    root, layout, pipeline, store = k
    src = drop(root, layout, "dilekce_01.txt")
    job = pipeline.process(root, src, store.load_settings())
    src.write_text(src.read_text(encoding="utf-8") + "\nEk: Hülya Demirkol\n", encoding="utf-8")
    with pytest.raises(pipeline.Changed):
        pipeline.release(root, CASE, job["key"], store.load_settings())
    assert not (root / layout.OUT / CASE).exists()


def test_unreadable_file_goes_to_error(k):
    root, layout, pipeline, store = k
    d = root / layout.INBOX / CASE
    d.mkdir(parents=True)
    (d / "bos.docx").write_bytes(b"not a zip")
    job = pipeline.process(root, d / "bos.docx", store.load_settings())
    assert job["status"] == "error"


# ---------------------------------------------------------------- restore
def test_restore_from_answers_folder(k):
    root, layout, pipeline, store = k
    pipeline.process(root, drop(root, layout, "dilekce_01.txt"), store.load_settings())
    release_all(root, pipeline, store)
    a = root / layout.ANSWERS / CASE
    a.mkdir(parents=True)
    (a / "taslak.md").write_text("[AD SOYAD-1] adına, [T.C. KIMLIK NO-1] numarasıyla.", encoding="utf-8")
    res = pipeline.restore_file(root, a / "taslak.md")
    assert res["restored"] == 2
    t = Path(res["path"]).read_text(encoding="utf-8")
    assert NAMES[0] in t or any(n in t for n in NAMES)
    assert HARD[0] in t
    assert pipeline.restore_file(root, a / "taslak.md") == {"skipped": True}


def test_restore_needs_a_case_when_labels_fit_several(k):
    root, layout, pipeline, store = k
    for case in ("Dava A", "Dava B"):
        pipeline.process(root, drop(root, layout, "dilekce_01.txt", case=case), store.load_settings())
        release_all(root, pipeline, store, case)
    with pytest.raises(pipeline.Ambiguous):
        pipeline.restore_text(root, "[AD SOYAD-1] için taslak", None)
    assert pipeline.restore_text(root, "[AD SOYAD-1] için taslak", "Dava B")["restored"] == 1
    (root / layout.ANSWERS / "x.txt").write_text("[AD SOYAD-1]", encoding="utf-8")
    assert "error" in pipeline.restore_file(root, root / layout.ANSWERS / "x.txt")


# ---------------------------------------------------------------- audit
def test_audit_has_no_personal_data(k):
    root, layout, pipeline, store = k
    pipeline.process(root, drop(root, layout, "dilekce_01.txt", dst="Emal YILDIRIM dilekce.txt"), store.load_settings())
    release_all(root, pipeline, store)
    raw = json.dumps(store.audit_rows(CASE), ensure_ascii=False) + store.audit_csv(CASE)
    for v in HARD + NAMES + [CASE]:
        assert v.casefold() not in raw.casefold(), v
    assert [r["event"] for r in store.audit_rows(CASE)] == ["masked", "released"]


def test_job_store_is_encrypted(k):
    root, layout, pipeline, store = k
    pipeline.process(root, drop(root, layout, "dilekce_01.txt"), store.load_settings())
    for f in (store.home() / "jobs").iterdir():
        raw = f.read_bytes()
        assert raw.startswith(b"KJ1") and NAMES[0].encode() not in raw


# ---------------------------------------------------------------- watcher + API
def test_watcher_waits_for_a_stable_file(k):
    root, layout, pipeline, store = k
    from katip_klasor.watcher import Watcher
    w = Watcher()
    drop(root, layout, "dilekce_01.txt")
    assert w.scan_once() == 0      # first sight: size not yet known to be stable
    assert w.scan_once() == 1
    assert w.scan_once() == 0      # same content: not masked again


def test_api_needs_token(k):
    root, layout, pipeline, store = k
    from katip_klasor import server
    url, srv, _ = server.serve(0, token="tok")
    base = url.split("/?")[0]
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/api/state")
        assert e.value.code == 403
        req = urllib.request.Request(base + "/api/state", headers={"X-Katip-Token": "tok"})
        st = json.loads(urllib.request.urlopen(req).read())
        assert st["root"] == str(root) and "court" in st["profiles"]
        assert b"Katip" in urllib.request.urlopen(base + "/").read()
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/../pyproject.toml")
    finally:
        srv.shutdown()
