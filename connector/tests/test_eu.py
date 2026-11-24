"""The "eu" (GDPR) profile: EU national IDs with checksums, VAT ids, phones, addresses, non-Turkish names.

Every value below is synthetic or a published specimen (BSN 111222333, Steuer-ID 86095742719, NIR 1 84 12 76 451
089 46, codice fiscale RSSMRA85T10A562S, DNI 12345678Z, NIE X1234567L, BE 85.07.30-033.28, PESEL 44051401359).

Run:  cd connector && python -m pytest -q tests/test_eu.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("KATIP_HOME", str(tmp_path / "katip"))
    monkeypatch.setenv("KATIP_NO_KEYCHAIN", "1")
    monkeypatch.setenv("KATIP_FOLDER", str(tmp_path))
    monkeypatch.setenv("KATIP_DOWNLOADS", "0")
    from katip_kalkan import vault
    vault._memory.clear()
    return tmp_path


# ------------------------------------------------------------------ checksums
@pytest.mark.parametrize("fn,good,bad", [
    ("bsn_valid", "111222333", "111222334"),
    ("steuer_id_valid", "86095742719", "86095742718"),
    ("steuer_id_valid", "65929970489", "11111111111"),  # all digits the same breaks the digit rule
    ("nir_valid", "1 84 12 76 451 089 46", "1 84 12 76 451 089 47"),
    ("nir_valid", "2 69 05 2A 123 456 31", "2 69 05 2A 123 456 30"),  # Corsica
    ("cf_valid", "RSSMRA85T10A562S", "RSSMRA85T10A562T"),
    ("dni_valid", "12345678Z", "12345678A"),
    ("dni_valid", "X1234567L", "X1234567A"),
    ("be_nn_valid", "85.07.30-033.28", "85.07.30-033.29"),
    ("pesel_valid", "44051401359", "44051401358"),
    ("iban_valid", "DE89 3704 0044 0532 0130 00", "DE89 3704 0044 0532 0130 01"),
    ("iban_valid", "FR14 2004 1010 0505 0001 3M02 606", "FR14 2004 1010 0505 0001 3M02 60"),
])
def test_checksums(fn, good, bad):
    from katip_kalkan import eu
    f = getattr(eu, fn)
    if fn == "nir_valid" and "2A" in good:  # build a valid Corsican NIR rather than trust a hand-typed key
        body = "2690519123456"
        good = f"2 69 05 2A 123 456 {97 - int(body) % 97:02d}"
        bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    assert f(good) and not f(bad)


LETTER = """Mandant: Herr Jonas Becker, geboren am 12.03.1985
Steuer-ID 86 095 742 719, IBAN DE89 3704 0044 0532 0130 00, Tel. +49 30 1234567, jonas.becker@example.de
Anschrift: Hauptstraße 5, 10115 Berlin. USt-IdNr. DE136695976. Reisepass Nr. C01X00T47.
Client : M. Pierre Dupont, NIR 1 84 12 76 451 089 46, 12 rue de la Paix, 75002 Paris.
Codice fiscale RSSMRA85T10A562S, Sig. Mario Rossi, Via Roma 12, 00184 Roma.
DNI 12345678Z, Sra. Lucía García López. NIE X1234567L. BSN 111222333, dhr. J. de Vries.
Rijksregisternummer 85.07.30-033.28. PESEL 44051401359. Die Steuer-ID lautet 23 196 807 946 (Tippfehler).
Becker unterschrieb am 3. Mai 2024 nach Art. 6 Abs. 1 lit. f DSGVO, EuGH C-311/18, ECLI:EU:C:2020:559.
Kind regards,
Emma Thompson
"""
SECRETS = ["Jonas Becker", "12.03.1985", "86 095 742 719", "DE89 3704 0044 0532 0130 00", "+49 30 1234567",
           "jonas.becker@example.de", "Hauptstraße 5", "DE136695976", "C01X00T47", "Pierre Dupont",
           "1 84 12 76 451 089 46", "rue de la Paix", "RSSMRA85T10A562S", "Mario Rossi", "Via Roma 12", "12345678Z",
           "Lucía García López", "X1234567L", "111222333", "de Vries", "85.07.30-033.28", "44051401359",
           "23 196 807 946", "Becker", "Emma Thompson"]
READABLE = ["Art. 6 Abs. 1 lit. f DSGVO", "C-311/18", "ECLI:EU:C:2020:559", "3. Mai 2024", "Kind regards"]


def test_eu_profile_masks_eu_letter(tmp_path):
    from katip_kalkan import core
    f = tmp_path / "letter.txt"
    f.write_text(LETTER, encoding="utf-8")
    eu_text = core.mask_file(str(f), "eu1", profile="eu")["masked_text"]
    left = [s for s in SECRETS if s in eu_text]
    assert left == [], left
    for keep in READABLE:
        assert keep in eu_text, keep
    assert "[ULUSAL KİMLİK NO-1]" in eu_text and "[KDV/VAT NO-1]" in eu_text
    # the KVKK profile alone misses most of these: that is the point of the new profile
    ai_text = core.mask_file(str(f), "eu2", profile="ai")["masked_text"]
    assert len([s for s in SECRETS if s in ai_text]) >= 10


def test_eu_profile_restores(tmp_path):
    from katip_kalkan import core
    f = tmp_path / "letter.txt"
    f.write_text(LETTER, encoding="utf-8")
    masked = core.mask_file(str(f), "eu3", profile="eu")["masked_text"]
    from katip_kalkan import vault
    restored, n = vault.open_vault("eu3").unmask(masked)
    assert n > 10 and "Jonas Becker" in restored and "86 095 742 719" in restored


def test_eu_profile_keeps_turkish_samples_unchanged():
    """On Turkish documents the eu profile masks at least what "ai" masks."""
    from katip_kalkan import engine, eu
    samples = sorted((HERE.parents[1] / "docs" / "samples").glob("*.txt")) + [HERE / "fixtures" / "dilekce_01.txt"]
    assert samples
    for f in samples:
        t = f.read_text(encoding="utf-8")
        types, addr = engine.profile_types("ai")
        a = engine.detect(t, 0.5, types, address_detail=addr)
        types, addr = engine.profile_types("eu")
        b = eu.merge(t, engine.detect(t, 0.5, types, address_detail=addr))
        ca, cb = set(), set()
        for s in a:
            ca.update(range(s["start"], s["end"]))
        for s in b:
            cb.update(range(s["start"], s["end"]))
        assert ca <= cb, (f.name, sorted({t[i] for i in ca - cb}))


@pytest.mark.parametrize("text", [
    "Under Article 6(1)(f) GDPR, processing is lawful where necessary for legitimate interests.",
    "Regulation (EU) 2016/679 applies from 25 May 2018; fines may reach EUR 20 000 000.",
    "Invoice 2024-000123 dated 12.03.2024, order no. 4500012345, total EUR 1,234.56.",
    "Tracking number 1Z999AA10123456784 and reference 123456789 for the shipment.",
    "Das Landgericht München I hat mit Urteil vom 20.01.2022 (Az. 3 O 17493/20) entschieden.",
    "Mit freundlichen Grüßen\nIhre Kanzlei",
])
def test_no_false_positives_in_plain_legal_text(text):
    from katip_kalkan import engine, eu
    types, addr = engine.profile_types("eu")
    spans = eu.merge(text, engine.detect(text, 0.5, types, address_detail=addr))
    assert spans == [], [(s["entity_type"], s["text"]) for s in spans]


def test_merge_never_leaves_part_of_a_value():
    from katip_kalkan import eu
    text = "IBAN DE89 3704 0044 0532 0130 00 ok"
    engine_spans = [{"id": "a", "entity_type": "PERSON", "start": 5, "end": 14, "text": text[5:14], "score": 0.6}]
    out = eu.merge(text, engine_spans)
    assert len(out) == 1 and out[0]["entity_type"] == "IBAN" and out[0]["text"] == "DE89 3704 0044 0532 0130 00"


def test_profile_listed_for_claude():
    from katip_kalkan import engine, local_server
    assert "eu" in engine.PROFILES and "eu" in local_server.PROFILE["enum"]
    types, _ = engine.profile_types("eu")
    assert {"NATIONAL_ID", "VAT_ID", "ID_DOCUMENT", "TCKN", "PERSON"} <= set(types)


# ------------------------------------------------------------------ names without a title (round 2 of the EU work)
def _eu_spans(text):
    from katip_kalkan import engine, eu
    types, addr = engine.profile_types("eu")
    return eu.merge(text, engine.detect(text, 0.5, types, address_detail=addr))


def _masked(text):
    out, pos = [], 0
    for s in sorted(_eu_spans(text), key=lambda s: (s["start"], -s["end"])):
        if s["start"] < pos:
            continue
        out.append(text[pos:s["start"]] + "#")
        pos = s["end"]
    return "".join(out) + text[pos:]


@pytest.mark.parametrize("text,secret", [
    ("Wir vertreten Detlef Weißenberger in dieser Sache.", "Weißenberger"),          # act cue
    ("Directors: Anna Kowalski, Hidde Hoekstra and Marie Dubois.", "Hoekstra"),     # role + list
    ("Rozenn Perrin (the Employee) agrees to the terms.", "Rozenn"),                # apposition
    ("Please contact orla.brennan@example.ie. Orla Brennan will reply.", "Orla Brennan"),  # name in e-mail
    ("The shares are held by Tjeerd Postma since 2019.", "Postma"),                 # known surname
    ("Signed for the seller: Mindaugas Kazlauskas.", "Kazlauskas"),                 # surname ending
    ("Approved by P. van der Heijden. Van der Heijden left early.", "Heijden"),      # initials + repeat
    ("[10:01] Jule Krause: hi\n[10:02] Fabian Krüger: ok\n", "Krüger"),              # chat speakers
    ("Müvekkilimiz Siobhan Brennan ile görüştük. Brennan'ın talebi açıktır.", "Brennan"),  # Turkish suffix
    ("Tel. 06-41837265 of 02 98 44 71 20", "41837265"),                              # national phones
    ("Anschrift: Venloer Straße 389, 50825 Köln", "389"),
    ("The employee has been on sick leave since May (burn-out).", "burn-out"),       # Art. 9 keyword
])
def test_eu_names_and_more_without_titles(text, secret):
    assert secret not in _masked(text), _masked(text)


@pytest.mark.parametrize("text,keep", [
    ("The seller is Rossi Tessuti S.r.l., represented by its director.", "Rossi Tessuti S.r.l."),
    ("Payment to Deutsche Bank AG, Frankfurt.", "Deutsche Bank AG"),
    ("Clause 13 of Commission Implementing Decision (EU) 2021/914 applies.", "2021/914"),
    ("Siehe z. B. Pseudonymisierung nach Art. 4 DSGVO.", "Pseudonymisierung"),
])
def test_eu_keeps_companies_and_acts_readable(text, keep):
    assert keep in _masked(text), _masked(text)


def test_eu_name_model_is_off_by_default(monkeypatch):
    from katip_kalkan import eu
    monkeypatch.delenv("KATIP_EU_NER", raising=False)
    eu._NER = None
    assert eu.find_names_model("Gennaro Caruso signed.") == []


@pytest.mark.parametrize("text,value", [
    ("Thanks,\nRosalind Ashworth", "Rosalind Ashworth"),
    ("Groeten,\nMarloes de Groot", "Marloes de Groot"),
    ("Danke und Grüße\nFriederike Schöndorf", "Friederike Schöndorf"),
    ("De huur werd betaald op naam van Marloes de Groot.", "Marloes de Groot"),
    ("Die Miete ging auf das Konto, Inhaber Friederike Schöndorf.", "Friederike Schöndorf"),
    ("The tenant of our villa, Callum Brannigan, has not paid.", "Callum Brannigan"),
])
def test_names_after_closings_and_account_cues(text, value):
    from katip_kalkan import eu
    found = {s["text"] for s in eu.merge(text, [])}
    assert value in found, found


@pytest.mark.parametrize("text,value", [
    ("Nací el 25.12.1975 y vivo en Madrid.", "25.12.1975"),
    ("Urodziłem się 06.01.1982, mieszkam w Gdańsku.", "06.01.1982"),
])
def test_birth_dates_in_spanish_and_polish(text, value):
    from katip_kalkan import eu
    assert value in {s["text"] for s in eu.find_birth_dates(text)}
