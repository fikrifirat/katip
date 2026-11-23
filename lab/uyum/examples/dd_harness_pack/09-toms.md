# 09 · Technical and organisational measures (GDPR Art. 32, KVKK m.12)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

Status comes from the answers. A free-text answer is shown as given, with the status left for the reviewer; only an explicit yes is shown as 'in place'.

| Area | Measure | Status | Source |
|---|---|---|---|
| Pseudonymisation | Personal data masked on the device before cloud model calls; key stays local (profile: eu) | in place | GDPR Art. 32(1)(a) |
| Encryption | TLS in transit | in place | GDPR Art. 32(1)(a) |
| Encryption | Disks, databases and backups at rest | in place | GDPR Art. 32(1)(a) |
| Keys | API keys and the masking vault key in a secrets store, rotated | **[OPEN: in place?]** | GDPR Art. 32(1)(b) |
| Access | Named accounts, least privilege, per-matter access | answer: Per-matter folders; two named lawyer accounts; status: **[OPEN: reviewer]** | GDPR Art. 32(1)(b), 32(4) |
| Access | Multi-factor login | **[OPEN: in place?]** | GDPR Art. 32(1)(b) |
| Logging | Who and which agent read or sent what, kept 90 days | in place | GDPR Arts. 5(2), 32(1)(b) |
| Agents | Tool allow-list per agent; outside documents treated as data; no autonomous outbound e-mail/upload | answer: Each agent has a fixed tool list; documents are treated as data; status: **[OPEN: reviewer]** | GDPR Art. 32(1)(b) |
| Agents | A lawyer approves every output before it leaves the firm | in place | GDPR Arts. 5(1)(d), 25(1) |
| Resilience | Backups | **[OPEN: in place?]** | GDPR Art. 32(1)(c) |
| Resilience | Restore from backup tested | **[OPEN: in place?]** | GDPR Art. 32(1)(c)-(d) |
| Testing | Regular test of the measures (incl. a prompt-injection test) | **[OPEN: in place?]** | GDPR Art. 32(1)(d) |
| People | Staff act only on instructions; confidentiality undertakings | **[OPEN: in place?]** | GDPR Art. 32(4) |
| People | AI-literacy training | **[OPEN: in place?]** | AI Act Art. 4 |
| Vendors | DPAs and transfer tools (documents 04, 05) | see 04 and 05 | GDPR Arts. 28, 32 |

## Special-category data: KVKK Board decision 2018/10 (m.6/4)

Summary for a checklist; the decision text is authoritative.

| Measure | Status |
|---|---|
| A separate written policy and procedure for special-category data | **[OPEN: in place?]** |
| Regular training of staff who handle it; confidentiality agreements | **[OPEN: in place?]** |
| Clear authorisations and periodic access reviews; access removed at once when a role changes | **[OPEN: in place?]** |
| Electronic: encryption, keys kept separately, logs of all actions, security updates, two-factor for remote access | **[OPEN: in place?]** |
| Physical: adequate physical security and entry controls where it is kept | **[OPEN: in place?]** |
| Transfers: encrypted corporate e-mail or KEP; encrypted portable media; VPN or sFTP between servers | **[OPEN: in place?]** |

## Points for the reviewer

- **Risk to address: Anthropic (Claude API) still sees the facts in health data in case files (e.g. workplace accident opinions).** Masking hides who the person is, not what happened to them. A rare accident or diagnosis plus a date and place can point back to the person. Keep such passages local or generalise them. *(GDPR Arts. 9, 25, 32; Recital 26)*
- **Open question: Security: Backups?** Not answered. *(GDPR Art. 32(1)(c))*
- **Open question: Security: A named person who runs a breach?** Not answered. *(GDPR Arts. 33-34)*
- **Open question: Security: Multi-factor login for staff and admin accounts?** Not answered. *(GDPR Art. 32(1)(b))*
- **Open question: Security: A tested restore from backup?** Not answered. *(GDPR Art. 32(1)(c)-(d))*
- **Note: AI literacy.** Providers and deployers must take measures to support the AI literacy of staff who operate AI systems (Art. 4 as amended in 2026). Keep a short training record. *(AI Act Art. 4)*
- **Note: Masked text is pseudonymised, not anonymous.** Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Describe masking as: detected values are masked and leak-checked before the text leaves the computer. *(GDPR Art. 4(5), Recital 26; CJEU C-413/23 P)*
- **Note: The 'eu' masking profile is beta: names are its weak spot.** On a held-out set of 24 lawyer-style EU documents (221 values; lab/eu/README.md) the rules alone masked about 73% of all values and 64% of names; with the optional name model about 89% and 92%. National IDs were caught in 21 of 24 documents, IBANs and e-mail addresses in all. Only 21% (rules) or 42% (with the name model) of documents had every value masked, so a person must check the output before it is sent. *(GDPR Arts. 25, 32(1)(a))*

## KVKK (Türkiye)

KVKK m.12/1 requires 'technical and administrative measures'. The Board's Personal Data Security Guide lists them in the same groups; this table maps one-to-one.
