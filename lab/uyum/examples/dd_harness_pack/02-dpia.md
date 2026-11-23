# 02 · Data protection impact assessment (GDPR Art. 35)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## 1. Is a DPIA required? (Art. 35(1), WP248 rev.01)

| EDPB criterion | Met? | Why |
|---|---|---|
| Evaluation or scoring, including profiling and predicting | unknown | not answered |
| Automated decision-making with legal or similarly significant effect | unknown | not answered |
| Systematic monitoring | unknown | not answered |
| Sensitive data or data of a highly personal nature (Art. 9, Art. 10 data) | yes | data categories: Sanctions, asset-freeze and court records about individuals, Health data in case files (e.g. workplace accident opinions) |
| Data processed on a large scale | no |  |
| Matching or combining datasets | yes | activities combining sources: DD screening of target companies and their people |
| Data concerning vulnerable data subjects (employees, children, patients...) | yes | vulnerable data subjects: People named in case files (employees, witnesses, counterparties) |
| Innovative use or new technological or organisational solutions (EDPB lists AI) | yes | agents built on language models |
| Processing that prevents data subjects from exercising a right or using a service | unknown | not answered |

**At least 4 of 9 criteria met; 4 unanswered.** Two or more usually mean a DPIA is required: treat this document as mandatory and complete it before go-live.

## 2. Systematic description (Art. 35(7)(a))

Three agents help two lawyers prepare due-diligence (DD) reports and legal opinions. An intake agent sorts the client's documents and checks conflicts. A screening agent looks up the target company and its officers and shareholders in Turkish public sources (MASAK asset-freeze lists, ilan.gov.tr, Türkiye Ticaret Sicili Gazetesi) and returns the exact records with links. A drafting agent writes report and opinion drafts with a cloud language model. Documents are masked on the lawyer's computer (Katip Kalkan) before any text goes to a cloud model. A lawyer reviews every output before it goes to the client.

| Agent | What it does | Models and tools | Lawyer reads output first | Output goes to |
|---|---|---|---|---|
| Intake agent | Sorts incoming documents, extracts parties, runs the conflict check | Mistral AI | always | internal |
| Screening agent | Searches public sources by name and shows exact records with links; no scores, no summaries about people | TOBB Türkiye Ticaret Sicili Gazetesi portal; tools: Katip DD (local) | always | internal |
| Drafting agent | Writes report and opinion drafts from masked documents | Anthropic (Claude API), Hetzner; tools: Katip Kalkan masking, Katip Mevzuat, Katip Emsal | always | client |

Purposes and data per activity: document 01.

## 3. Necessity and proportionality (Art. 35(7)(b))

| Question | Answer for this system |
|---|---|
| Is each data item needed for the purpose? (Art. 5(1)(c)) | Names, ID numbers, contact details and addresses are masked on the device before any text goes to a cloud model; detected values are masked and leak-checked before the text leaves the computer. **[OPEN: data items that could be dropped]** |
| Lawful bases | Document 01, per activity; balancing tests in document 11. |
| Retention limits | Document 06. |
| Information to people | Document 03. |
| Rights handling | Document 08. |
| Processors and transfers | Documents 04 and 05. |

## 4. Risks to people (Art. 35(7)(c))

Likelihood and severity before the measures in section 5. Generated from the answers; the reviewer should adjust them.

| # | Risk to the people concerned | Likelihood | Severity | Triggered by |
|---|---|---|---|---|
| 1 | A person is wrongly linked to sanctions, crime or insolvency (false name match), harming reputation or a deal | medium | high | screening against lists by name |
| 2 | The model invents facts or citations about a person and a lawyer relies on them | medium | high | LLM-written drafts |
| 3 | Client or third-party data leaks through a vendor (breach, logs, staff access) | low | high | masked text to cloud vendors |
| 4 | Authorities abroad access data held by a vendor in a country without an adequacy decision | low | high | transfers on SCCs, onward transfers, or without a tool |
| 5 | Authorities in Türkiye access EU clients' data held by the firm itself | **[OPEN: reviewer, from the TIA in document 05]** | high | the firm is the importer of EU data |
| 6 | Prompt injection in a fetched document makes an agent leak or alter data | medium | medium | agents that read outside documents and call tools |
| 7 | People cannot exercise rights because they never learn about the processing | high | medium | data collected about third parties (Art. 14) |
| 8 | Data kept longer than needed in agent memory, vector stores or vendor logs | medium | medium | retention across several stores |

