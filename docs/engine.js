// Katip Yerel engine: parse -> detect -> redact -> leak check, all in-process.
// Used by worker.js in the browser and by test_node.mjs in Node. No network I/O here.
export const OCR_DPI = 300;
const MIN_TEXT_CHARS = 20;

export function kindOf(name) {
  const ext = name.toLowerCase().split(".").pop();
  if (ext === "pdf") return "pdf";
  if (["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"].includes(ext)) return "image";
  if (ext === "docx") return "docx";
  if (ext === "udf") return "udf";
  if (["txt", "md", "csv"].includes(ext)) return "txt";
  throw new Error(`Desteklenmeyen dosya türü: .${ext}`);
}

// ---- text assembly (same layout rule as documents._assemble on the server)
function assemble(pages) {
  let text = "";
  for (const p of pages) {
    p.start = text.length;
    for (const line of p.lines) {
      line.forEach((w, k) => {
        if (k) text += " ";
        w.start = text.length; text += w.text; w.end = text.length;
        p.words.push(w);
      });
      text += "\n";
    }
    text += "\f\n";
    p.end = text.length;
  }
  return text;
}

// MuPDF structured text -> lines of words with boxes (PDF points)
function pdfLines(page) {
  const st = page.toStructuredText("preserve-whitespace");
  const lines = []; let line = null, word = null;
  const flush = () => { if (word && word.text.trim()) line.push(word); word = null; };
  st.walk({
    beginLine() { line = []; },
    onChar(c, origin, font, size, quad) {
      if (/\s/.test(c)) { flush(); return; }
      const xs = [quad[0], quad[2], quad[4], quad[6]], ys = [quad[1], quad[3], quad[5], quad[7]];
      const b = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
      if (!word) word = { text: "", bbox: b };
      word.text += c;
      word.bbox = [Math.min(word.bbox[0], b[0]), Math.min(word.bbox[1], b[1]), Math.max(word.bbox[2], b[2]), Math.max(word.bbox[3], b[3])];
    },
    endLine() { flush(); if (line.length) lines.push(line); },
  });
  st.destroy?.();
  lines.sort((a, b) => Math.min(...a.map(w => w.bbox[1])) - Math.min(...b.map(w => w.bbox[1])));
  return lines.map(l => l.sort((a, b) => a.bbox[0] - b.bbox[0]));
}

// ocr(pngBytes) must resolve to lines of {text, bbox:[x0,y0,x1,y1]} in pixels
export async function parsePdf(mupdf, bytes, ocr, { forceOcr = false, onProgress } = {}) {
  const doc = mupdf.Document.openDocument(bytes, "application/pdf");
  const n = doc.countPages(), pages = [];
  let ocrPages = 0;
  for (let i = 0; i < n; i++) {
    onProgress?.(`Sayfa ${i + 1}/${n}`);
    const page = doc.loadPage(i);
    const [x0, y0, x1, y1] = page.getBounds();
    const p = { number: i, width: x1 - x0, height: y1 - y0, words: [], ocr: false, lines: forceOcr ? [] : pdfLines(page) };
    if (p.lines.flat().reduce((s, w) => s + w.text.length, 0) < MIN_TEXT_CHARS) {
      if (!ocr) throw new Error("Taranmış sayfa var ama OCR yüklenmedi");
      onProgress?.(`OCR sayfa ${i + 1}/${n}`);
      const s = OCR_DPI / 72;
      const pix = page.toPixmap(mupdf.Matrix.scale(s, s), mupdf.ColorSpace.DeviceRGB, false);
      const png = pix.asPNG(); pix.destroy?.();
      p.lines = (await ocr(png)).map(l => l.map(w => ({ text: w.text, bbox: w.bbox.map(v => v / s) })));
      p.ocr = true; ocrPages++;
    }
    pages.push(p);
  }
  return { kind: "pdf", text: assemble(pages), pages, ocrPages, _doc: doc };
}

export async function parseImage(bytes, ocr, size) {
  const p = { number: 0, width: size?.width ?? 0, height: size?.height ?? 0, words: [], ocr: true, lines: await ocr(bytes) };
  return { kind: "image", text: assemble([p]), pages: [p], ocrPages: 1 };
}

