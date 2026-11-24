# Katip sample pack: realistic cases for the newest features

A catalogue of cases a Turkish law firm actually meets, built to be **scored now, fixed later, and shown to
lawyers**. It covers the three features shipped in Kalkan 0.5.x: EU/GDPR masking (`eu` profile), DD screening
(MASAK lists, Gazette and ilan.gov.tr notices) and Katip Uyum (GDPR/KVKK/AI Act pack). Every case says who meets
it, what it is modelled on, what Katip must do, and what it did on 24 Nov 2026.

```bash
python lab/samples/build_eu_docs.py               # rebuild data/eu_docs.jsonl (seeded, same output every time)
python lab/dd/dd.py update                         # DD part needs a local MASAK snapshot (never committed)
KATIP_SDK=0 python lab/samples/run_pack.py        # all parts -> results/pack_results.json
KATIP_SDK=0 python lab/samples/run_pack.py --part eu
```

Rules for this pack: every person, number, address and Turkish company in the documents and notices is invented,
and every ID has a valid checksum so the rules are really tested. The only real names are **public sanctions-list
entries for companies and organisations** (MASAK, UN) and well-known companies used as decoys. No listed
person's name is written to the results. No client document of anyone we know was used.

## Results on 24 Nov 2026 (first run, nothing tuned on these cases)

| Part | Cases | Result | Main gap |
|---|---|---|---|
| EU masking, `eu` profile | 16 documents, 132 values | **87.9%** of values masked [95% CI 81.2–92.4]; 5 of 16 documents fully masked; 65 of 73 must-keep strings kept | UK/Irish/Dutch street addresses (5 of 15 missed), German "geb." birth names, a few unlisted names |
| EU masking, Turkish `ai` profile (for comparison) | same | 42.4% [34.3–51.0]; 0 documents fully masked | a lawyer who forgets to switch profile leaks most EU identifiers |
| DD, listed companies as a lawyer types them | 14 | 9 found at the expected band | short trade names (2 of 6 words), English aliases, "X Foundation" |
| DD, 7262 (WMD) counterparties | 5 | 4 | "Bank Sepah" scores 0.76 because the list row is "BANK SEPAH AND BANK SEPAH INTERNATIONAL" |
| DD, UN organisations in Turkish spelling | 7 | 3 | El-Kaide, Doğu Türkistan İslami Hareketi, Leşker-i Tayyibe, DEAŞ Horasan: not found |
| DD, decoy companies | 8 | 8 no false match | |
| DD, 10 most common Turkish names (reported) | 10 | 1 exact homonym on the domestic list | a name alone cannot settle it; the answer shows the listed birth date so the lawyer can |
| DD, sanctioned elsewhere (EU/US) but not in Turkish lists | 2 | no hit, correct | the answer text does not say that OFAC/EU/UK lists are not covered |
| DD, Gazette / ilan notice texts | 10 queries, 8 notices | 9 | "Kuzey Rüzgarı" (two words) vs "KUZEYRÜZGARI" |
| Uyum, scenarios from real enforcement decisions | 12 | 12 raise the expected finding | expectations were written knowing the rule ids, so this is a coverage check, not a blind score; the right-hand column lists what no questionnaire can see |

The 132 values are few, so one document moves the total by several points. Read the per-case tables, not the
headline.

## Who these cases are for

- **Cross-border property and inheritance lawyer** (Antalya, Muğla, Bursa): German, Dutch, Spanish clients send a
  notarial power of attorney, an Erbschein, a divorce order for recognition (tanıma-tenfiz), an apostille, a sworn
  translation, and WhatsApp messages. Cases S-EU-01 to 06, 12, 14, 16.
- **Corporate / M&A lawyer** doing a share transfer or company set-up for a foreign client: KYC sheets, Italian and
  Polish powers of attorney, DD screening of counterparties. S-EU-07, 09, 13; dd-01 to dd-19.
