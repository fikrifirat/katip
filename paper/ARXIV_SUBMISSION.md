# arXiv submission sheet

Upload `kvkk-bench-arxiv-source.tar.gz` (main.tex, main.bbl, refs.bib, fig_overall_size.pdf). It compiles with pdflatex, no bibtex step needed.

* **Title:** KVKK-Bench: Measuring Personal-Data Masking in Turkish Legal Text, with Small On-Device Models
* **Authors:** Fikri Fırat
* **Primary category:** cs.CL (Computation and Language). **Cross-list:** cs.CR (Cryptography and Security).
* **Licence:** CC BY 4.0
* **Comments:** 7 pages (4 main + references and appendices), 1 figure, 2 tables. Benchmark, code and models: https://github.com/fikrifirat/katip, https://huggingface.co/spaces/f1k/kvkk-bench
* **Abstract (plain text for the form):**

General-purpose AI assistants are now part of legal work. The Turkish data-protection authority's 2026 guide for lawyers states that uploading client documents to such assistants can amount to a transfer of personal data abroad under art. 9 of Law No. 6698 (KVKK), and recommends masking personal data first. Masking needs a detector that works on Turkish legal prose and can run on the lawyer's own machine, but published Turkish PII models are evaluated on their own, mostly synthetic, data. We release KVKK-Bench, a public benchmark with a fixed scorer that ranks systems on real text only (Yargitay sentences with held-out Turkish and foreign names, and Wikipedia sentences), reports a character-level leak rate, and closes a loophole by which over-masking scored perfect precision. We evaluate 14 systems and release two small models, Katip Mask Base (110M parameters, 111 MB int8) and Katip Mask Nano (2.5M, 2.9 MB, 50 pages/s on a laptop CPU), both of which run in a browser. Base scores 97.0 Overall [95% CI 96.5-97.5], 1.1 points above the best general model (XLM-R Large, 95.9) but with twice its leak rate (6.9% vs 3.4%). We do not claim a state of the art: the margins are small, part of the test is in-domain for our models, and no real client documents are labelled yet. The contribution is a shared, reproducible yardstick, a practical model family for local masking, and a local connector for AI assistants whose guarantee we state precisely: it fails closed on every value it detects, and its residual risk is the detector's measured miss rate.

First-time submitters to cs.CL may be asked for an endorsement.
After it is announced: claim the paper on huggingface.co/papers, and add the arXiv ID to the two model cards and the Space README so Hugging Face links them.
