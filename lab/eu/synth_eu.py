"""Synthetic EU documents for the "eu" profile, with gold spans. Everything here is made up.

Six languages (en, de, fr, it, es, nl), one client letter per document, holding: a person's name in one of four
settings (after a title, in a form field, under a closing, bare in a sentence), a national ID of the country, an
IBAN, a phone, an e-mail, a street address, a date of birth, a VAT id and a passport number. 10% of the IDs carry
a typo (checksum fails) next to a cue, to test the fail-closed path.

Names come from two pools: "listed" (in eu.FIRST_NAMES, the list the rules know) and "unlisted" (checked not to
be in that list), so the report shows how much depends on the list. The surname pools are shared.

Valid IDs are drawn at random until eu.py's checksum accepts them. Those checksums were checked against the
published examples (BSN 111222333, Steuer-ID 86095742719, NIR 1 84 12 76 451 089 46, codice fiscale
RSSMRA85T10A562S, DNI 12345678Z, NIE X1234567L, BE 85.07.30-033.28, PESEL 44051401359, IBAN DE89 3704 ...).

Also writes negatives: GDPR/legal prose with article numbers, case numbers, ECLIs, amounts and dates and no
personal data, to count what the EU rules mask that they should not.

  python lab/eu/synth_eu.py --seed 2611 --n 300 --out lab/eu/data
"""
from __future__ import annotations

import argparse
import json
import random
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "connector"))
from katip_kalkan import eu  # noqa: E402

LISTED = {
    "en": ["James", "Emily", "Oliver", "Charlotte", "Daniel", "Hannah", "Thomas", "Eleanor"],
    "de": ["Jonas", "Sabine", "Matthias", "Katharina", "Wolfgang", "Leonie", "Florian", "Ursula"],
    "fr": ["Pierre", "Isabelle", "Julien", "Camille", "Guillaume", "Mathilde", "Antoine", "Hélène"],
    "it": ["Giuseppe", "Francesca", "Lorenzo", "Chiara", "Alessandro", "Giulia", "Matteo", "Beatrice"],
    "es": ["Javier", "Lucía", "Alejandro", "Pilar", "Gonzalo", "Nuria", "Santiago", "Raquel"],
    "nl": ["Daan", "Sanne", "Pieter", "Femke", "Maarten", "Lotte", "Joost", "Willemijn"],
}
UNLISTED = {
    "en": ["Declan", "Fionnuala", "Brendan", "Imogen", "Rupert", "Tamsin", "Alistair", "Philippa"],
    "de": ["Hauke", "Wiebke", "Thorsten", "Gesa", "Volker", "Silke", "Rüdiger", "Imke"],
    "fr": ["Yannick", "Gwendoline", "Loïc", "Maud", "Gaëtan", "Solène", "Benoît", "Ségolène"],
    "it": ["Ottavio", "Ludovica", "Gianmarco", "Ilaria", "Ruggero", "Ottavia", "Corrado", "Benedetta"],
    "es": ["Iñaki", "Ainhoa", "Aitor", "Nerea", "Unai", "Itziar", "Xabier", "Amaia"],
    "nl": ["Joep", "Mirjam", "Ruud", "Wietske", "Jelle", "Geertje", "Sjoerd", "Marloes"],
}
SURNAMES = {
    "en": ["Thompson", "Fairbanks", "O'Connor", "Whitaker", "Ashworth", "Pemberton", "Holloway", "Kingsley"],
    "de": ["Becker", "Schäfer", "Hoffmann", "von Arnim", "Krüger", "Lindemann", "Wagner-Holz", "Brandt"],
    "fr": ["Dupont", "Lefèvre", "Moreau", "de La Tour", "Girard", "Rousseau", "Lambert", "Fontaine"],
    "it": ["Rossi", "Bianchi", "Esposito", "Di Stefano", "Colombo", "Ricci", "De Luca", "Marchetti"],
    "es": ["García López", "Martínez", "Fernández Ruiz", "Sánchez", "de la Fuente", "Moreno", "Navarro", "Ortega Gil"],
    "nl": ["de Vries", "van den Berg", "Jansen", "Bakker", "van der Meer", "Visser", "Smit", "Mulder"],
}
for lang, names in UNLISTED.items():
    assert not set(names) & eu.FIRST_NAMES, (lang, set(names) & eu.FIRST_NAMES)

