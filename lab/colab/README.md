# Training notebooks (Colab / Kaggle, free T4 GPU)

Each notebook clones this repo, downloads public data and the teacher from Hugging Face, runs a 5-minute smoke test,
then the full run, and gives you a zip (and, if you add an `HF_TOKEN` secret, a private Hugging Face upload).
No secrets are stored in the notebooks.

| Notebook | What | Time on a T4 | Open in Colab |
|---|---|---|---|
| `katip_mask_mini.ipynb` | Katip Mask Mini, 15-30 MB, taught by Base | ~2 h | [open](https://colab.research.google.com/github/fikrifirat/katip/blob/legal-study/lab/colab/katip_mask_mini.ipynb) |
| `katip_mask_nano_v2.ipynb` | Nano v2, same 2.5 MB size, taught by Base on real text | ~40 min | [open](https://colab.research.google.com/github/fikrifirat/katip/blob/legal-study/lab/colab/katip_mask_nano_v2.ipynb) |
| `xlmr_katip_recipe.ipynb` | XLM-R base with Base v2's recipe | ~1 h | [open](https://colab.research.google.com/github/fikrifirat/katip/blob/legal-study/lab/colab/xlmr_katip_recipe.ipynb) |
| `katip_mask_base_clean.ipynb` | Base without Wikipedia data (Apache-2.0 candidate); needs your court-decision `train.jsonl` | ~1 h | [open](https://colab.research.google.com/github/fikrifirat/katip/blob/legal-study/lab/colab/katip_mask_base_clean.ipynb) |

In Colab: Runtime > Change runtime type > T4 GPU, then Runtime > Run all.
