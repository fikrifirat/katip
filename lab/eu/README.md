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
| Names | after a title (Herr, Frau, M., Mme, Sig., Sig.ra, Sr., Sra., dhr., mevr., Mr, Ms, Dr ...), in a form field (Name:, Nom :, Kläger: ...), under a closing (Kind regards, Mit freundlichen Grüßen, Cordialement ...), or starting with one of ~580 common European first names; a surname found once is masked everywhere | - |

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
"Zertifizierung", "Behörden" read as names); `eu` masks **0**. 30 short negatives in `data/eu_negatives.jsonl`
(GDPR prose, case numbers, ECLIs, amounts): 0 spans, but those were seen while tuning.

Turkish documents: on the 80 `docs/samples` texts and the test petition, `eu` masks everything `ai` masks
(checked in `connector/tests/test_eu.py`).

## What this means

* ID numbers, IBANs, VAT ids, phones, e-mails, passports, dates of birth and European-style addresses are
  covered well on these synthetic letters, including mistyped IDs next to a cue.
* **Names are the gap.** A name with no title, form field or closing around it is caught only when its first
  name is in the list. On the blind set that is about half of the names. The fix is a model (a multilingual
  PII/NER model as an extra layer, like Katip Mask for Turkish), not more rules; that was out of scope here.
* Synthetic data, one letter shape per set. No real EU document has been scored. Before anyone relies on it:
  a small gold set of real (consented or public) EU documents.
* Never describe this as "GDPR-safe" or "no leakage". The guarantee is the same as for KVKK: every value Katip
  detects is masked and checked before the text leaves the computer. Values it does not detect are not covered.

## Reproduce

```bash
python lab/eu/synth_eu.py --seed 2611 --n 300            # dev set + negatives
python lab/eu/synth_eu.py --blind --seed 9091 --n 300    # blind set
KATIP_SDK=0 python lab/eu/eval_eu.py lab/eu/data/eu_blind_seed9091.jsonl
KATIP_SDK=0 python lab/eu/fp_gdpr_text.py                # fetches the GDPR pages once into a temp cache
cd connector && python -m pytest -q tests/test_eu.py
```

`KATIP_SDK=0` uses the bundled engine; the result is the same with katip-mask 0.1.1 installed, since `eu.py`
runs after the engine either way.
