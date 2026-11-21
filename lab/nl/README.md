# Katip NL: Dutch masking, wetten and rechtspraak (personal use)

A Dutch counterpart of Katip for fikri's own documents in the Netherlands: mask personal data under the
AVG/GDPR before any text goes to a cloud model, check statute citations against wetten.overheid.nl, and
check ECLI numbers against rechtspraak.nl. Every label shows English next to Dutch (or Turkish).

Status: first runnable slice, standard library only, text files. Not a product, not legal advice.

```bash
cd lab/nl
python -m katip_nl mask    brief.txt --lang en        # -> brief.masked.txt + brief.vault.json (stays local)
python -m katip_nl restore antwoord.txt --vault brief.vault.json
python -m katip_nl check   brief.txt                  # citations + ECLIs (sends only ids, never text)
python -m pytest tests -q                             # 14 offline tests, synthetic data
python eval_rechtspraak.py --n 60                     # false-positive check on real court text
```

## What it masks

| Type | How | Default |
| --- | --- | --- |
| BSN (citizen service number) | 9 digits passing the 11-proef; with a "BSN" cue also 8 digits or a failed checksum (typo/scan) | masked |
| IBAN | mod-97, NL format checked (bank code + 10 digits), foreign IBANs too | masked |
| Postcode + house number | `1016 EZ` only next to a town or street, never after "Postbus"; `Keizersgracht 312-III` keeps the street | masked (street and town readable) |
| Full address | `--full-address` | off |
| Phone, e-mail | +31 / 06 / (020) / foreign | masked |
| Licence plate | the 14 Dutch side codes, with dashes | masked |
| Passport / ID card / driving licence no. | document-number shape (no letter O) or a cue | masked |
| V-number (IND) | 10 digits after "V-nummer" / "vreemdelingennummer" | masked |
| Date of birth | a date in the same sentence as "geboren", "geboortedatum" | masked |
| VAT id (btw-id) | NL#########B## (identifies sole traders) | masked |
| KvK, RSIN | with a cue | shown for review, not masked (companies are not personal data; turn on for sole traders) |
| Names | title + name (dhr., mevr., mr., de heer ...), initials + surname with tussenvoegsels (J.P. van der Berg), form fields (Naam:, Eiser:), signature blocks, then every later mention of that surname gets the same placeholder | masked |

Kept readable on purpose: ECLI numbers, case and roll numbers (C/13/745123 / HA ZA 26-0412, 200.123.456/01),
article citations, Staatsblad references, court names, ordinary dates.

## Measured so far (20 Nov 2026)

- 14 synthetic tests pass (checksums, each type, roundtrip, legal references untouched, negative prose).
- Real text: 120 decisions from rechtspraak.nl open data (Sep 2026 onwards, ~170k words in the 60-decision
  run). Courts pseudonymise parties but leave judges', clerks', lawyers' and experts' names in, so every
  PERSON hit there should be a real professional's name. After four rounds of fixes: 435 distinct name
  strings, all real names except roughly 3 (e.g. "V. Hierdoor", a numbered heading). Non-name false positives:
  0 house numbers or postcodes outside real addresses (one court address remains, correctly found).
- Caveat: these are the same decisions the rules were tuned on, so they are a development set. Recall on
  parties' names is not measured yet (they are already pseudonymised in this source). Next: a held-out set
  of fresh decisions, plus synthetic documents where the [eiser]/[adres] slots are filled with invented
  names and addresses, the same method as KVKK-Bench.

## Plan

**1. Masking models (names are the weak spot for rules).** Options, all usable offline:

