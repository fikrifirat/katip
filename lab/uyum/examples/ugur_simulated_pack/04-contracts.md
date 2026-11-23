# 04 · Roles and contracts: processors, clients, partners, secrecy (GDPR Arts. 26 and 28)

**System:** Uğur Hukuk ajan sistemi (simulated) · **Controller:** Uğur Hukuk Bürosu (simulated) · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## Controller or processor towards each client

A law firm giving legal advice normally decides why and how client data is used, so it is a controller (EDPB Guidelines 07/2020, which give lawyers as an example). It is a processor only for work it does strictly on a client's instructions for the client's purposes. The answer decides the contract each client needs:

| If you are… | Contract with the EU client | Your duties | Breach notice goes to |
|---|---|---|---|
| Controller (usual) | SCC Module One if you are outside the EEA; no Art. 28 contract | All controller duties for your own processing | Supervisory authority (Art. 33(1)); under the SCCs also the exporting client |
| Processor (on instructions) | Art. 28(3) contract (a German client calls it AVV); SCC Module Two if outside the EEA | Processor duties: instructions, Art. 30(2) record, help with requests | The client, without undue delay (Art. 33(2)) |

This questionnaire says: **both**. **[OPEN: list which clients and matters are processor work]**

## Partners and co-counsel

| Firm | Country | Role | Arrangement |
|---|---|---|---|
| Düsseldorf correspondent firm (fictional) | Germany | joint controller | **[OPEN: arrangement in place?]** |

For joint controllers, the Art. 26 arrangement must say: who gives the notices (Arts. 13-14), who answers requests (Arts. 15-22), who notifies breaches, and a contact point; its essence must be available to the people concerned (Art. 26(2)). People can exercise their rights against either firm (Art. 26(3)).

## Professional secrecy

| Regime | Applies? |
|---|---|
| Avukatlık Kanunu m.36 (sır saklama) and TBB Meslek Kuralları | yes |
| § 203 StGB and § 43e BRAO (German lawyers may use IT service providers only with written secrecy undertakings) | § 203 StGB / § 43e BRAO when the Düsseldorf firm instructs |

Each vendor that sees client text must accept confidentiality terms that cover client secrets; the checklist below has a row for it.

## Vendors

Most AI vendors offer a standard DPA; you usually cannot negotiate it, but you must read it against this list and record gaps. A missing term is a reason to choose another tier or vendor, or to mask more before sending.

### OpenAI (API): LLM for intake and drafting

|  |  |
|---|---|
| Role | processor |
| Country / region | United States / **[OPEN: region]** |
| Tier | **[OPEN: free / paid / enterprise]** |
| Receives | raw |
| DPA status | accepted_online |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | no |
| Sub-processor list published | **[OPEN: sub-processor list]** | *Note from the questionnaire: Raw from intake, masked from drafting (expressed with agents[].sends).*

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; same terms flow down; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |
| Secrecy | Confidentiality undertaking covering client secrets, incl. staff and sub-processors | ☐ yes ☐ no |  |

### Anthropic (Claude API): LLM for screening and drafting

|  |  |
|---|---|
| Role | processor |
| Country / region | United States / **[OPEN: region]** |
| Tier | **[OPEN: free / paid / enterprise]** |
| Receives | raw |
| DPA status | accepted_online |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | no |
| Sub-processor list published | **[OPEN: sub-processor list]** |

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; same terms flow down; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |
| Secrecy | Confidentiality undertaking covering client secrets, incl. staff and sub-processors | ☐ yes ☐ no |  |

### Google Gemini API (free tier): OCR and translation

|  |  |
|---|---|
| Role | controller (answered: processor; a free tier without a DPA gives no Art. 28 terms) |
| Country / region | United States / **[OPEN: region]** |
| Tier | free |
| Receives | raw |
| DPA status | none |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | yes |
| Sub-processor list published | **[OPEN: sub-processor list]** | *Note from the questionnaire: Free tier: persona believes content may be used to improve products and reviewed by humans.*

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; same terms flow down; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |
| Secrecy | Confidentiality undertaking covering client secrets, incl. staff and sub-processors | ☐ yes ☐ no |  |

### Google Workspace (Gmail, Drive): Email and file storage

|  |  |
|---|---|
| Role | processor |
| Country / region | United States / **[OPEN: region]** |
| Tier | **[OPEN: free / paid / enterprise]** |
| Receives | raw |
| DPA status | accepted_online |
| Vendor retention | as configured by us (never deleted) |
| Trains on data | no |
| Sub-processor list published | yes |

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; same terms flow down; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |
| Secrecy | Confidentiality undertaking covering client secrets, incl. staff and sub-processors | ☐ yes ☐ no |  |

### Supabase (pgvector): Vector store

