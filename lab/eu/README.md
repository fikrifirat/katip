# EU / GDPR profile: rules and measured recall

The `eu` profile in Katip Kalkan is the `ai` (Yapay zekâ ile paylaşım) profile plus the rules in
`connector/katip_kalkan/eu.py`. Rules only: no model was trained or changed for this.

| Type | How | Checksum |
| --- | --- | --- |
| National ID: NL BSN, DE Steuer-ID, FR NIR, IT codice fiscale, ES DNI/NIE, BE national number, PL PESEL | shape + checksum; a bare 9-digit BSN or 11-digit PESEL only next to a cue | 11-proef, ISO 7064 MOD 11,10 + digit rule, mod 97 key (2A/2B), check letter, mod 23 letter, mod 97 (pre/post 2000), weighted mod 10 |
| Any number after an ID cue (BSN, Steuer-ID, NIR, DNI, PESEL, "national number" ...) | masked even when no checksum fits (typo, OCR slip): fail closed | - |
| IBAN | every SEPA country, length per country | mod 97 |
| VAT id | country prefix + the country's shape (27 EU states + XI) | shape only |
| Phone | +30..+49, +35x..+38x, +420..423 (and 00); national numbers only after Tel./Telefon/Tél./... | - |
| Passport, ID card, driving licence, residence permit | number after the word, in 8 languages | - |
| Date of birth | date after born / geboren / né le / nato il / nacido el / geboren op / urodzony | - |
| Street address | Hauptstraße 5, Am Markt 3, 12 rue de la Paix, Via Roma 12, Calle Mayor, 5, 221B Baker Street, Flat 3 ...; postcode and town after it | - |
| Names | after a title (Herr, Frau, M., Mme, Sig., Sr., dhr., Mr, Dr, Sayın, κ. ...), in a form field (Name:, Nom :, Kläger:, Imię i nazwisko: ...), under a closing, in a role ("the seller X", "zwischen X und Y"), in a mail header, from an e-mail address (anna.kowalska@...), by surname ending (-ska, -escu, -ssen, -opoulos, -ainen ...), initial + surname (J. Müller), chat speakers and handles (@lucia.moretti), table columns (first_name, Nachname ...), or starting with one of ~900 European/Slavic/Arabic first names; a surname found once is masked everywhere | - |
| Special categories (GDPR Art. 9/10) | health, religion, union, political, sex life, biometric/genetic, criminal record keywords in 6 languages; flagged and masked, skipped on Turkish text | - |
| Optional: names by model | `KATIP_EU_NER=gliner` adds GLiNER multi-PII (`urchade/gliner_multi_pii-v1`) for names only; off by default | - |

The Turkish (KVKK) rules still run first, so Turkish names, T.C. kimlik etc. are masked as before. On text that
is not Turkish, the Turkish name tagger's one-word guesses ("Schaden", "Invoice") and guesses holding an
abbreviation ("DSGVO, EuGH") are dropped unless they contain a Turkish name.

## Results

`synth_eu.py` writes two synthetic sets of 300 letters (50 per language: en, de, fr, it, es, nl; 9 values
each = 2,700 values). A value counts as caught only when every character of it is masked. Numbers are recall
with 95% Wilson intervals. Files: `results/*.json`.

**Blind set** (`--blind --seed 9091`): written before any tuning, other phrasing (prose sentences, no labelled
lines), other streets, other names; half of the first names are not in the list. Run once, then the misses
were read and five general bugs fixed (a `geb.` cue, "26 de abril de 1995", "passport (N123...)", a cue
followed by a few words, "Flat 3,"); the second line is after those fixes and is no longer blind.

| Blind set, recall | KVKK `ai` | `eu`, first run | `eu`, after fixes |
| --- | --- | --- | --- |
| All values | 22.5% | 87.0% [85.6–88.2] | 94.2% [93.2–95.0] |
| National IDs (checksum valid) | 0.7% | 100% (267/267) | 100% |
| National IDs with a typo, after a cue | 0% | 51.5% (17/33) | 100% (33/33) |
| IBAN, e-mail, phone, VAT id | 100 / 100 / 0 / 0.7% | 100% each | 100% each |
| Address | 0% | 89.7% | 100% |
| Date of birth | 0% | 74.0% | 100% |
| Passport | 0% | 78.0% | 100% |
| **Names, all bare in a sentence** | 1.0% | 46.3% | 47.7% [42.1–53.3] |
| names whose first name is in the list | 2.0% | 92.7% | 95.3% |
| names whose first name is not in the list | 0% | **0%** (0/150) | **0%** (0/150) |

**Dev set** (`--seed 2611`, labelled lines, the set the rules were tuned on; optimistic): 99.4% of values,
names 94.7% (title, form field and closing 100%; bare in a sentence 76.1%).

