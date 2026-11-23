# 09 · Technical and organisational measures (GDPR Art. 32)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

| Area | Measure | Status | Art. 32 |
|---|---|---|---|
| Pseudonymisation | Personal data masked on the device before cloud model calls; key stays local | in place | 32(1)(a) |
| Encryption | TLS in transit | in place | 32(1)(a) |
| Encryption | Disks, databases and backups at rest | in place | 32(1)(a) |
| Keys | API keys and the masking vault key in a secrets store, rotated | **[OPEN: key management]** | 32(1)(b) |
| Access | Least privilege; per-matter access; named accounts | in place: Per-matter folders; two named lawyer accounts | 32(1)(b) |
| Access | Multi-factor login | **[OPEN: MFA]** | 32(1)(b) |
| Logging | Who and which agent read or sent what, kept 90 days | in place | 32(1)(b), 33(5) |
| Agents | Tool allow-list per agent; outside documents treated as data; no autonomous outbound email/upload | in place: Each agent has a fixed tool list; documents are treated as data | 32(1)(b) |
| Agents | Human review before any output leaves the firm | in place | 32(1)(b) |
| Resilience | Backups and tested restore | **[OPEN: backups]** | 32(1)(c) |
| Testing | Regular test of the measures (incl. a prompt-injection test) | **[OPEN: testing]** | 32(1)(d) |
| People | Confidentiality and AI-literacy training (AI Act Art. 4) | **[OPEN: training]** | 32(4) |
| Vendors | DPAs and transfer tools (documents 04, 05) | see 04/05 | 28, 32 |

## Points for the reviewer

- **Risk to address: Anthropic (Claude API) still sees the facts in health data in case files (e.g. workplace accident opinions).** Masking hides who the person is, not what happened to them. A rare accident or diagnosis plus a date and place can point back to the person. Keep such passages local or generalise them. *(GDPR Arts. 9, 25, 32; Recital 26)*
- **Open question: Security: Backups and restore test?** Not answered. *(GDPR Art. 32(1)(c))*
- **Open question: Security: A named person who runs a breach?** Not answered. *(GDPR Arts. 33-34)*
- **Open question: Security: Multi-factor login for staff and admin accounts?** Not answered. *(GDPR Art. 32(1)(b))*
- **Note: AI literacy.** Everyone who operates the agents needs enough AI literacy for their role, in force since 2 Feb 2025. Keep a short training record. *(AI Act Art. 4)*
- **Note: Masked text is pseudonymised, not anonymous.** Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Do not describe the system as 'anonymous'. *(GDPR Art. 4(5), Recital 26; CJEU C-413/23 P)*

## KVKK (Türkiye)

KVKK m.12/1 requires 'technical and administrative measures'. The Board's Personal Data Security Guide lists them in the same groups; this table maps one-to-one.
