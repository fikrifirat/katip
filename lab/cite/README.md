# Katip Cite and Cite-Bench-TR

**Do AI models cite Turkish law correctly?** Lawyers, clients and expats now ask chatbots about Turkish law, and the
answers come with confident citations: *"TBK m. 344"*, *"Article 54 of Law No. 6458"*. Some of those articles do not
exist, were repealed years ago, or belong to another law. Nobody measures this for Turkish law. This folder does.

| | What it is | Size | Runs |
|---|---|---|---|
| **Katip Cite** (`katip_cite.py`) | finds every statute citation in a text (Turkish or English) and checks it against the official text of all 1,085 Turkish laws | 1.6 MB index, standard-library Python | offline, on a laptop, milliseconds per page |
| **Cite-Bench-TR** (`bench.py`) | 63 questions in 10 risk areas, each asked in Turkish and English, that rank language models by how often their answers are *safe* | 126 prompts per model | any OpenAI-compatible endpoint; local models through Ollama |

Follow `01_cite_bench.ipynb` step by step: setup, the checker, the questions, running models, scoring, auditing the
checker on real answers, and the report.

## Quick start

```
python lab/cite/katip_cite.py "Kiracı temerrüde düşerse TBK m. 315 uygulanır; TBK m. 712 de geçerlidir."
python lab/cite/test_katip_cite.py
ollama pull qwen3:8b
python lab/cite/bench.py run --model qwen3:8b --no-think --limit 3   # smoke test
python lab/cite/bench.py run --model qwen3:8b --no-think             # all 126
python lab/cite/bench.py score && python lab/cite/make_leaderboard.py
```

## How a citation is checked

1. **Find.** Patterns for the forms people and models write: `TBK m. 344/1`, `TBK'nın 315. maddesi`,
   `6098 sayılı Türk Borçlar Kanunu'nun 350 nci maddesi`, `İş Kanunu ek madde 3`, `TMK m. 161, 162 ve 166`,
   `aynı Kanunun 21. maddesi`, `Article 54 of the Law on Foreigners and International Protection`, `Law No. 6735, Article 7`.
   Abbreviations follow Turkish legal writing: **BK = 818 (the old code, repealed 2012)**, TBK = 6098; a bare
   "Borçlar Kanunu" is read as the code in force, and MK as TMK.
2. **Verify** against the index (`build_index.py`, from a dated snapshot of Açık Mevzuat, a daily mirror of
   mevzuat.adalet.gov.tr). One verdict per citation:

| Verdict | Meaning | Example |
|---|---|---|
| `OK` | law in force, article exists and is in force | TBK m. 344 |
| `NO_SUCH_ARTICLE` | the law has no such article | TBK m. 712 (TBK has 649) |
| `ARTICLE_REPEALED` | the article is marked Mülga | İş Kanunu m. 87 |
| `LAW_REPEALED` | the whole law is repealed | BK m. 248, HUMK m. 432 |
| `NUMBER_NAME_CLASH` | number and name point to different laws | 6098 sayılı Türk Medeni Kanunu |
| `UNKNOWN_LAW` | no law has that number | 9999 sayılı Kanun |
| `UNVERIFIED` | we could not decide (gap in our copy of that law) | rare outside the core laws |

Case-law citations (Yargıtay, Danıştay, AYM) are found and counted, not verified yet.

## What the bench measures

Per answer, then averaged per model with a 95% bootstrap interval:

- **Safe answer** (the ranking): no provably wrong citation, **and** cites at least one article a lawyer would expect,
  **and** states the key fact where the question has one (a deadline, a share, a threshold).
- **Wrong citations %**: provably wrong / all checkable statute citations.
- **Right article %** and **Key fact %**, separately.
- **Stale rule**: the answer gives the old rule of a law changed recently (e.g. 7 days to appeal a criminal judgment;
  Law 7499 of 2 March 2024 made it two weeks from service of the reasoned judgment).
- **TR − EN**: the same 63 questions in Turkish and English, paired, exact McNemar test. This is the expat question:
  is an English answer about Turkish law less safe?
- **Case-law citations per answer**: exposure that is not checked yet.

Two reference rows set the scale: `ref-quote` quotes the expected article (the ceiling, 94% safe) and
`ref-fabricator` invents article numbers (0%).

## Risk areas

| Area | Questions | Why it is risky |
|---|---|---|
| Labour (İş) | 6 | notice, severance (still in the old 1475 law, art. 14), reinstatement within one month |
| Rent (Kira) | 6 | rent increase rules changed 2022–24; mediation became mandatory in 2023 |
| Family (Aile) | 6 | divorce grounds and short deadlines (adultery: six months) |
| Inheritance (Miras) | 6 | renunciation within three months; foreigners' property in Turkey (MÖHUK art. 20) |
| Enforcement (İcra) | 6 | seven-day and five-day objection windows |
| Criminal (Ceza) | 6 | custody, detention, appeal deadline changed in 2024 |
| Procedure and deadlines (Usul) | 6 | two-week appeal windows, judicial recess, e-tebligat on the fifth day |
| Data protection (KVKK) | 6 | articles 6 and 9 rewritten in 2024 |
| Foreigners and expats (Yabancılar) | 9 | residence permits, deportation, work permits, citizenship |
| Consumer and property | 6 | defects, withdrawal, building charges |

The questions, expected articles and key facts were drafted by Claude and checked against the article texts in the
index (`python lab/cite/make_questions.py` prints each expected article's first words). **They are `draft` until a
lawyer reviews them**: the notebook writes `review/questions_review.csv` for that.

## Privacy

Everything runs locally. The questions are public and contain no client data. API models are optional, get only these
questions, and take their key from an environment variable (`--api-key-env`), never from the command line.

## Sources and licences

- Law texts: official texts of the Republic of Türkiye (not protected by copyright, FSEK art. 31), via
  [Açık Mevzuat](https://github.com/onurcan-b/acik-mevzuat) (code MIT; texts sourced from UYAP/Bedesten). Every result
  records the snapshot commit. Verify against mevzuat.gov.tr before relying on a text.
- Katip code: AGPL-3.0, commercial licence on request (see the repository root).

## Limits

- "Exists and in force" is not "supports the argument". The *right article* metric covers that for the bench, using
  expected articles per question; a free-text answer can still misread a correct article.
- Patterns can miss unusual citation forms. Step 6 of the notebook audits the checker on real answers; report that
  audit next to any result.
- Regulations (yönetmelik), communiqués and Board decisions are not in the index yet, so citations to them are not
  checked.

## Amendments

Changes to the question set after the first model run go here, with the date and the reason.
