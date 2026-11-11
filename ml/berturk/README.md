# Fine-tune BERTurk for Katip (run on your own machine)

Trains BERTurk to tag **names, addresses and KVKK art. 6 health terms**, scores it on Katip's blind,
held-out and name-free sets, and exports ONNX for the browser. The training data is in `data/`
(synthetic, ~2 MB), so nothing else needs downloading except the base model (~440 MB, once).

## Mac (Apple silicon) steps

```bash
git clone https://github.com/fikrifirat/katip && cd katip/ml/berturk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python train_berturk.py --limit 300 --epochs 1      # smoke test, a few minutes
python train_berturk.py                             # full run, roughly 30-60 min on M1-M3
```

It picks the Apple GPU (MPS) automatically and prints dev scores after each epoch and the final
scores at the end. Output goes to `out/`: `results.json`, the PyTorch weights, `onnx/model.onnx`
(~440 MB) and `onnx/model_quantized.onnx` (~110 MB, the one the browser would use).

To publish it on Hugging Face (after `hf auth login`):

```bash
python train_berturk.py --push fikrifirat/katip-tr-pii-berturk
```

Send me `out/results.json` and I'll wire the model into the demo (multi-type support in `src/ner.js`
and the merge policy in `src/py/local_detect.py`) and update the README charts.

## Options

| Flag | Default | |
| --- | --- | --- |
| `--base` | `dbmdz/bert-base-turkish-cased` | any BERT-style model id or folder |
| `--types` | `PERSON,ADDRESS,HEALTH` | Katip entity types to learn |
| `--epochs`, `--bs`, `--lr` | 3, 16, 3e-5 | |
| `--max-tokens` | 256 | window size; the browser uses the same value from `config.json` |
| `--limit N` | all | first N training docs only |
| `--device` | auto | `mps`, `cuda` or `cpu` |
| `--no-onnx` | | skip export |

Organisation names are not in the training data yet, so `ORG` is not a default type.

`data/` was made with `ml/gen_train.py` (train, dev) and from Katip's `eval/blind`, `eval/heldout`
and `eval/negatives` sets.
