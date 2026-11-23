# 00 · Pack overview: what to do first, findings, open questions

**System:** Uğur Hukuk ajan sistemi (simulated) · **Controller:** Uğur Hukuk Bürosu (simulated) · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## Do these first

Ranked by severity and by how sensitive the data involved is.

1. **Stop sending client data to Google Gemini API (free tier).** This tier offers no Art. *(GDPR Arts. 28(1), 28(3), 28(10), 9(1); Avukatlık Kanunu m.36)*
2. **Split the legal basis for 'Email intake, filing and conflict check'.** Art. *(GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019)*
3. **Split the legal basis for 'Emailing drafts to clients'.** Art. *(GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019)*
4. **Write the legitimate-interests test for 'Operating the system'.** Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance against the data subjects' rights and reasonable expectations. *(GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21)*
5. **Write the legitimate-interests test for 'DD screening of officers and shareholders'.** Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance against the data subjects' rights and reasonable expectations. *(GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21)*

## The system in one paragraph

Five agents help a small Istanbul law firm (two lawyers, one trainee, one secretary) with due-diligence reports on Turkish targets for German and Dutch clients and with legal opinions on workplace accidents and negligent homicide. An intake agent reads the firm's Gmail, files attachments to Google Drive and checks conflicts with OpenAI. An OCR/translation agent sends scanned German/Dutch documents unmasked to Google Gemini (free tier). A screening agent searches Turkish and international sanctions lists and the web for officers and shareholders and gives each person a red/amber/green label with Claude. A drafting agent writes reports and opinions from Kalkan-masked text with OpenAI or Anthropic and a Supabase vector store. A sending agent emails approved drafts to clients, and in urgent cases emails a 'pre-draft, pending lawyer approval' without a lawyer having read it.

## Who is responsible

|  |  |
|---|---|
| Controller | Uğur Hukuk Bürosu (simulated) (Türkiye) |
| Role towards clients | both |
| Privacy contact | **[OPEN: privacy contact]** |
| DPO | none appointed (see findings) |
| EU representative (Art. 27) | none |
| Partners | Düsseldorf correspondent firm (fictional) |

## Which laws apply, and why

- Art. 3(2): the GDPR applies directly, but only to the processing related to offering services to people in the EU (3(2)(a)) or monitoring their behaviour there (3(2)(b)). Other activities (e.g. screening Turkish company officers) are not pulled in by this alone; the activity table in document 01 says which route applies to each.
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

17 must do, 10 risk to address, 16 open question, 16 note.

### Which law applies, and to what

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Appoint an EU representative (Art. 27) | GDPR Art. 27 | 00, 01, 03 |
| Open question | How many people's data a year, and is that large scale? | GDPR Arts. 35(3), 37(1); Recital 91 | 02 |
| Note | A DPO is probably not mandatory, but write down why | GDPR Art. 37(1)(c), Recital 91 | 00 |

### Legal bases

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Split the legal basis for 'Email intake, filing and conflict check' | GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019 | 01, 03, 11 |
| Must do | Split the legal basis for 'Emailing drafts to clients' | GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019 | 01, 03, 11 |
| Must do | Write the legitimate-interests test for 'Operating the system' | GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21 | 01, 02, 11 |
| Must do | Write the legitimate-interests test for 'DD screening of officers and shareholders' | GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21 | 01, 02, 11 |

### Special-category and criminal data

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Name the legal authority for criminal-offence data (GDPR Art. 10) | GDPR Art. 10 | 01, 02, 10 |
| Must do | Art. 9 condition for 'Operating the system' | GDPR Art. 9; KVKK m.6/3, m.6/4 | 01, 02, 09 |
| Must do | KVKK m.6/3 condition for criminal data | KVKK m.6/1, m.6/3-d, m.6/4 | 01, 09 |
| Note | Deceased people | GDPR Recital 27 | 02 |
| Note | Is a sanctions listing or pending case special-category data under KVKK? | KVKK m.5, m.6/1 | 01 |

### Vendors and contracts

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Joint-controller arrangement with Düsseldorf correspondent firm (fictional) | GDPR Art. 26(1)-(2) | 04, 03 |
| Must do | Settle, per client and matter, whether you are controller or processor | GDPR Arts. 4(7)-(8), 28(3), 30(2); EDPB Guidelines 07/2020 | 04, 01, 07 |
| Must do | Stop sending client data to Google Gemini API (free tier) | GDPR Arts. 28(1), 28(3), 28(10), 9(1); Avukatlık Kanunu m.36 | 04, 02 |
| Risk to address | Supabase (pgvector) still sees the facts in forensic and hospital reports, disability rates, indictments, statements, sanctions and asset-freeze listings | GDPR Arts. 9, 25, 32; Recital 26 | 02, 09 |
| Risk to address | Anthropic (Claude API) receives unmasked criminal, id_number, special data | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Risk to address | Google Gemini API (free tier) receives unmasked id_number, special data | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Risk to address | Google Workspace (Gmail, Drive) receives unmasked criminal, id_number, special data | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Risk to address | LangSmith (LangChain) receives unmasked criminal, id_number, special data | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Risk to address | OpenAI (API) receives unmasked criminal, id_number, special data | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Open question | Is there a DPA with Supabase (pgvector)? | GDPR Art. 28(3) | 04 |
| Open question | Is Brave Search API a processor or a controller? | GDPR Arts. 4(7)-(8), 28 | 04 |
| Open question | Is LangSmith (LangChain) a processor or a controller? | GDPR Arts. 4(7)-(8), 28 | 04 |
| Open question | Does Supabase (pgvector) train on what you send? | GDPR Arts. 5(1)(b), 28(3)(a) | 04 |
| Open question | How long does Anthropic (Claude API) keep prompts and outputs? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Open question | How long does Google Gemini API (free tier) keep prompts and outputs? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Open question | How long does OpenAI (API) keep prompts and outputs? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Open question | How long does Supabase (pgvector) keep prompts and outputs? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |

