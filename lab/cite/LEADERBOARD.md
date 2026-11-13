# Cite-Bench-TR leaderboard (v0.1, draft questions)

Each model answers 63 Turkish legal questions in Turkish and in English (126 answers). Katip Cite checks every statute citation against the official law text (offline index, snapshot in each results file). **Safe answer** = no wrong citation + cites an article a lawyer would expect + states the key fact where there is one. 95% bootstrap CIs; TR−EN is the paired difference with an exact McNemar p. Questions are Claude-drafted and await lawyer review.

| # | Model | Local | Safe answers % | Right article % | Key fact % | Wrong citations % | Answers with a wrong citation % | Stale rule | TR safe % | EN safe % | TR−EN (p) | High-risk safe % | Case-law cites / answer | s / answer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ref | Reference: invents article numbers | yes | 0 [0–0] | 0 | 0 | 100.0 | 100 | 0 | 0 | 0 | +0 (1.00) | 0 | 0.00 | 0.0 |
| ref | Reference: quotes the expected article | yes | 94 [89–98] | 100 | 93 | 2.7 | 2 | 0 | 94 | 94 | +0 (1.00) | 91 | 0.00 | 0.0 |

## Safe answers by risk area (%)

| Model | Labour | Rent | Family | Inheritance | Enforcement | Criminal | Procedure & deadlines | KVKK | Foreigners | Consumer & property |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
