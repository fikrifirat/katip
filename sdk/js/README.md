# katip-mask (JavaScript / TypeScript)

Find and mask Turkish personal data (KVKK) in the browser or in Node, on the user's own device. The same
detection engine as the [Katip web demo](https://fikrifirat.github.io/katip), the Katip Kalkan connector and
the Python package [`katip-mask`](https://pypi.org/project/katip-mask/), with identical output, plus
optional small name models that run locally with ONNX Runtime.

```bash
npm install katip-mask                      # rules only, no dependencies
npm install katip-mask onnxruntime-node     # + name models in Node
npm install katip-mask onnxruntime-web      # + name models in the browser
```

```ts
import { Masker } from "katip-mask";

const masker = await Masker.create({ profile: "ai", model: "mini" });  // model: null runs the rules only
const result = await masker.mask(petition);

result.text;     // "Davacı [AD SOYAD-1] (T.C. Kimlik No: [T.C. KİMLİK NO-1]) ..."
result.spans;    // [{ entityType: "PERSON", start: 7, end: 19, text: "Ahmet YILMAZ", score: 0.95, ... }, ...]
result.mapping;  // { "[AD SOYAD-1]": "Ahmet YILMAZ", ... }  keep this on your side

const answer = await callYourLLM(result.text);  // the model only ever sees placeholders
console.log(result.restore(answer));           // placeholders back to the real values
```

Rules only, synchronously, with no download at all:

```ts
const { text } = new Masker({ profile: "court" }).maskSync(petition);
```

## What it promises, and what it does not

Every value the detector finds is masked **everywhere** it occurs in the text (other spellings of the same
value included, case-insensitive), or `mask()` rejects with `LeakError` instead of returning text. That is
the whole guarantee. A value the detector does not find is not masked, so this is not a promise that a
document is anonymous or "KVKK-compliant": review the output where it matters. Detection quality per
document type and per model is published on the
[KVKK-Bench leaderboard](https://huggingface.co/spaces/f1k/kvkk-bench).

Nothing is sent anywhere. The only network access is the one-time model download you ask for
(`model: "mini"`), from Hugging Face at a pinned commit, with every file checked against a SHA-256 in the
package before it is used. `LeakError` carries the entity types and line numbers, never the values.

## Profiles

One option sets which data types are masked and how much of an address stays readable. Each profile masks
everything the one before it does.

| profile | for | masks | keeps readable |
|---|---|---|---|
| `court` (default) | evidence and petition attachments | all personal data: names, T.C./YKN/passport/foreign IDs, tax no, IBAN, cards, phones, e-mails, plates, birth dates, IPs, building/door/flat numbers, KVKK art. 6 special categories | mahalle, street, district, province, case numbers, dates, court names, precedent citations |
| `ai` | sending a document to ChatGPT, Claude, etc. | `court` + whole addresses, case/UYAP numbers, bar/registry numbers, criminal-record terms | dates, places, institutions, precedent citations |
| `anon` | publishing, research | `ai` + dates, provinces/districts, court, company and institution names | precedent citations (public law) |

`PROFILES`, `ENTITY_TYPES` and `LABELS_TR` (the Turkish placeholder names) are exported.

## Options

```ts
await Masker.create({
  profile: "court",        // "court" | "ai" | "anon"
  model: null,             // null | "mini" | "nano" | "base" | a NameModel you loaded
  threshold: 0.5,          // minimum confidence for a rule or model hit
  entities: undefined,     // your own list of types instead of the profile's
  addressDetail: undefined,// "street" | "full" (default: the profile's)
  allow: [],               // terms never masked, e.g. your firm's name
  deny: [],                // terms always masked, e.g. client names you know in advance
  style: "label",          // "label" -> [AD SOYAD-1] (reversible), "block" -> ██████
  // model loading
  modelBaseUrl: undefined, // serve the model files yourself: `${modelBaseUrl}/${model}/${file}`
  offline: false,          // never download; fail unless the model is cached
  fetch: undefined,        // your own fetch (proxy, auth)
  ort: undefined,          // your own onnxruntime module, e.g. onnxruntime-web/webgpu
  onProgress: undefined,   // (message) => void while downloading
});

await masker.mask(text, { ocrRanges: [[0, text.length]] });  // text from OCR: misread IDs are still caught
await masker.detect(text);                                   // spans only
masker.maskSync(text); masker.detectSync(text);              // rules-only Masker
```

`mask(text, options)`, `detect(text, options)` and `restore(text, mapping)` are one-call shortcuts. Span
offsets are UTF-16 indices, so `text.slice(span.start, span.end) === span.text` (also after emoji).

## Models

| model | size | note |
|---|---|---|
| `nano` | 2.6 MB | fastest; finds names well in court text, misses more in everyday prose |
| `mini` | 31 MB | recommended, and the browser default of the Katip demo: names in court text and in petitions, e-mails, messages |
| `base` | 111 MB | most accurate; also tags addresses and health terms; better suited to Node than to a page |

The models are CC BY-SA 4.0 ([f1k/katip-mask-mini](https://huggingface.co/f1k/katip-mask-mini) and
siblings), built on BERTurk by dbmdz (MIT).

**Node.** Files are cached in `~/.cache/katip-mask` (or `$KATIP_MASK_CACHE`), shared with the Python
package. `npx katip-mask download mini` fetches one ahead of time (for a container image), then
`KATIP_MASK_OFFLINE=1` keeps it off the network. `KATIP_MASK_ENDPOINT` (or `HF_ENDPOINT`) points at a mirror.

**Browser.** Files are cached in Cache Storage and verified again on every load. Bundlers pick the browser
build through the `browser` export condition (Vite, webpack, esbuild and Rollup do this by default).
onnxruntime-web loads its `.wasm` files at run time; with a bundler, either copy them from
`node_modules/onnxruntime-web/dist` to your site and set `ort.env.wasm.wasmPaths`, or let it fetch them
from a CDN. Pass your configured module as `ort`:

```ts
import * as ort from "onnxruntime-web";
ort.env.wasm.wasmPaths = "/ort/";

const masker = await Masker.create({ profile: "ai", model: "mini", ort, onProgress: console.log });
```

With a strict Content Security Policy, either allow `connect-src https://huggingface.co` and the CDN it
redirects to, or serve the three model files yourself and pass `modelBaseUrl`. They are checked against
the same pinned hashes either way. `test/browser.test.mjs` runs the package in headless Chromium this way
and checks that the result equals Node's.

## Command line

```bash
npx katip-mask mask dilekce.txt --profile ai --model mini > maskeli.txt
npx katip-mask mask dilekce.txt --json > result.json
npx katip-mask restore cevap.txt --mapping result.json
npx katip-mask detect dilekce.txt
```

The JSON is the same as the Python CLI's (snake_case keys, code point offsets), so the two are
interchangeable. Exit code 3 means masking was refused because a detected value would have stayed readable.

## Same output as Python

The JavaScript engine is a port of the Python one. Every regular expression is compiled from the Python
source by a generator that reproduces Python's Unicode and case-insensitive matching (Turkish dotted and
dotless i included), and the result is tested case by case: thousands of documents and fuzzed variants
must give byte-identical text, spans and mappings in both packages, and the name models must give the
same spans in Node, in the browser and in Python. See
[sdk/README.md](https://github.com/fikrifirat/katip/tree/main/sdk#readme) for how.

## Licence

Code: AGPL-3.0, with a commercial licence for products, internal systems or hosted services that cannot
meet the AGPL's source-sharing terms (see
[COMMERCIAL.md](https://github.com/fikrifirat/katip/blob/main/COMMERCIAL.md)). Models: CC BY-SA 4.0.
Cite with [CITATION.cff](https://github.com/fikrifirat/katip/blob/main/CITATION.cff).
