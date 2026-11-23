# 11 · Legitimate-interests assessments (GDPR Art. 6(1)(f))

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

One assessment per activity based on legitimate interests. The three steps follow Art. 6(1)(f) as the CJEU reads it (C-252/21, Meta v Bundeskartellamt): a legitimate interest, processing strictly necessary for it, and the interest not overridden by the person's rights, taking into account their reasonable expectations (Recital 47).

## Client intake and conflict check

| Step | Assessment |
|---|---|
| 1. Interest | Taking on the client and avoiding conflicts of interest; for individual clients the contract (6(1)(b)) also applies. Is it lawful, clear and present? **[OPEN: reviewer]** |
| 2. Necessity | Purpose: Take on the client, identify the matter, check conflicts of interest. Could it be reached with less data or a less intrusive method (e.g. screening companies before people, exact matches instead of fuzzy ones)? **[OPEN: reviewer]** |
| 3a. Who is affected | Clients (individuals) and contact persons of corporate clients |
| 3b. What data | Names and contact details, National ID and passport numbers. Sensitive: National ID and passport numbers |
| 3c. Reasonable expectations | Would these people expect a law firm acting for the other side to process this? **[OPEN: reviewer]** |
| 3d. Safeguards | masking before cloud calls, lawyer review of every output, retention limited to: 10 years after the matter closes |
| Result | **[OPEN: interest prevails / does not prevail, with reasons; date; reviewer]** |

## DD screening of target companies and their people

| Step | Assessment |
|---|---|
| 1. Interest | The client's interest in knowing who it is dealing with before a transaction; limited to people with a control or signing role. Is it lawful, clear and present? **[OPEN: reviewer]** |
| 2. Necessity | Purpose: Find public records (sanctions lists, insolvency and court notices, trade registry gazette) about the target company and the individuals behind it, for the client's DD report. Could it be reached with less data or a less intrusive method (e.g. screening companies before people, exact matches instead of fuzzy ones)? **[OPEN: reviewer]** |
| 3a. Who is affected | Officers, shareholders and signatories of DD target companies |
| 3b. What data | Names and contact details, National ID and passport numbers, Roles, shareholdings and signing powers, Financial and insolvency information (konkordato, bankruptcy notices), Sanctions, asset-freeze and court records about individuals. Sensitive: National ID and passport numbers, Sanctions, asset-freeze and court records about individuals |
| 3c. Reasonable expectations | Would these people expect a law firm acting for the other side to process this? **[OPEN: reviewer]** |
| 3d. Safeguards | masking before cloud calls, lawyer review of every output, retention limited to: Until the DD report is delivered + 2 years, then only the report |
| Result | **[OPEN: interest prevails / does not prevail, with reasons; date; reviewer]** |

## Drafting DD reports and legal opinions

| Step | Assessment |
|---|---|
| 1. Interest | Providing the legal service the client engaged us for, which requires reading the documents it sends. Is it lawful, clear and present? **[OPEN: reviewer]** |
| 2. Necessity | Purpose: Draft reports and opinions from the client's documents and the screening results. Could it be reached with less data or a less intrusive method (e.g. screening companies before people, exact matches instead of fuzzy ones)? **[OPEN: reviewer]** |
| 3a. Who is affected | Clients (individuals) and contact persons of corporate clients, Officers, shareholders and signatories of DD target companies, People named in case files (employees, witnesses, counterparties). Vulnerable: People named in case files (employees, witnesses, counterparties) |
| 3b. What data | Names and contact details, Roles, shareholdings and signing powers, Financial and insolvency information (konkordato, bankruptcy notices), Health data in case files (e.g. workplace accident opinions). Sensitive: Health data in case files (e.g. workplace accident opinions) |
| 3c. Reasonable expectations | Would these people expect a law firm acting for the other side to process this? **[OPEN: reviewer]** |
| 3d. Safeguards | masking before cloud calls, lawyer review of every output, retention limited to: 10 years after the matter closes |
| Result | **[OPEN: interest prevails / does not prevail, with reasons; date; reviewer]** |

## Running and securing the system

| Step | Assessment |
|---|---|
| 1. Interest | Keeping client data secure (Art. 32). Is it lawful, clear and present? **[OPEN: reviewer]** |
| 2. Necessity | Purpose: Security logs, abuse detection, troubleshooting. Could it be reached with less data or a less intrusive method (e.g. screening companies before people, exact matches instead of fuzzy ones)? **[OPEN: reviewer]** |
| 3a. Who is affected | Lawyers and assistants using the system |
| 3b. What data | Login, prompt and agent-action logs |
| 3c. Reasonable expectations | Would these people expect a law firm acting for the other side to process this? **[OPEN: reviewer]** |
| 3d. Safeguards | masking before cloud calls, retention limited to: 90 days |
| Result | **[OPEN: interest prevails / does not prevail, with reasons; date; reviewer]** |


## KVKK (Türkiye)

KVKK m.5/2-f (meşru menfaat) also requires that the processing does not harm the person's fundamental rights and freedoms; the Board's guidance expects a balancing test of the same kind. For client work, m.5/2-e (establishing, exercising or protecting a right) is often the better KVKK basis.