// ---- spans -> boxes (port of redact.attach_boxes; errs towards over-masking)
export function attachBoxes(doc, spans) {
  for (const sp of spans) {
    const page = doc.pages.find(p => sp.start >= p.start && sp.start < p.end);
    if (!page) continue;
    sp.page = page.number;
    const byLine = new Map();
    for (const w of page.words) {
      if (w.end <= sp.start || w.start >= sp.end) continue;
      const [x0, y0, x1, y1] = w.bbox, n = Math.max(1, w.text.length);
      let a = Math.max(sp.start, w.start) - w.start, b = Math.min(sp.end, w.end) - w.start;
      if (!/[\p{L}\p{N}]/u.test(w.text.slice(0, a))) a = 0;
      if (!/[\p{L}\p{N}]/u.test(w.text.slice(b))) b = n;
      const cw = (x1 - x0) / n;
      const cx0 = x0 + cw * a - (a ? cw / 2 : 0), cx1 = x0 + cw * b + (b < n ? cw / 2 : 0);
      const key = Math.round((y0 + y1) / 2 / 4);
      const box = byLine.get(key) ?? [cx0, y0, cx1, y1];
      byLine.set(key, [Math.min(box[0], cx0), Math.min(box[1], y0), Math.max(box[2], cx1), Math.max(box[3], y1)]);
    }
    sp.boxes = [...byLine.values()];
  }
}

// Fill rectangles (page space, y down) into the page content itself, wrapped so the
// original content's graphics state cannot leak into ours.
function paintBoxes(mupdf, pdf, page, boxes, [r, g, b]) {
  const inv = mupdf.Matrix.invert(page.getTransform());
  const f = v => v.toFixed(3);
  let ops = `Q q ${f(r)} ${f(g)} ${f(b)} rg\n`;
  for (const box of boxes) {
    const [x0, y0, x1, y1] = mupdf.Rect.transform(box, inv);
    ops += `${f(Math.min(x0, x1))} ${f(Math.min(y0, y1))} ${f(Math.abs(x1 - x0))} ${f(Math.abs(y1 - y0))} re f\n`;
  }
  ops += "Q\n";
  const obj = page.getObject(), old = obj.get("Contents");
  const arr = pdf.newArray();
  arr.push(pdf.addStream(new TextEncoder().encode("q\n"), {}));
  if (old.isArray()) old.forEach(v => arr.push(v)); else if (!old.isNull?.()) arr.push(old);
  arr.push(pdf.addStream(new TextEncoder().encode(ops), {}));
  obj.put("Contents", arr);
}

// ---- true PDF redaction: remove glyphs + blank image pixels, then paint the mask colour,
// add the optional watermark line + link, and scrub metadata.
// opts.color: [r, g, b] in 0..1 (default black); opts.watermark: { text, url } or null
export function redactPdf(mupdf, doc, spans, opts = {}) {
  const pdf = doc._doc, PAD = 1, color = opts.color ?? [0, 0, 0], wm = opts.watermark;
  const per = new Map();
  for (const sp of spans) if (sp.page != null) per.set(sp.page, [...(per.get(sp.page) ?? []), ...sp.boxes]);
  for (const [pno, boxes] of per) {
    const page = pdf.loadPage(pno);
    for (const [x0, y0, x1, y1] of boxes) {
      const a = page.createAnnotation("Redact");
      a.setRect([x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD]);
      a.update?.();
    }
    page.applyRedactions(false, mupdf.PDFPage.REDACT_IMAGE_PIXELS);
    paintBoxes(mupdf, pdf, page, boxes.map(([x0, y0, x1, y1]) => [x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD]), color);
  }
  const links = [];
  if (wm?.text) for (let i = 0; i < pdf.countPages(); i++) {
    const page = pdf.loadPage(i), [bx0, by0, bx1, by1] = page.getBounds();
    const r = [bx0 + 24, by1 - 18, Math.min(bx1 - 24, bx0 + 24 + wm.text.length * 3.6), by1 - 8];
    const a = page.createAnnotation("FreeText");
    a.setRect(r); a.setContents(wm.text); a.setDefaultAppearance("Helv", 6.5, [0.45, 0.45, 0.45]); a.setBorderWidth(0); a.setFlags(4 | 128); a.update?.();  // print + locked
    if (wm.url) links.push([i, r]);
  }
  for (const [i, r] of links) pdf.loadPage(i).createLink(r, wm.url);
  for (const k of ["info:Title", "info:Author", "info:Subject", "info:Keywords", "info:Creator", "info:Producer"])
    pdf.setMetaData(k, k === "info:Producer" || k === "info:Creator" ? "katip-yerel" : "");
  try { pdf.getTrailer().get("Root").delete("Metadata"); } catch { /* no XMP */ }
  return pdf.saveToBuffer("garbage=4,compress,clean").asUint8Array().slice();
}

