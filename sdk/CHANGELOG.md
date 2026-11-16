# Changelog

Both packages share a version number and are released together. A change to what is masked by default
(new rule, new default threshold) bumps at least the minor version.

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
