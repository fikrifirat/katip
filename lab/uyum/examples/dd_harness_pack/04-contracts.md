# 04 · Roles and contracts: processors, clients, partners, secrecy (GDPR Arts. 26 and 28)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## Controller or processor towards each client

A law firm giving legal advice normally decides why and how client data is used, so it is a controller (EDPB Guidelines 07/2020, which give lawyers as an example). It is a processor only for work it does strictly on a client's instructions for the client's purposes. The answer decides the contract each client needs:

| If you are… | Contract with the EU client | Your duties | Breach notice goes to |
|---|---|---|---|
| Controller (usual) | SCC Module One if you are outside the EEA; no Art. 28 contract | All controller duties for your own processing | Supervisory authority (Art. 33(1)); under the SCCs also the exporting client |
| Processor (on instructions) | Art. 28(3) contract (a German client calls it AVV); SCC Module Two if outside the EEA | Processor duties: instructions, Art. 30(2) record, help with requests | The client, without undue delay (Art. 33(2)) |

This questionnaire says: **controller**.

## Professional secrecy

| Regime | Applies? |
|---|---|
| Avukatlık Kanunu m.36 (sır saklama) and TBB Meslek Kuralları | yes |
| § 203 StGB and § 43e BRAO (German lawyers may use IT service providers only with written secrecy undertakings) | **[OPEN: does a foreign law firm instruct you?]** |

Each vendor that sees client text must accept confidentiality terms that cover client secrets; the checklist below has a row for it.

## Vendors

Most AI vendors offer a standard DPA; you usually cannot negotiate it, but you must read it against this list and record gaps. A missing term is a reason to choose another tier or vendor, or to mask more before sending.

### Anthropic (Claude API): Language model for drafting

|  |  |
|---|---|
| Role | processor |
| Country / region | United States / **[OPEN: region]** |
| Tier | paid |
| Receives | masked |
| DPA status | accepted_online |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | no |
| Sub-processor list published | yes | *Note from the questionnaire: Example values: confirm the commercial terms, retention and DPF status for the exact contracting entity.*

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

### Mistral AI: Language model for intake sorting

|  |  |
|---|---|
| Role | processor |
| Country / region | France / EU |
| Tier | paid |
| Receives | masked |
| DPA status | available |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | **[OPEN: training on inputs?]** |
| Sub-processor list published | yes | *Note from the questionnaire: Example values: confirm.*

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

### Hetzner: Server for the vector store and agent logs

|  |  |
|---|---|
| Role | processor |
| Country / region | Germany / Falkenstein |
| Tier | **[OPEN: free / paid / enterprise]** |
| Receives | masked |
| DPA status | signed |
| Vendor retention | as configured by us |
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

### TOBB Türkiye Ticaret Sicili Gazetesi portal: Public gazette searched by company name

|  |  |
|---|---|
| Role | controller |
| Country / region | Türkiye / **[OPEN: region]** |
| Tier | **[OPEN: free / paid / enterprise]** |
| Receives | metadata |
| DPA status | **[OPEN: DPA status]** |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | **[OPEN: training on inputs?]** |
| Sub-processor list published | **[OPEN: sub-processor list]** | *Note from the questionnaire: Only the search term (company name, first letters) leaves the computer, under the lawyer's own login.*

This vendor acts as a **controller** for the data it receives, so Art. 28 does not apply. Check its own privacy terms, the purpose it uses the data for, and whether sharing with it is covered by your lawful basis and notice (document 03).

## Points for the reviewer

- **Must do: Prepare SCCs for EU clients who send files to Türkiye.** Türkiye has no EU adequacy decision, so each EU client needs the 2021 SCCs with you and its own transfer impact assessment. As an independent controller you would sign Module One (controller to controller); where a client instructs you as its processor, Module Two. Document 05 has a pre-filled annex and the list of local laws the TIA has to discuss. *(GDPR Art. 46(2)(c); Decision (EU) 2021/914)*
- **Must do: Sign or accept Mistral AI's DPA.** No processing on behalf of the controller without an Art. 28(3) contract. Check it against the checklist in document 04 before accepting. *(GDPR Art. 28(3))*
- **Open question: Does Mistral AI train on what you send?** Check the plan's terms; API and business tiers usually differ from consumer apps. *(GDPR Arts. 5(1)(b), 28(3)(a))*
- **Open question: How long does Anthropic (Claude API) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does Mistral AI keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*

## KVKK (Türkiye)

KVKK has no equivalent of GDPR Art. 28's list of terms, but the controller is jointly liable with the veri işleyen for security (m.12/2), so the Board expects a written contract with security terms. The same checklist works. If the vendor is abroad, the contract alone is not a transfer tool: see document 05.