- **Employment and litigation lawyer** with EU witnesses or a Turkish company's EU subsidiary: S-EU-08, 15.
- **The firm itself as data controller**: an access request from an EU guest, a vendor's breach notice, and the
  GDPR/KVKK pack. S-EU-10, 11; U-01 to U-12.

## 1. EU masking: 16 documents

Written from the public shape of each document type (notarial deed headers with UR-Nr./Repertorio, Dutch
"zaaknummer / rekestnummer" and ECLI, the Hague apostille's ten numbered fields, a Turkish tanıma-tenfiz
petition under MÖHUK m.50, a yeminli tercüman certificate, a WhatsApp export). `keep` strings are the parts a
lawyer needs readable: courts, case and register numbers, statutes, companies, tapu ada/parsel. Data:
`data/eu_docs.jsonl`.

| Case | Document | Lang | Values | `ai` | `eu` | Kept readable (`eu`) | Missed by `eu` |
|---|---|---|---|---|---|---|---|
| S-EU-01 | German notarial power of attorney for a flat purchase in Alanya | de | 11 | 3 | 11 | 7/7 | - |
| S-EU-02 | German certificate of inheritance (Erbschein) for a dual citizen's estate | de | 9 | 2 | 5 | 4/5 | 11.02.1949, Gülizar Kaplanoğlu geb. Sert, Derya Rauschenberger geb. Kaplanoğlu, Overbeck |
| S-EU-03 | Dutch divorce order sent for recognition in Türkiye (tanıma-tenfiz) | nl | 11 | 5 | 10 | 5/5 | Groene Hilledijk 318, 3074 AM Rotterdam |
| S-EU-04 | Turkish recognition petition about the Dutch divorce (foreign names inside Turkish text) | tr | 13 | 10 | 12 | 4/5 | Groene Hilledijk 318, 3074 AM Rotterdam / HOLLANDA |
| S-EU-05 | Apostille on a German court document (Hague Convention 1961 form) | de | 2 | 0 | 2 | 4/4 | - |
| S-EU-06 | Sworn translation of the Erbschein with the translator's certificate | tr | 9 | 8 | 8 | 2/3 | 11.02.1949 |
| S-EU-07 | Italian special power of attorney to set up a Turkish company | it | 8 | 3 | 7 | 5/5 | Giuseppina Lo Faro |
| S-EU-08 | French sworn statement for a Turkish employment claim | fr | 8 | 3 | 8 | 4/4 | - |
| S-EU-09 | KYC sheet for a UK buyer in a Turkish share transfer | en | 11 | 4 | 9 | 6/6 | Flat 4, 27 Pembridge Villas, London W11 3EP, 12 Elm Grove, Harrogate HG1 2JL |
| S-EU-10 | Data-subject access request from an EU resident to a Turkish firm | en | 6 | 1 | 5 | 4/4 | 31 Fairview Strand, Dublin 3, D03 KX88 |
| S-EU-11 | IT vendor's breach notice to the firm (GDPR Art. 33 / KVKK m.12) | en | 5 | 2 | 5 | 6/7 | - |
| S-EU-12 | WhatsApp export: German client, Turkish lawyer, property dispute in Fethiye | mixed | 11 | 5 | 9 | 2/2 | C4R7NK2T9, Rüdiger |
| S-EU-13 | Polish power of attorney for a Turkish debt claim | pl | 6 | 1 | 6 | 4/5 | - |
| S-EU-14 | Spanish notarial power for a Turkish inheritance (NIE holder) | es | 6 | 3 | 5 | 3/4 | Íñigo Arrizabalaga Etxeberria |
| S-EU-15 | German dismissal letter from a Turkish company's subsidiary, with a sick-leave mention | de | 7 | 2 | 6 | 3/4 | Bandscheibenvorfall |
| S-EU-16 | Dutch client e-mail about a holiday-home dispute in Didim | nl | 9 | 4 | 8 | 2/3 | NFG1C9LD8 |

