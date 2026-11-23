# 05 · International transfers and transfer impact assessment (GDPR Chapter V, KVKK m.9)

**System:** Uğur Hukuk ajan sistemi (simulated) · **Controller:** Uğur Hukuk Bürosu (simulated) · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## Map of data leaving the EU/EEA or Türkiye

| Vendor | Country | Receives | GDPR route | TIA needed | KVKK m.9 transfer |
|---|---|---|---|---|---|
| OpenAI (API) | United States | raw | onward (client SCCs) | yes | yes |
| Anthropic (Claude API) | United States | raw | onward (client SCCs) | yes | yes |
| Google Gemini API (free tier) | United States | raw | onward (client SCCs) | yes | yes |
| Google Workspace (Gmail, Drive) | United States | raw | onward (client SCCs) | yes | yes |
| Supabase (pgvector) | Germany | masked | EEA | no | yes |
| LangSmith (LangChain) | United States | raw | onward (client SCCs) | yes | yes |
| Brave Search API | United States | raw | onward (client SCCs) | yes | yes |

GDPR routes: **EEA** no transfer; **adequacy** Art. 45 decision; **DPF** a US organisation certified under the EU-US Data Privacy Framework, usable by exporters in the EU/EEA; **SCC** Art. 46(2)(c) standard clauses (Decision 2021/914), which need this assessment; **onward (client SCCs)** a firm outside the EU passes EU clients' data on, governed by Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers of the SCCs it signed with them; **same country** the vendor sits where the controller does.

## EU clients sending data to Türkiye

Each EU client exporting files to you needs the SCCs and its own TIA about Türkiye. Proposed module: **Module One (controller to controller)** (and Module Two for matters where you act on instructions). Pre-filled annexes, for the reviewer to complete:

| SCC Annex | Content |
|---|---|
| I.A Data importer | Uğur Hukuk Bürosu (simulated), Şişli, İstanbul (fictional); contact **[OPEN: contact]**; role: controller |
| I.B Categories of data subjects | Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files, Firm lawyers, trainee, secretary |
| I.B Categories of data | Names and contact details, TC kimlik, passport, German Steuer-ID, Dutch BSN, Roles, shareholdings, signing powers, Salary, IBAN, insolvency notices, Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings, Children of deceased workers (dates of birth), Prompts, outputs, agent traces, logins |
| I.B Sensitive data and safeguards | See documents 02 and 09; masking before any cloud call where configured |
| I.B Purpose | Receive client documents, file them per matter, check conflicts of interest; Turn scanned German/Dutch documents into Turkish text; Find sanctions, asset-freeze, insolvency and court records and press about people behind a DD target; Draft DD reports and expert opinions (workplace accident, negligent homicide); Deliver drafts and pre-drafts to the client; Troubleshooting and quality checks via agent traces |
| I.B Retention | Document 06 |
| I.B Onward recipients | OpenAI (API), Anthropic (Claude API), Google Gemini API (free tier), Google Workspace (Gmail, Drive), Supabase (pgvector), LangSmith (LangChain), Brave Search API |
| II Technical and organisational measures | Document 09 |

**Local laws a TIA about Türkiye has to discuss** (Clause 14: local laws and practices (the TIA); Clause 15: requests from public authorities). Candidates for the reviewing lawyer to confirm and analyse, not a finished assessment:

