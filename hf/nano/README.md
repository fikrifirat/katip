---
language: tr
license: cc-by-sa-4.0
datasets: [turkish-nlp-suite/turkish-wikiNER]
library_name: transformers.js
pipeline_tag: token-classification
tags:
- ner
- pii
- kvkk
- turkish
- legal
- onnx
- privacy
- redaction
---

# Katip Mask Nano · tr v1.1

A 2.5 MB Turkish person-name tagger (int8 ONNX) that runs in the browser or on a laptop CPU, next to
Katip's rule-based PII detection. It is the default model of [Katip Mask](https://huggingface.co/spaces/f1k/katip-mask),
a KVKK redaction tool where the document never leaves the user's computer, and of the
[Katip Kalkan](https://github.com/fikrifirat/katip/tree/main/connector) connector for Claude.

**New in v1.1 (13 Nov 2026):** trained with foreign client names as they appear in Turkish documents
(Syrian, Iranian, Afghan, Georgian, Armenian, Greek, Arab, Russian/Ukrainian, Azerbaijani and Western names,
transliterated with inconsistent spellings). v1 (Turkish names only) is kept at the `v1.0` tag of this repo.

## Results

Measured with Katip's rules (v0.2, 14 Nov 2026) and the exact detection code the browser runs. "Rules" means no model.
A value counts as found when a detected span of the same type covers it. Model spans scored 0.5 or higher keep
their edges (`trust` 0.5, in `katip.json`).

**Foreign client names in real court prose.** TurkishLegalNER *test* sentences (Yargıtay), with the anonymised
slots filled by names from held-out families (no spelling of them was used in training), 3 fills per sentence,
1,011 names. 95% CIs from a document bootstrap.

| | Foreign names | Turkish names, same slots | Precision | False names per 1,000 words of name-free trap text |
| --- | --- | --- | --- | --- |
| Rules | 77.1% [73.9–80.1] | 93.0% | 99.9% | 0.6 |
| Rules + Nano v1 | 80.3% [77.0–83.3] | 97.4% | 99.6% | 0.6 |
| **Rules + Nano v1.1** | **94.6% [92.5–96.2]** | **98.7%** | 97.4% | 9.1 |

By origin (v1 → v1.1): Arab 69% → 93%, Azerbaijani 60% → 74%, Western 75% → 91%, Persian 88% → 98%,
Armenian 87% → 97%, Georgian 89% → 99%, Greek 89% → 100%, Russian/Ukrainian 90% → 95%, Afghan 92% → 100%.
Azerbaijani names are still the weakest, because many are written with Turkish word stems.

**Synthetic Turkish legal documents** (person names / all values, whole-address scoring):

| Set | Rules | Rules + Nano v1 | Rules + Nano v1.1 | False names added by v1.1 |
| --- | --- | --- | --- | --- |
| Blind (80 docs, new names) | 364 / 365 · 754 / 757 | 364 / 365 · 754 / 757 | 364 / 365 · 754 / 757 | 0 |
| Held-out (60 docs) | 263 / 275 · 605 / 618 | 268 / 275 · 610 / 618 | **271 / 275 · 613 / 618** | 0 |
| Tuning (40 docs) | 159 / 165 · 425 / 431 | 159 / 165 · 425 / 431 | **163 / 165 · 429 / 431** | 1 |
| Name-free legal prose | | | | 0 |

**The cost.** On trap sentences full of words that are also names or places (Hakim, Emir, Nur, Rahim, Halep,
Kabil, Erbil...) v1.1 adds about 9 false names per 1,000 words, against 0.6 for v1. Katip shows every masked
value with a tick box, so a false name costs a click; a missed name is a KVKK breach.

**Honest caveats.** The legal documents above are synthetic. The court prose is real, but its names are filled in
by us. The foreign-name scores come from the same TurkishLegalNER corpus whose *train* split was used in training
(the test split was not). Real case files will score lower, so always review the masked output.

## How it is meant to be used

Labels (`O`, `B-PER`, `I-PER`) are trained **per word on the word's first sub-token**. Words are split with the
regex in `config.json` → `katip.word_regex` (`[\p{L}\p{N}][\p{L}\p{N}'’.-]*`). Feed words in order inside
`[CLS] … [SEP]` windows of at most 256 tokens and read the logits at each word's first sub-token. The stock
Hugging Face token-classification pipeline splits differently and gives noisy output.

How Katip combines it with the rules (`local_detect.py` in the Space):

1. keep model spans with mean probability ≥ 0.5;
2. below `trust`, trim ordinary Turkish words off both edges; at or above it, keep the edges;
3. widen an overlapping rule PERSON span to the union;
4. otherwise add the span when it has two or more capitalised words, or one capitalised word that is not an
   ordinary word (or carries a proper-noun case suffix, as in *Topçu'nun*), or one already found as a name in the
   same document.

Reference code: `src/ner.js` (transformers.js) and `connector/katip_kalkan/ner.py` (onnxruntime, no PyTorch) in
the [source repository](https://github.com/fikrifirat/katip). This release ships only the int8 ONNX file; the
PyTorch weights of v1 are at the `v1.0` tag.

## Model and training

BERT trained from scratch: 2 layers, hidden size 128, 2 heads, 512 FFN, 256 positions, cased WordPiece vocabulary
of 16,000. 5 epochs, seed 0, about 8 minutes on 4 CPU cores (`train_info.json`).

Training data: 8,000 synthetic documents from Katip's legal templates (petitions, judgments, leases, employment
contracts, powers of attorney, notices, e-mails, minutes, chats, expert reports), with some of their names swapped
for foreign ones; 4,182 real-text documents (all 17,967 Turkish Wiki NER sentences, packed, plus TurkishLegalNER
train-split court sentences and generated petitions with names filled in); and the foreign-name mix: transliterated
names from 10 origin groups with spelling variants (Muhammed / Mohammad / Mhd, Al- / El-, -zadeh / -zade,
-shvili / -şvili, -yan / -ian), minus every family held out for testing. Recipe: `lab/foreign/` in the source
repository.

## Limits

- Person names only. Everything with a checksum or fixed shape (T.C. kimlik, YKN, passport, VKN, IBAN, card,
  phone, plate, e-mail) and addresses are left to the rules.
- Legal Turkish. Not tested on OCR output beyond Katip's scans and photos, or on non-legal text.
- Not a privacy guarantee: always review redacted output before sending it.

## Licence

**CC BY-SA 4.0** (see `LICENSE`). You may use, share and adapt the model, also commercially. Credit Katip
and the training data, and share adaptations under the same licence. Nano v1.1 is trained partly on Turkish Wiki NER
(Altinok, D. (2023). *A Diverse Set of Freely Available Linguistic Resources for Turkish*. ACL 2023;
CC BY-SA 4.0, https://github.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset). Earlier versions (v1.0)
were released under CC BY-NC 4.0. Katip's code is AGPL-3.0, with a commercial licence on request:
https://github.com/fikrifirat/katip.

## Citation

```bibtex
@misc{firat2026katipmasknano,
  title  = {Katip Mask Nano (tr): a 2.5M-parameter Turkish name tagger for the browser},
  author = {F{\i}rat, Fikri},
  year   = {2026},
  url    = {https://huggingface.co/f1k/katip-mask-nano}
}
```

Please also cite Turkish Wiki NER (Altinok, 2023).