|  |  |
|---|---|
| Role | processor |
| Country / region | Germany / Frankfurt (US company) (parent: United States) |
| Tier | **[OPEN: free / paid / enterprise]** |
| Receives | masked |
| DPA status | **[OPEN: DPA status]** |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | **[OPEN: training on inputs?]** |
| Sub-processor list published | **[OPEN: sub-processor list]** |

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; same terms flow down; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |
| Secrecy | Confidentiality undertaking covering client secrets, incl. staff and sub-processors | ☐ yes ☐ no |  |

### LangSmith (LangChain): Agent tracing: full prompts and outputs

|  |  |
|---|---|
| Role | **[OPEN: processor or controller]** |
| Country / region | United States / **[OPEN: region]** |
| Tier | **[OPEN: free / paid / enterprise]** |
| Receives | raw |
| DPA status | **[OPEN: DPA status]** |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | **[OPEN: training on inputs?]** |
| Sub-processor list published | **[OPEN: sub-processor list]** |

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; same terms flow down; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |
| Secrecy | Confidentiality undertaking covering client secrets, incl. staff and sub-processors | ☐ yes ☐ no |  |

### Brave Search API: Web search by person name

|  |  |
|---|---|
| Role | **[OPEN: processor or controller]** |
| Country / region | United States / **[OPEN: region]** |
| Tier | **[OPEN: free / paid / enterprise]** |
| Receives | raw |
| DPA status | **[OPEN: DPA status]** |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | **[OPEN: training on inputs?]** |
| Sub-processor list published | **[OPEN: sub-processor list]** |

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; same terms flow down; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |
| Secrecy | Confidentiality undertaking covering client secrets, incl. staff and sub-processors | ☐ yes ☐ no |  |

## Points for the reviewer

- **Must do: Prepare SCCs for EU clients who send files to Türkiye.** Türkiye has no EU adequacy decision, so each EU client needs the 2021 SCCs with you and its own transfer impact assessment. As an independent controller you would sign Module One (controller to controller); where a client instructs you as its processor, Module Two. Document 05 has a pre-filled annex and the list of local laws the TIA has to discuss. *(GDPR Art. 46(2)(c); Decision (EU) 2021/914)*
- **Must do: Joint-controller arrangement with Düsseldorf correspondent firm (fictional).** Where you and another firm decide purposes and means together, Art. 26 requires a transparent arrangement on who does what (notices, requests), and its essence must be made available to the people concerned. Document 04 has a checklist. *(GDPR Art. 26(1)-(2))*
- **Must do: Settle, per client and matter, whether you are controller or processor.** A lawyer giving legal advice usually decides why and how client data is used, which makes the firm a controller (EDPB Guidelines 07/2020 give lawyers as an example). Where a client nevertheless wants an Art. 28 contract (e.g. a German client asking for an AVV) for work done strictly on its instructions, you are its processor for that work: you then need the Art. 28(3) terms with the client, a processor's record (Art. 30(2)) and breach notices to the client, not to the authority (Art. 33(2)). Document 04 has a section on this. *(GDPR Arts. 4(7)-(8), 28(3), 30(2); EDPB Guidelines 07/2020)*
- **Must do: Stop sending client data to Google Gemini API (free tier).** This tier offers no Art. 28 terms and may use your inputs for its own purposes. The vendor is then not your processor but a separate recipient, which needs its own legal basis (and an Art. 9 condition for health data) and is hard to square with lawyers' secrecy. Move to a paid tier with a DPA, or keep this step on your own computer. *(GDPR Arts. 28(1), 28(3), 28(10), 9(1); Avukatlık Kanunu m.36)*
- **Open question: Is there a DPA with Supabase (pgvector)?** A processor may act only under a contract with the Art. 28(3) terms. *(GDPR Art. 28(3))*
- **Open question: Is Brave Search API a processor or a controller?** It decides whether you need an Art. 28 DPA or a controller-to-controller arrangement. Search APIs and tracing tools often receive the full text of queries and prompts. *(GDPR Arts. 4(7)-(8), 28)*
- **Open question: Is LangSmith (LangChain) a processor or a controller?** It decides whether you need an Art. 28 DPA or a controller-to-controller arrangement. Search APIs and tracing tools often receive the full text of queries and prompts. *(GDPR Arts. 4(7)-(8), 28)*
- **Open question: Does Supabase (pgvector) train on what you send?** Check the plan's terms; API and business tiers usually differ from consumer apps. *(GDPR Arts. 5(1)(b), 28(3)(a))*
- **Open question: How long does Anthropic (Claude API) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does Google Gemini API (free tier) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does OpenAI (API) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does Supabase (pgvector) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*

## KVKK (Türkiye)

KVKK has no equivalent of GDPR Art. 28's list of terms, but the controller is jointly liable with the veri işleyen for security (m.12/2), so the Board expects a written contract with security terms. The same checklist works. If the vendor is abroad, the contract alone is not a transfer tool: see document 05.
