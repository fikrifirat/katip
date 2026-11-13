---
title: KVKK-Bench-TR
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
pinned: true
license: apache-2.0
short_description: Which tool removes personal data from Turkish documents?
tags:
- leaderboard
- pii
- kvkk
- turkish
- de-identification
datasets:
- f1k/kvkk-bench-tr
---

# KVKK-Bench-TR leaderboard

Ranks tools that mask personal data in Turkish documents, on real text, with a missed item weighted 4× a false alarm.
Results live in `results/` (or the dataset in `RESULTS_REPO`). Submissions go to `REQUESTS_REPO` when `HF_TOKEN` is set.
Benchmark card, scorer and runner: github.com/fikrifirat/katip, `lab/legal/`.
