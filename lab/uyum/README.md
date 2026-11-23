# Katip Uyum: GDPR document pack for AI agent systems (draft generator)

A firm that builds its own AI agents ("agent harness") and touches EU personal data hits the same wall:
about ten GDPR documents, each asking the same questions about the same data flows. Katip Uyum takes one
short questionnaire about those flows (what data, which agents, which model vendors, where it is stored,
how long) and drafts the whole pack from it, with the article next to every requirement and a KVKK
section in each document.

It **drafts for a lawyer to review**. It does not decide that anything is compliant, and every document
says so. Where an answer is missing it prints **[OPEN: ...]** instead of guessing, and the findings list
says what that answer changes.

```bash
cd lab/uyum
python -m katip_uyum template > my_harness.json        # empty questionnaire
python -m katip_uyum check  examples/dd_harness.json   # findings only: must-dos, risks, open questions
python -m katip_uyum build  examples/dd_harness.json --out pack/
python -m pytest tests -q                              # 13 offline tests
```

Standard library only, offline. The questionnaire describes the system, not any client: no personal data
goes in it.

## The pack

| # | Document | Main source | KVKK counterpart |
|---|---|---|---|
| 00 | Overview: which laws apply and why, all findings, KVKK map | GDPR Art. 3 | |
| 01 | Record of processing activities | GDPR Art. 30 | envanter, VERBİS (m.16) |
| 02 | DPIA, with the 9-criteria screening | GDPR Art. 35, WP248 rev.01 | risk analysis (no statutory DPIA) |
| 03 | Privacy notices: A (Art. 13, given directly) and B (Art. 14, from clients or public sources, with the 14(5) exemption check) | GDPR Arts. 12-14 | aydınlatma metni (m.10) |
| 04 | Per-vendor DPA checklist (Art. 28(3)(a)-(h) plus AI terms: training, retention, abuse monitoring) | GDPR Art. 28 | veri işleyen sözleşmesi (m.12/2) |
| 05 | Transfer map and TIA per non-adequate destination; EU clients' export to a non-EU firm | GDPR Arts. 44-49, EDPB Rec. 01/2020 | yurt dışına aktarım (m.9, 2024) |
| 06 | Retention schedule per store, incl. agent memory, embeddings, vendor logs | GDPR Art. 5(1)(e) | saklama ve imha politikası |
| 07 | Breach procedure with the 72-hour clock and agent-specific incidents | GDPR Arts. 33-34 | m.12/5, Board decision 2019/10 |
| 08 | Data subject request procedure | GDPR Arts. 12, 15-22 | m.11, m.13 |
| 09 | Technical and organisational measures | GDPR Art. 32 | m.12/1 |
| 10 | EU AI Act note: role, risk class, Art. 5(1)(d) check, Art. 4/50 duties, dates | Reg. (EU) 2024/1689 | none in force |

## What the rules catch

`katip_uyum/rules.py` turns answers into findings, each with the facts that triggered it and its source.
Examples from the worked example (`examples/dd_harness.json`, a fictional two-lawyer Istanbul firm doing
DD reports and legal opinions with EU clients):

- **Art. 10**: screening individuals against sanctions and court records is criminal-offence data; a
  private firm needs a Union or Member State law that authorises it, or should screen companies only.
- **DPIA required**: 4 of 9 EDPB criteria (sensitive data, matching sources, vulnerable people in case
  files, LLMs as new technology).
- **EU clients' transfer to Türkiye**: no adequacy decision, so each EU client needs SCCs with the firm.
- **KVKK m.9**: sending even masked text to Anthropic, Mistral or Hetzner is a transfer abroad under the
  2024 rules (standard contract notified within 5 business days).
- **Masking is not anonymisation**: masked text is pseudonymised (Art. 4(5)); health facts in a workplace
  accident file can point back to a person even with the name masked.
- **AI Act**: a deployer, not high-risk for legal research, but Art. 5(1)(d) is checked whenever an agent
  might score people for criminal risk.

The full rendered pack for the example is in `examples/dd_harness_pack/` (a test fails if it goes stale).

## Limits

- Lists that change (adequacy decisions, DPF certifications, AI Act dates under the Digital Omnibus
  proposal, KVKK Board exemptions) are dated in `katip_uyum/law.py` and marked for re-checking.
- The documents are English with KVKK sections in each. Turkish versions of the notices are the next step.
- Vendor facts in the example are placeholders, not checked claims about those vendors.
- No contract text is generated (SCCs, DPAs): the pack points to the official texts and checks them.

`SORULAR.tr.md` is the questionnaire in plain Turkish, to send to a lawyer who runs an agent system.