Misses worth fixing first (from `results/pack_results.json`):

1. **Street addresses outside the DE/FR/IT/ES patterns**: "Groene Hilledijk 318, 3074 AM Rotterdam", "Flat 4, 27
   Pembridge Villas, London W11 3EP", "12 Elm Grove, Harrogate HG1 2JL", "31 Fairview Strand, Dublin 3, D03 KX88".
   A postcode rule (NL `1234 AB`, UK outward+inward code, Irish Eircode) would anchor them.
2. **"geb." birth names** in German civil-status documents ("Gülizar Kaplanoğlu geb. Sert"): the part after
   "geb." stays readable. Also the date of birth in "der am 11.02.1949 in Kayseri geborene" (cue after the date).
3. **Passport numbers without the word "passport"**: "Pass Nr." in a German chat line, "paspoortnummer" in Dutch.
4. **Names after a notary or clerk title in other languages**: "Notaio Dott.ssa …", "Ante mí, …, Notario",
   "…, Rechtspflegerin" written before the name.
5. **Over-masking**: "32 VI 518/26" (German court file number) cut to "32 VI 518"; "2026/18831 Esas" and
   "Sulh Hukuk Mahkemesi" partly masked; the firm's own name "Karaağaç Hukuk Bürosu"; a company address
   ("Hafenstraße 9", arguably fine to mask).
6. One health term in German ("Bandscheibenvorfall") was not flagged as Art. 9 data.

## 2. DD screening

Run against the live MASAK snapshot of 24 Nov 2026 (2,311 rows; art. 5 list last changed 11 Nov 2026). Queries
are what a lawyer types: the name as it appears in a contract, an invoice, a SWIFT message, or the press, with
abbreviations expanded or shortened, Turkish letters lost, and Turkish spellings of UN-listed groups. Decoys are
real, unlisted companies and near-miss trade names. Data: `data/dd_cases.json`, `data/notices.json`.

