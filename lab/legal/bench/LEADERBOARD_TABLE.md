# KVKK-Bench-TR leaderboard (v0.1)

Baselines: **Presidio + spaCy** (the standard open-source PII tool, reference baseline) and the **kvkk-pii** regex library (floor). Speed: words per second and ms per 500-word page on one CPU core-set (x86_64 Linux, 4 CPUs), same machine for every row; size is what you download to run it.

Track cells are F2 (%). KVKK-F2 = mean F2 over real-text tracks (the ranking). Generated tracks are a regression check: Katip's models were trained on the same generator. Leak = share of personal-data characters left readable.

## Public split (self-reported, for development)

| # | System | Params | Size MB | Words/s (CPU) | ms/page | Browser | KVKK-F2 (real text) | generated (check) | Leak % | court-filled | prose | petition | contract | correspondence | health | court-generated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Katip Tiny: rules + katip-tr-name-tagger-tiny | 2.5M | 2.9 | 14,549 | 34.0 | yes | **55.4** | 99.4 | 13.0 | 93.4 | 17.4 | 100.0 | 100.0 | 99.6 | 97.4 | 100.0 |
| 2 | Katip Rules v0.2 | 0 (rules) | 0.3 | 39,819 | 13.0 | yes | **53.9** | 98.9 | 13.9 | 90.1 | 17.6 | 98.4 | 100.0 | 99.6 | 96.4 | 100.0 |
| 3 | Presidio + spaCy xx (vanilla) (reference baseline) |  |  | 7,627 | 66.0 | no | **49.6** | 28.7 | 34.2 | 38.0 | 61.2 | 29.6 | 10.0 | 42.3 | 23.1 | 38.2 |
| 4 | kvkk-pii 0.2 (regex library, MIT) (floor baseline) | 0 (rules) | 0.1 | 385,589 | 1.0 | no | **0.0** | 25.1 | 87.9 | 0.0 | 0.0 | 25.9 | 43.9 | 23.8 | 20.8 | 11.3 |
