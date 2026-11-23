# 07 · Personal data breach procedure (GDPR Arts. 33 and 34, KVKK m.12/5)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

## Who

| Role | Person |
|---|---|
| Breach lead (decides and notifies) | **[OPEN: named person]** |
| Deputy | **[OPEN: deputy]** |
| Technical contact | **[OPEN: who can switch agents off and pull logs]** |

## Clock

| When | What | Source |
|---|---|---|
| 0 h: aware | Someone has reasonable certainty that personal data was lost, disclosed, altered or accessed without authority. Log the time. Contain: revoke keys, pause agents, stop syncs. | Art. 4(12); EDPB 9/2022 |
| < 24 h | Assess: what data, how many people, masked or raw, who could see it, likely consequences. |  |
| ≤ 72 h | Notify the competent supervisory authority unless the breach is unlikely to result in a risk. Late? Give reasons. Information can come in phases. | Art. 33(1), 33(4) |
| ≤ 72 h (KVKK) | Notify the KVKK Board 'en kısa sürede', interpreted as 72 hours, on its breach form. | KVKK m.12/5; Board decision 2019/10 |
| Without undue delay | Tell the people affected if the risk to them is high, in plain language, with what they can do. Not needed if the data was unintelligible to anyone without access, as with proper encryption. Masked text is not unintelligible: it still carries the facts, so masking lowers the risk but does not by itself meet Art. 34(3)(a). | Art. 34(1), 34(3) |
| Always | Record every breach, even unnotified ones: facts, effects, actions, reasons. | Art. 33(5) |

## Who notifies whom

One breach can trigger several of these at once.

| Your role for the data | Notify |
|---|---|
| Controller under the GDPR (Art. 3(1) or 3(2)) | The supervisory authority (Art. 33); people if high risk (Art. 34) |
| Importer of an EU client's data under SCC Module One | The exporting client and the authority named in the SCCs (Clause 8.5 (Module One) / Clause 8.6 (Module Two): security of processing, incl. breach notification) |
| Controller under KVKK | The KVKK Board and the people affected (m.12/5) |

Without an EU establishment the one-stop-shop (Art. 56) does not apply: **[OPEN: which authorities, by where the affected people live]**.

## Processors

Each vendor must tell us without undue delay (Art. 33(2)); see the agreed hours in document 04. Vendor contacts: Anthropic (Claude API): **[OPEN: breach contact]**; Mistral AI: **[OPEN: breach contact]**; Hetzner: **[OPEN: breach contact]**.

## Agent-specific incidents to treat as possible breaches

- An agent e-mailed a document to the wrong client, or with the wrong attachment.
- An agent sent unmasked text to a cloud model that should only get masked text.
- A prompt injection made an agent send data to a tool, URL or e-mail it should not use.
- An agent wrote one client's data into another client's matter or shared memory.
- An API key or the masking key (vault) was exposed.
- A vendor reports a breach of its logs.

## Points for the reviewer

- **Open question: Does the GDPR reach you directly (Art. 3(2))?** If you offer services to people in the EU (individuals, not only EU companies) the GDPR applies directly to that processing and you need an EU representative (Art. 27). If not, it reaches you through your EU clients' SCCs. The answer decides documents 00, 01, 03 and 07. *(GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018)*

## KVKK (Türkiye)

The KVKK Board publishes breach notifications in summary on its website. Data subjects are informed within a reasonable time after they are identified, directly if contact details exist, otherwise by publication.
