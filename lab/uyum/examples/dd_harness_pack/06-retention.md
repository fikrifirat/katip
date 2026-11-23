# 06 · Retention and deletion policy (GDPR Art. 5(1)(e))

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

Personal data is kept no longer than needed for the purpose (Art. 5(1)(e)). In an agent system data is copied into places people forget: prompts, tool outputs, embeddings, caches, logs, the vendor's own logs, backups. Each row below needs an owner and a deletion method.

## Schedule

| Data / store | Where | Kept for | Deleted how | Encrypted |
|---|---|---|---|---|
| Matter folders (originals) | own computer | 10 years after the matter closes | Secure delete of the matter folder, logged | yes |
| Masking vault (placeholder ↔ real value) | own computer | Deleted with the matter (forget_matter) | Katip forget_matter | yes |
| Local snapshot of public lists and saved notices | own computer | Refreshed weekly; notices kept with the matter | **[OPEN: how deleted]** | **[OPEN: encrypted?]** |
| Vector store of masked document chunks | Hetzner | Deleted with the matter | **[OPEN: how deleted]** | yes |
| Agent-action and access logs | Hetzner | 90 days | Automatic rotation | yes |
| Prompts and outputs kept by Anthropic (Claude API) | Anthropic (Claude API) | **[OPEN: vendor retention]** | by vendor; confirm in DPA | vendor |
| Prompts and outputs kept by Mistral AI | Mistral AI | **[OPEN: vendor retention]** | by vendor; confirm in DPA | vendor |

## Per purpose

| Activity | Retention | Reason / legal basis for the period |
|---|---|---|
| Client intake and conflict check | 10 years after the matter closes | Turkish general limitation period (TBK m.146) for claims against the lawyer |
| DD screening of target companies and their people | Until the DD report is delivered + 2 years, then only the report | **[OPEN: reason]** |
| Drafting DD reports and legal opinions | 10 years after the matter closes | **[OPEN: reason]** |
| Running and securing the system | 90 days | **[OPEN: reason]** |

## Rules

- When a matter closes, the matter's prompts, agent memory and embeddings are deleted with it, not only the documents.
- Deletion runs on a schedule **[OPEN: how often]** and is logged.
- Backups age out within **[OPEN: backup retention]**; restored backups are re-cleaned.
- Legal holds pause deletion for the affected matter only, with a written reason.

## Points for the reviewer

- **Open question: How long does Anthropic (Claude API) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does Mistral AI keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*

## KVKK (Türkiye)

Controllers that must register in VERBİS must also keep a written saklama ve imha politikası and run periodic destruction at most every 6 months (Silme, Yok Etme veya Anonim Hale Getirme Yönetmeliği m.5, m.11). Turkish limitation periods (e.g. TBK m.146: 10 years; VUK m.253: 5 years for books) often set the outer limit for client files.