**False positives on real text** (`fp_gdpr_text.py`): all 99 GDPR articles in English and German (198 pages,
424k characters, no personal data, not used for tuning): KVKK `ai` masks 117 spans (German nouns such as
"Zertifizierung", "Behörden" read as names); `eu` masked **0** in #82; with the special-category keywords added since, 3 (health words, see below). 30 short negatives in `data/eu_negatives.jsonl`
(GDPR prose, case numbers, ECLIs, amounts): 0 spans, but those were seen while tuning.

Turkish documents: on the 80 `docs/samples` texts and the test petition, `eu` masks everything `ai` masks
(checked in `connector/tests/test_eu.py`).

## Lawyer-style documents (the "Uğur" rounds)

The synthetic letters above have one shape. To test documents a cross-border lawyer actually sees, an agent
playing Uğur (a Turkish lawyer doing DD and legal opinions for foreign clients) wrote three rounds of synthetic
documents without seeing the code: DD reports, SPAs, DPAs, board minutes, court filings, criminal complaints,
breach notifications, KYC and cover e-mails, CSV/HR exports, Slack and WhatsApp chats, invoices, Turkish
dilekçe and mütalaa, in 15 languages. Each round was scored once on unseen code, then its misses were read and
general rules added. A round is held out only until it is scored; after that it is a dev set.

| Recall, all values (95% CI) | KVKK `ai` | `eu` rules | `eu` + GLiNER names |
| --- | --- | --- | --- |
| Round 1, 48 docs / 474 values, held out | - | 78.7% | - |
| Round 2, 48 docs / 486 values, held out | - | 71.0% [66.8–74.8] | 79.8% [76.0–83.2] |
| **Round 3, 24 docs / 221 values, held out (final code)** | 30.3% | **72.9% [66.6–78.3]** | **89.1% [84.4–92.6]** |
| names only, round 3 (127 names) | - | 63.8% | 92.1% |
| documents with every value masked, round 3 | - | 20.8% | 41.7% |
| strings that must stay readable (case nos, statutes, courts), round 3 | - | 85/87 kept | 85/87 kept |
| Round 1 / round 2 after their fixes (dev, optimistic) | - | 95.4% / 82.9% | - / 91.6% |

Round 3 by type (rules): IBAN 12/12, e-mail 10/10, national ID 21/24, phone 8/9, address 16/21, date of birth
10/13, names 81/127. The model layer only changes names.

**Trade-off of the name model.** GLiNER multi-PII (`urchade/gliner_multi_pii-v1`, Apache-2.0) adds about 16
points on held-out lawyer documents, almost all of it names without any cue. It costs PyTorch plus a 1.1 GB
model and about 0.5 s per document on CPU, which is why it is off by default. False positives on the 424k
characters of GDPR text: rules 3 spans (the words "diagnosis", "Diagnostik" and "Behinderung"
flagged as Art. 9 health data), with GLiNER 0–1 extra name spans in our runs. A torch-free ONNX port of a small multilingual model is the obvious
follow-up.

## What this means

* ID numbers, IBANs, VAT ids, phones, e-mails, passports, dates of birth and European-style addresses are
  covered well on these synthetic letters, including mistyped IDs next to a cue.
* **Names are the gap.** With rules only, a name with no title, role, form field, closing, known first name or
  telling surname ending is missed: 64% of names on held-out lawyer documents. The optional model layer brings
  that to 92%. Rules alone will not close it.
* About one held-out lawyer document in five (rules) or two in five (with the model) came out with every value
  masked. Have a person read the masked text before it is sent anywhere.
* Synthetic data only, written by people or agents who know what is being tested. No real EU document has been scored. Before anyone relies on it:
  a small gold set of real (consented or public) EU documents.
* Never describe this as "GDPR-safe" or "no leakage". The guarantee is the same as for KVKK: every value Katip
  detects is masked and checked before the text leaves the computer. Values it does not detect are not covered.

## Reproduce

```bash
python lab/eu/synth_eu.py --seed 2611 --n 300            # dev set + negatives
python lab/eu/synth_eu.py --blind --seed 9091 --n 300    # blind set
KATIP_SDK=0 python lab/eu/eval_eu.py lab/eu/data/eu_blind_seed9091.jsonl
KATIP_SDK=0 python lab/eu/fp_gdpr_text.py                # fetches the GDPR pages once into a temp cache
KATIP_SDK=0 python lab/eu/eval_eu.py lab/eu/data/ugur_round3.jsonl
pip install gliner && KATIP_EU_NER=gliner KATIP_SDK=0 python lab/eu/eval_eu.py lab/eu/data/ugur_round3.jsonl
cd connector && python -m pytest -q tests/test_eu.py
```

`KATIP_SDK=0` uses the bundled engine; the result is the same with katip-mask 0.1.1 installed, since `eu.py`
runs after the engine either way.
