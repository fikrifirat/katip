---
language: tr
license: cc-by-sa-4.0
library_name: transformers.js
pipeline_tag: token-classification
base_model: dbmdz/bert-base-turkish-cased
datasets: [turkish-nlp-suite/turkish-wikiNER]
tags: [ner, pii, kvkk, turkish, legal, onnx, privacy, redaction, berturk, gdpr, anonymization, pseudonymization, de-identification, data-masking, personal-data, legal-nlp, lawyer, avukat, kisisel-veri, anonimlestirme, maskeleme]
---

# Katip Mask Base · tr v2 (katip-mask-base)

[![KVKK-Bench](https://img.shields.io/badge/KVKK--Bench-96.1%20Overall-4c1)](https://huggingface.co/spaces/f1k/kvkk-bench)

*Türkçe:* Türkçe hukuk belgelerinde ad soyad, adres ve KVKK md. 6 sağlık verilerini bulan, cihazda çalışan kişisel veri maskeleme / anonimleştirme modeli.

BERTurk (`dbmdz/bert-base-turkish-cased`) fine-tuned to tag **person names, addresses and KVKK
art. 6 health terms** in Turkish legal documents, as the on-device model for
[Katip Mask](https://huggingface.co/spaces/f1k/katip-kvkk-anonymization). Exported to ONNX (fp32 and int8) for transformers.js.

### KVKK-Bench (v0.1.2)

| # | System | Overall | Turkish names (court) | Foreign names (court) | Everyday text | Forms ◇ | Size MB |
|---|---|---|---|---|---|---|---|
| 1 | [Katip Mask Base · tr v2](https://huggingface.co/f1k/katip-mask-base) | 96.1 | 99.9 | 97.6 | 84.9 | 99.4 | 111.1 |
| 2 | [XLM-RoBERTa Large NER](https://huggingface.co/FacebookAI/xlm-roberta-large-finetuned-conll03-english) | 95.9 | 97.6 | 97.5 | 89.9 | 41.6 | 2235.4 |
| 3 | [XLM-RoBERTa Base Turkish NER](https://huggingface.co/akdeniz27/xlm-roberta-base-turkish-ner) | 95.7 | 98.5 | 98.2 | 86.3 | – | 1109.8 |
| 4 | [Katip rules + GLiNER2 · tr fine-tuned](https://github.com/fikrifirat/katip/blob/legal-study/lab/colab/gliner2_katip_recipe.ipynb) | 95.5 | 98.7 | 97.3 | 86.0 | 98.2 | 1228.7 |
| 5 | [GLiNER2 PII Multi](https://huggingface.co/fastino/gliner2-privacy-filter-PII-multi) | 95.0 | 98.1 | 98.2 | 83.9 | 43.2 | 1228.4 |
| 6 | [PII Redactor Base](https://huggingface.co/Horizon-Labs/pii-redactor-base) | 94.0 | 97.8 | 99.1 | 79.5 | 63.8 | 1230.3 |
| 7 | [Katip Mask Mini · tr v2](https://huggingface.co/f1k/katip-mask-mini) | 93.0 | 99.1 | 97.2 | 73.6 | 98.6 | 31.4 |
| 8 | [BERTurk NER](https://huggingface.co/savasy/bert-base-turkish-ner-cased) | 91.6 | 97.4 | 91.7 | 77.1 | 38.3 | 440.1 |
| 9 | [GLiNER Multi PII v1](https://huggingface.co/urchade/gliner_multi_pii-v1) | 91.3 | 93.1 | 92.9 | 85.2 | – | 1155.8 |
| 10 | [GLiNER2.5 KVKK TR v2](https://huggingface.co/newmindai/gliner2.5-kvkk-tr-v2) | 88.1 | 90.1 | 90.3 | 80.8 | 92.3 | 1149.4 |
| 11 | [Katip Mask Nano · tr v1.1](https://huggingface.co/f1k/katip-mask-nano) | 85.9 | 94.4 | 95.5 | 55.2 | 97.7 | 2.9 |
| 12 | [ModernBERT-TR PII NER](https://huggingface.co/ytu-ce-cosmos/modernbert-tr-pii-ner) | 85.3 | 99.0 | 96.9 | 39.4 | – | 597.5 |
| 13 | [Qwen2.5 1.5B Instruct (zero-shot)](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | 57.5 | 59.1 | 57.6 | 53.7 | – | 3087 |
| 14 | [Privacy Filter Multilingual v2](https://huggingface.co/OpenMed/privacy-filter-multilingual-v2) | 57.2 | 59.8 | 57.4 | 50.7 | – | 2799.2 |
| 15 | [GLiNER2.5 Mürşit KVKK TR v1](https://huggingface.co/newmindai/gliner2.5-mursit-kvkk-tr-v1) | 53.3 | 60.8 | 46.7 | 41.1 | 88.5 | 661.9 |
| 16 | [Privacy Filter](https://huggingface.co/openai/privacy-filter) | 51.3 | 58.0 | 58.0 | 27.9 | – | 2799 |
| 17 | [Hushmark TR 289M](https://huggingface.co/lokomotifai/hushmark-tr-289m) | 50.4 | 50.9 | 48.8 | 50.8 | 51.8 | 1155.8 |
| 18 | [Piiranha v1](https://huggingface.co/iiiorg/piiranha-v1-detect-personal-information) | 49.8 | 41.4 | 61.5 | 59.4 | – | 1112.9 |
| 19 | [Presidio](https://github.com/microsoft/presidio) | 45.0 | 39.3 | 44.0 | 60.4 | 36.1 | 11 |
| 20 | [Werea KVKK PII 150M](https://huggingface.co/Werea-co/Werea-KVKK-PII-150M) | 24.9 | 31.0 | 7.3 | 27.2 | 19.7 | 597.4 |
| 21 | [OpenMed PII Turkish Small](https://huggingface.co/OpenMed/OpenMed-PII-Turkish-ClinicalE5-Small-33M-v1) | 19.1 | 11.8 | 18.8 | 37.5 | – | 133 |

KVKK-Bench v0.1.2, scores out of 100, higher is better. *Overall* is the weighted F2 score for finding names in real text: Yargıtay decisions with Turkish and foreign names, and everyday Wikipedia sentences. *Forms* ◇ covers T.C. kimlik, tax numbers, IBANs and addresses on 306 synthetic petitions and bar forms; it is not in Overall, and blank means not run. Rows named Katip include Katip's rules. Live table and method: https://huggingface.co/spaces/f1k/kvkk-bench

**Test sets built by other teams.** On held-out halves of four public Turkish PII test sets (all synthetic), Katip Mask Base scores F2 95.9 on NewMind's nm-kvkk-pii-6K, 95.9 on piimask TR, 95.2 on Çağrı Güngör's set and 95.8 on Werea's, against 93.9, 93.8, 72.6 and 54.3 for NewMind's kvkk-v2. The lead is significant on nm6k, piimask and Çağrı (95% paired bootstrap); on piimask documents with unseen templates the two tie (96.5), and Werea's halves share templates, so that result is not independent. NewMind keeps higher precision on nm6k (99.7 vs 91.2) and piimask (93.2 vs 89.8). Katip leaves less personal data readable on Çağrı (6.8% vs 41.1%) and Werea (26.3% vs 65.2%), about the same on nm6k and piimask. Method and every row: [RESULTS.md](https://github.com/fikrifirat/katip/blob/legal-study/lab/legal/external/RESULTS.md).

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
