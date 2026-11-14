"""KVKK-Bench file-format track: the 306 forms-id documents saved as .udf, .docx, digital PDF and a scanned PDF,
read back the way a firm would read them, then masked and scored against the same gold spans.

Two steps, because the readers and the models live in different Python environments:

  # 1. write the files and read them back (needs pymupdf + rapidocr: Katip connector's uv env)
  <connector python> lab/legal/bench_format.py build
  # 2. run the systems on what was read and score (the bench venv)
  python lab/legal/bench_format.py score rules nano-v2 presidio ...

Files and read-back text go to lab/data/bench/format/ (git-ignored). Scores go to bench/results/format/<system>.json.

Readers
  katip    Katip's own file pipeline (connector engine.read_text = the browser's local_formats.py for UDF/DOCX;
           pymupdf text layer for PDF, local OCR (PaddleOCR/Tesseract) for pages without one).
  generic  what a firm gets with a stock text extractor in front of a plain text model: body paragraphs of the DOCX
           (python-docx's doc.paragraphs), the PDF text layer (pdftotext-style). No UDF reader, no OCR, so UDF and
           scans are "not supported".
Gold spans are moved onto the read-back text with a character alignment (difflib); a value the reader lost entirely
is not counted (it is not in the output, so it cannot leak). Leak rate is the same as on every other track:
share of gold PII characters left readable.
"""
from __future__ import annotations

import argparse, difflib, html, io, json, random, re, sys, time, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FORMS = ROOT / "lab" / "data" / "bench" / "forms-id" / "public" / "forms-id.jsonl"
OUT = ROOT / "lab" / "data" / "bench" / "format"
RES = HERE / "bench" / "results" / "format"
KATIP = Path("/Users/f1k0/Development/Personal/Projects/active/katip")
FONT = "/System/Library/Fonts/Supplemental/Georgia.ttf"   # its cmap gives ordinary spaces back (Times/Arial subsets read back as U+00A0)
FORMATS = ["udf", "docx", "pdf", "scan"]
EXT = {"udf": "udf", "docx": "docx", "pdf": "pdf", "scan": "pdf"}
KATIP_SYSTEMS = {"rules", "tiny", "tiny-f", "mini", "mini-v2", "nano-v2", "xlmr", "berturk-v2", "berturk-clean", "berturk-v1"}


def load_forms():
    return [r for r in (json.loads(l) for l in FORMS.open(encoding="utf-8")) if "canary" not in r]

# ---------------------------------------------------------------- writers

def write_udf(text):
    """UYAP UDF: a zip holding content.xml, the text in one CDATA block plus paragraph offsets."""
    paras, pos = [], 0
    for line in text.split("\n"):
        paras.append(f'<paragraph><content startOffset="{pos}" length="{len(line) + 1}" /></paragraph>')
        pos += len(line) + 1
    xml = ('<?xml version="1.0" encoding="UTF-8" ?>\n<template format_id="1.8">\n'
           f'<content><![CDATA[{text}]]></content>\n'
           '<properties><pageFormat mediaSizeName="1" leftMargin="70.875" rightMargin="70.875" topMargin="56.7" '
           'bottomMargin="56.7" paperOrientation="1" headerFOffset="20.0" footerFOffset="20.0" /></properties>\n'
           f'<elements resolver="hvl-default">{"".join(paras)}</elements>\n'
           '<styles><style name="default" description="Geçerli" family="Times New Roman" size="12" /></styles>\n</template>\n')
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("content.xml", xml)
    return b.getvalue()

def write_docx(text):
    """Minimal WordprocessingML package, one paragraph per line, as Word saves a typed petition."""
    def run(t): return f'<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/></w:rPr><w:t xml:space="preserve">{html.escape(t, quote=False)}</w:t></w:r>'
    body = "".join(f"<w:p>{run(line) if line else ''}</w:p>" for line in text.split("\n"))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f'<w:body>{body}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels); z.writestr("word/document.xml", doc)
    return b.getvalue()