COUNTRY = {"en": "IE", "de": "DE", "fr": "FR", "it": "IT", "es": "ES", "nl": "NL"}


def _draw(r, make, ok):
    while True:
        v = make(r)
        if ok(v):
            return v


def national_id(r, lang):
    d = lambda n: "".join(r.choice(string.digits) for _ in range(n))  # noqa: E731
    if lang == "de":
        v = _draw(r, lambda r: r.choice("123456789") + d(10), eu.steuer_id_valid)
        return f"{v[:2]} {v[2:5]} {v[5:8]} {v[8:]}", "Steuer-ID"
    if lang == "fr":
        def mk(r):
            body = r.choice("12") + d(2) + f"{r.randint(1, 12):02d}" + f"{r.randint(1, 95):02d}" + d(6)
            return body + f"{97 - int(body) % 97:02d}"
        v = _draw(r, mk, eu.nir_valid)
        return f"{v[0]} {v[1:3]} {v[3:5]} {v[5:7]} {v[7:10]} {v[10:13]} {v[13:]}", "numéro de sécurité sociale"
    if lang == "it":
        def mk(r):
            s = ("".join(r.choice(string.ascii_uppercase) for _ in range(6)) + d(2) + r.choice("ABCDEHLMPRST")
                 + f"{r.randint(1, 71):02d}" + r.choice("ABCDEFGHILM") + d(3))
            tot = sum(eu._CF_ODD[c] if i % 2 == 0 else (int(c) if c.isdigit() else ord(c) - 65) for i, c in enumerate(s))
            return s + chr(65 + tot % 26)
        return _draw(r, mk, eu.cf_valid), "codice fiscale"
    if lang == "es":
        if r.random() < 0.3:
            n = d(7)
            p = r.choice("XYZ")
            return f"{p}{n}{eu._DNI_LETTERS[int(str('XYZ'.index(p)) + n) % 23]}", "NIE"
        n = d(8)
        return f"{n}{eu._DNI_LETTERS[int(n) % 23]}", "DNI"
    if lang == "nl":
        v = _draw(r, lambda r: d(9), eu.bsn_valid)
        return v, "BSN"
    # en: a Belgian national number (the client lives in Belgium)
    v = _draw(r, lambda r: f"{r.randint(50, 99):02d}{r.randint(1, 12):02d}{r.randint(1, 28):02d}" + d(5), eu.be_nn_valid)
    return f"{v[:2]}.{v[2:4]}.{v[4:6]}-{v[6:9]}.{v[9:]}", "national number"


def typo(v):
    i = max(k for k, c in enumerate(v) if c.isdigit())
    return v[:i] + str((int(v[i]) + 1) % 10) + v[i + 1:]


IBAN_FMT = {"IE": "IE{c}{b}{n}", "DE": "DE{c}{n}", "FR": "FR{c}{n}", "IT": "IT{c}{b}{n}", "ES": "ES{c}{n}", "NL": "NL{c}{b}{n}"}


def iban(r, cc):
    length = eu.IBAN_LEN[cc]
    body = "".join(r.choice(string.digits) for _ in range(length - 4))
    if cc in ("NL", "IE"):
        body = "".join(r.choice(string.ascii_uppercase) for _ in range(4)) + body[4:]
    if cc == "IT":
        body = r.choice(string.ascii_uppercase) + body[1:]
    raw = cc + "00" + body
    chk = 98 - int("".join(str(int(c, 36)) for c in raw[4:] + raw[:4])) % 97
    v = f"{cc}{chk:02d}{body}"
    assert eu.iban_valid(v)
    return " ".join(v[i:i + 4] for i in range(0, len(v), 4))


PHONE = {"en": "+353 {a} {b}", "de": "+49 {a} {b}", "fr": "+33 {a} {b}", "it": "+39 {a} {b}", "es": "+34 {a} {b}",
         "nl": "+31 {a} {b}"}
