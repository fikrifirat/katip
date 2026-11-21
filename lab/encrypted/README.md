# Encrypted inference: Katip Mask Nano under FHE (experiment 1)

Can a server find the names in a Turkish legal document without ever seeing the document? This folder runs
Katip Mask Nano (f1k/katip-mask-nano, 2-layer BERT, hidden 128) under CKKS homomorphic encryption with
open-source OpenFHE, on CPU, and compares it with the same model in plaintext on KVKK-Bench.

## Split

* **Device (plaintext):** tokenizer, embedding lookup + first LayerNorm, encryption, decryption, Katip's rules.
* **Server (ciphertext only):** both transformer layers and the classifier. It holds evaluation keys and the
  weights, never the secret key.

## Results (20 Nov 2026, 4 vCPU Intel Xeon @ 2.1 GHz, OpenFHE 1.6.1 via openfhe-python, 128-bit security)

KVKK-Bench public names tracks (court-filled 566 docs, prose 1,000 sentences), Katip rules + model at trust 0.5:

| Model | Runs as | KVKK-F2 | court-filled F2 | prose F2 |
| --- | --- | ---: | ---: | ---: |
| Nano (published, int8) | plaintext | 75.8 | 96.7 | 54.9 |
| Nano, attention limited to +-16 tokens | plaintext | 76.1 | 96.6 | 55.5 |
| Nano with rough polynomial stand-ins, no retraining | plaintext | 60.6 | 88.5 | 32.8 |
| **Nano-FHE: fitted polynomials, +-16 attention, no retraining** | plaintext simulation | **74.0** | 96.1 | 51.8 |
| Nano-FHE retrained by distillation (best of 3 recipes) | plaintext simulation | 73.7 | 96.5 | 51.0 |

The retrained variants did not beat the fitted one on dev data (Wiki NER dev prose F2: fitted 49.4, best
retrained 46.7), so the fitted model is the one run encrypted. Recipes were chosen on dev, not on the bench.

Encrypted run of Nano-FHE on one page of bench text (25 documents, 614 words, 1,021 tokens):

| | |
| --- | --- |
| Ring dimension / slots | 65,536 / 32,768 (depth 16, no bootstrapping) |
| Server time | **667 s (11.1 min)** for the page; plaintext Nano on the same 25 documents: 0.02 s |
| Upload per page | 71.3 MB (4 ciphertexts) |
| Download per page | 2.1 MB (1 ciphertext, 3 label scores per token) |
| One-time keys | public 17.8 MB, relinearization 69.2 MB, rotation 4,360 MB |
| Max logit error vs plaintext | 2.6e-5 |
| Token labels identical to plaintext | 100% (1,021 of 1,021) |
| Documents with identical masked spans | 25 of 25 (rules + model, and model only) |

So the encrypted model gives exactly the plaintext simulation's answers on that page, and the bench accuracy
of the encrypted system is the "Nano-FHE fitted" row (74.0 vs 75.8). The price is speed and bytes.

## Take 2: faster on the same CPU (`ServerTake2`, `--take 2`)

openfhe-python releases the GIL, and OpenMP inside a single CKKS operation barely helps at this size (one
operation: same time with 1 or 4 threads; 4 operations side by side: 3.2x). Take 2 runs independent operations on
a thread pool with `OMP_NUM_THREADS=1` and reuses rotations across the linear layers that share an input.

| | Take 1 | Take 2 | Take 2b (attention rotations also parallel) |
| --- | ---: | ---: | ---: |
| Server time per page | 667 s | 432 s | **373 s** |
| Rotations | 3,900 | 2,908 | 2,908 |
| Labels identical to plaintext | 1,021/1,021 | 1,021/1,021 | 1,021/1,021 |

The rest is about 12,400 plaintext-ciphertext multiplications per page, set by the model's multiply-adds.

## Take 3: Belfort eML (`belfort/`)

`eml_nano.py` writes Nano-FHE with eML-supported operations only (Linear, add, tensor products); one encrypted
input of 64 embedded tokens plus a plaintext attention mask, so short windows share a call exactly. It compiles
locally (`compile_eml.py`). `run_belfort.py` runs the same page as the CPU runs: 24 calls, one deploy of at most
30 minutes (needs `BELFORT_API_KEY`; spends credits). `--plaintext-only` checks the packing: the masked page is
identical to the CPU model's (rules + model, 25 of 25 documents).

## What makes it encryption-friendly (`fhe_ops.PolyFHE`)

CKKS can only add and multiply, and each multiplication spends one level. Nano's non-linearities become:

* GELU -> 0.1535 x^2 + 0.5 x + 0.0723 (least-squares fit over Nano's activation range)
* softmax -> (1 + s/3)^2 / n_keys, over +-16 neighbours (no exp, no division by a ciphertext)
* LayerNorm -> gamma (x - mean) / sigma + beta with sigma a constant per LayerNorm, measured on training data

All constants fold into the weights (`ckks_nano.fold`), so a layer costs 8 levels and the classifier folds
into the last LayerNorm.

## Files

| File | |
| --- | --- |
| `nano_torch.py` | Nano rebuilt in PyTorch from the published int8 ONNX (matches it to 0.03 in logits, same labels) |
| `fhe_ops.py` | exact and FHE-friendly non-linearities |
| `ckks_nano.py` | weight folding, CKKS context, block packing (32 features x 1,024 tokens per ciphertext), server, client |
| `train_fhe.py` | distillation of the FHE-friendly student from Nano |
| `dev_select.py` | recipe choice on dev data |
| `score_plain.py` | bench scores in plaintext -> `results/plaintext_scores.json` |
| `run_encrypted.py` | the encrypted run -> `results/encrypted_<run>.json` |

Reproduce (from the repository root, with KVKK-Bench built by `lab/legal/bench_build.py`):

```
pip install torch onnx onnxruntime tokenizers regex transformers huggingface_hub openfhe
python lab/encrypted/score_plain.py nano fitted
python lab/encrypted/run_encrypted.py fitted          # about 15 min and 6 GB RAM on 4 vCPU
```

## Limits

* One page encrypted, not the whole bench: at 11 minutes a page, the 1,566 names-track documents would take
  about a day on this machine. Agreement on the page is exact, so the bench row is the plaintext simulation.
* The server learns the number of tokens (the packing layout), not their content.
* Rotation keys (4.4 GB) dominate the one-time setup; fewer rotations (baby-step giant-step) would cut them.
* Timings are open-source CPU numbers, a floor for what accelerators should improve on, not a forecast.