## 5. Measures (Art. 35(7)(d))

Status comes from the answers: a measure is only marked in place when the questionnaire says so.

| Measure | Status | Source |
|---|---|---|
| Mask personal data on the device before cloud model calls; keep the key locally (Katip Kalkan) | in place | GDPR Arts. 25, 32(1)(a) |
| A named lawyer approves every output before it leaves the firm | in place | GDPR Arts. 5(1)(d), 22 |
| Screening shows the source record and link for each hit; no score about a person | **[OPEN: in place?]** | GDPR Art. 5(1)(d); AI Act Art. 5(1)(d) |
| No training on inputs, shortest retention, in each vendor contract | **[OPEN: confirmed per vendor?]** | GDPR Art. 28 |
| Fetched documents treated as data, never instructions; tool allow-list per agent | answer: Each agent has a fixed tool list; documents are treated as data; status: **[OPEN: reviewer]** | GDPR Art. 32(1)(b) |
| Retention enforced in every store, incl. embeddings and logs (document 06) | **[OPEN: in place?]** | GDPR Art. 5(1)(e) |
| Art. 14 notice for third parties, or a documented exemption (document 03) | **[OPEN: in place?]** | GDPR Art. 14 |
| Multi-factor login | **[OPEN: in place?]** | GDPR Art. 32(1)(b) |
| Encryption at rest | in place | GDPR Art. 32(1)(a) |
| Logs of who and which agent accessed what | in place | GDPR Arts. 5(2), 32(1)(b) |

## 6. Residual risk and sign-off

|  |  |
|---|---|
| Residual risk after measures | **[OPEN: reviewer's conclusion: low / medium / high]** |
| Prior consultation needed (Art. 36)? | Only if high residual risk remains: **[OPEN: yes / no]** |
| DPO advice (Art. 35(2)) | **[OPEN: advice, or 'no DPO']** |
| Views of data subjects (Art. 35(9)) | **[OPEN: sought / not appropriate, with reason]** |
| Approved by, date | **[OPEN: name, date]** |
| Review date | **[OPEN: at least yearly, and on any new agent, model or vendor]** |

## Points for the reviewer

- **Must do: Do the DPIA before going live (at least 4 of 9 EDPB criteria met).** Two or more criteria usually mean the processing is likely to result in a high risk. Document 02 is a starting draft; if high residual risk remains after measures, consult the supervisory authority first. *(GDPR Arts. 35(1), 35(7), 36; WP248 rev.01)*
- **Must do: Name the legal authority for criminal-offence data (GDPR Art. 10).** For screening (DD screening of target companies and their people): GDPR Art. 10 allows criminal-offence data only under official authority or where Union or Member State law authorises it with safeguards. For AML-obliged clients that is the national AML law (Regulation (EU) 2024/1624 and the transposition of Directive (EU) 2015/849); otherwise consider screening companies only and keeping individuals to exact list matches. *(GDPR Art. 10)*
- **Risk to address: Anthropic (Claude API) still sees the facts in health data in case files (e.g. workplace accident opinions).** Masking hides who the person is, not what happened to them. A rare accident or diagnosis plus a date and place can point back to the person. Keep such passages local or generalise them. *(GDPR Arts. 9, 25, 32; Recital 26)*
- **Note: Masked text is pseudonymised, not anonymous.** Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Describe masking as: detected values are masked and leak-checked before the text leaves the computer. *(GDPR Art. 4(5), Recital 26; CJEU C-413/23 P)*

## KVKK (Türkiye)

KVKK has no statutory DPIA. Keeping this one also covers the risk analysis the Board's security guide expects under m.12/1.