STREETS = {
    "en": ["{n} Merrion Square, Dublin 2", "{n} Baker Street, London NW1 6XE"],
    "de": ["Lindenstraße {n}, 10969 Berlin", "Am Rosengarten {n}", "Schillerplatz {n}, 70173 Stuttgart"],
    "fr": ["{n} rue de la Paix, 75002 Paris", "{n} avenue Victor Hugo, 69006 Lyon"],
    "it": ["Via Garibaldi {n}, 20121 Milano", "Piazza Navona {n}, 00186 Roma"],
    "es": ["Calle Mayor, {n}, 28013 Madrid", "Avenida de la Constitución {n}, 41004 Sevilla"],
    "nl": ["Keizersgracht {n}, 1015 CJ Amsterdam", "Laan van Meerdervoort {n}, 2517 AB Den Haag"],
}
VAT = {"en": "IE{d7}W", "de": "DE{d9}", "fr": "FR{x2}{d9}", "it": "IT{d11}", "es": "ESB{d7}0", "nl": "NL{d9}B01"}

TEMPLATES = {
    "en": {"title": ["Mr {name}", "Ms {name}", "Dr {name}"], "field": "Client: {name}",
           "closing": "Kind regards,\n{name}", "bare": "{name} signed the processing agreement on behalf of the firm.",
           "body": ("Re: data subject access request under Article 15 GDPR\n{person}\n{idcue} {id}\nDate of birth: {dob}\n"
                    "Address: {addr}\nPhone: {phone}\nE-mail: {email}\nIBAN: {iban}\nVAT number: {vat}\n"
                    "Passport No. {passport}\nThe request was received on 4 March 2025 and must be answered within one month "
                    "(Case C-311/18).\n{closing}")},
    "de": {"title": ["Herr {name}", "Frau {name}", "Herrn Dr. {name}"], "field": "Mandant: {name}",
           "closing": "Mit freundlichen Grüßen\n{name}", "bare": "{name} hat den Vertrag am 3. Mai 2024 unterschrieben.",
           "body": ("Betreff: Auskunftsersuchen nach Art. 15 DSGVO\n{person}\n{idcue} {id}\ngeboren am {dob}\n"
                    "Anschrift: {addr}\nTel. {phone}\nE-Mail: {email}\nIBAN: {iban}\nUSt-IdNr. {vat}\n"
                    "Reisepass Nr. {passport}\nDas Schreiben ging am 4. März 2025 ein (Az. 2 O 123/24).\n{closing}")},
    "fr": {"title": ["M. {name}", "Mme {name}", "Maître {name}"], "field": "Nom : {name}",
           "closing": "Cordialement,\n{name}", "bare": "{name} a signé le contrat le 3 mai 2024.",
           "body": ("Objet : demande d'accès au titre de l'article 15 du RGPD\n{person}\n{idcue} : {id}\nné le {dob}\n"
                    "Adresse : {addr}\nTél. {phone}\nCourriel : {email}\nIBAN : {iban}\nTVA intracommunautaire : {vat}\n"
                    "Passeport n° {passport}\nLa demande a été reçue le 4 mars 2025 (RG n° 24/01234).\n{closing}")},
    "it": {"title": ["Sig. {name}", "Sig.ra {name}", "Avv. {name}"], "field": "Cognome e nome: {name}",
           "closing": "Cordiali saluti,\n{name}", "bare": "{name} ha firmato il contratto il 3 maggio 2024.",
           "body": ("Oggetto: richiesta di accesso ai sensi dell'art. 15 GDPR\n{person}\n{idcue}: {id}\nnato il {dob}\n"
                    "Indirizzo: {addr}\nTel. {phone}\nE-mail: {email}\nIBAN: {iban}\nPartita IVA: {vat}\n"
                    "Passaporto n. {passport}\nLa richiesta è pervenuta il 4 marzo 2025 (R.G. 1234/2024).\n{closing}")},
    "es": {"title": ["Sr. {name}", "Sra. {name}", "D. {name}"], "field": "Nombre: {name}",
           "closing": "Atentamente,\n{name}", "bare": "{name} firmó el contrato el 3 de mayo de 2024.",
           "body": ("Asunto: solicitud de acceso conforme al art. 15 RGPD\n{person}\n{idcue}: {id}\nnacido el {dob}\n"
                    "Domicilio: {addr}\nTeléfono: {phone}\nCorreo: {email}\nIBAN: {iban}\nNIF-IVA: {vat}\n"
                    "Pasaporte n.º {passport}\nLa solicitud se recibió el 4 de marzo de 2025 (autos 123/2024).\n{closing}")},
    "nl": {"title": ["dhr. {name}", "mevr. {name}", "De heer {name}"], "field": "Naam: {name}",
           "closing": "Met vriendelijke groet,\n{name}", "bare": "{name} heeft de overeenkomst op 3 mei 2024 getekend.",
           "body": ("Betreft: inzageverzoek op grond van art. 15 AVG\n{person}\n{idcue} {id}\ngeboren op {dob}\n"
                    "Adres: {addr}\nTelefoon: {phone}\nE-mail: {email}\nIBAN: {iban}\nBtw-id: {vat}\n"
                    "Paspoort nr. {passport}\nHet verzoek is op 4 maart 2025 ontvangen (zaaknummer C/13/123456).\n{closing}")},
}
SIGNERS = {"en": "Kind regards,\nThe Data Protection Team", "de": "Mit freundlichen Grüßen\nDie Rechtsabteilung",
           "fr": "Cordialement,\nLe service juridique", "it": "Cordiali saluti,\nL'ufficio legale",
           "es": "Atentamente,\nEl departamento jurídico", "nl": "Met vriendelijke groet,\nDe juridische afdeling"}


