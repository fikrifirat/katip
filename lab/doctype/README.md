# Katip Algıla: document-type classifier (H10)

Names a document's type on the device (ödeme emri, ihtarname, dilekçe, karar, sözleşme, tebligat, data-room
documents…), then suggests what to do next: mask it, show the related articles (Mevzuat), offer a precedent
search (Emsal). Code: `connector/katip_kalkan/doctype.py` (Python, standard library only) and `src/doctype.js`
(browser / iOS WebView, identical output: `node src/tests/doctype_parity.mjs`).

## Results (tr-0.1)

Raw numbers, per-type and per-form breakdowns: `results/heldout_family.json`, `results/independent_sets.json`.

All numbers are accuracy on documents the model never trained on, with 95% bootstrap intervals. "Keywords" is a
title-keyword rule list (`eval.py: KEYWORDS`), the obvious cheap alternative.

| Test set | What it is | n | Katip Algıla | Keywords |
| --- | --- | ---: | ---: | ---: |
| Held-out writing style | synthetic, 24 types, family 2 of 3 never seen in training; OCR noise, ASCII, all caps, page cuts | 2,880 | **89.5%** (88.4–90.7) | 59.3% |
| Same, clean | no augmentation | 1,440 | **90.6%** (89.1–92.1) | 64.7% |
| Katip samples | `docs/samples`, 80 docs from Katip's earlier, separate generator, 15 types | 80 | **93.8%** (87.5–98.8) | 80.0% |
| KVKK-Bench forms | 306 petitions and forms, 34 bodies, separate generator (scored only: the file says "do not train") | 306 | **82.7%** (78.4–86.6) | 58.5% |
| Real Yargıtay text | TurkishLegalNER decisions, 8-sentence chunks, mostly mid-document with no header | 73 | **97.3%** (93.2–100) | 9.6% |
| Real Wikipedia text | non-legal Turkish; right answer is "other" | 100 | **88.0%** (81–94) | 98.0% |

Held-out style is scored with a model trained on families 0 and 1 only (`results/heldout_family.json`); the other rows use
the shipped model, trained on all three families (`connector/katip_kalkan/doctype_packs/tr.model.*`).

Size and speed: 384 KB of int8 weights (2^14 hashed features × 24 types), 1 ms to load, about 2 ms for a
one-page document and at most ~8 ms for any longer one (only the first 3,000 and last 1,000 characters are read),
in pure Python on one CPU core.

### Where it fails (read this before quoting the numbers)

- **A new sub-kind of a type, not a new style, is the weak spot.** On the held-out family the errors are almost
  all two systematic ones: a Bölge Adliye *istinaf decision* (only first-instance and Yargıtay decisions were in
  training) reads as an appeal petition (107/120), and a *share transfer agreement* reads as a corporate
  resolution (100/120). The cure is data for that sub-kind, not tuning.
- **Forms with no counterpart in training:** bar applications (staj, staj nakli, ruhsat: 10/36), ödeme emrine
  itiraz (0/9: it says "ödeme emri" throughout, so it is typed as the payment order itself; the suggested
  articles, İİK md. 62 and 168, are still the right ones), uzlaşma (0/9), tüketici (2/9).
- **Meeting minutes** (toplantı tutanağı, a company meeting) abstain as "other" (0/5): our tutanak class is
  official records.
- **Non-legal text:** 12% of Wikipedia chunks get a legal type, mostly corporate resolution or tutanak. In a
  lawyer's folder that is a wrong suggestion, not a leak: masking runs either way.
- Everything except the two real-text rows is synthetic. No real lawyer's folder has been scored yet; the next
  honest number is a labelled gold set from pilot firms (labels only, documents never leave the office;
  `eval.py` can run there and print only the confusion table).

## How it works

- **Features** (`doctype.tokens`): Turkish lower-case, folded to ASCII (so OCR output and ASCII-typed text match
  clean text), digits collapsed; words, word bigrams and character 3–4-grams of the first 3,000 and last 1,000
  characters. Hashed with FNV-1a 32 into 2^14 signed buckets, log-scaled, L2-normalised. The spec is the code;
  `test_doctype.py` pins the hash values so ports can't drift.
- **Model**: multinomial logistic regression (numpy, Adam, L2 1e-4, 3 epochs), int8 per class. A linear model
  is deliberate: fast in pure Python, easy to port, and under FHE it is one plaintext-matrix × encrypted-vector
  product with the argmax done by the client (encrypted-compute experiment 3 can use these weights as they are).
- **Abstaining**: probabilities are temperature-scaled across writing styles (train without family f, fit T on
  family f, average; in-distribution data is separable and would make the model always certain). Below 0.5 the
  answer is "diger" (other) and no type is claimed.
- **Hyper-parameters** were chosen on family 0 → 1 and 1 → 0 transfer only (`tune.py`, `results/tune_drop*.json`):
  character n-grams matter most (without them ~56%), line-start and title features didn't help and are off,
  line dropout and mixing two families' lines in training add ~1.5 points.
  For the record: the first family-2 run, before any tuning, scored 55.8%, mostly by over-using "other".

## Data

`templates_tr.py`: 24 types × 3 families, written for this purpose; structure follows public statutes (HMK md.
119/129/342, İİK md. 58/60, Tebligat K., TTK md. 21/390, KVKK md. 10–14, VUK md. 230). Fill values are random
(`fill.py`). No real document, no Ozan or client material, no sentence from KVKK-Bench or docs/samples.
`gen.py` writes 9,600 training documents with augmentation (OCR swaps and drops, ASCII Turkish, all caps,
missing title block, middle page only, top of page only, PDF re-wrapping, line dropout, family mixing).

```
python lab/doctype/gen.py                         # synthetic sets -> lab/doctype/data/ (git-ignored)
python lab/doctype/tune.py 0.3                    # cross-family hyper-parameter search (families 0/1 only)
python lab/doctype/train.py --train train --out lab/doctype/runs/family_split
python lab/doctype/eval.py --models lab/doctype/runs/family_split --sets test_family test_family_clean
python lab/doctype/train.py --train full          # shipped pack
python lab/doctype/eval.py                        # independent sets (downloads forms, TurkishLegalNER, Wiki NER)
```

## Language packs

`doctype_packs/<lang>.pack.json`: the types, their names (local + English, the UI shows both), related
articles, precedent query templates and steps. `<lang>.model.json` + `.bin`: weights. `nl.pack.json` (Dutch:
dagvaarding, vonnis, beschikking, IND/WOZ/belasting, arbeids- en huurovereenkomst, sommatie, factuur, polis,
KvK-uittreksel, privacyverklaring) is labels and actions only; its steps call the Dutch thread's
`katip_nl.detect`, `katip_nl.wetten.check_text` and `katip_nl.rechtspraak.check_text`. A Dutch model is
`train.py --lang nl --train <jsonl with text, label>`; until then Dutch text is detected (`detect_language`) and
abstains with a reason.

## Privacy rule (plan H10)

Steps with `"where": "device"` (mask, offline Mevzuat, citation check, deadline hint) may run automatically.
Steps with `"where": "network"` (live Emsal search, drafting with Claude/ChatGPT) come back as
`"run": "suggest"` with the exact query; `doctype.py` never makes a network call. A lawyer can switch any step
off (`settings={"off": [...]}`) or allow network steps to auto-run (`auto_network`), and even then the caller
shows the query first. The Emsal queries are fixed templates per type, never text from the document.
Articles and time limits are pointers to check, not legal advice; the pack says so in both languages.
