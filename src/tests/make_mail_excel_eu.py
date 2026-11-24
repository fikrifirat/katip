"""E-mail and Excel test set in EU languages (English, Dutch, German, plus the sample pack's other EU documents).

Two sources, all people and numbers invented:
  * the 16 cross-border documents of the sample pack (lab/samples/data/eu_docs.jsonl; run
    lab/samples/build_eu_docs.py first): de, nl, en, fr, it, pl, es and Turkish text about EU clients;
  * 24 new client e-mails written here, 8 each in English, Dutch and German (four kinds of letter x two people),
    with ID numbers drawn with valid checksums, and 16 shorter ones in French, Italian, Spanish and Polish
    (2 letters x 4 people each). --heldout writes the same letters for other people (other seed), none of
    whose names were used while tuning eu.py.
Every text becomes an .eml (MIME styles in turn) and an Outlook .msg, and its .txt is kept as the baseline.
Each language's people also go into a client workbook with headers in that language (en, nl, de).

answer_key.json: {file: {"mask": [...], "keep": [...], "source": [...], "lang": "en"}}

  python3 lab/samples/build_eu_docs.py
  python3 src/tests/make_mail_excel_eu.py /tmp/mx-eu [--heldout]
  python3 src/tests/eval_mail_excel_corpus.py /tmp/mx-eu --profile eu
"""
from __future__ import annotations

import importlib.util
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import mail_samples as M  # noqa: E402