def make_doc(r, lang, pool):
    first = r.choice((LISTED if pool == "listed" else UNLISTED)[lang])
    name = f"{first} {r.choice(SURNAMES[lang])}"
    setting = r.choice(["title", "field", "closing", "bare"])
    t = TEMPLATES[lang]
    person = closing = ""
    if setting == "title":
        person = r.choice(t["title"]).format(name=name)
    elif setting == "field":
        person = t["field"].format(name=name)
    elif setting == "bare":
        person = t["bare"].format(name=name)
    if setting == "closing":
        closing = t["closing"].format(name=name)
        person = ""  # the name is only in the signature
    else:
        closing = SIGNERS[lang]
    idv, idcue = national_id(r, lang)
    is_typo = r.random() < 0.1
    if is_typo:
        idv = typo(idv)
    dg = lambda n: "".join(r.choice(string.digits) for _ in range(n))  # noqa: E731
    vals = {
        "person": person, "closing": closing, "idcue": idcue, "id": idv,
        "dob": f"{r.randint(1, 28):02d}.{r.randint(1, 12):02d}.{r.randint(1950, 2004)}" if lang != "en"
        else f"{r.randint(1, 28)} {r.choice(['January', 'March', 'July', 'October'])} {r.randint(1950, 2004)}",
        "addr": r.choice(STREETS[lang]).format(n=r.randint(1, 240)),
        "phone": PHONE[lang].format(a=dg(2), b=f"{dg(3)} {dg(4)}"),
        "email": f"{first.lower()}.{r.choice(['k', 'm', 'v'])}{dg(2)}@example.{COUNTRY[lang].lower()}",
        "iban": iban(r, COUNTRY[lang]),
        "vat": VAT[lang].format(d7=dg(7), d9=dg(9), d11=dg(11), x2=dg(2)),
        "passport": r.choice(["C", "Y", "X", "P"]) + "".join(r.choice(string.ascii_uppercase + string.digits) for _ in range(6)) + dg(2),
    }
    text = t["body"].format(**vals)
    gold = []

    def add(typ, value):
        for start in _all(text, value):
            gold.append({"type": typ, "start": start, "end": start + len(value), "text": value})

    add("PERSON", name)
    add("NATIONAL_ID", idv)
    add("BIRTH_DATE", vals["dob"])
    add("ADDRESS", vals["addr"])
    add("PHONE", vals["phone"])
    add("EMAIL", vals["email"])
    add("IBAN", vals["iban"])
    add("VAT_ID", vals["vat"])
    add("PASSPORT", vals["passport"])
    return {"lang": lang, "pool": pool, "setting": setting, "id_typo": is_typo, "text": text, "gold": gold}


def _all(text, v):
    i = text.find(v)
    while i >= 0:
        yield i
        i = text.find(v, i + 1)


