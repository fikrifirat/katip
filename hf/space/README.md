---
title: Katip KVKK Masking & Anonymisation
emoji: 🛡️
colorFrom: green
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: agpl-3.0
short_description: KVKK anonymisation of Turkish legal documents, in-browser
models:
- f1k/katip-mask-nano
- f1k/katip-mask-mini
- f1k/katip-mask-base
tags:
- pii
- redaction
- kvkk
- turkish
- legal
- privacy
- webassembly
- gdpr
- anonymization
- pseudonymization
- de-identification
- data-masking
- personal-data
- legal-nlp
- lawyer
- avukat
- kisisel-veri
- anonimlestirme
- maskeleme
- anonymisation
- ner
- turkish-nlp
---

# Katip: KVKK masking and anonymisation (Katip Mask)

Türkçe hukuk belgelerinde kişisel verileri (T.C. kimlik no, VKN, IBAN, telefon, e-posta, plaka,
adres, ad soyad, KVKK md. 6 özel nitelikli veriler) **tamamen tarayıcıda** bulur ve maskeler.
Belge hiçbir sunucuya yüklenmez; sayfanın güvenlik politikası başka bir adrese veri gönderilmesini engeller.

Turkish PII redaction for legal documents (PDF, scanned PDF, photos, Word, UYAP .udf, text),
running entirely client-side: Python rules in Pyodide, true PDF redaction with MuPDF (WASM),
OCR with Tesseract.js and PaddleOCR, and an on-device name model
([Katip Mask Nano](https://huggingface.co/f1k/katip-mask-nano), 2.5 MB, Turkish and foreign client names) via transformers.js;
the 110 MB [Katip Mask Base](https://huggingface.co/f1k/katip-mask-base) is one click away under "Gelişmiş ayarlar".

- Drop a file and get the masked copy: scanning, masking and the leak check run automatically.
- Untick anything that should stay visible, or type a missed term; then download.
- 80 synthetic samples (16 document types, 5 each) with answer keys; model, OCR, threshold, data types and mask style under "Gelişmiş ayarlar".
- "Görüş bildir" opens a ready e-mail for feedback.

## How it compares

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

How the tools compare on Turkish documents: [KVKK-Bench leaderboard](https://huggingface.co/spaces/f1k/kvkk-bench).
Questions and answers: [Türkçe SSS](https://fikrifirat.github.io/katip/sss.html) · [English FAQ](https://fikrifirat.github.io/katip/faq.html).
Mask files before Claude reads them: [Katip Kalkan](https://github.com/fikrifirat/katip/tree/main/connector).

Source: https://github.com/fikrifirat/katip · Licence: AGPL-3.0, with a commercial licence
available for use in products or real operations (contact fikrifirat@gmail.com or open an issue).
