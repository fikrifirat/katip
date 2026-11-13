---
language: tr
license: cc-by-sa-4.0
library_name: transformers.js
pipeline_tag: token-classification
base_model: dbmdz/bert-base-turkish-cased
datasets: [turkish-nlp-suite/turkish-wikiNER]
tags: [ner, pii, kvkk, turkish, legal, onnx, privacy, redaction, berturk]
---

# katip-tr-pii-berturk

BERTurk (`dbmdz/bert-base-turkish-cased`) fine-tuned to tag **person names, addresses and KVKK
art. 6 health terms** in Turkish legal documents, as the on-device model for
[Katip Yerel](https://github.com/fikrifirat/katip). Exported to ONNX (fp32 and int8) for transformers.js.

## Results (model alone, before Katip's rules are added)

Trained for 3 epochs on 8,000 synthetic documents in 25.5 minutes on an Apple-silicon Mac (MPS).
Scored on sets the training never saw; the blind set's names never appear in training.

| Set | Names | Addresses | Health terms | Extra spans | Time per document |
| --- | --- | --- | --- | --- | --- |
| Blind (80 docs, 16 styles, 4 new) | 364 / 365 | 80 / 80 | 26 / 26 | 2 | 17.6 ms |
| Held-out (60 docs) | 275 / 275 | 70 / 70 | 26 / 26 | 0 | 16.1 ms |
| Name-free legal prose (3 docs) | | | | 0 | 20.3 ms |

For comparison, Katip's rules plus the 2.6 MB
[`katip-tr-name-tagger-tiny`](https://huggingface.co/f1k/katip-tr-name-tagger-tiny) find 364 / 365
names on the blind set and 268 / 275 on the held-out set, with 3 false alarms on name-free prose.
Times are PyTorch on the Mac GPU; in the browser (int8 ONNX, WebAssembly, one thread) it is slower.
Raw numbers: `results.json`.

**Limits.** All documents are synthetic and 12 of the 16 blind styles share templates with the
training data, so real case files will score lower. In Katip the model is combined with the rules:
a model address or health span widens an overlapping rule span of the same type, and a new one is
only added where nothing else was found (and, for addresses, with two or more words). That policy
was checked with a small stand-in model on the blind set, not with this model.

## Results in Katip (rules + this model)

With Katip's rules, keeping model names scored 0.9 or higher as they are: blind set **757 / 757** values
(names 365 / 365, 1 extra name, 10 extra health highlights from the rules), held-out set 618 / 618, 3 false
alarms on name-free prose. About 28 ms per document on the Mac (int8 ONNX, onnxruntime).

## Files

| File | Size | |
| --- | --- | --- |
| `onnx/model_quantized.onnx` | 110.8 MB | int8, used by the browser demo |
| `onnx/model.onnx` | 440.3 MB | fp32 |
| `model.safetensors` | | PyTorch weights, for further fine-tuning |

The int8 file is 4× smaller than fp32, and every Katip score above was measured on the int8 file, so
quantising cost no accuracy. Side-by-side size, speed and accuracy for all Katip models:
https://github.com/fikrifirat/katip#size-speed-and-accuracy-side-by-side

Labels are word-level BIO on each word's first sub-token; use the word split in `config.json`
(`katip.word_regex`) as Katip's `src/ner.js` does.

**Licence:** CC BY-SA 4.0. v2 is trained partly on Turkish Wiki NER (Altinok, 2023; CC BY-SA 4.0,
https://github.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset), so the model is shared under the same
licence: credit Katip and the dataset, and share adaptations under CC BY-SA 4.0. v1 (synthetic data
only) was released under CC BY-NC 4.0. Katip's code is AGPL-3.0; for a commercial licence for the
code or support, open an issue at https://github.com/fikrifirat/katip.
