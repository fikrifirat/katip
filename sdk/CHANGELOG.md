# Changelog

Both packages share a version number and are released together. A change to what is masked by default
(new rule, new default threshold) bumps at least the minor version.

## Unreleased

Engine rules v0.2+98e64720 (docs/katip_py.zip). New detections, found by scoring on other teams' test sets:

- TROY cards (BKM's domestic scheme, numbers from 9792) are masked like Visa/Mastercard (Luhn still required).
- TCKN written in 3-3-3-2 groups with dots or dashes ("532.830.965.12", "614-371-928-12"); checksum still required.
- Birth date right after a bare "doğum" ("doğum 09.06.1983", "(doğum: 09.06.1983)").
- A number right after its label is masked even when it fails its check digits (a typo'd ID is still personal data):
  10 digits after "Vergi No" / "Vergi Kimlik Numarası" / "VKN", 16 digits after "Kart No" / "Kredi kartı", and an ID
  after "Kimlik Numarası", "Yabancı Kimlik No" or "YKN". "Vergi Kimlik No" is no longer read as a TCKN label.
- Blood group values ("0 Rh-", "AB Rh pozitif") as health data.
- The surname after "Kızlık Soyadı" / "Anne Kızlık Soyadı", even when no name list knows it.

With the items above, KVKK-Bench v0.1.2 public split was unchanged (0 of 2,037 documents differ for Rules and Base).

- Special-category values after their field label are masked as that category: "Tanı: ...", "Kullanılan İlaç: ...",
  "din hanesi ...", "etnik köken alanı ...", "sendika bilgisi ...", "adli sicil kaydı: ...", "biyometrik veri: ...".
  A bare label needs its colon; the label word alone is no longer masked when its value is.
- Generic medical words on their own are no longer masked (tedavi, ilaç, reçete, ameliyat, hastalık, tanı, teşhis,
  maluliyet, biyometrik); a condition keeps the word after it ("kanser tedavisi", "diyabet tanısı").
- Numbers read out as words ("tc dokuz dokuz yedi ..."), typed by the label before them; without a label only
  phone-length numbers. Amounts never match.
- E-mails written out ("ali [at] proton [dot] me"), IBANs in dashed groups, plates next to "plaka"/"plakalı" in any
  letter pattern, flat and door numbers ("daire no 28"), birth dates with month names, ISO dates and "'te doğan".
- Field labels at the start of a line ("Kayıt Saati:", "Poliçe Durumu:") are no longer read as names, and a cue word
  from a form row no longer reaches across a blank line.

KVKK-Bench v0.1.2 public split: Base KVKK-F2 93.10 → 93.16; the only changes are 13 removed false health masks.

## 0.1.1 (2026-11-16)

Package page fixes only, no change to what is masked.

- README: npm package is not published yet; say so instead of linking it. Removed a stray blank line.

## 0.1.0 (2026-11-16)

First release.

- Rules from `docs/katip_py.zip` (sha256 `aaf36904…98f0`), default threshold 0.5. Court profile masks UETS addresses, bar numbers and parties' own addresses, and keeps the property in dispute readable.
- Profiles `court`, `ai`, `anon`; `[AD SOYAD-1]`-style placeholders with `restore()`, or block style.
- `LeakError` when a detected value would remain in the output.
- Optional Nano, Mini and Base name models (ONNX), pinned by commit and SHA-256.
- Node and browser builds; command-line tools in both packages.
