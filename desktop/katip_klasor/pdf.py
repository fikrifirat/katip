"""True redaction of PDFs with a text layer (PyMuPDF): the text under each box is removed from the file,
not just covered, and the placeholder is printed in the box when it fits."""
from __future__ import annotations

import re

_FOLD = str.maketrans("İŞĞÜÖÇÂÎÛışğüöçâîû", "ISGUOCAIUisguocaiu")  # the base-14 font has no İ or Ş


def text_of(data: bytes) -> str:
    import pymupdf
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        return "\n\n".join(p.get_text() for p in doc)


def _parts(value: str) -> list[str]:
    """A value that wraps onto the next line is searched one line at a time."""
    return [p.strip() for p in re.split(r"\s*\n\s*", value) if len(p.strip()) >= 2]


def _core(r):
    """The middle band of a found word: MuPDF removes every glyph whose box touches the redaction area, and
    line boxes overlap the lines above and below, so the full box would also delete neighbouring text."""
    import pymupdf
    dy, dx = r.height * 0.3, min(0.8, r.width * 0.1)
    return pymupdf.Rect(r.x0 + dx, r.y0 + dy, r.x1 - dx, r.y1 - dy)


def redact(data: bytes, spans: list[dict]) -> bytes:
    import pymupdf
    vals: dict[str, str] = {}
    for s in spans:
        vals.setdefault(s["text"].strip(), s.get("label", ""))
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            boxes = []
            for value, label in sorted(vals.items(), key=lambda kv: -len(kv[0])):
                for i, part in enumerate(_parts(value)):
                    for r in page.search_for(part):
                        page.add_redact_annot(_core(r), fill=False)
                        boxes.append((r, label.translate(_FOLD) if i == 0 else ""))
            if not boxes:
                continue
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
            for r, text in boxes:  # the visible box and placeholder are drawn after the text is gone
                page.draw_rect(r, color=None, fill=(0, 0, 0), overlay=True)
                fs = min(r.height * 0.72, r.width / max(1, 0.55 * len(text))) if text else 0
                if fs >= 4:
                    page.insert_text((r.x0 + max(0.5, (r.width - pymupdf.get_text_length(text, "helv", fs)) / 2),
                                      r.y1 - (r.height - fs) / 2 - fs * 0.18), text, fontname="helv", fontsize=fs,
                                     color=(1, 1, 1), overlay=True)
        doc.set_metadata({})  # author, title and producer can name the client
        doc.del_xml_metadata()
        return doc.tobytes(garbage=4, deflate=True)
