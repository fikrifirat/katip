# katip-mask

Detect and mask Turkish personal data (KVKK) in text, locally. It uses the same rules as the
[Katip demo](https://fikrifirat.github.io/katip) and the Katip Kalkan connector, with optional small name
models (ONNX). A JavaScript version with identical output is on npm as
[`katip-mask`](https://www.npmjs.com/package/katip-mask).

```bash
pip install katip-mask            # rules only, no dependencies
pip install "katip-mask[model]"   # adds onnxruntime and numpy for the name models
```

```python
from katip_mask import Masker

masker = Masker("ai", model="mini")
result = masker.mask(text)

result.text      # 'Davacı [AD SOYAD-1] (T.C. Kimlik No: [T.C. KİMLİK NO-1]) ...'
result.spans     # what was masked, with offsets, type and score
result.mapping   # {'[AD SOYAD-1]': 'Ahmet YILMAZ', ...}

result.restore(answer)   # put the original values back, e.g. into an LLM's reply
```

## Limits

How Katip handles data, and what masking does and does not do under KVKK: [PRIVACY.md](https://github.com/fikrifirat/katip/blob/main/PRIVACY.md).


Each detected value is masked everywhere it appears in the text, or `mask()` raises `LeakError`.
Values the detector misses stay in the text, so check the output before relying on it. Detection rates
by document type and model are on the [KVKK-Bench leaderboard](https://huggingface.co/spaces/f1k/kvkk-bench).

Text never leaves the machine. The only network call is the model download, which happens only when you
pass `model=`.

## Profiles

| profile | use | masks | leaves readable |
|---|---|---|---|
| `court` (default) | court filings | names, ID/passport/tax numbers, IBAN, cards, phones, e-mails, plates, birth dates, IPs, building and door numbers, health and other special-category data | street, district, province, case numbers, dates, courts, precedent citations |
| `ai` | sending text to an LLM | `court`, plus full addresses, case and UYAP numbers, bar numbers, criminal-record terms | dates, places, institutions, precedent citations |
| `anon` | publishing, research | `ai`, plus dates, places, courts, companies and institutions | precedent citations |

## Options

```python
Masker(
    profile="court",       # "court" | "ai" | "anon"
    model=None,            # None (rules only) | "mini" | "nano" | "base" | path to a model folder
    threshold=0.5,         # minimum confidence
    entities=None,         # replace the profile's entity types (see katip_mask.ENTITY_TYPES)
    address_detail=None,   # "street" | "full"; default comes from the profile
    allow=(),              # never mask these terms
    deny=(),               # always mask these terms
    style="label",         # "label": [AD SOYAD-1], reversible; "block": ██████
)
masker.mask(text, ocr_ranges=[(0, len(text))])   # mark OCR text so misread ID numbers are still caught
masker.detect(text)                                # spans only
```

`mask()`, `detect()` and `restore()` are also available as functions. Offsets are Python string indices.

## Models

| model | size | |
|---|---|---|
| `nano` | 2.6 MB | fastest, weaker on informal text |
| `mini` | 31 MB | recommended |
| `base` | 111 MB | most accurate, also tags addresses and health terms |

Models are downloaded from Hugging Face ([f1k/katip-mask-mini](https://huggingface.co/f1k/katip-mask-mini)
and siblings) at a fixed commit and checked against SHA-256 hashes in the package. They are cached in
`~/.cache/katip-mask` (or `$KATIP_MASK_CACHE`), which the Node package shares.

```bash
katip-mask download mini       # fetch ahead of time
export KATIP_MASK_OFFLINE=1    # never use the network
export KATIP_MASK_ENDPOINT=https://your-mirror.example
```

## Command line

```bash
katip-mask mask dilekce.txt --profile ai --model mini > maskeli.txt
katip-mask mask dilekce.txt --json > result.json
katip-mask restore cevap.txt --mapping result.json
katip-mask detect dilekce.txt
```

The JSON matches the JavaScript CLI's. Exit code 3 means masking was refused (`LeakError`).

## Licence

Code: AGPL-3.0, or a [commercial licence](https://github.com/fikrifirat/katip/blob/main/COMMERCIAL.md).
Models: CC BY-SA 4.0, based on BERTurk (dbmdz, MIT).
Citation: [CITATION.cff](https://github.com/fikrifirat/katip/blob/main/CITATION.cff).
