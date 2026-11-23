# 01 · Record of processing activities (GDPR Art. 30)

**System:** Uğur Hukuk ajan sistemi (simulated) · **Controller:** Uğur Hukuk Bürosu (simulated) · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

Controller's record under Art. 30(1). The Art. 30(5) exemption for organisations under 250 people does not apply where processing is not occasional or includes Art. 9 or Art. 10 data.

## Controller (Art. 30(1)(a))

|  |  |
|---|---|
| Name | Uğur Hukuk Bürosu (simulated) |
| Address | Şişli, İstanbul (fictional) |
| Contact | **[OPEN: privacy contact]** |
| Representative | none |
| DPO | none |

## Activity: Email intake, filing and conflict check

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Receive client documents, file them per matter, check conflicts of interest |
| Role | unknown |
| How the GDPR applies | Art. 3(2), if this activity relates to the offer to people in the EU **[OPEN: confirm per activity]** |
| Lawful basis | GDPR Art. 6(1)(b) (performance of a contract with the data subject); Art. 9(2)(f) (establishment, exercise or defence of legal claims) |
| KVKK basis | KVKK m.5/2-c (sözleşmenin kurulması veya ifası) **[OPEN: confirm; for client work m.5/2-e may fit better]**; KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması) |
| Data subjects (c) | Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files |
| Personal data (c) | Names and contact details, TC kimlik, passport, German Steuer-ID, Dutch BSN, Salary, IBAN, insolvency notices, Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings |
| Source | data_subject, client |
| Recipients (d) | **[OPEN: recipients (clients, co-counsel, courts?)]** |
| Processors and vendors | OpenAI (API) (United States), Google Workspace (Gmail, Drive) (United States), LangSmith (LangChain) (United States) |
| Transfers outside the EEA (e) | OpenAI (API) → United States (onward (client SCCs)); Google Workspace (Gmail, Drive) → United States (onward (client SCCs)); LangSmith (LangChain) → United States (onward (client SCCs)) |
| Where it is stored | Matter folders (originals) on Google Drive, Mailbox incl. attachments and sent drafts, LangSmith traces (full prompts and outputs) |
| Retention (f) | 10 years after the matter closes |
| Security (g) | See document 09 (TOMs). |

## Activity: OCR and translation of scanned foreign documents

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Turn scanned German/Dutch documents into Turkish text |
| Role | unknown |
| How the GDPR applies | Art. 3(2), if this activity relates to the offer to people in the EU **[OPEN: confirm per activity]** |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: Understanding documents the client sent for the engaged legal service; Art. 9(2)(f) (establishment, exercise or defence of legal claims) |
| KVKK basis | KVKK m.5/2-f (meşru menfaat) **[OPEN: confirm; for client work m.5/2-e may fit better]**; KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması) |
| Data subjects (c) | Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files, Clients and their contact persons (DE/NL companies, DE individuals) |
| Personal data (c) | Names and contact details, TC kimlik, passport, German Steuer-ID, Dutch BSN, Salary, IBAN, insolvency notices, Forensic and hospital reports, disability rates |
| Source | client |
| Recipients (d) | **[OPEN: recipients (clients, co-counsel, courts?)]** |
| Processors and vendors | Google Gemini API (free tier) (United States), LangSmith (LangChain) (United States), Google Workspace (Gmail, Drive) (United States) |
| Transfers outside the EEA (e) | Google Gemini API (free tier) → United States (onward (client SCCs)); Google Workspace (Gmail, Drive) → United States (onward (client SCCs)); LangSmith (LangChain) → United States (onward (client SCCs)) |
| Where it is stored | Matter folders (originals) on Google Drive, LangSmith traces (full prompts and outputs) |
| Retention (f) | **[OPEN: retention period]** |
| Security (g) | See document 09 (TOMs). |

## Activity: DD screening of officers and shareholders

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Find sanctions, asset-freeze, insolvency and court records and press about people behind a DD target |
| Role | unknown |
| How the GDPR applies | Through EU clients' SCCs for their data; otherwise KVKK only |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: **[OPEN: legitimate interest + balancing test]** |
| KVKK basis | KVKK m.5/2-f (meşru menfaat) **[OPEN: confirm; for client work m.5/2-e may fit better]** |
| Data subjects (c) | Officers, shareholders and signatories of DD targets |
| Personal data (c) | Names and contact details, TC kimlik, passport, German Steuer-ID, Dutch BSN, Roles, shareholdings, signing powers, Salary, IBAN, insolvency notices, Indictments, statements, sanctions and asset-freeze listings |
| Source | public |
| Recipients (d) | the client (reports, opinions, results) |
| Processors and vendors | Anthropic (Claude API) (United States), Brave Search API (United States), LangSmith (LangChain) (United States), Google Workspace (Gmail, Drive) (United States), Supabase (pgvector) (Germany) |
| Transfers outside the EEA (e) | Anthropic (Claude API) → United States (onward (client SCCs)); Google Workspace (Gmail, Drive) → United States (onward (client SCCs)); LangSmith (LangChain) → United States (onward (client SCCs)); Brave Search API → United States (onward (client SCCs)) |
| Where it is stored | Matter folders (originals) on Google Drive, Vector store of masked chunks of past opinions and DD reports, LangSmith traces (full prompts and outputs) |
| Retention (f) | 10 years after the matter closes |
| Security (g) | See document 09 (TOMs). |