export function pdfText(mupdf, bytes) {
  const d = mupdf.Document.openDocument(bytes, "application/pdf"); let t = "";
  for (let i = 0; i < d.countPages(); i++) t += d.loadPage(i).toStructuredText().asText() + "\n";
  return t;
}

// ---- python bridge
export function pyDetect(py, text, opts) {
  py.globals.set("_T", text); py.globals.set("_O", JSON.stringify(opts ?? {}));
  return JSON.parse(py.runPython("import local_detect; local_detect.detect_json(_T, _O)"));
}
export function pyExtract(py, kind, bytes) {
  py.globals.set("_K", kind); py.globals.set("_B", bytes);
  return py.runPython("import local_formats; local_formats.extract(_K, _B.to_py())");
}
export function pyRedact(py, kind, bytes, spans, style, watermark = "") {
  py.globals.set("_K", kind); py.globals.set("_B", bytes); py.globals.set("_S", JSON.stringify(spans)); py.globals.set("_Y", style); py.globals.set("_W", watermark);
  const r = py.runPython("import local_formats; local_formats.redact(_K, _B.to_py(), _S, _Y, _W)");
  const out = r.toJs(); r.destroy(); return out;
}
export function pyLeaks(py, outText, spans) {
  py.globals.set("_T", outText); py.globals.set("_S", JSON.stringify(spans));
  return JSON.parse(py.runPython("import local_formats; local_formats.leak_check(_T, _S)"));
}

// ---- images: burn boxes into pixels (colour [r,g,b] 0..1), re-encode as PNG (drops EXIF/GPS)
export function redactImage(mupdf, bytes, spans, mime = "image/png", color = [0, 0, 0]) {
  const d = mupdf.Document.openDocument(bytes, mime);
  const page = d.loadPage(0);
  const img = new mupdf.Image(bytes);
  const [x0, , x1] = page.getBounds();
  const s = img.getWidth() / (x1 - x0);
  const pix = page.toPixmap(mupdf.Matrix.scale(s, s), mupdf.ColorSpace.DeviceRGB, false);
  const w = pix.getWidth(), h = pix.getHeight(), stride = pix.getStride(), n = pix.getNumberOfComponents();
  const px = pix.getPixels(), P = 2;
  for (const sp of spans) for (const [bx0, by0, bx1, by1] of sp.boxes ?? []) {
    for (let y = Math.max(0, Math.floor(by0 - P)); y < Math.min(h, Math.ceil(by1 + P)); y++)
      for (let x = Math.max(0, Math.floor(bx0 - P)); x < Math.min(w, Math.ceil(bx1 + P)); x++)
        for (let c = 0; c < n; c++) px[y * stride + x * n + c] = Math.round(255 * (color[c] ?? 0));
  }
  return pix.asPNG().slice();
}

// render each page of a PDF for a second OCR pass (leak check on scans)
export function pdfPagePngs(mupdf, bytes, pages, dpi = OCR_DPI) {
  const d = mupdf.Document.openDocument(bytes, "application/pdf"), s = dpi / 72;
  return pages.map(i => d.loadPage(i).toPixmap(mupdf.Matrix.scale(s, s), mupdf.ColorSpace.DeviceRGB, false).asPNG().slice());
}
