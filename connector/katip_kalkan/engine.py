"""Load Katip's detection engine and read documents, entirely on this device.

The engine is the same pure-Python bundle the browser demo runs in Pyodide
(docs/katip_py.zip: recognizers, word lists, overlap rules, txt/docx/udf
readers). Nothing here needs the network.

Lookup order for the bundle:
  1. $KATIP_ENGINE (a .zip or an unpacked folder)
  2. katip_kalkan/engine.zip (copied in by build_bundle.py)
  3. <repo>/docs/katip_py.zip (when running from a checkout)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
_loaded = None

KINDS = {".txt": "txt", ".md": "txt", ".udf": "udf", ".docx": "docx", ".pdf": "pdf"}


def _bundle() -> Path:
    for p in (os.environ.get("KATIP_ENGINE"), HERE / "engine.zip", HERE.parents[1] / "docs" / "katip_py.zip"):
        if p and Path(p).exists():
            return Path(p)
    raise RuntimeError("Katip engine not found: set KATIP_ENGINE or run connector/build_bundle.py")


def _unpack(zpath: Path) -> Path:
    """Word lists are read from disk, so the zip is unpacked once into a private cache."""
    digest = hashlib.sha256(zpath.read_bytes()).hexdigest()[:12]
    from .vault import katip_home
    dst = katip_home() / "engine" / digest
    if not (dst / "local_detect.py").exists():
        dst.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath) as z:
            for name in z.namelist():  # no path traversal from a tampered zip
                if name.startswith("/") or ".." in Path(name).parts:
                    raise RuntimeError(f"bad entry in engine zip: {name}")
            z.extractall(dst)
    return dst


def load():
    """Returns (local_detect, local_formats) modules."""
    global _loaded
    if _loaded is None:
        b = _bundle()
        root = b if b.is_dir() else _unpack(b)
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        import local_detect  # noqa: E402
        import local_formats  # noqa: E402
        _loaded = (local_detect, local_formats)
    return _loaded


def kind_of(path: Path) -> str:
    k = KINDS.get(path.suffix.lower())
    if not k:
        raise ValueError(f"unsupported file type {path.suffix!r}: use .txt, .docx, .udf or a text-layer .pdf")
    return k


def read_text(path: Path) -> tuple[str, str, bytes]:
    """Returns (kind, plain text, original bytes)."""
    kind = kind_of(path)
    data = path.read_bytes()
    if kind == "pdf":
        try:
            import pymupdf  # optional; the browser app uses MuPDF.js for burn-in PDF redaction
        except ImportError:
            raise ValueError("PDF needs `pip install pymupdf` for the local connector "
                             "(or use the Katip app for scanned PDFs)") from None
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            text = "\n\n".join(p.get_text() for p in doc)
        if not text.strip():
            raise ValueError("this PDF has no text layer (scan): open it in the Katip app, which runs OCR locally")
        return kind, text, data
    _, fmt = load()
    return kind, fmt.extract(kind, data), data


def detect(text: str, threshold: float = 0.7, entities: list[str] | None = None,
           mask_terms=(), allow_terms=()) -> list[dict]:
    det, _ = load()
    spans = json.loads(det.detect_json(text, json.dumps({
        "threshold": threshold, "entities": entities, "mask": list(mask_terms), "allow": list(allow_terms)})))
    return [s for s in spans if not s.get("flag_only")]


def redact_bytes(kind: str, data: bytes, spans: list[dict], style: str = "label") -> bytes:
    _, fmt = load()
    return fmt.redact(kind, data, json.dumps(spans), style)


def leaked(out_text: str, spans: list[dict]) -> list[str]:
    _, fmt = load()
    return json.loads(fmt.leak_check(out_text, json.dumps(spans)))


def label_name(entity_type: str) -> str:
    load()
    from katip_redact.recognizers import ENTITY_LABELS_TR
    from katip_redact.textutil import tr_upper
    return tr_upper(ENTITY_LABELS_TR.get(entity_type, entity_type))