NEGATIVES = [
    "Under Article 6(1)(f) GDPR, processing is lawful where it is necessary for the purposes of the legitimate interests pursued by the controller.",
    "The Court of Justice held in Case C-311/18 (ECLI:EU:C:2020:559) that Decision 2016/1250 is invalid.",
    "Regulation (EU) 2016/679 applies from 25 May 2018; fines may reach EUR 20 000 000 or 4 % of turnover.",
    "Gemäß Art. 82 Abs. 1 DSGVO hat jede Person, der ein Schaden entstanden ist, Anspruch auf Schadenersatz.",
    "Das Landgericht München I hat mit Urteil vom 20.01.2022 (Az. 3 O 17493/20) entschieden.",
    "Selon l'article 17 du RGPD, la personne concernée a le droit d'obtenir l'effacement de ses données.",
    "La CNIL a prononcé une amende de 150 000 000 euros le 31 décembre 2021 (délibération n° SAN-2021-023).",
    "Ai sensi dell'articolo 9 del Regolamento (UE) 2016/679, è vietato trattare dati relativi alla salute.",
    "Il Garante ha adottato il provvedimento n. 9870832 del 9 febbraio 2023.",
    "De conformidad con el artículo 33 del RGPD, la violación se notificará en un plazo de 72 horas.",
    "La AEPD resolvió el procedimiento PS/00059/2020 con una multa de 6 000 000 euros.",
    "Op grond van artikel 35 AVG voert de verwerkingsverantwoordelijke een gegevensbeschermingseffectbeoordeling uit.",
    "De Autoriteit Persoonsgegevens legde op 18 juli 2024 een boete op van 290 miljoen euro (zaaknummer 2024-123).",
    "Invoice 2024-000123 dated 12.03.2024, order no. 4500012345, total EUR 1,234.56 incl. VAT 19 %.",
    "The Data Protection Officer can be reached through the contact form on the controller's website.",
    "Annex II lists the technical and organisational measures: encryption at rest, access logging, ISO 27001.",
    "Standard Contractual Clauses (Commission Implementing Decision (EU) 2021/914), Module Two, Clause 13.",
    "Mit freundlichen Grüßen\nIhre Rechtsabteilung",
    "Kind regards,\nThe Privacy Team",
    "Cordialement,\nLe service client",
    "Version 3.2.1 of the DPA, last updated 01/02/2025, document ID DPA-2025-07.",
    "Tracking number 1Z999AA10123456784 and reference 123456789 for the shipment.",
    "The Board adopted Guidelines 05/2020 on consent and Guidelines 01/2022 on data subject rights.",
    "Der Bundesgerichtshof (BGH, Urteil vom 18.11.2024 – VI ZR 10/24) bestätigte den Kontrollverlust als Schaden.",
    "Corte di Cassazione, sez. I civile, ordinanza n. 13073 del 12 maggio 2023.",
    "Tribunal Supremo, Sala de lo Contencioso, sentencia 1234/2023 de 10 de octubre.",
    "Hoge Raad 14 juni 2024, ECLI:NL:HR:2024:889, rov. 3.4.",
    "Conseil d'État, 10ème chambre, 19 juin 2020, n° 430810.",
    "The retention period is 6 years after the end of the contract (section 147 AO).",
    "Microsoft Ireland Operations Limited, One Microsoft Place, acts as processor for the EEA.",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2611)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--out", default=str(Path(__file__).parent / "data"))
    ap.add_argument("--blind", action="store_true", help="the blind set (prose phrasing, other names and streets)")
    a = ap.parse_args()
    if a.blind:
        r = random.Random(a.seed)
        docs = [make_blind(r, list(BLIND)[i % 6], "listed" if (i // 6) % 2 == 0 else "unlisted") for i in range(a.n)]
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / f"eu_blind_seed{a.seed}.jsonl").write_text(
            "\n".join(json.dumps(d, ensure_ascii=False) for d in docs) + "\n", encoding="utf-8")
        print(f"{len(docs)} blind docs -> {a.out}")
        return
    r = random.Random(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    docs = [make_doc(r, lang, pool) for i in range(a.n)
            for lang, pool in [(list(TEMPLATES)[i % 6], "listed" if (i // 6) % 2 == 0 else "unlisted")]]
    (out / f"eu_synth_seed{a.seed}.jsonl").write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in docs) + "\n",
                                                      encoding="utf-8")
    (out / "eu_negatives.jsonl").write_text("\n".join(json.dumps({"text": t}, ensure_ascii=False) for t in NEGATIVES) + "\n",
                                            encoding="utf-8")
    print(f"{len(docs)} docs, {len(NEGATIVES)} negatives -> {out}")



# ---------------------------------------------------------------- blind set
# Written before any rule was tuned on the main set and not looked at while tuning: other phrasing (prose, not
# labelled lines), other streets, other first names (listed and unlisted) and surnames. Quote this one.
BLIND_LISTED = {
    "en": ["Richard", "Sarah", "Benjamin", "Victoria", "Samuel", "Rebecca"],
    "de": ["Klaus", "Petra", "Dominik", "Johanna", "Tobias", "Birgit"],
    "fr": ["Laurent", "Sylvie", "Mathieu", "Pauline", "Olivier", "Juliette"],
    "it": ["Salvatore", "Paola", "Riccardo", "Valentina", "Massimo", "Federica"],
    "es": ["Fernando", "Mercedes", "Ignacio", "Rocío", "Enrique", "Montserrat"],
    "nl": ["Wouter", "Marieke", "Jeroen", "Annemieke", "Koen", "Esther"],
}
BLIND_UNLISTED = {
    "en": ["Cormac", "Orla", "Lachlan", "Hermione", "Barnaby", "Clementine"],
    "de": ["Detlef", "Elke", "Hartmut", "Gudrun", "Lutz", "Almut"],
    "fr": ["Gérald", "Annick", "Hervé", "Rozenn", "Ghislain", "Bérénice"],
    "it": ["Gennaro", "Assunta", "Calogero", "Graziella", "Ermanno", "Fiorella"],
    "es": ["Eneko", "Leire", "Borja", "Maite", "Txema", "Edurne"],
    "nl": ["Hidde", "Jikke", "Freek", "Aaltje", "Tjeerd", "Hennie"],
}
BLIND_SURNAMES = {
    "en": ["Gallagher", "Featherstone", "McAllister", "Ellingham", "Radcliffe", "Brennan"],
    "de": ["Zimmermann", "Böhm", "Kaiser", "zu Solms", "Weißenberger", "Hartung"],
    "fr": ["Mercier", "Chevalier", "Le Goff", "Faure", "d'Aubigny", "Perrin"],
    "it": ["Ferrara", "Lombardi", "Santoro", "Del Piero", "Caruso", "Gentile"],
    "es": ["Romero Díaz", "Iglesias", "Castillo", "del Río", "Vázquez Pardo", "Herrera"],
    "nl": ["Hoekstra", "de Graaf", "van Leeuwen", "Dijkstra", "ter Horst", "Postma"],
}
for lang, names in BLIND_UNLISTED.items():
    assert not set(names) & eu.FIRST_NAMES, (lang, set(names) & eu.FIRST_NAMES)
BLIND_STREETS = {
    "en": ["Flat 3, {n} Victoria Road, Cork", "{n} Grafton Street, Dublin 2"],
    "de": ["Goethestraße {n}, 80336 München", "Bahnhofstr. {n}, 50667 Köln"],
    "fr": ["{n}, boulevard Haussmann, 75009 Paris", "{n} place Bellecour, 69002 Lyon"],
    "it": ["Corso Vittorio Emanuele II {n}, 10121 Torino", "Viale Europa {n}, 50126 Firenze"],
    "es": ["Paseo de Gracia {n}, 08007 Barcelona", "Calle de Alcalá {n}, 28014 Madrid"],
    "nl": ["Prinsengracht {n}, 1016 GV Amsterdam", "Stationsweg {n}, 3511 ED Utrecht"],
}
BLIND = {
    "en": ("We act for {name}, who lives at {addr} and was born on {dob}. Our client's {idcue} is {id} and the refund "
           "should go to account {iban}. Please call {phone} or write to {email}. The client's passport ({passport}) "
           "was copied for the KYC file. Our VAT registration is {vat}.\nYours sincerely,\nThe Firm"),
    "de": ("Wir vertreten {name}, wohnhaft {addr}, geb. {dob}. Die {idcue} unseres Mandanten lautet {id}; die "
           "Erstattung bitten wir auf das Konto {iban} zu überweisen. Rückfragen unter {phone} oder {email}. Der "
           "Reisepass ({passport}) liegt in Kopie bei. Unsere USt-IdNr.: {vat}.\nMit freundlichen Grüßen\nDie Kanzlei"),
    "fr": ("Nous représentons {name}, demeurant {addr}, né le {dob}. Son {idcue} est le {id} et le remboursement doit "
           "être versé sur le compte {iban}. Vous pouvez joindre le cabinet au {phone} ou par courriel à {email}. "
           "Copie du passeport {passport} jointe. N° TVA : {vat}.\nBien à vous,\nLe cabinet"),
    "it": ("Assistiamo {name}, residente in {addr}, nato il {dob}. Il {idcue} del cliente è {id}; il rimborso va "
           "accreditato sul conto {iban}. Per informazioni: {phone} oppure {email}. Si allega copia del passaporto "
           "{passport}. P. IVA dello studio: {vat}.\nDistinti saluti,\nLo studio"),
    "es": ("Representamos a {name}, con domicilio en {addr}, nacido el {dob}. Su {idcue} es {id} y el reembolso debe "
           "abonarse en la cuenta {iban}. Contacto: {phone} o {email}. Se adjunta copia del pasaporte {passport}. "
           "NIF-IVA del despacho: {vat}.\nUn saludo,\nEl despacho"),
    "nl": ("Wij staan {name} bij, wonende aan {addr}, geboren op {dob}. Het {idcue} van cliënt is {id}; de "
           "terugbetaling graag op rekening {iban}. Bereikbaar via {phone} of {email}. Een kopie van het paspoort "
           "({passport}) is bijgevoegd. Ons btw-id: {vat}.\nMet vriendelijke groet,\nHet kantoor"),
}


def make_blind(r, lang, pool):
    first = r.choice((BLIND_LISTED if pool == "listed" else BLIND_UNLISTED)[lang])
    name = f"{first} {r.choice(BLIND_SURNAMES[lang])}"
    idv, idcue = national_id(r, lang)
    is_typo = r.random() < 0.1
    if is_typo:
        idv = typo(idv)
    dg = lambda n: "".join(r.choice(string.digits) for _ in range(n))  # noqa: E731
    months = {"en": "April", "de": "April", "fr": "avril", "it": "aprile", "es": "abril", "nl": "april"}
    dob = r.choice([f"{r.randint(1, 28)} {months[lang]} {r.randint(1950, 2004)}",
                    f"{r.randint(1, 28):02d}/{r.randint(1, 12):02d}/{r.randint(1950, 2004)}"])
    if lang == "es":
        dob = dob.replace(f" {months[lang]} ", f" de {months[lang]} de ")
    vals = {"name": name, "idcue": idcue, "id": idv, "dob": dob,
            "addr": r.choice(BLIND_STREETS[lang]).format(n=r.randint(1, 240)),
            "phone": PHONE[lang].format(a=dg(2), b=f"{dg(2)} {dg(2)} {dg(3)}"),
            "email": f"{first.lower()[:1]}{r.choice(BLIND_SURNAMES[lang]).split()[-1].lower().replace(chr(39), '')}"
                     f"@mail.example",
            "iban": iban(r, COUNTRY[lang]).replace(" ", "") if r.random() < 0.5 else iban(r, COUNTRY[lang]),
            "vat": VAT[lang].format(d7=dg(7), d9=dg(9), d11=dg(11), x2=dg(2)),
            "passport": r.choice(["K", "N", "AA", "YA"]) + dg(7)}
    text = BLIND[lang].format(**vals)
    gold = []
    for typ, key in (("PERSON", "name"), ("NATIONAL_ID", "id"), ("BIRTH_DATE", "dob"), ("ADDRESS", "addr"),
                     ("PHONE", "phone"), ("EMAIL", "email"), ("IBAN", "iban"), ("VAT_ID", "vat"), ("PASSPORT", "passport")):
        for start in _all(text, vals[key]):
            gold.append({"type": typ, "start": start, "end": start + len(vals[key]), "text": vals[key]})
    return {"lang": lang, "pool": pool, "setting": "bare", "id_typo": is_typo, "text": text, "gold": gold}


if __name__ == "__main__":
    main()
