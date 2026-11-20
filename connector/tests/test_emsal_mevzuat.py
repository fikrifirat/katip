"""Offline tests for emsal_ara, geri_bildirim and mevzuat_bak (the court's service is replaced by a fake).

Run:  cd connector && python -m pytest -q tests/test_emsal_mevzuat.py
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from katip_kalkan import emsal, mevzuat, vault  # noqa: E402

DOC = ("Şüpheli ████ ████. Müvekkil evinde 10 kök kenevir yetiştirmiştir; 97 gram esrar kişisel kullanım "
       "sınırındadır. Eylem TCK 188 değil TCK 191 kapsamındadır; ticareti gösteren delil yoktur.")
DECISIONS = {
    "111": ("Ceza Genel Kurulu", "2018/208", "2020/522", "15.12.2020",
            "Ceza Genel Kurulu 2018/208 E. , 2020/522 K.\n\nEle geçirilen 6,4 gram esrarın miktar itibarıyla kişisel "
            "kullanım sınırları içinde kalması, hassas terazi bulunmaması karşısında eylem kullanmak için "
            "bulundurma suçunu oluşturur. TCK 191.\n\nHükmün BOZULMASINA karar verildi."),
    "222": ("10. Ceza Dairesi", "2021/1", "2022/2", "01.01.2022",
            "10. Ceza Dairesi 2021/1 E. , 2022/2 K.\n\nKira bedelinin tespiti davasında hakkaniyet indirimi yapılır. "
            "ONANMASINA."),
    "333": ("10. Ceza Dairesi", "2021/5", "2022/6", "01.01.2022",      # numbers in the list don't match the text
            "10. Ceza Dairesi 2019/99 E. , 2020/98 K.\n\nKenevir kişisel kullanım sınırı esrar. BOZULMASINA."),
}


@pytest.fixture(autouse=True)
def fake_court(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "katip"))
    sent = []

    def post(endpoint, data):
        sent.append((endpoint, data))
        if endpoint == "searchDocuments":
            rows = [{"documentId": i, "birimAdi": c, "esasNo": e, "kararNo": k, "kararTarihiStr": d}
                    for i, (c, e, k, d, _) in DECISIONS.items()
                    if not data.get("birimAdi") or data["birimAdi"] == c]
            return {"emsalKararList": rows, "total": len(rows)}
        t = DECISIONS[data["documentId"]][4]
        return {"content": base64.b64encode(f"<p>{t}</p>".encode()).decode(), "mimeType": "text/html"}

    monkeypatch.setattr(emsal, "_post", post)
    monkeypatch.setattr(emsal, "_stopped", None)
    return sent


def test_safe_words_refuses_identifiers():
    assert emsal.safe_words("kenevir kişisel kullanım", set()) == ["kenevir", "kişisel", "kullanım"]
    for bad in ("Ahmet kenevir", "kenevir 97", "kenevir, esrar", "ab", "a b c d e f", ""):
        with pytest.raises(ValueError):
            emsal.safe_words(bad, set())


def test_masked_values_never_leave(fake_court):
    v = vault.open_vault("m1")
    v.label_for("PERSON", "Ayşe Kenevirci")
    v.save()
    with pytest.raises(ValueError):
        emsal.find(["kenevirci kullanım"], "m1", DOC)
    assert fake_court == []                                   # refused before anything was sent


def test_find_ranks_verifies_and_logs(fake_court):
    r = emsal.find(["kenevir kişisel kullanım"], "default", DOC, None, 5)
    ids = [x["link"].rsplit("/", 1)[1] for x in r["results"]]
    assert ids[0] == "111" and "333" not in ids               # unverifiable numbers are dropped
    assert r["dropped_unverified"] == 1
    assert r["results"][0]["general_assembly"] and r["results"][0]["outcome"] == "bozma"
    assert r["statutes_in_document"] == ["TCK 188", "TCK 191"]
    sent_phrases = [d["phrase"] for e, d in fake_court if e == "searchDocuments"]
    assert all(set(p.replace("+", "").split()) <= set("kenevir kişisel kullanım ticareti kullanmak".split())
               for p in sent_phrases)                         # only keywords, incl. the statute contrast query
    assert not any("97" in json.dumps(d) or "████" in json.dumps(d) for _, d in fake_court)
    log = (emsal.home() / "requests.log").read_text(encoding="utf-8")
    assert "kenevir" in log


def test_contrast_query_from_statute_headings():
    assert emsal.statutes(DOC) == ["TCK 188", "TCK 191"]
    assert emsal.contrast_queries(["TCK 188", "TCK 191"], DOC) == ["ticareti kullanmak"]


def test_grade_saved_locally_and_note_checked():
    r = emsal.find(["kenevir kişisel kullanım"], "default", DOC, None, 3)
    rid = r["results"][0]["result_id"]
    g = emsal.grade(rid, 2, True, "kişisel kullanım sınırını tartışıyor")
    assert g["saved"] and g["grades_on_this_computer"] == 1
    rec = json.loads((emsal.home() / "grades.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert rec["decision_id"] == "111" and rec["relevance"] == 2 and rec["rank"] == 1
    with pytest.raises(ValueError):
        emsal.grade(rid, 2, True, "TC 12345678901")
    with pytest.raises(ValueError):
        emsal.grade(rid, 3)
    with pytest.raises(ValueError):
        emsal.grade("nope-1", 1)


def test_verified_accepts_old_general_assembly_numbers():
    h = {"esas": "2012/1335", "karar": "2013/423"}
    assert emsal.verified(h, "Ceza Genel Kurulu 2012/10-1335 E. , 2013/423 K.")
    assert not emsal.verified(h, "Ceza Genel Kurulu 2012/10-13351 E. , 2013/423 K.")


def test_mevzuat_lookup_and_check():
    r = mevzuat.lookup("TBK 344")
    c = r["citations"][0]
    assert c["verdict"] == "OK" and c["law_no"] == "6098" and "kira bedeli" in c["article_text"]
    r = mevzuat.lookup(text="TCK 191 ve BK 315 ile 6098 sayılı Kanun m. 999")
    verdicts = {x["cited_as"]: x["verdict"] for x in r["citations"]}
    assert verdicts["TCK 191"] == "OK"
    assert verdicts["BK 315"] == "LAW_REPEALED"
    assert verdicts["6098 sayılı Kanun m. 999"] == "NO_SUCH_ARTICLE"
    assert mevzuat.lookup(text="hiç atıf yok")["citations"] == []
    with pytest.raises(ValueError):
        mevzuat.lookup()


def test_tools_listed_with_hints():
    from katip_kalkan import local_server
    tools = {t.name: t for t in local_server.TOOLS}
    assert tools["emsal_ara"].annotations["openWorldHint"] is True
    assert tools["mevzuat_bak"].annotations["openWorldHint"] is False
    assert tools["geri_bildirim"].schema["required"] == ["result_id", "puan"]


def test_feedback_summary_and_export(tmp_path):
    r = emsal.find(["kenevir kişisel kullanım"], "default", DOC, None, 3)
    emsal.grade(r["results"][0]["result_id"], 2, True)
    emsal.grade(r["results"][1]["result_id"], 0, False)
    s = emsal.feedback(str(tmp_path / "out.json"))
    assert s["grades"] == 2 and s["on_point"] == 1 and s["mean_by_rank"] == {1: 2.0, 2: 0.0}
    b = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert b["format"] == "katip-emsal-feedback/1" and len(b["runs"]) == 1
    assert "████" not in json.dumps(b, ensure_ascii=False) and "97 gram" not in json.dumps(b, ensure_ascii=False)


def test_emsal_view_served_and_linked():
    from katip_kalkan import local_server
    srv = local_server.build()
    tools = {t["name"]: t for t in srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]}
    uri = tools["emsal_ara"]["_meta"]["ui"]["resourceUri"]
    assert "_meta" not in tools["mask_file"]
    init = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}})["result"]
    assert "resources" in init["capabilities"]
    listed = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "resources/list"})["result"]["resources"]
    assert [r["uri"] for r in listed] == [uri]
    c = srv.handle({"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": uri}})["result"]["contents"][0]
    assert c["mimeType"] == "text/html;profile=mcp-app"
    assert "geri_bildirim" in c["text"] and "ui/initialize" in c["text"]
    assert "http://" not in c["text"].replace("http://www.w3", "") and "fetch(" not in c["text"]   # the view never calls out
    assert srv.handle({"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": "ui://x"}})["error"]


def test_judged_again_latest_verdict_wins():
    r = emsal.find(["kenevir kişisel kullanım"], "default", DOC, None, 3)
    rid = r["results"][0]["result_id"]
    emsal.grade(rid, 0, False)
    g = emsal.grade(rid, 2, True)
    assert g["grades_on_this_computer"] == 1
    s = emsal.feedback()
    assert s["grades"] == 1 and s["on_point"] == 1
