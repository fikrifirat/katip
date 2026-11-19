# KVKK-Bench external track: test sets built by other teams

## Round 2 (19 Nov 2026): rules PR #58, scored on held-out halves

**Short version.** With the rules in PR #58, Katip Base beats NewMind's kvkk-v2 on all four sets' held-out halves.
The win is significant on three. On piimask's held-out documents with a template not seen in the dev half, the two
tie. NewMind still has higher precision on nm6k and piimask, and Katip leaves less personal data readable on every set.

How this was kept honest:

- Each set is split in two by document id (sha256 of `split20261119:<id>`, even = dev). The PR #58 rules were
  written only from errors read on the **dev** half; the test half was scored, never read.
- Templates: these sets are generated from templates, so a test document can repeat a dev template with new values.
  "Unseen" rows keep only test documents whose template (text with values and digits blanked) is not in the dev half.
  Werea has no unseen test documents (104 templates over 240 rows), so its result is not independent.
- Caveat: yesterday's fixes (PRs #55 and #57) were found by reading errors on the full sets, test halves included.
  The "before" column below is main before all three PRs.
- Same scorer for every system. One change from round 1: a predicted type that a set never labels (piimask has no IP
  label) is now neutral for precision, as the round 1 text already said. It moves round 1 numbers by ≤0.2 points,
  except Werea-150M (up to +5, still last).
- KVKK-Bench v0.1.2 public split with PR #58: Base KVKK-F2 93.10 → 93.16, leak rate unchanged (3.06%). The only
  changes are 13 removed false health masks. Python and JavaScript engines agree on 1,856 parity cases.
- 95% paired bootstrap over documents, 2,000 resamples, against newmind-kvkk-v2.

Held-out test halves (F2; recall-weighted):

| Set (test docs) | Katip Base before | Katip Base, PR #58 | Katip Mini, PR #58 | NewMind kvkk-v2 | Base minus NewMind, 95% CI |
|---|---|---|---|---|---|
| nm-kvkk-pii-6K (290, all unseen) | 89.0 | **95.9** | 93.4 | 93.9 | +0.6 to +3.5 |
| piimask TR (99) | 86.2 | **95.9** | 95.7 | 93.8 | +0.1 to +4.6 |
| piimask TR, unseen templates (60) | 87.2 | 96.5 | 96.5 | 96.5 | −1.1 to +1.0 (tie) |
| Çağrı "mask all" (168) | 65.8 | **95.2** | 93.0 | 72.6 | +17.8 to +27.3 |
| Çağrı, unseen templates (92) | 66.0 | **95.4** | 92.6 | 72.0 | +17.7 to +29.1 |
| Werea (116, no unseen templates) | 52.5 | 95.8 | 93.6 | 54.3 | +31.8 to +51.9 (not independent) |

Other aspects on the same test halves (Base PR #58 vs NewMind):

| | nm6k | piimask TR | Çağrı | Werea |
|---|---|---|---|---|
| Recall | 97.2 vs 92.5 | 97.6 vs 93.9 | 94.6 vs 68.2 | 94.8 vs 48.7 |
| Precision | 91.2 vs **99.7** | 89.8 vs **93.2** | 97.3 vs 97.6 | 100 vs 100 |
| Leak (personal-data characters left readable) | 8.9% vs 9.0% | 2.0% vs 4.5% | 6.8% vs 41.1% | 26.3% vs 65.2% |
| False masks per 1k words on PII-free text (Çağrı negatives) | | | 3.4 vs 37.8 | |
| Model size | 111 MB vs 1.1 GB | | | |

Where NewMind still leads: precision on nm6k (its own set; most of Katip's false hits there are capitalised form
words read as names and health words the set does not label) and on piimask (mostly surnames repeated later in a
text, which piimask leaves unlabelled but KVKK treats as personal data). Mini matches NewMind on nm6k (CI −1.9 to
+1.0) and beats it elsewhere; Nano and rules alone are behind on nm6k. Full rows: `heldout_v4.txt`
(`python heldout.py <systems> dev|test|unseen`).

What PR #58 changed (all found on dev halves, all checked on new hand-written sentences, including ones that must
stay unmasked):

