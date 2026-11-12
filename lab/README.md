# Katip lab: small models, real text, measured properly

Seven notebooks, three studies, all on a laptop. Each one starts from a concrete problem, writes down
what would count as success before training, keeps a test set sealed until the end, and reports
confidence intervals and a paired significance test.

## What we found so far (reference run, 12 Nov 2026, 4-core Linux VM)

| Study | Problem | Result |
| --- | --- | --- |
| **1 · Tiny-R** (notebooks 00–03) | Katip Tiny finds 99.7% of names on our synthetic blind set but **14.8%** in real Turkish sentences (Turkish Wiki NER test) | Same 2.57 MB model, same recipe, real sentences mixed into training: **55.2%** [50.5–59.7], +40.4 points, McNemar p = 1.5e-76; blind set unchanged (99.7%); 3 false names on legal prose (was 2). All 4 pre-registered checks pass. |
| **2 · Distillation** (04) | BERTurk is 110.8 MB; can its knowledge fit in 2.6 MB? | Ready to run on your Mac. Not run here: Hugging Face is blocked in our build sandbox, so it was only smoke-tested with a stand-in teacher. |
| **3 · Certified recall** (05) | "99.9% on average" is not a promise a lawyer can use | Tiny-R can promise "at most 5% of name words readable" on real text by masking or reviewing **12.9%** of other words. The published Tiny can't keep even a 20% promise without masking 99.8% of words. Calibrating on synthetic documents breaks the promise on real text (87% readable). |
| **4 · Suffix leakage** (06) | Katip masks *Öztürk* but keeps *'ün*, and the suffix agrees with the hidden name | 28% of names in real prose carry a suffix (4% in our synthetic data). One suffix reveals **2.4 bits** on average (up to 6.7 bits). Re-inflecting it to agree with the placeholder (`[AD SOYAD]'ın`) brings that to 0 bits and keeps the sentence grammatical. |

Reports and charts from that run are in `reference/`. Expect small differences on your machine
(different CPU, PyTorch version and thread count).

## The notebooks

| Notebook | What you do | Time on a laptop |
| --- | --- | --- |
| `00_setup` | check the environment, download Wiki NER, prove the lab runs the browser's own code, reproduce the README number | 3 min |
| `01_reality_check` | score Rules, Tiny (and your BERTurk) on real text; find out why names are missed | 5 min |
| `02_train_with_real_text` | pre-register, train the tagger with 0 to 18k real sentences, learning curves, pick a setting on dev | quick 20 min / full 1.5 h |
| `03_test_and_report` | open the sealed test once, significance tests, size vs accuracy chart, PASS/FAIL, `results/REPORT.md` | 3 min |
| `04_distill_berturk` | fine-tune BERTurk-R as a teacher, distil it into a 2.6 MB student, test once | smoke 5 min / quick ~1 h |
| `05_certified_recall` | conformal risk control: the threshold that keeps a stated miss rate, and what it costs per model | 3 min |
| `06_suffix_leakage` | measure what case suffixes reveal; test the re-inflection fix | 2 min |

Order: 00 → 01 → 02 → 03, then 04, then 05 (it includes 04's models if they exist). 06 stands
alone. In 04, run `MODE = "smoke"` first, then `"quick"`.

## Run it

Copy this `lab/` folder into the repository root (next to `ml/`, `docs/`, `hf/`). Then, from the
repository root, with the BERTurk virtual environment (Homebrew Python refuses `pip` outside a venv):

```
cd /Users/f1k0/Development/Personal/Projects/active/katip
source ml/berturk/.venv/bin/activate
pip install -r lab/requirements.txt
jupyter lab lab/
```

Run each notebook top to bottom. A failed checkpoint (`assert`) stops the notebook, so you never get
numbers you can't trust.

## Rules the notebooks follow

* **Reproduce first.** Notebook 00 must reproduce 364/365 on the blind set with the browser's own code.
* **One variable at a time.** Notebook 02 changes only the training data, and notebook 04 changes only the loss.
* **Pre-register.** Hypotheses and the selection rule go into `results/*_prereg.json` before training,
  and the file can't be overwritten.
* **Choose on dev, report on test.** Wiki NER dev and Katip's held-out set are for choices; Wiki NER test,
  the blind set and the name-free set are opened once.
* **Intervals, not points.** Document-level bootstrap 95% CIs; paired bootstrap and McNemar for comparisons.
* **Controls.** The published model is also scored with the new trust setting, so a gain can't hide
  inside a knob.

## Files

| Path | |
| --- | --- |
| `katiplab.py` | data loading, the browser-identical model runner (`Tagger`), scoring, bootstrap, Tiny-R training |
| `distill.py` | teacher fine-tuning, soft labels, student training with distillation, dev-rule trust selection |
| `conformal.py` | word scores, loss/cost matrices, conformal risk control, random-split validation |
| `suffix.py` | Turkish case suffixes: abstract form, realisation, compatible names, leak in bits, re-inflection |
| `data/`, `runs/` | downloaded data and trained models (git-ignored, created by the notebooks) |
| `results/` | your run's JSON, CSV, charts and `REPORT.md` |
| `reference/` | the executed notebooks and results from our reference run |

## Data and licences

Turkish Wiki NER: https://github.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset (CC BY-SA 4.0).
Cite: Altinok, D. (2023). *A Diverse Set of Freely Available Linguistic Resources for Turkish*. ACL 2023.
A model trained on it may have to carry ShareAlike terms. Katip's models are CC BY-NC 4.0 today, so
check this before you publish a Tiny-R model.

Conformal risk control: Angelopoulos, Bates, Fisch, Lei, Schuster, *Conformal Risk Control*, ICLR 2024,
https://arxiv.org/abs/2208.02814. Distillation: Hinton, Vinyals, Dean, *Distilling the Knowledge in a
Neural Network*, 2015, https://arxiv.org/abs/1503.02531.
