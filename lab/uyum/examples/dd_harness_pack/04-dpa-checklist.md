# 04 · Processor agreements: checklist per vendor (GDPR Art. 28)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

Use one copy of this checklist per vendor. Most AI vendors offer a standard DPA; you usually cannot negotiate it, but you must read it against this list and record gaps. A missing term is a reason to choose another tier or vendor, or to mask more before sending.

## Anthropic (Claude API): Language model for drafting

|  |  |
|---|---|
| Role | processor |
| Country / region | United States / **[OPEN: region]** |
| Receives | masked |
| DPA status | accepted_online |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | no |
| Sub-processor list published | yes |
| Notes | Example values: confirm the commercial terms, retention and DPF status for the exact contracting entity. |

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; flows down the same terms; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module, DPF certification) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |

## Mistral AI: Language model for intake sorting

|  |  |
|---|---|
| Role | processor |
| Country / region | France / EU |
| Receives | masked |
| DPA status | available |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | **[OPEN: training on inputs?]** |
| Sub-processor list published | yes |
| Notes | Example values: confirm. |

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; flows down the same terms; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module, DPF certification) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |

## Hetzner: Server for the vector store and agent logs

|  |  |
|---|---|
| Role | processor |
| Country / region | Germany / Falkenstein |
| Receives | masked |
| DPA status | signed |
| Vendor retention | as configured by us |
| Trains on data | no |
| Sub-processor list published | yes |
| Notes |  |

| GDPR | Term | In the DPA? | Clause / note |
|---|---|---|---|
| 28(3) | Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated | ☐ yes ☐ no |  |
| 28(3)(a) | Processes only on documented instructions, including on transfers | ☐ yes ☐ no |  |
| 28(3)(b) | Staff are bound by confidentiality | ☐ yes ☐ no |  |
| 28(3)(c) | Takes all Art. 32 security measures | ☐ yes ☐ no |  |
| 28(2), 28(3)(d), 28(4) | Sub-processors only with prior authorisation; flows down the same terms; you can object to new ones | ☐ yes ☐ no |  |
| 28(3)(e) | Helps you answer data subject requests | ☐ yes ☐ no |  |
| 28(3)(f) | Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36) | ☐ yes ☐ no |  |
| 28(3)(g) | Deletes or returns all data at the end; says how long logs and backups persist | ☐ yes ☐ no |  |
| 28(3)(h) | Makes information available and allows audits; tells you if an instruction breaks the law | ☐ yes ☐ no |  |
| 33(2) | Notifies you of a breach without undue delay (agree a number of hours) | ☐ yes ☐ no |  |
| Ch. V | Transfer tool named (SCC module, DPF certification) with its sub-processor countries | ☐ yes ☐ no |  |
| AI-specific | No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered) | ☐ yes ☐ no |  |
| AI-specific | Abuse-monitoring access by vendor staff described and limited | ☐ yes ☐ no |  |

## TOBB Türkiye Ticaret Sicili Gazetesi portal: Public gazette searched by company name

|  |  |
|---|---|
| Role | controller |
| Country / region | Türkiye / **[OPEN: region]** |
| Receives | metadata |
| DPA status | **[OPEN: DPA status]** |
| Vendor retention | **[OPEN: how long the vendor keeps inputs and outputs]** |
| Trains on data | **[OPEN: training on inputs?]** |
| Sub-processor list published | **[OPEN: sub-processor list]** |
| Notes | Only the search term (company name, first letters) leaves the computer, under the lawyer's own login. |

This vendor acts as a **controller** for the data it receives, so Art. 28 does not apply. Check its own privacy terms, the purpose it uses the data for, and whether sharing with it is covered by your lawful basis and notice (document 03).

## Points for the reviewer

- **Must do: Sign or accept Mistral AI's DPA.** No processing on behalf of the controller without an Art. 28(3) contract. Check it against the checklist in document 04 before accepting. *(GDPR Art. 28(3))*
- **Must do: Prepare SCCs for EU clients who send files to Türkiye.** Türkiye has no EU adequacy decision, so each EU client needs the 2021 SCCs with you (Module 1 controller-to-controller or Module 2 controller-to-processor) and its own TIA. Have one ready-made set and a standard answer on local government-access laws. *(GDPR Art. 46(2)(c); Decision (EU) 2021/914)*
- **Open question: Does Mistral AI train on what you send?** Check the plan's terms; API and business tiers usually differ from consumer apps. *(GDPR Arts. 5(1)(b), 28(3)(a))*
- **Open question: How long does Anthropic (Claude API) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does Mistral AI keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*

## KVKK (Türkiye)

KVKK has no Art. 28 list, but the controller is jointly liable with the veri işleyen for security (m.12/2), so the Board expects a written contract with security terms. The same checklist works. If the vendor is abroad, the contract alone is not a transfer tool: see 05.
