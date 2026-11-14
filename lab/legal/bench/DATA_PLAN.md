# KVKK-Bench v0.2 data plan

Status: draft, 14 Nov 2026. Based on a 30-minute feasibility check (low-rate fetching, robots.txt
respected, all fetched text kept on the maintainer's machine; only counts are reported here).

Rule for every new source: **public-by-law personal data stays local and goes only into the hidden split.
We publish scores, never the text.**

## Summary

| # | Track | What is real | Source | Licence / legal basis | Count estimate | Split | Labelling effort |
|---|---|---|---|---|---|---|---|
| 1 | `special-health` | real health text from real cases (diagnoses, reports, disability rates); names already anonymised by the court, filled with synthetic names | Yargıtay, Danıştay (mevzuat.adalet.gov.tr), AYM (already crawled) | court decisions are free to use (FSEK art. 31); real health data, so hidden only | 765 of 5,507 crawled decisions mention health; 229 have strong cues (diagnosis, report, disability rate) | hidden | pre-label with rules, human review ~1 min per doc; 300 docs ≈ 6–8 h |
| 2 | `special-criminal` | real names + offence + court + dates in criminal judgments served by public notice | Resmî Gazete, ilân section, *Yargı İlânları* | ilanen tebliğ under Tebligat Kanunu art. 28–29; public by law, but real people: hidden only | ~2–5 PDFs per day (5, 2, 3 on 13, 12, 14 Nov), ~6 notices per 4-page PDF → ~15 notices/day, ~4,000/year | hidden | scans: OCR, then label ~2 min per notice; 200 notices ≈ 7 h |
| 3 | `forms-id` | real UYAP and bar-association form layouts; IDs and contact data are fake but checksum-valid (TCKN, VKN, IBAN, phone, address) | UYAP Vatandaş sample petitions, İstanbul/Ankara bar sample petitions | official forms: structure only, re-typed; fill values are ours | ~100–200 templates → 300 filled docs | public | none: spans come from the fill |
| 4 | `pilot-gold` | real client documents | 2–3 pilot firms | firm is controller; processed on the firm's machines under a DPA, nothing leaves the firm | 3 firms × 50 docs | private (scores only) | lawyer 5–10 min per doc, with Katip's review screen |
| 5 | `photo-handwritten`, `scan` | synthetic phone photos (v0.1.3); real scans from #2 | `lab/photo_forms`, Resmî Gazete scans | ours; scans as in #2 | 60 photos (v0.1.3); scans from #2 | public dev + hidden | photos none; scans as #2 |
| — | OCRTurk | real scanned and born-digital pages | github.com/metunlp/ocrturk | **no licence**: local measurement only, never committed or published | to be counted | not used | — |
| — | belediye meclis kararları | real council decisions | municipality sites | public; robots allow (Çankaya `Disallow:` empty) | — | dropped (see below) | — |

Order of work: 1 → 3 → 4 → 2 → 5. #2 is the richest real-name source but needs OCR, so it lands with the scan track.

## 1. Health in court decisions (priority 1)

* Local crawl (`lab/data/legal_web/raw.jsonl`, git-ignored): Yargıtay 4,000, Danıştay 333, AYM 1,174 decisions.
* Any health language: Yargıtay 423, Danıştay 27, AYM 315. Strong cues (tanısı, teşhis, epikriz, psikiyatri,
  maluliyet, engel oranı, meslekte kazanma gücü, ameliyat, kanser, HIV, akıl hastalığı): Yargıtay 82, Danıştay 10,
  AYM 137 docs, 748 mentions.
* The Yargıtay crawl was query-driven (e.g. "tazminat"); add queries like "maluliyet", "Adli Tıp raporu",
  "engellilik", "iş kazası" to reach 300 strong documents.
* Label: span type `HEALTH` on the diagnosis / report finding / disability rate, plus the existing slot fill for
  the anonymised person. Scored as a separate track; leak = any health span left readable.

## 2. Resmî Gazete Yargı İlânları (criminal records, Art. 6)

* URL pattern `resmigazete.gov.tr/ilanlar/eskiilanlar/YYYY/MM/YYYYMMDD-2.htm` is an index; each notice group is a
  PDF (`YYYYMMDD-2-N.pdf`).
* The PDFs are **scans** (sample: 4 pages, 4 images, no fonts, no text layer). Local OCR (macOS Vision) of one PDF:
  818 words, 6 "ilanen tebliğ olunur", 12 sanık/şüpheli, 4 birth-date mentions, defendants' and parents' names in
  clear, offence names; 0 TCKN in the sample.
* robots.txt of resmigazete.gov.tr has only Googlebot noindex lines. **ilan.gov.tr disallows `/*tebligat`: not used.**
* This is Art. 6 data (criminal convictions) about real, named people. Hidden split only, never published, keep the
  OCR text local, fetch ≤ 1 request per 5 s.

## 3. Forms with fake IDs

* Not fetched in this check. Plan: collect ~100–200 form layouts (UYAP sample petitions, bar sample petitions),
  re-type the structure, fill with generated persons whose TCKN/VKN/IBAN pass checksum, Turkish phone and
  address formats, and some foreign names.
* Gives the ID/contact tracks real-looking layout at zero labelling cost. Public.

## 4. Pilot-firm private gold

* Firms label their own documents in Katip's review screen; Katip computes the score on the firm's machine and
  sends back only the numbers (per type recall/precision, leak).
* Needs: DPA, a one-page labelling guide, an export that contains no text.

## 5. Photo and scan tracks

* v0.1.3 photo set (60 synthetic photos, seed 3011) scored on box coverage: leaked < 70 % covered, over-masked > 30 %.
* First scores (`bench_run.py --track photo`, same OCR for every system): Katip rows leak 5.2–6.7 %, 0 TCKN/name
  leaks, misses are building/door numbers; Presidio 51.5 %, kvkk-pii 77.9 %. Over-masked readable streets 18–22 %.
* OCRTurk (local count only): 180 one-page PDFs (45 each academic / non-academic / slides / thesis), all with a
  text layer, 19 with a full-page image; rules find ~107 person mentions in 33 docs, mostly authors. Low value for KVKK.
* Real scans come from #2; Çankaya council PDFs could add name-free scan negatives.

## Belediye meclis kararları: dropped for PII

* Çankaya: monthly decision book, ~230 scanned pages (Aralık 2024: 230 pages, 230 images, no text). OCR of 10
  sampled pages: 1,832 words, 0 TCKN, 0 phone numbers, mostly council members (public officials), ada/parsel and
  street names, a few citizen names in zoning decisions.
* Kadıköy index reachable; İzmir path 404; İBB timed out.
* Low personal-data density per page and heavy OCR cost. Possible later use: false-alarm negatives for the scan track.
