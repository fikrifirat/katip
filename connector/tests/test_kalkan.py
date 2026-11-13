"""End-to-end tests for the local connector, the vault and the relay.

Run:  cd connector && python -m pytest -q
"""
from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest

HERE = Path(__file__).parent
FIX = HERE / "fixtures"
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

GOLD = json.loads((FIX / "dilekce_01.gold.json").read_text(encoding="utf-8"))
HARD_IDS = {"TCKN", "PHONE", "EMAIL", "IBAN"}  # values that must never get through


def _model_available():
    import importlib.util
    return all(importlib.util.find_spec(m) for m in ("onnxruntime", "numpy")) and os.environ.get("KATIP_MODEL") != "none"


MODEL = _model_available()


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "katip"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    monkeypatch.delenv("KATIP_VAULT_MEMORY_ONLY", raising=False)
    from katip_kalkan import vault
    vault._memory.clear()
    return tmp_path


def _gold_left(text: str) -> list[str]:
    return [g["text"] for g in GOLD if g["text"] in text]


# ------------------------------------------------------------------ masking
@pytest.mark.parametrize("ext", ["txt", "docx", "udf"])
def test_mask_file_formats(ext):
    from katip_kalkan import core
    doc = core.mask_file(str(FIX / f"dilekce_01.{ext}"), "2026/101")
    text = doc["masked_text"]
    assert "[AD SOYAD-1]" in text and "[T.C. KİMLİK NO-1]" in text
    assert not [g for g in GOLD if g["entity_type"] in HARD_IDS and g["text"] in text]
    if MODEL:  # rules + Katip Mask Nano: every value in this file is masked
        assert _gold_left(text) == [] and "YILDIRIM" not in text, _gold_left(text)
    else:  # rules only: the all-caps surname "YILDIRIM" is the known miss
        assert set(_gold_left(text)) <= {"Emal YILDIRIM"}, _gold_left(text)
    assert "Yiğitalp" not in text and "Tekinalp" not in text  # caught once, masked everywhere (propagation)
    assert doc["file_name"] == f"dilekce 01.{ext}"  # only safe words of the file name are echoed


def test_placeholders_stable_across_documents_of_a_matter():
    from katip_kalkan import core
    a = core.mask_file(str(FIX / "dilekce_01.txt"), "2026/7")["masked_text"]
    b = core.mask_file(str(FIX / "dilekce_01.docx"), "2026/7")["masked_text"]
    assert a.split("\n")[2] == b.split("\n")[2] or "[AD SOYAD-1]" in b


def test_restore_roundtrip(home):
    from katip_kalkan import core
    doc = core.mask_file(str(FIX / "dilekce_01.txt"), "m1")
    answer = "Müvekkilimiz [AD SOYAD-1] adına, [T.C. KİMLİK NO-1] numaralı kimlikle başvurulmuştur."
    out = home / "out" / "cevap.txt"
    res = core.restore_to_file(answer, str(out), "m1")
    assert res == {"output_path": str(out), "placeholders_restored": 2}
    restored = out.read_text(encoding="utf-8")
    assert ("Müvekkilimiz Emal YILDIRIM adına" if MODEL else "Müvekkilimiz Emal") in restored
    assert "75428707268" in restored
    assert oct(out.stat().st_mode & 0o777) == "0o600"
    with pytest.raises(FileExistsError):
        core.restore_to_file(answer, str(out), "m1")


def test_write_masked_copy_docx():
    from katip_kalkan import core
    src = FIX / "dilekce_01.docx"
    res = core.write_redacted(str(src), "m2")
    out = src.with_name(f"{src.stem}.maskeli{src.suffix}")
    assert "output_path" not in res and res["name"] == "dilekce 01.maskeli.docx"
    try:
        with zipfile.ZipFile(out) as z:
            xml = z.read("word/document.xml").decode()
        assert "75428707268" not in xml and "Tekinalp" not in xml
    finally:
        out.unlink()


def test_allowed_dirs(monkeypatch, home):
    from katip_kalkan import core
    monkeypatch.setenv("KATIP_ALLOWED_DIRS", str(home))
    with pytest.raises(PermissionError):
        core.mask_file(str(FIX / "dilekce_01.txt"))


# ------------------------------------------------------------------ vault
def test_vault_is_encrypted_and_name_is_hashed(home):
    from katip_kalkan import core
    core.mask_file(str(FIX / "dilekce_01.txt"), "Yıldırım işçilik davası")
    files = list((home / "katip" / "vault").glob("*"))
    assert len(files) == 1
    raw = files[0].read_bytes()
    assert raw.startswith(b"KV1")
    for needle in (b"Emal", "Tekinalp".encode(), "Yıldırım".encode(), b"75428707268", b"AD SOYAD"):
        assert needle not in raw and needle not in files[0].name.encode()