- CMK m.130 (search of law offices: by a judge's decision, under the prosecutor's supervision, with the bar president or a representative present)
- Law No. 2937 on State Intelligence Services and MİT (powers to request information and documents)
- Law No. 5651 (internet content and traffic data)
- KVKK m.28 (processing by public authorities outside parts of the Law: e.g. national security, criminal investigations)
- Avukatlık Kanunu m.36 (lawyer's duty of secrecy) and m.58 (investigations concerning lawyers)

**[OPEN: conclusion: are there laws or practices that prevent the importer from meeting the SCCs, and which supplementary measures address them?]**

## TIA: OpenAI (API) (United States)

Steps from EDPB Recommendations 01/2020.

| Step | Assessment |
|---|---|
| 1. Know the transfer | LLM for intake and drafting; data: raw; region: **[OPEN: region]**; sub-processor list: **[OPEN: sub-processors]** |
| 2. Transfer tool | Onward transfer under the clients' SCCs: the recipient accepts the SCCs (or another Chapter V safeguard). **[OPEN: which tool the vendor offers]** |
| 3. Laws and practice of the destination | **[OPEN: government access laws that apply to this vendor, e.g. FISA 702 for US providers]** |
| 4. Supplementary measures | **[OPEN: supplementary measures; the text is sent unmasked]** |
| 5. Procedural steps | If SCCs are changed or another tool is used, check whether Art. 46(3) authorisation is needed |
| 6. Re-evaluate | **[OPEN: date; at least yearly and on vendor changes]** |

## TIA: Anthropic (Claude API) (United States)

Steps from EDPB Recommendations 01/2020.

| Step | Assessment |
|---|---|
| 1. Know the transfer | LLM for screening and drafting; data: raw; region: **[OPEN: region]**; sub-processor list: **[OPEN: sub-processors]** |
| 2. Transfer tool | Onward transfer under the clients' SCCs: the recipient accepts the SCCs (or another Chapter V safeguard). **[OPEN: which tool the vendor offers]** |
| 3. Laws and practice of the destination | **[OPEN: government access laws that apply to this vendor, e.g. FISA 702 for US providers]** |
| 4. Supplementary measures | **[OPEN: supplementary measures; the text is sent unmasked]** |
| 5. Procedural steps | If SCCs are changed or another tool is used, check whether Art. 46(3) authorisation is needed |
| 6. Re-evaluate | **[OPEN: date; at least yearly and on vendor changes]** |

## TIA: Google Gemini API (free tier) (United States)

Steps from EDPB Recommendations 01/2020.

| Step | Assessment |
|---|---|
| 1. Know the transfer | OCR and translation; data: raw; region: **[OPEN: region]**; sub-processor list: **[OPEN: sub-processors]** |
| 2. Transfer tool | Onward transfer under the clients' SCCs: the recipient accepts the SCCs (or another Chapter V safeguard). **[OPEN: which tool the vendor offers]** |
| 3. Laws and practice of the destination | **[OPEN: government access laws that apply to this vendor, e.g. FISA 702 for US providers]** |
| 4. Supplementary measures | **[OPEN: supplementary measures; the text is sent unmasked]** |
| 5. Procedural steps | If SCCs are changed or another tool is used, check whether Art. 46(3) authorisation is needed |
| 6. Re-evaluate | **[OPEN: date; at least yearly and on vendor changes]** |

## TIA: Google Workspace (Gmail, Drive) (United States)

Steps from EDPB Recommendations 01/2020.

| Step | Assessment |
|---|---|
| 1. Know the transfer | Email and file storage; data: raw; region: **[OPEN: region]**; sub-processor list: yes |
| 2. Transfer tool | Onward transfer under the clients' SCCs: the recipient accepts the SCCs (or another Chapter V safeguard). **[OPEN: which tool the vendor offers]** |
| 3. Laws and practice of the destination | **[OPEN: government access laws that apply to this vendor, e.g. FISA 702 for US providers]** |
| 4. Supplementary measures | **[OPEN: supplementary measures; the text is sent unmasked]** |
| 5. Procedural steps | If SCCs are changed or another tool is used, check whether Art. 46(3) authorisation is needed |
| 6. Re-evaluate | **[OPEN: date; at least yearly and on vendor changes]** |

## TIA: LangSmith (LangChain) (United States)

Steps from EDPB Recommendations 01/2020.

| Step | Assessment |
|---|---|
| 1. Know the transfer | Agent tracing: full prompts and outputs; data: raw; region: **[OPEN: region]**; sub-processor list: **[OPEN: sub-processors]** |
| 2. Transfer tool | Onward transfer under the clients' SCCs: the recipient accepts the SCCs (or another Chapter V safeguard). **[OPEN: which tool the vendor offers]** |
| 3. Laws and practice of the destination | **[OPEN: government access laws that apply to this vendor, e.g. FISA 702 for US providers]** |
| 4. Supplementary measures | **[OPEN: supplementary measures; the text is sent unmasked]** |
| 5. Procedural steps | If SCCs are changed or another tool is used, check whether Art. 46(3) authorisation is needed |
| 6. Re-evaluate | **[OPEN: date; at least yearly and on vendor changes]** |

## TIA: Brave Search API (United States)

Steps from EDPB Recommendations 01/2020.

| Step | Assessment |
|---|---|
| 1. Know the transfer | Web search by person name; data: raw; region: **[OPEN: region]**; sub-processor list: **[OPEN: sub-processors]** |
| 2. Transfer tool | Onward transfer under the clients' SCCs: the recipient accepts the SCCs (or another Chapter V safeguard). **[OPEN: which tool the vendor offers]** |
| 3. Laws and practice of the destination | **[OPEN: government access laws that apply to this vendor, e.g. FISA 702 for US providers]** |
| 4. Supplementary measures | **[OPEN: supplementary measures; the text is sent unmasked]** |
| 5. Procedural steps | If SCCs are changed or another tool is used, check whether Art. 46(3) authorisation is needed |
| 6. Re-evaluate | **[OPEN: date; at least yearly and on vendor changes]** |

## Points for the reviewer

- **Must do: Prepare SCCs for EU clients who send files to Türkiye.** Türkiye has no EU adequacy decision, so each EU client needs the 2021 SCCs with you and its own transfer impact assessment. As an independent controller you would sign Module One (controller to controller); where a client instructs you as its processor, Module Two. Document 05 has a pre-filled annex and the list of local laws the TIA has to discuss. *(GDPR Art. 46(2)(c); Decision (EU) 2021/914)*
- **Must do: KVKK transfer abroad: OpenAI (API), Anthropic (Claude API), Google Gemini API (free tier), Google Workspace (Gmail, Drive), Supabase (pgvector), LangSmith (LangChain), Brave Search API.** Since 1 June 2024, KVKK m.9 allows transfers abroad on an adequacy decision of the Board, appropriate safeguards (the Board's standard contract, notified to the Authority within 5 business days of signing; binding corporate rules; a written undertaking with the Board's permission) or the occasional-transfer exceptions of m.9/6. Explicit consent is no longer the general route. Masked text is still personal data for you, so the rule applies to it too. *(KVKK m.9; Regulation on transfers abroad (10 Jul 2024))*
- **Note: Anthropic (Claude API): onward transfer of EU clients' data.** Your EU clients' SCCs let you pass their data on to a third country only on the onward-transfer conditions (Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers): typically the recipient accepts the SCCs or another safeguard. The US Data Privacy Framework does not cover a transfer made by a Turkish firm. *(GDPR Art. 44; Decision (EU) 2021/914)*
- **Note: Brave Search API: onward transfer of EU clients' data.** Your EU clients' SCCs let you pass their data on to a third country only on the onward-transfer conditions (Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers): typically the recipient accepts the SCCs or another safeguard. The US Data Privacy Framework does not cover a transfer made by a Turkish firm. *(GDPR Art. 44; Decision (EU) 2021/914)*
- **Note: Google Gemini API (free tier): onward transfer of EU clients' data.** Your EU clients' SCCs let you pass their data on to a third country only on the onward-transfer conditions (Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers): typically the recipient accepts the SCCs or another safeguard. The US Data Privacy Framework does not cover a transfer made by a Turkish firm. *(GDPR Art. 44; Decision (EU) 2021/914)*
- **Note: Google Workspace (Gmail, Drive): onward transfer of EU clients' data.** Your EU clients' SCCs let you pass their data on to a third country only on the onward-transfer conditions (Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers): typically the recipient accepts the SCCs or another safeguard. The US Data Privacy Framework does not cover a transfer made by a Turkish firm. *(GDPR Art. 44; Decision (EU) 2021/914)*
- **Note: LangSmith (LangChain): onward transfer of EU clients' data.** Your EU clients' SCCs let you pass their data on to a third country only on the onward-transfer conditions (Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers): typically the recipient accepts the SCCs or another safeguard. The US Data Privacy Framework does not cover a transfer made by a Turkish firm. *(GDPR Art. 44; Decision (EU) 2021/914)*
- **Note: OpenAI (API): onward transfer of EU clients' data.** Your EU clients' SCCs let you pass their data on to a third country only on the onward-transfer conditions (Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers): typically the recipient accepts the SCCs or another safeguard. The US Data Privacy Framework does not cover a transfer made by a Turkish firm. *(GDPR Art. 44; Decision (EU) 2021/914)*
- **Note: Supabase (pgvector): EU region, United States parent.** Hosting in the EU avoids a Chapter V transfer for storage, but a non-EU parent can be subject to its home country's access laws, and support or sub-processors may sit outside the EU. Check the sub-processor list and the contract's clause on government requests. *(GDPR Arts. 28(2), 44, 48; EDPB Guidelines 05/2021)*

## KVKK (Türkiye)

Since the amendment by Law No. 7499 (in force 1 June 2024) and the Regulation on the Procedures and Principles for the Transfer of Personal Data Abroad (10 July 2024), KVKK m.9 works like GDPR Chapter V: an adequacy decision of the Board, or appropriate safeguards (standard contract in the Board's form, notified to the Authority within 5 business days of signing; binding corporate rules; written undertaking with Board permission), or the occasional-transfer exceptions in m.9/6. Each vendor marked 'KVKK m.9 transfer' needs one of these, separately from its GDPR tool. The EU-US Data Privacy Framework has no effect under KVKK.
