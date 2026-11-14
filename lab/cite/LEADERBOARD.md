# Cite-Bench-TR leaderboard (v0.1, draft questions)

Each model answers 63 Turkish legal questions in Turkish and in English (126 answers). Katip Cite checks every statute citation against the official law text (offline index, snapshot in each results file). **Safe answer** = no wrong citation + cites an article a lawyer would expect + states the key fact where there is one. 95% bootstrap CIs; TR−EN is the paired difference with an exact McNemar p. Questions are Claude-drafted and await lawyer review.

| # | Model | Local | Safe answers % | Right article % | Key fact % | Wrong citations % | Answers with a wrong citation % | Stale rule | TR safe % | EN safe % | TR−EN (p) | High-risk safe % | Case-law cites / answer | s / answer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | gemma3:4b | yes | 4 [1–8] | 4 | 29 | 8.7 | 6 | 0 | 5 | 3 | +2 (1.00) | 0 | 0.00 | 3.8 |
| 2 | llama3.2:3b | yes | 2 [0–6] | 4 | 24 | 4.8 | 2 | 0 | 0 | 5 | -5 (0.25) | 2 | 0.00 | 10.6 |
| 3 | qwen3:8b | yes | 0 [0–0] | 0 | 27 | 7.5 | 8 | 0 | 0 | 0 | +0 (1.00) | 0 | 0.00 | 25.2 |
| ref | Reference: invents article numbers | yes | 0 [0–0] | 0 | 0 | 100.0 | 100 | 0 | 0 | 0 | +0 (1.00) | 0 | 0.00 | 0.0 |
| ref | Reference: quotes the expected article | yes | 95 [91–98] | 100 | 93 | 0.0 | 0 | 0 | 95 | 95 | +0 (1.00) | 94 | 0.00 | 0.0 |

## Safe answers by risk area (%)

| Model | Labour | Rent | Family | Inheritance | Enforcement | Criminal | Procedure & deadlines | KVKK | Foreigners | Consumer & property |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemma3:4b | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 42 | 0 | 0 |
| llama3.2:3b | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 6 | 0 |
| qwen3:8b | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
