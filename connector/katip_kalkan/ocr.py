"""Local OCR for scans and phone photos, the Python twin of the browser's "Otomatik" reader.

* PaddleOCR PP-OCRv5 (mobile detector + Latin recogniser, Apache-2.0, the same ONNX files as
  docs/vendor/paddleocr) through RapidOCR on onnxruntime: reads handwriting and photos.
* Tesseract (`tesseract` command with the `tur` language) for clean printed scans, when installed.

Routing ("auto", the default): PaddleOCR on pages with ballpoint-blue ink or that look like a photo
(little white paper), Tesseract on everything else; PaddleOCR on every page when Tesseract is not
installed. KATIP_OCR=paddle|tesseract|auto forces a reader. Everything runs on this device.

The browser's rule looks at ink blobs; this one uses whole-page colour statistics, which is close
for the forms in lab/photo_forms but not identical.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = HERE / "ocr_models"
DPI = int(os.environ.get("KATIP_OCR_DPI", 200))
_paddle = None


def available() -> list[str]:
    out = []
    try:
        import rapidocr  # noqa: F401
        if (MODELS / "det" / "inference.onnx").exists():
            out.append("paddle")
    except ImportError:
        pass
    if _tesseract_ok():
        out.append("tesseract")
    return out


def _tesseract_ok() -> bool:
    exe = shutil.which("tesseract") or next((p for p in ("/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract")
                                             if Path(p).exists()), None)
    if not exe:
        return False
    try:
        langs = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "tur" in langs.split()


def _tess_exe() -> str:
    return shutil.which("tesseract") or next(p for p in ("/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract")
                                              if Path(p).exists())


def fix_case(w: str) -> str:
    """Mostly-capital words come out mixed ("BOZDEMiR"): upper-case them the Turkish way, keep the
    suffix after an apostrophe (same as fixCase in src/paddle_ocr.js)."""
    k = min([w.index(q) for q in ("'", "’") if q in w] + [len(w)])
    stem, rest = w[:k], w[k:]
    letters = [c for c in stem if c.isalpha()]
    up = sum(1 for c in letters if c != c.lower())
    if len(letters) < 3 or up == len(letters) or up * 2 < len(letters):
        return w
    return stem.replace("i", "İ").replace("ı", "I").upper() + rest


def route(rgb) -> str:
    """auto: which reader for this page image (H x W x 3 uint8)."""
    want = os.environ.get("KATIP_OCR", "auto")
    have = available()
    if want in have:
        return want
    if not have:
        raise RuntimeError("no OCR installed: Katip needs rapidocr (fetched automatically with uv) or "
                           "`brew install tesseract tesseract-lang`")
    if len(have) == 1:
        return have[0]
    import numpy as np
    small = rgb[::4, ::4].astype(np.int16)
    r, g, b = small[..., 0], small[..., 1], small[..., 2]
    blue = ((b - r) > 35) & ((b - g) > 10) & (b > 60)
    white = (r > 200) & (g > 200) & (b > 200)
    pen = blue.mean() > 0.001
    photo = white.mean() < 0.55
    return "paddle" if pen or photo else "tesseract"


def _paddle_engine():
    global _paddle
    if _paddle is None:
        from rapidocr import RapidOCR
        keys = MODELS / "rec" / "keys.txt"  # dict.json from the browser build, one character per line
        _paddle = RapidOCR(params={"Global.use_cls": False, "Global.log_level": "error",
                                   "Det.model_path": str(MODELS / "det" / "inference.onnx"),
                                   "Rec.model_path": str(MODELS / "rec" / "inference.onnx"),
                                   "Rec.rec_keys_path": str(keys)})
    return _paddle


def _lines(boxes: list[tuple[float, float, float, str]]) -> str:
    """(y_centre, x_left, height, text) boxes -> reading-order lines; boxes on one row join with spaces."""
    rows: list[list] = []
    for y, x, h, t in sorted(boxes):
        if rows and abs(rows[-1][0] - y) < max(8.0, 0.5 * h):
            rows[-1][1].append((x, t))
        else:
            rows.append([y, [(x, t)]])
    return "\n".join(" ".join(t for _, t in sorted(items)) for _, items in rows)


def _ocr_paddle(rgb) -> str:
    r = _paddle_engine()(rgb)
    if r is None or r.boxes is None:
        return ""
    boxes = []
    for quad, txt in zip(r.boxes, r.txts):
        ys, xs = [p[1] for p in quad], [p[0] for p in quad]
        boxes.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), " ".join(fix_case(w) for w in txt.split())))
    return _lines(boxes)


def _ocr_tesseract(rgb) -> str:
    from PIL import Image
    with tempfile.TemporaryDirectory() as d:  # page image lives only in a private temp dir
        p = Path(d) / "page.png"
        Image.fromarray(rgb).save(p)
        r = subprocess.run([_tess_exe(), str(p), "stdout", "-l", "tur", "--psm", "6"],
                           capture_output=True, text=True, timeout=120, env={**os.environ, "OMP_THREAD_LIMIT": "1"})
    return r.stdout


def ocr_page(rgb) -> tuple[str, str]:
    reader = route(rgb)
    return (_ocr_paddle(rgb) if reader == "paddle" else _ocr_tesseract(rgb)), reader


def pixmap_rgb(pix):
    import numpy as np
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    return np.ascontiguousarray(a[..., :3])


def image_rgb(data: bytes):
    import io
    import numpy as np
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    return np.asarray(im)
