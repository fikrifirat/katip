"""The ChatGPT side: the relay's research tools (emsal_ara, mevzuat_bak, geri_bildirim) and the results view.

Run:  cd connector && python -m pytest -q tests/test_relay_chatgpt.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from katip_kalkan import emsal, relay  # noqa: E402
from test_emsal_mevzuat import fake_court  # noqa: E402,F401  (autouse: the court's service is faked)

MASKED = ("Şüpheli [AD SOYAD-1] evinde 10 kök kenevir yetiştirmiştir; esrar kişisel kullanım sınırındadır. "
          "Eylem TCK 188 değil TCK 191 kapsamındadır.")


def call(name, args, i=1):
    return relay.MCP.handle({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                             "params": {"name": name, "arguments": args}})["result"]


def payload(res):
    return res.get("structuredContent") or json.loads(res["content"][0]["text"])


def test_tools_and_view_listed():
    tools = {t["name"]: t for t in relay.MCP.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]}
    assert set(tools) == {"open_masked_document", "emsal_ara", "mevzuat_bak", "geri_bildirim"}
    for t in tools.values():   # OpenAI requires explicit booleans
        assert all(isinstance(t["annotations"][k], bool) for k in ("readOnlyHint", "destructiveHint", "openWorldHint"))
    assert tools["emsal_ara"]["annotations"]["openWorldHint"] is True
    assert "not" not in tools["geri_bildirim"]["inputSchema"]["properties"]     # no free text on the server
    uri = tools["emsal_ara"]["_meta"]["ui"]["resourceUri"]
    assert all("_meta" not in t for n, t in tools.items() if n != "emsal_ara")  # only the render tool
    c = relay.MCP.handle({"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": uri}})
    c = c["result"]["contents"][0]
    assert c["mimeType"] == "text/html;profile=mcp-app" and "csp" not in c.get("_meta", {}).get("ui", {})
    assert "grades_note" in c["text"]


def test_emsal_on_the_relay_sends_only_keywords(fake_court):
    res = call("emsal_ara", {"sorgular": ["kenevir kişisel kullanım"], "baglam": MASKED, "adet": 3})
    assert not res.get("isError"), res
    out = payload(res)
    assert out["results"][0]["link"].endswith("/111") and out["statutes_in_document"] == ["TCK 188", "TCK 191"]
    assert "Katip'e gider" in out["grades_note"] and "this computer" not in out["note"]
    sent = json.dumps([d for _, d in fake_court], ensure_ascii=False)
    assert "AD SOYAD" not in sent and "10 kök" not in sent and "Şüpheli" not in sent


@pytest.mark.parametrize("args", [
    {"sorgular": ["Ahmet kenevir"]},
    {"sorgular": ["kenevir 97"]},
    {"sorgular": ["kenevir"], "baglam": "Müvekkil 12345678901 numaralı"},
    {"sorgular": ["kenevir"], "baglam": "yazışma ali@example.com adresinden"},
])
def test_refused_before_anything_is_sent(fake_court, args):
    assert call("emsal_ara", args)["isError"]
    assert fake_court == []


def test_verdict_from_the_view_is_saved_without_identity(fake_court):
    out = payload(call("emsal_ara", {"sorgular": ["kenevir kişisel kullanım"], "adet": 3}))
    rid = out["results"][0]["result_id"]
    g = payload(call("geri_bildirim", {"result_id": rid, "puan": 2, "atif_yapar": True}))
    assert g["saved"] and "grades_on_this_computer" not in g
    assert call("geri_bildirim", {"result_id": rid, "puan": 2, "not": "x"})["isError"]   # notes refused
    rec = json.loads((emsal.home() / "grades.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert rec["decision_id"] == "111" and rec["note"] == ""
    assert set(rec) <= {"at", "result_id", "decision_id", "decision", "queries", "rank", "relevance", "would_cite", "note"}


def test_mevzuat_on_the_relay():
    out = payload(call("mevzuat_bak", {"atif": "TBK 344"}))
    assert out["citations"][0]["verdict"] == "OK"


def test_upload_rate_limit():
    rl = relay.RateLimit(2)
    assert rl.allow("a") and rl.allow("a") and not rl.allow("a") and rl.allow("b")
