# katip-mask

Python and JavaScript packages for detecting and masking Turkish personal data, built on the Katip
engine (the same rules as the web demo and Katip Kalkan).

| | install | docs |
|---|---|---|
| Python ≥ 3.10 | `pip install katip-mask` | [python/README.md](python/README.md) |
| Node ≥ 22 and browsers | `npm install katip-mask` (npm release coming) | [js/README.md](js/README.md) |

Both packages return the same text, spans and placeholders for the same input. The only difference is
offsets: Python counts code points, JavaScript counts UTF-16 units.

## Keeping the two in sync

- The Python package vendors `docs/katip_py.zip` unchanged (`tools/sync_engine.py`).
- The JavaScript engine is a TypeScript port. Its regular expressions and character classes are generated
  from the Python source (`tools/gen_js_tables.py`, `tools/pyre2js.py`) to reproduce Python's Unicode and
  case-insensitive matching, including Turkish i/İ/ı.
- `parity/golden.py` records Python's output for the sample documents, mutated copies and generated
  edge cases; the JavaScript tests must reproduce it exactly. CI also runs the models in Python, Node and
  headless Chromium and compares the results.

```bash
python sdk/tools/check.py              # after the engine changes: re-vendor and regenerate (Python 3.14)
python sdk/tools/check.py --check      # CI: fail if anything is stale or versions differ
python sdk/parity/golden.py > sdk/parity/cases.jsonl
cd sdk/js && npm ci && npm run build && npm test
cd sdk/python && pip install -e ".[model,test]" && pytest     # KATIP_MASK_TEST_MODELS=1 to include models
```

`spec/` holds the profiles and model pins used by both packages. `examples/` has an LLM round trip
(Python), a batch script (Node) and a browser page without a build step.

Releasing: [RELEASING.md](RELEASING.md). Changes: [CHANGELOG.md](CHANGELOG.md).
