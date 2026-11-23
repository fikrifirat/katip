"""Offline tests for katip_uyum. All data is invented. Run: python -m pytest lab/uyum/tests -q"""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from katip_uyum.docs import DOCS, render_all  # noqa: E402
from katip_uyum.model import QuestionnaireError, validate  # noqa: E402
from katip_uyum.rules import analyse  # noqa: E402

EXAMPLE = json.loads((ROOT / "examples" / "dd_harness.json").read_text(encoding="utf-8"))
TEMPLATE = json.loads((ROOT / "katip_uyum" / "template.json").read_text(encoding="utf-8"))


def ids(q):
    return {f.id: f for f in analyse(q).findings}


def q(**patch):
    x = copy.deepcopy(EXAMPLE)
    for path, value in patch.items():
        obj = x
        *parts, last = path.split("__")
        for p in parts:
            obj = obj[int(p)] if p.isdigit() else obj[p]
        obj[int(last) if last.isdigit() else last] = value
    return x


def test_example_and_template_validate():
    validate(EXAMPLE)
    validate(TEMPLATE)


def test_bad_reference_is_an_error():
    bad = q(agents__0__models=["nope"])
    with pytest.raises(QuestionnaireError, match="unknown vendors id 'nope'"):
        validate(bad)


def test_bad_enum_is_an_error():
    with pytest.raises(QuestionnaireError, match="kind"):
        validate(q(data__0__kind="secret"))


def test_pack_has_all_documents_with_banner_and_no_compliance_claim():
    files = render_all(analyse(EXAMPLE))
    assert len(files) == len(DOCS) == 11
    for name, text in files.items():
        assert "DRAFT for lawyer review" in text, name
        low = text.lower()
        assert "is compliant" not in low and "fully compliant" not in low and "kvkk-safe" not in low, name
        assert "## KVKK" in text or name.startswith("00"), name


def test_criminal_data_needs_art10():
    f = ids(EXAMPLE)
    assert f["art10:screening"].severity == "action"
    assert "art10:screening" not in ids(q(activities__1__art10_basis="national AML law"))


def test_dpia_screening_counts_criteria():
    an = analyse(EXAMPLE)
    met = {k for k, _, m, _ in an.dpia_criteria if m}
    assert {"sensitive", "matching", "innovative", "vulnerable"} <= met
    assert an.dpia_required
    # A system with only ordinary data, no LLM and no combining does not trigger the DPIA.
    small = copy.deepcopy(TEMPLATE)
    small["agents"][0]["models"] = []
    assert not analyse(small).dpia_required


def test_transfer_routes():
    an = analyse(EXAMPLE)
    route = {t.vendor["id"]: t for t in an.transfers}
    assert route["mistral"].route == "EEA" and not route["mistral"].needs_tia
    assert route["anthropic"].route == "unknown" and route["anthropic"].needs_tia
    assert route["tsg"].route == "same country"
    assert "kalkan" not in route  # the lawyer's own computer is not a transfer
    assert all(route[v].kvkk_transfer for v in ("anthropic", "mistral", "hetzner"))
    dpf = analyse(q(vendors__0__dpf_certified=True))
    assert {t.vendor["id"]: t.route for t in dpf.transfers}["anthropic"] == "DPF"
    scc = analyse(q(vendors__0__country="IN", vendors__0__transfer_mechanism="none"))
    assert {f.id: f.severity for f in scc.findings}["xfer:anthropic"] == "action"


def test_eu_controller_has_no_kvkk_transfers_and_no_eu_client_scc():
    eu = q(controller__country="NL", scope__kvkk_applies=False)
    f = ids(eu)
    assert "kvkk9" not in f and "eu_scc" not in f
    assert all(not t.kvkk_transfer for t in analyse(eu).transfers)


def test_art27_when_art3_2_applies():
    f = ids(q(scope__offers_to_eu_data_subjects=True))
    assert f["art27"].severity == "action"
    assert "art27" not in ids(q(scope__offers_to_eu_data_subjects=True, controller__eu_representative="Rep BV"))


def test_ai_act_flags():
    f = ids(q(ai__predicts_crime_risk=True))
    assert f["ai5"].severity == "action"
    f = ids(q(ai__annex_iii=["employment"]))
    assert "Annex III point 4" in f["ai_high"].detail
    assert analyse(EXAMPLE).ai_risk == "limited / minimal"


def test_unknowns_become_open_markers():
    files = render_all(analyse(TEMPLATE))
    assert "[OPEN: privacy contact]" in files["01-ropa.md"]
    assert all(f.severity in ("open", "info") for f in analyse(TEMPLATE).findings)


def test_masked_special_data_is_still_a_risk():
    f = ids(EXAMPLE)
    assert f["maskspecial:anthropic"].severity == "risk"
    assert f["mask_note"].severity == "info"


def test_committed_example_pack_is_current():
    """examples/dd_harness_pack must be regenerated when the generator changes."""
    files = render_all(analyse(EXAMPLE))
    pack = ROOT / "examples" / "dd_harness_pack"
    for name, text in files.items():
        assert (pack / name).read_text(encoding="utf-8") == text, f"rebuild {name}: python -m katip_uyum build examples/dd_harness.json --out examples/dd_harness_pack"
