---
language: tr
license: cc-by-sa-4.0
library_name: transformers.js
pipeline_tag: token-classification
base_model: dbmdz/bert-base-turkish-cased
datasets: [turkish-nlp-suite/turkish-wikiNER]
tags: [ner, pii, kvkk, turkish, legal, onnx, privacy, redaction, berturk]
---

# Katip Mask Base · tr v2 (katip-mask-base)

BERTurk (`dbmdz/bert-base-turkish-cased`) fine-tuned to tag **person names, addresses and KVKK
art. 6 health terms** in Turkish legal documents, as the on-device model for
[Katip Mask](https://huggingface.co/spaces/f1k/katip-mask). Exported to ONNX (fp32 and int8) for transformers.js.

**v2 (13 Nov 2026)** adds 17,967 real Turkish sentences (Turkish Wiki NER, person names only) to the
synthetic training documents. v1 found every name in Katip's synthetic test sets but only 41% of names in
real Turkish sentences; v2 finds 90%.

## Results in Katip (rules + this model, as the demo runs it)

Model names scored 0.5 or higher keep their edges (`trust` 0.5, chosen on dev data).

| Set | v2 | v1 |
| --- | --- | --- |
| Blind (80 synthetic docs, 757 values) | 757 / 757, names 365 / 365 | 757 / 757 |
| Held-out (60 synthetic docs, 618 values) | 618 / 618 | 618 / 618 |
| Name-free legal prose | 3 false alarms | 3 |
| Real Yargıtay prose, anonymised names filled back in (1,643 names) | **99.3%** found, 96.2% precision | 98.6%, 95.9% |
| Real Wikipedia sentences, Wiki NER test (654 names) | **89.8%** [87.1–92.1], 89.9% precision | 40.7% |

About 27 ms per synthetic document and 19 ms per sentence on an Apple-silicon Mac (int8 ONNX,
onnxruntime). Method and scripts: https://github.com/fikrifirat/katip/tree/lab/lab

## Results (model alone, no rules)

Trained for 3 epochs on 8,000 synthetic documents plus 2,246 pseudo-documents of eight real sentences
each, in 28 minutes on an Apple-silicon Mac (MPS).

| Set | Names | Addresses | Health terms | Extra spans |
| --- | --- | --- | --- | --- |
| Blind (80 docs, 16 styles, 4 new) | 364 / 365 | 80 / 80 | 25 / 26 | 0 |
| Held-out (60 docs) | 275 / 275 | 70 / 70 | 26 / 26 | 0 |
| Wiki NER dev (1,000 real sentences) | 583 / 641 | | | 53 |

**Limits.** Addresses and health terms are still learned from synthetic documents only. The real-text
court set uses real decisions with names filled in by us, because published Turkish decisions are
anonymised; consented real case files from pilot firms are the next test.

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

**Base model:** BERTurk (`dbmdz/bert-base-turkish-cased`) by Stefan Schweter / dbmdz, MIT licence.

**Licence:** CC BY-SA 4.0 (see `LICENSE`). v2 is trained partly on Turkish Wiki NER (Altinok, 2023; CC BY-SA 4.0,
https://github.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset), so the model is shared under the same
licence: credit Katip and the dataset, and share adaptations under CC BY-SA 4.0. v1 (synthetic data
only) was released under CC BY-NC 4.0. Katip's code is AGPL-3.0; for a commercial licence for the
code or support, open an issue at https://github.com/fikrifirat/katip.

## Citation

```bibtex
@misc{firat2026katipmaskbase,
  title  = {Katip Mask Base (tr): a Turkish personal-data tagger fine-tuned from BERTurk},
  author = {F{\i}rat, Fikri},
  year   = {2026},
  url    = {https://huggingface.co/f1k/katip-mask-base},
  note   = {Fine-tuned from BERTurk (Schweter, 2020)}
}
```

Please also cite BERTurk (Stefan Schweter, https://doi.org/10.5281/zenodo.3770924) and Turkish Wiki NER (Altinok, 2023).
