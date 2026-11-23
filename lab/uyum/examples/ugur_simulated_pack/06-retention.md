# 06 · Retention and deletion policy (GDPR Art. 5(1)(e), KVKK m.7)

**System:** Uğur Hukuk ajan sistemi (simulated) · **Controller:** Uğur Hukuk Bürosu (simulated) · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

Personal data is kept no longer than needed for the purpose (Art. 5(1)(e)). In an agent system data is copied into places people forget: prompts, tool outputs, embeddings, caches, logs, the vendor's own logs, backups, sent e-mail. Each row below needs an owner and a deletion method.

## Schedule

| Data / store | Where | Kept for | Deleted how | Encrypted |
|---|---|---|---|---|
| Matter folders (originals) on Google Drive | Google Workspace (Gmail, Drive) | 10 years after matter closes | **[OPEN: how deleted]** | yes |
| Mailbox incl. attachments and sent drafts | Google Workspace (Gmail, Drive) | Never deleted | **[OPEN: how deleted]** | yes |
| Vector store of masked chunks of past opinions and DD reports | Supabase (pgvector) | **[OPEN: period]** | **[OPEN: how deleted]** | **[OPEN: encrypted?]** |
| Kalkan masking vault | own computer | With the matter | Katip forget_matter | yes |
| LangSmith traces (full prompts and outputs) | LangSmith (LangChain) | **[OPEN: period]** | **[OPEN: how deleted]** | **[OPEN: encrypted?]** |
| Time Machine backup | own computer | **[OPEN: period]** | **[OPEN: how deleted]** | **[OPEN: encrypted?]** |
| Prompts and outputs kept by OpenAI (API) | OpenAI (API) | **[OPEN: vendor retention]** | by vendor; confirm in DPA | vendor |
| Prompts and outputs kept by Anthropic (Claude API) | Anthropic (Claude API) | **[OPEN: vendor retention]** | by vendor; confirm in DPA | vendor |
| Prompts and outputs kept by Google Gemini API (free tier) | Google Gemini API (free tier) | **[OPEN: vendor retention]** | by vendor; confirm in DPA | vendor |

## Per purpose

| Activity | Retention | Reason / legal basis for the period |
|---|---|---|
| Email intake, filing and conflict check | 10 years after the matter closes | TBK m.146 limitation period |
| OCR and translation of scanned foreign documents | **[OPEN: period]** | **[OPEN: reason]** |
| DD screening of officers and shareholders | 10 years after the matter closes | **[OPEN: reason]** |
| Drafting DD reports and legal opinions | 10 years after the matter closes | **[OPEN: reason]** |
| Emailing drafts to clients | Not deleted | **[OPEN: reason]** |
| Operating the system | **[OPEN: period]** | **[OPEN: reason]** |

## Rules

- When a matter closes, the matter's prompts, agent memory and embeddings are deleted with it, not only the documents.
- Deletion runs on a schedule **[OPEN: how often]** and is logged.
- Backups age out within **[OPEN: backup retention]**; restored backups are re-cleaned.
- Legal holds pause deletion for the affected matter only, with a written reason.

## Points for the reviewer

- **Must do: 'Emailing drafts to clients' keeps data with no end date.** Retention 'Not deleted' is not a limit. Set a period or the criteria that end it. *(GDPR Arts. 5(1)(e), 13(2)(a); KVKK m.7)*
- **Open question: How long is data from 'OCR and translation of scanned foreign documents' kept?** Each purpose needs a retention period or the criteria that set it. *(GDPR Arts. 5(1)(e), 30(1)(f))*
- **Open question: How long is data from 'Operating the system' kept?** Each purpose needs a retention period or the criteria that set it. *(GDPR Arts. 5(1)(e), 30(1)(f))*
- **Open question: How long does Anthropic (Claude API) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does Google Gemini API (free tier) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does OpenAI (API) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*
- **Open question: How long does Supabase (pgvector) keep prompts and outputs?** Include abuse-monitoring logs and backups; ask for zero retention if offered. *(GDPR Arts. 5(1)(e), 28(3)(g))*

## KVKK (Türkiye)

Controllers that must register in VERBİS must also keep a written saklama ve imha politikası and run periodic destruction at most every 6 months (Silme, Yok Etme veya Anonim Hale Getirme Yönetmeliği m.5, m.11). Turkish limitation periods often set the outer limit for client files: TBK m.146 sets 10 years in general, but claims from a mandate (vekâlet) against a lawyer fall under the 5 years of TBK m.147/5; the reviewer should choose with reasons **[OPEN: period and reason]**. VUK m.253: 5 years for books.