| Case | Group | Query | Expected | Got (score) | OK |
|---|---|---|---|---|---|
| dd-01 | listed_company_as_typed | Alsultan Kuyumculuk Elektronik Gıda İthalat İhracat Limited Şirketi | match | match (1.0) | ✓ |
| dd-02 | listed_company_as_typed | ALSULTAN KUYUMCULUK ELEKTRONIK GIDA ITH. IHR. LTD. STI. | match | match (1.0) | ✓ |
| dd-03 | listed_company_as_typed | Al Sultan Kuyumculuk | review | weak (0.815) | ✗ |
| dd-04 | listed_company_as_typed | Alsultan Kuyumculuk | review | weak (0.84) | ✗ |
| dd-05 | listed_company_as_typed | Alfay İnşaat Turizm Dış Ticaret Sanayi Limited Şirketi | match | match (0.945) | ✓ |
| dd-06 | listed_company_as_typed | Al Fay Company | review | none | ✗ |
| dd-07 | listed_company_as_typed | Arasta İth. İhr. Dış Tic. Ltd. Şti. | match | match (1.0) | ✓ |
| dd-08 | listed_company_as_typed | Endex Nakliyat Kuyumculuk | review | match (0.948) | ✓ |
| dd-09 | listed_company_as_typed | First One International Dış Ticaret Tekstil Sanayi Ltd. Şti. | review | match (0.951) | ✓ |
| dd-10 | listed_company_as_typed | Aslan SK Medikal Sanayi Ticaret Limited Şirketi | match | match (1.0) | ✓ |
| dd-11 | listed_company_as_typed | Al Haram Foreign Exchange | match | match (1.0) | ✓ |
| dd-12 | listed_company_as_typed | Embrace Relief Foundation | review | none | ✗ |
| dd-13 | listed_company_as_typed | Coral Port LLC | match | match (1.0) | ✓ |
| dd-14 | listed_company_as_typed | Mezopotamya Verlag und Vertrieb GmbH | review | weak (0.84) | ✗ |
| dd-15 | wmd_list_counterparty | Bank Sepah | match | weak (0.76) | ✗ |
| dd-16 | wmd_list_counterparty | Atomic Energy Organization of Iran | match | match (0.933) | ✓ |
| dd-17 | wmd_list_counterparty | Office 39 | review | match (1.0) | ✓ |
| dd-18 | wmd_list_counterparty | Bank of East Land | match | match (1.0) | ✓ |
| dd-19 | wmd_list_counterparty | Amin Industrial Complex | match | match (1.0) | ✓ |
| dd-20 | un_org_turkish_spelling | El-Kaide | review | none (0.787) | ✗ |
| dd-21 | un_org_turkish_spelling | Al Qaeda | match | match (1.0) | ✓ |
| dd-22 | un_org_turkish_spelling | Boko Haram | match | match (1.0) | ✓ |
| dd-23 | un_org_turkish_spelling | Doğu Türkistan İslami Hareketi | review | none | ✗ |
| dd-24 | un_org_turkish_spelling | Eastern Turkistan Islamic Movement | match | match (0.948) | ✓ |
| dd-25 | un_org_turkish_spelling | Leşker-i Tayyibe | review | none | ✗ |
| dd-26 | un_org_turkish_spelling | DEAŞ Horasan | review | none | ✗ |
| dd-27 | decoy_company | Türk Hava Yolları Anonim Ortaklığı | none | none | ✓ |
| dd-28 | decoy_company | Koç Holding A.Ş. | none | none | ✓ |
| dd-29 | decoy_company | Arçelik Anonim Şirketi | none | none | ✓ |
| dd-30 | decoy_company | Sultan Kuyumculuk Ltd. Şti. | no_match | weak (0.815) | ✓ |
| dd-31 | decoy_company | Aslan Medikal Sanayi ve Ticaret A.Ş. | no_match | review (0.92) | ✓ |
| dd-32 | decoy_company | Bank of Georgia | none | none | ✓ |
| dd-33 | decoy_company | Atom Enerjisi Mühendislik Ltd. Şti. | no_match | none | ✓ |
| dd-34 | decoy_company | Embrace Logistics GmbH | no_match | none | ✓ |
| dd-35 | common_person_name | Mehmet Yılmaz | report | none | (reported) |
| dd-36 | common_person_name | Ayşe Kaya | report | none | (reported) |
| dd-37 | common_person_name | Mustafa Demir | report | match (1.0) | (reported) |
| dd-38 | common_person_name | Fatma Şahin | report | none | (reported) |
| dd-39 | common_person_name | Ahmet Çelik | report | none | (reported) |
| dd-40 | common_person_name | Emine Yıldız | report | none | (reported) |
| dd-41 | common_person_name | Ali Öztürk | report | none | (reported) |
| dd-42 | common_person_name | Hatice Aydın | report | none | (reported) |
| dd-43 | common_person_name | Hüseyin Özdemir | report | none | (reported) |
| dd-44 | common_person_name | Zeynep Arslan | report | none | (reported) |
| dd-45 | out_of_scope_source | Wagner Group | none | none | ✓ |
| dd-46 | out_of_scope_source | Rosneft Trading S.A. | none | none | ✓ |

### Gazette and ilan.gov.tr notice texts

Eight invented notices in the real formats (registry office header, Sicil/Mersis no., İlan Sıra No; court
konkordato notices under İİK m.285), with the defects of scanned pages: a word split across a column break,
OCR "l" for "İ", missing "Ş", a Turkish case suffix after the name, a change of name, a merger that names two
companies.

