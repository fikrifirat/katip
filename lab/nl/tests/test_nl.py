"""Offline tests for katip_nl. All data below is invented. Run: python -m pytest lab/nl/tests -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from katip_nl.mask import mask, restore  # noqa: E402
from katip_nl.recognizers import bsn_valid, btw_valid, detect, iban_valid  # noqa: E402
from katip_nl.rechtspraak import find_eclis  # noqa: E402
from katip_nl.wetten import find_citations  # noqa: E402

SAMPLE = (Path(__file__).resolve().parents[1] / "samples" / "synthetic_arbeidsgeschil.txt").read_text(encoding="utf-8")


def types(text, **kw):
    return {(s["entity_type"], s["text"]) for s in detect(text, **kw)}


def test_checksums():
    assert bsn_valid("111222333") and bsn_valid("1112.22.333") and bsn_valid("12345672")  # 8 digits = leading 0
    assert not bsn_valid("111222334") and not bsn_valid("000000000")
    assert iban_valid("NL91ABNA0417164300") and iban_valid("NL91 ABNA 0417 1643 00")
    assert not iban_valid("NL91ABNA0417164301")
    assert iban_valid("DE89370400440532013000")  # foreign IBANs count too
    assert btw_valid("NL111222333B01")  # old style: 11-proef on the 9 digits


def test_ids_masked():
    t = types("BSN: 111222333. Rekening NL91 ABNA 0417 1643 00. Mail a.b@example.nl, bel 06-12345678 of +31 20 123 4567.")
    assert ("BSN", "111222333") in t
    assert ("IBAN", "NL91 ABNA 0417 1643 00") in t
    assert ("EMAIL", "a.b@example.nl") in t
    assert ("PHONE", "06-12345678") in t and ("PHONE", "+31 20 123 4567") in t


def test_bsn_needs_checksum_or_cue():
    assert not types("Het bedrag van 123456789 is betaald.")  # fails 11-proef, no cue
    assert ("BSN", "123456789") in types("Mijn BSN is 123456789")  # cue, typo: still masked, low score


def test_address_street_mode_keeps_street_and_town():
    t = "wonende aan de Keizersgracht 312-III, 1016 EZ Amsterdam"
    found = types(t)
    assert ("HOUSE_NUMBER", "312-III") in found and ("POSTCODE", "1016 EZ") in found
    masked = mask(t)[0]
    assert "Keizersgracht" in masked and "Amsterdam" in masked
    assert ("ADDRESS", "Keizersgracht 312-III") in types(t, address_detail="full")


def test_postcode_not_company_or_year():
    assert not any(e == "POSTCODE" for e, _ in types("In 2023 BV-vorming besproken; Holding 2019 BV is opgericht."))


def test_names():
    t = types("De heer J.P. van der Berg en mevr. Sanne de Wit. Later: Van der Berg kwam niet.")
    assert ("PERSON", "J.P. van der Berg") in t and ("PERSON", "Sanne de Wit") in t
    assert ("PERSON", "Van der Berg") in t


def test_repeated_surname_shares_placeholder():
    m, table, _ = mask("De heer J.P. van der Berg verscheen. Van der Berg verklaarde dat hij ziek was.")
    assert m.count("[NAAM-1]") == 2 and "[NAAM-2]" not in m


def test_ids_documents_plates():
    t = types("paspoort NWR4K7T21, V-nummer 2834917265, kenteken 12-ABC-3, geboren op 14-03-1986")
    assert {("ID_DOCUMENT", "NWR4K7T21"), ("V_NUMBER", "2834917265"), ("PLATE", "12-ABC-3"),
            ("BIRTH_DATE", "14-03-1986")} <= t


def test_legal_references_stay_readable():
    t = ("Zaaknummer: C/13/745123 / HA ZA 26-0412. Zie ECLI:NL:HR:2023:1000, art. 7:611 BW, artikel 8:69 Awb, "
         "hof 200.123.456/01 en Stb. 1996, 406. Uitspraak van 3 maart 2026 door de Rechtbank Amsterdam.")
    assert detect(t) == []


def test_kvk_flag_only():
    s = [x for x in detect("Bakkerij De Molen B.V. (KvK 12345678)") if x["entity_type"] == "KVK"]
    assert s and s[0]["flag_only"]
    assert "12345678" in mask("Bakkerij De Molen B.V. (KvK 12345678)")[0]


def test_negative_prose():
    prose = ("De Hoge Raad overweegt dat de werkgever zich als goed werkgever moet gedragen. Het hof heeft in rov. 4.3 "
             "geoordeeld dat de opzegging niet rechtsgeldig was. De Staat der Nederlanden wordt veroordeeld in de "
             "proceskosten, aan de zijde van eiser begroot op € 1.234,56. Het beroep is gegrond.")
    assert detect(prose) == []


def test_sample_roundtrip():
    masked, table, spans = mask(SAMPLE)
    for secret in ("111222333", "NL91 ABNA 0417 1643 00", "1016 EZ", "312-III", "jp.vdberg@example.nl", "06-12345678",
                   "NWR4K7T21", "2834917265", "14-03-1986", "Sanne de Wit", "Pieter Jansen", "El Amrani"):
        assert secret not in masked, secret
    for keep in ("ECLI:NL:HR:2023:1000", "art. 7:611 BW", "C/13/745123", "Keizersgracht", "Rechtbank Amsterdam"):
        assert keep in masked, keep
    assert restore(masked, table).count("111222333") == 1


def test_citations_and_eclis():
    c = find_citations("art. 7:611 BW, artikel 6:162 BW, art. 8:69 Awb, art. 3 lid 2 Rv, art. 6 AVG, art. 611 BW")
    got = [(x["act_key"], x["article"], x.get("bwb")) for x in c]
    assert ("BW", "611", "BWBR0005290") in got and ("BW", "162", "BWBR0005289") in got
    assert ("Awb", "8:69", "BWBR0005537") in got and ("Rv", "3", "BWBR0001827") in got
    assert ("AVG", "6", None) in got and ("BW", "611", None) in got  # book missing -> flagged, not guessed
    assert find_eclis("zie ECLI:NL:HR:2023:1000 en ECLI:NL:HR:2023:1000.") == ["ECLI:NL:HR:2023:1000"]


def test_court_text_regressions():
    """Shapes found in real rechtspraak.nl decisions (eval_rechtspraak.py) that the first rules got wrong."""
    t = ("Vgl. Rb. Amsterdam 26 juli 2018, ECLI:NL:RBAMS:2018:5807.\nI. Het proces-verbaal van aangifte.\n"
         "Antwoord 5 Nee. Vordering 2 en 3 zijn gestoeld op art. 6:162 BW. Belastingdienst, Postbus 20303, "
         "2500 EH Den Haag. 24/1149 PW Centrale Raad van Beroep. Eiseres heeft beroep ingesteld.")
    assert detect(t) == []
    names = {s["text"] for s in detect("advocaat mr. P. Oskam te Amsterdam en mr. T. Pavićević, rechters.")}
    assert names == {"P. Oskam", "T. Pavićević"}
