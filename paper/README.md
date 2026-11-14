# KVKK-Bench paper (draft)

`main.tex` + `refs.bib` → `main.pdf` (`pdflatex main && bibtex main && pdflatex main && pdflatex main`).

Every number comes from the KVKK-Bench v0.1.2 public split and the saved predictions on the `legal-study`
branch (`lab/legal/bench/results`, `lab/legal/bench/preds`), which are identical to the files on the live
Space `f1k/kvkk-bench` (checked 14 Nov 2026).

* `bootstrap_ci.py`: sentence-clustered bootstrap (10,000 resamples, seed 20261114) for Table 1 and the paired
  comparisons; output in `bootstrap_output.txt`. Run it in a `legal-study` checkout after building the public split.
* `make_fig.py`: Figure 1 from `bootstrap_samples.json` (written by `bootstrap_ci.py`).

Items marked *pending* in the PDF are not results yet.
