# Bundled name model

`katip-mask-nano-tr-v1.1/` is **Katip Mask Nano · tr v1.1** (2.5 MB int8 ONNX), the retrain with
foreign client names from PR #7 (Tiny-F in `lab/foreign`). It runs at trust 0.5 (`katip.json`).
Licence: CC BY-NC 4.0. Court sentences: Turkish names 98.8% recall, foreign names 94.9%.

Other models, such as Katip Mask Base · tr v2 (110 MB, [f1k/katip-tr-pii-berturk](https://huggingface.co/f1k/katip-tr-pii-berturk)),
go in `~/.katip/models/` and win over the bundled one:

    katip-kalkan install-model ~/Downloads/katip-tr-pii-berturk --trust 0.5

or set `KATIP_MODEL=/path/to/model`. `KATIP_MODEL=none` runs rules only.
