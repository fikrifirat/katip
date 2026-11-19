# Changelog

Both packages share a version number and are released together. A change to what is masked by default
(new rule, new default threshold) bumps at least the minor version.

## Unreleased

Engine rules v0.2+54f36be8 (docs/katip_py.zip). New detections, found by scoring on other teams' test sets:

- TROY cards (BKM's domestic scheme, numbers from 9792) are masked like Visa/Mastercard (Luhn still required).
- TCKN written in 3-3-3-2 groups with dots or dashes ("532.830.965.12", "614-371-928-12"); checksum still required.
- Birth date right after a bare "doğum" ("doğum 09.06.1983", "(doğum: 09.06.1983)").
- A number right after its label is masked even when it fails its check digits (a typo'd ID is still personal data):
  10 digits after "Vergi No" / "Vergi Kimlik Numarası" / "VKN", 16 digits after "Kart No" / "Kredi kartı", and an ID
  after "Kimlik Numarası", "Yabancı Kimlik No" or "YKN". "Vergi Kimlik No" is no longer read as a TCKN label.
- Blood group values ("0 Rh-", "AB Rh pozitif") as health data.
- The surname after "Kızlık Soyadı" / "Anne Kızlık Soyadı", even when no name list knows it.

KVKK-Bench v0.1.2 public split: unchanged (0 of 2,037 documents differ for Rules and Base).

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
