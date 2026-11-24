"""Load Katip's detection engine and read documents, entirely on this device.

The engine is the same pure-Python bundle the browser demo runs in Pyodide
(docs/katip_py.zip: recognizers, word lists, overlap rules, txt/docx/udf/xlsx/eml/msg
readers). Nothing here needs the network.

Detection comes from the katip-mask SDK (pinned to SDK_PIN, installed by launch.py with uv), so the
connector, the SDK and the browser app run the same tested rules. The bundle below still provides the
document readers (.txt/.docx/.udf), redaction and the leak check, and is the detection fallback when
katip-mask is missing (no uv, offline first start) or KATIP_ENGINE points elsewhere.

Lookup order for the bundle:
  1. $KATIP_ENGINE (a .zip or an unpacked folder; also forces its own detection)
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
SDK_PIN = "0.1.1"  # exact katip-mask version (launch.py); a new SDK version needs a Kalkan release
_loaded = None
_source = "bundled rules"

KINDS = {".txt": "txt", ".md": "txt", ".udf": "udf", ".docx": "docx", ".pdf": "pdf",
         ".xlsx": "xlsx", ".eml": "eml", ".msg": "msg",
         ".png": "image", ".jpg": "image", ".jpeg": "image", ".tif": "image", ".tiff": "image", ".webp": "image"}

# Masking profiles, the same ladder as PROFILES in src/app.js: each masks everything the one before it does.
CASE = ["CASE_NO", "BAR_NO"]
ANON = ["DATE", "PLACE", "INSTITUTION"]
PROFILES = {
    # a masked lawyer's bar registry number would give the name away, so it goes with the names
    "court": {"label": "Mahkemeye sunum", "addr": "street", "extra": ["BAR_NO"], "drop": ["CRIMINAL_RECORD"]},
    "ai": {"label": "Yapay zekâ ile paylaşım", "addr": "full", "extra": CASE, "drop": []},
    "anon": {"label": "Tam anonim", "addr": "full", "extra": CASE + ANON, "drop": []},
    # "ai" plus the EU rules in eu.py (national IDs, VAT ids, EU phones and addresses, non-Turkish names)
    "eu": {"label": "AB / GDPR: yapay zekâ ile paylaşım", "addr": "full", "extra": CASE, "drop": [], "eu": True},
}


def profile_types(profile: str) -> tuple[list[str], str]:
    """(entity types, address rule) for a profile name."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}: use court, ai, anon or eu")
    load()
    from katip_redact.recognizers import ALL_ENTITIES
    p = PROFILES[profile]
    eu_types = []
    if p.get("eu"):
        from .eu import ENTITIES as eu_types
    return [e for e in ALL_ENTITIES if e not in p["drop"]] + p["extra"] + list(eu_types), p["addr"]


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


def sdk():
    """The katip_mask package when exactly SDK_PIN is installed and KATIP_SDK isn't 0, else None."""
    if os.environ.get("KATIP_SDK", "1") == "0" or os.environ.get("KATIP_ENGINE"):
        return None
    try:
        import katip_mask
    except ImportError:
        return None
    return katip_mask if getattr(katip_mask, "__version__", None) == SDK_PIN else None


def source() -> str:
    """Where detection comes from, for katip_status."""
    load()
    return _source


def load():
    """Returns (detector, local_formats) modules: the detector is katip-mask's when the pinned SDK is installed."""
    global _loaded, _source
    if _loaded is None:
        b = _bundle()
        root = b if b.is_dir() else _unpack(b)
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        import local_detect  # noqa: E402
        import local_formats  # noqa: E402
        det, _source = local_detect, "bundled rules"
        if (km := sdk()) is not None:
            from katip_mask._engine import local_detect as det  # noqa: E402
            _source = f"katip-mask {km.__version__}"
        _loaded = (det, local_formats)
    return _loaded


def kind_of(path: Path) -> str:
    k = KINDS.get(path.suffix.lower())
    if not k:
        raise ValueError(f"unsupported file type {path.suffix!r}: use .txt, .docx, .udf, .pdf, .xlsx, .eml, .msg or a photo")
    return k


def read_text(path: Path) -> tuple[str, str, bytes, list[tuple[int, int]], list[str]]:
    """Returns (kind, plain text, original bytes, OCR ranges, OCR readers used).
    Scanned PDF pages and photos are read with local OCR (ocr.py); their character ranges are passed
    to the detector, which is more tolerant there (a misread TC kimlik digit is still masked)."""
    kind = kind_of(path)
    data = path.read_bytes()
    if kind in ("pdf", "image"):
        from . import ocr
        if kind == "image":
            text, reader = ocr.ocr_page(ocr.image_rgb(data))
            return kind, text, data, [(0, len(text))], [reader]
        try:
            import pymupdf
        except ImportError:
            raise ValueError("PDF needs pymupdf (Katip fetches it with uv; or `pip install pymupdf`)") from None
        parts, ranges, readers, pos = [], [], [], 0
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                t = page.get_text()
                if len(t.strip()) < 20:  # no text layer: a scan or a photo saved as PDF
                    t, reader = ocr.ocr_page(ocr.pixmap_rgb(page.get_pixmap(dpi=ocr.DPI)))
                    ranges.append((pos, pos + len(t)))
                    readers.append(reader)
                parts.append(t)
                pos += len(t) + 2
        return kind, "\n\n".join(parts), data, ranges, readers
    _, fmt = load()
    return kind, fmt.extract(kind, data), data, [], []


def detect(text: str, threshold: float = 0.5, entities: list[str] | None = None,
           mask_terms=(), allow_terms=(), ocr_ranges=(), address_detail: str | None = None) -> list[dict]:
    """Rules, plus the on-device Katip Mask model when one is installed (see ner.py)."""
    det, _ = load()
    from . import ner
    model = ner.get()
    extra = [list(x) for x in model.spans(text)] if model else []
    spans = det.detect(text, threshold, entities, list(mask_terms), list(allow_terms), extra,
                       ner.trust() if model else None,
                       ocr_ranges=[list(r) for r in ocr_ranges],
                       address_detail=address_detail or os.environ.get("KATIP_ADDRESS_DETAIL", "street"))
    if entities:  # a profile chose these types: mask all of them
        return spans
    return [s for s in spans if not s.get("flag_only")]


def redact_bytes(kind: str, data: bytes, spans: list[dict], style: str = "label") -> bytes:
    _, fmt = load()
    return fmt.redact(kind, data, json.dumps(spans), style)


def leaked(out_text: str, spans: list[dict]) -> list[str]:
    _, fmt = load()
    return json.loads(fmt.leak_check(out_text, json.dumps(spans)))


def label_name(entity_type: str) -> str:
    load()
    from katip_redact.textutil import tr_upper
    from local_formats import ENTITY_LABELS_TR  # includes the profile types (Dosya No, Tarih, Kurum ...)
    from .eu import LABELS_TR as EU_LABELS
    return tr_upper(ENTITY_LABELS_TR.get(entity_type) or EU_LABELS.get(entity_type, entity_type))