| Model | Licence | Size | Why / why not |
| --- | --- | --- | --- |
| `urchade/gliner_multi_pii-v1` | Apache-2.0 | ~1.2 GB | Zero-shot multilingual PII incl. Dutch; quickest to try as the `extra=` span source. Large and slow (GLiNER2 on Turkish was 1.2 GB / 82 ms per doc). |
| `knowledgator/gliner-pii-base-v1.0` | Apache-2.0 | base | Newer GLiNER PII; check Dutch quality. |
| `openai/privacy-filter` | Apache-2.0 | check | Recent (Apr 2026) PII filter; check Dutch support before relying on it. |
| RobBERT-2023 (`DTAI-KULeuven/robbert-2023-dutch-base/large`) | MIT | 125 M / 355 M | Best Dutch encoder to fine-tune a Katip Mask NL, same recipe as Katip Mask Base (BERTurk). |
| `pdelobelle/robbert-v2-dutch-ner` | MIT | 125 M | Ready Dutch NER (PER/LOC/ORG); trained on CoNLL-2002, check that dataset's terms before any redistribution. |
| Deduce (`deduce` 3.0.6, UMC Utrecht) | LGPL-3.0 | rules + lists | Dutch clinical de-identification with Dutch name/place lists; good baseline and source of lookup lists. |
| Presidio | MIT | - | No Dutch country recognizers in 2.2.366 (checked); our rules fill that gap. |
| `Babelscape/wikineural-multilingual-ner` | CC BY-NC-SA | - | Non-commercial: fine for personal use, not for anything shipped. |
| spaCy `nl_core_news_lg` | CC BY-SA 4.0 | 560 MB | Generic NER; weaker on legal text. |

Recommendation: keep rules as the floor (they do the checksummed IDs), add GLiNER multi-PII as a first
`extra=` model to measure, then distil into a small RobBERT-based "Katip Mask NL" only if it beats rules +
GLiNER on a held-out Dutch set. Same discipline as KVKK-Bench: a frozen test set before any tuning.

**2. Wetten (Dutch Mevzuat).** Done for the first slice: SRU search on zoekservice.overheid.nl finds the
version in force on a date, the act XML comes from repository.officiele-overheidspublicaties.nl, cached
in `~/.cache/katip-nl/bwb`. BW books 1-10, Rv, Sr, Sv, Awb, Gw, UAVG, Vw 2000, WOR, IB/LB/OB/AWR mapped
(ids checked against SRU on 20 Nov 2026). Statute text has no copyright (Auteurswet art. 11). Next: more
acts on demand, AVG articles from EUR-Lex, and an English gloss next to each article (local model by
default; the text is public, so a cloud translator is allowed for statute text but never for documents).

**3. Rechtspraak (Dutch Emsal).** Done: ECLI check with court, date, area of law, summary and formal
relations (appeal, cassation, AG opinion) from data.rechtspraak.nl. The open-data API has filters (date,
court, area, type) but no full-text search, so phase 2 is a local index (BM25 + a Dutch embedding model)
over a downloaded subset. This is easier than in Turkey: Rechtspraak publishes the decisions as open data
for reuse and they are already pseudonymised. Wet/article -> decisions links exist in LiDO
(linkeddata.overheid.nl, needs a free account).

**4. Document scanner.** Built in the scanner thread (branch `doctype-classifier`,
`connector/katip_kalkan/doctype.py`): `detect_language()` picks tr/nl/en, `classify()` names the type from a
per-language pack (`doctype_packs/nl.pack.json`: arbeidsovereenkomst, huurovereenkomst, loonstrook, IND-beschikking,
WOZ-beschikking, dagvaarding, vonnis ...), and the Dutch steps call `katip_nl.detect` (on device),
`katip_nl.wetten.check_text` and `katip_nl.rechtspraak.check_text` (network, ids only). Next here: synthetic
Dutch documents per type so it can train `nl` weights.
`detect()` returns the same span dicts as Turkish Katip (`src/py/local_detect.py`), so the masking UI,
vault, restore and Kalkan relay can be reused unchanged.

**5. UI.** Labels already carry English (`labels.py`: `label("BSN", "nl")` -> "Burgerservicenummer (BSN) /
Citizen service number"; `"tr"` gives Turkish / English). Next: plug `katip_nl` into the browser app's
Pyodide bundle behind a language switch, and add the same English-alongside labels to the Turkish UI.

**Privacy rules for this work.** fikri's own documents (Control_Room) are read only to learn which
document types exist. They never go into the repo, a dataset, or an external service. Tests use invented
data; real-text checks use public, court-pseudonymised decisions.
