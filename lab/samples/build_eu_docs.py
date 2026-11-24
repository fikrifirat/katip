"""Write the sample pack's cross-border documents (data/eu_docs.jsonl) from the marked-up texts below.

Each text marks every value that must be masked as {{TYPE:value}}. ID numbers are written as {{TYPE:@kind}} and
drawn here with a valid checksum (seed fixed), so every number is fictional but well formed. `keep` lists strings
that must stay readable (courts, case numbers, statutes, notaries' register numbers, companies).

The documents imitate what a Turkish law firm receives from EU clients: powers of attorney for a property purchase
in Antalya, a German certificate of inheritance, a Dutch divorce order for recognition (tanıma-tenfiz), an apostille,
a sworn translation, KYC for a share transfer, a data-subject request, a breach notice, a WhatsApp chat. They were
written from the public shape of these documents (see README, "Sources") before any of them was scored. All people,
numbers and addresses are invented.

    python lab/samples/build_eu_docs.py
"""
from __future__ import annotations

import json
import random
import re
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "connector"))
from katip_kalkan import eu  # noqa: E402

R = random.Random(2411)


def _digits(n):
    return "".join(R.choice(string.digits) for _ in range(n))


def _draw(make, ok):
    while True:
        v = make()
        if ok(v):
            return v


