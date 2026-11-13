"""Fetch the PaddleOCR models used for handwriting and phone photos into src/models/paddleocr.

  python src/fetch_paddleocr.py

PP-OCRv5 mobile text-line detector + Latin mobile recogniser (covers Turkish ç ğ ı İ ö ş ü), the official
ONNX exports published by PaddlePaddle on Hugging Face, Apache-2.0. Revisions and checksums are pinned,
so a rebuild gets exactly the files that were benchmarked (lab/ocr_bench/README.md). build_site.py copies
the folder to vendor/paddleocr; the browser loads them from the site itself, never from Hugging Face.
"""
import hashlib, json, sys, urllib.request
from pathlib import Path

import yaml  # PyYAML: the character list lives in inference.yml

MODELS = {
    "det": ("PaddlePaddle/PP-OCRv5_mobile_det_onnx", "e6f4fa85f00e168c862bc462aebca69eef9b3d3d",
            "a431985659dc921974177a95adcfbb90fd9e51989a5e04d70d0b75f597b6e61d"),
    "rec": ("PaddlePaddle/latin_PP-OCRv5_mobile_rec_onnx", "89d3a50e2c27e2e7cceeab0e944c25c807d5db4f",
            "7888113072263cb471b93f66dd5e2ad70548dc526fa1ace760d0d973dd121498"),
}
out = Path(__file__).parent / "models/paddleocr"
for name, (repo, rev, sha) in MODELS.items():
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    for f in ("inference.onnx", "inference.yml"):
        if not (d / f).exists():
            urllib.request.urlretrieve(f"https://huggingface.co/{repo}/resolve/{rev}/{f}", d / f)
    got = hashlib.sha256((d / "inference.onnx").read_bytes()).hexdigest()
    if got != sha:
        sys.exit(f"{repo}: checksum {got} does not match the pinned {sha}")
    (d / "SOURCE.txt").write_text(f"https://huggingface.co/{repo}/tree/{rev}\nLicence: Apache-2.0 (PaddlePaddle/PaddleOCR)\n")
    if name == "rec":
        chars = yaml.safe_load((d / "inference.yml").read_text())["PostProcess"]["character_dict"]
        (d / "dict.json").write_text(json.dumps(chars, ensure_ascii=False))
    (d / "inference.yml").unlink()
    print(name, repo, "ok")
