# Study 5: Does legal-domain data make Turkish PII detection better on real legal text?

Pre-registration, written 13 Nov 2026 **before** any legal-web data is collected or any model in this study
is trained. The commit that adds this file is the timestamp. Changes after that go in the
"Amendments" section at the bottom, dated, with a reason, and never edit the text above it.

## 1. The question in one paragraph

Katip's models are trained mostly on synthetic documents. They score 99–100% on synthetic tests and much
less on real text. We already showed that adding real Wikipedia sentences closes most of that gap
(BERTurk v1 → v2: 40.7% → 89.8% of names on Wiki NER test). Lawyers do not send Wikipedia. This study
asks whether **real Turkish court decisions, with their anonymised slots filled with realistic synthetic
values**, improve detection on legal text beyond what general real text gives, and whether a test set
built that way is a faithful stand-in for legal text with genuine names.

## 2. Systems

| ID | System | Role |
| --- | --- | --- |
| **B0** | BERTurk v1: `dbmdz/bert-base-turkish-cased` fine-tuned on 8,000 synthetic documents | **Baseline** (what shipped first) |
| **M1** | BERTurk v2: B0's recipe + 17,967 real Wiki NER sentences (PERSON only) | Previous result ("ours" so far) |
| **M2** | M1's recipe + legal-web training split (section 3), all PII types | **This study's model** |
| **M2-vol** | M1's recipe + the same number of *extra synthetic* documents instead of legal-web ones | Volume control for M2 |
| R0 | Katip rules v0.2 (Presidio Analyzer + Turkish recognizers, checksums, name lists) | Rules baseline |
| R1 | Vanilla Presidio 2.x + spaCy `xx_ent_wiki_sm`, default recognizers, no Katip code | Off-the-shelf rules + NER |
| X1 | `savasy/bert-base-turkish-ner-cased` (Turkish NER, PER/LOC/ORG) | Off-the-shelf Turkish NER |
| X2 | `akdeniz27/xlm-roberta-base-turkish-ner` | Off-the-shelf multilingual NER fine-tuned on Turkish |
| X3 | `urchade/gliner_multi_pii-v1` (GLiNER, zero-shot PII labels) | Modern multilingual PII baseline |
| S1–S3 | Katip Tiny (2.6 MB), pii-names-tiny (2.6 MB), DistilBERTurk + real text (68 MB) | Small browser models |

Every Katip system is scored the way the product runs it (rules + model, merge with `trust`). B0, M1, M2
and M2-vol are also scored model-only, so a gain can't hide in the merge step. Off-the-shelf models are
scored model-only and also merged with R0, because that's how a team would use them.

## 3. Data

### 3.1 Sources and licences

| Source | What we take | Licence / legal basis | Use |
| --- | --- | --- | --- |
| Yargıtay decisions (Bedesten API behind mevzuat.adalet.gov.tr) | full text + court, chamber, E./K. no, date | FSEK art. 31: no copyright in court decisions; reproduction is free. Database as a whole may be protected (FSEK add. art. 8), so we publish IDs + rebuild script, not a dump | train / dev / test |
| Danıştay decisions (karararama.danistay.gov.tr) | same | same | train / dev / test |
| AYM individual-application judgments (kararlarbilgibankasi.anayasa.gov.tr) | same; many name the applicant in the title | same; names were published by the court itself | test (real names) |
| TurkishLegalNER (koc-lab, 2022) | 2,918 Yargıtay sentences, PER labels | Apache-2.0 | existing legal test (kept for comparability) |
| TLNER (incidelen, 2026) | 1,887 sentences from Yargıtay, Danıştay, first-instance courts, PER labels, readable names | **CC BY-NC 4.0** | external test **only**; never in training of a shipped model |
| Turkish Wiki NER | real sentences, PERSON | CC BY-SA 4.0 | train (M1, M2), test |
| Legal news sites | | Articles are copyrighted (FSEK protects news text; art. 36 only allows short news summaries with source) | **not used** |
| TurkishLegalBench (Zenodo, 2026) | | CC BY-NC-SA 4.0, no person labels | not used |