def test_vault_tamper_is_detected(home):
    from katip_kalkan import core, vault
    core.mask_file(str(FIX / "dilekce_01.txt"), "m3")
    f = next((home / "katip" / "vault").glob("*.bin"))
    raw = bytearray(f.read_bytes())
    raw[-1] ^= 1
    f.write_bytes(bytes(raw))
    with pytest.raises(Exception):
        vault.open_vault("m3")


def test_memory_only_mode_writes_nothing(monkeypatch, home):
    from katip_kalkan import core, vault
    monkeypatch.setattr(vault, "AESGCM", None)
    core.mask_file(str(FIX / "dilekce_01.txt"), "m4")
    assert not (home / "katip" / "vault").exists() or not list((home / "katip" / "vault").iterdir())
    assert "memory only" in core.status()["vault"]


def test_forget(home):
    from katip_kalkan import core
    core.mask_file(str(FIX / "dilekce_01.txt"), "m5")
    assert core.forget_matter("m5") == {"deleted": True}
    out = home / "x.txt"
    core.restore_to_file("[AD SOYAD-1]", str(out), "m5")
    assert out.read_text() == "[AD SOYAD-1]"


# ------------------------------------------------------------------ local MCP over stdio
def _rpc(proc, mid, method, params=None):
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}}) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def test_stdio_server_end_to_end(home):
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.Popen([sys.executable, "-m", "katip_kalkan.local_server"], cwd=ROOT, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        init = _rpc(proc, 1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                            "clientInfo": {"name": "test", "version": "0"}})
        assert init["result"]["protocolVersion"] == "2025-06-18"
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        tools = _rpc(proc, 2, "tools/list")["result"]["tools"]
        names = {t["name"] for t in tools}
        assert {"mask_file", "restore_to_file", "write_masked_copy", "forget_matter", "katip_status"} <= names
        for t in tools:  # directory rules: title + readOnlyHint/destructiveHint on every tool
            a = t["annotations"]
            assert a["title"] and isinstance(a["readOnlyHint"], bool) and isinstance(a["destructiveHint"], bool)
        r = _rpc(proc, 3, "tools/call", {"name": "mask_file", "arguments": {"path": str(FIX / "dilekce_01.udf"),
                                                                             "matter": "e2e"}})["result"]
        wire = json.dumps(r, ensure_ascii=False)
        assert not r["isError"] and "[AD SOYAD-1]" in wire
        assert "75428707268" not in wire and "Tekinalp" not in wire
        out = home / "final.txt"
        r = _rpc(proc, 4, "tools/call", {"name": "restore_to_file", "arguments": {
            "text": "Davacı [AD SOYAD-1]", "output_path": str(out), "matter": "e2e"}})["result"]
        assert "Emal" not in json.dumps(r, ensure_ascii=False)  # real values never go back to the model
        assert out.read_text(encoding="utf-8") == ("Davacı Emal YILDIRIM" if MODEL else "Davacı Emal")
        bad = _rpc(proc, 5, "tools/call", {"name": "mask_file", "arguments": {"path": "/nope.docx"}})["result"]
        assert bad["isError"]
        assert _rpc(proc, 6, "nope")["error"]["code"] == -32601
    finally:
        proc.stdin.close()
        stderr = proc.stderr.read()
        proc.wait(timeout=5)
    assert "Emal" not in stderr and "75428707268" not in stderr


# ------------------------------------------------------------------ relay (ChatGPT path)
@pytest.fixture
def relay(monkeypatch):
    from katip_kalkan import relay as r
    monkeypatch.setattr(r, "STORE", r.DropStore())
    srv = r.serve("127.0.0.1", 0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield r, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _post(url, body):
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read() or b"null")


def test_relay_share_open_once(relay, caplog):
    r, url = relay
    from katip_kalkan.cli import share
    caplog.set_level(logging.INFO, logger="katip.relay")
    code = share(str(FIX / "dilekce_01.docx"), url, "rel")
    assert code.startswith("katip-")
    # the relay holds ciphertext only
    stored = b"".join(v["ct"] for v in r.STORE._d.values())
    assert b"AD SOYAD" not in stored and b"75428707268" not in stored

    st, init = _post(url + "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                    "params": {"protocolVersion": "2025-11-25"}})
    assert st == 200 and init["result"]["serverInfo"]["name"] == "katip-relay"
    assert _post(url + "/mcp", {"jsonrpc": "2.0", "method": "notifications/initialized"})[0] == 202
    call = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "open_masked_document", "arguments": {"share_code": f"Kod: {code}"}}}
    _, res = _post(url + "/mcp", call)
    body = res["result"]["structuredContent"]
    assert "[AD SOYAD-1]" in body["masked_text"] and "75428707268" not in body["masked_text"]
    _, again = _post(url + "/mcp", call)
    assert again["result"]["isError"] and "expired or was already used" in again["result"]["content"][0]["text"]
    assert len(r.STORE) == 0
    logs = caplog.text
    assert code.split(".")[1] not in logs and code.split(".")[0][6:] not in logs and "SOYAD" not in logs