spec = importlib.util.spec_from_file_location("build_eu_docs", ROOT / "lab" / "samples" / "build_eu_docs.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
B.R.seed(2611)
R = random.Random(2611)

STYLES = ["alternative", "html", "plain", "qp-html", "base64"]
FIRM = "Örnek Hukuk Bürosu <buro@ornekhukuk.invalid>"

PEOPLE = {
    "en": ["Harriet Pennington", "Gareth Llewellyn", "Siobhan Gallagher", "Duncan McAllister",
           "Imogen Whitcombe", "Callum Fairbairn", "Rosalind Ashworth", "Declan Brannigan"],
    "nl": ["Femke van der Heijden", "Joost Verhoeven", "Marloes de Groot", "Sjoerd Bakker",
           "Annelies Kuipers", "Thijs van Dongen", "Noortje Hendriks", "Wouter Mulder"],
    "de": ["Annegret Hoffmeister", "Lukas Brandauer", "Friederike Schöndorf", "Matthias Kellermann",
           "Ulrike Pfeiffer", "Henrik Großmann", "Sabine Wendtland", "Torsten Eichhorn"],
    "fr": ["Clémence Vautrin", "Bertrand Lemaire", "Solène Garnier", "Thibault Rousseau"],
    "it": ["Ginevra Bellandi", "Riccardo Ferraresi", "Ilaria Montanari", "Edoardo Galimberti"],
    "es": ["Ainhoa Etxeberria", "Jordi Puigdemunt", "Rocío Valdivieso", "Iñaki Arrieta"],
    "pl": ["Małgorzata Wiśniewska", "Krzysztof Zieliński", "Agnieszka Dąbrowska", "Tomasz Kaczmarek"],
}
# --heldout: other people, other seed; nothing in eu.py was tuned on these names
HELDOUT = {
    "en": ["Philippa Hargreaves", "Rory Whitfield", "Eleanor Cartwright", "Jamie Thornbury",
           "Lydia Ormerod", "Simon Prestwich", "Natalie Bramwell", "Owen Treharne"],
    "nl": ["Esther Wijnands", "Ruben Schouten", "Lieke Vermeulen", "Gert-Jan Kooistra",
           "Iris Molenaar", "Dirk Postma", "Yvonne Brinkman", "Hugo Dijkstra"],
    "de": ["Kathrin Wohlgemuth", "Stefan Ostermann", "Renate Lichtenberg", "Florian Achenbach",
           "Birgit Kühnel", "Andreas Hollmann", "Petra Sommerfeld", "Johannes Weidinger"],
    "fr": ["Manon Lefebvre", "Julien Marchetti", "Camille Dufresne", "Antoine Berthelot"],
    "it": ["Francesca Zanetti", "Lorenzo Castellani", "Giulia Morandi", "Matteo Ruggieri"],
    "es": ["Lucía Ortega", "Javier Sandoval", "Marta Quintero", "Álvaro Benítez"],
    "pl": ["Joanna Kowalczyk", "Paweł Szymański", "Monika Lewandowska", "Marek Jabłoński"],
}
STREETS = {
    "en": [("42 Ravensworth Road", "Leeds LS6 2PQ"), ("7 Holly Bank Close", "Bristol BS8 4JT"),
           ("118 Albert Terrace", "Manchester M20 6RX"), ("3 Kingfisher Way", "Norwich NR4 7TJ")],
    "nl": [("Keizersgracht 418", "1016 GD Amsterdam"), ("Oudegracht 211", "3511 NH Utrecht"),
           ("Lange Voorhout 36", "2514 EE Den Haag"), ("Witte de Withstraat 88", "3012 BR Rotterdam")],
    "de": [("Lindenstraße 14", "50674 Köln"), ("Am Rosengarten 3", "80331 München"),
           ("Hauptstraße 152", "69117 Heidelberg"), ("Kirchweg 27", "22297 Hamburg")],
    "fr": [("12 rue des Lilas", "69003 Lyon"), ("47 avenue Jean Jaurès", "31000 Toulouse")],
    "it": [("Via Garibaldi 28", "40124 Bologna"), ("Corso Vittorio Emanuele 112", "10121 Torino")],
    "es": [("Calle Mayor 17, 3º B", "28013 Madrid"), ("Carrer de Mallorca 241", "08008 Barcelona")],
    "pl": [("ul. Długa 14/3", "80-827 Gdańsk"), ("ul. Kwiatowa 7", "30-019 Kraków")],
}
PHONE = {"en": lambda: f"+44 7{R.randint(100, 999)} {R.randint(100000, 999999)}",
         "nl": lambda: f"06-{R.randint(10000000, 99999999)}",
         "de": lambda: f"+49 171 {R.randint(1000000, 9999999)}",
         "fr": lambda: f"06 {R.randint(10, 99)} {R.randint(10, 99)} {R.randint(10, 99)} {R.randint(10, 99)}",
         "it": lambda: f"+39 347 {R.randint(100, 999)} {R.randint(1000, 9999)}",
         "es": lambda: f"+34 612 {R.randint(100, 999)} {R.randint(100, 999)}",
         "pl": lambda: f"+48 501 {R.randint(100, 999)} {R.randint(100, 999)}"}
NATID = {"en": ("PASSPORT", "uk_pass"), "nl": ("NATIONAL_ID", "bsn"), "de": ("NATIONAL_ID", "steuer"),
         "fr": ("NATIONAL_ID", "nir"), "it": ("NATIONAL_ID", "cf"), "es": ("NATIONAL_ID", "nie"), "pl": ("NATIONAL_ID", "pesel")}
IBAN = {"en": lambda: B.iban("GB"),
        "nl": lambda: B.iban("NL"), "de": lambda: B.iban("DE"), "fr": lambda: B.iban("FR"), "it": lambda: B.iban("IT"),
        "es": lambda: B.iban("ES"), "pl": lambda: B.iban("PL")}

# Four letters a Turkish firm gets from EU clients, per language. {name}, {addr}, ... are filled per person.
LETTERS = {
 "en": [
  ("Purchase of the flat in Kalkan", """Dear Ms Erel,

Following our call, I confirm that I wish to go ahead with the purchase of the flat in Kalkan (Ada 118, Parsel 4).
My details for the power of attorney are below.

Full name: {{PERSON:{name}}}
Date of birth: {{BIRTH_DATE:{dob}}}
Home address: {{ADDRESS:{addr}}}
Passport number: {{PASSPORT:{id}}}

The deposit of GBP 25,000 will come from my account {{IBAN:{iban}}}.
Please call me on {{PHONE:{phone}}} if anything is missing.

Kind regards,
{{PERSON:{name}}}""", ["Ada 118, Parsel 4", "GBP 25,000", "power of attorney"]),
  ("Estate of my late father", """Dear Ms Erel,

My father, {{PERSON:{other}}}, passed away in Fethiye in March. I am his only child and need a certificate of
inheritance (veraset ilamı) from the Fethiye court.

I was born on {{BIRTH_DATE:{dob}}} and live at {{ADDRESS:{addr}}}. My passport number is {{PASSPORT:{id}}}.
You can reach me on {{PHONE:{phone}}} or by e-mail.

Best wishes,
{{PERSON:{name}}}""", ["veraset ilamı", "Fethiye court"]),
  ("Unpaid rent, villa in Bodrum", """Hello,

The tenant of our villa in Bodrum, {{PERSON:{other}}}, has not paid rent since July (EUR 1,800 a month).
The lease was signed on 1 May 2025 for two years. Could you send a formal notice (ihtarname) through the notary?

The rent was paid to {{IBAN:{iban}}}, which is in my name ({{PERSON:{name}}}).
My mobile is {{PHONE:{phone}}}.

Thanks,
{{PERSON:{name}}}""", ["EUR 1,800 a month", "ihtarname", "1 May 2025"]),
  ("Residence permit renewal", """Dear Sir or Madam,

My residence permit in Antalya expires on 30 January 2027 and I would like your firm to handle the renewal.
Name: {{PERSON:{name}}}
Date of birth: {{BIRTH_DATE:{dob}}}
Passport no.: {{PASSPORT:{id}}}
Address in the UK: {{ADDRESS:{addr}}}

My wife, {{PERSON:{other}}}, will apply at the same time.

Regards,
{{PERSON:{name}}}
{{PHONE:{phone}}}""", ["30 January 2027", "residence permit in Antalya"]),
 ],
 "nl": [
  ("Aankoop appartement Didim", """Beste mevrouw Erel,

Zoals besproken wil ik doorgaan met de aankoop van het appartement in Didim (Ada 2207, Parsel 11).
Hieronder mijn gegevens voor de volmacht.

Naam: {{PERSON:{name}}}
Geboortedatum: {{BIRTH_DATE:{dob}}}
Adres: {{ADDRESS:{addr}}}
BSN: {{NATIONAL_ID:{id}}}

De aanbetaling van € 30.000 komt van rekening {{IBAN:{iban}}}.
U kunt mij bellen op {{PHONE:{phone}}}.

Met vriendelijke groet,
{{PERSON:{name}}}""", ["Ada 2207, Parsel 11", "€ 30.000", "volmacht"]),
  ("Nalatenschap van mijn moeder", """Beste mevrouw Erel,

Mijn moeder, {{PERSON:{other}}}, is in april in Alanya overleden. Ik heb een verklaring van erfrecht
(veraset ilamı) nodig van de rechtbank in Alanya.

Ik ben geboren op {{BIRTH_DATE:{dob}}} en woon op {{ADDRESS:{addr}}}. Mijn BSN is {{NATIONAL_ID:{id}}}.
Telefoon: {{PHONE:{phone}}}.

Hartelijke groet,
{{PERSON:{name}}}""", ["verklaring van erfrecht", "veraset ilamı"]),
  ("Huurachterstand vakantiewoning", """Hallo,

De huurder van onze vakantiewoning in Kuşadası, {{PERSON:{other}}}, betaalt sinds augustus geen huur meer
(€ 950 per maand). Kunt u via de notaris een ingebrekestelling (ihtarname) sturen?

De huur werd betaald op {{IBAN:{iban}}}, op naam van {{PERSON:{name}}}.
Mijn mobiele nummer is {{PHONE:{phone}}}.

Groeten,
{{PERSON:{name}}}""", ["€ 950 per maand", "ihtarname", "Kuşadası"]),
  ("Verlenging verblijfsvergunning", """Geachte heer/mevrouw,

Mijn verblijfsvergunning in Muğla verloopt op 15 februari 2027. Ik wil graag dat uw kantoor de verlenging regelt.
Naam: {{PERSON:{name}}}
Geboortedatum: {{BIRTH_DATE:{dob}}}
BSN: {{NATIONAL_ID:{id}}}
Adres in Nederland: {{ADDRESS:{addr}}}

Mijn partner, {{PERSON:{other}}}, vraagt tegelijk aan.

Met vriendelijke groet,
{{PERSON:{name}}}
{{PHONE:{phone}}}""", ["15 februari 2027", "verblijfsvergunning in Muğla"]),
 ],
 "de": [
  ("Kauf der Wohnung in Alanya", """Sehr geehrte Frau Erel,

wie besprochen möchte ich die Wohnung in Alanya (Ada 412, Parsel 9) kaufen. Für die Vollmacht meine Angaben:

Name: {{PERSON:{name}}}
Geburtsdatum: {{BIRTH_DATE:{dob}}}
Anschrift: {{ADDRESS:{addr}}}
Steuer-ID: {{NATIONAL_ID:{id}}}

Die Anzahlung von 40.000 EUR überweise ich von meinem Konto {{IBAN:{iban}}}.
Sie erreichen mich unter {{PHONE:{phone}}}.

Mit freundlichen Grüßen
{{PERSON:{name}}}""", ["Ada 412, Parsel 9", "40.000 EUR", "Vollmacht"]),
  ("Nachlass meines Vaters", """Sehr geehrte Frau Erel,

mein Vater, {{PERSON:{other}}}, ist im Mai in Antalya verstorben. Ich brauche einen Erbschein
(veraset ilamı) vom Gericht in Antalya.

Ich bin am {{BIRTH_DATE:{dob}}} geboren und wohne in der {{ADDRESS:{addr}}}. Steuer-ID: {{NATIONAL_ID:{id}}}.
Telefon: {{PHONE:{phone}}}.

Viele Grüße
{{PERSON:{name}}}""", ["Erbschein", "veraset ilamı"]),
  ("Mietrückstand Ferienwohnung", """Hallo Frau Erel,

der Mieter unserer Ferienwohnung in Side, {{PERSON:{other}}}, zahlt seit September keine Miete mehr
(1.200 EUR im Monat). Können Sie über den Notar eine Mahnung (ihtarname) schicken?

Die Miete ging auf das Konto {{IBAN:{iban}}}, Inhaber {{PERSON:{name}}}.
Mobil: {{PHONE:{phone}}}

Danke und Grüße
{{PERSON:{name}}}""", ["1.200 EUR im Monat", "ihtarname", "Side"]),
  ("Verlängerung der Aufenthaltserlaubnis", """Sehr geehrte Damen und Herren,

meine Aufenthaltserlaubnis in Antalya läuft am 10. März 2027 ab. Bitte übernehmen Sie die Verlängerung.
Name: {{PERSON:{name}}}
Geburtsdatum: {{BIRTH_DATE:{dob}}}
Steuer-ID: {{NATIONAL_ID:{id}}}
Anschrift in Deutschland: {{ADDRESS:{addr}}}

Meine Frau, {{PERSON:{other}}}, stellt den Antrag gleichzeitig.

Mit freundlichen Grüßen
{{PERSON:{name}}}
{{PHONE:{phone}}}""", ["10. März 2027", "Aufenthaltserlaubnis in Antalya"]),
 ],

 "fr": [
  ("Achat d'un appartement à Bodrum", """Maître,

Suite à notre entretien, je souhaite poursuivre l'achat de l'appartement à Bodrum (Ada 905, Parsel 2).
Voici mes coordonnées pour la procuration :

Nom : {{PERSON:{name}}}
Date de naissance : {{BIRTH_DATE:{dob}}}
Adresse : {{ADDRESS:{addr}}}
Numéro de sécurité sociale : {{NATIONAL_ID:{id}}}

L'acompte de 20 000 EUR sera versé depuis le compte {{IBAN:{iban}}}.
Vous pouvez me joindre au {{PHONE:{phone}}}.

Cordialement,
{{PERSON:{name}}}""", ["Ada 905, Parsel 2", "20 000 EUR", "procuration"]),
  ("Succession de mon oncle", """Bonjour Maître,

Mon oncle, {{PERSON:{other}}}, est décédé à Marmaris en juin. J'ai besoin d'un certificat d'hérédité
(veraset ilamı) du tribunal de Marmaris.

Je suis né le {{BIRTH_DATE:{dob}}} et j'habite au {{ADDRESS:{addr}}}. Téléphone : {{PHONE:{phone}}}.

Bien à vous,
{{PERSON:{name}}}""", ["certificat d'hérédité", "veraset ilamı"]),
 ],
 "it": [
  ("Acquisto appartamento a Fethiye", """Gentile Avvocato,

come concordato, desidero procedere con l'acquisto dell'appartamento a Fethiye (Ada 310, Parsel 6).
Ecco i miei dati per la procura:

Nome e cognome: {{PERSON:{name}}}
Data di nascita: {{BIRTH_DATE:{dob}}}
Indirizzo: {{ADDRESS:{addr}}}
Codice fiscale: {{NATIONAL_ID:{id}}}

L'acconto di 35.000 EUR partirà dal conto {{IBAN:{iban}}}.
Il mio cellulare è {{PHONE:{phone}}}.

Cordiali saluti,
{{PERSON:{name}}}""", ["Ada 310, Parsel 6", "35.000 EUR", "procura"]),
  ("Eredità di mia madre", """Buongiorno Avvocato,

mia madre, {{PERSON:{other}}}, è deceduta ad Antalya a luglio. Mi serve il certificato di eredità
(veraset ilamı) del tribunale di Antalya.

Sono nato il {{BIRTH_DATE:{dob}}} e abito in {{ADDRESS:{addr}}}. Telefono: {{PHONE:{phone}}}.

Distinti saluti,
{{PERSON:{name}}}""", ["certificato di eredità", "veraset ilamı"]),
 ],
 "es": [
  ("Compra de piso en Alanya", """Estimada letrada:

Como hablamos, quiero seguir adelante con la compra del piso en Alanya (Ada 77, Parsel 13).
Le envío mis datos para el poder notarial:

Nombre y apellidos: {{PERSON:{name}}}
Fecha de nacimiento: {{BIRTH_DATE:{dob}}}
Domicilio: {{ADDRESS:{addr}}}
NIE: {{NATIONAL_ID:{id}}}

La señal de 15.000 EUR saldrá de la cuenta {{IBAN:{iban}}}.
Mi móvil es el {{PHONE:{phone}}}.

Atentamente,
{{PERSON:{name}}}""", ["Ada 77, Parsel 13", "15.000 EUR", "poder notarial"]),
  ("Herencia de mi abuelo", """Hola,

Mi abuelo, {{PERSON:{other}}}, falleció en Bodrum en agosto. Necesito el certificado de herederos
(veraset ilamı) del juzgado de Bodrum.

Nací el {{BIRTH_DATE:{dob}}} y vivo en {{ADDRESS:{addr}}}. Teléfono: {{PHONE:{phone}}}.

Un saludo,
{{PERSON:{name}}}""", ["certificado de herederos", "veraset ilamı"]),
 ],
 "pl": [
  ("Zakup mieszkania w Alanyi", """Szanowna Pani Mecenas,

zgodnie z rozmową chcę kontynuować zakup mieszkania w Alanyi (Ada 512, Parsel 3).
Poniżej moje dane do pełnomocnictwa:

Imię i nazwisko: {{PERSON:{name}}}
Data urodzenia: {{BIRTH_DATE:{dob}}}
Adres: {{ADDRESS:{addr}}}
PESEL: {{NATIONAL_ID:{id}}}

Zaliczka 25 000 EUR zostanie przelana z konta {{IBAN:{iban}}}.
Mój telefon: {{PHONE:{phone}}}.

Z poważaniem,
{{PERSON:{name}}}""", ["Ada 512, Parsel 3", "25 000 EUR", "pełnomocnictwa"]),
  ("Spadek po ojcu", """Dzień dobry,

mój ojciec, {{PERSON:{other}}}, zmarł w Kemerze we wrześniu. Potrzebuję stwierdzenia nabycia spadku
(veraset ilamı) z sądu w Kemerze.

Urodziłem się {{BIRTH_DATE:{dob}}}, mieszkam: {{ADDRESS:{addr}}}. Telefon: {{PHONE:{phone}}}.

Pozdrawiam,
{{PERSON:{name}}}""", ["stwierdzenia nabycia spadku", "veraset ilamı"]),
 ],
}
HEADERS = {
    "en": ["File", "Name", "Date of birth", "Address", "Phone", "E-mail", "IBAN", "ID / passport no.", "Note"],
    "nl": ["Dossier", "Naam", "Geboortedatum", "Adres", "Telefoon", "E-mail", "IBAN", "BSN / paspoort", "Notitie"],
    "de": ["Akte", "Name", "Geburtsdatum", "Anschrift", "Telefon", "E-Mail", "IBAN", "Steuer-ID / Pass", "Notiz"],
    "fr": ["Dossier", "Nom", "Date de naissance", "Adresse", "Téléphone", "E-mail", "IBAN", "N° d'identité", "Note"],
    "it": ["Pratica", "Nome", "Data di nascita", "Indirizzo", "Telefono", "E-mail", "IBAN", "Codice fiscale", "Nota"],
    "es": ["Expediente", "Nombre", "Fecha de nacimiento", "Domicilio", "Teléfono", "Correo", "IBAN", "DNI / NIE", "Nota"],
    "pl": ["Sprawa", "Imię i nazwisko", "Data urodzenia", "Adres", "Telefon", "E-mail", "IBAN", "PESEL", "Uwagi"],
}
NOTES = {"en": ["Power of attorney signed", "Waiting for documents"], "nl": ["Volmacht getekend", "Wacht op documenten"],
         "de": ["Vollmacht unterschrieben", "Unterlagen ausstehend"], "fr": ["Procuration signée", "Documents attendus"],
         "it": ["Procura firmata", "Documenti in attesa"], "es": ["Poder firmado", "Faltan documentos"],
         "pl": ["Pełnomocnictwo podpisane", "Czekamy na dokumenty"]}
COL_TYPES = ["PERSON", "BIRTH_DATE", "ADDRESS", "PHONE", "EMAIL", "IBAN", ("NATIONAL_ID", "PASSPORT", "ID_DOCUMENT")]


def mail_of(name, cc):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", ".", s).strip(".") + f"@example.{cc}"


def dob():
    return f"{R.randint(1, 28):02d}.{R.randint(1, 12):02d}.{R.randint(1948, 1995)}"


def new_letters(pools):
    docs = []
    for lang, letters in LETTERS.items():
        people = pools[lang]
        for i, person in enumerate(people):
            title, text, keep = letters[i % len(letters)]
            street, town = STREETS[lang][i % len(STREETS[lang])]
            kind = NATID[lang][1]
            fill = {"name": person, "other": people[(i + 3) % len(people)].split()[0] + " " + people[(i + 2) % len(people)].split()[-1],
                    "dob": dob(), "addr": f"{street}, {town}", "id": B.GEN[kind](), "iban": IBAN[lang](), "phone": PHONE[lang]()}
            body = text
            for k, v in fill.items():
                body = body.replace("{" + k + "}", v)
            d = B.render({"id": f"{lang}-{i + 1:02d}", "case": "", "doc_type": "letter", "lang": lang, "title": title,
                          "text": body, "keep": keep})
            d["sender"] = person
            d["email"] = mail_of(person, {"en": "co.uk"}.get(lang, lang))
            docs.append(d)
    return docs


def first_of(doc, t):
    ts = t if isinstance(t, tuple) else (t,)
    return next((g["text"] for g in doc["gold"] if g["type"] in ts), "")


def main(out: Path, heldout: bool = False):
    if heldout:
        B.R.seed(3011)
        R.seed(3011)
    out.mkdir(parents=True, exist_ok=True)
    pack = [json.loads(x) for x in (ROOT / "lab" / "samples" / "data" / "eu_docs.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    for d in pack:
        p = next((g["text"] for g in d["gold"] if g["type"] == "PERSON"), "Client")
        d["sender"], d["email"] = p, next((g["text"] for g in d["gold"] if g["type"] == "EMAIL"), None) or mail_of(p, "eu")
    docs = (pack if not heldout else []) + new_letters(HELDOUT if heldout else PEOPLE)
    key = {}
    for i, d in enumerate(docs):
        gold = list(dict.fromkeys([g["text"] for g in d["gold"]] + [d["email"]]))
        head = {"Kimden": f"{d['sender']} <{d['email']}>", "Kime": FIRM, "Konu": d["title"], "Tarih": "12.11.2026"}
        att = [("scan.pdf", b"%PDF-1.4 sample")] if i % 3 == 0 else []
        style = STYLES[i % len(STYLES)]
        (out / f"{d['id']}.{style}.eml").write_bytes(M.eml(head, d["text"], style, att))
        (out / f"{d['id']}.msg").write_bytes(M.msg(head, d["text"], html_only=(i % 2 == 1), attachments=att))
        (out / f"{d['id']}.txt").write_text(d["text"], encoding="utf-8")
        meta = {"keep": d["keep"], "source": [d["id"]], "lang": d["lang"]}
        key[f"{d['id']}.{style}.eml"] = {"mask": gold, **meta}
        key[f"{d['id']}.msg"] = {"mask": gold, **meta}
        key[f"{d['id']}.txt"] = {"mask": [g["text"] for g in d["gold"]], **meta, "baseline": True}
    for lang in LETTERS:
        group = [d for d in docs if d["lang"] == lang]
        rows, gold = [HEADERS[lang]], []
        for j, d in enumerate(group):
            row = [f"{2026}/{300 + j}"]
            for t in COL_TYPES:
                v = d["email"] if t == "EMAIL" else first_of(d, t)
                row.append(v)
                if v:
                    gold.append(v)
            row.append(NOTES[lang][j % 2])
            rows.append(row)
        name = f"clients_{lang}.xlsx"
        (out / name).write_bytes(M.xlsx([(HEADERS[lang][0] if lang not in ("en", "nl", "de") else {"en": "Clients", "nl": "Cliënten", "de": "Mandanten"}[lang], rows)], creator="Katip sample"))
        key[name] = {"mask": list(dict.fromkeys(gold)), "keep": NOTES[lang], "source": [d["id"] for d in group], "lang": lang}
    (out / "answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    n = lambda ext: sum(1 for f in key if f.endswith(ext))
    print(f"{out}: {n('.eml')} .eml, {n('.msg')} .msg, {n('.xlsx')} .xlsx, {n('.txt')} .txt baselines")


if __name__ == "__main__":
    main(Path(sys.argv[1]), "--heldout" in sys.argv)
