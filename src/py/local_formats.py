"""Browser-side parsing and masking for txt, UYAP .udf and .docx (stdlib only,
runs in Pyodide). PDF and images are handled in JS with MuPDF/Tesseract.

Mirrors katip_redact/redact.py: same labels, same BLOCK, same UDF same-length
rule. The .docx path edits the XML text nodes in place (no re-serialisation,
so Word never sees a rewritten namespace) and also masks tracked-change
deletions (w:delText) and comment text, which python-docx does not expose.
"""
from __future__ import annotations

import html
import io
import json
import re
import zipfile
from collections import defaultdict

from katip_redact.recognizers import ENTITY_LABELS_TR
from katip_redact.textutil import tr_upper

import local_detect

BLOCK = "█"
UDF_CDATA = re.compile(r"(<content>\s*<!\[CDATA\[)(.*?)(\]\]>\s*</content>)", re.S)
DOCX_PARTS = re.compile(r"word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$")
TOKEN = re.compile(r"<w:(t|delText)\b([^>]*?)(?:/>|>(.*?)</w:\1>)|</w:p>|<w:tab\b[^>]*/>|<w:br\b[^>]*/>", re.S)


def _label(sp, counters, seen):
    key = (sp["entity_type"], re.sub(r"\s+", " ", sp["text"].strip()).casefold())
    if key not in seen:
        counters[sp["entity_type"]] += 1
        seen[key] = f"[{tr_upper(ENTITY_LABELS_TR.get(sp['entity_type'], sp['entity_type']))}-{counters[sp['entity_type']]}]"
    return seen[key]


def mask_text(text, spans, style="box"):
    counters, seen = defaultdict(int), {}
    out, pos = [], 0
    for sp in sorted(spans, key=lambda s: s["start"]):
        if sp["start"] < pos:
            continue
        out.append(text[pos:sp["start"]])
        out.append(_label(sp, counters, seen) if style == "label" else BLOCK * 6)
        pos = sp["end"]
    out.append(text[pos:])
    return "".join(out)


# ------------------------------------------------------------------ UDF
def udf_text(data: bytes):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("content.xml").decode("utf-8")
    m = UDF_CDATA.search(xml)
    if not m:
        raise ValueError("UDF content.xml has no <content> CDATA block")
    return xml, m.group(2)


def udf_redact(data: bytes, spans) -> bytes:
    xml, text = udf_text(data)
    chars = list(text)
    for sp in spans:
        for k in range(sp["start"], sp["end"]):
            if not chars[k].isspace():
                chars[k] = BLOCK  # same length: UDF styling is offset based
    new_text = "".join(chars).replace("]]>", "]]&gt;")
    xml = UDF_CDATA.sub(lambda m: m.group(1) + new_text + m.group(3), xml, count=1)
    return _rezip(data, {"content.xml": xml.encode("utf-8")})


# ------------------------------------------------------------------ DOCX
def _rezip(data, replace):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, replace.get(item.filename, zin.read(item.filename)))
    return out.getvalue()


def _docx_scan(data):
    """-> text, list of parts [(name, xml, [(tok_start, tok_end, attrs, text_start, text)])]"""
    parts, buf, pos = [], [], 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted((n for n in z.namelist() if DOCX_PARTS.match(n)), key=lambda n: (n != "word/document.xml", n))
        for name in names:
            xml = z.read(name).decode("utf-8")
            nodes = []
            for m in TOKEN.finditer(xml):
                tok = m.group(0)
                if tok == "</w:p>":
                    buf.append("\n"); pos += 1
                elif tok.startswith(("<w:tab", "<w:br")):
                    buf.append(" " if tok.startswith("<w:tab") else "\n"); pos += 1
                else:
                    t = html.unescape(m.group(3) or "")
                    nodes.append((m.start(), m.end(), m.group(1), m.group(2), pos, t))
                    buf.append(t); pos += len(t)
            parts.append((name, xml, nodes))
    return "".join(buf), parts


def docx_text(data: bytes) -> str:
    return _docx_scan(data)[0]


def docx_redact(data: bytes, spans, style="box") -> bytes:
    text, parts = _docx_scan(data)
    counters, seen = defaultdict(int), {}
    rep = {}  # char offset -> replacement ("" = drop)
    for sp in sorted(spans, key=lambda s: s["start"]):
        for k in range(sp["start"], sp["end"]):
            rep[k] = ""
        rep[sp["start"]] = _label(sp, counters, seen) if style == "label" else BLOCK * 6
    replace = {}
    for name, xml, nodes in parts:
        out, last, changed = [], 0, False
        for a, b, tag, attrs, tstart, t in nodes:
            if not any(k in rep for k in range(tstart, tstart + len(t))):
                continue
            new = "".join(rep.get(tstart + i, c) for i, c in enumerate(t))
            if 'xml:space="preserve"' not in attrs:
                attrs = attrs + ' xml:space="preserve"'
            out.append(xml[last:a]); out.append(f"<w:{tag}{attrs}>{html.escape(new, quote=False)}</w:{tag}>")
            last, changed = b, True
        if changed:
            out.append(xml[last:])
            xml = "".join(out)
        # who wrote / changed / commented is personal data too
        xml2 = re.sub(r'(w:author|w:initials)="[^"]*"', r'\1=""', xml)
        if changed or xml2 != xml:
            replace[name] = xml2.encode("utf-8")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if "docProps/core.xml" in z.namelist():
            core = z.read("docProps/core.xml").decode("utf-8")
            for tag in ("dc:creator", "cp:lastModifiedBy", "dc:title", "dc:subject", "dc:description",
                        "cp:keywords", "cp:category"):
                core = re.sub(rf"<{tag}>.*?</{tag}>", f"<{tag}></{tag}>", core, flags=re.S)
            replace["docProps/core.xml"] = core.encode("utf-8")
    return _rezip(data, replace)


# ------------------------------------------------------------------ entry points for JS
def extract(kind, data):
    data = bytes(data)
    if kind == "udf":
        return udf_text(data)[1]
    if kind == "docx":
        return docx_text(data)
    return data.decode("utf-8", errors="replace")


def redact(kind, data, spans_json, style="box"):
    data, spans = bytes(data), json.loads(spans_json)
    if kind == "udf":
        return udf_redact(data, spans)
    if kind == "docx":
        return docx_redact(data, spans, style)
    return mask_text(data.decode("utf-8", errors="replace"), spans, style).encode("utf-8")


def squash(s):
    return re.sub(r"\s+", "", s).casefold()


def leak_check(out_text, spans_json):
    out = squash(out_text)
    return json.dumps([s["id"] for s in json.loads(spans_json)
                       if len(squash(s["text"])) >= 4 and squash(s["text"]) in out])
