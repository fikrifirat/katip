# 02 · Data protection impact assessment (GDPR Art. 35)

**System:** Uğur Hukuk ajan sistemi (simulated) · **Controller:** Uğur Hukuk Bürosu (simulated) · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## 1. Is a DPIA required? (Art. 35(1), WP248 rev.01)

| EDPB criterion | Met? | Why |
|---|---|---|
| Evaluation or scoring, including profiling and predicting | yes | profiling or per-person labels: DD screening of officers and shareholders |
| Automated decision-making with legal or similarly significant effect | unknown | not answered |
| Systematic monitoring | unknown | not answered |
| Sensitive data or data of a highly personal nature (Art. 9, Art. 10 data) | yes | data categories: Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings |
| Data processed on a large scale | unknown | not answered |
| Matching or combining datasets | yes | activities combining sources: DD screening of officers and shareholders |
| Data concerning vulnerable data subjects (employees, children, patients...) | yes | vulnerable data subjects: Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files |
| Innovative use or new technological or organisational solutions (EDPB lists AI) | yes | agents built on language models |
| Processing that prevents data subjects from exercising a right or using a service | unknown | not answered |

**At least 5 of 9 criteria met; 4 unanswered.** Two or more usually mean a DPIA is required. The system is already in use, so this DPIA is overdue: Art. 35(1) asks for it before the processing starts. Complete it now, and pause the highest-risk flows until it is done.

## 2. Systematic description (Art. 35(7)(a))

Five agents help a small Istanbul law firm (two lawyers, one trainee, one secretary) with due-diligence reports on Turkish targets for German and Dutch clients and with legal opinions on workplace accidents and negligent homicide. An intake agent reads the firm's Gmail, files attachments to Google Drive and checks conflicts with OpenAI. An OCR/translation agent sends scanned German/Dutch documents unmasked to Google Gemini (free tier). A screening agent searches Turkish and international sanctions lists and the web for officers and shareholders and gives each person a red/amber/green label with Claude. A drafting agent writes reports and opinions from Kalkan-masked text with OpenAI or Anthropic and a Supabase vector store. A sending agent emails approved drafts to clients, and in urgent cases emails a 'pre-draft, pending lawyer approval' without a lawyer having read it.

| Agent | What it does | Models and tools | Lawyer reads output first | Output goes to |
|---|---|---|---|---|
| Intake agent | Reads Gmail, files attachments, classifies, conflict check | OpenAI (API) (raw), Google Workspace (Gmail, Drive), LangSmith (LangChain); tools: Gmail API, Google Drive | no | internal |
| OCR/translation agent | Sends scanned PDFs unmasked to Gemini for OCR and translation | Google Gemini API (free tier), LangSmith (LangChain) | always | internal |
| Screening agent | Searches lists and web by name; red/amber/green label and summary per person | Anthropic (Claude API), Brave Search API, LangSmith (LangChain); tools: MASAK, ilan.gov.tr, TSG, EU/UN/OFAC lists | always | client |
| Drafting agent | Writes drafts from masked text with RAG over past opinions | OpenAI (API) (masked), Anthropic (Claude API) (masked), Supabase (pgvector), LangSmith (LangChain); tools: Katip Kalkan | always | client |
| Sending agent | Emails approved drafts; in urgent cases emails pre-drafts before lawyer review | Google Workspace (Gmail, Drive); tools: Gmail API | sometimes | client |

Purposes and data per activity: document 01.

## 3. Necessity and proportionality (Art. 35(7)(b))