def write_pdf(text):
    """Digital PDF: A4, Georgia 11 pt, lines wrapped at the margin like a word processor's PDF export."""
    import pymupdf
    font = pymupdf.Font(fontfile=FONT)
    W, H, M, SIZE, LEAD = 595, 842, 60, 11, 15
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in re.split(r"(?<= )", para) or [""]:
            if cur and font.text_length(cur + word, SIZE) > W - 2 * M:
                lines.append(cur.rstrip()); cur = word.lstrip()
            else: cur += word
        lines.append(cur)
    doc = pymupdf.open()
    per = int((H - 2 * M) / LEAD)
    for i in range(0, len(lines), per):
        page = doc.new_page(width=W, height=H)
        page.insert_font(fontname="tnr", fontfile=FONT)
        for j, line in enumerate(lines[i:i + per]):
            if line: page.insert_text((M, M + SIZE + j * LEAD), line, fontname="tnr", fontsize=SIZE)
    return doc.tobytes(garbage=3, deflate=True)

def write_scan(pdf_bytes, rng):
    """Office-scanner copy of the digital PDF: 200 dpi greyscale, slight skew and noise, JPEG, no text layer."""
    import pymupdf, numpy as np
    from PIL import Image, ImageFilter
    src, out = pymupdf.open(stream=pdf_bytes, filetype="pdf"), pymupdf.open()
    for page in src:
        pix = page.get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
        im = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        im = im.rotate(rng.uniform(-0.6, 0.6), resample=Image.BICUBIC, fillcolor=255, expand=False).filter(ImageFilter.GaussianBlur(0.5))
        a = np.asarray(im, dtype=np.int16) + np.random.default_rng(rng.randrange(1 << 30)).normal(0, 6, (im.height, im.width)).astype(np.int16)
        im = Image.fromarray(np.clip(a * 0.92 + 14, 0, 255).astype(np.uint8))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=70)
        p = out.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, stream=buf.getvalue())
    return out.tobytes(deflate=True)

# ---------------------------------------------------------------- readers

