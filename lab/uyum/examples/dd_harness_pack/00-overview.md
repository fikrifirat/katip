# 00 · Pack overview: what to do first, findings, open questions

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## Do these first

Ranked by severity and by how sensitive the data involved is.

1. **Name the legal authority for criminal-offence data (GDPR Art. 10).** For screening (DD screening of target companies and their people): GDPR Art. 10 allows criminal-offence data only under official authority or where Union or Member State law authorises it with safeguards. *(GDPR Art. 10)*
2. **Prepare SCCs for EU clients who send files to Türkiye.** Türkiye has no EU adequacy decision, so each EU client needs the 2021 SCCs with you and its own transfer impact assessment. *(GDPR Art. 46(2)(c); Decision (EU) 2021/914)*
3. **Do the DPIA before going live (at least 4 of 9 EDPB criteria met).** Two or more criteria usually mean the processing is likely to result in a high risk. *(GDPR Arts. 35(1), 35(7), 36; WP248 rev.01)*
4. **KVKK transfer abroad: Anthropic (Claude API), Mistral AI, Hetzner.** Since 1 June 2024, KVKK m.9 allows transfers abroad on an adequacy decision of the Board, appropriate safeguards (the Board's standard contract, notified to the Authority within 5 business days of signing; binding corporate rules; a written undertaking with the Board's permission) or the occasional-transfer exceptions of m.9/6. *(KVKK m.9; Regulation on transfers abroad (10 Jul 2024))*
5. **Anthropic (Claude API) still sees the facts in health data in case files (e.g. workplace accident opinions).** Masking hides who the person is, not what happened to them. *(GDPR Arts. 9, 25, 32; Recital 26)*

## The system in one paragraph

Three agents help two lawyers prepare due-diligence (DD) reports and legal opinions. An intake agent sorts the client's documents and checks conflicts. A screening agent looks up the target company and its officers and shareholders in Turkish public sources (MASAK asset-freeze lists, ilan.gov.tr, Türkiye Ticaret Sicili Gazetesi) and returns the exact records with links. A drafting agent writes report and opinion drafts with a cloud language model. Documents are masked on the lawyer's computer (Katip Kalkan) before any text goes to a cloud model. A lawyer reviews every output before it goes to the client.

## Who is responsible

|  |  |
|---|---|
| Controller | Örnek Hukuk Bürosu (Türkiye) |
| Role towards clients | controller |
| Privacy contact | kvkk@ornekhukuk.example |
| DPO | none appointed (see findings) |
| EU representative (Art. 27) | none |
| Partners | none |

## Which laws apply, and why

- EU clients send personal data out of the EU/EEA: for them that is a transfer under Chapter V, so the GDPR's standards reach this firm through the SCCs it signs with them (Decision (EU) 2021/914), even where Art. 3(2) does not apply.
- KVKK (Law No. 6698) applies in parallel: the controller processes data in Türkiye.

## The pack

| # | Document | What it is for |
|---|---|---|
| 01 | [Record of processing activities (GDPR Art. 30)](01-ropa.md) | What is processed, why, for whom, where, how long. The supervisory authority can ask for it. |
| 02 | [Data protection impact assessment (GDPR Art. 35)](02-dpia.md) | Whether the risk is high, and what reduces it. Required before go-live when risk is likely high. |
| 03 | [Privacy notices (GDPR Arts. 13 and 14)](03-privacy-notice.md) | What clients and other people are told, at collection or within a month. |
| 04 | [Roles and contracts: processors, clients, partners, secrecy (GDPR Arts. 26 and 28)](04-contracts.md) | Controller or processor per client; DPA checklist per vendor; joint controllers; secrecy. |
| 05 | [International transfers and transfer impact assessment (GDPR Chapter V, KVKK m.9)](05-transfers-tia.md) | Which data leaves the EU or Türkiye, on what legal tool, and with what risk. |
| 06 | [Retention and deletion policy (GDPR Art. 5(1)(e), KVKK m.7)](06-retention.md) | How long each kind of data is kept and how it is deleted, including in the agents' memory. |
| 07 | [Personal data breach procedure (GDPR Arts. 33 and 34, KVKK m.12/5)](07-breach.md) | Who notifies whom, and what happens in the 72 hours after a leak. |
| 08 | [Data subject request procedure (GDPR Arts. 12 and 15-22, KVKK m.11 and m.13)](08-dsr.md) | How access, deletion and other requests are answered within a month. |
| 09 | [Technical and organisational measures (GDPR Art. 32, KVKK m.12)](09-toms.md) | The security measures, with what is in place and what is not. |
| 10 | [EU AI Act note: role, risk class and duties (Regulation (EU) 2024/1689 as amended)](10-ai-act.md) | What the EU AI Act asks of this system, and from when. |
| 11 | [Legitimate-interests assessments (GDPR Art. 6(1)(f))](11-lia.md) | The written balancing test for each activity based on legitimate interests. |
| TR | [Özet ve yapılacaklar](00-ozet.tr.md) | Turkish summary of the findings, for the lawyer |
| TR | [Kişisel veri işleme envanteri](01-envanter.tr.md) | Turkish inventory (KVKK, VERBİS) |
| TR | [Aydınlatma metni](03-aydinlatma-metni.tr.md) | Turkish notice under KVKK m.10 |

