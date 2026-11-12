# Fine-tune BERTurk for Katip (run on your own machine)

Trains BERTurk to tag **names, addresses and KVKK art. 6 health terms**, scores it on Katip's blind,
held-out and name-free sets, and exports ONNX for the browser. The training data is in `data/`
(synthetic, ~2 MB), so nothing else needs downloading except the base model (~440 MB, once).

## Mac (Apple silicon) steps

```bash
git clone https://github.com/fikrifirat/katip && cd katip/ml/berturk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python train_berturk.py --limit 300 --epochs 1
python train_berturk.py
```

The first command is a smoke test (a few minutes); the second is the full run (roughly 30-60 min on M1-M3).

It picks the Apple GPU (MPS) automatically and prints dev scores after each epoch and the final
scores at the end. Output goes to `out/`: `results.json`, the PyTorch weights, `onnx/model.onnx`
(~440 MB) and `onnx/model_quantized.onnx` (~110 MB, the one the browser would use).

## After training

Score the whole pipeline (rules + this model, every data type) with the same code the browser runs,
from the repository root:

```bash
source ml/berturk/.venv/bin/activate
pip install numpy onnxruntime tokenizers regex
KATIP_MODEL=ml/berturk/out python3 ml/benchmark.py ml/berturk/data berturk > metrics/accuracy-berturk.json
```

The training venv already has these packages; on a Homebrew or system Python outside a venv, `pip install` is refused (PEP 668).

Publish the model and put its browser files in the Hugging Face Space (no retraining), from the
repository root, after `hf auth login`:

```bash
./publish_hf.sh
```

The int8 model is 110.8 MB, over GitHub's 100 MB file limit, so GitHub Pages lists Katip BERTurk
with a link to the Space, where it runs.

## v2: learn names from real text (recommended)

The v1 model was trained on synthetic documents only. It finds every name in Katip's synthetic blind
set, but only about 41% of names in real Turkish sentences once Katip's rules are added. Mixing
17,967 real sentences from Turkish Wiki NER (Altinok 2023, CC BY-SA 4.0) into training took the
names-only lab version to **90%** at 90% precision (`lab/04_distill_berturk.ipynb`).

From `ml/berturk`, with the venv active:

```bash
python train_berturk.py --real-text --limit 300 --epochs 1
python train_berturk.py --real-text
```

The first is a smoke test; the second takes about 35-50 min on an M1-M3. Then, from the repository root:

```bash
python lab/score_model.py ml/berturk/out
KATIP_TRUST=0.5 python3 ml/benchmark.py ml/berturk/data berturk > metrics/accuracy-berturk.json
```

`score_model.py` picks the trust setting on the dev sets and prints real-text recall on the sealed
Wiki NER test set. Use the trust it prints in the second command (0.5 in the lab).

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