def generic_read(fmt, data):
    """Stock extractor in front of a plain text model. None = this format is not supported."""
    if fmt == "docx":   # python-docx: "\n".join(p.text for p in doc.paragraphs), runs' w:t and w:tab only
        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
        body = xml.split("<w:body>", 1)[1]
        paras = []
        for p in re.findall(r"<w:p[ >].*?</w:p>|<w:p/>", body, re.S):
            paras.append("".join(html.unescape(t) if t else "\t" for t in re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>|<w:tab/>", p, re.S)))
        return "\n".join(paras)
    if fmt in ("pdf", "scan"):   # text layer only (pdftotext-style); a scan has none
        import pymupdf
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            t = "\n".join(page.get_text() for page in doc)
        return t if len(t.strip()) >= 20 else None
    return None   # UDF: no stock reader

def _one(d):
    sys.path[:0] = [str(KATIP / "connector")]
    from katip_kalkan import engine
    rng = random.Random(f"20261115-{d['id']}")
    files = {"udf": write_udf(d["text"]), "docx": write_docx(d["text"]), "pdf": write_pdf(d["text"])}
    files["scan"] = write_scan(files["pdf"], rng)
    rows = []
    for fmt, data in files.items():
        p = OUT / fmt / f"{d['id']}.{EXT[fmt]}"; p.write_bytes(data)
        t0 = time.time()
        _, text, _, ranges, readers = engine.read_text(p)
        rows.append({"id": d["id"], "format": fmt, "reader": "katip", "text": text, "ocr_ranges": ranges, "ocr": readers,
                     "ms": round(1000 * (time.time() - t0))})
        rows.append({"id": d["id"], "format": fmt, "reader": "generic", "text": generic_read(fmt, data), "ocr_ranges": [], "ocr": []})
    return rows

def build(a):
    from concurrent.futures import ProcessPoolExecutor
    docs = load_forms()[: a.limit or None]
    for f in FORMATS: (OUT / f).mkdir(parents=True, exist_ok=True)
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(_one, docs)):
            rows += r
            if i % 25 == 0: print(f"{i + 1}/{len(docs)}", flush=True)
    with (OUT / "read.jsonl").open("w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    src = {d["id"]: d["text"] for d in docs}
    same = {fmt: sum(r["text"] == src[r["id"]] for r in rows if r["format"] == fmt and r["reader"] == "katip") for fmt in FORMATS}
    print("katip read-back identical to source:", same, f"of {len(docs)}")

# ---------------------------------------------------------------- scoring

def move_spans(src, dst, spans):
    """Map gold [s, e) from src onto dst by character alignment. Spans the reader dropped completely are left out."""
    if src == dst: return [list(x) for x in spans]
    m = [None] * len(src)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, src, dst, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1): m[i1 + k] = j1 + k
        elif op == "replace":
            for k in range(i2 - i1): m[i1 + k] = j1 + min(j2 - j1 - 1, (k * (j2 - j1)) // (i2 - i1))
    out = []
    for s, e, t in spans:
        js = [m[k] for k in range(s, e) if m[k] is not None]
        if js: out.append([min(js), max(js) + 1, t])
    return out

def score(a):
    import bench_run as BR, bench_score as BS
    docs = {d["id"]: d for d in load_forms()}
    read = [json.loads(l) for l in (OUT / "read.jsonl").open(encoding="utf-8")]
    RES.mkdir(parents=True, exist_ok=True)
    for key in a.systems:
        reader = "katip" if key in KATIP_SYSTEMS else "generic"
        name, make = BR.SYSTEMS[key]
        det, _ = make()
        cached = {}
        pf = HERE / "bench" / "preds" / "forms" / f"{key}.jsonl"
        if pf.exists(): cached = {p["id"]: p["spans"] for p in map(json.loads, pf.open(encoding="utf-8"))}
        row = {"system": key, "name": name, "track": "format",
               "set": "forms-id v0.1 (306 docs) saved as UDF / DOCX / digital PDF / 200 dpi scan PDF",
               "reader": "Katip's own file readers" if reader == "katip" else "with a generic text extractor (python-docx paragraphs / PDF text layer)",
               "formats": {}}
        for fmt in FORMATS:
            rs = [r for r in read if r["format"] == fmt and r["reader"] == reader]
            if not rs or all(r["text"] is None for r in rs):
                why = "no UDF reader" if fmt == "udf" else ("no OCR: a scan has no text layer" if fmt == "scan" else "no reader")
                row["formats"][fmt] = {"supported": False, "leak_rate": None, "docs": 0, "note": why}; continue
            gold, pred, lost, t0 = [], [], 0, time.time()
            for r in rs:
                d = docs[r["id"]]
                spans = move_spans(d["text"], r["text"], d["spans"])
                lost += len(d["spans"]) - len(spans)
                gold.append({"id": r["id"], "track": "format", "text": r["text"], "spans": spans})
                if r["text"] == d["text"] and r["id"] in cached: ps = cached[r["id"]]
                else:
                    BR.DETECT_KW = {"address_detail": "full", **({"ocr_ranges": [tuple(x) for x in r["ocr_ranges"]]} if r["ocr_ranges"] else {})}
                    ps = [list(x[:3]) for x in det(r["text"])]
                    BR.DETECT_KW = {"address_detail": "full"}
                pred.append({"id": r["id"], "spans": ps})
            x = BS.score(gold, pred)["tracks"]["format"]
            row["formats"][fmt] = {"supported": True, "leak_rate": round(x["leak_rate"], 4), "docs": len(rs),
                                   "recall": round(x["recall"], 4), "precision": round(x["precision"], 4),
                                   "clean_doc_rate": round(x["clean_doc_rate"], 4), "gold_values_lost_by_reader": lost}
        (RES / f"{key}.json").write_text(json.dumps(row, indent=1, ensure_ascii=False))
        print(f"{name[:55]:55} " + "  ".join(f"{f}: " + (f"{100 * v['leak_rate']:5.2f}%" if v["supported"] else "  n/a ") for f, v in row["formats"].items()), flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--limit", type=int, default=0); b.add_argument("--workers", type=int, default=4)
    s = sub.add_parser("score"); s.add_argument("systems", nargs="+")
    a = ap.parse_args()
    if a.cmd == "build": build(a)
    else:
        sys.path[:0] = [str(HERE), str(HERE.parent)]
        score(a)
