---
language: tr
license: cc-by-sa-4.0
base_model: dbmdz/distilbert-base-turkish-cased
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
- gdpr
- anonymization
- pseudonymization
- de-identification
- data-masking
- personal-data
- legal-nlp
- knowledge-distillation
- lawyer
- avukat
- kisisel-veri
- anonimlestirme
- maskeleme
---

# Katip Mask Mini · tr v2

[![KVKK-Bench](https://img.shields.io/badge/KVKK--Bench-93.0%20Overall-4c1)](https://huggingface.co/spaces/f1k/kvkk-bench)

*Türkçe:* Tarayıcıda ya da dizüstü bilgisayarda çalışan 31 MB'lık Türkçe ad soyad tanıma modeli. Katip Mask Base'den
damıtıldı. Avukatlar için kişisel veri maskeleme aracı Katip'in orta boy modelidir.

A 31 MB Turkish person-name tagger (int8 ONNX, 31M parameters) that runs in the browser or on a laptop CPU, next to
Katip's rule-based PII detection. It sits between [Katip Mask Nano](https://huggingface.co/f1k/katip-mask-nano)
(3 MB) and [Katip Mask Base](https://huggingface.co/f1k/katip-mask-base) (111 MB). It is built for
[Katip Mask](https://huggingface.co/spaces/f1k/katip-kvkk-anonymization), a redaction tool where the document never leaves the
user's computer, and for the [Katip Kalkan](https://github.com/fikrifirat/katip/tree/main/connector) connector for Claude.

Mini is a smaller copy of Base. It starts from DistilBERTurk, keeps 3 of its 6 layers and the 12,000 word pieces
our text uses, and is then taught by Base. Base catches more names in everyday prose. Mini is the option when 111 MB
is too much to download in a browser tab.

## Results

These are [KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench) v0.1.2 scores (re-scored with the rules shipped on 16 Nov 2026). Every row runs
Katip's rules plus the model, with the same detection code the browser runs. A value counts as found when a detected
span of the same type covers it. Speed is measured in Python on an Apple M-series laptop CPU, one page being
500 words.

The leaderboard's *Overall* and *Leaked* columns cover only the three real-text name columns (court Turkish, foreign
names, everyday prose): 93.0 and 11.6% for Mini. The KVKK-F2 and leak figures below cover all tracks, rules included.

| | Nano v1.1 | **Mini v2** | Base v2 |
| --- | --- | --- | --- |
| Download (int8 ONNX) | 2.9 MB | **31 MB** | 111 MB |
| KVKK-F2, all tracks | 80.8 | **88.9** | 93.1 |
| Leaked (characters of personal data still readable) | 7.0% | **4.3%** | 3.1% |
| Turkish names in real Yargıtay prose: found / precision | 94.1% / 95.8% | **99.2% / 98.8%** | 99.9% / 100% |
| Foreign names, same sentences: found / precision | 95.5% / 95.6% | **96.8% / 98.6%** | 97.1% / 100% |
| Names in everyday prose (Wiki NER test): found / precision | 53.7% / 62.2% | **72.2% / 78.7%** | 84.1% / 88.0% |
| Pages per second, laptop CPU | 32 | **5** | 1.7 |

The two court-prose tracks use TurkishLegalNER *test* sentences (Koç University, Apache-2.0). Their anonymised name
slots were filled with held-out names, giving 1,011 names per track. Everyday prose is the Turkish Wiki NER test split
(654 names).

**Synthetic legal documents.** On the blind set (80 documents, names never seen in training), Mini found 364 of
365 names and added 0 false ones. It also added 0 false names on name-free negative documents. On the held-out set
(60 documents) it found 99.6% of names.

**Phone photos** (KVKK-Bench photo track: 60 synthetic phone photos of filled forms, OCR by Katip Otomatik, with ink
masks):

- 5.8% of personal data leaked, against 5.0% for Base and 5.4% for Nano.
- No names or T.C. kimlik numbers leaked (0 of 120 each).
- Addresses leaked 28 times out of 120.
- 0.8 false masks per page.

**Dev scores for the release.** Three candidates were trained and the winner was picked on dev data only:

| Candidate | Layers kept | Vocabulary | int8 | Wiki NER dev F2 |
| --- | --- | --- | --- | --- |
| **L3-V12k (this model)** | 0, 2, 5 | 12,000 | 31.1 MB | **72.5** |
| L3-V8k | 0, 2, 5 | 8,000 | 28.0 MB | 69.2 |
| L2-V12k | 0, 5 | 12,000 | 23.9 MB | 66.5 |

The test sets were scored once, after the winner was picked. On Wiki NER test, the model alone (without rules) found
71.4% of names [67.5–75.1] at 80.1% precision [76.3–83.6]. Brackets are 95% CIs from a document bootstrap.

## How it is meant to be used

It is used exactly like Nano. Labels (`O`, `B-PER`, `I-PER`) are trained **per word on the word's first sub-token**.
Words are split with the regex in `config.json` → `katip.word_regex` (`[\p{L}\p{N}][\p{L}\p{N}'’.-]*`). Feed words in
order inside `[CLS] … [SEP]` windows of at most 256 tokens, and read the logits at each word's first sub-token. The
stock Hugging Face token-classification pipeline splits words differently and gives noisy output.

`katip.json` holds `trust` 0.5. Model spans scored at or above it keep their edges. Below it, Katip trims ordinary
Turkish words off both edges. The full rule-merging steps are on the
[Nano card](https://huggingface.co/f1k/katip-mask-nano#how-it-is-meant-to-be-used). Reference code is `src/ner.js`
(transformers.js) and `connector/katip_kalkan/ner.py` (onnxruntime, no PyTorch) in the
[source repository](https://github.com/fikrifirat/katip).

This release ships the int8 ONNX file only.

## Model and training

- **Starting point:** DistilBERTurk (`dbmdz/distilbert-base-turkish-cased`, MIT): 6 layers, hidden size 768,
  32k cased WordPiece vocabulary, pretrained on general Turkish.
- **Shrinking:**
  - The vocabulary is pruned to 12,000 pieces: every special token and single character (so no word becomes
    `[UNK]`), then the pieces used most often in the training text.
  - The model keeps transformer layers 0, 2 and 5.
- **Distillation from [Katip Mask Base](https://huggingface.co/f1k/katip-mask-base):**
  - Loss: ½ gold cross-entropy + ½ T²·KL against Base's predictions, at T = 2.
  - 4 epochs, AdamW, learning rate 1e-4 with a one-cycle schedule, batch size 32, windows of 256 tokens.
  - About 12.5 minutes on a Colab T4.
- **Training text** (the same as Mini v1):
  - Katip's synthetic legal documents.
  - The Turkish Wiki NER *train* split, packed 8 sentences per document.
  - TurkishLegalNER *train*-split court sentences, with their name slots refilled.
  - Katip's foreign-name training files.

None of KVKK-Bench's test documents were used: not the TLNER test split, not the Wiki NER test split, and not the
held-out names. The recipe is `lab/mini/train_mini_v2.py` in the source repository.

## Limits

- **Fewer names in everyday prose than Base.** Mini finds 70.9% of names in ordinary Turkish text, against 83.9% for
  Base, and is less precise (79.2% against 88.3%). On court decisions the gap is under one point. On news-like,
  letter-like or chat text, use Base if you can, and always review the output.
- **Building and door numbers on photos.** On phone photos, parts of addresses (mostly building and door numbers
  that OCR splits off the street) were still readable in 28 of 120 addresses. Over-masking street names was
  common (70 of 360). Addresses are handled by the rules and the OCR, not by this model, so Base leaks about as much.
- **Person names only.** Everything with a checksum or fixed shape is left to the rules: T.C. kimlik, YKN,
  passport, VKN, IBAN, card, phone, plate and e-mail. So are addresses.
- **Mostly synthetic legal test data.** The court prose is real, but its names were filled in by us. The legal
  documents and photos are synthetic. Real case files will score lower.
- **Not a privacy guarantee and not a compliance certificate.** Using this model does not by itself make processing
  lawful under KVKK or GDPR. Always review redacted output before sending it.

## Licence

**CC BY-SA 4.0** (see `LICENSE`). You may use, share and adapt the model, also commercially. You must credit Katip
and the sources below, and share adaptations under the same licence.

- **Weights:** initialised from DistilBERTurk by the MDZ Digital Library team (dbmdz) at the Bavarian State Library,
  MIT licence: https://huggingface.co/dbmdz/distilbert-base-turkish-cased.
- **Training text:** partly Turkish Wiki NER (Altinok, D. (2023). *A Diverse Set of Freely Available Linguistic
  Resources for Turkish*. ACL 2023; CC BY-SA 4.0, https://github.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset).
- **Code:** Katip's code is AGPL-3.0, with a commercial licence on request: https://github.com/fikrifirat/katip.

## Citation

```bibtex
@misc{firat2026katipmaskmini,
  title  = {Katip Mask Mini (tr): a 31 MB Turkish name tagger distilled from Katip Mask Base},
  author = {F{\i}rat, Fikri},
  year   = {2026},
  url    = {https://huggingface.co/f1k/katip-mask-mini}
}
```

Please also cite Turkish Wiki NER (Altinok, 2023) and DistilBERTurk (Schweter, dbmdz).