## All findings, by theme

5 must do, 1 risk to address, 8 open question, 9 note.

### Which law applies, and to what

| Type | Finding | Source | Docs |
|---|---|---|---|
| Open question | Does the GDPR reach you directly (Art. 3(2))? | GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018 | 00, 01, 03, 07 |
| Note | A DPO is probably not mandatory, but write down why | GDPR Art. 37(1)(c), Recital 91 | 00 |

### Special-category and criminal data

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Name the legal authority for criminal-offence data (GDPR Art. 10) | GDPR Art. 10 | 01, 02, 10 |
| Note | Is a sanctions listing or pending case special-category data under KVKK? | KVKK m.5, m.6/1 | 01 |

### Vendors and contracts

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Sign or accept Mistral AI's DPA | GDPR Art. 28(3) | 04 |
| Risk to address | Anthropic (Claude API) still sees the facts in health data in case files (e.g. workplace accident opinions) | GDPR Arts. 9, 25, 32; Recital 26 | 02, 09 |
| Open question | Does Mistral AI train on what you send? | GDPR Arts. 5(1)(b), 28(3)(a) | 04 |
| Open question | How long does Anthropic (Claude API) keep prompts and outputs? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Open question | How long does Mistral AI keep prompts and outputs? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |

### Transfers abroad

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Prepare SCCs for EU clients who send files to Türkiye | GDPR Art. 46(2)(c); Decision (EU) 2021/914 | 05, 04 |
| Must do | KVKK transfer abroad: Anthropic (Claude API), Mistral AI, Hetzner | KVKK m.9; Regulation on transfers abroad (10 Jul 2024) | 05 |
| Note | Anthropic (Claude API): onward transfer of EU clients' data | GDPR Art. 44; Decision (EU) 2021/914 | 05 |

### Security

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Do the DPIA before going live (at least 4 of 9 EDPB criteria met) | GDPR Arts. 35(1), 35(7), 36; WP248 rev.01 | 02 |
| Open question | Security: Backups? | GDPR Art. 32(1)(c) | 09 |
| Open question | Security: A named person who runs a breach? | GDPR Arts. 33-34 | 09 |
| Open question | Security: Multi-factor login for staff and admin accounts? | GDPR Art. 32(1)(b) | 09 |
| Open question | Security: A tested restore from backup? | GDPR Art. 32(1)(c)-(d) | 09 |
| Note | Masked text is pseudonymised, not anonymous | GDPR Art. 4(5), Recital 26; CJEU C-413/23 P | 02, 03, 09 |
| Note | The 'eu' masking profile is beta: names are its weak spot | GDPR Arts. 25, 32(1)(a) | 09 |

### Information and rights

| Type | Finding | Source | Docs |
|---|---|---|---|
| Note | 'Drafting DD reports and legal opinions' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |
| Note | 'Client intake and conflict check' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |
| Note | 'DD screening of target companies and their people' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |

### EU AI Act

| Type | Finding | Source | Docs |
|---|---|---|---|
| Note | AI literacy | AI Act Art. 4 | 10, 09 |

## KVKK map

| GDPR document | KVKK counterpart |
|---|---|
| 01 RoPA (Art. 30) | Kişisel veri işleme envanteri; VERBİS registration (m.16) unless a Board exemption decision covers the firm. Exemption decisions since 2018 cover several professions; check whether lawyers are covered in the current list **[OPEN: decision number, verified]**. An exemption from registration does not remove the other duties. |
| 02 DPIA (Art. 35) | No statutory DPIA; the Board's security guide expects a risk analysis |
| 03 Notice (Arts. 13-14) | Aydınlatma metni (m.10; Aydınlatma Yükümlülüğü Tebliği), in Turkish |
| 04 Contracts (Arts. 26, 28) | Veri işleyen sözleşmesi; joint liability for security (m.12/2) |
| 05 Transfers | Yurt dışına aktarım (m.9 as amended in 2024): standard contract notified within 5 business days |
| 06 Retention | Saklama ve imha politikası (Silme, Yok Etme veya Anonim Hale Getirme Yönetmeliği), required for controllers that must register in VERBİS |
| 07 Breach (Arts. 33-34) | m.12/5: notify the Board 'en kısa sürede', read as 72 hours (Board decision 2019/10) |
| 08 Rights (Arts. 15-22) | m.11 rights; m.13 answer within 30 days, free in principle |
| 09 TOMs (Art. 32) | m.12/1; for special-category data the adequate measures of m.6/4 (Board decision 2018/10) |
| 10 AI Act | No Turkish equivalent in force |
| 11 LIA (Art. 6(1)(f)) | KVKK m.5/2-f meşru menfaat: the Board also expects a balancing test |

## Sources

Lists checked 23 Nov 2026 (compiled from the texts; re-check lists marked 'moving' before use). AI Act text and dates as amended by Regulation (EU) 2026/1744 (Digital Omnibus on AI), in force 27 July 2026.

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
