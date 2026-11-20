# Katip Klasör

A desktop app for Mac and Windows. A lawyer drops case documents into a folder. Katip masks them **on the
computer**, shows the few spots a person should check, and puts clean copies in a separate folder for Claude,
ChatGPT or an email. A local case key puts the real names back into the AI's answer. Nothing is uploaded.

Design: [Katip desktop app: design v0.1](https://claude.ai/artifact/NK3ZskPNoVoXD5Gy6HRduv)

> Katip masks what it detects. The review screen exists because detection is not perfect: check the
> flagged spots before you share a file. Masked text is pseudonymised, and it is still personal data under KVKK.

## Folders

```
Documents/Katip/
  1 Gelen/<dava>/                drop originals here (never moved or changed)
  2 Maskeli/<dava>/              masked copies, written only after you approve the review
  3 Yapay zekâ cevapları/<dava>/ drop the AI's answer (.docx, .txt, .md)
  4 Geri yüklenmiş/<dava>/       the answer with real names, stays on this computer
~/.katip/                        case keys (vault/), review data (klasor/jobs, encrypted), audit log (klasor/audit)
```

Each case folder is one case key, shared with Katip Kalkan: a name is `[AD SOYAD-1]` in every file of the case.

| Dropped in | Masked copy |
|---|---|
| `.udf` | `.maskeli.udf` for UYAP (same-length blocks) and `.maskeli.docx` with placeholders for AI tools |
| `.docx`, `.txt`, `.md` | same format, placeholders, Word author fields cleared |
| PDF with text | `.maskeli.pdf`: the text is removed from the file, a black box with the placeholder drawn over it, metadata cleared |
| scanned PDF, photo | `.maskeli.docx` with the masked text read by OCR (a blacked-out image comes later) |

A masked copy's name drops words that may be personal data (`Ayşe Kaya vekaletname.pdf` becomes `vekaletname 3f2a.maskeli.pdf`).

## The review

| Flag | Rule | Default |
|---|---|---|
| Gözden kaçmış olabilir | scored 0.30 to 0.50: below the mask threshold, so not masked by the detector | masked |
| Tek başına ad | a one-word name | masked |
| Emin değil | masked with a score under 0.70 | masked |
| Fotoğraftan okunan sayfa | a page read by OCR | look at it |

Approving re-runs Kalkan's leak check on every output file, read back from its bytes. If a detected value is
still readable, nothing is written and the file goes to Hata. "Her zaman maskele" adds a word to the case's list.
Every step goes to the audit log (Kayıt, CSV export): time, user, file hash, safe name, profile, counts. The log
never holds a real value or an original file name.

## Test Katip on your own documents

Turn on **Bu belgeyle Katip'i test et** in the review screen to measure Katip on a firm's real files without
sending them anywhere.

1. Pick the document type.
2. Read the whole document. Click a mask that is wrong; select an unmasked value Katip missed and press
   **Seçili metin kaçmış**. Flag decisions count too ("Maskeleme" on a masked value is a false mask,
   "Maskele" on a missed candidate is a miss), and so do words added with "Her zaman maskele".
3. Tick **Belgenin tamamını ve kontrol listesini okudum**. Only files with this tick count.
4. **Test raporunu kaydet** writes `Katip test raporu <date>.json` to the Katip folder
   (or `katip-klasor eval --export rapor.json`).

Scores are for the detector as it ran, before your review: *found* = values it masked that you did not mark
wrong, *false* = masks you marked wrong, *missed* = every unmasked occurrence of a value you marked missed.
The report holds per-type counts, recall, precision and F2, and per file only the document type, format,
OCR yes/no, profile and a size bucket. It never holds a value, a file name, a case name or a position, and
the export refuses to write if any string in it appears in one of your documents. Read it before you send it.

Testing never makes the shared copy less private: a value you mark missed is masked in the shared copy too,
and a mask you mark wrong stays masked (only "Maskeleme" on a flagged value unmasks it).

## Run from the repo

```bash
pip install -e "desktop[window]"     # or: pip install cryptography pymupdf rapidocr onnxruntime numpy katip-mask==0.1.1 pywebview
python -m katip_klasor               # window; --browser opens the same screens in a browser
python -m katip_klasor scan          # mask what is waiting once, no window
python -m katip_klasor status
cd desktop && python -m pytest -q    # synthetic fixtures only
```

The first start downloads Katip Mask Base (111 MB, pinned commit, SHA-256 checked) through katip-mask. After
that the app makes no network calls. Settings can switch to Mini or Nano.

## Builds

`.github/workflows/klasor.yml` tests on Linux, Mac and Windows. On `main` and on a `klasor-vX.Y.Z` tag it builds
a Mac `.dmg` and a Windows `.zip` with PyInstaller, runs the built app once on a synthetic file, and on a tag
publishes them as a pre-release. The builds are **unsigned**: on a Mac, right-click the app and choose Open; on
Windows, choose More info, then Run anyway. Signing needs an Apple Developer account and a Windows code-signing certificate.

## Modules

`katip_klasor/modules.py` lists the tools in the app. v0.1 has Maskeleme; Katip Emsal, Katip Cite and Katip
Taslak are shown as "Yakında" (coming soon) placeholders. They would use the same case folders, case keys
and audit log.

## Licence

AGPL-3.0-or-later, as the rest of the repo; commercial licence on request ([COMMERCIAL.md](../COMMERCIAL.md)).
Fonts: Inter and Space Grotesk (SIL OFL, licences in `katip_klasor/ui/fonts`).
