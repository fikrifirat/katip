# 10 · EU AI Act note: role, risk class and duties (Regulation (EU) 2024/1689)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

## Role

| Question | Answer |
|---|---|
| Role under the AI Act | deployer (Art. 3(3) provider: develops a system and places it on the market or puts it into service under its own name; Art. 3(4) deployer: uses a system under its authority) |
| Offered to others under own name? | no |
| Models used | Anthropic (Claude API), Mistral AI |
| Territorial reach | Applies to providers and deployers outside the EU where the output is used in the EU (Art. 2(1)(c)) |

Using a vendor's general-purpose model through its API does not make you a GPAI model provider. Fine-tuning one may, if the modification is substantial (Commission GPAI guidelines, July 2025): no.

## Risk class: limited / minimal

| Check | Result | Source |
|---|---|---|
| Prohibited practice? | Check Art. 5(1)(d): no prediction of a person's criminal risk from profiling. Not indicated by the answers. | Art. 5 |
| Annex III high-risk use? | none indicated. Legal research for a law firm's own clients is not listed; point 8(a) covers systems used by or for a judicial authority or in ADR. | Art. 6(2), Annex III |
| Transparency | People who chat with an agent must be told (Art. 50(1)); published AI text on public-interest matters must be disclosed unless human-reviewed (Art. 50(4)). | Art. 50 |
| AI literacy | Training for everyone who operates the system. | Art. 4 |

## Dates

| Date | What applies |
|---|---|
| 1 Aug 2024 | Regulation in force |
| 2 Feb 2025 | Prohibited practices (Art. 5) and AI literacy (Art. 4) apply |
| 2 Aug 2025 | General-purpose AI model obligations (Chapter V), governance, penalties apply |
| 2 Aug 2026 | Most of the Regulation applies, incl. Annex III high-risk systems and Art. 50 transparency |
| 2 Aug 2027 | High-risk systems that are safety components of products under Annex I (Art. 6(1)) |

The Commission's Digital Omnibus proposal (19 Nov 2025) would postpone the Annex III high-risk dates. **[OPEN: check whether it was adopted, and the dates now in force]**

## Professional duties beside the AI Act

Bar rules on confidentiality and competence apply to AI use regardless of the AI Act: check the Türkiye Barolar Birliği and, for EU work, the CCBE guidance on AI use by lawyers. **[OPEN: which bar rules the reviewing lawyer applies]**

## Points for the reviewer

- **Must do: Art. 10 authority for criminal-offence data in 'DD screening of target companies and their people'.** Data on criminal convictions and offences (including sanctions and court records about individuals) may be processed only under the control of official authority or when Union or Member State law authorises it with safeguards. A private screening tool needs to name that law (for AML-obliged clients, the national law implementing Directive (EU) 2015/849). Without it, screen companies, not individuals. *(GDPR Art. 10; KVKK m.6)*
- **Note: AI literacy.** Everyone who operates the agents needs enough AI literacy for their role, in force since 2 Feb 2025. Keep a short training record. *(AI Act Art. 4)*

## KVKK (Türkiye)

Türkiye has no AI act in force; a bill was submitted to the Grand National Assembly in 2024. **[OPEN: current status]** KVKK m.11/1-g already lets a person object to an outcome against them that results exclusively from automated analysis.