## Activity: Drafting DD reports and legal opinions

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Draft DD reports and expert opinions (workplace accident, negligent homicide) |
| Role | unknown |
| How the GDPR applies | Art. 3(2), if this activity relates to the offer to people in the EU **[OPEN: confirm per activity]** |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: Providing the legal service the client engaged; Art. 9(2)(f) (establishment, exercise or defence of legal claims) |
| KVKK basis | KVKK m.5/2-f (meşru menfaat) **[OPEN: confirm; for client work m.5/2-e may fit better]**; KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması) |
| Data subjects (c) | Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files |
| Personal data (c) | Names and contact details, Roles, shareholdings, signing powers, Salary, IBAN, insolvency notices, Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings, Children of deceased workers (dates of birth) |
| Source | client |
| Recipients (d) | the client (reports, opinions, results), Düsseldorf correspondent firm (fictional) (joint controller) |
| Processors and vendors | OpenAI (API) (United States), Anthropic (Claude API) (United States), Supabase (pgvector) (Germany), LangSmith (LangChain) (United States), Google Workspace (Gmail, Drive) (United States), Katip Kalkan (lawyer's MacBook) (the user's own computer) |
| Transfers outside the EEA (e) | OpenAI (API) → United States (onward (client SCCs)); Anthropic (Claude API) → United States (onward (client SCCs)); Google Workspace (Gmail, Drive) → United States (onward (client SCCs)); LangSmith (LangChain) → United States (onward (client SCCs)) |
| Where it is stored | Matter folders (originals) on Google Drive, Vector store of masked chunks of past opinions and DD reports, Kalkan masking vault, LangSmith traces (full prompts and outputs) |
| Retention (f) | 10 years after the matter closes |
| Security (g) | See document 09 (TOMs). |

## Activity: Emailing drafts to clients

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Deliver drafts and pre-drafts to the client |
| Role | unknown |
| How the GDPR applies | Art. 3(2), if this activity relates to the offer to people in the EU **[OPEN: confirm per activity]** |
| Lawful basis | GDPR Art. 6(1)(b) (performance of a contract with the data subject); Art. 9(2)(f) (establishment, exercise or defence of legal claims) |
| KVKK basis | KVKK m.5/2-c (sözleşmenin kurulması veya ifası) **[OPEN: confirm; for client work m.5/2-e may fit better]**; KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması) |
| Data subjects (c) | Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files |
| Personal data (c) | Names and contact details, Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings, Salary, IBAN, insolvency notices |
| Source | generated |
| Recipients (d) | the client (reports, opinions, results) |
| Processors and vendors | Google Workspace (Gmail, Drive) (United States) |
| Transfers outside the EEA (e) | Google Workspace (Gmail, Drive) → United States (onward (client SCCs)) |
| Where it is stored | Mailbox incl. attachments and sent drafts |
| Retention (f) | Not deleted |
| Security (g) | See document 09 (TOMs). |

## Activity: Operating the system

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Troubleshooting and quality checks via agent traces |
| Role | unknown |
| How the GDPR applies | Art. 3(2), if this activity relates to the offer to people in the EU **[OPEN: confirm per activity]** |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: **[OPEN: legitimate interest + balancing test]** |
| KVKK basis | KVKK m.5/2-f (meşru menfaat) **[OPEN: confirm; for client work m.5/2-e may fit better]** |
| Data subjects (c) | Firm lawyers, trainee, secretary, Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files |
| Personal data (c) | Prompts, outputs, agent traces, logins, Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings |
| Source | generated |
| Recipients (d) | **[OPEN: recipients (clients, co-counsel, courts?)]** |
| Processors and vendors | LangSmith (LangChain) (United States) |
| Transfers outside the EEA (e) | LangSmith (LangChain) → United States (onward (client SCCs)) |
| Where it is stored | LangSmith traces (full prompts and outputs) |
| Retention (f) | **[OPEN: retention period]** |
| Security (g) | See document 09 (TOMs). |

## Processor's record (Art. 30(2))

For work done on a client's instructions. One row per client.

| Client (controller) | Categories of processing | Transfers and safeguards | Measures |
|---|---|---|---|
| **[OPEN: client]** | **[OPEN: e.g. DD research on instructions]** | document 05 | document 09 |

## Points for the reviewer