def tckn():
    d = [R.randint(1, 9)] + [R.randint(0, 9) for _ in range(8)]
    d.append((sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10)
    d.append(sum(d) % 10)
    return "".join(map(str, d))


def iban(cc):
    length = eu.IBAN_LEN[cc]
    body = _digits(length - 4)
    if cc in ("NL", "IE", "GB"):
        body = "".join(R.choice(string.ascii_uppercase) for _ in range(4)) + body[4:]
    if cc == "IT":
        body = R.choice(string.ascii_uppercase) + body[1:]
    raw = cc + "00" + body
    chk = 98 - int("".join(str(int(c, 36)) for c in raw[4:] + raw[:4])) % 97
    v = f"{cc}{chk:02d}{body}"
    return " ".join(v[i:i + 4] for i in range(0, len(v), 4))


def cf():
    def mk():
        s = ("".join(R.choice(string.ascii_uppercase) for _ in range(6)) + _digits(2) + R.choice("ABCDEHLMPRST")
             + f"{R.randint(1, 71):02d}" + R.choice("ABCDEFGHILM") + _digits(3))
        tot = sum(eu._CF_ODD[c] if i % 2 == 0 else (int(c) if c.isdigit() else ord(c) - 65) for i, c in enumerate(s))
        return s + chr(65 + tot % 26)
    return _draw(mk, eu.cf_valid)


def nir():
    def mk():
        body = R.choice("12") + _digits(2) + f"{R.randint(1, 12):02d}" + f"{R.randint(1, 95):02d}" + _digits(6)
        return body + f"{97 - int(body) % 97:02d}"
    v = _draw(mk, eu.nir_valid)
    return f"{v[0]} {v[1:3]} {v[3:5]} {v[5:7]} {v[7:10]} {v[10:13]} {v[13:]}"


def pesel():
    return _draw(lambda: _digits(11), eu.pesel_valid)


def nie():
    n = _digits(7)
    p = R.choice("XYZ")
    return f"{p}{n}{eu._DNI_LETTERS[int(str('XYZ'.index(p)) + n) % 23]}"


GEN = {
    "steuer": lambda: (lambda v: f"{v[:2]} {v[2:5]} {v[5:8]} {v[8:]}")(_draw(lambda: R.choice("123456789") + _digits(10), eu.steuer_id_valid)),
    "bsn": lambda: _draw(lambda: _digits(9), eu.bsn_valid),
    "cf": cf, "nir": nir, "pesel": pesel, "nie": nie, "tckn": tckn,
    "iban_de": lambda: iban("DE"), "iban_nl": lambda: iban("NL"), "iban_tr": lambda: iban("TR"),
    "iban_it": lambda: iban("IT"), "iban_fr": lambda: iban("FR"),
    "perso": lambda: "".join(R.choice("CFGHJKLMNPRTVWXYZ") for _ in range(1)) + "".join(R.choice("CFGHJKLMNPRTVWXYZ0123456789") for _ in range(8)),
    "nl_pass": lambda: "N" + "".join(R.choice("ABCDEFGHJKLNPRSTUVWXYZ") for _ in range(1)) + "".join(R.choice("ABCDEFGHJKLNPRSTUVWXYZ0123456789") for _ in range(6)) + _digits(1),
    "uk_pass": lambda: _digits(9),
    "it_ci": lambda: "CA" + _digits(5) + "".join(R.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(2)),
}

# --------------------------------------------------------------------------------------------- documents
DOCS = [
 dict(id="eu-01", case="S-EU-01", doc_type="power_of_attorney", lang="de", title="German notarial power of attorney for a flat purchase in Alanya",
  text="""UR-Nr. 1187/2026 B

Vollmacht

Heute, den 14. Oktober 2026, erschien vor mir, Dr. {{PERSON:Heike Brandstätter}}, Notarin mit dem Amtssitz in Düsseldorf,
Herr {{PERSON:Jörg Pfannenschmidt}}, geboren am {{BIRTH_DATE:03.07.1961}} in Mönchengladbach,
wohnhaft {{ADDRESS:Kaiserswerther Straße 212, 40474 Düsseldorf}},
ausgewiesen durch Personalausweis Nr. {{ID_DOCUMENT:@perso}}, Steuer-Identifikationsnummer {{NATIONAL_ID:@steuer}}.

Der Erschienene erklärte:
Ich bevollmächtige hiermit Frau Rechtsanwältin Av. {{PERSON:Selin Karaağaç}}, T.C. Kimlik Nr. {{TCKN:@tckn}},
Antalya Barosu Sicil Nr. 4471, mich vor dem Tapu Müdürlüğü Alanya beim Erwerb der Wohnung in Mahmutlar Mahallesi,
Ada 412, Parsel 9, Block B, Unabhängige Einheit Nr. 14 zu vertreten, den Kaufpreis von 165.000 EUR von meinem Konto
{{IBAN:@iban_de}} zu überweisen und die DASK-Versicherung abzuschließen.

Die Vollmacht erlischt am 31.12.2027. Kosten nach GNotKG trägt der Vollmachtgeber.

{{PERSON:Jörg Pfannenschmidt}}                       {{PERSON:Brandstätter}}, Notarin""",
  keep=["UR-Nr. 1187/2026 B", "Düsseldorf", "Tapu Müdürlüğü Alanya", "Ada 412, Parsel 9", "Antalya Barosu", "GNotKG", "165.000 EUR"]),

 dict(id="eu-02", case="S-EU-02", doc_type="inheritance_certificate", lang="de", title="German certificate of inheritance (Erbschein) for a dual citizen's estate",
  text="""Amtsgericht Köln
- Nachlassgericht -
Geschäftsnummer: 32 VI 518/26

Erbschein

Es wird bezeugt, dass der am {{BIRTH_DATE:11.02.1949}} in Kayseri (Türkei) geborene und am 2. Mai 2026 in Köln verstorbene
{{PERSON:Hüseyin Kaplanoğlu}}, zuletzt wohnhaft {{ADDRESS:Keupstraße 61, 51063 Köln}},
beerbt worden ist von:
  1. seiner Ehefrau {{PERSON:Gülizar Kaplanoğlu geb. Sert}}, geboren am {{BIRTH_DATE:20.09.1953}}, zu 1/2,
  2. seinem Sohn {{PERSON:Murat Kaplanoğlu}}, wohnhaft {{ADDRESS:Bergisch Gladbacher Str. 1040, 51069 Köln}}, zu 1/4,
  3. seiner Tochter {{PERSON:Derya Rauschenberger geb. Kaplanoğlu}}, wohnhaft in Wien, zu 1/4.

Der Erbschein ist beschränkt auf den im Inland befindlichen Nachlass (§ 352c FamFG). Für das in der Türkei
belegene unbewegliche Vermögen gilt nach Art. 20 Abs. 1 des türkischen Gesetzes Nr. 5718 türkisches Recht.

Köln, 18.08.2026
{{PERSON:Overbeck}}, Rechtspflegerin""",
  keep=["Amtsgericht Köln", "32 VI 518/26", "§ 352c FamFG", "Gesetzes Nr. 5718", "Kayseri"]),

 dict(id="eu-03", case="S-EU-03", doc_type="court_order", lang="nl", title="Dutch divorce order sent for recognition in Türkiye (tanıma-tenfiz)",
  text="""ECLI:NL:RBROT:2026:4417
RECHTBANK ROTTERDAM
Team familie
zaaknummer / rekestnummer: C/10/701233 / FA RK 26-2290

Beschikking van 9 juli 2026 op het verzoek van:
{{PERSON:Sevda Akbulut}},
wonende te {{ADDRESS:Groene Hilledijk 318, 3074 AM Rotterdam}},
BSN {{NATIONAL_ID:@bsn}},
verzoekster, advocaat mr. {{PERSON:F.J. van Kooten}},

tegen

{{PERSON:Erdinç Akbulut}},
wonende te Bursa (Turkije), geboren op {{BIRTH_DATE:14 maart 1984}},
verweerder, niet verschenen.

De rechtbank spreekt de echtscheiding uit tussen partijen, gehuwd te Bursa op 22 juni 2009.
Ten aanzien van de minderjarige {{PERSON:Elif Akbulut}}, geboren op {{BIRTH_DATE:5 januari 2012}}, en
{{PERSON:Yusuf Akbulut}}, geboren op {{BIRTH_DATE:30 oktober 2015}}, wordt het ouderschapsplan (artikel 815 Rv)
aan deze beschikking gehecht. Verweerder betaalt een kinderalimentatie van € 310 per kind per maand.

Deze beschikking is gegeven door mr. {{PERSON:A.M. Dijkstra-Hoekstra}}, rechter, en in het openbaar uitgesproken.""",
  keep=["ECLI:NL:RBROT:2026:4417", "RECHTBANK ROTTERDAM", "C/10/701233 / FA RK 26-2290", "artikel 815 Rv", "Bursa"]),

 dict(id="eu-04", case="S-EU-04", doc_type="tanima_tenfiz_petition", lang="tr", title="Turkish recognition petition about the Dutch divorce (foreign names inside Turkish text)",
  text="""BURSA NÖBETÇİ AİLE MAHKEMESİ HAKİMLİĞİ'NE

DAVACI      : {{PERSON:Sevda Akbulut}} (T.C. Kimlik No: {{TCKN:@tckn}})
              {{ADDRESS:Groene Hilledijk 318, 3074 AM Rotterdam / HOLLANDA}}
VEKİLİ      : Av. {{PERSON:Burak Tezcanlı}}, Bursa Barosu
DAVALI      : {{PERSON:Erdinç Akbulut}} (T.C. Kimlik No: {{TCKN:@tckn}})
              {{ADDRESS:Fethiye Mah. Kanarya Sk. No: 7 D: 3 Nilüfer/BURSA}}
KONU        : Rotterdam Mahkemesi'nin 09.07.2026 tarihli, C/10/701233 / FA RK 26-2290 sayılı boşanma kararının
              5718 sayılı MÖHUK m.50 vd. uyarınca tanınması talebidir.

AÇIKLAMALAR :
1. Taraflar 22.06.2009 tarihinde Bursa'da evlenmiş, müşterek çocuklar {{PERSON:Elif}} ve {{PERSON:Yusuf}} dünyaya gelmiştir.
2. Davacı Hollanda'da ikamet etmekte olup Hollanda kimlik numarası (BSN) {{NATIONAL_ID:@bsn}}'dir. Hollanda mahkemesinde
   davalı usulüne uygun çağrılmış, ancak duruşmaya gelmemiştir. Davalıya tebligat mr. {{PERSON:F.J. van Kooten}} aracılığıyla yapılmıştır.
3. Karar Lahey Apostil Şerhi ile onaylanmış ve yeminli tercüman {{PERSON:Nermin Uçar}} tarafından tercüme edilmiştir.

HUKUKİ NEDENLER : 5718 s. MÖHUK m.50-59, HMK ve ilgili mevzuat.
SONUÇ VE İSTEM  : Yabancı mahkeme kararının tanınmasına ve nüfus kütüğüne işlenmesine karar verilmesini saygıyla arz ederim.

Davacı Vekili Av. {{PERSON:Burak Tezcanlı}}""",
  keep=["BURSA NÖBETÇİ AİLE MAHKEMESİ", "C/10/701233 / FA RK 26-2290", "MÖHUK m.50", "Bursa Barosu", "HMK"]),

 dict(id="eu-05", case="S-EU-05", doc_type="apostille", lang="de", title="Apostille on a German court document (Hague Convention 1961 form)",
  text="""APOSTILLE
(Convention de La Haye du 5 octobre 1961)

1. Land: Bundesrepublik Deutschland
   Diese öffentliche Urkunde
2. ist unterschrieben von {{PERSON:Sabine Overbeck}}
3. in seiner/ihrer Eigenschaft als Rechtspflegerin
4. sie ist versehen mit dem Siegel des Amtsgerichts Köln
                    Bestätigt
5. in Köln                                 6. am 25.08.2026
7. durch den Präsidenten des Landgerichts Köln
8. unter Nr. 4120 E – 1938/26
9. Stempel/Siegel                          10. Unterschrift
                                               Dr. {{PERSON:Kühnemund-Ebersbach}}""",
  keep=["Amtsgerichts Köln", "Landgerichts Köln", "4120 E – 1938/26", "Convention de La Haye du 5 octobre 1961"]),

 dict(id="eu-06", case="S-EU-06", doc_type="sworn_translation", lang="tr", title="Sworn translation of the Erbschein with the translator's certificate",
  text="""(Almanca aslından tercümedir)
KÖLN SULH HUKUK MAHKEMESİ – Tereke Mahkemesi – Dosya No: 32 VI 518/26
MİRASÇILIK BELGESİ
02.05.2026 tarihinde Köln'de vefat eden, {{BIRTH_DATE:11.02.1949}} Kayseri doğumlu {{PERSON:Hüseyin Kaplanoğlu}}'nun mirasçıları:
eşi {{PERSON:Gülizar Kaplanoğlu}} (1/2), oğlu {{PERSON:Murat Kaplanoğlu}} (1/4), kızı {{PERSON:Derya Rauschenberger}} (1/4).

Tercümanın Beyanı: Almanca dilinden Türkçeye yapılan bu tercümenin aslına uygun olduğunu beyan ederim.
Yeminli Tercüman {{PERSON:Nermin Uçar}} – T.C. Kimlik No: {{TCKN:@tckn}}
Beyoğlu 27. Noterliği yemin zaptı tarih/no: 11.03.2019 / 05612
İrtibat: {{PHONE:+90 532 418 27 63}} – {{EMAIL:nermin.ucar.ceviri@example.com.tr}}""",
  keep=["32 VI 518/26", "Beyoğlu 27. Noterliği", "11.03.2019 / 05612"]),

 dict(id="eu-07", case="S-EU-07", doc_type="power_of_attorney", lang="it", title="Italian special power of attorney to set up a Turkish company",
  text="""PROCURA SPECIALE
Repertorio n. 48.211          Raccolta n. 17.906

Il sottoscritto {{PERSON:Gianluca Benvenuti}}, nato a Prato il {{BIRTH_DATE:9 novembre 1977}}, residente in
{{ADDRESS:Via Ferrucci 88, 59100 Prato}}, codice fiscale {{NATIONAL_ID:@cf}}, carta d'identità n. {{ID_DOCUMENT:@it_ci}},
nomina e costituisce suo procuratore speciale l'avv. {{PERSON:Kerem Dalkılıç}} del Foro di Istanbul affinché, in suo nome,
costituisca in Turchia la società "Benvenuti Tessuti Dış Ticaret Limited Şirketi", sottoscriva l'atto costitutivo
davanti al Registro delle Imprese di Istanbul (İstanbul Ticaret Sicili Müdürlüğü) e apra un conto presso una banca turca.
Il capitale sociale di TRY 50.000 sarà versato dal conto {{IBAN:@iban_it}}.

Prato, 3 settembre 2026
Notaio Dott.ssa {{PERSON:Giuseppina Lo Faro}}""",
  keep=["Repertorio n. 48.211", "Raccolta n. 17.906", "Benvenuti Tessuti Dış Ticaret Limited Şirketi", "İstanbul Ticaret Sicili Müdürlüğü", "TRY 50.000"]),

 dict(id="eu-08", case="S-EU-08", doc_type="attestation", lang="fr", title="French sworn statement for a Turkish employment claim",
  text="""ATTESTATION SUR L'HONNEUR
(article 202 du code de procédure civile)

Je soussigné, {{PERSON:Benoît Laforgue}}, né le {{BIRTH_DATE:17 avril 1980}} à Lyon, demeurant {{ADDRESS:14 rue Paul Bert, 69003 Lyon}},
numéro de sécurité sociale {{NATIONAL_ID:@nir}}, ancien directeur des achats de la société Rhône Textiles SAS,
atteste que M. {{PERSON:Okan Yeşilyurt}} a travaillé sous mes ordres à Istanbul du 1er mars 2021 au 30 juin 2025,
à temps plein, et qu'il recevait ses instructions directement de Lyon.

Je sais que cette attestation est destinée à être produite en justice devant le İstanbul 21. İş Mahkemesi
et qu'une fausse attestation m'expose à des sanctions pénales (article 441-7 du code pénal).

Fait à Lyon, le 2 octobre 2026.
Contact : {{EMAIL:b.laforgue@orange.example.fr}} – {{PHONE:+33 6 71 24 90 18}}
{{PERSON:B. Laforgue}}""",
  keep=["article 202 du code de procédure civile", "Rhône Textiles SAS", "İstanbul 21. İş Mahkemesi", "article 441-7 du code pénal"]),

 dict(id="eu-09", case="S-EU-09", doc_type="kyc", lang="en", title="KYC sheet for a UK buyer in a Turkish share transfer",
  text="""KNOW-YOUR-CLIENT SUMMARY – Project Lodos (share purchase, Ege Zeytin Gıda A.Ş.)
Prepared by: Associate {{PERSON:Deniz Arıkan}} / reviewed by Partner Av. {{PERSON:Ömer Faruk Tunalı}}

Buyer: Thornbury Olive Holdings Ltd (Companies House no. 09812345)
Ultimate beneficial owner: {{PERSON:Alistair Fenwick-Rowe}}, British citizen, born {{BIRTH_DATE:22 January 1969}},
passport no. {{PASSPORT:@uk_pass}}, residential address {{ADDRESS:Flat 4, 27 Pembridge Villas, London W11 3EP}}.
Second director: {{PERSON:Priyanka Raghunathan}}, residential address {{ADDRESS:12 Elm Grove, Harrogate HG1 2JL}}.
Source of funds: sale of {{PERSON:Fenwick-Rowe}}'s shares in Cotswold Presses plc (2025), confirmed by Barclays letter.
Screening (MASAK 6415 m.5/m.6/m.7, 7262; UN 1267): no hits on 20.11.2026. PEP: none declared.
Contact for completion: {{EMAIL:a.fenwickrowe@thornbury-olive.example.co.uk}}, {{PHONE:+44 7700 900 418}}.""",
  keep=["Ege Zeytin Gıda A.Ş.", "Thornbury Olive Holdings Ltd", "09812345", "Cotswold Presses plc", "MASAK 6415 m.5/m.6/m.7, 7262", "UN 1267"]),

 dict(id="eu-10", case="S-EU-10", doc_type="dsar_email", lang="en", title="Data-subject access request from an EU resident to a Turkish firm",
  text="""From: {{PERSON:Siobhán McGettigan}} <{{EMAIL:siobhan.mcgettigan@example.ie}}>
To: kvkk@karaagac-hukuk.example.com.tr
Subject: Subject access request under Article 15 GDPR and KVKK m.11

Dear Sir or Madam,

I stayed at the Alanya hotel you represent in the dispute with Sunwing Travel in August 2026 and I understand my
booking file was passed to your firm. Please send me a copy of all personal data you hold about me, the purposes,
the recipients (including any AI service), and the retention period, as required by Article 15 GDPR and
Article 11 of Law No. 6698.

My details for identification: date of birth {{BIRTH_DATE:04/06/1990}}, address {{ADDRESS:31 Fairview Strand, Dublin 3, D03 KX88}},
booking reference ALY-26-77812.

Kind regards,
{{PERSON:Siobhán McGettigan}}
{{PHONE:+353 87 412 6630}}""",
  keep=["Article 15 GDPR", "Article 11 of Law No. 6698", "Sunwing Travel", "ALY-26-77812"]),

 dict(id="eu-11", case="S-EU-11", doc_type="breach_notice", lang="en", title="IT vendor's breach notice to the firm (GDPR Art. 33 / KVKK m.12)",
  text="""SECURITY INCIDENT NOTIFICATION – ref. INC-2026-0412

To: Managing Partner, Karaağaç Hukuk Bürosu
From: {{PERSON:Thijs Wijnberg}}, Incident Lead, NordCloud Backup B.V. ({{EMAIL:t.wijnberg@nordcloud-backup.example.nl}})

On 19 November 2026 at 03:12 CET we detected unauthorised access to one storage bucket (eu-west-4) holding your
encrypted nightly backups. The attacker used the API key of a former contractor, {{PERSON:Ruslan Gaynutdinov}}, which
had not been revoked. We have no evidence that the encryption keys were accessed.

Affected: 1 bucket, 2,418 files, period 01.06.2026–18.11.2026. Our DPO, {{PERSON:Annelies Verhoeven}}
({{PHONE:+31 20 794 1180}}), is available for your notification to the KVKK Board within 72 hours (KVKK m.12/5,
Board decision 2019/10) and to the Autoriteit Persoonsgegevens where relevant (GDPR Art. 33).""",
  keep=["INC-2026-0412", "Karaağaç Hukuk Bürosu", "NordCloud Backup B.V.", "KVKK m.12/5", "2019/10", "GDPR Art. 33", "Autoriteit Persoonsgegevens"]),

 dict(id="eu-12", case="S-EU-12", doc_type="chat", lang="mixed", title="WhatsApp export: German client, Turkish lawyer, property dispute in Fethiye",
  text="""[03.11.26, 09:14:22] {{PERSON:Ingrid Halvorsen-Bauer}}: Guten Morgen Frau Anwältin, der Verkäufer {{PERSON:Cengiz Toprakoğlu}} antwortet nicht mehr.
[03.11.26, 09:15:03] {{PERSON:Ingrid Halvorsen-Bauer}}: Seine Nummer ist {{PHONE:0533 714 22 09}}, vielleicht rufen Sie ihn an?
[03.11.26, 09:31:47] Av. {{PERSON:Pınar Ekici}}: Günaydın {{PERSON:Ingrid}} Hanım, bugün arayacağım. Tapu kaydı Fethiye Tapu Müdürlüğü'nde, Ada 118 Parsel 4.
[03.11.26, 09:32:10] Av. {{PERSON:Pınar Ekici}}: Can you send me your passport copy again? The notary in Fethiye needs it.
[03.11.26, 10:02:55] {{PERSON:Ingrid Halvorsen-Bauer}}: Pass Nr. {{PASSPORT:C4R7NK2T9}}, gültig bis 2031. Mein Mann {{PERSON:Rüdiger}} kommt am 20.11.
[03.11.26, 10:03:30] {{PERSON:Ingrid Halvorsen-Bauer}}: <Medien ausgeschlossen>""",
  keep=["Fethiye Tapu Müdürlüğü", "Ada 118 Parsel 4"]),

 dict(id="eu-13", case="S-EU-13", doc_type="power_of_attorney", lang="pl", title="Polish power of attorney for a Turkish debt claim",
  text="""PEŁNOMOCNICTWO

Ja, niżej podpisana {{PERSON:Małgorzata Wierzbicka-Ossowska}}, urodzona {{BIRTH_DATE:12.12.1975}} r., PESEL {{NATIONAL_ID:@pesel}},
zamieszkała {{ADDRESS:ul. Grunwaldzka 186/12, 80-266 Gdańsk}}, działająca jako prezes zarządu spółki Baltic Amber Trade Sp. z o.o.
(KRS 0000612345), udzielam pełnomocnictwa adwokatowi Av. {{PERSON:Taner Gökbudak}} z Izby Adwokackiej w Izmirze
do reprezentowania spółki w postępowaniu egzekucyjnym przed İzmir 14. İcra Dairesi, sygn. 2026/18831 Esas,
przeciwko spółce Kordon Mermer San. ve Tic. A.Ş.

Gdańsk, dnia 7 października 2026 r.
{{PERSON:M. Wierzbicka-Ossowska}}""",
  keep=["Baltic Amber Trade Sp. z o.o.", "KRS 0000612345", "İzmir 14. İcra Dairesi", "2026/18831 Esas", "Kordon Mermer San. ve Tic. A.Ş."]),

 dict(id="eu-14", case="S-EU-14", doc_type="power_of_attorney", lang="es", title="Spanish notarial power for a Turkish inheritance (NIE holder)",
  text="""PODER ESPECIAL
Número mil doscientos cuatro (1.204)

En Málaga, a veintiuno de septiembre de dos mil veintiséis.
Ante mí, {{PERSON:Íñigo Arrizabalaga Etxeberria}}, Notario del Ilustre Colegio de Andalucía,

COMPARECE:
Doña {{PERSON:Ainhoa Castelló Ribera}}, mayor de edad, casada, vecina de Málaga, con domicilio en {{ADDRESS:Calle Larios, 9, 29005 Málaga}},
con NIE {{NATIONAL_ID:@nie}}.

Y OTORGA poder especial a favor del abogado turco Av. {{PERSON:Mert Sarıgül}} para que la represente en la sucesión
de su difunto esposo {{PERSON:Levent Sarıçiçek}} ante el İzmir 3. Sulh Hukuk Mahkemesi (mirasçılık belgesi), y cobre
las cantidades depositadas en Türkiye Garanti Bankası A.Ş.""",
  keep=["Número mil doscientos cuatro (1.204)", "Ilustre Colegio de Andalucía", "İzmir 3. Sulh Hukuk Mahkemesi", "Türkiye Garanti Bankası A.Ş."]),

 dict(id="eu-15", case="S-EU-15", doc_type="employment_letter", lang="de", title="German dismissal letter from a Turkish company's subsidiary, with a sick-leave mention",
  text="""Anatolia Logistics GmbH · Hafenstraße 9 · 28217 Bremen

Herrn
{{PERSON:Sjoerd Brinkhuis}}
{{ADDRESS:Am Wall 141, 28195 Bremen}}

Bremen, 28.10.2026

Ordentliche Kündigung des Arbeitsverhältnisses

Sehr geehrter Herr {{PERSON:Brinkhuis}},
hiermit kündigen wir das mit Ihnen bestehende Arbeitsverhältnis ordentlich und fristgerecht zum 31.01.2027
(§ 622 Abs. 2 BGB). Der Betriebsrat wurde gemäß § 102 BetrVG angehört. Ihre {{HEALTH:Arbeitsunfähigkeit}}
seit 02.10.2026 ({{HEALTH:Bandscheibenvorfall}}, AU-Bescheinigung Dr. {{PERSON:Wolters}}) ist nicht Grund der Kündigung.
Ihr Resturlaub von 11 Tagen wird mit der Abrechnung November ausgezahlt (Konto {{IBAN:@iban_de}}).

Mit freundlichen Grüßen
{{PERSON:Tolga Uzunhasanoğlu}}, Geschäftsführer""",
  keep=["Anatolia Logistics GmbH", "Hafenstraße 9", "§ 622 Abs. 2 BGB", "§ 102 BetrVG"]),

 dict(id="eu-16", case="S-EU-16", doc_type="email", lang="nl", title="Dutch client e-mail about a holiday-home dispute in Didim",
  text="""Van: {{PERSON:Lieke Brouwer-Smit}} <{{EMAIL:lieke.brouwer@example.nl}}>
Aan: {{EMAIL:av.cansu.erel@example.com.tr}}
Onderwerp: RE: Zaak Didim – terugbetaling aanbetaling

Beste mevrouw {{PERSON:Erel}},

Zoals besproken heb ik op 12 mei 2025 een aanbetaling van € 40.000 gedaan aan Didim Marina Yapı Ltd. Şti.
vanaf onze rekening {{IBAN:@iban_nl}} (op naam van mijn man {{PERSON:Bram Brouwer}}).
Mijn paspoortnummer is {{PASSPORT:@nl_pass}}; ons adres is {{ADDRESS:Prinsengracht 774-H, 1017 LH Amsterdam}}.
De makelaar was {{PERSON:Serkan Yıldızhan}} van Ege Emlak.

Met vriendelijke groet,
{{PERSON:Lieke Brouwer-Smit}}
{{PHONE:06-41827733}}""",
  keep=["Didim Marina Yapı Ltd. Şti.", "Ege Emlak", "€ 40.000"]),
]

MARK = re.compile(r"\{\{([A-Z_]+):([^}]*)\}\}")


def render(doc):
    text, gold, pos, out = doc["text"], [], 0, []
    cur = 0
    for m in MARK.finditer(text):
        out.append(text[pos:m.start()])
        cur += len(text[pos:m.start()])
        typ, val = m.group(1), m.group(2)
        if val.startswith("@"):
            val = GEN[val[1:]]()
        gold.append({"type": typ, "start": cur, "end": cur + len(val), "text": val})
        out.append(val)
        cur += len(val)
        pos = m.end()
    out.append(text[pos:])
    plain = "".join(out)
    for g in gold:
        assert plain[g["start"]:g["end"]] == g["text"]
    for k in doc["keep"]:
        assert k in plain, (doc["id"], k)
    return {"id": doc["id"], "case": doc["case"], "doc_type": doc["doc_type"], "lang": doc["lang"], "title": doc["title"],
            "text": plain, "gold": gold, "keep": doc["keep"]}


def main():
    rows = [render(d) for d in DOCS]
    out = HERE / "data" / "eu_docs.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} documents, {sum(len(r['gold']) for r in rows)} values -> {out}")


if __name__ == "__main__":
    main()
