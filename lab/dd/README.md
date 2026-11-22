# Katip DD (MVP): screen a person or company against Turkish public lists

A lawyer writing a due-diligence report checks the target against Turkish public sources that
have no API: MASAK asset-freeze lists, ilan.gov.tr notices and the Türkiye Ticaret Sicili
Gazetesi. Today that is done by hand. Katip DD keeps a local, dated copy of what can be
fetched politely, and answers "is this name on any of them?" with the **exact source record
and the official link**. It never summarises. A hit is a lead to check against the source,
and no hit is not a clearance.

```
python lab/dd/dd.py update                         # MASAK (ilan.gov.tr goes through ilan-lookup)
python lab/dd/dd.py search "Ayşe Nur Kocabey" --birth 1978
python lab/dd/dd.py search "Kuzeyrüzgarı Tekstil Ltd. Şti." --json
python lab/dd/dd.py status                         # what is stored, how fresh, what failed
python lab/dd/dd.py add-gazette ~/Documents/katip/tsg --ocr   # Gazete PDFs you saved (files or a folder)
python lab/dd/dd.py ilan-lookup "Kuzeyrüzgarı Tekstil" --headed  # ilan.gov.tr in a real browser, one target
python lab/dd/test_dd.py                           # offline tests (invented names)
python lab/dd/eval_dd.py --seed 2026 --n 600       # matching evaluation on your local snapshot
python lab/dd/check_un.py                          # MASAK art. 5 vs the UN Security Council list
```

Standard library only, except Playwright for `ilan-lookup` and PyMuPDF or pdfplumber for the
Gazette. Data lives in `~/.katip/dd` (`KATIP_DD_HOME`): a SQLite file and gzipped raw snapshots
of every fetch. **It is never committed**: the lists contain real people's ID numbers and
parents' names.

## Sources: what works on 21 Nov 2026

| Source | Status | How |
|---|---|---|
| MASAK, Law 6415 art. 5 (UN), art. 6 (foreign request), art. 7 (domestic), Law 7262 (WMD) | **Works** | The list pages are a React app whose own search box calls an open JSON endpoint. One POST per list, empty name filter, returns every row with aliases, ID/passport, birth date, organisation and the Resmî Gazete date/issue. robots.txt allows all. We also read the CSV files linked from each page. |
| ilan.gov.tr (Basın İlan Kurumu) | **Blocked from the cloud; browser route on your own computer** | The site's search API answers a plain, honestly labelled client with HTTP 403 (from the site's own IIS behind Kong, not a captcha). Sitemaps listed in robots.txt return 404. We do not forge headers or imitate a browser. `ilan-lookup` opens the site in a real browser on the lawyer's computer, types one target into the site's own search box, and keeps the notices the page loads: one target per run, ≤20 notice pages, 5 s between pages, stops on any captcha or block page. robots.txt disallows `/*tebligat`, so those notices are skipped, even though they are the ones that name individuals. **First live run from fikri's Mac (21 Nov 2026): works.** Query "konkordato" returned 12 notices; the 3 opened came through in full (~1,170 chars each), the rest as titles only, which are marked "title/summary only" in results. End-to-end test the same evening: a company picked from a full-text konkordato notice was looked up by name; the site returned 4 notices, 3 mention the company (July, October and November 2026 konkordato decisions) and all 3 came back as MATCH 1.00, for both the full name and "ertona tekstil" (lower case, no Turkish letters, no legal form); the 4th notice did not mention it and stayed below the threshold. No captcha or block page. Snippets mask 11-digit ID numbers of other people in a notice; through MCP the whole record is redacted the same way. |
| Türkiye Ticaret Sicili Gazetesi (TOBB) | **Works with the lawyer's own login, on their computer** | From the cloud the site resets the connection. From fikri's Mac (21 Nov 2026) it opens, but notices are shown only after login (e-Devlet, or a member account whose form has a captcha); there is no public issue archive. `katip-kalkan dd gazette-lookup NAME --office BURSA` opens Chrome on a new empty profile, the lawyer logs in, Katip fills the site's own İlan Görüntüleme form (office + first 5 letters; no captcha on the search), saves up to 3 free gazette pages (the "Gazete" link; never the paid "Sepete Ekle"). The login profile is deleted right after the login; only the site's cookies are kept, AES-256-GCM encrypted with Katip's key, for 8 hours, and later lookups run headless. Expired: logged out on the site and deleted on the next run; `dd gazette-logout` ends it at once. Pages are scans, read with Katip's OCR and split by layout (two columns, notices run on into the next column). **Tested on 3 real pages (Ertona, Bursa): Ertona found at 1.00 on all 3.** Bulk access is TOBB's paid web service (2026: 484,932 TL/yr image PDFs + index, up to 1,427,688 TL with tax no. and partners). From 1 Dec 2026 login is e-Devlet or e-signature only. Drop folder (`add-gazette`) still works for pages saved by hand. |

Uğur mentioned the Ministry of Trade once offered an API and withdrew it citing load. We found
no public successor: MERSİS and the Gazete are integrated with each other, but there is no open
API (search on 21 Nov 2026). It is a good reason to stay gentle: one request every 2 s, on demand.

Some .gov.tr servers send an incomplete certificate chain. `certs/gov_tr_intermediates.pem`
holds the two public intermediates (GeoTrust TLS RSA CA G1, Sectigo OV R36) that complete them.
TLS verification is never switched off.