| Case | Query | Expected notices | Found | OK |
|---|---|---|---|---|
| nq1 | Kuzeyrüzgarı Tekstil Sanayi ve Ticaret Ltd. Şti. | n1 | n1 | ✓ |
| nq2 | Mavideniz Gıda İthalat İhracat A.Ş. | n2 | n2 | ✓ |
| nq3 | Yeşilova Agro Lojistik | n3 | n3 | ✓ |
| nq4 | Yeşilova Tarım Ürünleri Pazarlama | n3 | n3 | ✓ |
| nq5 | Karadağ Yapı Malzemeleri A.Ş. | n4 | n4 | ✓ |
| nq6 | Çayırova Metal Kalıp | n5, n7 | n5, n7 | ✓ |
| nq7 | Saruhan Bağ ve Şarapçılık | n6 | n6 | ✓ |
| nq8 | Dilovası Pres Döküm Ltd. Şti. | n7 | n7 | ✓ |
| nq9 | Kuzey Rüzgarı Tekstil | n1 | - | ✗ |
| nq10 | Karadağlar Yapı | n8 | n8 | ✓ |

What to fix first:

1. **Turkish names of UN-listed groups**: add the Turkish names lawyers write (El-Kaide, DEAŞ, Doğu Türkistan İslami
   Hareketi, Leşker-i Tayyibe; MASAK's own records use "EL-KAİDE" and "DEAŞ" in the organisation field) as aliases at index time, from a small reviewed table.
2. **List rows holding two entities** ("BANK SEPAH AND BANK SEPAH INTERNATIONAL"): split on " AND " / " VE " when
   both sides look like names, so "Bank Sepah" matches.
3. **Short trade names**: "Alsultan Kuyumculuk" (2 of 6 words) lands at 0.84, just under review. A trade-name rule
   (first distinctive word + sector word) could raise these to review without raising decoys; dd-30 and dd-31 are
   the guard cases.
4. **Say what is not covered**: the answer's `how_to_read` should name the lists Katip does not check (OFAC, EU,
   UK OFSI, UN lists other than 1267/1988) so "no hit" is never read as a sanctions clearance.
5. "Kuzey Rüzgarı" vs "KUZEYRÜZGARI": compare with spaces removed when the word count differs.

## 3. Katip Uyum: scenarios from real decisions

Each case changes the worked example (`lab/uyum/examples/dd_harness.json`) the way the facts of a public decision
would, and checks that Uyum raises the finding a lawyer would expect. Data: `data/uyum_cases.json`.

