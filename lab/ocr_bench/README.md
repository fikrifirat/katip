# OCR for handwriting and phone photos: PaddleOCR vs Tesseract

Question: Tesseract cannot read handwriting, so on phone photos of hand-filled lease contracts
(kira sözleşmesi) some TC kimlik numbers and names stayed readable after masking. Does PaddleOCR, which
also runs offline in the browser, fix that without hurting printed scans?

Answer: yes for photos and handwriting, no for printed scans. Katip Yerel's default OCR is now
**Otomatik**: PaddleOCR on pages with ballpoint-blue ink or a sheet cut out of a photo, Tesseract (compact
`tur` model) everywhere else.

All documents are synthetic. No real document was used.

## What was compared

| Reader | Files | Licence |
|---|---|---|
| Tesseract 5 (tesseract.js 7), Turkish `tur` best_int (the current default) | 2 MB | Apache-2.0 |
| PaddleOCR PP-OCRv5 **mobile** detector + **Latin mobile** recogniser (covers ç ğ ı İ ö ş ü) | 4.8 + 8.0 MB ONNX | Apache-2.0 |
| PaddleOCR PP-OCRv5 **server** detector + Latin mobile recogniser | 88 + 8.0 MB ONNX | Apache-2.0 |

Official ONNX exports from huggingface.co/PaddlePaddle, revisions pinned in `src/fetch_paddleocr.py`.
PaddleOCR runs on ONNX Runtime Web (wasm, one thread), with our own pre/post-processing in
`src/paddle_ocr.js`. Everything after OCR (rules, Katip Tiny, pen-ink masking, scoring) is the same browser
pipeline for every reader.

## Sets

* **Photos, tuning** (12): `python lab/photo_forms/make_photo_forms.py DIR --n 12` (seed 1311), the set from
  PR #6. Used to fix two things (below).
* **Photos, held-out** (24): `--n 24 --seed 2026`. Not looked at while tuning; the numbers below are from
  one run after the code was final.
* **Printed scans** (96): the 48 `.scan.pdf` + 48 `.png` documents of `eval/blind` (katip-redact).

Photo scoring (`src/tests/test_photo_forms.mjs`, no OCR in the scoring): a value is leaked when masks cover
less than 70% of its box; a street/mahalle/district that must stay readable is over-masked above 30%.
Scan scoring (`src/tests/test_scan_ocr.mjs`): the masked output is read again with Tesseract for every
reader (same re-reader), and a gold value that is still there counts as readable.

## Results: held-out photos (24 forms, 48 of each value)

| | Tesseract | PaddleOCR mobile | PaddleOCR server det |
|---|---|---|---|
| TC kimlik numbers leaked | **9 / 48** | **0 / 48** | 0 / 48 |
| Names leaked (form rows) | 14 / 48 | 0 / 48 | 0 / 48 |
| Names leaked (signature block) | 6 / 48 | 1 / 48 | 1 / 48 |
| Building/door part leaked | 23 / 48 | 6 / 48 | 9 / 48 |
| Street names kept readable | 90 / 144 | 110 / 144 | 115 / 144 |
| Masks on nothing personal | 0.7 per page | 0.9 per page | 0.5 per page |
| Time per page (Node, 1 thread) | 2.5 s | 6.2 s | 58 s |
| Extra download | – | 13 MB | 96 MB |

Tuning set (12 forms), same order: TC leaked 3 → 0 / 24, names 5 → 0 / 24, signature names 3 → 0,
building/door 16 → 5, streets readable 53 → 60 / 72.

Across both photo sets, Tesseract left 12 of 72 TC numbers readable and PaddleOCR none. The server
detector is not worth 7× the size and 9× the time: no fewer leaks, slightly worse on door numbers.

## Results: printed scans (96 documents, 904 gold values)

| | Tesseract | PaddleOCR mobile (every page) | Otomatik (default) |
|---|---|---|---|
| Still readable after masking, scan.pdf | 0 | 6 | 0 |
| Still readable after masking, png | 1 | 14 | 1 |
| Not detected (scan.pdf / png) | 46 / 49 | 20 / 34 | 46 / 49 |
| Pages sent to PaddleOCR | – | 96 | 0 (identical to Tesseract) |

PaddleOCR *finds* more values on printed scans, but its word boxes are less tight than Tesseract's, so
more values stay partly readable after masking. That is why it is used only where Tesseract fails.

## Two fixes made on the tuning set

1. **Turkish capitals.** The Latin recogniser mixes cases inside capitals (`SözERi`, `HACısALiHOĞLU`), so
   surname rules missed them. A word that is mostly capitals is upper-cased the Turkish way (`fixCase`).
2. **Row matching for pen ink.** PaddleOCR boxes are about a third taller than Tesseract's, so the
   "blue ink in a TC / Adı soyadı row is always masked" rule reached the street row below. On PaddleOCR pages
   the blob's middle must now sit within 0.6 line of the label (`page.engine === "paddle"`); Tesseract pages
   keep the old rule (changing it there made Tesseract worse: TC leaks 3 → 7).

## Limits

* The handwriting is font-drawn (5 OFL fonts) and neater than real handwriting; blue ink makes the
  handwriting switch easy. Real photos may have black pens: those pages go to Tesseract unless the sheet
  was photographed against a background. Choosing "PaddleOCR" by hand is not offered yet; the next step is a
  small set of real, consented photos scored locally.
* 36 photo forms is small: "0 of 48" means the true leak rate is probably below about 6% (one-sided 95%),
  not that it is zero.
* Speed was measured in Node on one thread; in Chromium the first handwritten page also loads the model
  (about 12 s for a page including the load in the Playwright test).

## Re-run

```
npm ci && python src/fetch_paddleocr.py           # models -> src/models/paddleocr (build copies them to docs/vendor/paddleocr)
python lab/photo_forms/make_photo_forms.py /tmp/photo_test --n 24 --seed 2026
node src/tests/test_photo_forms.mjs /tmp/photo_test --ocr tesseract|paddle|auto
node src/tests/test_scan_ocr.mjs <katip-redact>/eval/blind --ocr tesseract|paddle|auto
python docs/serve.py 8770 & node src/tests/tests_e2e_handwriting.cjs /tmp/photo_test/kira_foto_03.pdf
```