- **Special categories by value.** These sets label the value after a field ("din hanesi *Musevi*", "Tanı:
  *atopik dermatit*", "köken bilgisi *Kürt*"); Katip used to mask only the label word. It now masks the value after
  a special-category label, and drops the label hit when it does. A bare label needs its colon.
- **Fewer false health masks.** Generic medical words alone (tedavi, ilaç, reçete, ameliyat, hastalık, tanı,
  biyometrik) are no longer masked; a condition keeps the word after it ("kanser tedavisi").
- **Numbers read out as words** ("tc dokuz dokuz yedi..."), typed by the label before them. Amounts never match.
- **Written-out e-mails** ("[at] ... [dot]"), dashed IBANs, plates next to "plaka" in any letter pattern, flat and
  door numbers, birth dates with month names or ISO dates.
- **Field labels at a line start** ("Kayıt Saati:", "Poliçe Durumu:") are no longer names.

---

## Round 1 (18 Nov 2026): main as of 18 Nov, before PRs #55, #57 and #58

**Short version.** On test sets that other teams built, NewMind's kvkk-v2 beats Katip Base, and the gap is
statistically significant on 3 of 4 sets (95% paired bootstrap over documents, 2,000 resamples). Most of the gap
comes from two things: made-up numbers that fail their check digits, and a few formats Katip did not know (fixed
in PR #55). Katip makes about a tenth of NewMind's false masks on text with no
personal data, and it is the only system here that finds any KVKK art. 6 special categories.

| Set (rows) | Katip Base F2 | NewMind kvkk-v2 F2 | Base minus NewMind, 95% CI | Note |
|---|---|---|---|---|
| nm-kvkk-pii-6K test (602) | 90.6 | 94.3 | −5.2 to −1.5 | NewMind's own set: kvkk-v2 trained on its training split |
| piimask TR (180) | 84.0 | 91.2 | −8.7 to −5.7 | neutral |
| Çağrı Güngör, "mask all" rows (350) | 68.0 | 74.4 | −9.7 to −3.3 | neutral for both |
| Werea test (240) | 54.7 | 56.4 | −4.0 to +0.4 | not significant; 104 template sentences only |

Why NewMind leads (per-type recall, Base vs NewMind):

- **Check digits.** Katip masks a TCKN, YKN, VKN or card number only when it passes the official check (by design,
  to avoid masking case numbers). These sets mostly use made-up numbers that fail it: piimask VKN 28 of 34,
  Çağrı cards 22 of 24, nm6k YKN 6 of 6. Katip finds 0% of these, NewMind 77–100%. Left out, the gap shrinks to
  piimask TR 85.4 vs 90.4, Çağrı 70.6 vs 73.3, nm6k 90.8 vs 94.3. On a real document such a number is still a
  typo'd ID, so a follow-up will mask it when a label like "TC Kimlik No:" sits right next to it.
- **Formats Katip did not know**, fixed in PR #55: birth date after a bare "doğum" (piimask 0% → 100%), TROY
  cards, TCKN written 123.456.789.01. After PR #55 Base scores piimask TR 87.6 and Çağrı 69.0. These bugs were
  found on these sets, so post-fix numbers are not an independent test and are not in the table below.
- **Follow-up PR #57** (labelled numbers without a valid checksum, blood group, maiden name; stacked on #55):
  Base reaches Çağrı 77.5 (NewMind 74.4), piimask TR 89.6 (91.0), nm6k 92.1 (94.3), with false masks unchanged.
  Same caveat: not independent. Rows `base-v3` / `rules-v3` in results.json.
- **Precision on nm6k**: Base 78.7 vs NewMind 99.9. Mostly form labels masked as names ("Kayıt Sahibi", ~180)
  and health keywords ("ilaç", "reçete") flagged on their own.

Where Katip is ahead:

- **False masks on PII-free text** (Çağrı's 200 "negatif" rows): Base 3.4 per 1,000 words, NewMind 35.6,
  Horizon 228, Werea 404.
- **Special categories** (Çağrı set): Katip finds health 15%, religion 67%, union 60%, criminal record 22%,
  biometric 28%. NewMind finds 0% of each with its stack21 label set. Both miss ethnicity (0/18) and blood group.
- **Size and speed**: Base 111 MB, Mini 31 MB, Nano 3 MB, vs NewMind 1.1 GB.

Other models:

- **Werea / girenit 150M** (byte-identical weights): 100.0 on their own Werea set, 11.6–29.0 on everyone else's,
  404 false masks per 1k words. Overfit to their 104 templates.
- **pii-guard-turkish-270m** (by the Çağrı set's author): 96.3 on its home set, 55.8 on Werea. Not run on nm6k
  or piimask: as a text generator it took over 3 h on CPU without finishing piimask, so I stopped it.
  halilneed/turkish-pii-detection (same Gemma recipe) was not run for the same reason.
- **Horizon pii-redactor-base**: 87.4 nm6k, 75.6 piimask TR, but 228 false masks per 1k words.
- **hushmark-tr-289m**: 35–54 everywhere (model alone, no rules).
- **BTX24/turkish-privacy-filter-pii**: skipped; needs OpenAI's opf runtime, which I did not install.

Caveats: all five sets are synthetic, made by their authors; no public set of real Turkish documents exists.
Labels were mapped to KVKK-Bench types by hand (table in `ext_bench.py`, `MAP`); labels with no KVKK-Bench type
are neutral for precision and counted only in "leak, all labels". Revisions are pinned in `SETS`.

Reproduce: `python ext_bench.py run base mini nano rules newmind-kvkk-v2 ...` then `python ext_bench.py score`.

---

### Round 1 tables (rescored with the current scorer)

Scores of every system on four public Turkish PII test sets that Katip did not build. All four sets are synthetic
(generated by their authors; none contains real documents). Werea-co/Werea-KVKK-Bench and girenit/girenit-KVKK-Bench
are byte-identical, so they are one column. Cells: **F2** on the types both sides label (recall weighted 4×), then
**leak** (share of those personal-data characters left readable). † = the system was trained on that set's own
training split, or by that set's authors (in-distribution).

| System | nm-kvkk-pii-6K test (602) | piimask TR (180) | piimask TR-EN (80) | PII-masking 'mask all' (350) | Werea test (240) | false masks / 1k words on PII-free text (200) |
|---|---|---|---|---|---|---|
| Katip Mask Base (f1k/katip-mask-base) | 90.6 · 11.0 | 84.0 · 15.9 | 81.9 · 20.5 | 68.0 · 44.9 | 54.7 · 51.1 | 3.4 |
| Katip Mask Mini (f1k/katip-mask-mini) | 88.7 · 13.6 | 83.8 · 15.8 | 74.5 · 28.8 | 67.0 · 45.7 | 51.8 · 52.1 | 3.4 |
| Katip Mask Nano v1.1 (f1k/katip-mask-nano) | 83.6 · 18.8 | 83.2 · 15.8 | 73.3 · 28.1 | 66.7 · 45.3 | 47.6 · 55.1 | 17.0 |
| Katip rules only | 83.6 · 19.9 | 82.8 · 16.9 | 74.5 · 29.0 | 61.5 · 47.8 | 43.7 · 56.5 | 3.4 |
| newmindai/gliner2.5-kvkk-tr-v2 (stack21 labels, their extract_kvkk.py settings) | 94.3 · 8.3 † | 91.2 · 6.3 | 99.5 · 0.0 | 74.4 · 37.3 | 56.4 · 61.6 | 35.6 |
| Horizon-Labs/pii-redactor-base (mmBERT) | 87.4 · 13.0 | 75.7 · 10.6 | 76.5 · 5.5 | 58.1 · 40.6 | 43.2 · 64.5 | 228.2 |
| lokomotifai/hushmark-tr-289m (GLiNER, model only) | 54.0 · 58.5 | 35.3 · 65.3 | 38.7 · 62.9 | 35.1 · 74.5 | 38.4 · 61.5 | 6.8 |
| Werea-co/Werea-KVKK-PII-150M (ModernBERT-TR) | 13.9 · 10.9 | 34.0 · 7.3 | 16.1 · 7.4 | 22.7 · 39.4 | 100.0 · 0.0 † | 403.7 |
| girenit/girenit-KVKK-PII-150M (ModernBERT-TR) | 13.9 · 10.9 | 34.0 · 7.3 | 16.1 · 7.4 | 22.7 · 39.4 | 100.0 · 0.0 † | 403.7 |
| cagrigungor/pii-guard-turkish-270m (Gemma 3 270M, text-to-text) |  |  |  | 96.3 · 1.5 † | 55.8 · 45.8 | 16.1 |

## Per-type recall (nm-kvkk-pii-6K test, piimask TR)

**nm6k**

| Type (gold) | base | mini | nano | rules | newmind-kvkk-v2 | horizon-pii-base | hushmark-tr-289m | werea-pii-150m | girenit-pii-150m |
|---|---|---|---|---|---|---|---|---|---|
| PERSON (1536) | 99.4 | 98.1 | 88.5 | 85.8 | 97.7 | 99.5 | 73.5 | 66.5 | 66.5 |
| TCKN (242) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.8 | 0.0 | 69.8 | 69.8 |
| HEALTH (110) | 4.5 | 3.6 | 3.6 | 3.6 | 0.0 | 0.0 | 27.3 | 2.7 | 2.7 |
| EMAIL (91) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0.0 |
| PHONE (91) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 12.1 | 12.1 |
| BIRTH_DATE (56) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 87.5 | 78.6 | 78.6 |
| ADDRESS (54) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 31.5 | 22.2 | 5.6 | 5.6 |
| PLATE (44) | 93.2 | 93.2 | 93.2 | 93.2 | 100.0 | 0.0 | 0.0 | 18.2 | 18.2 |
| CREDIT_CARD (35) | 82.9 | 82.9 | 82.9 | 82.9 | 100.0 | 100.0 | 0.0 | 0.0 | 0.0 |
| IP_ADDRESS (29) | 100.0 | 100.0 | 100.0 | 100.0 | 69.0 | 34.5 | 0.0 | 89.7 | 89.7 |
| PASSPORT (23) | 91.3 | 91.3 | 91.3 | 91.3 | 100.0 | 91.3 | 0.0 | 0.0 | 0.0 |
| IBAN (14) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| VKN (12) | 91.7 | 91.7 | 91.7 | 91.7 | 83.3 | 100.0 | 0.0 | 41.7 | 41.7 |
| YKN (6) | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0 | 0.0 | 16.7 | 16.7 |
| BIOMETRIC_GENETIC (4) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 50.0 | 0.0 | 0.0 |
| DRESS (1) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| POLITICAL (1) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

**piimask-tr**

| Type (gold) | base | mini | nano | rules | newmind-kvkk-v2 | horizon-pii-base | hushmark-tr-289m | werea-pii-150m | girenit-pii-150m |
|---|---|---|---|---|---|---|---|---|---|
| PERSON (316) | 95.6 | 95.9 | 95.6 | 89.6 | 100.0 | 94.6 | 78.8 | 71.8 | 71.8 |
| PHONE (232) | 83.2 | 83.2 | 83.2 | 83.2 | 85.8 | 83.6 | 0.0 | 13.8 | 13.8 |
| EMAIL (158) | 87.3 | 87.3 | 87.3 | 87.3 | 87.3 | 100.0 | 0.0 | 12.7 | 12.7 |
| TCKN (138) | 85.5 | 85.5 | 85.5 | 85.5 | 85.5 | 96.4 | 0.0 | 63.0 | 63.0 |
| ADDRESS (132) | 77.3 | 77.3 | 77.3 | 77.3 | 77.3 | 28.8 | 59.1 | 39.4 | 39.4 |
| IBAN (62) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 40.3 | 40.3 |
| PLATE (34) | 55.9 | 55.9 | 55.9 | 55.9 | 100.0 | 0.0 | 0.0 | 11.8 | 11.8 |
| PASSPORT (34) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0.0 |
| BIRTH_DATE (34) | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 0.0 | 100.0 | 97.1 | 97.1 |
| VKN (34) | 17.6 | 17.6 | 17.6 | 17.6 | 100.0 | 100.0 | 0.0 | 35.3 | 35.3 |

## Precision and the other labels

| System | set | recall | precision | recall, any type | precision vs every label | leak, all labels |
|---|---|---|---|---|---|---|
| base | nm6k | 94.1 | 78.9 | 94.1 | 79.3 | 37.7 |
| base | piimask-tr | 83.0 | 88.3 | 84.2 | 87.2 | 21.4 |
| base | piimask-tr-en | 80.6 | 87.4 | 80.6 | 87.4 | 23.0 |
| base | cagri-tam | 64.2 | 89.1 | 64.5 | 89.8 | 66.9 |
| base | werea | 49.2 | 100.0 | 49.2 | 100.0 | 59.4 |
| mini | nm6k | 93.2 | 74.4 | 93.3 | 75.1 | 39.3 |
| mini | piimask-tr | 83.0 | 86.7 | 84.2 | 85.7 | 21.3 |
| mini | piimask-tr-en | 72.1 | 86.0 | 72.1 | 86.0 | 31.0 |
| mini | cagri-tam | 63.1 | 89.2 | 63.2 | 90.1 | 67.2 |
| mini | werea | 46.2 | 100.0 | 46.2 | 100.0 | 60.2 |
| nano | nm6k | 86.9 | 72.3 | 86.9 | 72.9 | 43.0 |
| nano | piimask-tr | 83.0 | 84.3 | 84.2 | 83.4 | 21.3 |
| nano | piimask-tr-en | 73.2 | 73.7 | 73.2 | 74.7 | 30.0 |
| nano | cagri-tam | 63.2 | 85.2 | 64.2 | 88.3 | 66.0 |
| nano | werea | 42.1 | 100.0 | 42.1 | 100.0 | 62.8 |
| rules | nm6k | 85.2 | 77.7 | 85.2 | 78.2 | 43.8 |
| rules | piimask-tr | 81.3 | 89.0 | 82.5 | 87.9 | 22.3 |
| rules | piimask-tr-en | 72.1 | 86.0 | 72.1 | 86.0 | 31.2 |
| rules | cagri-tam | 57.1 | 88.9 | 57.3 | 89.4 | 68.9 |
| rules | werea | 38.3 | 100.0 | 38.3 | 100.0 | 63.9 |
| newmind-kvkk-v2 | nm6k | 93.1 | 99.9 | 93.1 | 98.2 | 24.2 |
| newmind-kvkk-v2 | piimask-tr | 91.2 | 91.1 | 95.6 | 91.9 | 12.4 |
| newmind-kvkk-v2 | piimask-tr-en | 100.0 | 97.7 | 100.0 | 97.8 | 0.3 |
| newmind-kvkk-v2 | cagri-tam | 70.3 | 97.2 | 72.8 | 99.4 | 47.7 |
| newmind-kvkk-v2 | werea | 50.8 | 100.0 | 50.8 | 100.0 | 51.1 |
| horizon-pii-base | nm6k | 87.3 | 88.0 | 92.1 | 82.3 | 21.7 |
| horizon-pii-base | piimask-tr | 75.8 | 75.5 | 88.2 | 82.9 | 14.6 |
| horizon-pii-base | piimask-tr-en | 77.1 | 74.3 | 92.4 | 88.9 | 5.7 |
| horizon-pii-base | cagri-tam | 55.6 | 71.3 | 68.7 | 97.2 | 39.9 |
| horizon-pii-base | werea | 37.9 | 98.3 | 38.3 | 100.0 | 70.1 |
| hushmark-tr-289m | nm6k | 52.0 | 64.0 | 52.8 | 56.8 | 65.8 |
| hushmark-tr-289m | piimask-tr | 30.7 | 86.9 | 32.5 | 75.6 | 67.5 |
| hushmark-tr-289m | piimask-tr-en | 33.5 | 100.0 | 33.5 | 100.0 | 64.0 |
| hushmark-tr-289m | cagri-tam | 30.5 | 86.6 | 35.5 | 95.1 | 79.4 |
| hushmark-tr-289m | werea | 33.3 | 97.5 | 40.8 | 100.0 | 68.0 |
| werea-pii-150m | nm6k | 55.0 | 3.5 | 63.4 | 10.0 | 10.9 |
| werea-pii-150m | piimask-tr | 41.9 | 19.4 | 54.9 | 36.3 | 7.0 |
| werea-pii-150m | piimask-tr-en | 15.3 | 20.8 | 18.8 | 43.9 | 7.3 |
| werea-pii-150m | cagri-tam | 22.7 | 23.0 | 35.2 | 81.6 | 35.6 |
| werea-pii-150m | werea | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 |
| girenit-pii-150m | nm6k | 55.0 | 3.5 | 63.4 | 10.0 | 10.9 |
| girenit-pii-150m | piimask-tr | 41.9 | 19.4 | 54.9 | 36.3 | 7.0 |
| girenit-pii-150m | piimask-tr-en | 15.3 | 20.8 | 18.8 | 43.9 | 7.3 |
| girenit-pii-150m | cagri-tam | 22.7 | 23.0 | 35.2 | 81.6 | 35.6 |
| girenit-pii-150m | werea | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 |
| pii-guard-270m | cagri-tam | 95.6 | 99.0 | 98.6 | 99.4 | 1.9 |
| pii-guard-270m | werea | 50.4 | 97.6 | 53.3 | 98.1 | 38.0 |
