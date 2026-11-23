# 05 · International transfers and transfer impact assessment (GDPR Chapter V)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

## Map of data leaving the EU/EEA or Türkiye

| Vendor | Country | Receives | GDPR route | TIA needed | KVKK m.9 transfer |
|---|---|---|---|---|---|
| Anthropic (Claude API) | United States | masked | unknown | yes | yes |
| Mistral AI | France | masked | EEA | no | yes |
| Hetzner | Germany | masked | EEA | no | yes |
| TOBB Türkiye Ticaret Sicili Gazetesi portal | Türkiye | metadata | same country | no | no |

GDPR routes: **EEA** no transfer; **adequacy** Art. 45 decision; **DPF** US organisation certified under the EU-US Data Privacy Framework (check the [list](https://www.dataprivacyframework.gov/list) for the exact legal entity); **SCC** Art. 46(2)(c) standard clauses (Decision 2021/914), which need this assessment; **same country** the vendor sits where the controller does.

## EU clients sending data to Türkiye

For each EU client, sending its files to you is a transfer to a country without an adequacy decision. The client will need the SCCs with you (Module 1 if you act as an independent controller, Module 2 if you process on its behalf), and a TIA covering Türkiye's laws on government access. Prepare one standard answer so each client does not start from zero: **[OPEN: local counsel's summary of access laws]**

## TIA: Anthropic (Claude API) (United States)

Steps from EDPB Recommendations 01/2020.

| Step | Assessment |
|---|---|
| 1. Know the transfer | Language model for drafting; data: masked; region: **[OPEN: region]**; onward transfers: yes |
| 2. Transfer tool | SCCs **[OPEN: module and annexes]** |
| 3. Laws and practice of the destination | **[OPEN: government access laws that apply to this vendor, e.g. FISA 702 for US providers]** |
| 4. Supplementary measures | Masking on the device before sending (the vendor never gets the key); encryption in transit; zero-retention if offered |
| 5. Procedural steps | If SCCs are amended or another tool is used, check whether Art. 46(3) authorisation is needed |
| 6. Re-evaluate | **[OPEN: date; at least yearly and on vendor changes]** |

## Points for the reviewer

- **Must do: Prepare SCCs for EU clients who send files to Türkiye.** Türkiye has no EU adequacy decision, so each EU client needs the 2021 SCCs with you (Module 1 controller-to-controller or Module 2 controller-to-processor) and its own TIA. Have one ready-made set and a standard answer on local government-access laws. *(GDPR Art. 46(2)(c); Decision (EU) 2021/914)*
- **Must do: KVKK transfer abroad: Anthropic (Claude API), Mistral AI, Hetzner.** Since 1 June 2024, KVKK m.9 allows transfers abroad on an adequacy decision of the Board, appropriate safeguards (the Board's standard contract, notified to the Authority within 5 business days of signing; binding corporate rules; written undertakings) or the occasional-transfer exceptions. Explicit consent is no longer the general route. Masked text is still personal data for you, so the rule applies to it too. *(KVKK m.9; Regulation on transfers abroad (10 Jul 2024))*
- **Open question: Which transfer tool covers Anthropic (Claude API) (United States)?** The questionnaire does not say. Check whether it is on the Data Privacy Framework list. *(GDPR Arts. 45-46)*

## KVKK (Türkiye)

Since the amendment by Law No. 7499 (in force 1 June 2024) and the Regulation on the Procedures and Principles for the Transfer of Personal Data Abroad (10 July 2024), KVKK m.9 works like GDPR Chapter V: an adequacy decision of the Board, or appropriate safeguards (standard contract in the Board's form, notified to the Authority within 5 business days of signing; binding corporate rules; written undertaking with Board permission), or the listed occasional-transfer exceptions. Each vendor marked 'KVKK m.9 transfer' needs one of these, separately from its GDPR tool.
