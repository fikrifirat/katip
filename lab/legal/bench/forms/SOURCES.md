# forms-id v0.1: sources and legal basis

`forms-id.jsonl` is KVKK-Bench's public forms track (DATA_PLAN.md §3): 34 document bodies × 3 party-block layouts =
102 templates, each filled 3 times (seed 20261114) = 306 documents, 3,438 gold spans. Built by
`lab/legal/forms_build.py`.

## What was taken from where

Only **structure** was taken: which headings a petition has (mahkeme/makam line, DAVACI / DAVALI / VEKİLİ blocks,
KONU, AÇIKLAMALAR, HUKUKİ SEBEPLER, DELİLLER, SONUÇ VE İSTEM, signature block), the order of the party fields and the
form labels themselves ("T.C. Kimlik No", "Vergi Kimlik No", "Adres", "IBAN" …). No sentence of any sample petition
was copied; every body text was written for this set.

| Source | Used for | Basis |
| --- | --- | --- |
| HMK md. 119 (dilekçe içeriği), CMK (şikâyet, itiraz, tutuklamaya itiraz) | Mandatory petition fields and their order | Statute; official texts are not protected (FSEK md. 31) |
| İİK Uygulama Yönetmeliği örnek formlar (takip talebi, ödeme emrine itiraz, şikâyet) | Field labels of execution forms | Regulation annex; FSEK md. 31 |
| Ankara Barosu Staj Rehberi 2024 (public PDF) | Bar forms: staj başvurusu, staj nakli, ruhsat, adli yardım; general petition layout | Structure and labels only, robots.txt respected |
| İstanbul Barosu public petition / form pages | Party-table layout ("uyap" and "table" styles) | Structure and labels only, robots.txt respected |
| KVKK md. 11/13 başvuru format (Veri Sorumlusuna Başvuru Usul ve Esasları Tebliği) | kvkk-basvuru body | Official text; FSEK md. 31 |

**UYAP Vatandaş** sample petitions were not used: they sit behind e-Devlet login. The "uyap" layout name refers to
the party-table shape common in UYAP-filed petitions, rebuilt from the public sources above.

## Fill

Every value is synthetic. Nothing comes from a real person or a real case.

- **Names, addresses, e-mails, phones, IBANs, birth dates:** Katip's slot-fill generator (`slotfill.py`), the same
  one the generated legal track uses. Foreign parties use the held-out name families in `lab/foreign`.
- **T.C. kimlik:** checksum-valid, never starting with 99 (a 99-prefix number reads as a YKN).
- **YKN / passport / foreign ID:** foreign parties' ID lines from `lab/foreign/ids.py`, shape- and checksum-valid
  per country.
- **VKN:** 10 digits with the GİB check digit (the same algorithm as Katip's `vkn_valid`).
- **Plate:** valid shapes only (province 01–81; 1 letter + 4–5 digits, 2 letters + 3–4, 3 letters + 2–3).
- Company names, tax offices, bar sicil numbers, courts, case numbers and amounts are random and are not spans.

## Gold

Spans are character offsets written by the generator while filling, so they are exact. Types: PERSON, ADDRESS,
PHONE, TCKN, EMAIL, VKN, BIRTH_DATE, IBAN, YKN, PASSPORT, FOREIGN_ID, PLATE. Party, lawyer, representative and witness
names are PERSON ("Av." is outside the span). Company names, courts, case numbers, bar and trade-registry numbers,
ordinary dates and amounts are not spans, as in the generated legal track.

## Licence

The generated set (templates, fills, gold) is released under CC BY 4.0, like KVKK-Bench's other generated tracks. The canary line on top of
the file marks it as a benchmark; do not train on it.