## Matching

Deterministic, no model. `normalize.py`: Turkish-aware lower case (İ/I), diacritics folded,
company legal forms dropped (also misspelt ones), name particles (al-, el-, bin, abu) ignored,
transliteration canon (w→v, y→i, kh→h, ou→u…) and a small table of common transliterated given
names (Muhammad/Mohammed/Muhammed, Hussein/Hüseyin…; Mehmet≠Muhammad and Hasan≠Hüseyin on
purpose). `match.py`: per-word Jaro-Winkler with a prefix guard, order-free word alignment, a
penalty per unmatched word, a one-word query never reaches "match", exact ID/passport match = 1.0,
a different birth year ×0.85 and shown. Free-text notices (Gazette, ilan) are searched as windows
of consecutive words.

Bands: **match** ≥ 0.93, **review** ≥ 0.86. Scores are similarity, not probability.

## Validation (21 Nov 2026, snapshot of 2,310 MASAK rows)

**Coverage.** The endpoint returned exactly the count each list reports (473 + 109 + 1,442 + 277 =
2,301). The CSV files disagree slightly: art. 5 has 2 rows only in the CSV (spelling variants of
endpoint rows), art. 6 CSV is from January, has 112 rows to the endpoint's 109, and 6 of its rows match no endpoint row (some are older spellings of the same entity), art. 7 CSV has
1 person missing from the endpoint. For screening a missed name is worse than a duplicate, so the
9 CSV-only rows are kept and marked "only in the CSV file". The 7262 list has no CSV link we found.

**Against the UN list** (`check_un.py`, UN XML generated 21 Nov 2026): the UN has 473 ISIL/Al-Qaida
and Taliban entries, MASAK art. 5 has 473. 472 UN entries match a MASAK row at "match"; the one
miss (QDe.148, "The Army of Emigrants and Supporters") is published in MASAK under a Turkish
name, so an English query for it fails. Every MASAK art. 5 row has a UN counterpart. So art. 5 was
current with the UN on the day we checked.

**Freshness.** `status` shows when each list page last changed and its newest decision
(art. 5: 11 Nov 2026; art. 7: page changed 1 Oct 2026). MASAK publishes changes on its own
schedule, so a daily fetch is enough; `update` reports rows added and removed since the last run.

**Matching** (`eval_dd.py`, results in `results/eval.json`). Synthetic queries built from 600
listed records (dev 300 / test 300, split by record), and 1,200 decoys checked to be absent from
the lists. Held-out seed 2026, not looked at while tuning. Test split, shipped thresholds:

| Query kind | n | found at "review" | found at "match" |
|---|---|---|---|
| exact | 300 | 100% | 100% |
| ASCII, lower case | 300 | 100% | 100% |
| words reordered | 296 | 100% | 100% |
| listed alias | 75 | 100% | 100% |
| one typo | 286 | 98.6% | 85.7% |
| transliteration variant | 175 | 98.3% | 97.7% |
| middle name dropped | 113 | 92.9% | 8.8% (by design: an extra listed name means "review") |
| **all** | 1,545 | **99.0%** | 90.4% |

| Decoy kind | n | flagged "review" | wrongly "match" |
|---|---|---|---|
| common Turkish full name | 137 | 4.4% | 0.7% |
| listed person's first name + other surname | 153 | 2.0% | 1.3% |
| ordinary Turkish company | 165 | 0% | 0% |
| listed company with one word swapped | 145 | 0.7% | 0% |
| **all** | 600 | **1.7%** | 0.5% |

How to read this honestly:
- The query variants are generated by us. The transliteration score is partly circular, because
  the variant generator and the name table share spellings. Real users make other mistakes.
- In real DD almost every target is not listed, so the useful number is the decoy flag rate:
  about 1 clean name in 60 gets a "review" flag to check by hand. The "wrongly match" cases are
  real-looking namesakes (Mustafa Aslan vs Mustafa Arslan), which is why every hit carries the
  birth date and source link.
- No real lawyer queries yet. Next: Uğur's own past DD targets as a labelled set.

## MCP tools (for agents): now inside Katip Kalkan

The code moved to `connector/katip_kalkan/dd/`, and the tools are part of the Kalkan MCP server, so
one install gives masking and DD: `dd_screen`, `dd_record`, `dd_sources`, `dd_update` (refresh
MASAK) and `dd_ilan_lookup` (one named target on ilan.gov.tr, in a browser on your computer).
Results for the AI carry the listed name, dates, list, decision and links; third parties' ID numbers
and parents' names are removed (`id_number_matches` says yes or no instead). The same commands as
above also run as `katip-kalkan dd update|search|status|add-gazette|ilan-lookup`. Install for
Claude, Cursor, VS Code, Windsurf, Codex, Gemini CLI and ChatGPT: [connector/DD.md](../../connector/DD.md).
The scripts in this folder stay for evaluation.

**KVKK, not solved here.** Running this for yourself is processing public data for a legal
claim or obligation. Serving the index to another firm's agents makes the operator a controller or
processor of personal data (ID numbers, parents' names) for that firm's purpose: it needs a basis
under KVKK art. 5/2, a processing agreement, purpose limits, retention rules, and a VERBİS check.
Decide that before offering it as a hosted service.
