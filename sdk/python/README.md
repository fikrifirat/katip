# katip-mask (Python)

Find and mask Turkish personal data (KVKK) in text, on your own machine. Same detection engine as the
[Katip web demo](https://fikrifirat.github.io/katip) and the Katip Kalkan connector, plus optional small
name models that run locally with ONNX Runtime. A JavaScript package with identical output is on npm as
[`katip-mask`](https://www.npmjs.com/package/katip-mask).

```bash
pip install katip-mask            # rules only, no dependencies
pip install "katip-mask[model]"   # + on-device name models (onnxruntime, numpy)
```

```python
from katip_mask import Masker

masker = Masker("ai", model="mini")       # profile + model; model=None runs the rules only
result = masker.mask(open("dilekce.txt", encoding="utf-8").read())

result.text      # 'Davacı [AD SOYAD-1] (T.C. Kimlik No: [T.C. KİMLİK NO-1]) ...'
result.spans     # (Span(entity_type='PERSON', start=7, end=19, text='Ahmet YILMAZ', score=0.95, ...), ...)
result.mapping   # {'[AD SOYAD-1]': 'Ahmet YILMAZ', ...}  keep this on your side

answer = call_your_llm(result.text)       # the model only ever sees placeholders
print(result.restore(answer))             # placeholders back to the real values
```

## What it promises, and what it does not

Every value the detector finds is masked **everywhere** it occurs in the text (other spellings of the
same value included, case-insensitive), or `mask()` raises `LeakError` instead of returning text. That
is the whole guarantee. A value the detector does not find is not masked, so this is not a promise that a
document is anonymous or "KVKK-compliant": review the output where it matters. Detection quality per
document type and per model is published on the
[KVKK-Bench leaderboard](https://huggingface.co/spaces/f1k/kvkk-bench).

Nothing is sent anywhere. The only network access is the one-time model download you ask for
(`model="mini"`), from Hugging Face at a pinned commit, with every file checked against a SHA-256 in the
package before it is used.

## Profiles

One argument sets which data types are masked and how much of an address stays readable. Each profile
masks everything the one before it does.

| profile | for | masks | keeps readable |
|---|---|---|---|
| `court` (default) | evidence and petition attachments | all personal data: names, T.C./YKN/passport/foreign IDs, tax no, IBAN, cards, phones, e-mails, plates, birth dates, IPs, building/door/flat numbers, KVKK art. 6 special categories | mahalle, street, district, province, case numbers, dates, court names, precedent citations |
| `ai` | sending a document to ChatGPT, Claude, etc. | `court` + whole addresses, case/UYAP numbers, bar/registry numbers, criminal-record terms | dates, places, institutions, precedent citations |
| `anon` | publishing, research | `ai` + dates, provinces/districts, court, company and institution names | precedent citations (public law) |

The entity types and Turkish placeholder names are in `katip_mask.ENTITY_TYPES` and `katip_mask.LABELS_TR`.

## Options

```python
Masker(
    profile="court",          # "court" | "ai" | "anon"
    model=None,               # None | "mini" | "nano" | "base" | "/path/to/model-folder"
    threshold=0.5,            # minimum confidence for a rule or model hit
    entities=None,            # your own list of types instead of the profile's
    address_detail=None,      # "street" | "full" (default: the profile's)
    allow=(),                 # terms never masked, e.g. your firm's name
    deny=(),                  # terms always masked, e.g. client names you know in advance
    style="label",            # "label" -> [AD SOYAD-1] (reversible), "block" -> ██████
)
masker.mask(text, ocr_ranges=[(0, len(text))])   # text that came from OCR: misread IDs are still caught
masker.detect(text)                                # spans only
```

`mask(text, profile, **options)`, `detect(...)` and `restore(text, mapping)` are one-call shortcuts.
Offsets are Python string indices (code points).

## Models

| model | size | runs | note |
|---|---|---|---|
| `nano` | 2.6 MB | fastest | finds names well in court text, misses more in everyday prose |
| `mini` | 31 MB | fast | recommended: names in court text and in petitions, e-mails, messages |
| `base` | 111 MB | slower | most accurate; also tags addresses and health terms |

The models are CC BY-SA 4.0 ([f1k/katip-mask-mini](https://huggingface.co/f1k/katip-mask-mini) and siblings),
built on BERTurk by dbmdz (MIT). They are downloaded on first use into `~/.cache/katip-mask` (or
`$KATIP_MASK_CACHE`), shared with the JavaScript package in Node.

```bash
katip-mask download mini        # e.g. while building a container image
export KATIP_MASK_OFFLINE=1     # then never touch the network
export KATIP_MASK_ENDPOINT=https://your-mirror.example   # or HF_ENDPOINT
```

## Command line

```bash
katip-mask mask dilekce.txt --profile ai --model mini > maskeli.txt
katip-mask mask dilekce.txt --json > result.json
katip-mask restore cevap.txt --mapping result.json
katip-mask detect dilekce.txt
```

The `--json` output is the same from the JavaScript CLI, so the two are interchangeable. Exit code 3 means masking was refused because a detected value would have stayed readable.

## Licence

Code: AGPL-3.0, with a commercial licence for products, internal systems or hosted services that cannot
meet the AGPL's source-sharing terms (see
[COMMERCIAL.md](https://github.com/fikrifirat/katip/blob/main/COMMERCIAL.md)). Models: CC BY-SA 4.0.
Cite with [CITATION.cff](https://github.com/fikrifirat/katip/blob/main/CITATION.cff).
