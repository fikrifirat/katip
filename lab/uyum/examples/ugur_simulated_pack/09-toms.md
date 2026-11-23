# 09 · Technical and organisational measures (GDPR Art. 32, KVKK m.12)

**System:** Uğur Hukuk ajan sistemi (simulated) · **Controller:** Uğur Hukuk Bürosu (simulated) · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

Status comes from the answers. A free-text answer is shown as given, with the status left for the reviewer; only an explicit yes is shown as 'in place'.

| Area | Measure | Status | Source |
|---|---|---|---|
| Pseudonymisation | Personal data masked on the device before cloud model calls; key stays local (profile: ai) | not in place | GDPR Art. 32(1)(a) |
| Encryption | TLS in transit | in place | GDPR Art. 32(1)(a) |
| Encryption | Disks, databases and backups at rest | **[OPEN: in place?]** | GDPR Art. 32(1)(a) |
| Keys | API keys and the masking vault key in a secrets store, rotated | answer: API keys in a .env file; status: **[OPEN: reviewer]** | GDPR Art. 32(1)(b) |
| Access | Named accounts, least privilege, per-matter access | not in place (shared logins) | GDPR Art. 32(1)(b), 32(4) |
| Access | Multi-factor login | **[OPEN: in place?]** | GDPR Art. 32(1)(b) |
| Logging | Who and which agent read or sent what, kept **[OPEN: log retention]** | in place | GDPR Arts. 5(2), 32(1)(b) |
| Agents | Tool allow-list per agent; outside documents treated as data; no autonomous outbound e-mail/upload | **[OPEN: in place?]** | GDPR Art. 32(1)(b) |
| Agents | A lawyer approves every output before it leaves the firm | not in place for every agent | GDPR Arts. 5(1)(d), 25(1) |
| Resilience | Backups | in place | GDPR Art. 32(1)(c) |
| Resilience | Restore from backup tested | not in place | GDPR Art. 32(1)(c)-(d) |
| Testing | Regular test of the measures (incl. a prompt-injection test) | not in place | GDPR Art. 32(1)(d) |
| People | Staff act only on instructions; confidentiality undertakings | **[OPEN: in place?]** | GDPR Art. 32(4) |
| People | AI-literacy training | not in place | AI Act Art. 4 |
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

- **Must do: Security: add a tested restore from backup.** Answered 'no'. *(GDPR Art. 32(1)(c)-(d))*
- **Must do: Security: end shared logins and readable API keys.** Shared accounts and keys in a file anyone can read make access untraceable and impossible to revoke for one person. Use named accounts and a secrets store. *(GDPR Art. 32(1)(b), 32(4))*
- **Must do: Art. 9 condition for 'Operating the system'.** This activity touches special-category data (health, religion, ethnicity, ...). Besides an Art. 6 basis it needs an Art. 9(2) condition; for lawyers this is usually 9(2)(f) (legal claims). Under KVKK, the m.6/3 condition (usually m.6/3-d) and the Board's adequate measures (decision 2018/10) apply. *(GDPR Art. 9; KVKK m.6/3, m.6/4)*
- **Must do: KVKK m.6/3 condition for criminal data.** Under KVKK, data on criminal convictions and security measures is special-category data (m.6/1). It needs one of the m.6/3 conditions (for lawyers usually m.6/3-d, establishing or defending a right) and the Board's adequate measures (m.6/4, decision 2018/10). Activities: Email intake, filing and conflict check, DD screening of officers and shareholders, Drafting DD reports and legal opinions, Emailing drafts to clients, Operating the system. *(KVKK m.6/1, m.6/3-d, m.6/4)*
- **Risk to address: 'Sending agent' sends output to the client that a lawyer only sometimes reads first.** Outputs about people that leave the firm unchecked risk wrong facts about a person (Art. 5(1)(d)), the wrong recipient (the most common law-firm breach, Art. 33) and an Art. 22 decision without a person. Either require approval before sending, or limit what can be sent unreviewed and log it. The privacy notice no longer says 'a lawyer reviews every result' while this is open. *(GDPR Arts. 5(1)(d), 22, 25(1), 32(1)(b), 33)*
- **Risk to address: Cloud models see the raw text.** Pseudonymising before the model call (Art. 4(5)) is the cheapest strong measure available here. *(GDPR Arts. 25, 32(1)(a))*
- **Risk to address: EU documents are masked with a Turkish profile.** Kalkan's 'ai' profile is built for Turkish documents and misses EU ID formats (BSN, Steuer-ID, NIR, codice fiscale...) and many non-Turkish names. Use the 'eu' profile (beta) for EU clients' files. *(GDPR Arts. 25, 32(1)(a))*
- **Risk to address: Supabase (pgvector) still sees the facts in forensic and hospital reports, disability rates, indictments, statements, sanctions and asset-freeze listings.** Masking hides who the person is, not what happened to them. A rare accident or diagnosis plus a date and place can point back to the person. Keep such passages local or generalise them. *(GDPR Arts. 9, 25, 32; Recital 26)*
- **Risk to address: Anthropic (Claude API) receives unmasked criminal, id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Risk to address: Google Gemini API (free tier) receives unmasked id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Risk to address: Google Workspace (Gmail, Drive) receives unmasked criminal, id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Risk to address: LangSmith (LangChain) receives unmasked criminal, id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Risk to address: OpenAI (API) receives unmasked criminal, id_number, special data.** Mask before sending (Katip does this on the device) or justify why the raw text is needed. *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*
- **Open question: Security: Encryption at rest?** Not answered. *(GDPR Art. 32(1)(a))*
- **Open question: Security: Multi-factor login for staff and admin accounts?** Not answered. *(GDPR Art. 32(1)(b))*
- **Note: AI literacy.** Providers and deployers must take measures to support the AI literacy of staff who operate AI systems (Art. 4 as amended in 2026). Keep a short training record. *(AI Act Art. 4)*
- **Note: Masked text is pseudonymised, not anonymous.** Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Describe masking as: detected values are masked and leak-checked before the text leaves the computer. *(GDPR Art. 4(5), Recital 26; CJEU C-413/23 P)*

## KVKK (Türkiye)

KVKK m.12/1 requires 'technical and administrative measures'. The Board's Personal Data Security Guide lists them in the same groups; this table maps one-to-one.
