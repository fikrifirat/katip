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
_UP = "A-ZÇĞİIÖŞÜ"
# A notice starts with the registry office heading at the start of a line ("BURSA TİCARET SİCİLİ
# MÜDÜRLÜĞÜ'NDEN"). Body text like "... Ticaret Sicili Müdürlüğünce tescil edilmiştir" must not split.
_OFFICE = re.compile(r"(?m)^(?=\S+(?:[ \t]\S+)?[ \t]+Ticaret[ \t]+Sicil(?:i)?[ \t]+Müdürlüğü(?:'?nden)?(?![\wçğıöşü]))", re.I)
_SICIL = re.compile(r"(?=Ticaret\s+Sicil(?:i)?\s+No\s*:)", re.I)
_LABEL = re.compile(r"(?:Ticaret\s+)?[UÜuü]nvan[ıiIİ]\s*:?", re.I)
_ISSUE = re.compile(r"Sayı\s*:?\s*(\d{4,6}).{0,40}?(\d{1,2}[./]\d{1,2}[./]\d{4})", re.S)
_SIRA = re.compile(r"[İI]lan\s*S[ıi]ra\s*No", re.I)
_FIELD = re.compile(r"[İI]lan\s*S[ıi]ra|Mersis|Sicil\s*(?:/|No)|[UÜ]nvan|Müdürlüğü", re.I)
_CHROME = re.compile(r"^(T\.?\s?C\.?|.*TİCARET SİCİLİ GAZETESİ.*|\(?Devamı.*Sayfada\)?)$", re.I)
_FORMS = re.compile(r"(ŞİRKETİ|ŞTİ\.?|KOOPERATİFİ|A\.Ş\.?|ŞUBESİ|İŞLETMESİ)\s*$")
_NAME = re.compile(r"tsg_(\d{4}-\d{2}-\d{2})_(\d{3,6})_p(\d+)", re.I)


def meta_from_name(name: str) -> dict:
    """Issue, date and gazette page from a saved file name like tsg_2026-11-19_11712_p101.pdf."""
    m = _NAME.search(name)
    return {"date": m.group(1), "issue": m.group(2), "gazette_page": m.group(3)} if m else {}


def title_of(notice: str) -> str:
    """The company name after "Ticaret Unvanı:", on the same line or the lines after it."""
    lines = [ln.strip() for ln in notice.splitlines()]
    for i, ln in enumerate(lines):
        m = _LABEL.search(ln)
        if not m:
            continue
        rest, name = ln[m.end():].strip(), []
        if rest:
            name.append(rest)
        for nxt in lines[i + 1:]:
            if not nxt or (name and _FORMS.search(name[-1])) or len(name) >= 4:
                break
            if sum(c.isupper() for c in nxt) < 0.6 * sum(c.isalpha() for c in nxt):
                break  # body text, not the capitalised name
            name.append(nxt)
        if name:
            return " ".join(name)[:200]
    first = next((ln for ln in lines if ln), "")
    return first[:200]


def _rows(boxes) -> list[str]:
    rows: list[list] = []
    for b in sorted(boxes):
        y, x, h, t = b[0], b[1], b[2], b[-1]
        if rows and abs(rows[-1][0] - y) < max(8.0, 0.5 * h):
            rows[-1][1].append((x, t))
        else:
            rows.append([y, [(x, t)]])
    return [" ".join(t for _, t in sorted(items)) for _, items in rows]


