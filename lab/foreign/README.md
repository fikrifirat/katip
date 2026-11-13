# Foreign clients: transliterated names, YKN, passports

Turkish lawyers now represent many Syrian clients, plus Iranian, Afghan, Georgian, Armenian, Greek, Arab, Russian,
Ukrainian, Azerbaijani and Western ones. Their names reach Turkish documents transliterated, with inconsistent spellings
(Muhammed / Mohammad / Mhd, Abdulrahman / Abdurrahman, Al- / El-, -zadeh / -zade, -shvili / -şvili, -yan / -ian,
-opoulos / -opulos). They don't have a TCKN: they carry a **Yabancı Kimlik No** (YKN: 11 digits from 99, same checksum),
or, without one, a **passport** or **home-country ID** number.

## Results (13 Nov 2026)

**Foreign names in real court prose.** We used TurkishLegalNER's held-out *test* sentences (Yargıtay), filled the
anonymised slots with names from held-out families (no spelling of them was used in training), and made 3 fills per
sentence: 1,011 names in total. The same slots filled with unseen Turkish names are the reference. 95% CIs come from a
document bootstrap.

| Detector | Foreign names | Turkish names, same slots | Gap | Precision |
| --- | --- | --- | --- | --- |
| Rules | 77.1% [73.9–80.1] | 93.0% | −15.9 | 99.9% |
| Katip Tiny v1 (published) | 80.3% [77.0–83.3] | 97.4% | −17.1 | 99.6% |
| Tiny-R (pii-names-tiny recipe, control) | 78.2% [74.9–81.3] | 94.4% | −16.2 | 98.3% |
| **Tiny-F (same recipe + foreign mix)** | **94.9% [92.8–96.5]** | 98.6% | **−3.7** | 95.6% |

Tiny-F against Tiny-R, on the same names: **+16.6 points [+13.9, +19.0]**, McNemar p = 8e-46. Tiny-F found 172 names
the control missed, and the control found 4 that Tiny-F missed. Same size (2.58 MB int8), seed, real text and trust
(0.5, which is also the best trust on Wiki NER dev for both models).

By origin (Tiny-R → Tiny-F): Arab 64% → 93%, Azerbaijani 46% → 74%, Western 76% → 93%, Persian 88% → 98%,
Armenian 86% → 97%, Georgian 89% → 99%, Greek 89% → 100%, Russian/Ukrainian 88% → 95%, Afghan 92% → 100%.
Azerbaijani names are still the weakest; many are written with Turkish word stems (Məmmədzadə, Fikrətoğlu).

**What it costs.**
- Precision on the court set drops from 98.3% to 95.6% (43 false names in 988 spans).
- On the foreign trap sentences (name-free text full of Hakim, Emir, Nur, Rahim, Halep, Kabil, Erbil...) false names
  go from 8.7 to 13.0 per 1,000 words.
- On Katip's name-free legal prose: 1 false name (0 before).
- The synthetic blind set stays at 364/365 and the held-out set at 271/275.
- On Turkish Wiki NER dev, Tiny-F is better than the control (F2 0.536 vs 0.495), so learning foreign names did not cost
  Turkish real-text recall.
- The legal scores in `score_legal.py` are not a fair check for Tiny-F, because it trained on TurkishLegalNER's train split.

**ID numbers** (generated petitions, 300 documents; the share left readable):

| | before | after (rules) |
| --- | --- | --- |
| YKN | 0% readable, but labelled "T.C. Kimlik No" | 0% readable, labelled "Yabancı Kimlik No" |
| Passport number | **100% readable** | 0% |
| Home-country ID (Kod-e Melli, Tazkira, SSN, FİN, AMKA ...) | **84% readable** | 0% (96% with the right label) |

Caveat: the petition templates and the ID rules were written by the same hand, so treat 0% as "the patterns work", not
as a field measurement. Real documents will phrase things in ways we haven't seen.