| Case | Modelled on | Uyum must raise | OK | What a questionnaire cannot show |
|---|---|---|---|---|
| U-01 | ICO, DPP Law Ltd, monetary penalty £60,000, 14 Apr 2025 (UK GDPR Arts 5(1)(f), 32(1), 32(2), 33(1)). | `sec:mfa=action`, `sec:shared=action`, `sec:incident_owner=action` | ✓ | The 43-day delay is an operational failure; a questionnaire can only check that a breach owner and a 72-hour procedure exist (document 07). |
| U-02 | Datatilsynet (Denmark), SIRIUS law firm, fine EUR 67,200, 14 Jul 2022 (GDPR Art. 32). | `sec:mfa=action`, `sec:restore_tested=action` | ✓ | Whether patches were applied is not asked. |
| U-03 | UODO (Poland), court bailiff, fines EUR 4,935, decision 23 Oct 2025 (GDPR Arts 33(1), 34(1)-(2)). | `noreview:drafting=risk`, `sec:incident_owner=open` | ✓ | The missing risk analysis after the incident; the pack's breach procedure (07) asks for one, but only a drill shows it is used. |
| U-04 | Garante (Italy), OpenAI, EUR 15 million, decision 2 Nov 2024, published 20 Dec 2024. Reported annulled on appeal in March 2026: check before citing. | `basis:intake=open`, `lia:screening=action`, `ai50_1=action` | ✓ | Age verification is not asked (a law firm's agents rarely face the public). |
| U-05 | KVKK Board, decision 2020/26 (14 Jan 2020): a lawyer disclosed personal data to third parties by SMS; administrative fine reported as 50,000 TL. | `noreview:drafting=risk` | ✓ | Who the lawyer chooses to message is a professional decision, not a system design; Uyum can only flag outputs that leave the firm unchecked. |
| U-06 | KVKK Board, decision 2022/249 (17 Mar 2022): a technology company kept data on cloud servers abroad without a m.9 basis. | `kvkk9=action`, `raw:anthropic=risk`, `mask=risk` | ✓ | - |
| U-07 | KVKK Board, WhatsApp decision (2021): 1,950,000 TL for a bundled consent and transfers abroad without a valid basis. | `kvkk9=action`, `xfer:whatsapp=action` | ✓ | A personal WhatsApp account is a common real channel; the questionnaire only sees it if the firm lists it as a vendor. |
| U-08 | Garante (Italy), urgent limitation order against the DeepSeek chatbot, 30 Jan 2025 (data stored in China, insufficient answers on transfers). | `xfer:anthropic=action`, `kvkk9=action` | ✓ | - |
| U-09 | KVKK Board guide for lawyers (22 Sep 2026), p. 146: mask or anonymise before using AI tools; uploading client files to generative AI can be a transfer abroad. | `dpa:anthropic=action`, `mask=risk`, `kvkk9=action` | ✓ | - |
| U-10 | KVKK Board, decision 2023/1414: a lawyer submitted special-category (health) data to a court file. | `art9:drafting=action` | ✓ | Necessity for the specific claim is a legal judgment per file. |
| U-11 | Autoriteit Persoonsgegevens (NL), Clearview AI, EUR 30.5 million, Sep 2024: scraped public data into profiles of people. | `label:screening=risk`, `dpia=action` | ✓ | - |
| U-12 | EU AI Act Art. 5(1)(d), prohibited since 2 Feb 2025: predicting a person's risk of committing a crime from profiling alone. | `ai5=action` | ✓ | - |


The useful part of this table is the last column: breach timing, risk analysis after an incident, age checks and
per-file necessity are things only a drill or a lawyer's review shows. The pack's documents 07 and 08 describe
them; Uyum cannot verify them.

## Sources

- MASAK asset-freeze lists, open JSON endpoint, snapshot 24 Nov 2026 (`lab/dd`); UN Security Council consolidated
  list XML, same day (entity aliases).
- ICO, DPP Law Ltd penalty notice, 14 Apr 2025: https://ico.org.uk/action-weve-taken/enforcement/2025/04/dpp-law-ltd
- UODO via EDPB news, bailiff fined for not notifying a misdirected letter, decision 23 Oct 2025:
  https://www.edpb.europa.eu/news/polish-sa-administrative-fine-of-4-935-eur-for-bailiff-for-failure-to-notify-a-personal-data_lt
- Datatilsynet, SIRIUS law firm, 14 Jul 2022 (via enforcementtracker.com ETid-1270).
- Garante, OpenAI decision of 2 Nov 2024 (published 20 Dec 2024); press reports of the March 2026 appeal ruling
  were not checked against the judgment.
- KVKK Board decision summaries 2020/26, 2022/249, 2023/1414 and the 2021 WhatsApp announcement: titles and
  summaries from kvkk.gov.tr search results; the full texts returned HTTP 503 on 24 Nov 2026 and were not read.
- KVKK Board guide for lawyers, 22 Sep 2026, p. 146 (already cited in the main README).
- The ten common names are among the most frequent Turkish first names and surnames (TÜİK publishes the ranking); the list was not re-checked for this pack.

## Next

- Fix the items above, then add a **second, unseen round** of documents (written by someone who has not read
  this file) so the next score is blind again.
- Add Turkish-only cases from the core product (court decisions, icra files, health reports) to the same runner,
  so one command shows the whole product.
- Pick 5 cases with a before/after view (S-EU-01, S-EU-04, dd-01, dd-15, U-09) for the demo page.