def test_relay_wrong_key_and_expiry(relay, monkeypatch):
    r, url = relay
    from katip_kalkan import vault
    key, nonce, ct = vault.seal_for_relay(json.dumps({"masked_text": "x"}))
    _, drop = _post(url + "/v1/drops", {"nonce": vault.b64u(nonce), "ciphertext": vault.b64u(ct)})
    wrong = f"katip-{drop['id']}.{vault.b64u(os.urandom(16))}"
    with pytest.raises(ValueError, match="could not be opened"):
        r.open_masked_document(wrong)
    _, drop = _post(url + "/v1/drops", {"nonce": vault.b64u(nonce), "ciphertext": vault.b64u(ct)})
    import time
    monkeypatch.setattr(time, "time", lambda: 10**12)
    with pytest.raises(ValueError, match="expired"):
        r.open_masked_document(f"katip-{drop['id']}.{vault.b64u(key)}")


def test_relay_upload_token(relay, monkeypatch):
    import urllib.error
    r, url = relay
    monkeypatch.setenv("KATIP_RELAY_UPLOAD_TOKEN", "s3cret")
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(url + "/v1/drops", {"nonce": "AAAAAAAAAAAAAAAA", "ciphertext": "A" * 40})
    assert e.value.code == 401


# ------------------------------------------------------------------ name model and new rules from main
@pytest.mark.skipif(not MODEL, reason="onnxruntime not installed")
def test_bundled_model_is_used():
    from katip_kalkan import core, ner
    st = core.status()
    assert "katip-mask-nano-tr-v1.1" in st["engine"] and ner.trust() == 0.5


def test_rules_only_switch(monkeypatch):
    from katip_kalkan import core, ner
    monkeypatch.setenv("KATIP_MODEL", "none")
    ner._cache.clear()
    assert core.status()["engine"].startswith("rules only")
    ner._cache.clear()


def test_wordpiece_matches_hf_tokenizers():
    tk = pytest.importorskip("tokenizers")
    from katip_kalkan.ner import WORD, WordPiece
    folder = ROOT / "katip_kalkan" / "models" / "katip-mask-nano-tr-v1.1"
    ref = tk.Tokenizer.from_file(str(folder / "tokenizer.json"))
    wp = WordPiece(json.loads((folder / "tokenizer.json").read_text(encoding="utf-8")))
    text = (FIX / "dilekce_01.txt").read_text(encoding="utf-8") + " Ahmet'in Müller-Lüdenscheidt O'Neil İĞNE café 1.234,56"
    for m in WORD.finditer(text):
        assert wp.encode(m.group(0)) == ref.encode(m.group(0), add_special_tokens=False).ids, m.group(0)


def test_foreign_client_ids(tmp_path):
    from katip_kalkan import core
    f = tmp_path / "yabanci.txt"
    f.write_text("Müvekkil Mohammad Reza Hosseini, Yabancı Kimlik No: 99123456782, pasaport no: U12345678, "
                 "Bağdat Cad. No:12 D:4 Kadıköy/İstanbul adresinde ikamet etmektedir.", encoding="utf-8")
    doc = core.mask_file(str(f), "foreign")
    text = doc["masked_text"]
    assert "99123456782" not in text and "U12345678" not in text
    assert "[YABANCI KİMLİK NO-1]" in text or "YKN" in doc["entity_counts"]
    if MODEL:
        assert "Hosseini" not in text, text


def test_udf_signature_is_dropped(tmp_path):
    from katip_kalkan import core
    src = tmp_path / "imzali.udf"
    with zipfile.ZipFile(FIX / "dilekce_01.udf") as zin, zipfile.ZipFile(src, "w") as zout:
        for i in zin.infolist():
            zout.writestr(i, zin.read(i))
        zout.writestr("sign.sgn", b"PKCS7 Av. Yigitalp Tekinalp serial 123")
    doc = core.mask_file(str(src), "sig")  # the signature is not text: never sent
    assert "Tekinalp" not in json.dumps(doc, ensure_ascii=False)
    core.write_redacted(str(src), "sig")
    out = src.with_name(f"{src.stem}.maskeli{src.suffix}")
    with zipfile.ZipFile(out) as z:
        assert not [n for n in z.namelist() if n.lower().endswith(".sgn")]
        assert "75428707268" not in z.read("content.xml").decode("utf-8")


