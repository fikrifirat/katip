# Katip Emsal (MVP): find Yargıtay decisions for a petition

A lawyer gives Katip a petition that Katip has already masked. Katip Emsal returns Yargıtay decisions that fit
the argument, each with a link to the official text and the paragraph that matches. Only lowercase words
from the petition and the headings of the statutes it cites leave the computer. Names and numbers never do.

The use case we built it on: an objection to a detention order (tutuklamaya itiraz) in a drug case. The
argument is that the act is personal use (TCK 191), not dealing (TCK 188). The lawyer wants General
Assembly decisions on where that line is, plus chamber decisions with similar facts.

```
pip install turk-hukuku-ictihat-mcp==0.5.1
python lab/emsal/emsal.py PETITION.maskeli.udf --out ~/emsal-runs/case1
python lab/emsal/blind.py make ~/emsal-runs/case1      # blind grading sheet for a lawyer
python lab/emsal/blind.py score ~/emsal-runs/case1     # after grading
python lab/emsal/test_emsal.py                         # offline tests
```

Keep `--out` outside the repository when the petition is real. The tool refuses a petition with no masked parts.

## How it works

1. **Read.** `.udf` or `.txt`. Masked blocks (█) and placeholders are dropped.
2. **Pick words, on this computer.** A candidate word must appear in lowercase in the petition (names are
   capitalised, so they never qualify), be at least 4 letters, not be boilerplate (`müvekkil`, `itiraz`, ...)
   and not be among the 2,000 commonest everyday Turkish words.
3. **Weight words by the court's own collection.** For each candidate, one request asks how many Yargıtay
   decisions contain it. That gives a real document frequency over all 10,042,632 decisions (count on
   14 Nov 2026). Words in fewer than 300 decisions are too specific, and words in more than a third are too
   generic. The rest are ranked by tf-idf.
4. **Write queries.** There are six 3-word AND queries over the top 7 words, in a fixed design. There is
   also one "statute contrast" query. When the petition cites two articles of one code (TCK 188 and 191), it
   takes the heading word only one article has, for each article, choosing the word the petition itself
   uses (`ticareti kullanmak`). Headings come from `data/headings.json`, built from Katip Cite's statute
   index (`build_headings.py`).
5. **Search, politely.** Each query runs once across all chambers (1 page) and once in the relevant General
   Assembly (Ceza or Hukuk Genel Kurulu, 3 pages; the service returns 10 per page). Requests go through the
   MIT-licensed `turk-hukuku-ictihat-mcp` client: it names itself, sends one request at a time, and stops on
   a 429, a CAPTCHA or a login page. We wait 3 s between requests.
6. **Re-rank, on this computer.** Results from all lists are merged with reciprocal rank fusion. Then up to
   80 General Assembly and 30 chamber decisions are fetched in full. Each is cut into ~90-word windows and
   scored with BM25 (five-letter stems; Can et al. 2008) against the whole masked petition, plus 0.25 ×
   the share of the petition's statute articles the decision also cites.
7. **Verify.** A decision is shown only if its esas and karar numbers appear in the official text we
   fetched. Older General Assembly numbers carrying the chamber (`2012/10-1335`) count.
8. **Report.** `report.html` (Turkish, two sections: General Assembly, then chambers), `results.json`,
   `grading.csv`, and `queries.txt`, which lists exactly what was sent.

Decision texts and word counts are public, so they are cached in `~/.cache/katip-emsal/`. A second run asks
the service only for the searches. A cold run makes about 160 requests (about 8 minutes at 3 s each). A warm
run on the same topic makes about 20 (about 1 minute).

## First result: one petition, a development case, not a test

Petition: a real detention objection from a lawyer we work with, masked with Katip. The masked file stays
on our side and is not in this repository. The petition itself cites one decision as support:
**Yargıtay Ceza Genel Kurulu, E. 2017/378, K. 2018/618** (06.12.2018). In the masked copy that number is
hidden, so the tool could not just look it up.

| | Plain keyword search (baseline) | Katip Emsal |
| --- | --- | --- |
| What it is | Official search, petition's top 3 words, first 10 results | 7 queries, re-ranked, verified |
| Cited decision found? | No, not in the top 10 | Yes: 15th of 80 General Assembly decisions checked; not in the 5 shown |
| Requests sent | 1 | ~160 cold, ~20 warm |
| Unverifiable numbers shown | not checked | 0 |

What the top of the list looks like: the five General Assembly decisions shown all deal with the personal-use
vs. dealing line in drug cases (four of them cannabis), and all five are reversals (bozma). The first chamber decision is
about a defendant found through orders on a site selling indoor-growing supplies, which is close to this
petition's facts. **Whether these are better than the decision the lawyer chose is for the lawyer to say.**
That is what the blind sheet is for.

Be careful with this result:

- **n = 1, and we tuned on it.** The query rules changed four times on this same petition: the statute
  contrast query, which heading word it picks, reading three General Assembly pages, and fetching 80 of
  them. Each change was made after seeing the cited decision missed. So this petition shows the pipeline
  works end to end; it is not evidence that it beats keyword search.
- **One cited decision is a weak gold standard.** The lawyer cited one decision from memory, not the
  best one in the collection. Other General Assembly decisions on the same line can be just as good.
- **The real test is next:** 5 to 10 new masked petitions the rules have not seen. For each, a lawyer grades
  the blind sheet (Emsal's list and the baseline's, shuffled together). We report mean relevance, decisions
  graded "on point", nDCG@10 and "would cite" per system. The rules stay frozen until those grades are in.

## Privacy, and what can still leak

- Only `safe_query()` builds outgoing text. It refuses any word that is not lowercase letters, under 4
  letters, or absent from the masked petition (or from public statute headings). Tests cover names, digits,
  UETS numbers and made-up words.
- Known limit: a rare identifier the mask missed **and** that is written in lowercase in the petition could
  be sent as a single-word count request. Search queries only use words found in 300+ decisions, so such a
  word would not reach a search query. Running Katip Mask with the court-filing profile first is still required.
- The tool does not send the petition, quotes from it, or any number. `queries.txt` lists every request.

## Not done yet

- Danıştay and Constitutional Court decisions (Bedesten has `DANISTAYKARAR`).
- Dense retrieval (Mursit embeddings) for decisions that use different words; needs a local model download.
- A lawyer-facing screen in the demo and a `find_precedents` tool in Katip Kalkan.
- The plan this MVP comes from: "Katip Emsal: Yargıtay precedent finder plan" (project doc).