| Question | Answer for this system |
|---|---|
| Is each data item needed for the purpose? (Art. 5(1)(c)) | Raw text goes to: OpenAI (API), Anthropic (Claude API), Google Gemini API (free tier), Google Workspace (Gmail, Drive), LangSmith (LangChain), Brave Search API. **[OPEN: why raw text is necessary for each]** **[OPEN: data items that could be dropped]** |
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
| 2 | A per-person risk label is wrong, unexplained, or reused beyond the matter | medium | high | per-person labels |
| 3 | The model invents facts or citations about a person and a lawyer relies on them | medium | high | LLM-written drafts |
| 4 | An unreviewed output goes to the wrong recipient or states something wrong about a person | medium | high | agents without consistent review: Sending agent |
| 5 | Client or third-party data leaks through a vendor (breach, logs, staff access) | medium | high | raw text to cloud vendors |
| 6 | Authorities abroad access data held by a vendor in a country without an adequacy decision | low | high | transfers on SCCs, onward transfers, or without a tool |
| 7 | Authorities in Türkiye access EU clients' data held by the firm itself | **[OPEN: reviewer, from the TIA in document 05]** | high | the firm is the importer of EU data |
| 8 | Prompt injection in a fetched document makes an agent leak or alter data | medium | medium | agents that read outside documents and call tools |
| 9 | People cannot exercise rights because they never learn about the processing | high | medium | data collected about third parties (Art. 14) |
| 10 | Children's data (e.g. dependants in compensation claims) is exposed or kept too long | low | high | children in case files |
| 11 | Data kept longer than needed in agent memory, vector stores or vendor logs | medium | medium | retention across several stores |

## 5. Measures (Art. 35(7)(d))

Status comes from the answers: a measure is only marked in place when the questionnaire says so.

| Measure | Status | Source |
|---|---|---|
| Mask personal data on the device before cloud model calls; keep the key locally (Katip Kalkan) | not in place | GDPR Arts. 25, 32(1)(a) |
| A named lawyer approves every output before it leaves the firm | not in place for every agent | GDPR Arts. 5(1)(d), 22 |
| Screening shows the source record and link for each hit; no score about a person | not in place (per-person labels) | GDPR Art. 5(1)(d); AI Act Art. 5(1)(d) |
| No training on inputs, shortest retention, in each vendor contract | not in place: Google Gemini API (free tier) | GDPR Art. 28 |
| Fetched documents treated as data, never instructions; tool allow-list per agent | **[OPEN: in place?]** | GDPR Art. 32(1)(b) |
| Retention enforced in every store, incl. embeddings and logs (document 06) | **[OPEN: in place?]** | GDPR Art. 5(1)(e) |
| Art. 14 notice for third parties, or a documented exemption (document 03) | **[OPEN: in place?]** | GDPR Art. 14 |
| Multi-factor login | **[OPEN: in place?]** | GDPR Art. 32(1)(b) |
| Encryption at rest | **[OPEN: in place?]** | GDPR Art. 32(1)(a) |
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

