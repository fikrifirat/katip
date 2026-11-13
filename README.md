# Katip Yerel: Turkish KVKK redaction that runs in your browser

**English** · [Türkçe](README.tr.md)

[![Live demo](https://img.shields.io/badge/demo-GitHub%20Pages-2f7d4f)](https://fikrifirat.github.io/katip/)
[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Space-katip--yerel-yellow)](https://huggingface.co/spaces/f1k/katip-yerel)
[![Model](https://img.shields.io/badge/%F0%9F%A4%97%20model-name--tagger--tiny-yellow)](https://huggingface.co/f1k/katip-tr-name-tagger-tiny)
[![BERTurk model](https://img.shields.io/badge/%F0%9F%A4%97%20model-pii--berturk-yellow)](https://huggingface.co/f1k/katip-tr-pii-berturk)
[![Licence: AGPL-3.0 + commercial](https://img.shields.io/badge/licence-AGPL--3.0%20%2B%20commercial-blue)](COMMERCIAL.md)

Katip finds and masks personal data in Turkish legal documents (T.C. kimlik no, VKN, IBAN, phone,
e-mail, plate, address, names, KVKK art. 6 health data) **without the document ever leaving your
computer**. The file is opened, analysed, masked and leak-checked inside the browser tab. Nothing is
uploaded or stored, and the page's Content-Security-Policy blocks sending data to any other address.
Only the redacted copy you download leaves the machine.

Built for law firms, in-house legal and compliance teams who need to share case files, contracts or
court documents with clients, experts or AI tools under KVKK.

![Katip Yerel](screenshot.png)

## Key numbers

Measured on Katip's synthetic Turkish legal documents. The **blind set** uses 80 documents with
names never seen during development or training, in 16 document styles (4 of them new).

| | Result |
| --- | --- |
| Values found (blind set, default settings) | **756 of 757 (99.9%)**, 10 extra highlights, all health terms |
| Names found | 364 of 365 (99.7%); 98.4% with rules only |
| Values still readable after masking (full pipeline, rules only) | 0.8% for text, PDF, Word and UDF; 0.7–1.1% for photos and scans |
| False alarms on name-free legal prose | 3 across 3 documents |
| Time per document | 0.1–0.3 s for text, PDF, Word, UDF; 2–4.5 s with OCR (4-core cloud VM) |
| Network requests after a document is opened | **0** (verified in Chromium) |
| First load | about 30 MB of engine files (Python, PDF, OCR), plus about 30 MB for the name tagger; cached by the browser afterwards |

### Models in the demo

| Model | What it is | Values found (blind) | Names found |
| --- | --- | --- | --- |
| **Katip Mask Nano** (recommended) | Katip Rules + `katip-tr-name-tagger-tiny`, 2.6 MB | **756 / 757 (99.9%)** | 364 / 365 |
| **Katip Rules** | Katip's Turkish rules v0.2, 0.3 MB | 751 / 757 (99.2%) | 359 / 365 |
| Vanilla: kvkk-pii | open-source [kvkk-pii](https://pypi.org/project/kvkk-pii/) 0.2 regex layer, default settings (baseline) | 183 / 757 (24.2%) | 0 / 365 |
| **Katip Mask Base** | Katip Rules + [`katip-tr-pii-berturk`](https://huggingface.co/f1k/katip-tr-pii-berturk), 110.8 MB, names + addresses + health terms; on the [Space](https://huggingface.co/spaces/f1k/katip-yerel) only | **757 / 757 (100%)** | **365 / 365** |

**Katip Mask Base v2** is fine-tuned from BERTurk on 8,000 synthetic documents plus 17,967 real
Turkish sentences (Turkish Wiki NER, names only), 3 epochs in 28 minutes on a Mac.

**Full pipeline** (rules + Katip Mask Base, as the demo runs it, [`metrics/accuracy-berturk.json`](metrics/accuracy-berturk.json)):
every value on the blind set (757 / 757, names 365 / 365) and on the held-out set (618 / 618; Nano: 611),
3 false alarms on name-free prose (same as Nano). Model names scored 0.5 or higher keep their edges; that
value was chosen on dev data (Wiki NER dev + held-out), not on the test sets below.

**On real text** (measured in [`lab/`](lab/), names only, rules + model):

| | Real court prose: Yargıtay sentences, anonymised names filled back in | Real Wikipedia sentences (Wiki NER test) |
| --- | --- | --- |
| Katip Rules | 90.6% found, 96.0% precision | 15.0% |
| Katip Mask Nano | 93.9%, 95.9% | 14.8% |
| Katip Mask Base v1 (synthetic only) | 98.6%, 95.9% | 40.7% |
| **Katip Mask Base v2** | **99.3%, 96.2%** | **89.8%** [87.1–92.1], 89.9% precision |

The court set fills the "..." that courts put in place of names (TurkishLegalNER, Çetindağ et al. 2022,
Apache-2.0) with common Turkish names, in court casing, with the case suffix re-inflected; a second version
with rare unseen names scores within 0.5 points. Scripts: `lab/score_legal.py`, `lab/score_model.py`.

It is 40 times bigger than Katip Mask Nano, so the demo keeps Nano as the default and offers Katip Mask Base on
the Hugging Face Space (its 110.8 MB file is over GitHub's 100 MB limit for Pages).

### Size, speed and accuracy side by side

| | Download | Detection time per document (text, no OCR) | Blind set | Held-out set |
| --- | --- | --- | --- | --- |
| Vanilla kvkk-pii | 0.1 MB | 1 ms | 183 / 757 (24.2%) | 154 / 618 |
| Katip Rules | 0.3 MB | 3 ms | 751 / 757 (99.2%) | 605 / 618 |
| Katip Mask Nano | + 2.6 MB | 7 ms | 756 / 757 (99.9%) | 611 / 618 |
| Katip Mask Base v2 | + 110.8 MB | 27 ms | **757 / 757 (100%)** | **618 / 618** |

**Shrinking.** Both models ship as int8 ONNX: Katip Mask Nano 10.0 → 2.6 MB, Katip Mask Base 440.3 → 110.8 MB (4×
smaller each). All scores above were measured on the int8 files, so quantising cost no accuracy. For OCR,
the compact Turkish model is 2 MB instead of 7.7 MB with about the same recall (49 vs 48 misses on 96 scans).
**Timings** are onnxruntime in Python, Nano and the rules on a 4-core cloud VM, Katip Mask Base on an Apple-silicon
Mac; browser timings (WebAssembly, one thread) are slower and not measured yet. Distilling BERTurk to a
size that fits GitHub Pages is on the roadmap.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="metrics/accuracy-dark.svg">
  <img alt="Share of values found by data type on the blind set" src="metrics/accuracy-light.svg" width="720">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="metrics/speed-dark.svg">
  <img alt="Time per document and share of values still readable after masking, by format" src="metrics/speed-light.svg" width="720">
</picture>

**What these numbers do not show yet.** The blind and held-out documents are synthetic, and 12 of the 16 blind
styles share templates with the training data, so real case files will score lower. Timings come
from a cloud VM, not a typical laptop. Raw numbers: [`metrics/`](metrics/). Scripts:
`ml/benchmark.py`, `ml/make_charts.py`. Help us measure on real documents: see [Contact](#questions-pilots-and-contact).

## What Katip adds on top of the base models

| Base | On its own | With Katip (measured, blind set) |
| --- | --- | --- |
| [kvkk-pii](https://pypi.org/project/kvkk-pii/) 0.2, open-source Turkish PII regex | 183 / 757 values (24.2%), 0 of 365 names | 756 / 757 (99.9%), 364 / 365 names |
| Katip's own rules | 359 / 365 names (98.4%) | 364 / 365 with the 2.6 MB tagger, no new false names |
| [BERTurk](https://huggingface.co/dbmdz/bert-base-turkish-cased) | a language model with no PII labels | 757 / 757 values with Katip's rules; alone: names 364 / 365, addresses 80 / 80, health terms 26 / 26 |
| Tesseract `tur` | text only, no check that a value is really gone | every masked value is searched for again in a second OCR pass of the output; the compact OCR model is 4× smaller with about the same recall (49 vs 48 misses on 96 scans) |

**Next:** add a stock Turkish NER model as a second baseline in the demo, distil BERTurk into a model
small enough for GitHub Pages, and repeat every measurement on consented real documents from pilot firms.

## What it supports

| Documents | How |
| --- | --- |
| PDF with a text layer | true removal of the glyphs under each box (MuPDF `applyRedactions`), metadata scrubbed |
| Scanned PDF, photos (PNG, JPG) | OCR (Tesseract for printed scans, PaddleOCR for handwriting and phone photos), boxes burned into the image |
| Word `.docx` | text, tracked deletions, comment authors and document properties masked |
| UYAP `.udf` | masked in place, stays a valid UDF |
| Plain text | |

| Data type | Detection |
| --- | --- |
| T.C. kimlik no, VKN, IBAN, card number | checksum-validated patterns |
| Phone, e-mail, plate, birth date | Turkish formats with context words |
| Address | Turkish address structure (Mh., Cd., Sk., No, district/province) |
| Person names | gazetteers, cue words (Av., Sayın, davacı …), casing and suffix rules, plus an on-device name tagger |
| KVKK art. 6 special categories (health, union, …) | lexicon, flagged for review |

Context it has been tested on: petitions, judgments, leases, employment contracts, invoices,
privacy notices, powers of attorney, notices, letters, e-mails, hearing minutes, chat logs,
discharge summaries (epikriz) and expert reports.

## Try it

- **Demo:** https://fikrifirat.github.io/katip/ (or the [Hugging Face Space](https://huggingface.co/spaces/f1k/katip-yerel)).
  Pick one of 16 sample documents to see live recall, precision, misses and false alarms against its
  answer key, or open your own file.
- The document shows up as soon as you pick it; detected values are highlighted on the page itself.
- One review screen: tick or untick each value (on the page or in the list), add missed terms, then
  **Apply masks** and download. Choose the mask colour, an optional one-line credit and an optional Katip logo across the middle of each page (PDF and images).
- Switch the detection model, OCR model, confidence threshold and data types; Turkish and English interface.
- **Report a mistake** (*Hata bildir*) builds a small report (settings, scores, the masked output,
  and the original only if you tick it) and opens an e-mail draft.

## How it works

| Step | Component |
| --- | --- |
| Detection rules | Katip's Python recognizers and word lists, unchanged, in Pyodide (Python compiled to WebAssembly) |
| Name tagger | [`katip-tr-name-tagger-tiny`](https://huggingface.co/f1k/katip-tr-name-tagger-tiny), 2.6 MB int8 ONNX, transformers.js; or [`katip-tr-pii-berturk`](https://huggingface.co/f1k/katip-tr-pii-berturk) (names, addresses, health), 110.8 MB |
| Text, UDF, Word | standard-library Python in Pyodide (`src/py/local_formats.py`) |
| PDF | MuPDF.js |
| Scans and photos | tesseract.js with the Turkish model; PaddleOCR PP-OCRv5 (small detector + Latin recogniser, 13 MB ONNX) on pages with ballpoint ink or a photographed sheet ([lab/ocr_bench](lab/ocr_bench/README.md)) |
| Leak check | the output is read again (text layer or a second OCR pass) for every masked value |

The browser rules give exactly the same results as Katip's server engine (0 differences on 1,803
spans), and the browser tagger matches Python onnxruntime (0 differences on 152 spans, for both the
name-only and the multi-type model code).

## Roadmap

- [x] Fully in-browser redaction for PDF, scans, photos, Word, UDF, text
- [x] On-device name tagger, public demo, Hugging Face Space and model
- [x] BERTurk model for names, addresses and health terms ([`ml/berturk/`](ml/berturk/))
- [x] Full pipeline with BERTurk: 757 / 757 on the blind set
- [ ] A smaller distilled BERTurk that fits on GitHub Pages
- [ ] A stock Turkish NER model as a second baseline in the demo
- [ ] Evaluation on real, consented documents from pilot firms
- [ ] Laptop and phone timings; smaller first download
- [ ] Organisation and court names, case numbers, more KVKK art. 6 categories
- [ ] Excel, e-mail (`.eml`, `.msg`) and batch folders
- [ ] Packaged as a browser extension and a desktop app for offline use

## Questions, pilots and contact

- Questions, missed redactions, feature requests: [open an issue](https://github.com/fikrifirat/katip/issues/new/choose).
  Please never paste real personal data; use the demo's *Hata bildir* button or fake values.
- Pilots in your firm, integration or a commercial licence: **fikrifirat@gmail.com**.

## Develop

```bash
npm install
python3 src/build_site.py <path-to-katip-redact> node_modules docs --source https://github.com/fikrifirat/katip
python3 docs/serve.py
```

`npm install` fetches Pyodide, MuPDF, tesseract.js, transformers.js and JSZip; `serve.py` serves the site at http://127.0.0.1:8765.

`build_site.py` copies the detection code from the Katip server repository (one source of truth)
and the sample documents from its `eval/blind` set.

- **GitHub Pages:** Settings → Pages → Deploy from a branch → `main` / `/docs`.
- **Hugging Face:** `./publish_hf.sh` (after `hf auth login`) uploads the models and the Space.

| Test | Checks |
| --- | --- |
| `src/tests/parity.mjs` + `parity_server.py` | browser rules = server engine, span by span |
| `src/tests/tests_parity_tagger.cjs` + `ml/parity_py.py` | browser tagger = Python onnxruntime |
| `src/tests/tests_e2e_demo.cjs` | Chromium: every format, report flow, 0 requests to other origins |
| `ml/eval_system.py`, `ml/benchmark.py` | name recall with and without the tagger; all data types |

Training: `ml/gen_train.py` + `ml/train.py` (tiny tagger, about 6 minutes on CPU) and
[`ml/berturk/`](ml/berturk/) (BERTurk fine-tune for a Mac or GPU).

## Licence

Code and demo: **[AGPL-3.0](LICENSE)**, with a **commercial licence** for use in products, internal
systems or hosted services without the AGPL's source-sharing obligation; see [COMMERCIAL.md](COMMERCIAL.md).
Models: CC BY-NC 4.0.

Third-party parts: MuPDF (AGPL-3.0, Artifex), kvkk-pii (MIT, Aleonis; baseline only), Inter and Space Grotesk fonts (SIL OFL 1.1), Pyodide (MPL-2.0), tesseract.js and the `tur` model
(Apache-2.0), PaddleOCR PP-OCRv5 models (Apache-2.0, PaddlePaddle), transformers.js (Apache-2.0), ONNX Runtime (MIT), `common_words.txt` from the
OpenSubtitles frequency list (CC BY-SA 4.0). Sample documents are synthetic; any resemblance to
real people is accidental.