Crawling rules: identify ourselves in the User-Agent, one request per second per host, stop on any
CAPTCHA or 429, no login-only content. We use the MIT-licensed `turk-hukuku-ictihat-mcp` client, which
already implements those rules. Raw decision text stays on the machine that crawled it; the repository
gets document IDs, offsets and the scripts.

KVKK: published decisions are anonymised by the courts; every value we insert is synthetic, so the
training set holds no real person's data. The AYM real-name test subset contains names the court
published itself; we store it locally, use it only for evaluation, and publish only IDs and spans.
This is our reading, not legal advice; check it with a KVKK lawyer before releasing any dataset.

### 3.2 Building the legal-web set (slot filling)

1. **Find the slots.** Courts write "...", "…", "X", "XXX", initials ("A.K.", "M. K."), "[AD SOYAD]",
   or drop the value. A detector marks each slot and guesses its type from context (cue words before
   and after: "davacı", "T.C. Kimlik No", "adresi", "tel", "IBAN", "plaka", "doğum tarihi", "Av.").
2. **Fill each slot** with a synthetic value of that type: person names in court casing
   (Title 40%, Ahmet YILMAZ 40%, ALL CAPS 20%), with the following case suffix re-inflected to agree
   (`lab/suffix.py`); TCKN and VKN with valid checksums; IBAN with valid mod-97; Turkish phone formats;
   addresses from the province/district lists; plates; e-mails; dates of birth.
3. **Name pools are split.** Train fills use one pool of first names and surnames; dev and test use a
   disjoint pool (rare and unseen names), so a model can't pass by memorising names.
4. **Residual real names** (judges, lawyers, experts the court left readable) are labelled by an
   ensemble (R0 ∪ M1 at trust 0.5) and, in the test split, every residual name is checked by hand.

### 3.3 Splits (decided now)

* **By document and by case.** All decisions sharing an E. number (same case, other instance) go to
  the same split.
* **By time.** Train: decisions dated ≤ 2023. Dev: 2024. Test: 2025–2026. This also blocks
  near-duplicates of training text from reaching test.
* **By court.** One out-of-domain test: Danıştay decisions are excluded from M2's training in a
  second run (M2-noDAN), to measure transfer to an unseen court.
* **Sizes (targets).** Train 6,000 decisions, dev 500, test 1,000 (≈ 600 Yargıtay, 300 Danıştay,
  100 AYM), plus the AYM real-name subset (≥ 150 judgments, ≥ 1,000 name mentions).
* Test sets are written once, hashed (SHA-256 in `results/05_test_hashes.json`) and opened once,
  after model selection on dev.

## 4. Hypotheses

Each is a claim with a test and a pass rule. "Recall" means entity-level PERSON recall unless stated.

**H1. Synthetic scores overstate real performance.** For B0 and M1, recall on the synthetic blind set
minus recall on each real test set (Wiki NER test, legal-web test, AYM real names, TLNER) is > 0.
*Test:* document-level bootstrap 95% CI of the difference; pass if the lower bound > 0 on every real set.

**H2. Real-text fine-tuning closes the gap.** M1 − B0 recall > 0 on Wiki NER test and on the AYM
real-name set. *Test:* McNemar exact test on paired entity outcomes per seed, and a hierarchical
bootstrap (seeds, then documents) for the mean difference. Pass if p < 0.05 after Holm correction and
the CI lower bound > 0.

**H3. Legal-domain data helps on legal text.** M2 − M1 ≥ **+1.0 point** of recall (smallest effect
we care about) on the legal-web test **and** on the AYM real-name set, with precision falling by no
more than 0.5 points. Two guards:
* H3-vol: M2 − M2-vol > 0, so the gain comes from the domain, not from more data.
* H3-wiki: M2 is non-inferior to M1 on Wiki NER test (difference CI lower bound > −2 points).

**H4. A slot-filled legal test is a faithful proxy.** For every system, recall on the slot-filled
legal-web test and on the AYM real-name set differ by ≤ 3 points, and the two sets rank the systems the
same way (Kendall τ ≥ 0.8). If H4 fails, we say so and the paper's main legal number becomes the
real-name set.

Holm correction runs over the primary family {H2, H3, H3-vol, H4}. α = 0.05.

## 5. Metrics