def layout_notices(boxes, width: float) -> list[dict]:
    """Split one scanned page into notices using the layout: anchor on "İlan Sıra No", keep the
    narrow field column apart from the body, and drop the page header and footer.

    ``boxes`` are (y_centre, x_left, height, width, text). Returns [] when the page has no anchor,
    so the caller falls back to the plain text splitter.
    """
    boxes = [b for b in boxes if b[-1].strip() and not _CHROME.match(b[-1].strip())]
    anchors = sorted((b for b in boxes if _SIRA.search(b[-1])), key=lambda b: b[1])
    if not anchors:
        return []
    cols: list[list] = []  # page columns, by the x of their anchors
    for a in anchors:
        if cols and abs(cols[-1][0][1] - a[1]) < 0.15 * width:
            cols[-1].append(a)
        else:
            cols.append([a])
    out = []
    for ci, col in enumerate(cols):
        x0 = min(a[1] for a in col) - 0.03 * width
        x1 = (min(a[1] for a in cols[ci + 1]) - 0.03 * width) if ci + 1 < len(cols) else width + 1
        inside = [b for b in boxes if x0 <= b[1] < x1]
        labels = [b for b in inside if _FIELD.search(b[-1]) and b[1] < x0 + 0.5 * (x1 - x0)]
        edge = max(b[1] + b[3] for b in labels) + 0.01 * width  # right edge of the field column
        col = sorted(col)
        starts = [a[0] - 2.2 * a[2] for a in col]  # the office heading sits a line above the anchor
        for k, a in enumerate(col):
            y0 = starts[k] if k else -1
            y1 = starts[k + 1] if k + 1 < len(col) else float("inf")
            part = [b for b in inside if y0 <= b[0] < y1]
            fields = _rows([b for b in part if b[1] < edge])
            body = _rows([b for b in part if b[1] >= edge])
            ftext = "\n".join(fields)
            title = title_of(ftext)
            name_line = title if title and title not in fields else None
            text = "\n".join([*fields, *([name_line] if name_line else []), *body])
            sira = re.search(r"(\d{3,})", next((f for f in fields if _SIRA.search(f)), "")) 
            out.append({"title": title, "text": text, "sira": sira.group(1) if sira else ""})
    return out


def _ocr_page(page):
    """Text of a scanned page, or a list of notices when the layout is recognised."""
    from ... import ocr  # Kalkan's reader (PaddleOCR or Tesseract); heavy, only when asked

    pix = page.get_pixmap(dpi=200)
    rgb = ocr.pixmap_rgb(pix)
    try:
        notices = layout_notices(ocr.ocr_boxes(rgb), pix.w)
        if notices:
            return notices
    except (ImportError, OSError, RuntimeError):
        pass  # no PaddleOCR here: plain text below
    text, _reader = ocr.ocr_page(rgb)
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
    text = "\n".join(ln for ln in text.splitlines() if not _CHROME.match(ln.strip()))
    splitter = _OFFICE if _OFFICE.search(text) else _SICIL
    parts = [p.strip() for p in splitter.split(text) if p and p.strip()]
    if len(parts) > 1 and not splitter.match(parts[0]):
        parts = parts[1:]  # page header / issue line before the first notice
    return [p for p in parts if len(p) > 40] or ([text.strip()] if text.strip() else [])


def ingest(paths: list[Path], ocr: bool = False) -> list[dict]:
    out = []
    for path in paths:
        digest = hashlib.sha1(path.read_bytes()).hexdigest()[:10]
        meta = meta_from_name(path.name)
        issue, date = meta.get("issue", ""), meta.get("date", "")
        for page_no, content in _pages(path, ocr):
            if isinstance(content, str):
                if not issue:
                    m = _ISSUE.search(content)
                    if m:
                        issue, date = m.groups()
                notices = [{"title": title_of(n), "text": n} for n in split_notices(content)]
            else:
                notices = content
            for k, n in enumerate(notices):
                rec = {"rid": f"gazette:{digest}:{page_no}:{k}", "source": SOURCE, "kind": "notice",
                       "title": n["title"], "names": [n["title"]], "text": n["text"], "issue": issue, "date": date,
                       "url": f"{path}#page={page_no}"}
                if meta.get("gazette_page"):
                    rec["gazette_page"] = meta["gazette_page"]
                if n.get("sira"):
                    rec["ilan_sira_no"] = n["sira"]
                out.append(rec)
    return out
