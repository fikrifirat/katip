# Third-party components

| Component | Where | Licence |
|---|---|---|
| Katip Kalkan code and detection rules | `katip_kalkan/`, `engine.zip` | AGPL-3.0-or-later (commercial licence on request) |
| Katip Mask Nano · tr v1.1 | `katip_kalkan/models/katip-mask-nano-tr-v1.1/` | CC BY-SA 4.0, see its `LICENSE` (trained partly on Turkish Wikipedia NER data, Altinok 2023) |
| PaddleOCR PP-OCRv5 mobile det/rec ONNX | `katip_kalkan/ocr_models/` | Apache-2.0, PaddlePaddle (pinned revisions in each `SOURCE.txt`) |
| Statute index (`mevzuat_bak`) | `katip_kalkan/data/statutes.json.gz`, from Katip Cite (lab/cite) | Built from github.com/onurcan-b/acik-mevzuat (code MIT), a mirror of mevzuat.adalet.gov.tr; legislation texts are not protected by copyright (FSEK art. 31) |
| Yargıtay decisions (`emsal_ara`) | fetched on request from bedesten.adalet.gov.tr, cached in `~/.katip/emsal` | Court decisions are not protected by copyright (FSEK art. 31) |
| katip-mask 0.1.1 | downloaded by uv on first start | AGPL-3.0-only, same author |
| Katip Mask Base / Mini (optional, `KATIP_MODEL`) | downloaded once from Hugging Face (f1k/katip-mask-base, f1k/katip-mask-mini) | CC BY-SA 4.0 |
| onnxruntime 1.32.0 | downloaded by uv on first start | MIT, Microsoft |
| numpy 2.5.4 | downloaded by uv on first start | BSD-3-Clause |
| cryptography 50.0.2 | downloaded by uv on first start | Apache-2.0 or BSD-3-Clause |
| PyMuPDF 2.1 | downloaded by uv on first start | AGPL-3.0 (Artifex; commercial licence available from Artifex) |
| RapidOCR 3.10.0 | downloaded by uv on first start | Apache-2.0 |

PyMuPDF is AGPL-3.0, which matches Katip's own licence. A commercial licence of Katip that drops the
AGPL terms also needs a commercial PyMuPDF licence from Artifex, or a different PDF reader.
