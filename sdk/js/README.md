# katip-mask

Detect and mask Turkish personal data (KVKK) in Node or the browser, locally. It uses the same rules as
the [Katip demo](https://fikrifirat.github.io/katip) and the Katip Kalkan connector, with optional small
name models (ONNX). The output is identical to the Python package
[`katip-mask`](https://pypi.org/project/katip-mask/).

```bash
npm install katip-mask                     # rules only, no dependencies
npm install katip-mask onnxruntime-node    # name models in Node
npm install katip-mask onnxruntime-web     # name models in the browser
```

```ts
import { Masker } from "katip-mask";

const masker = await Masker.create({ profile: "ai", model: "mini" });
const result = await masker.mask(text);

result.text;     // "Davacı [AD SOYAD-1] (T.C. Kimlik No: [T.C. KİMLİK NO-1]) ..."
result.spans;    // what was masked, with offsets, type and score
result.mapping;  // { "[AD SOYAD-1]": "Ahmet YILMAZ", ... }

result.restore(answer);  // put the original values back, e.g. into an LLM's reply
```

Rules only, synchronous, no download:

```ts
const { text } = new Masker({ profile: "court" }).maskSync(input);
```

## Limits

Each detected value is masked everywhere it appears in the text, or `mask()` rejects with `LeakError`.
Values the detector misses stay in the text, so check the output before relying on it. Detection rates
by document type and model are on the [KVKK-Bench leaderboard](https://huggingface.co/spaces/f1k/kvkk-bench).

Text never leaves the device. The only network call is the model download, which happens only when you
pass `model`.

## Profiles

| profile | use | masks | leaves readable |
|---|---|---|---|
| `court` (default) | court filings | names, ID/passport/tax numbers, IBAN, cards, phones, e-mails, plates, birth dates, IPs, building and door numbers, health and other special-category data | street, district, province, case numbers, dates, courts, precedent citations |
| `ai` | sending text to an LLM | `court`, plus full addresses, case and UYAP numbers, bar numbers, criminal-record terms | dates, places, institutions, precedent citations |
| `anon` | publishing, research | `ai`, plus dates, places, courts, companies and institutions | precedent citations |

## Options

```ts
await Masker.create({
  profile: "court",         // "court" | "ai" | "anon"
  model: null,              // null (rules only) | "mini" | "nano" | "base" | a loaded NameModel
  threshold: 0.5,           // minimum confidence
  entities: undefined,      // replace the profile's entity types (see ENTITY_TYPES)
  addressDetail: undefined, // "street" | "full"; default comes from the profile
  allow: [],                // never mask these terms
  deny: [],                 // always mask these terms
  style: "label",           // "label": [AD SOYAD-1], reversible; "block": ██████
  modelBaseUrl: undefined,  // load model files from `${modelBaseUrl}/${model}/${file}`
  offline: false,           // fail instead of downloading
  ort: undefined,           // your own onnxruntime module
  onProgress: undefined,    // download progress callback
});

await masker.mask(text, { ocrRanges: [[0, text.length]] });  // mark OCR text so misread ID numbers are still caught
await masker.detect(text);                                   // spans only
```

`mask()`, `detect()` and `restore()` are also exported as functions. Offsets are UTF-16 indices, so
`text.slice(span.start, span.end) === span.text`.

## Models

| model | size | |
|---|---|---|
| `nano` | 2.6 MB | fastest, weaker on informal text |
| `mini` | 31 MB | recommended |
| `base` | 111 MB | most accurate, also tags addresses and health terms |

Models are downloaded from Hugging Face ([f1k/katip-mask-mini](https://huggingface.co/f1k/katip-mask-mini)
and siblings) at a fixed commit and checked against SHA-256 hashes in the package.

**Node:** cached in `~/.cache/katip-mask` (or `$KATIP_MASK_CACHE`), shared with the Python package.
`npx katip-mask download mini` fetches one ahead of time; `KATIP_MASK_OFFLINE=1` disables downloads.

**Browser:** cached in Cache Storage. Bundlers pick the browser build automatically. onnxruntime-web
loads `.wasm` files at run time, so set `ort.env.wasm.wasmPaths` and pass the module in:

```ts
import * as ort from "onnxruntime-web";
ort.env.wasm.wasmPaths = "/ort/";  // copied from node_modules/onnxruntime-web/dist
const masker = await Masker.create({ profile: "ai", model: "mini", ort });
```

With a strict Content Security Policy, host the model files yourself and set `modelBaseUrl`. The hashes
are checked either way.

## Command line

```bash
npx katip-mask mask dilekce.txt --profile ai --model mini > maskeli.txt
npx katip-mask mask dilekce.txt --json > result.json
npx katip-mask restore cevap.txt --mapping result.json
npx katip-mask detect dilekce.txt
```

The JSON matches the Python CLI's. Exit code 3 means masking was refused (`LeakError`).

## Licence

Code: AGPL-3.0, or a [commercial licence](https://github.com/fikrifirat/katip/blob/main/COMMERCIAL.md).
Models: CC BY-SA 4.0, based on BERTurk (dbmdz, MIT).
Citation: [CITATION.cff](https://github.com/fikrifirat/katip/blob/main/CITATION.cff).