* **Primary:** PERSON recall on the legal test sets (exact span match, Katip's `matches` rule).
* **Secondary:** precision, F1 and F2 per type (PERSON, TCKN, VKN, PHONE, E-MAIL, IBAN, ADDRESS,
  PLATE, DOB, HEALTH), micro and macro; **leak rate** = share of gold characters left readable
  (a half-masked name counts as a partial leak); **clean-document rate** = share of documents with
  no PII left readable; false names per 1,000 words on name-free legal prose; ms per page.
* Partial-overlap scores are reported next to exact scores, never instead of them.

## 6. Statistics

* 5 seeds (0–4) for every trained system (B0, M1, M2, M2-vol, M2-noDAN). Report mean, SD, min, max.
* 95% CIs: document-level bootstrap, 2,000 resamples; across seeds, hierarchical bootstrap.
* Paired comparisons: McNemar exact on entity outcomes; paired document bootstrap for differences.
* Thresholds (`trust`) are chosen on dev only, from {0.3, 0.5, 0.7, 0.9}, one per system.

## 7. Model selection rule (applied on dev, then frozen)

1. **Hard constraints.** Runs in the browser (ONNX int8, transformers.js, ≤ 150 MB download,
   ≤ 300 ms per page on an Apple-silicon laptop); PERSON precision ≥ 95% on legal dev; recall on the
   synthetic held-out set ≥ 99.5% (no regression on the documents the product already handles).
2. **Objective.** Highest legal-dev PERSON recall (seed mean).
3. **Ties** (overlapping 95% CIs): smaller model, then higher macro-F2 over all PII types.

The selected system is then scored once on every test set.

## 8. Error analysis (planned)

Every miss and false positive of B0, M1 and M2 on 200 sampled legal test documents is tagged with one
or more of: ALL CAPS, case suffix, initials only, next to a title (Av., Hâkim, Bilirkişi), foreign
name, name that is also a word (Gül, Can, Bayram, Barış), split across a line, inside a table or
header, partial span, wrong type. We report counts per category and system, and 10 examples each.

## 9. Threats to validity

* **Slot artefacts.** Filled names sit where courts put "...", so a model could learn the position, not
  the name. H4 and the AYM real-name set test this directly.
* **Silver labels** on residual names in train; test residuals are hand-checked.
* **Ceiling.** The current TurkishLegalNER set is near saturation (B0 98.6%, M1 99.3%), so it can't
  separate strong systems. The new sets use harder fills (rare names, ALL CAPS, suffixes) and more types.
* **Health terms** all score exactly 0.70 under the current model, an artefact of the synthetic
  templates; health is reported separately and isn't part of the primary claim.
* Decisions are not client documents. The final check is 20–30 consented pilot-firm documents,
  labelled on the firm's machine.

## 10. Compute

One BERTurk fine-tune took 28 min on fikri's Mac (MPS). This study needs about 25 runs
(5 systems × 5 seeds), roughly 4 h on a single T4 GPU or 15–20 h on the Mac.

## Amendments

**A1, 13 Nov 2026 (after a 90-document smoke crawl, before any training or scoring).**
1. AYM publishes real names by default (bench, rapporteur, applicant, lawyer in a fixed header); it uses
   initials only when an applicant asked for confidentiality. The AYM real-name set therefore takes its
   gold names from that header (`build_dataset.aym_header_names`), not just the title. Other people named
   in the body are unlabelled, so precision on this set is a lower bound; recall is the measured quantity.
   AYM judgments that fall in the train years are slot-filled *and* keep their header names as labels.
2. Yargıtay's API throttles at one request per second, so its crawl runs at one request per 3 s
   (`--gap 3`). If it still falls short, the Yargıtay share comes from TurkishLegalNER (Apache-2.0).
3. Clarification: the trained models learn PERSON, ADDRESS and HEALTH (as v1 and v2 do). TCKN, IBAN,
   phone, e-mail, plate and birth date are found by the checksum rules, so they are scored at system
   level (rules + model) only.
4. The slot detector was checked against TurkishLegalNER's own tags before use: it marks 99.1% of
   person slots as PERSON at 89.1% precision (`lab/legal/validate_slots.py`).
