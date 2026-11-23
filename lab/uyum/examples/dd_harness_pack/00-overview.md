# 00 · Pack overview, findings and open questions

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

## The system in one paragraph

Three agents help two lawyers prepare due-diligence (DD) reports and legal opinions. An intake agent sorts the client's documents and checks conflicts. A screening agent looks up the target company and its officers and shareholders in Turkish public sources (MASAK asset-freeze lists, ilan.gov.tr, Türkiye Ticaret Sicili Gazetesi) and returns the exact records with links. A drafting agent writes report and opinion drafts with a cloud language model. Documents are masked on the lawyer's computer (Katip Kalkan) before any text goes to a cloud model. A lawyer reviews every output before it goes to the client.

## Who is responsible

|  |  |
|---|---|
| Controller | Örnek Hukuk Bürosu (Türkiye) |
| Role | controller |
| Privacy contact | kvkk@ornekhukuk.example |
| DPO | none appointed (see findings) |
| EU representative (Art. 27) | none |

## Which laws apply, and why

- EU clients send personal data out of the EU/EEA: for them it is a transfer under Chapter V, so they will ask for SCCs and security terms even where Art. 3(2) does not reach this controller directly.
- KVKK (Law No. 6698) applies in parallel: the controller processes data in Türkiye.

## The pack

| # | Document | What it is for |
|---|---|---|
| 01 | [Record of processing activities (GDPR Art. 30)](01-ropa.md) | What is processed, why, for whom, where, how long. The supervisory authority can ask for it. |
| 02 | [Data protection impact assessment (GDPR Art. 35)](02-dpia.md) | Whether the risk is high, and what reduces it. Required before go-live when risk is likely high. |
| 03 | [Privacy notice (GDPR Arts. 13 and 14)](03-privacy-notice.md) | What clients and other people are told, at collection or within a month. |
| 04 | [Processor agreements: checklist per vendor (GDPR Art. 28)](04-dpa-checklist.md) | Per vendor: does its contract have every Art. 28(3) term? |
| 05 | [International transfers and transfer impact assessment (GDPR Chapter V)](05-transfers-tia.md) | Which data leaves the EU or Türkiye, on what legal tool, and with what risk. |
| 06 | [Retention and deletion policy (GDPR Art. 5(1)(e))](06-retention.md) | How long each kind of data is kept and how it is deleted, including in the agents' memory. |
| 07 | [Personal data breach procedure (GDPR Arts. 33 and 34)](07-breach.md) | Who does what in the 72 hours after a leak. |
| 08 | [Data subject request procedure (GDPR Arts. 12 and 15-22)](08-dsr.md) | How access, deletion and other requests are answered within a month. |
| 09 | [Technical and organisational measures (GDPR Art. 32)](09-toms.md) | The security measures, written down so they can be checked. |
| 10 | [EU AI Act note: role, risk class and duties (Regulation (EU) 2024/1689)](10-ai-act.md) | What the EU AI Act asks of this system, and from when. |

## Findings