### Transfers abroad

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Prepare SCCs for EU clients who send files to Türkiye | GDPR Art. 46(2)(c); Decision (EU) 2021/914 | 05, 04 |
| Must do | KVKK transfer abroad: OpenAI (API), Anthropic (Claude API), Google Gemini API (free tier), Google Workspace (Gmail, Drive), Supabase (pgvector), LangSmith (LangChain), Brave Search API | KVKK m.9; Regulation on transfers abroad (10 Jul 2024) | 05 |
| Note | Anthropic (Claude API): onward transfer of EU clients' data | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Note | Brave Search API: onward transfer of EU clients' data | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Note | Google Gemini API (free tier): onward transfer of EU clients' data | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Note | Google Workspace (Gmail, Drive): onward transfer of EU clients' data | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Note | LangSmith (LangChain): onward transfer of EU clients' data | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Note | OpenAI (API): onward transfer of EU clients' data | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Note | Supabase (pgvector): EU region, United States parent | GDPR Arts. 28(2), 44, 48; EDPB Guidelines 05/2021 | 05 |

### Agents and human review

| Type | Finding | Source | Docs |
|---|---|---|---|
| Risk to address | 'DD screening of officers and shareholders' puts a risk label on people | GDPR Arts. 4(4), 5(1)(d), 15, 22 | 02, 10 |
| Risk to address | 'Sending agent' sends output to the client that a lawyer only sometimes reads first | GDPR Arts. 5(1)(d), 22, 25(1), 32(1)(b), 33 | 02, 03, 07, 09 |

### Security

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | Do the DPIA before going live (at least 5 of 9 EDPB criteria met) | GDPR Arts. 35(1), 35(7), 36; WP248 rev.01 | 02 |
| Must do | Security: add a tested restore from backup | GDPR Art. 32(1)(c)-(d) | 09 |
| Must do | Security: end shared logins and readable API keys | GDPR Art. 32(1)(b), 32(4) | 09 |
| Risk to address | Cloud models see the raw text | GDPR Arts. 25, 32(1)(a) | 02, 09 |
| Risk to address | EU documents are masked with a Turkish profile | GDPR Arts. 25, 32(1)(a) | 09, 02 |
| Open question | Security: Encryption at rest? | GDPR Art. 32(1)(a) | 09 |
| Open question | Security: Multi-factor login for staff and admin accounts? | GDPR Art. 32(1)(b) | 09 |
| Note | Masked text is pseudonymised, not anonymous | GDPR Art. 4(5), Recital 26; CJEU C-413/23 P | 02, 03, 09 |

### Retention

| Type | Finding | Source | Docs |
|---|---|---|---|
| Must do | 'Emailing drafts to clients' keeps data with no end date | GDPR Arts. 5(1)(e), 13(2)(a); KVKK m.7 | 06, 01 |
| Open question | How long is data from 'OCR and translation of scanned foreign documents' kept? | GDPR Arts. 5(1)(e), 30(1)(f) | 01, 06 |
| Open question | How long is data from 'Operating the system' kept? | GDPR Arts. 5(1)(e), 30(1)(f) | 01, 06 |

### Information and rights

| Type | Finding | Source | Docs |
|---|---|---|---|
| Open question | Privacy contact address | GDPR Arts. 13(1)(a), 30(1)(a); KVKK m.10/1-a | 01, 03 |
| Note | 'Drafting DD reports and legal opinions' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |
| Note | 'Email intake, filing and conflict check' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |
| Note | 'OCR and translation of scanned foreign documents' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |
| Note | 'DD screening of officers and shareholders' collects data not from the person: Art. 14 notice | GDPR Art. 14(3), 14(5) | 03 |

### EU AI Act

| Type | Finding | Source | Docs |
|---|---|---|---|
| Open question | Does any label or score predict whether a person will offend? (AI Act Art. 5(1)(d)) | AI Act Art. 5(1)(d); GDPR Art. 4(4) | 10, 02 |
| Open question | Will you offer the system to others under your name? | AI Act Arts. 3(3), 50 | 10 |
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