- **Must do: Write the legitimate-interests test for 'Operating the system'.** Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance against the data subjects' rights and reasonable expectations. Document 11 is the template, pre-filled. *(GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21)*
- **Must do: Write the legitimate-interests test for 'DD screening of officers and shareholders'.** Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance against the data subjects' rights and reasonable expectations. Document 11 is the template, pre-filled. *(GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21)*
- **Must do: Do the DPIA before going live (at least 5 of 9 EDPB criteria met).** Two or more criteria usually mean the processing is likely to result in a high risk. Document 02 is a starting draft; if high residual risk remains after measures, consult the supervisory authority first. *(GDPR Arts. 35(1), 35(7), 36; WP248 rev.01)*
- **Must do: Name the legal authority for criminal-offence data (GDPR Art. 10).** For screening (Email intake, filing and conflict check, DD screening of officers and shareholders, Emailing drafts to clients, Operating the system): GDPR Art. 10 allows criminal-offence data only under official authority or where Union or Member State law authorises it with safeguards. For AML-obliged clients that is the national AML law (Regulation (EU) 2024/1624 and the transposition of Directive (EU) 2015/849); otherwise consider screening companies only and keeping individuals to exact list matches. For legal advice and defence (Drafting DD reports and legal opinions): the criminal facts are the subject of the service, so 'screen less' is no answer. Art. 10 has no legal-claims exception of its own; identify the Member State law that authorises lawyers to process such data (many have one), or record why the GDPR does not reach this activity directly (see Art. 3 in document 00). *(GDPR Art. 10)*
- **Must do: Art. 9 condition for 'Operating the system'.** This activity touches special-category data (health, religion, ethnicity, ...). Besides an Art. 6 basis it needs an Art. 9(2) condition; for lawyers this is usually 9(2)(f) (legal claims). Under KVKK, the m.6/3 condition (usually m.6/3-d) and the Board's adequate measures (decision 2018/10) apply. *(GDPR Art. 9; KVKK m.6/3, m.6/4)*
- **Must do: Stop sending client data to Google Gemini API (free tier).** This tier offers no Art. 28 terms and may use your inputs for its own purposes. The vendor is then not your processor but a separate recipient, which needs its own legal basis (and an Art. 9 condition for health data) and is hard to square with lawyers' secrecy. Move to a paid tier with a DPA, or keep this step on your own computer. *(GDPR Arts. 28(1), 28(3), 28(10), 9(1); Avukatlık Kanunu m.36)*
- **Risk to address: 'DD screening of officers and shareholders' puts a risk label on people.** A per-person label (e.g. red/amber/green) is profiling (Art. 4(4)): it is personal data in its own right, must be accurate (Art. 5(1)(d)), and is exactly what a person will ask about under Art. 15. Write down the logic, show the source records next to it, and keep it internal. If the label predicts whether someone will commit an offence, see the AI Act Art. 5(1)(d) finding. *(GDPR Arts. 4(4), 5(1)(d), 15, 22)*
- **Risk to address: 'Sending agent' sends output to the client that a lawyer only sometimes reads first.** Outputs about people that leave the firm unchecked risk wrong facts about a person (Art. 5(1)(d)), the wrong recipient (the most common law-firm breach, Art. 33) and an Art. 22 decision without a person. Either require approval before sending, or limit what can be sent unreviewed and log it. The privacy notice no longer says 'a lawyer reviews every result' while this is open. *(GDPR Arts. 5(1)(d), 22, 25(1), 32(1)(b), 33)*
- **Risk to address: Cloud models see the raw text.** Pseudonymising before the model call (Art. 4(5)) is the cheapest strong measure available here. *(GDPR Arts. 25, 32(1)(a))*
- **Risk to address: Supabase (pgvector) still sees the facts in forensic and hospital reports, disability rates, indictments, statements, sanctions and asset-freeze listings.** Masking hides who the person is, not what happened to them. A rare accident or diagnosis plus a date and place can point back to the person. Keep such passages local or generalise them. *(GDPR Arts. 9, 25, 32; Recital 26)*
- **Risk to address: Anthropic (Claude API) receives unmasked criminal, id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Risk to address: Google Gemini API (free tier) receives unmasked id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Risk to address: Google Workspace (Gmail, Drive) receives unmasked criminal, id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Risk to address: LangSmith (LangChain) receives unmasked criminal, id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Risk to address: OpenAI (API) receives unmasked criminal, id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Open question: Does any label or score predict whether a person will offend? (AI Act Art. 5(1)(d)).** The questionnaire leaves this open while the system labels people. A list match shown with its source is outside the prohibition; a score of how likely someone is to offend, based on profiling, is not. Describe what the label means and how it is computed. *(AI Act Art. 5(1)(d); GDPR Art. 4(4))*
- **Open question: How many people's data a year, and is that large scale?** Scale feeds the DPIA, the DPO question and Art. 27(2). *(GDPR Arts. 35(3), 37(1); Recital 91)*
- **Note: Masked text is pseudonymised, not anonymous.** Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Describe masking as: detected values are masked and leak-checked before the text leaves the computer. *(GDPR Art. 4(5), Recital 26; CJEU C-413/23 P)*
- **Note: Deceased people.** The GDPR does not protect the data of deceased persons (Recital 27), but their relatives' data in the same file is protected, and some Member States and KVKK practice go further. Keep the same safeguards. *(GDPR Recital 27)*

## KVKK (Türkiye)

KVKK has no statutory DPIA. Keeping this one also covers the risk analysis the Board's security guide expects under m.12/1.
