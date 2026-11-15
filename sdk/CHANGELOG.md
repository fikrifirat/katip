# Changelog

Both packages share one version number and are released together. Format:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [semver](https://semver.org/).
A change in what gets masked by default (a new rule, a changed default threshold) is at least a minor
version, since the same input then gives different output.

## 0.1.0 (unreleased)

First release, on PyPI and npm as `katip-mask`.

- Engine: the rules of Katip Kalkan and the web demo (`docs/katip_py.zip` sha256 `dfb86f1e…7428`), with
  default threshold 0.5.
- Profiles `court`, `ai`, `anon`; Turkish placeholders (`[AD SOYAD-1]`) with `restore()`, or blocks.
- Fail-closed masking: every detected value masked everywhere, or `LeakError`.
- Optional on-device name models Nano, Mini, Base (ONNX), pinned by commit and SHA-256; shared cache.
- Node and browser builds (onnxruntime-node / onnxruntime-web); CLIs with interchangeable JSON.
