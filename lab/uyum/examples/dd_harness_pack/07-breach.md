# 07 · Personal data breach procedure (GDPR Arts. 33 and 34)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document 00 says what each one changes.

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
| ≤ 72 h | Notify the lead supervisory authority unless the breach is unlikely to result in a risk. Late? Give reasons. Information can come in phases. | Art. 33(1), 33(4) |
| ≤ 72 h (KVKK) | Notify the KVKK Board 'en kısa sürede', interpreted as 72 hours, on its breach form. | KVKK m.12/5; Board decision 2019/10 |
| Without undue delay | Tell the people affected if the risk to them is high, in plain language, with what they can do. Not needed if the data was unintelligible to the recipient (e.g. encrypted, or masked with the key safe) or the risk was neutralised. | Art. 34(1), 34(3) |
| Always | Record every breach, even unnotified ones: facts, effects, actions, reasons. | Art. 33(5) |

## Processors

Each vendor must tell us without undue delay (Art. 33(2)); see the agreed hours in document 04. Vendor contacts: Anthropic (Claude API): **[OPEN: breach contact]**; Mistral AI: **[OPEN: breach contact]**; Hetzner: **[OPEN: breach contact]**.

## Agent-specific incidents to treat as possible breaches

- An agent sent unmasked text to a cloud model that should only get masked text.
- A prompt injection made an agent send data to a tool, URL or email it should not use.
- An agent wrote one client's data into another client's matter or shared memory.
- An API key or the masking key (vault) was exposed.
- A vendor reports a breach of its logs.

## Where to notify

| Authority | How |
|---|---|
| Lead EU supervisory authority | **[OPEN: which one; with no EU establishment, every authority where affected people live (Art. 56 one-stop-shop does not apply)]** |
| KVKK Board | Online breach notification form on kvkk.gov.tr |

## Points for the reviewer

- **Open question: Does the GDPR reach you directly (Art. 3(2))?** If you offer your services to people in the EU (not only to EU companies), the GDPR applies to you directly and you need an EU representative (Art. 27). If not, it reaches you through your EU clients' contracts. The answer decides documents 00, 01, 03 and 07. *(GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018)*

## KVKK (Türkiye)

The KVKK Board publishes breach notifications in summary on its website. Data subjects are informed within a reasonable time after they are identified, directly if contact details exist, otherwise by publication.
