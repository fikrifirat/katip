"""Browser-side parsing and masking for txt, UYAP .udf, .docx, .xlsx and e-mail (.eml, Outlook .msg)
(stdlib only, runs in Pyodide). PDF and images are handled in JS with MuPDF/Tesseract.

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

# labels for the browser-only case-detail types (local_detect.CASE_TYPES)
ENTITY_LABELS_TR = {**ENTITY_LABELS_TR, "CASE_NO": "Dosya No", "BAR_NO": "Sicil No", "DATE": "Tarih", "PLACE": "Yer", "INSTITUTION": "Kurum"}
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
    return _mask_range(text, spans, 0, len(text), style, defaultdict(int), {})


def _mask_range(text, spans, a, b, style, counters, seen):
    """text[a:b] with the spans inside it replaced; a span crossing a or b is cut there (both sides masked)."""
    out, pos = [], a
    for sp in sorted(spans, key=lambda s: s["start"]):
        s, e = max(sp["start"], a), min(sp["end"], b)
        if e <= s or s < pos:
            continue
        out.append(text[pos:s])
        out.append(_label(sp, counters, seen) if style == "label" else BLOCK * 6)
        pos = e
    out.append(text[pos:b])
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
    # sign.sgn is the e-imza signature (PKCS#7): it carries the signer's certificate (name, title, city, serial
    # number) and no longer matches the masked text, so it is left out of the masked copy
    return _rezip(data, {"content.xml": xml.encode("utf-8")}, drop=lambda n: n.lower().endswith(".sgn"))


# ------------------------------------------------------------------ DOCX
def _rezip(data, replace, drop=lambda name: False):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if drop(item.filename):
                continue
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
            replace["docProps/core.xml"] = _clear_core(z.read("docProps/core.xml").decode("utf-8")).encode("utf-8")
    return _rezip(data, replace)


def _clear_core(core):
    """Author, last editor, title and the like in docProps/core.xml are personal data too. Some writers
    put a namespace declaration on each element (<dc:creator xmlns:dc="...">), so attributes are allowed."""
    for tag in ("dc:creator", "cp:lastModifiedBy", "dc:title", "dc:subject", "dc:description",
                "cp:keywords", "cp:category"):
        core = re.sub(rf"<{tag}(\s[^>]*)?>.*?</{tag}>", lambda m: f"<{tag}{m.group(1) or ''}></{tag}>", core, flags=re.S)
    return core


# ------------------------------------------------------------------ E-MAIL (.eml, Outlook .msg)
# A message becomes a few labelled fields plus the body. The masked copy is a new, plain-text .eml built from
# the masked fields only: every other header (Received, Message-ID, Reply-To, X-...) and the HTML part are
# left out, and attachments are not carried over (their names are listed, masked, so each can be masked on its own).
MAIL_FIELDS = (("from", "Kimden"), ("to", "Kime"), ("cc", "Bilgi"), ("date", "Tarih"), ("subject", "Konu"))
MAIL_NOTE = "Ekler bu maskeli kopyaya alınmadı; her eki ayrıca maskeleyin."


def _html_to_text(h):
    from html.parser import HTMLParser  # imported here: only an HTML-only mail needs it

    class _HtmlText(HTMLParser):
        BREAK = {"br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "blockquote"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.out, self.skip = [], 0

        def handle_starttag(self, tag, attrs):
            if tag in ("style", "script", "head"):
                self.skip += 1
            elif tag in self.BREAK:
                self.out.append("\n")
            elif tag == "td":
                self.out.append("\t")

        def handle_endtag(self, tag):
            if tag in ("style", "script", "head"):
                self.skip = max(0, self.skip - 1)
            elif tag in self.BREAK:
                self.out.append("\n")

        def handle_data(self, d):
            if not self.skip:
                self.out.append(d)

    p = _HtmlText()
    p.feed(h)
    p.close()
    t = re.sub(r"[ \t\r\f\v\xa0]+\n", "\n", "".join(p.out).replace("\xa0", " "))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _eml_header(m, key):
    """Decoded header text. Read raw and decoded word by word: some mailers wrap a whole "Name <address>" in one
    encoded word, which a structured address parser can mangle."""
    from email.header import decode_header, make_header
    v = m.get(key)
    if v is None:
        return ""
    try:
        return str(make_header(decode_header(str(v)))).strip()
    except Exception:  # noqa: BLE001 - a broken header is still shown as it is
        return str(v).strip()


def _eml_part_text(part):
    raw = part.get_payload(decode=True) or b""
    cs = part.get_content_charset() or "utf-8"
    try:
        return raw.decode(cs, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _eml_fields(data):
    import email
    from email import policy
    m = email.message_from_bytes(data, policy=policy.compat32)
    f = {key: _eml_header(m, key) for key, _ in MAIL_FIELDS}
    plain, htm, att = None, None, []

    def walk(part, top):
        nonlocal plain, htm
        ctype = part.get_content_type()
        name = part.get_filename()
        if name:
            from email.header import decode_header, make_header
            try:
                name = str(make_header(decode_header(name)))
            except Exception:  # noqa: BLE001
                pass
        if not top and (ctype == "message/rfc822" or name or part.get("Content-Disposition", "").lower().startswith("attachment")):
            att.append(name or ctype)  # a forwarded mail or a file: listed, not read
            return
        if part.is_multipart():
            for sub in part.get_payload():
                walk(sub, False)
        elif ctype == "text/plain" and plain is None:
            plain = _eml_part_text(part)
        elif ctype == "text/html" and htm is None:
            htm = _eml_part_text(part)

    walk(m, True)
    f["body"] = (plain if plain is not None else _html_to_text(htm or "")).replace("\r\n", "\n").strip()
    f["att"] = att
    return f


# Outlook .msg is an OLE compound file (MS-CFB) holding MAPI properties (MS-OXMSG); read with the stdlib only
def _cfb_streams(data):
    """-> {path: bytes}, path like "__substg1.0_0037001F" or "__recip_version1.0_#00000000/__substg1.0_3001001F"."""
    import struct
    if data[:8] != bytes.fromhex("D0CF11E0A1B11AE1"):
        raise ValueError("not an Outlook .msg file")
    ssz = 1 << struct.unpack_from("<H", data, 30)[0]
    msz = 1 << struct.unpack_from("<H", data, 32)[0]
    nfat, dir0, mini_cut, mfat0, nmfat, difat0, ndifat = struct.unpack_from("<I I 4x I I I I I", data, 44)
    sec = lambda i: data[(i + 1) * ssz:(i + 2) * ssz]
    fat_secs = list(struct.unpack_from("<109I", data, 76))
    d = difat0
    for _ in range(ndifat):
        if d >= 0xFFFFFFFA:
            break
        ints = struct.unpack("<%dI" % (ssz // 4), sec(d))
        fat_secs += ints[:-1]
        d = ints[-1]
    fat = []
    for s in fat_secs[:nfat]:
        fat += struct.unpack("<%dI" % (ssz // 4), sec(s))

    def chain(start, table, guard):
        out, i = [], start
        while i < 0xFFFFFFFA and len(out) < guard:
            out.append(i)
            i = table[i]
        return out

    guard = len(data) // 64 + 16
    dirs = b"".join(sec(i) for i in chain(dir0, fat, guard))
    ents = []
    for k in range(len(dirs) // 128):
        e = dirs[k * 128:(k + 1) * 128]
        nlen = struct.unpack_from("<H", e, 64)[0]
        name = e[:max(0, nlen - 2)].decode("utf-16-le", "replace")
        typ = e[66]
        left, right, child = struct.unpack_from("<III", e, 68)
        start, size = struct.unpack_from("<IQ", e, 116)
        ents.append((name, typ, left, right, child, start, size if ssz == 4096 else size & 0xFFFFFFFF))
    root = ents[0]
    big = lambda st, sz: b"".join(sec(i) for i in chain(st, fat, guard))[:sz]
    ministream = big(root[5], root[6])
    minifat = []
    if mfat0 < 0xFFFFFFFA:
        for s in chain(mfat0, fat, guard):
            minifat += struct.unpack("<%dI" % (ssz // 4), sec(s))
    mini = lambda st, sz: b"".join(ministream[i * msz:(i + 1) * msz] for i in chain(st, minifat, guard))[:sz]
    out, seen = {}, set()

    def walk(idx, prefix):
        stack = [idx]
        while stack:
            i = stack.pop()
            if i >= len(ents) or i in seen:
                continue
            seen.add(i)
            name, typ, left, right, child, st, sz = ents[i]
            stack += [left, right]
            path = prefix + name
            if typ == 2:
                out[path] = mini(st, sz) if sz < mini_cut else big(st, sz)
            elif typ == 1 and not name.startswith("__substg1.0_3701"):  # an attached .msg: not read
                walk(child, path + "/")

    walk(root[4], "")
    return out


def _msg_fields(data):
    st = _cfb_streams(data)

    def prop(pid, base=""):
        for t in ("001F", "001E"):
            v = st.get(f"{base}__substg1.0_{pid}{t}")
            if v is not None:
                return (v.decode("utf-16-le", "replace") if t == "001F" else v.decode("cp1254", "replace")).rstrip("\x00")
        return ""

    f = {}
    sender = prop("0C1A") or prop("0042")
    addr = prop("5D01") or prop("0C1F") or prop("0065")
    f["from"] = f"{sender} <{addr}>" if sender and addr and "@" in addr else (sender or addr)
    to, cc = [], []
    for base in sorted({p.split("/")[0] for p in st if p.startswith("__recip_version1.0_")}):
        b = base + "/"
        name, a = prop("3001", b), prop("39FE", b) or prop("3003", b)
        who = f"{name} <{a}>" if name and a and "@" in a and a not in name else (name or a)
        rtype = st.get(b + "__properties_version1.0", b"")
        kind = 1
        for k in range(8, len(rtype) - 15, 16):  # fixed-size property entries: PR_RECIPIENT_TYPE 0x0C150003
            if rtype[k:k + 4] == bytes.fromhex("0300150C"):
                kind = int.from_bytes(rtype[k + 8:k + 12], "little")
        (cc if kind == 2 else to).append(who)
    f["to"] = ", ".join(to) or prop("0E04")
    f["cc"] = ", ".join(cc) or prop("0E03")
    f["date"] = ""
    f["subject"] = prop("0037")
    body = prop("1000")
    if not body.strip():
        h = st.get("__substg1.0_10130102")
        body = _html_to_text(h.decode("utf-8", "replace")) if h else ""
    f["body"] = body.replace("\r\n", "\n").strip()
    f["att"] = []
    for base in sorted({p.split("/")[0] for p in st if p.startswith("__attach_version1.0_")}):
        f["att"].append(prop("3707", base + "/") or prop("3704", base + "/") or "ek")
    return f


def _mail_layout(f):
    """-> text, [(field, start, end)]"""
    buf, segs, pos = [], [], 0

    def add(s, key=None):
        nonlocal pos
        if key:
            segs.append((key, pos, pos + len(s)))
        buf.append(s)
        pos += len(s)

    for key, label in MAIL_FIELDS:
        if f.get(key):
            add(label + ": "); add(f[key], key); add("\n")
    add("\n"); add(f["body"], "body"); add("\n")
    for i, a in enumerate(f["att"]):
        add("\nEkler: " if i == 0 else ", "); add(a, f"att{i}")
    if f["att"]:
        add("\n")
    return "".join(buf), segs


def _mail_fields(kind, data):
    return _msg_fields(data) if kind == "msg" else _eml_fields(data)


def mail_text(kind, data):
    return _mail_layout(_mail_fields(kind, data))[0]


def mail_redact(kind, data, spans, style="box", watermark=""):
    from email.message import EmailMessage
    from email.policy import SMTP
    f = _mail_fields(kind, data)
    text, segs = _mail_layout(f)
    counters, seen = defaultdict(int), {}
    m = {k: _mask_range(text, spans, a, b, style, counters, seen) for k, a, b in segs}
    msg = EmailMessage(policy=SMTP.clone(max_line_length=998))
    for key, _ in MAIL_FIELDS:
        if m.get(key):
            msg[key.capitalize() if key != "cc" else "Cc"] = re.sub(r"[\r\n]+", " ", m[key])
    body = m.get("body", "")
    att = [m[k] for k, _, _ in segs if k.startswith("att")]
    if att:
        body += "\n\nEkler: " + ", ".join(att) + "\n" + MAIL_NOTE
    if watermark:
        body = body.rstrip("\n") + "\n\n" + watermark
    msg.set_content(body + "\n", charset="utf-8", cte="8bit")
    return msg.as_bytes()


# ------------------------------------------------------------------ EXCEL (.xlsx)
# Text is laid out one sheet after another ("## Sayfa: name", then one row per line, cells split by tabs),
# then cell notes. Masked cells become inline text (their formula is dropped); a masked shared string is
# rewritten in the shared-string table, so every cell that uses it is masked. A value masked anywhere is then
# masked in every other cell and in the rest of the workbook too (pivot caches, charts, defined names), since
# those keep their own copies of cell values. Note and comment authors and the document properties are cleared.
XL_CELL = re.compile(r"<c\b([^>]*?)(?:/>|>(.*?)</c>)", re.S)
XL_T = re.compile(r"<t\b[^>]*?(?:/>|>(.*?)</t>)", re.S)
XL_ATTR = lambda attrs, k: (re.search(rf'\b{k}="([^"]*)"', attrs) or [None, None])[1]
XL_SKIP = re.compile(r"(^\[Content_Types\]|styles\.xml$|theme/|\.rels$|calcChain\.xml$)")


def _xl_runs(xml):
    xml = re.sub(r"<rPh\b.*?</rPh>", "", xml, flags=re.S)  # phonetic hints, not cell text
    return "".join(html.unescape(m.group(1) or "") for m in XL_T.finditer(xml))


def _xl_target(base, target):
    if target.startswith("/"):
        return target[1:]
    parts = base.split("/")[:-1] + target.split("/")
    out = []
    for p in parts:
        if p == "..":
            out and out.pop()
        elif p and p != ".":
            out.append(p)
    return "/".join(out)


def _xlsx_scan(data):
    """-> text, sst [(text, si_start, si_end)], cells [(part, a, b, attrs, tstart, text, sst_index)],
    sheets [(name, tstart)], notes [(part, a, b, tstart, text, threaded)]"""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    rd = lambda n: z.read(n).decode("utf-8") if n in names else ""
    sst = []
    for m in re.finditer(r"<si\b[^>]*>(.*?)</si>|<si\b[^>]*/>", rd("xl/sharedStrings.xml"), re.S):
        sst.append((_xl_runs(m.group(1) or ""), m.start(), m.end()))
    rels = {m.group(1): m.group(2) for m in re.finditer(
        r'<Relationship\b[^>]*?Id="([^"]+)"[^>]*?Target="([^"]+)"', rd("xl/_rels/workbook.xml.rels"))}
    rels.update({m.group(2): m.group(1) for m in re.finditer(
        r'<Relationship\b[^>]*?Target="([^"]+)"[^>]*?Id="([^"]+)"', rd("xl/_rels/workbook.xml.rels"))})
    buf, pos, cells, sheets, notes = [], 0, [], [], []

    def add(s):
        nonlocal pos
        buf.append(s)
        pos += len(s)

    for m in re.finditer(r"<sheet\b([^>]*?)/?>", rd("xl/workbook.xml")):
        name = html.unescape(XL_ATTR(m.group(1), "name") or "")
        rid = XL_ATTR(m.group(1), "r:id")
        part = _xl_target("xl/workbook.xml", rels.get(rid, ""))
        if part not in names:
            continue
        if buf:
            add("\n")
        add("## Sayfa: ")
        sheets.append((name, pos)); add(name); add("\n")
        xml = rd(part)
        rows = []
        for row in re.finditer(r"<row\b[^>]*?(?:/>|>(.*?)</row>)", xml, re.S):
            body, off, vals = row.group(1) or "", row.start(1), []
            for c in XL_CELL.finditer(body):
                attrs, inner = c.group(1), c.group(2) or ""
                t, idx = XL_ATTR(attrs, "t"), None
                if t == "s":
                    v = re.search(r"<v>(.*?)</v>", inner)
                    if not v:
                        continue
                    idx = int(v.group(1))
                    val = sst[idx][0] if idx < len(sst) else ""
                elif t == "inlineStr":
                    val = _xl_runs(inner)
                else:
                    v = re.search(r"<v>(.*?)</v>", inner, re.S)
                    val = html.unescape(v.group(1)) if v else ""
                if val == "":
                    continue
                col = re.match(r"[A-Z]+", XL_ATTR(attrs, "r") or "")
                vals.append((col.group(0) if col else None, off + c.start(), off + c.end(), attrs, val, idx, t))
            if vals:
                rows.append(vals)
        # A first row of plain words is a header: the rows under it are laid out as records, one
        # "Header: value" line per cell, the way a form reads ("Doğum tarihi: 05.11.1959"), so a value
        # alone in its cell gets the context the detector needs. Without a header: one line per row, tab-separated.
        head = {}
        if len(rows) > 1 and len(rows[0]) > 1 and all(t == "s" or t == "inlineStr" or t == "str" for *_, t in rows[0]) \
                and all(not re.search(r"\d{3}", v[4]) and len(v[4]) <= 40 for v in rows[0]):
            head = {v[0]: v[4] for v in rows[0] if v[0]}
        for i, vals in enumerate(rows):
            record = bool(head) and i > 0
            if record:
                add("\n")
            for j, (col, a0, b0, attrs, val, idx, _) in enumerate(vals):
                if record and head.get(col):
                    add(head[col] + ": ")
                elif j:
                    add("\t")
                cells.append((part, a0, b0, attrs, pos, val, idx))
                add(val)
                if record:
                    add("\n")
            if not record:
                add("\n")
    nparts = sorted(n for n in names if re.match(r"xl/(comments\d*|comments/[^/]+|threadedComments/[^/]+)\.xml$", n))
    for part in nparts:
        threaded = "threadedComments" in part
        for m in re.finditer(r"<(comment|threadedComment)\b([^>]*?)>(.*?)</\1>", rd(part), re.S):
            tm = re.search(r"<text\b[^>]*>(.*?)</text>", m.group(3), re.S)
            if not tm:
                continue
            val = html.unescape(tm.group(1)) if threaded else _xl_runs(tm.group(1))
            if not val.strip():
                continue
            if not notes:
                add("\n## Notlar\n")
            add((XL_ATTR(m.group(2), "ref") or "") + ": ")
            notes.append((part, m.start(3) + tm.start(), m.start(3) + tm.end(), pos, val, threaded))
            add(val); add("\n")
    return "".join(buf), sst, cells, sheets, notes


def xlsx_text(data):
    return _xlsx_scan(data)[0]


def _xl_esc(s):
    return html.escape(s, quote=False)


def _xl_sheet_name(s):
    s = re.sub(r"[\[\]:*?/\\]", "", s).strip("'") or "Sayfa"
    return s[:31]


def xlsx_redact(data, spans, style="box"):
    text, sst, cells, sheets, notes = _xlsx_scan(data)
    counters, seen = defaultdict(int), {}
    spans = sorted(spans, key=lambda s: s["start"])
    # values masked somewhere are masked everywhere (a name in a heading is the same name in a list)
    vals = sorted({s["text"].strip() for s in spans if len(squash(s["text"])) >= 4}, key=len, reverse=True)
    lab = {}
    for s in spans:
        lab.setdefault(s["text"].strip(), s)
    rx = re.compile("|".join(r"(?<![\w])" + re.escape(v) + r"(?![\w])" for v in vals)) if vals else None

    def mask(tstart, val):
        new = _mask_range(text, spans, tstart, tstart + len(val), style, counters, seen)
        if rx:
            new = rx.sub(lambda m: _label(lab[m.group(0)], counters, seen) if style == "label" else BLOCK * 6, new)
        return new

    edits = defaultdict(list)  # part -> [(a, b, new xml)]
    sst_new = {}
    for part, a, b, attrs, tstart, val, idx in cells:
        new = mask(tstart, val)
        if new == val:
            continue
        if idx is not None:
            sst_new.setdefault(idx, new)
            continue
        attrs2 = re.sub(r'\s+t="[^"]*"', "", attrs)
        edits[part].append((a, b, f'<c{attrs2} t="inlineStr"><is><t xml:space="preserve">{_xl_esc(new)}</t></is></c>'))
    if sst_new:
        for idx, new in sst_new.items():
            _, a, b = sst[idx]
            edits["xl/sharedStrings.xml"].append((a, b, f'<si><t xml:space="preserve">{_xl_esc(new)}</t></si>'))
    for part, a, b, tstart, val, threaded in notes:
        new = mask(tstart, val)
        if new != val:
            inner = _xl_esc(new) if threaded else f'<t xml:space="preserve">{_xl_esc(new)}</t>'
            edits[part].append((a, b, f"<text>{inner}</text>"))
    renames = {}
    for name, tstart in sheets:
        new = mask(tstart, name)
        if new != name:
            new = _xl_sheet_name(new.replace("[", "").replace("]", ""))
            while new in renames.values() or new in [n for n, _ in sheets if n != name]:
                new = (new[:28] + "-" + str(len(renames) + 2))[:31]
            renames[name] = new
    z = zipfile.ZipFile(io.BytesIO(data))
    replace = {}
    for part in z.namelist():
        if not part.endswith((".xml", ".vml")) or XL_SKIP.search(part):
            continue
        xml = z.read(part).decode("utf-8", errors="replace")
        orig = xml
        for a, b, new in sorted(edits.get(part, []), reverse=True):
            xml = xml[:a] + new + xml[b:]
        for old, new in renames.items():
            q = _xl_esc(old).replace('"', "&quot;")
            xml = xml.replace(f'name="{q}"', f'name="{_xl_esc(new)}"')
            xml = xml.replace(f"<vt:lpstr>{_xl_esc(old)}</vt:lpstr>", f"<vt:lpstr>{_xl_esc(new)}</vt:lpstr>")

        def formula(m):  # formulas and defined names: sheet names and values written out in them
            f = html.unescape(m.group(2))
            for old, new in renames.items():
                f = f.replace(f"'{old.replace(chr(39), chr(39) * 2)}'!", f"'{new}'!").replace(f"{old}!", f"'{new}'!")
            if rx:
                f = rx.sub(lambda v: _label(lab[v.group(0)], counters, seen) if style == "label" else BLOCK * 6, f)
            return m.group(1) + _xl_esc(f) + m.group(3)

        xml = re.sub(r"(<(?:f|definedName)\b[^>]*>)(.*?)(</(?:f|definedName)>)", formula, xml, flags=re.S)
        if rx and not part.startswith("xl/worksheets/") and part != "xl/sharedStrings.xml":
            # copies of values outside the cells: pivot caches (<s v="..."/>), chart caches, text boxes, names
            erx = re.compile("|".join(r"(?<![\w])" + re.escape(_xl_esc(v).replace('"', "&quot;")) + r"(?![\w])"
                                      for v in vals))
            unesc = {_xl_esc(v).replace('"', "&quot;"): v for v in vals}
            xml = erx.sub(lambda m: _xl_esc(_label(lab[unesc[m.group(0)]], counters, seen)
                                            if style == "label" else BLOCK * 6), xml)
        if part.startswith("xl/comments"):
            xml = re.sub(r"<author>.*?</author>", "<author></author>", xml, flags=re.S)
        if part.startswith("xl/persons/"):
            xml = re.sub(r'(displayName|userId)="[^"]*"', r'\1=""', xml)
        if part == "docProps/core.xml":
            xml = _clear_core(xml)
        if part == "docProps/app.xml":
            xml = re.sub(r"<(Company|Manager)>.*?</\1>", r"<\1></\1>", xml, flags=re.S)
        if xml != orig:
            replace[part] = xml.encode("utf-8")
    return _rezip(data, replace)


def leak_text(kind, data):
    """Everything readable in an output file, for the leak check: for .xlsx also the text and values kept
    outside the cells (pivot caches, charts, names, properties)."""
    data = bytes(data)
    if kind != "xlsx":
        return extract(kind, data)
    parts = [xlsx_text(data)]
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if n.endswith((".xml", ".vml")) and not XL_SKIP.search(n):
                x = z.read(n).decode("utf-8", errors="replace")
                parts.append(html.unescape(" ".join(re.findall(r">([^<]+)<", x) + re.findall(r'="([^"]*)"', x))))
    return "\n".join(parts)


# ------------------------------------------------------------------ entry points for JS
def extract(kind, data):
    data = bytes(data)
    if kind in ("eml", "msg"):
        return mail_text(kind, data)
    if kind == "xlsx":
        return xlsx_text(data)
    if kind == "udf":
        return udf_text(data)[1]
    if kind == "docx":
        return docx_text(data)
    return data.decode("utf-8", errors="replace")


def _docx_watermark(data: bytes, mark: str) -> bytes:
    """Append one small grey paragraph at the end of the body (before the final sectPr)."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    para = ('<w:p><w:r><w:rPr><w:color w:val="8A8A8A"/><w:sz w:val="14"/></w:rPr>'
            f'<w:t xml:space="preserve">{html.escape(mark, quote=False)}</w:t></w:r></w:p>')
    k = xml.rfind("<w:sectPr")
    if k < 0 or k < xml.rfind("</w:p>"):
        k = xml.rfind("</w:body>")
    if k < 0:
        return data
    return _rezip(data, {"word/document.xml": (xml[:k] + para + xml[k:]).encode("utf-8")})


def redact(kind, data, spans_json, style="box", watermark=""):
    data, spans = bytes(data), json.loads(spans_json)
    if kind == "udf":
        return udf_redact(data, spans)  # UYAP files stay byte-compatible: no watermark
    if kind in ("eml", "msg"):  # an Outlook .msg comes back as a masked .eml
        return mail_redact(kind, data, spans, style, watermark)
    if kind == "xlsx":
        return xlsx_redact(data, spans, style)
    if kind == "docx":
        out = docx_redact(data, spans, style)
        return _docx_watermark(out, watermark) if watermark else out
    text = mask_text(data.decode("utf-8", errors="replace"), spans, style)
    if watermark:
        text = text.rstrip("\n") + "\n\n" + watermark + "\n"
    return text.encode("utf-8")


def squash(s):
    return re.sub(r"\s+", "", s).casefold()


def leak_check(out_text, spans_json):
    out = squash(out_text)
    return json.dumps([s["id"] for s in json.loads(spans_json)
                       if len(squash(s["text"])) >= 4 and squash(s["text"]) in out])
