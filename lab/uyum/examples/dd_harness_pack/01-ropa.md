# 01 · Record of processing activities (GDPR Art. 30)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

Controller's record under Art. 30(1). If you also process data **on behalf of clients**, keep a processor's record under Art. 30(2) as well (categories of processing per client, transfers, measures). The Art. 30(5) exemption for organisations under 250 people does not apply where processing is not occasional or includes Art. 9 or Art. 10 data.

## Controller (Art. 30(1)(a))

|  |  |
|---|---|
| Name | Örnek Hukuk Bürosu |
| Address | Örnek Mah. 1. Sok. No:1, Beşiktaş, İstanbul |
| Contact | kvkk@ornekhukuk.example |
| Representative | none |
| DPO | none |

## Activity: Client intake and conflict check

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Take on the client, identify the matter, check conflicts of interest |
| Lawful basis | GDPR Art. 6(1)(b) (performance of a contract with the data subject) |
| Data subjects (c) | Clients and their contact persons |
| Personal data (c) | Names and contact details, National ID and passport numbers |
| Source | data_subject |
| Recipients (d) | none outside the controller |
| Processors and vendors | Mistral AI (France), Katip Kalkan (on the lawyer's computer) (the user's own computer) |
| Transfers outside the EEA (e) | none |
| Where it is stored | Matter folders (originals), Masking vault (placeholder ↔ real value) |
| Retention (f) | 10 years after the matter closes |
| Security (g) | See document 09 (TOMs). |

## Activity: DD screening of target companies and their people

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Find public records (sanctions lists, insolvency and court notices, trade registry gazette) about the target company and the individuals behind it, for the client's DD report |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: The client's interest in knowing who it is dealing with before a transaction; limited to people with a control or signing role |
| Data subjects (c) | Officers, shareholders and signatories of DD target companies |
| Personal data (c) | Names and contact details, National ID and passport numbers, Roles, shareholdings and signing powers, Financial and insolvency information (konkordato, bankruptcy notices), Sanctions, asset-freeze and court records about individuals |
| Source | public |
| Recipients (d) | none outside the controller |
| Processors and vendors | TOBB Türkiye Ticaret Sicili Gazetesi portal (Türkiye), Katip Kalkan (on the lawyer's computer) (the user's own computer) |
| Transfers outside the EEA (e) | none |
| Where it is stored | Local snapshot of public lists and saved notices, Matter folders (originals) |
| Retention (f) | Until the DD report is delivered + 2 years, then only the report |
| Security (g) | See document 09 (TOMs). |

## Activity: Drafting DD reports and legal opinions

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Draft reports and opinions from the client's documents and the screening results |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: Providing the legal service the client engaged us for, which requires reading the documents it sends; Art. 9(2)(f) (establishment, exercise or defence of legal claims) |
| Data subjects (c) | Clients and their contact persons, Officers, shareholders and signatories of DD target companies, People named in case files (employees, witnesses, counterparties) |
| Personal data (c) | Names and contact details, Roles, shareholdings and signing powers, Financial and insolvency information (konkordato, bankruptcy notices), Health data in case files (e.g. workplace accident opinions) |
| Source | client |
| Recipients (d) | none outside the controller |
| Processors and vendors | Anthropic (Claude API) (United States), Hetzner (Germany), Katip Kalkan (on the lawyer's computer) (the user's own computer) |
| Transfers outside the EEA (e) | Anthropic (Claude API) → United States (unknown) |
| Where it is stored | Matter folders (originals), Vector store of masked document chunks, Masking vault (placeholder ↔ real value) |
| Retention (f) | 10 years after the matter closes |
| Security (g) | See document 09 (TOMs). |

## Activity: Running and securing the system

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Security logs, abuse detection, troubleshooting |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: Keeping client data secure (Art. 32) |
| Data subjects (c) | Lawyers and assistants using the system |
| Personal data (c) | Login, prompt and agent-action logs |
| Source | generated |
| Recipients (d) | none outside the controller |
| Processors and vendors | Hetzner (Germany) |
| Transfers outside the EEA (e) | none |
| Where it is stored | Agent-action and access logs |
| Retention (f) | 90 days |
| Security (g) | See document 09 (TOMs). |

## Points for the reviewer

- **Must do: Art. 10 authority for criminal-offence data in 'DD screening of target companies and their people'.** Data on criminal convictions and offences (including sanctions and court records about individuals) may be processed only under the control of official authority or when Union or Member State law authorises it with safeguards. A private screening tool needs to name that law (for AML-obliged clients, the national law implementing Directive (EU) 2015/849). Without it, screen companies, not individuals. *(GDPR Art. 10; KVKK m.6)*
- **Open question: Does the GDPR reach you directly (Art. 3(2))?** If you offer your services to people in the EU (not only to EU companies), the GDPR applies to you directly and you need an EU representative (Art. 27). If not, it reaches you through your EU clients' contracts. The answer decides documents 00, 01, 03 and 07. *(GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018)*

## KVKK (Türkiye)

Keep the same table as the kişisel veri işleme envanteri. VERBİS (KVKK m.16) registration is required unless a Board exemption decision covers the controller; the Board has exempted several groups by decision since 2018, so check the current list for law firms before registering or relying on an exemption.
