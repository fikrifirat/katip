"""Second EU document set (H-EU-01..20), written by a separate agent that had not read eu.py.

Builds data/eu_heldout.jsonl with the same markup and renderer as build_eu_docs.py. Every person, number and
address is invented. Used to tune on 24 Nov 2026, so it is now a dev set, not a blind one.
"""
import json
from pathlib import Path

import build_eu_docs as B

DOCS = [
dict(id="ho-01", case="H-EU-01", doc_type="notarial_deed", lang="de", title="Notariatsakt Vollmacht Liegenschaft Alanya",
text="""NOTARIATSAKT
GZ 1184/2026

Vor mir, Mag. {{PERSON:Barbara Leitgeb-Strasser}}, öffentliche Notarin mit dem Amtssitz in Wien, Wipplingerstraße 12, 1010 Wien, sind heute erschienen:

1. {{PERSON:Florian Haidinger}}, geboren am {{BIRTH_DATE:3. März 1979}}, wohnhaft
{{ADDRESS:Krongasse 4/II/7}}
{{ADDRESS:1050 Wien}},
ausgewiesen durch Reisepass Nr. {{PASSPORT:P 4827316}};

2. {{PERSON:Selin Haidinger-Kaya}}, geb. {{BIRTH_DATE:17.11.1984}}, ebendort wohnhaft, ausgewiesen durch Personalausweis {{ID_DOCUMENT:10938472}}, ausgestellt von der LPD Wien.

Die Erschienenen erteilen hiermit Herrn Rechtsanwalt Av. {{PERSON:Mehmet Ali Yücel}}, Anwaltskammer Istanbul, Sicil-Nr. 48213, Vollmacht, die im Grundbuch des Tapu Müdürlüğü Alanya eingetragene Liegenschaft (Ada 112, Parsel 7) zu verkaufen und den Kaufpreis auf das Konto IBAN {{IBAN:AT152011182941037756}} zu überweisen.

Herr {{PERSON:Haidinger}} erklärt, der türkischen Sprache nicht mächtig zu sein; Frau {{PERSON:Haidinger-Kaya}} übersetzt für ihn. Die Identität wurde gemäß § 52 NO festgestellt. Rückfragen unter {{PHONE:0664 381 2290}}.

Wien, am 14. Oktober 2026""",
keep=["GZ 1184/2026", "Wipplingerstraße 12, 1010 Wien", "Tapu Müdürlüğü Alanya", "§ 52 NO", "Anwaltskammer Istanbul", "LPD Wien"]),

dict(id="ho-02", case="H-EU-02", doc_type="court_order", lang="nl", title="Beschikking ondernemingsrechtbank Antwerpen",
text="""ONDERNEMINGSRECHTBANK ANTWERPEN, AFDELING ANTWERPEN
Rolnummer A/26/04417 – Beschikking van 9 september 2026

In de zaak van:
{{PERSON:Pieter-Jan De Smedt}}, geboren te Mechelen op {{BIRTH_DATE:22/06/1981}}, rijksregisternummer {{NATIONAL_ID:81.06.22-147.38}}, wonende te {{ADDRESS:Lange Leemstraat 214 bus 3}}, {{ADDRESS:2018 Antwerpen}},
verzoeker, vertegenwoordigd door Mr. {{PERSON:Els Vandenbroucke}}, advocaat te 2000 Antwerpen, Amerikalei 98;

tegen:
ATLAS TEKSTİL SANAYİ VE TİCARET A.Ş., met zetel te Bursa (Turkije),
verweerster, vertegenwoordigd door haar bestuurder {{PERSON:Oğuz Karabulut}}.

De rechtbank stelt vast dat verzoeker {{PERSON:De Smedt}} de factuur nr. 2026/118 tijdig heeft geprotesteerd. Verweerster wordt bevolen de som van EUR 48.730,00 te betalen op rekening {{IBAN:BE43310184627509}} op naam van {{PERSON:Pieter-Jan}}.

Betekening aan {{PERSON:Karabulut}} geschiedt overeenkomstig Verordening (EU) 2020/1784. Mr. {{PERSON:Vandenbroucke}} is bereikbaar op {{PHONE:0475 12 84 56}} of {{EMAIL:e.vandenbroucke@advocaat-vdb.be}}.

Aldus uitgesproken door {{PERSON:Hilde Peeters}}, rechter, bijgestaan door griffier {{PERSON:Koen Wauters}}.""",
keep=["ONDERNEMINGSRECHTBANK ANTWERPEN", "A/26/04417", "2000 Antwerpen, Amerikalei 98", "ATLAS TEKSTİL SANAYİ VE TİCARET A.Ş.", "Verordening (EU) 2020/1784", "nr. 2026/118"]),

dict(id="ho-03", case="H-EU-03", doc_type="email_thread", lang="en", title="Irish client e-mail thread re Istanbul apartment",
text="""From: {{PERSON:Aoife Ní Bhriain}} <{{EMAIL:aoife.nibhriain@eircom.net}}>
To: Av. {{PERSON:Zeynep Arslan}}
Subject: RE: Kadıköy apartment – documents

Hi {{PERSON:Zeynep}},

Thanks for the call. As requested, my PPS number is {{NATIONAL_ID:6382915QA}} and my passport is {{PASSPORT:PX4419072}} (renewed last May). My brother {{PERSON:Cathal}} will sign as second heir – he is in Galway and his number is {{PHONE:087 412 9930}}.

Our late mother's last address was:
{{ADDRESS:Apt 14, Dartry Hall}}
{{ADDRESS:Orwell Road}}
{{ADDRESS:Rathgar, Dublin 6}}
{{ADDRESS:D06 W2K7}}

She was born on {{BIRTH_DATE:the 4th of February 1951}}. The death cert from the GRO Roscommon is attached.

Kind regards,
{{PERSON:Aoife}}

--
{{PERSON:Aoife Ní Bhriain}} | Senior Analyst
Fennor Capital DAC, 2 Grand Canal Square, Dublin 2
M: {{PHONE:+353 86 207 5531}}

-----Original Message-----
From: Av. {{PERSON:Zeynep Arslan}} <{{EMAIL:zarslan@arslanhukuk.com.tr}}>

Dear Ms {{PERSON:Ní Bhriain}}, could you please send the PPS number and passport details for you and Mr {{PERSON:Ó Murchú}}? Regards, {{PERSON:Zeynep}}""",
keep=["Fennor Capital DAC, 2 Grand Canal Square, Dublin 2", "GRO Roscommon", "Kadıköy apartment – documents"]),

dict(id="ho-04", case="H-EU-04", doc_type="tenancy_agreement", lang="en", title="Assured shorthold tenancy London",
text="""ASSURED SHORTHOLD TENANCY AGREEMENT
(Housing Act 1988, Part I, Chapter II)

Landlord: {{PERSON:Hugh MacAllister}} of {{ADDRESS:27 Lauderdale Mansions}}, {{ADDRESS:Lauderdale Road, London W9 1LX}}
Agent: Northgate Lettings Ltd, 118 Kilburn High Road, London NW6 4HY (Company No. 07731842)

Tenants:
1. {{PERSON:Deniz Yalçın O'Rourke}}, date of birth {{BIRTH_DATE:09/12/1990}}, passport {{PASSPORT:@uk_pass}}
2. {{PERSON:Imogen Hartley-Price}}, DOB {{BIRTH_DATE:1 Aug 1992}}, NI No. {{NATIONAL_ID:JK 48 21 93 B}}

Property: {{ADDRESS:Flat 3, 41 Elgin Avenue}}, {{ADDRESS:London W9 2NR}}

Term: 12 months from 1 December 2026. Rent: £2,350 per calendar month, payable to the Landlord's account (IBAN {{IBAN:GB58NWBK20417763018827}}).
Deposit: £2,700, protected with the Deposit Protection Service within 30 days.

The Tenants are jointly and severally liable. Ms {{PERSON:Hartley-Price}} shall be the lead tenant for correspondence: {{EMAIL:imogen.hp@outlook.com}}, {{PHONE:07700 900418}}.

Guarantor: {{PERSON:Aylin Yalçın}}, {{ADDRESS:Bağdat Caddesi No: 214 D: 9}}, {{ADDRESS:34728 Kadıköy/İstanbul}}.

Signed by {{PERSON:MacAllister}} and by {{PERSON:Deniz}} and {{PERSON:Imogen}} on 18 November 2026.""",
keep=["Housing Act 1988", "Northgate Lettings Ltd, 118 Kilburn High Road, London NW6 4HY", "Company No. 07731842", "Deposit Protection Service"]),

dict(id="ho-05", case="H-EU-05", doc_type="chat_export", lang="nl", title="WhatsApp export huurgeschil Rotterdam",
text="""[03-11-2026 21:14] {{PERSON:Sanne}}: hoi {{PERSON:Emre}}, de advocaat in Istanbul wil mijn BSN en een kopie paspoort
[03-11-2026 21:15] {{PERSON:Emre}}: ok stuur maar hier, ik zet het door naar Av. {{PERSON:Kocabaş}}
[03-11-2026 21:17] {{PERSON:Sanne}}: BSN {{NATIONAL_ID:@bsn}}, paspoort {{PASSPORT:@nl_pass}} geldig tot 2031
[03-11-2026 21:17] {{PERSON:Sanne}}: en mijn adres is nu {{ADDRESS:Schiedamseweg 213b}}, {{ADDRESS:3026 AL Rotterdam}}
[03-11-2026 21:19] {{PERSON:Emre}}: geboortedatum?
[03-11-2026 21:20] {{PERSON:Sanne}}: {{BIRTH_DATE:28-3-88}}
[03-11-2026 21:22] {{PERSON:Emre}}: top. {{PERSON:Daan van der Wiel}} belt je morgen, dat is mijn compagnon, zijn nummer {{PHONE:06-41827730}}
[03-11-2026 21:25] {{PERSON:Sanne}}: mag het ook via mail? {{EMAIL:sanne.bouwmeester88@gmail.com}}
[03-11-2026 21:26] {{PERSON:Emre}}: prima, en de verhuurder heet toch {{PERSON:Van Leeuwen}}?
[03-11-2026 21:27] {{PERSON:Sanne}}: ja, {{PERSON:Gerard van Leeuwen}}, woont zelf op {{ADDRESS:Mathenesserlaan 402 A}}
[04-11-2026 08:02] {{PERSON:Daan}}: Goedemorgen {{PERSON:Sanne}}, ik heb de stukken. Huur ging naar {{IBAN:@iban_nl}} toch?
[04-11-2026 08:10] {{PERSON:Sanne}}: ja klopt, op naam van mij en {{PERSON:Joost}}""",
keep=["[03-11-2026 21:14]", "[04-11-2026 08:02]", "geldig tot 2031"]),

dict(id="ho-06", case="H-EU-06", doc_type="employment_letter", lang="de", title="Kündigungsschreiben Arbeitnehmer Köln",
text="""Rheinwerk Logistik GmbH · Industriestraße 40 · 50735 Köln
Amtsgericht Köln HRB 88412

Herrn
{{PERSON:Kemal Öztürk-Lindner}}
{{ADDRESS:Neusser Straße 271a}}
{{ADDRESS:50733 Köln}}

Köln, 30. September 2026

Ordentliche Kündigung des Arbeitsverhältnisses
Personalnummer 004417

Sehr geehrter Herr {{PERSON:Öztürk-Lindner}},

hiermit kündigen wir das mit Ihnen bestehende Arbeitsverhältnis ordentlich und fristgerecht gemäß § 622 Abs. 2 BGB zum 31. Dezember 2026. Der Betriebsrat wurde gemäß § 102 BetrVG angehört.

Ihre Lohnsteuerbescheinigung wird unter der Steuer-ID {{NATIONAL_ID:@steuer}} an das Finanzamt übermittelt. Die Abfindung gemäß Sozialplan wird auf Ihr Konto {{IBAN:@iban_de}} überwiesen. Ihre Sozialversicherungsnummer {{NATIONAL_ID:65 120584 Ö 017}} bleibt unverändert.

Für Rückfragen steht Ihnen Frau {{PERSON:von Ahlefeldt}} aus der Personalabteilung zur Verfügung ({{PHONE:0221 9745 1183}}, {{EMAIL:j.vonahlefeldt@rheinwerk-logistik.de}}).

Mit freundlichen Grüßen

{{PERSON:Johanna von Ahlefeldt}}          {{PERSON:Ralf Steinbrück}}
Leiterin Personal                 Geschäftsführer

Empfang bestätigt: ____________ ({{PERSON:K. Öztürk-Lindner}}), Ausweis-Nr. {{ID_DOCUMENT:@perso}}""",
keep=["Rheinwerk Logistik GmbH · Industriestraße 40 · 50735 Köln", "Amtsgericht Köln HRB 88412", "§ 622 Abs. 2 BGB", "§ 102 BetrVG", "Personalnummer 004417"]),

dict(id="ho-07", case="H-EU-07", doc_type="medical_certificate", lang="fr", title="Certificat médical initial accident du travail Lyon",
text="""CERTIFICAT MÉDICAL INITIAL – ACCIDENT DU TRAVAIL
Cerfa n° 11138*06

Victime : {{PERSON:Hakan Durmaz}}
N° d'immatriculation : {{NATIONAL_ID:@nir}}
Né le {{BIRTH_DATE:14 juillet 1986}}
Adresse : {{ADDRESS:27 bis, rue des Tanneurs}}, {{ADDRESS:69007 Lyon}}
Employeur : SAS Bâtiments Rhodaniens, 5 quai Perrache, 69002 Lyon, SIRET 512 847 330 00021

Date de l'accident : 2 octobre 2026

Je soussigné, Dr {{PERSON:Claire Fontaine-Morel}}, certifie avoir examiné ce jour M. {{PERSON:Durmaz}} et constaté : {{HEALTH:fracture ouverte du tiers distal du tibia gauche avec plaie contuse de 6 cm}}, ainsi qu'{{HEALTH:un traumatisme crânien sans perte de connaissance}}. Antécédents : {{HEALTH:diabète de type 2 sous metformine}}.

Arrêt de travail jusqu'au 15 décembre 2026. Sorties non autorisées.

Fait à Lyon, le 2 octobre 2026
Dr {{PERSON:C. Fontaine-Morel}}, RPPS 10101847362
Hôpital Édouard Herriot, service des urgences

Copie remise à l'intéressé et à son conseil, Me {{PERSON:Lucas Ferrand}} ({{PHONE:06 12 48 77 30}}).""",
keep=["Cerfa n° 11138*06", "SAS Bâtiments Rhodaniens, 5 quai Perrache, 69002 Lyon", "SIRET 512 847 330 00021", "RPPS 10101847362", "Hôpital Édouard Herriot"]),

dict(id="ho-08", case="H-EU-08", doc_type="power_of_attorney", lang="it", title="Procura speciale notarile Milano",
text="""PROCURA SPECIALE
Repertorio n. 31.874 – Raccolta n. 12.009

L'anno duemilaventisei, il giorno venti del mese di ottobre, in Milano, nel mio studio in Corso di Porta Romana 61, avanti a me dott. {{PERSON:Alessandro Lo Presti}}, Notaio in Milano, iscritto nel Collegio Notarile di Milano, è presente:

{{PERSON:Giulia Maria Esposito}}, nata a Napoli il {{BIRTH_DATE:5 maggio 1977}}, residente in {{ADDRESS:Via dei Mille 14/2}}, {{ADDRESS:20129 Milano}}, codice fiscale {{NATIONAL_ID:@cf}}, identificata mediante carta d'identità n. {{ID_DOCUMENT:@it_ci}}.

Detta comparente nomina e costituisce suo procuratore speciale l'Avv. {{PERSON:Burak Şahin}}, del Foro di Izmir, affinché in suo nome e conto la rappresenti davanti all'Izmir 3. Asliye Ticaret Mahkemesi nella causa contro {{PERSON:Riccardo De Luca}} e la società Egeo Marmi S.r.l.

La signora {{PERSON:Esposito}} dichiara di essere coniugata in regime di separazione dei beni con {{PERSON:Tommaso D'Amico}}. Eventuali somme dovranno essere accreditate su {{IBAN:@iban_it}}.

Recapiti della comparente: {{PHONE:347 218 9043}}, {{EMAIL:giulia.esposito77@libero.it}}.

Letto, confermato e sottoscritto.
F.to {{PERSON:Giulia Maria Esposito}} – {{PERSON:Alessandro Lo Presti}} Notaio""",
keep=["Repertorio n. 31.874", "Corso di Porta Romana 61", "Collegio Notarile di Milano", "Izmir 3. Asliye Ticaret Mahkemesi", "Egeo Marmi S.r.l."]),

dict(id="ho-09", case="H-EU-09", doc_type="kyc_form", lang="es", title="Formulario KYC cliente residente Madrid",
text="""FICHA DE IDENTIFICACIÓN DEL CLIENTE (Ley 10/2010 de prevención del blanqueo de capitales)
Ref. expediente: KYC-2026-0937

Nombre y apellidos: {{PERSON:María del Carmen Ruiz de Alarcón}}
NIE / DNI: {{NATIONAL_ID:@nie}}
Fecha de nacimiento: {{BIRTH_DATE:30/01/1969}}
Nacionalidad: colombiana (residente en España)
Domicilio: {{ADDRESS:Calle de Toledo 27, 3º B}}
{{ADDRESS:28005 Madrid}}
Teléfono: {{PHONE:612 48 39 07}}
Correo electrónico: {{EMAIL:mcarmen.ruizalarcon@telefonica.net}}
Pasaporte: {{PASSPORT:AV718203}}

Cuenta de origen de fondos: {{IBAN:ES6621000418401234567891}} (CaixaBank)
Titular real de Inversiones Lavapiés 2019 S.L.: la propia clienta (100 %).

Persona con responsabilidad pública (PEP): No. Familiar: su cuñado {{PERSON:Jorge Ruiz}} fue concejal en Getafe hasta 2019.

Objeto del encargo: compra de un local comercial en Beyoğlu, Estambul, a través del despacho Av. {{PERSON:Elif Tunç}}.

Comprobado por: {{PERSON:Sergio Navarro Gil}}, 12/11/2026
Firma de la clienta: {{PERSON:M. C. Ruiz de Alarcón}}""",
keep=["Ley 10/2010", "KYC-2026-0937", "Inversiones Lavapiés 2019 S.L.", "CaixaBank"]),

dict(id="ho-10", case="H-EU-10", doc_type="police_report", lang="pl", title="Notatka policyjna kradzież Gdańsk",
text="""KOMENDA MIEJSKA POLICJI W GDAŃSKU
Komisariat Policji Gdańsk-Śródmieście
Sygn. RSD-1442/26

PROTOKÓŁ PRZYJĘCIA ZAWIADOMIENIA O PRZESTĘPSTWIE

Zawiadamiający: {{PERSON:Tomasz Wiśniewski-Kaya}}
PESEL: {{NATIONAL_ID:@pesel}}
Data urodzenia: {{BIRTH_DATE:1985-04-19}}
Adres zamieszkania: {{ADDRESS:ul. Długa 14 m. 2}}, {{ADDRESS:80-827 Gdańsk}}
Dowód osobisty: seria i nr {{ID_DOCUMENT:CBM 418273}}
Tel.: {{PHONE:512 384 907}}

Zawiadamiający oświadcza, że w dniu 7 listopada 2026 r. z samochodu zaparkowanego przy ul. Ogarnej skradziono teczkę z dokumentami spółki Bałtyk-Anadolu Sp. z o.o., w tym umowę z kontrahentem tureckim reprezentowanym przez {{PERSON:Cem Akdağ}}. Podejrzewa byłego pracownika, {{PERSON:Łukasza Nowaka}}, zam. {{ADDRESS:ul. Wajdeloty 9/4}}, {{ADDRESS:80-437 Gdańsk}}. Świadkiem zdarzenia była sąsiadka, pani {{PERSON:Halina}}.

Pouczono o odpowiedzialności karnej z art. 233 § 1 Kodeksu karnego.

Przyjął: sierż. sztab. {{PERSON:Marek Zieliński}}
Podpis zawiadamiającego: {{PERSON:T. Wiśniewski-Kaya}}""",
keep=["KOMENDA MIEJSKA POLICJI W GDAŃSKU", "Sygn. RSD-1442/26", "Bałtyk-Anadolu Sp. z o.o.", "art. 233 § 1 Kodeksu karnego"]),

dict(id="ho-11", case="H-EU-11", doc_type="invoice", lang="da", title="Faktura advokatydelser København",
text="""FAKTURA nr. 2026-1187
Holm & Bech Advokatpartnerselskab
Bredgade 30, 1260 København K – CVR 38 41 77 21

Kunde:
{{PERSON:Mette Kjærsgaard Nielsen}}
{{ADDRESS:Nørrebrogade 44, 2. th.}}
{{ADDRESS:2200 København N}}
CPR-nr.: {{NATIONAL_ID:120384-1137}}

Sag: Arv efter {{PERSON:Ole Kjærsgaard}} – ejendom i Bodrum (koordinering med Av. {{PERSON:Seda Erkan}}, Muğla)

Ydelser i perioden 1.–31. oktober 2026:
- Møde med {{PERSON:Mette}} og hendes bror {{PERSON:Rasmus Kjærsgaard}} (2,0 t)
- Gennemgang af tyrkisk skifteretsattest (1,5 t)
- Korrespondance med {{PERSON:Erkan}} (0,75 t)

Honorar i alt ekskl. moms: DKK 13.500,00
Moms 25 %: DKK 3.375,00
I alt: DKK 16.875,00

Betaling til konto {{IBAN:DK3730004812937465}} senest 30.11.2026.

Spørgsmål: advokat {{PERSON:Søren Holm}}, {{PHONE:28 41 77 30}}, {{EMAIL:sh@holmbech.dk}}""",
keep=["FAKTURA nr. 2026-1187", "Holm & Bech Advokatpartnerselskab", "Bredgade 30, 1260 København K", "CVR 38 41 77 21", "DKK 16.875,00"]),

dict(id="ho-12", case="H-EU-12", doc_type="cv", lang="sv", title="CV svensk ingenjör för arbetstillstånd",
text="""CURRICULUM VITAE

{{PERSON:Linnea Åkesson Berg}}
{{ADDRESS:Götgatan 31 lgh 1102}}
{{ADDRESS:116 21 Stockholm}}
Mobil: {{PHONE:070-482 19 33}}
E-post: {{EMAIL:linnea.akesson.berg@gmail.com}}
Personnummer: {{NATIONAL_ID:19880412-3354}}
Född: {{BIRTH_DATE:12 april 1988}}

ARBETSLIVSERFARENHET
2021–nu   Projektledare, Vattenfall AB, Solna
2016–2021 Konstruktör, Skanska Sverige AB, Göteborg

UTBILDNING
2011–2016 Civilingenjör, Väg- och vattenbyggnad, Chalmers tekniska högskola

SPRÅK
Svenska (modersmål), engelska (flytande), turkiska (grundläggande)

ÖVRIGT
Söker arbetstillstånd i Turkiet för uppdrag hos Ege Enerji A.Ş. i Izmir. Pass nr {{PASSPORT:AB1293847}}.

REFERENSER
{{PERSON:Johan af Klinteberg}}, sektionschef, Vattenfall – {{PHONE:08-612 47 93}}
{{PERSON:Gunilla Ek}}, f.d. chef, Skanska – {{EMAIL:gunilla.ek@telia.com}}""",
keep=["Vattenfall AB, Solna", "Skanska Sverige AB", "Chalmers tekniska högskola", "Ege Enerji A.Ş."]),

dict(id="ho-13", case="H-EU-13", doc_type="sworn_translation_apostille", lang="tr", title="Alman doğum belgesinin yeminli tercümesi ve apostil",
text="""YEMİNLİ TERCÜME – Almanca aslından Türkçeye

DOĞUM KAYDI (Geburtsurkunde)
Standesamt München, Kayıt No. G 2417/1996

Çocuğun adı soyadı: {{PERSON:Lena Sophie Aydın}}
Doğum tarihi: {{BIRTH_DATE:23 Ağustos 1996}}
Doğum yeri: München
Annesi: {{PERSON:Katharina Aydın}}, doğum soyadı {{PERSON:Hofbauer}}
Babası: {{PERSON:Murat Aydın}}
İkametgâh: {{ADDRESS:Schleißheimer Straße 118, Rückgebäude}}, {{ADDRESS:80797 München}}

-----
APOSTILLE (Convention de La Haye du 5 octobre 1961)
1. Ülke: Federal Almanya Cumhuriyeti
2. İmzalayan: {{PERSON:Brigitte Wendlandt}}
4. Mühür: Standesamt München
6. Tarih: 02.09.2026
8. No: 26-R-04418

-----
Tercüman şerhi: Almancadan Türkçeye tam ve doğru olarak tercüme eden yeminli tercüman {{PERSON:Gökhan Erdem}}, T.C. Kimlik No {{TCKN:@tckn}}, Beyoğlu 14. Noterliği'nin 12.03.2024 tarih ve 08817 yevmiye sayılı yemin zaptı ile. Tel: {{PHONE:0532 418 77 21}}.

Tercümenin tercümana aidiyeti onaylanır. Beyoğlu 14. Noterliği, 05.09.2026, Yevmiye No 21734.""",
keep=["Standesamt München", "Kayıt No. G 2417/1996", "26-R-04418", "Beyoğlu 14. Noterliği", "Yevmiye No 21734", "Convention de La Haye du 5 octobre 1961"]),

dict(id="ho-14", case="H-EU-14", doc_type="petition", lang="tr", title="İş kazası tazminat dava dilekçesi Hollandalı işçi",
text="""İSTANBUL ANADOLU ( ) İŞ MAHKEMESİ'NE

DAVACI     : {{PERSON:Thijs van den Bosch}}, Hollanda vatandaşı, pasaport no: {{PASSPORT:@nl_pass}}, yabancı kimlik no {{NATIONAL_ID:99418273650}}
ADRESİ     : {{ADDRESS:Caferağa Mah. Moda Cad. No: 41/3}} {{ADDRESS:Kadıköy/İstanbul}}
VEKİLİ     : Av. {{PERSON:Ece Bayraktar}}, İstanbul Barosu
DAVALI     : Marmara Lojistik ve Depolama A.Ş., Tuzla OSB 3. Cad. No:12 Tuzla/İstanbul
KONU       : İş kazası nedeniyle maddi ve manevi tazminat talebimizdir.

AÇIKLAMALAR:
1. Müvekkil {{PERSON:van den Bosch}}, {{BIRTH_DATE:11.05.1993}} doğumlu olup davalı şirkette forklift operatörü olarak çalışmaktadır.
2. 14.06.2026 tarihinde depoda devrilen raf sistemi altında kalan müvekkilde {{HEALTH:L1 vertebra kompresyon kırığı}} ve {{HEALTH:sağ el 4. ve 5. parmakta kalıcı fonksiyon kaybı}} oluşmuştur. Maltepe Üniversitesi Hastanesi raporunda {{HEALTH:%32 sürekli iş göremezlik}} tespit edilmiştir.
3. Kaza anını iş arkadaşı {{PERSON:Serkan Uysal}} ile vardiya amiri {{PERSON:Jeroen}} görmüştür; {{PERSON:Thijs}} olay yerinden ambulansla kaldırılmıştır.

DELİLLER: SGK iş kazası bildirgesi, 5510 sayılı Kanun md. 13, tanık beyanları, bilirkişi incelemesi.

Davacı Vekili
Av. {{PERSON:Ece Bayraktar}}""",
keep=["İSTANBUL ANADOLU ( ) İŞ MAHKEMESİ'NE", "Marmara Lojistik ve Depolama A.Ş., Tuzla OSB 3. Cad. No:12 Tuzla/İstanbul", "5510 sayılı Kanun md. 13", "Maltepe Üniversitesi Hastanesi", "İstanbul Barosu"]),

dict(id="ho-15", case="H-EU-15", doc_type="client_onboarding", lang="tr", title="Müvekkil kabul formu Belçikalı yatırımcı",
text="""MÜVEKKİL KABUL VE TANIMA FORMU
Dosya No: 2026/MK-311

Müvekkil adı soyadı : {{PERSON:Amélie Dubois-Lefèvre}}
Uyruğu              : Belçika
Doğum tarihi        : {{BIRTH_DATE:7 Ocak 1975}}
Ulusal sicil no     : {{NATIONAL_ID:75.01.07-284.12}}
Kimlik kartı no     : {{ID_DOCUMENT:592-1847362-18}}
Vergi no (TR)       : {{NATIONAL_ID:9930418275}}
Adres               : {{ADDRESS:Rue de la Victoire 152 b 3}}
                      {{ADDRESS:1060 Saint-Gilles, Bruxelles}}
Türkiye adresi      : {{ADDRESS:Kalkan Mah. Şehitler Cad. No: 8/B}}, {{ADDRESS:Kaş/Antalya}}
Telefon             : {{PHONE:+32 476 39 20 81}}
E-posta             : {{EMAIL:amelie.dubois.lefevre@skynet.be}}
Banka hesabı        : {{IBAN:@iban_fr}}

İş konusu: Kaş'taki villanın satın alınması, 6306 sayılı Kanun kapsamında risk tespiti.

Görüşmeye eşi {{PERSON:Laurent Lefèvre}} de katılmıştır. Müvekkil, Fransızca konuşmakta olup tercümanlığı {{PERSON:Nur Kılıç}} yapmıştır. MASAK 5549 sayılı Kanun uyarınca kimlik tespiti yapılmıştır.

Formu dolduran: Av. {{PERSON:Hasan Tekin}}
Kontrol: Av. {{PERSON:Tekin}} / Stj. Av. {{PERSON:Dilara}}""",
keep=["Dosya No: 2026/MK-311", "6306 sayılı Kanun", "MASAK 5549 sayılı Kanun"]),

dict(id="ho-16", case="H-EU-16", doc_type="shareholder_register", lang="de", title="Gesellschafterliste GmbH Hamburg",
text="""Liste der Gesellschafter
der Elbmarsch Handelsgesellschaft mbH mit Sitz in Hamburg
Amtsgericht Hamburg, HRB 172044
(§ 40 GmbHG)

Lfd. Nr. | Gesellschafter | Geburtsdatum | Wohnort | Geschäftsanteile Nr. | Nennbetrag | Beteiligung
1 | {{PERSON:Friedrich von Bülow}} | {{BIRTH_DATE:14.02.1958}} | Hamburg | 1–12.500 | 12.500 € | 50 %
2 | {{PERSON:Ayşegül Demirtaş-Hansen}} | {{BIRTH_DATE:29.10.1981}} | Pinneberg | 12.501–18.750 | 6.250 € | 25 %
3 | Dr. {{PERSON:Henrik ter Horst}} | {{BIRTH_DATE:03.06.1970}} | Groningen (NL) | 18.751–22.500 | 3.750 € | 15 %
4 | Bosporus Holding A.Ş., Istanbul (Ticaret Sicil No. 845512) | – | – | 22.501–25.000 | 2.500 € | 10 %

Veränderungen: Die Geschäftsanteile Nr. 18.751–22.500 wurden mit Urkunde vom 2. Juli 2026 (UR-Nr. 1418/2026) von {{PERSON:Magdalena Wójcik}} auf {{PERSON:ter Horst}} übertragen.

Hamburg, den 9. Juli 2026

{{PERSON:Friedrich von Bülow}}, Geschäftsführer

Bescheinigung des Notars {{PERSON:Carsten Petersen}}, Hamburg, gemäß § 40 Abs. 2 GmbHG.""",
keep=["Elbmarsch Handelsgesellschaft mbH", "Amtsgericht Hamburg, HRB 172044", "§ 40 GmbHG", "Bosporus Holding A.Ş., Istanbul (Ticaret Sicil No. 845512)", "UR-Nr. 1418/2026"]),

dict(id="ho-17", case="H-EU-17", doc_type="bank_letter", lang="en", title="Dutch bank confirmation letter for Turkish property purchase",
text="""Noordhaven Bank N.V.
Coolsingel 104, 3011 AG Rotterdam
Chamber of Commerce 24301776

To whom it may concern / İlgili makama

Amsterdam, 12 November 2026
Our reference: NB/KYC/2026/55871

BANK CONFIRMATION

We hereby confirm that {{PERSON:Willemijn de Groot-Çelik}}, born {{BIRTH_DATE:2 September 1983}}, residing at
{{ADDRESS:Javakade 7-II}}
{{ADDRESS:1019 BH Amsterdam}}
The Netherlands
holds a current account with our bank under IBAN {{IBAN:@iban_nl}} since 2009, jointly with {{PERSON:Burak Çelik}}.

The account holders have been identified in accordance with the Wwft on the basis of passport {{PASSPORT:@nl_pass}} (Mrs {{PERSON:de Groot-Çelik}}) and Dutch identity card {{ID_DOCUMENT:IXR8F4LK2}} (Mr {{PERSON:Çelik}}). BSN on file: {{NATIONAL_ID:@bsn}}.

The funds of EUR 285,000.00 transferred on 4 November 2026 to the account of Av. {{PERSON:Cansu Öz}} at Türkiye İş Bankası ({{IBAN:@iban_tr}}) originate from the sale of the property at {{ADDRESS:Van Woustraat 186-3}}, {{ADDRESS:1073 LZ Amsterdam}}.

Yours faithfully,

{{PERSON:R. Mulder}}                {{PERSON:Femke Verhoeven}}
Relationship Manager       Compliance Officer
{{PHONE:020 794 31 88}}""",
keep=["Noordhaven Bank N.V.", "Coolsingel 104, 3011 AG Rotterdam", "NB/KYC/2026/55871", "Chamber of Commerce 24301776", "Türkiye İş Bankası"]),

dict(id="ho-18", case="H-EU-18", doc_type="insurance_claim", lang="es", title="Parte amistoso de accidente Málaga conductor turco",
text="""DECLARACIÓN AMISTOSA DE ACCIDENTE / PARTE DE SINIESTRO
Aseguradora: Mutua Costa del Sol, Póliza n.º AU-4418290-07
N.º de siniestro: 26/MLG/018834

Fecha y lugar: 21/08/2026, 17:40 h, Avenida de Andalucía, Málaga

VEHÍCULO A
Conductor: {{PERSON:Volkan Erdoğan}}
Fecha de nacimiento: {{BIRTH_DATE:02-11-1979}}
Permiso de conducir n.º: {{ID_DOCUMENT:TR-B 418273}} (Turquía)
Domicilio: {{ADDRESS:Atatürk Bulvarı No: 112 Daire 6}}, {{ADDRESS:06680 Çankaya/Ankara}}
Teléfono: {{PHONE:+90 532 744 18 09}}
Matrícula: 4182 LMN (vehículo de alquiler, Sol Rent a Car S.L.)

VEHÍCULO B
Conductora: {{PERSON:Lucía Fernández-Ortega}}
DNI: {{NATIONAL_ID:48291736H}}
Domicilio: {{ADDRESS:C/ Larios 6, 2º izq.}}, {{ADDRESS:29005 Málaga}}
Teléfono: {{PHONE:655 21 90 34}}
Pasajera herida: {{PERSON:Carmen Ortega}}, con {{HEALTH:esguince cervical (latigazo) y contusión torácica}}, atendida en el Hospital Regional de Málaga.

Observaciones: El conductor A ({{PERSON:Erdoğan}}) declara que el semáforo estaba en ámbar. Testigo: {{PERSON:Pablo}}, camarero del bar contiguo ({{PHONE:622 08 41 77}}).

Firma A: {{PERSON:V. Erdoğan}}     Firma B: {{PERSON:L. Fernández}}""",
keep=["Mutua Costa del Sol", "Póliza n.º AU-4418290-07", "26/MLG/018834", "Sol Rent a Car S.L.", "Hospital Regional de Málaga", "4182 LMN"]),

dict(id="ho-19", case="H-EU-19", doc_type="board_minutes", lang="en", title="Board minutes UK subsidiary Turkish JV",
text="""ANATOLIA BRIDGE PARTNERS LIMITED (Company No. 11847302)
Registered office: 3 More London Riverside, London SE1 2RE

MINUTES of a meeting of the Board of Directors held by video conference on 6 November 2026 at 10:00

Present: {{PERSON:Fiona MacLeod}} (Chair), {{PERSON:Seamus O'Driscoll}}, {{PERSON:Ahmet Gündoğdu}}, {{PERSON:Priya Raman-Whitfield}}
In attendance: {{PERSON:Tom}} (company secretary), Av. {{PERSON:Berk Ünal}} (Turkish counsel)
Apologies: {{PERSON:Gráinne McNamara}}

1. Quorum. The Chair noted that a quorum was present.

2. Directors' interests. Mr {{PERSON:O'Driscoll}} declared an interest under s.177 Companies Act 2006 as his wife, {{PERSON:Niamh}}, is a shareholder in Kuzey Yapı A.Ş.

3. Turkish JV. Mr {{PERSON:Ünal}} reported on the Ankara 7. Asliye Ticaret Mahkemesi proceedings. {{PERSON:Ahmet}} to circulate the share purchase agreement. {{PERSON:Priya}} noted that the guarantor, Mr {{PERSON:Kerem Aksoy}} of {{ADDRESS:14 Elm Park Gardens, London SW10 9NY}}, has not yet produced his passport; his mobile is {{PHONE:07700 900771}}.

4. Bank mandate. Resolved to add {{PERSON:Fiona}} and {{PERSON:Seamus}} as signatories.

There being no further business, the meeting closed at 11:05.

.................................
{{PERSON:Fiona MacLeod}}, Chair""",
keep=["ANATOLIA BRIDGE PARTNERS LIMITED", "Company No. 11847302", "3 More London Riverside, London SE1 2RE", "s.177 Companies Act 2006", "Kuzey Yapı A.Ş.", "Ankara 7. Asliye Ticaret Mahkemesi"]),

dict(id="ho-20", case="H-EU-20", doc_type="chat_export", lang="tr", title="Signal yazışması Alman müvekkil ile",
text="""Signal sohbet dökümü – Av. {{PERSON:Selim Korkmaz}} / {{PERSON:Jonas Becker}}

12.11.26, 09:41 - {{PERSON:Jonas}}: Guten Morgen Herr {{PERSON:Korkmaz}}, hier wie besprochen meine Daten
12.11.26, 09:42 - {{PERSON:Jonas}}: {{PERSON:Jonas Maximilian Becker}}, geb. {{BIRTH_DATE:07.04.1974}} in Freiburg
12.11.26, 09:42 - {{PERSON:Jonas}}: Perso-Nr {{ID_DOCUMENT:@perso}}, Steuer-ID {{NATIONAL_ID:@steuer}}
12.11.26, 09:43 - {{PERSON:Jonas}}: Wohnung: {{ADDRESS:Wiehre, Günterstalstraße 58, 2. OG links}}, {{ADDRESS:79102 Freiburg im Breisgau}}
12.11.26, 09:50 - {{PERSON:Selim Korkmaz}}: Teşekkürler / Danke. Und Ihre Frau?
12.11.26, 09:53 - {{PERSON:Jonas}}: {{PERSON:Ulrike}} ist im Krankenhaus, {{HEALTH:Chemotherapie wegen Brustkrebs}}, sie kann nicht nach Antalya reisen
12.11.26, 09:54 - {{PERSON:Jonas}}: Ihr Bruder {{PERSON:Matthias Graf von der Schulenburg}} kann die Vollmacht unterschreiben
12.11.26, 10:02 - {{PERSON:Selim Korkmaz}}: Anladım. Kira bedeli için hesap?
12.11.26, 10:05 - {{PERSON:Jonas}}: {{IBAN:@iban_de}}, Sparkasse Freiburg-Nördlicher Breisgau
12.11.26, 10:06 - {{PERSON:Jonas}}: Handy {{PHONE:0171 4482910}}, Mail {{EMAIL:jm.becker@posteo.de}}
12.11.26, 10:10 - {{PERSON:Selim Korkmaz}}: Antalya 2. Sulh Hukuk Mahkemesi 2026/1182 E. dosyası için yeterli. {{PERSON:Becker}} Bey, tapu randevusu 25.11.2026.""",
keep=["Sparkasse Freiburg-Nördlicher Breisgau", "Antalya 2. Sulh Hukuk Mahkemesi", "2026/1182 E."]),
]


if __name__ == "__main__":
    B.R.seed(7301)
    out = Path(__file__).resolve().parent / "data" / "eu_heldout.jsonl"
    out.write_text("".join(json.dumps(B.render(d), ensure_ascii=False) + "\n" for d in DOCS), encoding="utf-8")
    print(out, len(DOCS))