5 must do, 1 risk to address, 8 open question, 5 note.

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Art. 10 authority for criminal-offence data in 'DD screening of target companies and their people' | GDPR Art. 10; KVKK m.6 | 01, 02, 10 |
| Must do | Sign or accept Mistral AI's DPA | GDPR Art. 28(3) | 04 |
| Must do | Do the DPIA before going live (4 of 9 EDPB criteria met) | GDPR Arts. 35(1), 35(7), 36; WP248 rev.01 | 02 |
| Must do | Prepare SCCs for EU clients who send files to Türkiye | GDPR Art. 46(2)(c); Decision (EU) 2021/914 | 05, 04 |
| Must do | KVKK transfer abroad: Anthropic (Claude API), Mistral AI, Hetzner | KVKK m.9; Regulation on transfers abroad (10 Jul 2024) | 05 |
| Risk to address | Anthropic (Claude API) still sees the facts in health data in case files (e.g. workplace accident opinions) | GDPR Arts. 9, 25, 32; Recital 26 | 02, 09 |
| Open question | Does the GDPR reach you directly (Art. 3(2))? | GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018 | 00, 01, 03, 07 |
| Open question | Security: Backups and restore test? | GDPR Art. 32(1)(c) | 09 |
| Open question | Security: A named person who runs a breach? | GDPR Arts. 33-34 | 09 |
| Open question | Security: Multi-factor login for staff and admin accounts? | GDPR Art. 32(1)(b) | 09 |
| Open question | Does Mistral AI train on what you send? | GDPR Arts. 5(1)(b), 28(3)(a) | 04 |
| Open question | How long does Anthropic (Claude API) keep prompts and outputs? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Open question | How long does Mistral AI keep prompts and outputs? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Open question | Which transfer tool covers Anthropic (Claude API) (United States)? | GDPR Arts. 45-46 | 05 |
| Note | AI literacy | AI Act Art. 4 | 10, 09 |
| Note | 'Drafting DD reports and legal opinions' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |
| Note | 'DD screening of target companies and their people' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |
| Note | A DPO is probably not mandatory, but write down why | GDPR Art. 37(1)(c), Recital 91 | 00 |
| Note | Masked text is pseudonymised, not anonymous | GDPR Art. 4(5), Recital 26; CJEU C-413/23 P | 02, 03, 09 |

## KVKK map

KVKK was modelled on the GDPR's predecessor and shares most concepts. Where Türkiye differs, each document has a KVKK section.

| GDPR document | KVKK counterpart |
|---|---|
| 01 RoPA (Art. 30) | Kişisel veri işleme envanteri; VERBİS kaydı (m.16) unless an exemption decision of the Board covers the controller (check the current list) |
| 02 DPIA (Art. 35) | No statutory DPIA; the Board's guides recommend a risk analysis |
| 03 Notice (Arts. 13-14) | Aydınlatma metni (m.10; Aydınlatma Yükümlülüğü Tebliği) |
| 04 DPA (Art. 28) | Veri işleyen sözleşmesi; joint liability for security (m.12/2) |
| 05 Transfers | Yurt dışına aktarım (m.9, amended 2024): standard contract notified within 5 business days |
| 06 Retention | Saklama ve imha politikası (Silme, Yok Etme veya Anonim Hale Getirme Yönetmeliği) |
| 07 Breach (Arts. 33-34) | m.12/5: notify the Board 'en kısa sürede', read as 72 hours (Board decision 2019/10) |
| 08 Rights (Arts. 15-22) | m.11 rights; m.13 answer within 30 days, free of charge in principle |
| 09 TOMs (Art. 32) | m.12/1 technical and administrative measures; Board security guide |
| 10 AI Act | No Turkish equivalent in force (check the AI bill status) |

## Sources

Lists checked 23 Nov 2026 (compiled from the texts; re-check lists marked 'moving' before use).

- [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- [AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [KVKK](https://www.mevzuat.gov.tr/mevzuatmetin/1.5.6698.pdf)
- [SCCs (Decision 2021/914)](https://eur-lex.europa.eu/eli/dec_impl/2021/914/oj)
- [EDPB Recommendations 01/2020 (transfer tools)](https://www.edpb.europa.eu/our-work-tools/our-documents/recommendations/recommendations-012020-measures-supplement-transfer_en)
- [WP248 rev.01 (DPIA)](https://ec.europa.eu/newsroom/article29/items/611236)
- [EDPB Guidelines 9/2022 (breach notification)](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-92022-personal-data-breach-notification-under_en)
- [EDPB Guidelines 3/2018 (territorial scope)](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32018-territorial-scope-gdpr-article-3-version_en)
- [EU-US Data Privacy Framework list](https://www.dataprivacyframework.gov/list)
- [Adequacy decisions](https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en)
