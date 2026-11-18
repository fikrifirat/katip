PaddleOCR PP-OCRv5 mobile text detector (`det/`) and Latin mobile recogniser (`rec/`), the official ONNX
exports by PaddlePaddle, Apache-2.0. Same files and pinned revisions as `docs/vendor/paddleocr`
(see `src/fetch_paddleocr.py` and each `SOURCE.txt`). `rec/keys.txt` is `dict.json`, one character per line.

The recogniser's `inference.onnx` (8 MB) is not in git, because the Claude directory takes no file over 5 MiB:
`build_bundle.py` puts it into the `.mcpb`, and the plugin downloads it once (`ocr.rec_model()`, pinned revision and SHA-256).
