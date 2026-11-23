# 05 · International transfers and transfer impact assessment (GDPR Chapter V, KVKK m.9)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## Map of data leaving the EU/EEA or Türkiye

| Vendor | Country | Receives | GDPR route | TIA needed | KVKK m.9 transfer |
|---|---|---|---|---|---|
| Anthropic (Claude API) | United States | masked | onward (client SCCs) | yes | yes |
| Mistral AI | France | masked | EEA | no | yes |
| Hetzner | Germany | masked | EEA | no | yes |
| TOBB Türkiye Ticaret Sicili Gazetesi portal | Türkiye | metadata | same country | no | no |

GDPR routes: **EEA** no transfer; **adequacy** Art. 45 decision; **DPF** a US organisation certified under the EU-US Data Privacy Framework, usable by exporters in the EU/EEA; **SCC** Art. 46(2)(c) standard clauses (Decision 2021/914), which need this assessment; **onward (client SCCs)** a firm outside the EU passes EU clients' data on, governed by Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers of the SCCs it signed with them; **same country** the vendor sits where the controller does.

## EU clients sending data to Türkiye

Each EU client exporting files to you needs the SCCs and its own TIA about Türkiye. Proposed module: **Module One (controller to controller)**. Pre-filled annexes, for the reviewer to complete:

| SCC Annex | Content |
|---|---|
| I.A Data importer | Örnek Hukuk Bürosu, Örnek Mah. 1. Sok. No:1, Beşiktaş, İstanbul; contact kvkk@ornekhukuk.example; role: controller |
| I.B Categories of data subjects | Clients (individuals) and contact persons of corporate clients, Officers, shareholders and signatories of DD target companies, People named in case files (employees, witnesses, counterparties), Lawyers and assistants using the system |
| I.B Categories of data | Names and contact details, National ID and passport numbers, Roles, shareholdings and signing powers, Financial and insolvency information (konkordato, bankruptcy notices), Sanctions, asset-freeze and court records about individuals, Health data in case files (e.g. workplace accident opinions), Login, prompt and agent-action logs |
| I.B Sensitive data and safeguards | See documents 02 and 09; masking before any cloud call where configured |
| I.B Purpose | Take on the client, identify the matter, check conflicts of interest; Find public records (sanctions lists, insolvency and court notices, trade registry gazette) about the target company and the individuals behind it, for the client's DD report; Draft reports and opinions from the client's documents and the screening results; Security logs, abuse detection, troubleshooting |
| I.B Retention | Document 06 |
| I.B Onward recipients | Anthropic (Claude API), Mistral AI, Hetzner, TOBB Türkiye Ticaret Sicili Gazetesi portal |
| II Technical and organisational measures | Document 09 |

**Local laws a TIA about Türkiye has to discuss** (Clause 14: local laws and practices (the TIA); Clause 15: requests from public authorities). Candidates for the reviewing lawyer to confirm and analyse, not a finished assessment:

- CMK m.130 (search of law offices: by a judge's decision, under the prosecutor's supervision, with the bar president or a representative present)
- Law No. 2937 on State Intelligence Services and MİT (powers to request information and documents)
- Law No. 5651 (internet content and traffic data)
- KVKK m.28 (processing by public authorities outside parts of the Law: e.g. national security, criminal investigations)
- Avukatlık Kanunu m.36 (lawyer's duty of secrecy) and m.58 (investigations concerning lawyers)

**[OPEN: conclusion: are there laws or practices that prevent the importer from meeting the SCCs, and which supplementary measures address them?]**

## TIA: Anthropic (Claude API) (United States)

Steps from EDPB Recommendations 01/2020.

| Step | Assessment |
|---|---|
| 1. Know the transfer | Language model for drafting; data: masked; region: **[OPEN: region]**; sub-processor list: yes |
| 2. Transfer tool | Onward transfer under the clients' SCCs: the recipient accepts the SCCs (or another Chapter V safeguard). **[OPEN: which tool the vendor offers]** |
| 3. Laws and practice of the destination | **[OPEN: government access laws that apply to this vendor, e.g. FISA 702 for US providers]** |
| 4. Supplementary measures | Masking on the device before sending (the vendor never gets the key); encryption in transit |
| 5. Procedural steps | If SCCs are changed or another tool is used, check whether Art. 46(3) authorisation is needed |
| 6. Re-evaluate | **[OPEN: date; at least yearly and on vendor changes]** |

## Points for the reviewer

- **Must do: Prepare SCCs for EU clients who send files to Türkiye.** Türkiye has no EU adequacy decision, so each EU client needs the 2021 SCCs with you and its own transfer impact assessment. As an independent controller you would sign Module One (controller to controller); where a client instructs you as its processor, Module Two. Document 05 has a pre-filled annex and the list of local laws the TIA has to discuss. *(GDPR Art. 46(2)(c); Decision (EU) 2021/914)*
- **Must do: KVKK transfer abroad: Anthropic (Claude API), Mistral AI, Hetzner.** Since 1 June 2024, KVKK m.9 allows transfers abroad on an adequacy decision of the Board, appropriate safeguards (the Board's standard contract, notified to the Authority within 5 business days of signing; binding corporate rules; a written undertaking with the Board's permission) or the occasional-transfer exceptions of m.9/6. Explicit consent is no longer the general route. Masked text is still personal data for you, so the rule applies to it too. *(KVKK m.9; Regulation on transfers abroad (10 Jul 2024))*
- **Note: Anthropic (Claude API): onward transfer of EU clients' data.** Your EU clients' SCCs let you pass their data on to a third country only on the onward-transfer conditions (Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers): typically the recipient accepts the SCCs or another safeguard. The US Data Privacy Framework does not cover a transfer made by a Turkish firm. *(GDPR Art. 44; Decision (EU) 2021/914)*

## KVKK (Türkiye)

Since the amendment by Law No. 7499 (in force 1 June 2024) and the Regulation on the Procedures and Principles for the Transfer of Personal Data Abroad (10 July 2024), KVKK m.9 works like GDPR Chapter V: an adequacy decision of the Board, or appropriate safeguards (standard contract in the Board's form, notified to the Authority within 5 business days of signing; binding corporate rules; written undertaking with Board permission), or the occasional-transfer exceptions in m.9/6. Each vendor marked 'KVKK m.9 transfer' needs one of these, separately from its GDPR tool. The EU-US Data Privacy Framework has no effect under KVKK.
