# Katip roadmap

*Updated 21 Nov 2026. The checklist in the [README](README.md#roadmap) says what exists; this page
says in what order we build the rest, how we'll know each piece is done, and why.*

Katip is becoming an open, private legal AI platform for Turkish law firms, and later Dutch
ones: one place to ask a question, open a case, check the law, find precedents and draft, with
masking on the device as the trust layer under all of it. Dates below are for our own planning,
not promises to anyone. How the plan was made: [design note](roadmap/design-2026-11-21.md).

**Moat tags.** Each item says which lasting edge it builds:
`data` lawyer-graded private data · `bench` KVKK-Bench and other public tests ·
`sources` access to Turkish (and Dutch) law and case law · `local` masking on the device ·
`cost` small own models · `reach` distribution through tools lawyers already use · `trust`.

## Now: to 19 Dec 2026

| # | What | Done when | Builds | Status |
|---|------|-----------|--------|--------|
| N1 | **Kalkan 0.4.1**: PDF and UDF output, and a tested update path | Tagged release installs and updates cleanly on a fresh Mac and Windows machine from our marketplace and the `.mcpb` file | `reach` `local` | 0.4.0-beta.1 out |
| N2 | **Citation check before anything leaves the case** (moved up, see research) | Cite-Bench-TR out of draft with its LLM ranking; the checker runs on every Kalkan and relay answer and flags a statute article that doesn't exist, with its catch rate on Cite-Bench reported | `sources` `trust` `bench` | #12 draft |
| N3 | **Precedent search earns its default.** Live Emsal search stays off by default | 20 cases graded by a lawyer with the grading sheet; the on/off decision is written down with those numbers | `data` `sources` | case 1 sheet ready, ungraded |
| N4 | **Pilots that also fill our research gap**: Klasör test mode in real firms, plus interviews | 3 firms ran test mode and shared counts only; 10 lawyer interviews written up (Ozan and Uğur's questions included) | `data` `trust` | test mode merged (#70) |
| N5 | **Algıla** (document-type detection) merged, with a firm setting for what runs on its own and what waits for a lawyer | #69 merged; the setting exists in Kalkan, defaults to "on the device runs, anything leaving the device asks" | `local` `reach` | #69 open |
| N6 | **Bar-rules opinion for *Cebindeki hukuk*** before any public screen | A written opinion from a bar-registered lawyer on Av.K. m.35, advertising rules and the fee tariff | `trust` | not started |

## Next: Jan to Feb 2027

| # | What | Done when | Builds | Status |
|---|------|-----------|--------|--------|
| X1 | **Ask screen that opens a case (*dosya*)**: question plus file plus applicable law; the case keeps sources, history, next step and drafts | 5 pilot lawyers ran a real, masked matter through it and graded the answers | `data` `trust` | mockups v3 (20 Nov) |
| X2 | **Taslak**: drafts from the case's own sources | A draft can't be exported while it has an unchecked citation without a visible warning; 10 drafts graded by lawyers | `data` `sources` | not started |
| X3 | **Klasör for due-diligence data rooms**, signed builds | Signed Mac and Windows builds; one DD pilot masked a real data room | `local` `data` | v0.1 unsigned (#62) |
| X4 | **Katip for iOS**, first real build | Built in Xcode and on TestFlight; mask, send, restore names works on a phone | `local` `reach` | #64 open, never built |
| X5 | **Dutch first slice** out of draft | Dutch masking test set scored; wetten and rechtspraak checks work; one conversation with a Dutch lawyer about the NOvA recommendations | `sources` `local` | #67 draft |
| X6 | **Firm deployment**: on a laptop and on the firm's own server | The compose or Helm package ran on one real firm or test server with outbound traffic blocked | `trust` `local` | written, never run on real hardware |
| X7 | **Letter explained, private client test** (`cep.html`): a Dutch letter is read and masked on the phone, Katip names the type and the deadline rule with its official source, the AI explains it in plain NL/EN/TR, and the page points to Juridisch Loket, Raad voor Rechtsbijstand and NOvA | fikri tested it with his own IND and Dutch letters; letter types and deadlines checked by a Dutch lawyer before anyone else sees it. Not linked from the site, not public (N6 still applies) | `local` `trust` | web page live (#73); iOS screen added; untested on real letters |

## Alongside: all the time

| # | What | Done when (next step) | Builds |
|---|------|-----------------------|--------|
| A1 | **KVKK-Bench**: v0.2 tracks (phone scans, forms with IDs, health) and the paper on arXiv | Phone-scan and forms tracks live on the board; health track after ~7 hours of human review; fikri uploads the paper | `bench` |
| A2 | **Expert loop**: every grade from the gavel button goes into a private, lawyer-graded set | Monthly count of graded items reported; a held-out part never used in training | `data` |
| A3 | **Encrypted compute series** with Belfort | Post 1 published; experiments 1, 3 and 4 run with credits spent on purpose (#61) | `trust` |
| A4 | **ChatGPT relay** and its Hugging Face Space | Space live with share codes; precedent search on there by design | `reach` |
| A5 | **Serving economics**: the masking pipeline behind one endpoint, measured like an inference product ([lab/inference](lab/inference/RESULTS.md)) | First numbers on this Mac (done 24 Nov); next, the same harness on one rented 4-vCPU VM so cloud prices rest on cloud measurements, before any Katip API price is published | `cost` |

## Later: from Mar 2027

- **Cebindeki hukuk**: people send an official letter and a lawyer reviews it at tariff fees,
  with Katip drafts and the gavel. Only after N6, a lawyer in every answer, subscription for
  lawyers, no commission.
- Browser extension. (Excel and e-mail inputs shipped early, 24 Nov 2026.)
- Own small models for research and drafting steps where they match the large ones on our own
  tests (`cost`). Not before the tests exist.

## Research check

Before writing this we checked our reading of the problem against the last 30 days of public
discussion (Hacker News, GitHub, news and bar pages; Reddit was blocked and X needs paid keys, so
lawyers' own talk is missing). Full note with sources: [roadmap/research-2026-11-21.md](roadmap/research-2026-11-21.md).

**Confirmed**

- The code is not the moat. Three "open-source Harvey" clones reached Hacker News this month;
  the top replies say clones haven't dented Harvey or Legora, and that access to case law and the
  firms' own systems is the hard part.
- In Europe, where data is processed decides who gets bought. The Dutch bar's revised AI
  recommendations (Nov 2026) ask firms to keep confidential client data inside the EEA where
  possible and to decide in advance what an AI agent may do on its own.
- Turkish guidance points the same way: TBB (Aug 2026) and KVKK stress confidentiality, human
  oversight and the lawyer's final responsibility.
- Fake citations keep costing lawyers (a Delaware fine on 13 Nov 2026; co-signers sanctioned
  too). These are US cases; we know of no Turkish one.
- Running models on a Mac is becoming normal (Apple's coming local-model app drew 580 points
  and 570 comments on HN), which helps the laptop tier.

**Challenged, and what we changed**

- 78 Turkish bar associations opposed the Justice Ministry's AI petition platform for citizens
  (Apr 2026). *Cebindeki hukuk* keeps a lawyer in every answer and waits for a written bar-rules
  opinion (N6).
- Turkish research and drafting assistants are multiplying (Jupytr, Turbo Law, Leagle, Apilex),
  and one names Claude and ChatGPT as its main rivals. We keep plugging into those tools (N1, A4)
  and lead with what they can't do: masking on the device, verified sources in the case, lawyer
  grades.
- "The tech must win" holds only for the tech a cloud model can't copy: masking before data
  leaves, small own models that make it cheap, and the benchmark others measure against. Hence
  the moat tags.
- Citation checking moved into Now (N2).