**A real petition** (Iranian client, UYAP .udf from a practising lawyer; used only for diagnosis, never stored in the repo):

- Before: both names were masked, but the YKN was labelled as a TCKN. "Türk" was masked about 25 times as a surname
  (Türk Vatandaşlığı Kanunu, Türk Medenî Kanunu), which garbled the legal citations.
- Before, and unknown until now: **the masked .udf still carried `sign.sgn`, the lawyer's e-imza signature**, with
  their name, title, city and certificate serial number in it.
- After: the names and the YKN are masked under the right labels, there are no false "Türk" names, and `sign.sgn` is
  dropped from masked .udf files. The signature can't match the masked text anyway.
- Still readable: the UETS address, the bar registration number and the application/letter numbers, plus employer
  names. They need a "reference number" rule or the firm dictionary.

## Rule changes (browser bundle `docs/katip_py.zip` and the server source)

- `YKN` type: TCKN-valid numbers starting with 99 and numbers after "Yabancı Kimlik No / YKN / Geçici Koruma Kimlik No".
- `PASSPORT` type: a number after a passport cue ("Pasaport No:", "… numaralı pasaportu", "Passport No"), and both lines
  of a passport's machine-readable zone (line 1 is the holder's name, masked as PERSON).
- `FOREIGN_ID` type: a number after a home-country ID cue. Iran's national code is checked with its check digit.
- The TCKN fallback ("any number after Kimlik No") no longer fires after a passport or foreign-ID cue.
- Law and regulation titles are never names ("Türk Vatandaşlığı Kanunu"), including bare repeats.
- About 70 cities foreign clients come from are not names (Halep, Tahran, Tiflis, Erivan ...).
- A model's span is dropped when every word of it is a stop/place word, and a single ordinary word that opens a sentence
  ("Emir komuta…", "Selam verip…") is not taken from the model alone.
- PR #6's form-row address rule no longer swallows paragraphs that start with "İkamet şartına…".
- Masked .udf files leave out `sign.sgn`.

Tests: `python src/tests/test_foreign_ids.py`. PR #6's `test_photo_rules.py` still passes, and the blind and held-out
synthetic sets give identical results before and after the rule changes.

## Files

| | |
| --- | --- |
| `names.py` | name families by origin, spelling variants, family-level train/test split (seed 0, 30% held out) |
| `ids.py` | YKN, passport and home-country ID generators with the phrases petitions put around them |
| `build.py` | test sets (court-foreign, court-turkish, petition-foreign, negatives-foreign) and training sets |
| `mix.py` | swaps foreign people into training documents (consistent per document, suffixes re-inflected, TCKN → YKN) |
| `score.py` | the scores above, with CIs and the paired test |
| `train_tiny.py` | trains Tiny-R and Tiny-F on CPU (about 12 minutes each on 2 cores) |
| `berturk_v3_free_gpu.ipynb` | BERTurk v3 on a free Kaggle or Colab GPU: v2 baseline, training, paired comparison |
| `results/` | this run's numbers and the held-out name families |

```
pip install faker
python lab/foreign/build.py
python lab/foreign/score.py                     # rules + published Tiny
python lab/foreign/train_tiny.py both --threads 2
python lab/foreign/score.py lab/runs/tiny_r_seed0:0.5 lab/runs/tiny_f_seed0:0.5 --tag tiny
```

## Data and licences

- Names: Faker person providers (MIT) for Georgian, Armenian, Greek, Russian, Ukrainian, Azerbaijani and Western names,
  romanised two ways (English-style and Turkish-style). Arab, Persian and Afghan lists were curated for this lab (CC0).
- We do **not** use the `names-dataset` package, because its data comes from the 2021 Facebook scrape. Wikidata
  given/family names (CC0) are the next source to add. Wikidata was not reachable from the build machine.
- Sentences: TurkishLegalNER (Apache-2.0), Turkish Wiki NER (CC BY-SA 4.0). Every ID number is generated.
