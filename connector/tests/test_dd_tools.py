"""Katip DD inside Kalkan (stdio) and the relay (ChatGPT). All names and numbers are invented.

Run:  cd connector && python -m pytest -q tests/test_dd_tools.py
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from katip_kalkan.dd.store import Store  # noqa: E402

PERSON = {"rid": "6415-m7-ic:1:aaaa", "source": "masak", "list": "6415-m7-ic", "kind": "person",
          "names": ["AYŞE NUR KOCABEY", "A. N. KOCABEY"], "ids": ["12345678901"], "birth": "4/13/1978",
          "nationality": "TÜRKİYE", "organisation": "TEST", "decision": "2021-04-07 / 31447",
          "url": "https://masak.hmb.gov.tr/7madde", "gazette_url": "https://www.resmigazete.gov.tr/eskiler/2021/04/20210407.htm",
          "raw": {"ad_soyad_unvan": "AYŞE NUR KOCABEY", "tckn_vkn": "12345678901", "anne_adı": "GÜLTEN",
                  "baba_adı": "YUSUF", "dogum_tarihi": "4/13/1978"}}
NOTICE = {"rid": "ilan:1", "source": "ilan", "kind": "notice", "title": "Konkordato mühlet kararı",
          "names": ["Konkordato mühlet kararı"], "date": "2026-11-19T00:00:00", "url": "https://www.ilan.gov.tr/ilan/1/x",
          "full_text": True,
          "text": "Konkordato talep eden KUZEYRÜZGARI TEKSTİL ANONİM ŞİRKETİ vergi no 1234567890 ile müşterek talepçi 98765432109 TC kimlik "
                  "nolu kişi hakkında geçici mühlet verilmiştir."}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path))
    st = Store()
    st.replace_source("masak", [PERSON], {"lists": {}}, "t0")
    st.replace_source("ilan", [NOTICE], {}, "t0")
    return st


def kalkan():
    from katip_kalkan import local_server
    return local_server.build()


def call(server, name, args):
    res = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})["result"]
    if res.get("isError"):
        return res, res["content"][0]["text"]
    return res, (res.get("structuredContent") or json.loads(res["content"][0]["text"]))


def names(server):
    return {t["name"]: t for t in server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]}


def test_kalkan_lists_dd_tools():
    tools = names(kalkan())
    for n in ("dd_screen", "dd_record", "dd_sources", "dd_update", "dd_ilan_lookup"):
        assert n in tools, n
    assert tools["dd_screen"]["annotations"]["readOnlyHint"] is True
    assert tools["dd_update"]["annotations"]["openWorldHint"] is True
    assert "mask_file" in tools  # the old tools are still there


def test_screen_returns_source_record_without_third_party_ids(store):
    res, out = call(kalkan(), "dd_screen", {"name": "Ayse Kocabey", "id_number": "12345678901"})
    assert not res["isError"]
    hit = out["hits"][0]
    assert hit["listed_name"] == "AYŞE NUR KOCABEY" and hit["source_url"].startswith("https://masak")
    assert hit["id_number_matches"] is True
    blob = json.dumps(out, ensure_ascii=False)
    assert "12345678901" not in blob and "GÜLTEN" not in blob and "YUSUF" not in blob
    assert "not a clearance" in out["how_to_read"]


def test_screen_finds_company_in_notice_and_masks_co_applicant_id(store):
    _, out = call(kalkan(), "dd_screen", {"name": "kuzeyruzgari tekstil"})
    hit = next(h for h in out["hits"] if h["source"] == "ilan")
    assert hit["band"] == "match" and hit["date"] == "2026-11-19"
    blob = json.dumps(out, ensure_ascii=False)
    assert "98765432109" not in blob
    assert "1234567890" in blob  # a company's tax number is not personal data and helps DD


def test_id_masking_keeps_company_vkn_only():
    from katip_kalkan.dd.normalize import mask_ids, vkn_ok
    assert vkn_ok("1234567890") and not vkn_ok("1234567891")
    t = "X A.Ş. vergi no 1234567890, ortak T.C. 12345678901, tel 5321234567, vergi no 1234567891"
    m = mask_ids(t)
    assert "1234567890," in m and "12345678901" not in m
    assert "5321234567" not in m  # 10 digits without a tax-number label: could be a phone
    assert "1234567891" not in m  # fails the VKN checksum


def test_screen_says_which_sources_are_empty(store):
    _, out = call(kalkan(), "dd_screen", {"name": "Nobody Here"})
    assert out["hits"] == [] and "gazette" in out["not_covered"]


def test_record_is_redacted(store):
    _, out = call(kalkan(), "dd_record", {"record_id": PERSON["rid"]})
    assert "12345678901" not in json.dumps(out, ensure_ascii=False)


def test_screen_needs_a_name_or_id(store):
    res, _ = call(kalkan(), "dd_screen", {"name": "  "})
    assert res["isError"]


def test_relay_has_no_dd_tools_unless_switched_on(store, monkeypatch):
    monkeypatch.delenv("KATIP_RELAY_DD", raising=False)
    from katip_kalkan import relay
    relay = importlib.reload(relay)
    assert "dd_screen" not in names(relay.MCP)


def test_relay_dd_is_read_only_and_redacted(store, monkeypatch):
    monkeypatch.setenv("KATIP_RELAY_DD", "1")
    from katip_kalkan import relay
    relay = importlib.reload(relay)
    tools = names(relay.MCP)
    assert {"dd_screen", "dd_sources"} <= set(tools)
    assert "dd_update" not in tools and "dd_ilan_lookup" not in tools  # the operator refreshes the index, not callers
    assert all(isinstance(tools["dd_screen"]["annotations"][k], bool) for k in ("readOnlyHint", "destructiveHint", "openWorldHint"))
    _, out = call(relay.MCP, "dd_screen", {"name": "Ayşe Nur Kocabey"})
    assert out["hits"] and "12345678901" not in json.dumps(out, ensure_ascii=False)
    monkeypatch.delenv("KATIP_RELAY_DD")
    importlib.reload(relay)


def test_cli_dd_search_and_status(store, capsys):
    from katip_kalkan import cli
    cli.main(["dd", "search", "Ayşe Kocabey", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["hits"][0]["listed_name"] == "AYŞE NUR KOCABEY"
    assert "12345678901" in json.dumps(out)  # the lawyer's own terminal sees the full record
    cli.main(["dd", "status"])
    assert "masak" in capsys.readouterr().out


def test_masak_company_keeps_vkn_person_does_not(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path))
    firm = {"rid": "6415-m7-ic:2:bbbb", "source": "masak", "list": "6415-m7-ic", "kind": "unknown",
            "names": ["GÜNEYRÜZGARI GIDA ANONİM ŞİRKETİ"], "ids": ["9876543217"], "url": "https://masak.hmb.gov.tr/7madde",
            "raw": {"ad_soyad_unvan": "GÜNEYRÜZGARI GIDA ANONİM ŞİRKETİ", "tckn_vkn": "9876543217"}}
    Store().replace_source("masak", [PERSON, firm], {"lists": {}}, "t0")
    _, out = call(kalkan(), "dd_screen", {"name": "Güneyrüzgarı Gıda A.Ş."})
    assert out["hits"][0]["source_record"]["tckn_vkn"] == "9876543217"
    _, out = call(kalkan(), "dd_record", {"record_id": PERSON["rid"]})
    assert out["raw"]["tckn_vkn"] == "[gizlendi]"
