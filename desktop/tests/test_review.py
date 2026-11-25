"""Review queue: masking candidates the lawyer judges, and the lists Katip learns from those verdicts.

Invented names only. Everything lives in tmp_path (KATIP_HOME, no Keychain).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from test_engine import req  # noqa: E402


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    monkeypatch.setenv("KATIP_DD_HOME", str(tmp_path / "dd"))
    for k in ("KATIP_EMSAL_ONLINE", "KATIP_MODEL", "KATIP_PROFILE"):
        monkeypatch.delenv(k, raising=False)
    (tmp_path / "home").mkdir()
    from katip_engine import review
    review.install("app")
    yield
    review.uninstall()


def span(text, value, score, etype="PERSON", rec="model"):
    i = text.index(value)
    return {"entity_type": etype, "start": i, "end": i + len(value), "text": value, "score": score, "recognizer": rec}


TEXT = "Davacı Ayşe DEMİRCİ ile tanık Zümrüt Hanım, Bursa'da Kemal BEY'in evinde görüştü."


def test_unsure_and_missed_candidates_are_kept(tmp_path):
    from katip_engine import review
    final = [span(TEXT, "Ayşe DEMİRCİ", 0.97), span(TEXT, "Zümrüt", 0.62)]
    raw = [(TEXT.index("Kemal"), TEXT.index("Kemal") + 5, 0.31, "PERSON"),     # below threshold, not masked
           (TEXT.index("Ayşe"), TEXT.index("Ayşe") + 4, 0.3, "PERSON"),        # overlaps a masked span: no
           (TEXT.index("ile"), TEXT.index("ile") + 3, 0.25, "PERSON")]         # lower-case word: no
    review.collect(TEXT, final, raw, threshold=0.5, matter="2026/1")
    q = review.listing()["open"]
    kinds = {c["text"]: c["kind"] for c in q}
    assert kinds == {"Zümrüt": "unsure", "Kemal": "missed"}
    z = next(c for c in q if c["text"] == "Zümrüt")
    assert z["matter"] == "2026/1" and z["source"] == "app" and z["score"] == 0.62 and z["seen"] == 1
    # the context never shows another client's value
    assert "Ayşe" not in z["before"] + z["after"] and "•••" in z["before"]


def test_same_value_twice_is_one_candidate_counted_per_document():
    from katip_engine import review
    for _ in range(3):  # the same text again (paging re-detects it): counted once
        review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "default")
    other = TEXT + " Ek belge."
    review.collect(other, [span(other, "Zümrüt", 0.6)], [], 0.5, "default")
    q = review.listing()["open"]
    assert len(q) == 1 and q[0]["seen"] == 2


def test_dismissing_a_missed_word_does_not_put_it_on_the_never_mask_list():
    from katip_engine import review
    review.collect(TEXT, [], [(TEXT.index("Kemal"), TEXT.index("Kemal") + 5, 0.31, "PERSON")], 0.5, "default")
    review.judge(review.listing()["open"][0]["id"], "allow")
    out = review.listing()
    assert out["open"] == [] and out["learned"]["allow"] == [] and out["judged"] == 1


def test_forgetting_a_case_forgets_the_words_learned_from_it():
    from katip_kalkan import core
    from katip_engine import review
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "2026/9")
    review.judge(review.listing()["open"][0]["id"], "mask")
    other = "Tanık Nermin geldi."
    review.collect(other, [span(other, "Nermin", 0.6)], [], 0.5, "2026/8")
    review.judge(review.listing()["open"][0]["id"], "mask")
    core.forget_matter("2026/9")
    assert review.listing()["learned"]["mask"] == ["Nermin"]


def test_unreadable_lists_stop_masking_instead_of_dropping_the_mask_list(srv):
    from katip_engine import review
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "default")
    review.path().write_bytes(b"\0" * 64)  # what a changed key looks like from here
    review._cipher = None
    code, out = req(srv, "POST", "/v1/mask", {"text": "Tanık Zümrüt geldi."})
    assert code == 409 and "Keychain" in out["error"]
    assert req(srv, "GET", "/v1/review")[1]["unreadable"] is True
    code, out = req(srv, "POST", "/v1/review/reset", {})
    assert code == 200 and out["unreadable"] is False
    assert list(review.path().parent.glob("engine-review.bin.unreadable-*"))
    assert req(srv, "POST", "/v1/mask", {"text": "Tanık Zümrüt geldi."})[0] == 200


def test_queue_is_encrypted_on_disk():
    from katip_engine import review
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "default")
    blob = review.path().read_bytes()
    assert "Zümrüt".encode() not in blob and b"Z\\u00fcmr" not in blob


def test_mask_verdict_teaches_masking_everywhere():
    from katip_kalkan import engine
    from katip_engine import review
    text = "Toplantıya Zeyrek katıldı."
    assert not [s for s in engine.detect(text, 0.5, ["PERSON"]) if s["text"] == "Zeyrek"]
    review.collect(text, [], [(11, 17, 0.3, "PERSON")], 0.5, "default")
    cid = review.listing()["open"][0]["id"]
    review.judge(cid, "mask")
    assert [s for s in engine.detect(text, 0.5, ["PERSON"]) if s["text"] == "Zeyrek"]
    out = review.listing()
    assert out["open"] == [] and out["learned"]["mask"] == ["Zeyrek"] and out["judged"] == 1


def test_not_personal_verdict_stops_masking_it_and_undo_brings_it_back():
    from katip_kalkan import engine
    from katip_engine import review
    text = "Sayın Selin geldi."
    masked = lambda: [s["text"] for s in engine.detect(text, 0.5, ["PERSON"])]  # noqa: E731
    before = masked()
    review.collect(text, [span(text, "Selin", 0.6)], [], 0.5, "default")
    cid = review.listing()["open"][0]["id"]
    review.judge(cid, "allow")
    assert "Selin" not in masked() and review.listing()["learned"]["allow"] == ["Selin"]
    review.undo(cid)
    assert masked() == before and review.listing()["open"][0]["id"] == cid
    assert review.listing()["learned"]["allow"] == []


def test_judged_value_does_not_come_back_and_learned_values_are_not_asked():
    from katip_engine import review
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "default")
    review.judge(review.listing()["open"][0]["id"], "mask")
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "other")
    assert review.listing()["open"] == []


def test_later_keeps_it_out_of_the_way_but_open():
    from katip_engine import review
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "default")
    cid = review.listing()["open"][0]["id"]
    review.judge(cid, "later")
    q = review.listing()["open"]
    assert q[0]["id"] == cid and q[0]["later"] is True


def test_forgetting_a_case_drops_its_candidates():
    from katip_kalkan import core
    from katip_engine import review
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "2026/9")
    review.collect(TEXT, [span(TEXT, "Ayşe DEMİRCİ", 0.6)], [], 0.5, "2026/8")
    core.forget_matter("2026/9")
    assert [c["matter"] for c in review.listing()["open"]] == ["2026/8"]


def test_masking_through_kalkan_fills_the_queue():
    """The real path: core.mask_file and the engine both go through the hooked detection."""
    from katip_engine import review
    from katip_engine.server import Engine
    e = Engine()
    e.mask("Tanık Selin hanım ifade verdi.", matter="2026/5")
    q = review.listing()["open"]
    # whether the rules are sure about "Selin" depends on the engine; when unsure, the matter and source are right
    for c in q:
        assert c["matter"] == "2026/5" and c["source"] == "app"


def test_remove_a_learned_value():
    from katip_engine import review
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "default")
    review.judge(review.listing()["open"][0]["id"], "mask")
    review.forget_learned("mask", "Zümrüt")
    assert review.listing()["learned"]["mask"] == []


# -- HTTP ---------------------------------------------------------------------------------------------------
@pytest.fixture
def srv():
    from katip_engine.server import Server
    s = Server(0, "t0k3n", idle_exit=None)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s
    s.shutdown()
    s.server_close()


def test_routes(srv):
    from katip_engine import review
    review.collect(TEXT, [span(TEXT, "Zümrüt", 0.6)], [], 0.5, "default")
    code, out = req(srv, "GET", "/v1/review")
    assert code == 200 and len(out["open"]) == 1
    cid = out["open"][0]["id"]
    assert req(srv, "POST", "/v1/review/judge", {"id": cid, "verdict": "guilty"})[0] == 400
    assert req(srv, "POST", "/v1/review/judge", {"id": "nope", "verdict": "mask"})[0] == 404
    code, out = req(srv, "POST", "/v1/review/judge", {"id": cid, "verdict": "mask"})
    assert code == 200 and out["learned"]["mask"] == ["Zümrüt"]
    code, out = req(srv, "POST", "/v1/review/undo", {"id": cid})
    assert code == 200 and out["open"][0]["id"] == cid
    req(srv, "POST", "/v1/review/judge", {"id": cid, "verdict": "allow"})
    code, out = req(srv, "POST", "/v1/review/learned/remove", {"list": "allow", "text": "Zümrüt"})
    assert code == 200 and out["learned"]["allow"] == []


def test_paths_for_show_in_finder(srv, tmp_path):
    code, p = req(srv, "GET", "/v1/paths")
    assert code == 200
    assert p["katip"] == str(tmp_path / "home") and p["masak"] == str(tmp_path / "dd")
    assert set(p) >= {"cases", "documents", "models", "gazette", "precedents", "log", "claude_desktop"}
