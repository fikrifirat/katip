# KVKK-Bench leaderboard (v0.1)

Baselines: **Presidio + spaCy** (the standard open-source PII tool, reference baseline) and the **kvkk-pii** regex library (floor). Speed: words per second and ms per 500-word page on one CPU core-set (arm64 Darwin, 12 CPUs), same machine for every row; size is what you download to run it.

Track cells are F2 (%). KVKK-F2 = mean F2 over real-text tracks (the ranking). Generated tracks are a regression check: Katip's models were trained on the same generator. Leak = share of personal-data characters left readable.

## Public split (self-reported, for development)

| # | System | Params | Size MB | Words/s (CPU) | ms/page | Browser | KVKK-F2 (real text) | generated (check) | Leak % | court-filled | prose | petition | contract | correspondence | health | court-generated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Katip BERTurk v2: rules + f1k/katip-tr-pii-berturk | 110.0M | 111.1 | 890 | 562.0 | yes | **93.3** | 99.5 | 2.6 | 97.5 | 89.1 | 100.0 | 100.0 | 100.0 | 97.4 | 100.0 |
| 2 | urchade/gliner_multi_pii-v1 (person) | 288.9M | 1155.8 | 517 | 966.0 | no | **91.0** | 53.9 | 48.6 | 96.7 | 85.2 | 51.7 | 30.0 | 70.4 | 52.2 | 65.2 |
| 3 | akdeniz27/xlm-roberta-base-turkish-ner | 277.5M | 1109.8 | 2,544 | 197.0 | no | **87.9** | 53.2 | 47.4 | 95.5 | 80.3 | 51.4 | 29.1 | 69.3 | 49.5 | 66.7 |
| 4 | savasy/bert-base-turkish-ner-cased | 110.0M | 440.1 | 2,544 | 197.0 | no | **86.0** | 50.9 | 51.1 | 94.7 | 77.4 | 49.6 | 28.5 | 59.0 | 50.7 | 66.5 |
| 5 | ytu-ce-cosmos/modernbert-tr-pii-ner | 149.4M | 597.5 | 2,345 | 213.0 | no | **68.0** | 73.4 | 21.6 | 96.8 | 39.1 | 80.3 | 59.6 | 83.0 | 71.2 | 72.8 |
| 6 | Katip Tiny: rules + katip-tr-name-tagger-tiny | 2.5M | 2.9 | 21,544 | 23.0 | yes | **55.3** | 99.4 | 13.0 | 93.1 | 17.4 | 100.0 | 100.0 | 99.6 | 97.4 | 100.0 |
| 7 | Katip Rules v0.2 | 0 (rules) | 0.3 | 65,311 | 8.0 | yes | **53.6** | 98.9 | 13.9 | 89.6 | 17.6 | 98.4 | 100.0 | 99.6 | 96.4 | 100.0 |
| 8 | Presidio + spaCy xx (vanilla) (reference baseline) |  |  | 14,520 | 34.0 | no | **49.6** | 28.7 | 34.2 | 38.0 | 61.2 | 29.6 | 10.0 | 42.3 | 23.1 | 38.2 |
| 9 | ersanbil/kvkk-pii-ner (model only) | 110.0M | 440.1 | 2,781 | 180.0 | no | **0.0** | 7.8 | 82.9 | 0.0 | 0.0 | 17.5 | 11.2 | 8.6 | 0.0 | 1.9 |
| 10 | kvkk-pii 0.2 (regex library, MIT) (floor baseline) | 0 (rules) | 0.1 | 568,143 | 1.0 | no | **0.0** | 25.1 | 87.9 | 0.0 | 0.0 | 25.9 | 43.9 | 23.8 | 20.8 | 11.3 |
