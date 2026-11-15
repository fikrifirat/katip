# Katip Mask SDKs

Two packages that find and mask Turkish personal data (KVKK) on the user's own machine, with the same
engine as the [web demo](https://fikrifirat.github.io/katip) and the Katip Kalkan connector:

| | install | docs |
|---|---|---|
| Python ≥ 3.10 | `pip install katip-mask` (`"katip-mask[model]"` for the name models) | [python/README.md](python/README.md) |
| JavaScript / TypeScript, Node ≥ 22 and browsers | `npm install katip-mask` (+ `onnxruntime-node` or `onnxruntime-web`) | [js/README.md](js/README.md) |

Both give the same result for the same input and options: same masked text, same spans, same placeholder
mapping, same refusals. Python offsets count code points, JavaScript offsets count UTF-16 units; that is
the only difference.

## The guarantee, and its limit

Every value the detector finds is masked everywhere it occurs, or masking fails with `LeakError` and
returns no text. A value the detector does not find is not masked. Neither package claims that its output
is anonymous or KVKK-compliant; detection rates per document type are on the
[KVKK-Bench leaderboard](https://huggingface.co/spaces/f1k/kvkk-bench).

## How the two packages stay identical

| layer | Python | JavaScript | checked by |
|---|---|---|---|
| rules (recognisers, context words, overlap and merge rules) | `docs/katip_py.zip`, the engine the web demo and Kalkan run, vendored unchanged into `katip_mask/_engine` | TypeScript port; every regular expression and character class is **generated from the Python source** (`tools/pyre2js.py`), reproducing Python's Unicode classes and case-insensitive matching, Turkish i/İ/ı included | `parity/`: 7,380 cases (80 sample documents, mutated copies, 1,500 fuzzed documents with emoji, combining marks, odd spaces, Unicode digits; 185 local evaluation documents) × options, byte-identical |
| propagation, leak check, placeholders | `katip_mask/safety.py` (same steps as Kalkan's `core.py`) | `src/safety.ts` | same parity cases |
| profiles, labels, default threshold, model pins | `spec/profiles.json`, `spec/models.json` | generated `src/spec.generated.ts` | `tools/check.py --check` |
| tokenizer | WordPiece from `tokenizer.json` | same, ported | 20,151 words × 3 models, 0 differences from Hugging Face `tokenizers` |
| name models | ONNX Runtime (Python) | onnxruntime-node / onnxruntime-web | Mini and Nano on the samples: same spans, scores within 2.2e-16 (Node); headless Chromium gives the same spans as Node (`js/test/browser.test.mjs`) |

The generator also verifies that it has seen every regular expression in the engine, so a new rule in
the engine cannot be skipped by the JavaScript port without CI failing.

```bash
python sdk/tools/check.py --check                     # vendored engine, generated tables, spec copy, versions (Python 3.14: tables are pinned to its Unicode 16)
python sdk/parity/golden.py --fuzz 1500 > sdk/parity/cases.jsonl
cd sdk/js && npm ci && npm run build && npm test      # unit, parity and browser tests
cd sdk/python && pip install -e ".[model,test]" && pytest
KATIP_MASK_TEST_MODELS=1 pytest                       # + tests that download and run the models
```

When the engine changes (`src/build_core.py` rebuilds `docs/katip_py.zip`), run `python sdk/tools/check.py`,
then the parity tests. Only a TypeScript change is ever needed by hand, and the parity run shows where.

## Models

Downloaded only when asked for, from Hugging Face at a pinned commit, and verified against the SHA-256 in
`spec/models.json` before use (a file that does not match is deleted and never loaded). Mini is the
recommended default; Nano is the fastest; Base is the most accurate. All CC BY-SA 4.0, built on BERTurk
(dbmdz, MIT).

## Layout

```
sdk/
  spec/           profiles, labels, model pins: the single source for both packages
  python/         katip-mask on PyPI
  js/             katip-mask on npm
  parity/         corpus + golden cases (Python) that the JavaScript tests replay
  tools/          sync_engine.py, gen_js_tables.py, pyre2js.py, check.py
  examples/       LLM round trip (Python), batch folder (Node), browser page with no build step
```

Releasing: [RELEASING.md](RELEASING.md). Changes: [CHANGELOG.md](CHANGELOG.md).
