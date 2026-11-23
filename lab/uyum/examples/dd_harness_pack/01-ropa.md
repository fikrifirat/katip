# 01 · Record of processing activities (GDPR Art. 30)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

Controller's record under Art. 30(1). The Art. 30(5) exemption for organisations under 250 people does not apply where processing is not occasional or includes Art. 9 or Art. 10 data.

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
| Role | controller |
| How the GDPR applies | Through EU clients' SCCs for their data; otherwise KVKK only |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: Taking on the client and avoiding conflicts of interest; for individual clients the contract (6(1)(b)) also applies |
| KVKK basis | KVKK m.5/2-e (bir hakkın tesisi, kullanılması veya korunması) |
| Data subjects (c) | Clients (individuals) and contact persons of corporate clients |
| Personal data (c) | Names and contact details, National ID and passport numbers |
| Source | data_subject, client |
| Recipients (d) | **[OPEN: recipients (clients, co-counsel, courts?)]** |
| Processors and vendors | Mistral AI (France), Katip Kalkan (on the lawyer's computer) (the user's own computer) |
| Transfers outside the EEA (e) | none |
| Where it is stored | Matter folders (originals), Masking vault (placeholder ↔ real value) |
| Retention (f) | 10 years after the matter closes |
| Security (g) | See document 09 (TOMs). |

## Activity: DD screening of target companies and their people

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Find public records (sanctions lists, insolvency and court notices, trade registry gazette) about the target company and the individuals behind it, for the client's DD report |
| Role | controller |
| How the GDPR applies | Through EU clients' SCCs for their data; otherwise KVKK only |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: The client's interest in knowing who it is dealing with before a transaction; limited to people with a control or signing role |
| KVKK basis | KVKK m.5/2-e (bir hakkın tesisi, kullanılması veya korunması) |
| Data subjects (c) | Officers, shareholders and signatories of DD target companies |
| Personal data (c) | Names and contact details, National ID and passport numbers, Roles, shareholdings and signing powers, Financial and insolvency information (konkordato, bankruptcy notices), Sanctions, asset-freeze and court records about individuals |
| Source | public |
| Recipients (d) | **[OPEN: recipients (clients, co-counsel, courts?)]** |
| Processors and vendors | TOBB Türkiye Ticaret Sicili Gazetesi portal (Türkiye), Katip Kalkan (on the lawyer's computer) (the user's own computer) |
| Transfers outside the EEA (e) | none |
| Where it is stored | Local snapshot of public lists and saved notices, Matter folders (originals) |
| Retention (f) | Until the DD report is delivered + 2 years, then only the report |
| Security (g) | See document 09 (TOMs). |

## Activity: Drafting DD reports and legal opinions

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Draft reports and opinions from the client's documents and the screening results |
| Role | controller |
| How the GDPR applies | Through EU clients' SCCs for their data; otherwise KVKK only |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: Providing the legal service the client engaged us for, which requires reading the documents it sends; Art. 9(2)(f) (establishment, exercise or defence of legal claims) |
| KVKK basis | KVKK m.5/2-e (bir hakkın tesisi, kullanılması veya korunması) |
| Data subjects (c) | Clients (individuals) and contact persons of corporate clients, Officers, shareholders and signatories of DD target companies, People named in case files (employees, witnesses, counterparties) |
| Personal data (c) | Names and contact details, Roles, shareholdings and signing powers, Financial and insolvency information (konkordato, bankruptcy notices), Health data in case files (e.g. workplace accident opinions) |
| Source | client |
| Recipients (d) | the client (reports, opinions, results) |
| Processors and vendors | Anthropic (Claude API) (United States), Hetzner (Germany), Katip Kalkan (on the lawyer's computer) (the user's own computer) |
| Transfers outside the EEA (e) | Anthropic (Claude API) → United States (onward (client SCCs)) |
| Where it is stored | Matter folders (originals), Vector store of masked document chunks, Masking vault (placeholder ↔ real value) |
| Retention (f) | 10 years after the matter closes |
| Security (g) | See document 09 (TOMs). |

## Activity: Running and securing the system

| Art. 30(1) | Entry |
|---|---|
| Purpose (b) | Security logs, abuse detection, troubleshooting |
| Role | controller |
| How the GDPR applies | Through EU clients' SCCs for their data; otherwise KVKK only |
| Lawful basis | GDPR Art. 6(1)(f) (legitimate interests). Interest: Keeping client data secure (Art. 32) |
| KVKK basis | KVKK m.5/2-f (meşru menfaat) **[OPEN: confirm; for client work m.5/2-e may fit better]** |
| Data subjects (c) | Lawyers and assistants using the system |
| Personal data (c) | Login, prompt and agent-action logs |
| Source | generated |
| Recipients (d) | **[OPEN: recipients (clients, co-counsel, courts?)]** |
| Processors and vendors | Hetzner (Germany) |
| Transfers outside the EEA (e) | none |
| Where it is stored | Agent-action and access logs |
| Retention (f) | 90 days |
| Security (g) | See document 09 (TOMs). |

## Points for the reviewer

- **Must do: Name the legal authority for criminal-offence data (GDPR Art. 10).** For screening (DD screening of target companies and their people): GDPR Art. 10 allows criminal-offence data only under official authority or where Union or Member State law authorises it with safeguards. For AML-obliged clients that is the national AML law (Regulation (EU) 2024/1624 and the transposition of Directive (EU) 2015/849); otherwise consider screening companies only and keeping individuals to exact list matches. *(GDPR Art. 10)*
- **Open question: Does the GDPR reach you directly (Art. 3(2))?** If you offer services to people in the EU (individuals, not only EU companies) the GDPR applies directly to that processing and you need an EU representative (Art. 27). If not, it reaches you through your EU clients' SCCs. The answer decides documents 00, 01, 03 and 07. *(GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018)*
- **Note: Is a sanctions listing or pending case special-category data under KVKK?** KVKK m.6/1 names 'ceza mahkûmiyeti ve güvenlik tedbirleri'. A sanctions or asset-freeze listing, or a pending prosecution, is not a conviction; whether it falls under m.6 is not settled. Treat it with m.6 safeguards until Board practice says otherwise, and record the choice. Activities: DD screening of target companies and their people. *(KVKK m.5, m.6/1)*

## KVKK (Türkiye)

The Turkish inventory is [01-envanter.tr.md](01-envanter.tr.md). VERBİS (m.16): see the KVKK map in document 00.
