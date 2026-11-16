# arXiv submission sheet

Upload `kvkk-bench-arxiv-source.tar.gz` (main.tex, main.bbl, refs.bib, fig_overall_size.pdf, fig_leak_speed.pdf, fig_tracks.pdf). It compiles with pdflatex, no bibtex step needed.

* **Title:** KVKK-Bench: Measuring Personal-Data Masking in Turkish Legal Text, with Small On-Device Models
* **Authors:** Fikri Fırat
* **Primary category:** cs.CL (Computation and Language). **Cross-list:** cs.CR (Cryptography and Security).
* **Licence:** CC BY 4.0
* **Comments:** 10 pages (main text, references and appendices), 3 figures, 4 tables. Benchmark, code and models: https://github.com/fikrifirat/katip, https://huggingface.co/spaces/f1k/kvkk-bench
* **Abstract (plain text for the form):**

Türkiye's data-protection authority now says that uploading client documents to a foreign AI assistant can be a transfer of personal data abroad (art. 9, Law No. 6698, KVKK), and recommends masking personal data first. Masking needs a detector that works on Turkish legal text and runs on the lawyer's own machine. Turkish PII models exist, but each is tested on its own, mostly synthetic, data, so their scores cannot be compared. We release KVKK-Bench, a public benchmark for that question. Unlike general PII benchmarks, it (i) scores on real court text, with Turkish and foreign names that no system has seen in training; (ii) asks what a lawyer needs to know, how much personal data is still readable after masking (a character-level leak rate), next to a recall-weighted F2; and (iii) penalises masking everything, which a naive span scorer (including our own first version) rewards with perfect precision. We evaluate 17 systems and release three small models that run in a browser: Katip Mask Base (111 MB), Mini (31 MB) and Nano (2.9 MB, 43 pages/s on a laptop CPU). Base scores 96.1 Overall [95% CI 95.4-96.7], a statistical tie with the best general model (XLM-R Large, 95.9) at one twentieth of its size, but it leaks more than twice as much (8.2% vs 3.4%). Unranked synthetic tracks add forms, phone photos of forms, and the same forms as UDF, Word, PDF and scanned files. We do not claim a state of the art: margins are small, part of the test is in-domain for our models, and no real client documents are labelled yet.

First-time submitters to cs.CL may be asked for an endorsement.
After it is announced: claim the paper on huggingface.co/papers, and add the arXiv ID to the two model cards and the Space README so Hugging Face links them.