- **Must do: Split the legal basis for 'Email intake, filing and conflict check'.** Art. 6(1)(b) covers only processing necessary for a contract with the data subject. These people have no contract with the firm: Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files. Use 6(1)(b) for the contracting client (an individual), and 6(1)(f) with a legitimate-interests test (document 11) for everyone else, including the contact persons of corporate clients. *(GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019)*
- **Must do: Split the legal basis for 'Emailing drafts to clients'.** Art. 6(1)(b) covers only processing necessary for a contract with the data subject. These people have no contract with the firm: Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files. Use 6(1)(b) for the contracting client (an individual), and 6(1)(f) with a legitimate-interests test (document 11) for everyone else, including the contact persons of corporate clients. *(GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019)*
- **Must do: Write the legitimate-interests test for 'Operating the system'.** Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance against the data subjects' rights and reasonable expectations. Document 11 is the template, pre-filled. *(GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21)*
- **Must do: Write the legitimate-interests test for 'DD screening of officers and shareholders'.** Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance against the data subjects' rights and reasonable expectations. Document 11 is the template, pre-filled. *(GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21)*
- **Must do: 'Emailing drafts to clients' keeps data with no end date.** Retention 'Not deleted' is not a limit. Set a period or the criteria that end it. *(GDPR Arts. 5(1)(e), 13(2)(a); KVKK m.7)*
- **Must do: Appoint an EU representative (Art. 27).** The GDPR reaches this controller directly through Art. 3(2) and it has no EU establishment, so it must designate in writing a representative in a Member State where the people concerned are. The exemption in Art. 27(2)(a) needs processing that is occasional, does not include large-scale Art. 9 or Art. 10 data and is unlikely to result in a risk: document why, if you rely on it. *(GDPR Art. 27)*
- **Must do: Name the legal authority for criminal-offence data (GDPR Art. 10).** For screening (Email intake, filing and conflict check, DD screening of officers and shareholders, Emailing drafts to clients, Operating the system): GDPR Art. 10 allows criminal-offence data only under official authority or where Union or Member State law authorises it with safeguards. For AML-obliged clients that is the national AML law (Regulation (EU) 2024/1624 and the transposition of Directive (EU) 2015/849); otherwise consider screening companies only and keeping individuals to exact list matches. For legal advice and defence (Drafting DD reports and legal opinions): the criminal facts are the subject of the service, so 'screen less' is no answer. Art. 10 has no legal-claims exception of its own; identify the Member State law that authorises lawyers to process such data (many have one), or record why the GDPR does not reach this activity directly (see Art. 3 in document 00). *(GDPR Art. 10)*
- **Must do: Art. 9 condition for 'Operating the system'.** This activity touches special-category data (health, religion, ethnicity, ...). Besides an Art. 6 basis it needs an Art. 9(2) condition; for lawyers this is usually 9(2)(f) (legal claims). Under KVKK, the m.6/3 condition (usually m.6/3-d) and the Board's adequate measures (decision 2018/10) apply. *(GDPR Art. 9; KVKK m.6/3, m.6/4)*
- **Must do: KVKK m.6/3 condition for criminal data.** Under KVKK, data on criminal convictions and security measures is special-category data (m.6/1). It needs one of the m.6/3 conditions (for lawyers usually m.6/3-d, establishing or defending a right) and the Board's adequate measures (m.6/4, decision 2018/10). Activities: Email intake, filing and conflict check, DD screening of officers and shareholders, Drafting DD reports and legal opinions, Emailing drafts to clients, Operating the system. *(KVKK m.6/1, m.6/3-d, m.6/4)*
- **Must do: Settle, per client and matter, whether you are controller or processor.** A lawyer giving legal advice usually decides why and how client data is used, which makes the firm a controller (EDPB Guidelines 07/2020 give lawyers as an example). Where a client nevertheless wants an Art. 28 contract (e.g. a German client asking for an AVV) for work done strictly on its instructions, you are its processor for that work: you then need the Art. 28(3) terms with the client, a processor's record (Art. 30(2)) and breach notices to the client, not to the authority (Art. 33(2)). Document 04 has a section on this. *(GDPR Arts. 4(7)-(8), 28(3), 30(2); EDPB Guidelines 07/2020)*
- **Open question: How long is data from 'OCR and translation of scanned foreign documents' kept?** Each purpose needs a retention period or the criteria that set it. *(GDPR Arts. 5(1)(e), 30(1)(f))*
- **Open question: How long is data from 'Operating the system' kept?** Each purpose needs a retention period or the criteria that set it. *(GDPR Arts. 5(1)(e), 30(1)(f))*
- **Open question: Privacy contact address.** Needed in the notice and the record. *(GDPR Arts. 13(1)(a), 30(1)(a); KVKK m.10/1-a)*
- **Note: Is a sanctions listing or pending case special-category data under KVKK?** KVKK m.6/1 names 'ceza mahkûmiyeti ve güvenlik tedbirleri'. A sanctions or asset-freeze listing, or a pending prosecution, is not a conviction; whether it falls under m.6 is not settled. Treat it with m.6 safeguards until Board practice says otherwise, and record the choice. Activities: Email intake, filing and conflict check, DD screening of officers and shareholders, Drafting DD reports and legal opinions, Emailing drafts to clients, Operating the system. *(KVKK m.5, m.6/1)*

## KVKK (Türkiye)

The Turkish inventory is [01-envanter.tr.md](01-envanter.tr.md). VERBİS (m.16): see the KVKK map in document 00.
