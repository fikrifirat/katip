# KVKK-Bench-TR: a public leaderboard for Turkish personal-data masking

Draft design, 13 Nov 2026. It grows out of Study 5 (`DESIGN.md`): the study's test splits become the
leaderboard's hidden test, so the study and the benchmark are built once.

## Why

Several Turkish PII models are now public (for example `ytu-ce-cosmos/modernbert-tr-pii-ner`,
`ersanbil/kvkk-pii-ner`, `OpenMed/OpenMed-PII-Turkish-…`, Katip's own), but there is no shared test
to compare them. Each one reports scores on its own data, usually synthetic, and Study 5 shows how far
synthetic scores can sit from real ones (BERTurk v1: 100% synthetic, 40.7% real). A KVKK-specific benchmark
also asks what a lawyer asks: **was anything left readable**, and were the art. 6 special categories caught?

## Tracks (by kind of document)

| Track | Source | Gold | Size target (hidden test) |
| --- | --- | --- | --- |
| `court` | Yargıtay + Danıştay decisions 2025–26, anonymised slots filled with synthetic values | inserted values + hand-checked residual names | 1,000 docs |
| `court-real` | AYM judgments with the names the court published (bench, applicant, lawyer) | header names, hand-checked | 150 docs |
| `petition` | dilekçe, ihtarname, icra, vekaletname (Katip generators, new templates written for the test) | generator | 200 |
| `contract` | kira and iş sözleşmesi, aydınlatma metni, fatura | generator | 150 |
| `health` | epikriz, bilirkişi raporu, sick-leave letters | generator; art. 6 health | 150 |
| `correspondence` | e-posta, mesaj, mektup, tutanak, zabıt | generator | 200 |
| `scan` | the same documents printed and scanned (PDF/PNG); input is the image, OCR is the submitter's job | generator offsets mapped through the reference text | 150 |
| `prose` | Turkish Wiki NER test sentences (CC BY-SA 4.0), PERSON only | human (Altinok 2023) | 654 sentences |
| `special` | KVKK art. 6 categories in context: health, religion, ethnicity, political opinion, union, sexual life, criminal record, biometric/genetic, association, dress | generator + hand check | 300 |

Generators for the hidden test use templates and name pools that are never released, so a model can't
learn the test's style from the public dev set.

## Entity types

General: PERSON, TCKN, VKN, PHONE, EMAIL, IBAN, CREDIT_CARD, ADDRESS, PLATE, BIRTH_DATE, IP_ADDRESS.
KVKK art. 6 special categories: HEALTH, RELIGION, ETHNICITY, POLITICAL, UNION, SEXUAL_LIFE,
CRIMINAL_RECORD, BIOMETRIC_GENETIC, PHILOSOPHICAL, ASSOCIATION, DRESS. These are scored separately, and a
model that doesn't claim a type gets recall 0 for it, never "n/a".

## Metrics (recall first)

* **KVKK-F2**, the ranking score: F2 (recall weighted 4×) per track over all types, then the mean over tracks,
  so a large track can't drown a small one.
* Shown next to it: recall, precision, **leak rate** (share of gold PII characters left readable: a
  half-masked name counts as half a leak), **clean-document rate** (documents with nothing left readable),
  art. 6 recall, strict exact-span recall, false names per 1,000 words on name-free text, model size,
  ms per page, and a **runs locally** badge (no network calls during inference).
* Matching: Katip's rule (the prediction covers the value, or is at least half of it), and the type must
  match. Strict scores are always reported beside it.
* 95% CIs by document bootstrap. Two entries are only ranked apart if the paired bootstrap says so; ties
  share a rank.

`bench_score.py` implements all of this. On Katip's synthetic blind set, Katip Rules gets KVKK-F2 99.0 but
only 60–100% clean documents per style: it finds every value but leaves edges readable. That gap is exactly
what the leak rate is for.

## Splits and the hidden test

* **Public dev** (released with gold, CC BY 4.0): about 20% of each track. Use it for tuning.
* **Hidden test**: inputs and gold stay private. Two ways to submit:
  1. **Model submission** (ranked): a Hugging Face model repo, or a Docker image, with a small `predict(text) -> spans`
     entry point. The leaderboard Space runs it on the hidden test, offline. Nobody sees the test text.
  2. **Prediction file** (unranked, "self-reported"): JSONL predictions on the public dev inputs.
* **Refresh**: the court tracks get new decisions every year (2027 test = 2027 decisions), and the generated tracks
  get new templates. Old test sets are released when they retire. A canary string in every file lets crawlers
  and model trainers exclude the data.

## Submission format

```
predictions.jsonl  {"id": "court-000123", "spans": [[start, end, "PERSON"], [start, end, "TCKN"], ...]}
```
Offsets are character offsets into the given `text` (Python string indexing). Types are from the list above;
anything else is ignored. A missing `id` counts as no predictions for that document.

## Hosting

* HF Space `f1k/kvkk-bench-tr` (Gradio, leaderboard table + submit tab), the same pattern as the Open LLM
  Leaderboard: a submission writes a request to a queue dataset; a scheduled evaluator runs it and writes a
  row to `f1k/kvkk-bench-results` (public).
* Hidden test in a **private** dataset repo `f1k/kvkk-bench-hidden`, read by the evaluator with a token
  stored as a Space secret.
* Day-one rows: Katip Rules, Katip Tiny, pii-names-tiny, BERTurk v1/v2/legal (Study 5), vanilla Presidio,
  kvkk-pii (MIT regex library), savasy BERTurk NER, XLM-R Turkish NER, GLiNER multi PII, the three Turkish PII
  models above. Each with model size and the runs-locally badge.

## Licences

Court text: no copyright (FSEK art. 31); we release slot-filled documents, so no real personal data
except names AYM itself published. Generated documents: ours, CC BY 4.0. Wiki NER: CC BY-SA 4.0, kept as its own
track. TLNER (CC BY-NC) is not redistributed; scores on it are reported in the paper only.

## What it adds to the current work

Nothing in the crawl or the training changes. Three new pieces:
1. **Track split.** `build_dataset.py` writes the 2025–26 court decisions; the leaderboard keeps them
   hidden instead of publishing them with the study.
2. **New generators.** Test-only templates for the generated tracks, plus an art. 6 `special` generator:
   today's synthetic sets hold only 26 health terms and 1 union mention.
3. **Inter-annotator check.** Two people label the same 100 hidden-test documents and we report Cohen's κ,
   which a benchmark paper needs.

Possible venues: SIGTURK (the ACL workshop on Turkic languages), LREC-COLING (resource papers), or a
NeurIPS Datasets & Benchmarks track submission once there are external entries.
