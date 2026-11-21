"""Türkiye Ticaret Sicili Gazetesi (TOBB): company registrations, capital changes, board
changes, liquidations, mergers.

Status on 21 Nov 2026: www.ticaretsicil.gov.tr closes the connection from our cloud machine
(empty reply after the TLS handshake), so nothing is fetched automatically. The search
on the site is, as far as we know, behind a captcha, and we do not automate captchas.

What works now: the lawyer (or a scheduled job on a Turkish connection) saves gazette issue
PDFs, and ``ingest`` reads them on this computer. Text PDFs are read directly; pages with no
text layer are OCR'd with Katip's own reader (``--ocr``, PaddleOCR or Tesseract), the same
one Kalkan uses. Each notice becomes one searchable document with file and page.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

SOURCE = "gazette"
# A new notice usually starts with the registry office line or the "Ticaret Sicil No" field.
_OFFICE = re.compile(r"(?=\b\w+(?:\s\w+)?\s+Ticaret\s+Sicil(?:i)?\s+Müdürlüğü)", re.I)
_SICIL = re.compile(r"(?=Ticaret\s+Sicil(?:i)?\s+No\s*:)", re.I)
_TITLE = re.compile(r"(?:Ticaret Unvanı|Unvanı|ÜNVANI)\s*:?\s*(.+)")
_ISSUE = re.compile(r"Sayı\s*:?\s*(\d{4,6}).{0,40}?(\d{1,2}[./]\d{1,2}[./]\d{4})", re.S)


def _ocr_page(page) -> str:
    root = Path(__file__).resolve().parents[3] / "connector"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from katip_kalkan import ocr  # noqa: E402  (heavy; only when asked)

    pix = page.get_pixmap(dpi=200)
    text, _reader = ocr.ocr_page(ocr.pixmap_rgb(pix))
    return text


def _pages(path: Path, use_ocr: bool):
    try:
        import fitz  # PyMuPDF, already a Katip dependency

        with fitz.open(path) as doc:
            for i, page in enumerate(doc):
                t = page.get_text()
                if len(t.strip()) < 40 and use_ocr:
                    t = _ocr_page(page)
                yield i + 1, t
    except ImportError:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                yield i + 1, page.extract_text() or ""


def split_notices(text: str) -> list[str]:
    splitter = _OFFICE if _OFFICE.search(text) else _SICIL
    parts = [p.strip() for p in splitter.split(text) if p and p.strip()]
    if len(parts) > 1 and not splitter.match(parts[0]):
        parts = parts[1:]  # page header / issue line before the first notice
    return [p for p in parts if len(p) > 40] or ([text.strip()] if text.strip() else [])


def ingest(paths: list[Path], ocr: bool = False) -> list[dict]:
    out = []
    for path in paths:
        digest = hashlib.sha1(path.read_bytes()).hexdigest()[:10]
        issue = date = ""
        for page_no, text in _pages(path, ocr):
            if not issue:
                m = _ISSUE.search(text)
                if m:
                    issue, date = m.groups()
            for k, notice in enumerate(split_notices(text)):
                m = _TITLE.search(notice)
                title = (m.group(1).strip() if m else notice.splitlines()[0])[:200]
                out.append({"rid": f"gazette:{digest}:{page_no}:{k}", "source": SOURCE, "kind": "notice",
                            "title": title, "names": [title], "text": notice, "issue": issue, "date": date,
                            "url": f"{path}#page={page_no}"})
    return out
