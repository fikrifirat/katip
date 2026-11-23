# 02 · Data protection impact assessment (GDPR Art. 35)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

## 1. Is a DPIA required? (Art. 35(1), WP248 rev.01)

| EDPB criterion | Met? | Why |
|---|---|---|
| Evaluation or scoring, including profiling and predicting | no |  |
| Automated decision-making with legal or similarly significant effect | no |  |
| Systematic monitoring | no |  |
| Sensitive data or data of a highly personal nature (Art. 9, Art. 10 data) | yes | data categories: Sanctions, asset-freeze and court records about individuals, Health data in case files (e.g. workplace accident opinions) |
| Data processed on a large scale | no |  |
| Matching or combining datasets | yes | activities combining sources: DD screening of target companies and their people |
| Data concerning vulnerable data subjects (employees, children, patients...) | yes | vulnerable data subjects: People named in case files (employees, witnesses, counterparties) |
| Innovative use or new technological or organisational solutions (EDPB lists AI) | yes | agents built on language models |
| Processing that prevents data subjects from exercising a right or using a service | no |  |

**4 of 9 criteria met.** Two or more usually mean a DPIA is required: treat this document as mandatory and complete it before go-live.

## 2. Systematic description (Art. 35(7)(a))

Three agents help two lawyers prepare due-diligence (DD) reports and legal opinions. An intake agent sorts the client's documents and checks conflicts. A screening agent looks up the target company and its officers and shareholders in Turkish public sources (MASAK asset-freeze lists, ilan.gov.tr, Türkiye Ticaret Sicili Gazetesi) and returns the exact records with links. A drafting agent writes report and opinion drafts with a cloud language model. Documents are masked on the lawyer's computer (Katip Kalkan) before any text goes to a cloud model. A lawyer reviews every output before it goes to the client.

| Agent | What it does | Models and tools | Human review | Output goes to |
|---|---|---|---|---|
| Intake agent | Sorts incoming documents, extracts parties, runs the conflict check | Mistral AI | yes | internal |
| Screening agent | Searches public sources by name and shows exact records with links; no scores, no summaries about people | TOBB Türkiye Ticaret Sicili Gazetesi portal; tools: Katip DD (local) | yes | internal |
| Drafting agent | Writes report and opinion drafts from masked documents | Anthropic (Claude API), Hetzner; tools: Katip Kalkan masking, Katip Mevzuat, Katip Emsal | yes | client |

Purposes and data per activity: document 01.

## 3. Necessity and proportionality (Art. 35(7)(b))

| Question | Answer for this system |
|---|---|
| Is each data item needed for the purpose? (Art. 5(1)(c)) | Names, ID numbers, contact details and addresses are masked on the device before any text goes to a cloud model; placeholders come back and are restored locally. **[OPEN: data items that could be dropped]** |
| Lawful bases | Client intake and conflict check: GDPR Art. 6(1)(b) (performance of a contract with the data subject); DD screening of target companies and their people: GDPR Art. 6(1)(f) (legitimate interests). Interest: The client's interest in knowing who it is dealing with before a transaction; limited to people with a control or signing role; Drafting DD reports and legal opinions: GDPR Art. 6(1)(f) (legitimate interests). Interest: Providing the legal service the client engaged us for, which requires reading the documents it sends; Art. 9(2)(f) (establishment, exercise or defence of legal claims); Running and securing the system: GDPR Art. 6(1)(f) (legitimate interests). Interest: Keeping client data secure (Art. 32) |
| Retention limits | Document 06. |
| Information to people | Document 03. |
| Rights handling | Document 08. |
| Processors and transfers | Documents 04 and 05. |

## 4. Risks to people (Art. 35(7)(c))

Likelihood and severity: low / medium / high, before the measures in section 5. The reviewer should adjust these; they are generated from the answers.

| # | Risk to the people concerned | Likelihood | Severity | Triggered by |
|---|---|---|---|---|
| 1 | A person is wrongly linked to sanctions, crime or insolvency (false match), harming reputation or a deal | medium | high | screening against public lists by name |
| 2 | The model invents facts or citations about a person and a lawyer relies on them | medium | high | LLM-written drafts |
| 3 | Client or third-party data leaks through a vendor (breach, logs, staff access) | low | high | masked text to cloud vendors |
| 4 | Foreign authorities access data at a vendor in a country without adequate protection | low | high | transfers on SCCs or without a tool |
| 5 | Prompt injection in a fetched document makes an agent leak or alter data | medium | medium | agents that read outside documents and call tools |
| 6 | People cannot exercise rights because they never learn about the processing | high | medium | data collected about third parties (Art. 14) |
| 7 | Data kept longer than needed in agent memory, vector stores or vendor logs | medium | medium | retention across several stores |

## 5. Measures (Art. 35(7)(d))

- Mask personal data on the device before any cloud model call; keep the re-identification key locally (Katip Kalkan). Art. 25, 32(1)(a).
- A named lawyer reviews every output before it leaves the firm; agents draft, people decide. Art. 22, AI Act Art. 14 spirit.
- Show the source record and link for every screening hit; no score or summary about a person. Art. 5(1)(d).
- Zero-retention or shortest-retention API settings and no training on inputs, confirmed in each vendor contract. Art. 28.
- Treat fetched documents as data, never instructions; agents' tools limited to what the task needs. Art. 32.
- Retention schedule enforced in every store, including embeddings and logs (document 06). Art. 5(1)(e).
- Art. 14 notice for third parties, or a documented exemption (document 03).
- Encryption at rest (in place).
- Logs of who and which agent accessed what (in place).

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

- **Must do: Art. 10 authority for criminal-offence data in 'DD screening of target companies and their people'.** Data on criminal convictions and offences (including sanctions and court records about individuals) may be processed only under the control of official authority or when Union or Member State law authorises it with safeguards. A private screening tool needs to name that law (for AML-obliged clients, the national law implementing Directive (EU) 2015/849). Without it, screen companies, not individuals. *(GDPR Art. 10; KVKK m.6)*
- **Must do: Do the DPIA before going live (4 of 9 EDPB criteria met).** Two or more criteria usually mean the processing is likely to result in a high risk. Document 02 is a starting draft; if high residual risk remains after measures, consult the supervisory authority first. *(GDPR Arts. 35(1), 35(7), 36; WP248 rev.01)*
- **Risk to address: Anthropic (Claude API) still sees the facts in health data in case files (e.g. workplace accident opinions).** Masking hides who the person is, not what happened to them. A rare accident or diagnosis plus a date and place can point back to the person. Keep such passages local or generalise them. *(GDPR Arts. 9, 25, 32; Recital 26)*
- **Note: Masked text is pseudonymised, not anonymous.** Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Do not describe the system as 'anonymous'. *(GDPR Art. 4(5), Recital 26; CJEU C-413/23 P)*

## KVKK (Türkiye)

KVKK has no statutory DPIA. Keeping this one also covers the risk analysis the Board's security guide expects under m.12/1.
