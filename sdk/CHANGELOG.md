# Changelog

Both packages share a version number and are released together. A change to what is masked by default
(new rule, new default threshold) bumps at least the minor version.

## 0.1.0 (2026-11-15)

First release.

- Rules from `docs/katip_py.zip` (sha256 `dfb86f1e…7428`), default threshold 0.5.
- Profiles `court`, `ai`, `anon`; `[AD SOYAD-1]`-style placeholders with `restore()`, or block style.
- `LeakError` when a detected value would remain in the output.
- Optional Nano, Mini and Base name models (ONNX), pinned by commit and SHA-256.
- Node and browser builds; command-line tools in both packages.