# ------------------------------------------------------------------ profiles (src/app.js PROFILES)
def test_profiles_ladder(tmp_path):
    from katip_kalkan import core
    f = tmp_path / "karar.txt"
    f.write_text("İstanbul 3. Asliye Hukuk Mahkemesi 2023/145 Esas, 2024/77 Karar sayılı dosyada davacı "
                 "Ayşe Kaya, Bağdat Caddesi No:12 D:4 Kadıköy/İstanbul adresinde oturmaktadır. "
                 "Vekili Av. Mehmet Demir (İstanbul Barosu sicil no 34507). Karar tarihi 12.03.2024.", encoding="utf-8")
    court = core.mask_file(str(f), "p1", profile="court")["masked_text"]
    ai = core.mask_file(str(f), "p2")["masked_text"]  # default profile
    anon = core.mask_file(str(f), "p3", profile="anon")["masked_text"]
    for t in (court, ai, anon):
        assert "Ayşe Kaya" not in t and "Mehmet Demir" not in t
    assert "Bağdat Caddesi" in court and "2023/145" in court      # court: street and case number readable
    assert "Bağdat Caddesi" not in ai and "2023/145" not in ai    # ai: whole address and case number masked
    assert "12.03.2024" in ai and "12.03.2024" not in anon        # anon: dates too
    assert "Asliye Hukuk" not in anon
    with pytest.raises(ValueError):
        core.mask_file(str(f), "p4", profile="nope")


# ------------------------------------------------------------------ local OCR (scans and phone photos)
def _ocr_ready():
    from katip_kalkan import ocr
    return bool(ocr.available()) and all(__import__("importlib").util.find_spec(m) for m in ("pymupdf", "numpy"))


@pytest.mark.skipif(not _ocr_ready(), reason="no OCR installed")
def test_scanned_pdf_is_read_and_masked():
    from katip_kalkan import core
    doc = core.mask_file(str(FIX / "dilekce_01.scan.pdf"), "scan")
    t = doc["masked_text"]
    assert "ocr" in doc and "MAHKEME" in t.upper() and "[AD SOYAD-1]" in t
    for g in GOLD:
        assert g["text"] not in t, g["text"]


@pytest.mark.skipif(not _ocr_ready(), reason="no OCR installed")
def test_handwritten_photo_form():
    from katip_kalkan import core
    gold = json.loads((FIX / "kira_foto_01.gold.json").read_text(encoding="utf-8"))["entities"]
    doc = core.mask_file(str(FIX / "kira_foto_01.pdf"), "photo")
    t = doc["masked_text"]
    assert "paddle" in doc["ocr"] or "tesseract" in doc["ocr"]
    left = [g["text"] for g in gold if g["text"] and g["text"] in t]
    assert left == [], left  # synthetic, handwritten in blue ballpoint fonts (lab/photo_forms)


def test_default_folder_created_and_opened(tmp_path, monkeypatch):
    import subprocess
    from katip_kalkan import core
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setenv("KATIP_ALLOWED_DIRS", "${user_config.allowed_dir}")  # unfilled setting
    monkeypatch.setenv("KATIP_FOLDER", str(tmp_path / "katip-documents"))
    r = core.open_folder()
    assert (tmp_path / "katip-documents").is_dir() and r["opened"] and calls[0][-1] == r["folder"]
    assert r["link"].startswith("file://")
    monkeypatch.setenv("KATIP_ALLOWED_DIRS", str(tmp_path / "picked"))
    assert core.folder() == (tmp_path / "picked").resolve() and core.status()["folder_link"].endswith("/picked")


def test_file_names_stay_private(tmp_path, monkeypatch):
    import shutil
    import unicodedata
    from katip_kalkan import core, names
    root = tmp_path / "katip-documents"
    root.mkdir()
    monkeypatch.setenv("KATIP_ALLOWED_DIRS", "${HOME}/katip-documents")  # left unexpanded by the host
    monkeypatch.setenv("HOME", str(tmp_path))
    nfd = unicodedata.normalize("NFD", "Reza Karimi - Vatandaşlık Dava Dilekçesi.udf")  # how macOS stores it
    shutil.copy(FIX / "dilekce_01.udf", root / nfd)
    listing = core.list_files()
    assert len(listing["files"]) == 1
    f = listing["files"][0]
    assert "Reza" not in str(listing) and "Karimi" not in str(listing)
    assert f["name"] == "… - Vatandaşlık Dava Dilekçesi.udf"
    r = core.mask_file(file_id=f["file_id"], matter="names")
    assert "Karimi" not in str({k: v for k, v in r.items() if k != "masked_text"})
    r2 = core.mask_file(str(root / unicodedata.normalize("NFC", nfd)), matter="names")
    assert r2["file_id"] == f["file_id"]
    w = core.write_redacted(file_id=f["file_id"], matter="names")
    assert "Karimi" not in str(w)
    assert names.safe_title("Ara Miras İsmail Veli kira") == "… kira"
