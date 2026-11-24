"""Synthetic e-mail (.eml, Outlook .msg) and Excel files for Katip's demo samples and tests.

Stdlib only, except the .xlsx writer, which needs openpyxl. Nothing here reads real documents: the
inputs are the demo's synthetic samples (docs/samples) and made-up values.
"""
from __future__ import annotations

import base64
import re
import struct
from email import encoders
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

# ---------------------------------------------------------------- .msg (MS-CFB + MS-OXMSG, minimal writer)
def cfb(streams):
    """streams: {path: bytes} with '/' for storages. Version 3 (512-byte sectors), mini stream below 4096 bytes."""
    SS, MS, CUT = 512, 64, 4096
    FREE, END, FATSEC = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD
    tree = {}
    for path, data in streams.items():
        node = tree
        parts = path.split("/")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = data
    ents = []  # [name, type, children(list of idx), data]

    def add(name, node):
        idx = len(ents)
        ents.append([name, 1 if isinstance(node, dict) else 2, [], None if isinstance(node, dict) else node])
        if isinstance(node, dict):
            for k in sorted(node):
                ents[idx][2].append(add(k, node[k]))
        return idx

    ents.append(["Root Entry", 5, [], None])
    for k in sorted(tree):
        ents[0][2].append(add(k, tree[k]))
    mini, minifat, big = bytearray(), [], []  # big: list of (entry idx, data)
    start = {}
    for i, e in enumerate(ents):
        if e[1] != 2:
            continue
        d = e[3]
        if len(d) < CUT:
            if not d:
                start[i] = END
                continue
            start[i] = len(mini) // MS
            n = (len(d) + MS - 1) // MS
            minifat += [start[i] + k + 1 for k in range(n - 1)] + [END]
            mini += d + b"\0" * (n * MS - len(d))
        else:
            big.append((i, d))
    sectors, fat = [], []

    def put(blob):
        if not blob:
            return END
        n = (len(blob) + SS - 1) // SS
        first = len(sectors)
        for k in range(n):
            sectors.append(blob[k * SS:(k + 1) * SS].ljust(SS, b"\0"))
            fat.append(first + k + 1 if k < n - 1 else END)
        return first

    for i, d in big:
        start[i] = put(d)
    mini_start = put(bytes(mini))
    mf = b"".join(struct.pack("<I", x) for x in minifat)
    mf += b"\xff" * ((-len(mf)) % SS)
    minifat_start = put(mf) if minifat else END
    # directory: children as a degenerate tree (each child's right sibling is the next); colour black
    dirb = bytearray()
    for i, e in enumerate(ents):
        name = e[0].encode("utf-16-le") + b"\0\0"
        kids = e[2]
        child = kids[0] if kids else FREE
        dirb += name.ljust(64, b"\0") + struct.pack("<HBB", len(name), e[1], 1)
        sib = FREE
        for p in ents:
            if i in p[2]:
                j = p[2].index(i)
                sib = p[2][j + 1] if j + 1 < len(p[2]) else FREE
        dirb += struct.pack("<III", FREE, sib, child) + b"\0" * 36  # CLSID, state bits, times
        if e[1] == 5:
            dirb += struct.pack("<IQ", mini_start, len(mini))
        elif e[1] == 2:
            dirb += struct.pack("<IQ", start[i], len(e[3]))
        else:
            dirb += struct.pack("<IQ", 0, 0)
    dirb += b"\0" * ((-len(dirb)) % SS)
    # unused directory slots must be empty entries with FREE siblings
    for k in range(len(ents), len(dirb) // 128):
        dirb[k * 128 + 68:k * 128 + 80] = b"\xff" * 12
    dir_start = put(bytes(dirb))
    nfat = 1
    while (len(sectors) + nfat) > nfat * (SS // 4):
        nfat += 1
    fat_first = len(sectors)
    fat += [FATSEC] * nfat
    fat += [FREE] * (nfat * (SS // 4) - len(fat))
    fatb = b"".join(struct.pack("<I", x) for x in fat)
    for k in range(nfat):
        sectors.append(fatb[k * SS:(k + 1) * SS])
    hdr = bytes.fromhex("D0CF11E0A1B11AE1") + b"\0" * 16 + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6)
    hdr += b"\0" * 6 + struct.pack("<IIIIIIIII", 0, nfat, dir_start, 0, CUT, minifat_start,
                                    (len(mf) // SS) if minifat else 0, END, 0)
    difat = [fat_first + k for k in range(nfat)] + [FREE] * (109 - nfat)
    hdr += b"".join(struct.pack("<I", x) for x in difat)
    return hdr + b"".join(sectors)



def msg_streams(subject, sender_name, sender_addr, to, cc, body, html=None, attachments=()):
    """MAPI property streams for a simple Outlook message. to/cc: [(name, address)]; body None = HTML only."""
    u = lambda s: s.encode("utf-16-le")
    st = {"__substg1.0_0037001F": u(subject), "__substg1.0_0C1A001F": u(sender_name),
          "__substg1.0_5D01001F": u(sender_addr), "__properties_version1.0": b"\0" * 32}
    if to:
        st["__substg1.0_0E04001F"] = u("; ".join(n or a for n, a in to))
    if cc:
        st["__substg1.0_0E03001F"] = u("; ".join(n or a for n, a in cc))
    if body is not None:
        st["__substg1.0_1000001F"] = u(body.replace("\n", "\r\n"))
    if html is not None:
        st["__substg1.0_10130102"] = html.encode("utf-8")
    for k, ((name, addr), rtype) in enumerate([(r, 1) for r in to] + [(r, 2) for r in cc]):
        base = f"__recip_version1.0_#{k:08X}/"
        st[base + "__substg1.0_3001001F"] = u(name or addr)
        st[base + "__substg1.0_39FE001F"] = u(addr)
        st[base + "__properties_version1.0"] = b"\0" * 8 + struct.pack("<IIII", 0x0C150003, 6, rtype, 0)
    for k, (fname, data) in enumerate(attachments):
        base = f"__attach_version1.0_#{k:08X}/"
        st[base + "__substg1.0_3707001F"] = u(fname)
        st[base + "__substg1.0_37010102"] = data
        st[base + "__properties_version1.0"] = b"\0" * 8
    return st


HEADER = re.compile(r"^(Kimden|Kime|Bilgi|Tarih|Konu):\s*(.*)$")


def split_text_mail(text):
    """'Kimden: ...' style text (the demo's e-posta samples) -> ({field: value}, body)."""
    lines, head = text.split("\n"), {}
    i = 0
    while i < len(lines) and HEADER.match(lines[i]):
        k, v = HEADER.match(lines[i]).groups()
        head[k] = v.strip()
        i += 1
    return head, "\n".join(lines[i:]).strip("\n")


def parse_addr(v):
    """'Ad Soyad <a@b>' or 'a@b' -> (name, address)"""
    m = re.match(r"\s*\"?([^\"<]*?)\"?\s*<([^>]+)>\s*$", v)
    return (m.group(1).strip(), m.group(2).strip()) if m else ("", v.strip())


def html_of(body):
    from html import escape
    paras = [p for p in body.split("\n\n")]
    return ("<html><head><style>p{font-family:Calibri}</style></head><body>"
            + "".join(f'<p class="MsoNormal">{escape(p).replace(chr(10), "<br>")}</p>' for p in paras)
            + "</body></html>")


def eml(head, body, style="plain", attachments=()):
    """head: Kimden/Kime/Bilgi/Konu/Tarih values. style: plain | html | alternative | base64 | qp-html."""
    sender, to = parse_addr(head.get("Kimden", "")), parse_addr(head.get("Kime", ""))
    if style == "plain":
        m = EmailMessage()
        m.set_content(body)
    elif style == "base64":
        m = EmailMessage()
        m.set_content(body, cte="base64")
    elif style == "html":
        m = EmailMessage()
        m.set_content(html_of(body), subtype="html")
    elif style == "qp-html":
        m = MIMEMultipart("mixed")
        part = MIMEText(html_of(body), "html", "utf-8")
        payload = part.get_payload(decode=True)
        del part["Content-Transfer-Encoding"]
        part.set_payload(payload)
        encoders.encode_quopri(part)
        m.attach(part)
    else:  # alternative: plain + HTML
        m = EmailMessage()
        m.set_content(body)
        m.add_alternative(html_of(body), subtype="html")
    for fname, data in attachments:
        if isinstance(m, EmailMessage):
            m.add_attachment(data, maintype="application", subtype="octet-stream", filename=fname)
        else:
            a = MIMEApplication(data)
            a.add_header("Content-Disposition", "attachment", filename=fname)
            m.attach(a)
    m["From"] = formataddr(sender) if sender[0] else sender[1]
    if to[1]:
        m["To"] = formataddr(to) if to[0] else to[1]
    if head.get("Bilgi"):
        m["Cc"] = head["Bilgi"]
    m["Subject"] = head.get("Konu", "")
    if head.get("Tarih"):
        m["Date"] = mail_date(head["Tarih"])
    m["Message-ID"] = "<sample@ornek.invalid>"
    return m.as_bytes()


def msg(head, body, html_only=False, attachments=()):
    sender, to = parse_addr(head.get("Kimden", "")), parse_addr(head.get("Kime", ""))
    cc = [parse_addr(x) for x in head.get("Bilgi", "").split(",") if x.strip()]
    st = msg_streams(head.get("Konu", ""), sender[0] or sender[1], sender[1], [to] if to[1] else [], cc,
                     None if html_only else body, html_of(body) if html_only else None, attachments)
    return cfb(st)


def mail_date(v):
    """'24.03.2023' (as the samples write it) -> an RFC 5322 date; anything else is passed through."""
    import datetime
    from email.utils import format_datetime
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})$", v.strip())
    if not m:
        return v
    d, mo, y = map(int, m.groups())
    return format_datetime(datetime.datetime(y, mo, d, 9, 30, tzinfo=datetime.timezone(datetime.timedelta(hours=3))))


# ---------------------------------------------------------------- minimal .xlsx writer (stdlib only)
def _col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def xlsx(sheets, creator="Katip örnek"):
    """sheets: [(name, rows)], a row is a list of str | int | float | None. Strings go to the shared-string
    table (as Excel writes them), numbers stay numbers (an 11-digit TC kimlik typed into Excel is a number)."""
    import io
    import zipfile
    from xml.sax.saxutils import escape, quoteattr
    sst, idx = [], {}

    def si(s):
        if s not in idx:
            idx[s] = len(sst)
            sst.append(s)
        return idx[s]

    sheet_xml = []
    for _, rows in sheets:
        out = []
        for r, row in enumerate(rows, 1):
            cells = []
            for c, v in enumerate(row):
                ref = f"{_col(c)}{r}"
                if v is None or v == "":
                    continue
                if isinstance(v, (int, float)):
                    cells.append(f'<c r="{ref}"><v>{v}</v></c>')
                else:
                    cells.append(f'<c r="{ref}" t="s"><v>{si(str(v))}</v></c>')
            out.append(f'<row r="{r}">{"".join(cells)}</row>')
        sheet_xml.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                         f'<sheetData>{"".join(out)}</sheetData></worksheet>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                  for i in range(1, len(sheets) + 1))
        + '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '</Relationships>',
        "docProps/core.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>' + escape(creator) + '</dc:creator>'
        '<cp:lastModifiedBy>' + escape(creator) + '</cp:lastModifiedBy></cp:coreProperties>',
        "xl/workbook.xml": f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook {ns} {rns}><sheets>'
        + "".join(f'<sheet name={quoteattr(n)} sheetId="{i}" r:id="rId{i}"/>' for i, (n, _) in enumerate(sheets, 1))
        + '</sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                  for i in range(1, len(sheets) + 1))
        + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
        '</Relationships>',
    }
    for i, x in enumerate(sheet_xml, 1):
        files[f"xl/worksheets/sheet{i}.xml"] = x
    files["xl/sharedStrings.xml"] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<sst {ns} count="{len(sst)}" uniqueCount="{len(sst)}">'
                                     + "".join(f'<si><t xml:space="preserve">{escape(s)}</t></si>' for s in sst) + "</sst>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, x in files.items():
            z.writestr(zipfile.ZipInfo(name, (2026, 11, 24, 9, 0, 0)), x.encode("utf-8"), zipfile.ZIP_DEFLATED)
    return buf.getvalue()


# ---------------------------------------------------------------- tables from the samples' answer keys
COLS = [("PERSON", "Ad Soyad"), ("TCKN", "T.C. Kimlik No"), ("PHONE", "Telefon"), ("EMAIL", "E-posta"),
        ("ADDRESS", "Adres"), ("IBAN", "IBAN"), ("BIRTH_DATE", "Doğum tarihi")]


def client_rows(samples):
    """One row per sample: the first value of each column type in its answer key. Returns (rows, gold)."""
    rows, gold = [["Dosya", *[h for _, h in COLS], "Not"]], []
    for sm in samples:
        first = {}
        for g in sm["gold"]:
            first.setdefault(g["entity_type"], g["text"])
        row = [sm["title"]]
        for t, _ in COLS:
            v = first.get(t)
            if v and t == "TCKN" and v.isdigit():
                row.append(int(v))
            else:
                row.append(v)
            if v:
                gold.append({"entity_type": t, "text": v})
        row.append("Vekâlet alındı" if len(rows) % 2 else "Görüşme bekleniyor")
        rows.append(row)
    return rows, gold


def notes_rows(samples):
    """A call log in prose: names inside sentences, as people really type them into a cell."""
    rows, gold = [["Tarih", "Not"]], []
    for i, sm in enumerate(samples):
        p = next((g["text"] for g in sm["gold"] if g["entity_type"] == "PERSON"), None)
        ph = next((g["text"] for g in sm["gold"] if g["entity_type"] == "PHONE"), None)
        if not p:
            continue
        line = f"{p} ile telefonda görüşüldü" + (f", yeni numarası {ph}" if ph else "") + "; evraklar hazırlanacak."
        rows.append([f"{10 + i}.11.2026", line])
        gold += [{"entity_type": "PERSON", "text": p}] + ([{"entity_type": "PHONE", "text": ph}] if ph else [])
    return rows, gold
