---
language: tr
license: cc-by-nc-4.0
library_name: transformers.js
pipeline_tag: token-classification
base_model: dbmdz/bert-base-turkish-cased
tags: [ner, pii, kvkk, turkish, legal, onnx, privacy, redaction, berturk]
---

# katip-tr-pii-berturk

BERTurk (`dbmdz/bert-base-turkish-cased`) fine-tuned to tag **person names, addresses and KVKK
art. 6 health terms** in Turkish legal documents, as the on-device model for
[Katip Yerel](https://github.com/fikrifirat/katip). Exported to ONNX (fp32 and int8) for transformers.js.

Scores, training time and settings for this upload are in `results.json` (model alone, before
Katip's rules are added). Training data is synthetic; the blind set's names never appear in training.

Labels are word-level BIO on each word's first sub-token; use the word split in `config.json`
(`katip.word_regex`) as Katip's `src/ner.js` does.

**Licence:** CC BY-NC 4.0, non-commercial use only. For commercial or production use, contact
fikrifirat@gmail.com or open an issue at https://github.com/fikrifirat/katip.
