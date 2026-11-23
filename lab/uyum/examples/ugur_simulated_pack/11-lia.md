# 11 · Legitimate-interests assessments (GDPR Art. 6(1)(f))

**System:** Uğur Hukuk ajan sistemi (simulated) · **Controller:** Uğur Hukuk Bürosu (simulated) · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

One assessment per activity based on legitimate interests. The three steps follow Art. 6(1)(f) as the CJEU reads it (C-252/21, Meta v Bundeskartellamt): a legitimate interest, processing strictly necessary for it, and the interest not overridden by the person's rights, taking into account their reasonable expectations (Recital 47).

## OCR and translation of scanned foreign documents

| Step | Assessment |
|---|---|
| 1. Interest | Understanding documents the client sent for the engaged legal service. Is it lawful, clear and present? **[OPEN: reviewer]** |
| 2. Necessity | Purpose: Turn scanned German/Dutch documents into Turkish text. Could it be reached with less data or a less intrusive method (e.g. screening companies before people, exact matches instead of fuzzy ones)? **[OPEN: reviewer]** |
| 3a. Who is affected | Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files, Clients and their contact persons (DE/NL companies, DE individuals). Vulnerable: Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files |
| 3b. What data | Names and contact details, TC kimlik, passport, German Steuer-ID, Dutch BSN, Salary, IBAN, insolvency notices, Forensic and hospital reports, disability rates. Sensitive: TC kimlik, passport, German Steuer-ID, Dutch BSN, Forensic and hospital reports, disability rates |
| 3c. Reasonable expectations | Would these people expect a law firm acting for the other side to process this? **[OPEN: reviewer]** |
| 3d. Safeguards | lawyer review of every output |
| Result | **[OPEN: interest prevails / does not prevail, with reasons; date; reviewer]** |

## DD screening of officers and shareholders

| Step | Assessment |
|---|---|
| 1. Interest | **[OPEN: the interest, stated concretely]**. Is it lawful, clear and present? **[OPEN: reviewer]** |
| 2. Necessity | Purpose: Find sanctions, asset-freeze, insolvency and court records and press about people behind a DD target. Could it be reached with less data or a less intrusive method (e.g. screening companies before people, exact matches instead of fuzzy ones)? **[OPEN: reviewer]** |
| 3a. Who is affected | Officers, shareholders and signatories of DD targets |
| 3b. What data | Names and contact details, TC kimlik, passport, German Steuer-ID, Dutch BSN, Roles, shareholdings, signing powers, Salary, IBAN, insolvency notices, Indictments, statements, sanctions and asset-freeze listings. Sensitive: TC kimlik, passport, German Steuer-ID, Dutch BSN, Indictments, statements, sanctions and asset-freeze listings |
| 3c. Reasonable expectations | Would these people expect a law firm acting for the other side to process this? **[OPEN: reviewer]** |
| 3d. Safeguards | lawyer review of every output, retention limited to: 10 years after the matter closes |
| Result | **[OPEN: interest prevails / does not prevail, with reasons; date; reviewer]** |

## Drafting DD reports and legal opinions

| Step | Assessment |
|---|---|
| 1. Interest | Providing the legal service the client engaged. Is it lawful, clear and present? **[OPEN: reviewer]** |
| 2. Necessity | Purpose: Draft DD reports and expert opinions (workplace accident, negligent homicide). Could it be reached with less data or a less intrusive method (e.g. screening companies before people, exact matches instead of fuzzy ones)? **[OPEN: reviewer]** |
| 3a. Who is affected | Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files. Vulnerable: Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files |
| 3b. What data | Names and contact details, Roles, shareholdings, signing powers, Salary, IBAN, insolvency notices, Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings, Children of deceased workers (dates of birth). Sensitive: Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings, Children of deceased workers (dates of birth) |
| 3c. Reasonable expectations | Would these people expect a law firm acting for the other side to process this? **[OPEN: reviewer]** |
| 3d. Safeguards | lawyer review of every output, retention limited to: 10 years after the matter closes |
| Result | **[OPEN: interest prevails / does not prevail, with reasons; date; reviewer]** |

## Operating the system

| Step | Assessment |
|---|---|
| 1. Interest | **[OPEN: the interest, stated concretely]**. Is it lawful, clear and present? **[OPEN: reviewer]** |
| 2. Necessity | Purpose: Troubleshooting and quality checks via agent traces. Could it be reached with less data or a less intrusive method (e.g. screening companies before people, exact matches instead of fuzzy ones)? **[OPEN: reviewer]** |
| 3a. Who is affected | Firm lawyers, trainee, secretary, Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files. Vulnerable: Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files |
| 3b. What data | Prompts, outputs, agent traces, logins, Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings. Sensitive: Forensic and hospital reports, disability rates, Indictments, statements, sanctions and asset-freeze listings |
| 3c. Reasonable expectations | Would these people expect a law firm acting for the other side to process this? **[OPEN: reviewer]** |
| 3d. Safeguards | **[OPEN: safeguards]** |
| Result | **[OPEN: interest prevails / does not prevail, with reasons; date; reviewer]** |

## Points for the reviewer

- **Must do: Split the legal basis for 'Email intake, filing and conflict check'.** Art. 6(1)(b) covers only processing necessary for a contract with the data subject. These people have no contract with the firm: Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files. Use 6(1)(b) for the contracting client (an individual), and 6(1)(f) with a legitimate-interests test (document 11) for everyone else, including the contact persons of corporate clients. *(GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019)*
- **Must do: Split the legal basis for 'Emailing drafts to clients'.** Art. 6(1)(b) covers only processing necessary for a contract with the data subject. These people have no contract with the firm: Clients and their contact persons (DE/NL companies, DE individuals), Officers, shareholders and signatories of DD targets, Employees of DD targets in client data-room exports, Injured/deceased workers, relatives incl. children, witnesses, suspects in accident files. Use 6(1)(b) for the contracting client (an individual), and 6(1)(f) with a legitimate-interests test (document 11) for everyone else, including the contact persons of corporate clients. *(GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019)*
- **Must do: Write the legitimate-interests test for 'Operating the system'.** Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance against the data subjects' rights and reasonable expectations. Document 11 is the template, pre-filled. *(GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21)*
- **Must do: Write the legitimate-interests test for 'DD screening of officers and shareholders'.** Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance against the data subjects' rights and reasonable expectations. Document 11 is the template, pre-filled. *(GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21)*

## KVKK (Türkiye)

KVKK m.5/2-f (meşru menfaat) also requires that the processing does not harm the person's fundamental rights and freedoms; the Board's guidance expects a balancing test of the same kind. For client work, m.5/2-e (establishing, exercising or protecting a right) is often the better KVKK basis.
