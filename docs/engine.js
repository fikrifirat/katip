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

// ocr(pngBytes) must resolve to lines of {text, bbox:[x0,y0,x1,y1]} in pixels; ocr.engine names it ("paddle" or Tesseract by default)
export async function parsePdf(mupdf, bytes, ocr, { forceOcr = false, onProgress } = {}) {
  const doc = mupdf.Document.openDocument(bytes, "application/pdf");
  const n = doc.countPages(), pages = [];
  let ocrPages = 0;
  for (let i = 0; i < n; i++) {
    onProgress?.(`Sayfa ${i + 1}/${n}`);
    const page = doc.loadPage(i);
    const [x0, y0, x1, y1] = page.getBounds();
    const p = { number: i, width: x1 - x0, height: y1 - y0, words: [], ocr: false, engine: null, lines: forceOcr ? [] : pdfLines(page) };
    if (p.lines.flat().reduce((s, w) => s + w.text.length, 0) < MIN_TEXT_CHARS) {
      if (!ocr) throw new Error("Taranmış sayfa var ama OCR yüklenmedi");
      onProgress?.(`OCR sayfa ${i + 1}/${n}`);
      const s = ocrScale(p.width, p.height);
      const pix = page.toPixmap(mupdf.Matrix.scale(s, s), mupdf.ColorSpace.DeviceRGB, false);
      const { colour, ...prep } = prepareScan(pix) ?? {};
      p.prep = prep;
      const pen = unreadInk(pix, [], { colour }).filter(b => b.pen >= PEN_BLUE);
      const read = pickOcr(ocr, pen, prep);
      let raw = await read(pix.asPNG());
      const blobs = unreadInk(pix, raw.flat().map(w => w.bbox), { colour });
      const again = await reocrBlobs(mupdf, pix, blobs, read);
      raw = mergeLines(raw, again.words);
      p.unread = again.unread.map(b => Object.assign(b.map(v => v / s), { pen: b.pen }));
      p.pen = pen.map(b => Object.assign(b.map(v => v / s), { pen: b.pen }));
      p.reocr = again.words.length;
      pix.destroy?.();
      p.lines = raw.map(l => l.map(w => ({ text: w.text, bbox: w.bbox.map(v => v / s) })));
      p.ocr = true; p.engine = read.engine ?? "tesseract"; ocrPages++;
    }
    pages.push(p);
  }
  return { kind: "pdf", text: assemble(pages), pages, ocrPages, _doc: doc };
}

// "auto" OCR: an ocr function may carry forPage({ pen, cropped }) to pick a reader per page. Katip Yerel
// uses it to send handwriting and phone photos to PaddleOCR and printed scans to Tesseract.
// pen = ballpoint-blue ink blobs found before any OCR; cropped = a photographed sheet was cut out of a background.
export const HANDWRITING_MIN_BLOBS = 3;
function pickOcr(ocr, pen, prep) {
  return ocr.forPage?.({ pen: pen.length, cropped: !!prep?.cropped, handwriting: pen.length >= HANDWRITING_MIN_BLOBS || !!prep?.cropped }) ?? ocr;
}

export async function parseImage(bytes, ocr, size, mupdf = null) {
  let png = bytes, prep = null;
  if (mupdf) {  // same clean-up as scanned PDF pages; pixel coordinates stay those of the original image
    const img = new mupdf.Image(bytes), pix = img.toPixmap();
    const rgb = pix.getNumberOfComponents() === 3 && !pix.getAlpha?.() ? pix : pix.convertToColorSpace(mupdf.ColorSpace.DeviceRGB, false);
    const { colour, ...rest } = prepareScan(rgb) ?? {};
    prep = rest; png = rgb.asPNG().slice();
    const pen = unreadInk(rgb, [], { colour }).filter(b => b.pen >= PEN_BLUE), read = pickOcr(ocr, pen, prep);
    let lines = await read(png);
    const again = await reocrBlobs(mupdf, rgb, unreadInk(rgb, lines.flat().map(w => w.bbox), { colour }), read);
    lines = mergeLines(lines, again.words);
    const p = { number: 0, width: size?.width ?? rgb.getWidth(), height: size?.height ?? rgb.getHeight(), words: [], ocr: true, engine: read.engine ?? "tesseract", prep, unread: again.unread, pen, lines };
    return { kind: "image", text: assemble([p]), pages: [p], ocrPages: 1 };
  }
  const p = { number: 0, width: size?.width ?? 0, height: size?.height ?? 0, words: [], ocr: true, prep, unread: [], lines: await ocr(png) };
  return { kind: "image", text: assemble([p]), pages: [p], ocrPages: 1 };
}

// ---- handwriting the OCR could not read
// After prepareScan: dark strokes that no OCR word covers, with ruled lines (form borders) removed and
// strokes grouped into word-sized blobs. On a filled-in form these are mostly handwritten values the
// OCR skipped (an ID number, a name) and signatures; they become UNREAD items so they can be masked
// even though there is no text to check. Boxes are in pixmap pixels.
export function unreadInk(pix, wordBoxes, { dark = 150, colour = null } = {}) {
  const w = pix.getWidth(), h = pix.getHeight(), stride = pix.getStride(), n = pix.getNumberOfComponents(), px = pix.getPixels();
  const ink = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) ink[y * w + x] = px[y * stride + x * n] < dark ? 1 : 0;
  // ruled lines: long horizontal / vertical runs of ink. A photographed line is slanted and a few pixels
  // thick, so a pixel counts as "on" for the run if any pixel within 2 rows (columns) of it is ink, small
  // gaps are bridged, and the whole band around a found run is cleared.
  const L = Math.max(40, Math.round(Math.max(w, h) / 30)), T = 2, GAP = 3;
  const clearH = (y, a, b) => { for (let yy = Math.max(0, y - T - 1); yy <= Math.min(h - 1, y + T + 1); yy++) for (let k = a; k < b; k++) if (ink[yy * w + k]) ink[yy * w + k] = 2; };
  const clearV = (x, a, b) => { for (let xx = Math.max(0, x - T - 1); xx <= Math.min(w - 1, x + T + 1); xx++) for (let k = a; k < b; k++) if (ink[k * w + xx]) ink[k * w + xx] = 2; };
  for (let y = 0; y < h; y += 2) {
    let a = -1, gap = 0;
    for (let x = 0; x <= w; x++) {
      let on = false;
      if (x < w) for (let yy = Math.max(0, y - T); yy <= Math.min(h - 1, y + T) && !on; yy++) on = ink[yy * w + x] > 0;
      if (on) { if (a < 0) a = x; gap = 0; } else if (a >= 0 && ++gap > GAP) { if (x - gap - a >= L) clearH(y, a, x - gap + 1); a = -1; gap = 0; }
    }
  }
  for (let x = 0; x < w; x += 2) {
    let a = -1, gap = 0;
    for (let y = 0; y <= h; y++) {
      let on = false;
      if (y < h) for (let xx = Math.max(0, x - T); xx <= Math.min(w - 1, x + T) && !on; xx++) on = ink[y * w + xx] === 1;
      if (on) { if (a < 0) a = y; gap = 0; } else if (a >= 0 && ++gap > GAP) { if (y - gap - a >= L) clearV(x, a, y - gap + 1); a = -1; gap = 0; }
    }
  }
  // what the OCR read
  const P = 3;
  for (const [x0, y0, x1, y1] of wordBoxes)
    for (let y = Math.max(0, Math.floor(y0) - P); y < Math.min(h, Math.ceil(y1) + P); y++)
      for (let x = Math.max(0, Math.floor(x0) - P); x < Math.min(w, Math.ceil(x1) + P); x++) ink[y * w + x] = 0;
  // coarse grid, joined sideways so the strokes of one handwritten word become one blob
  const C = Math.max(3, Math.round(Math.max(w, h) / 600)), gw = Math.ceil(w / C), gh = Math.ceil(h / C), g = new Uint8Array(gw * gh);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (ink[y * w + x] === 1) g[((y / C) | 0) * gw + ((x / C) | 0)]++;
  const on = new Uint8Array(gw * gh), JX = 4, JY = 0;
  for (let y = 0; y < gh; y++) for (let x = 0; x < gw; x++) if (g[y * gw + x] >= 2)
    for (let dy = -JY; dy <= JY; dy++) for (let dx = -JX; dx <= JX; dx++) { const yy = y + dy, xx = x + dx; if (yy >= 0 && yy < gh && xx >= 0 && xx < gw) on[yy * gw + xx] = 1; }
  const seen = new Uint8Array(gw * gh), boxes = [], stack = [];
  for (let i = 0; i < gw * gh; i++) {
    if (!on[i] || seen[i]) continue;
    let bx0 = gw, by0 = gh, bx1 = 0, by1 = 0, mass = 0;
    stack.push(i); seen[i] = 1;
    while (stack.length) {
      const j = stack.pop(), x = j % gw, y = (j / gw) | 0;
      bx0 = Math.min(bx0, x); bx1 = Math.max(bx1, x); by0 = Math.min(by0, y); by1 = Math.max(by1, y); mass += g[j];
      for (const k of [j - 1, j + 1, j - gw, j + gw]) if (k >= 0 && k < gw * gh && on[k] && !seen[k] && Math.abs((k % gw) - x) <= 1) { seen[k] = 1; stack.push(k); }
    }
    // undo the sideways join on the box edges, then keep word-sized blobs with real ink in them
    const x0 = (bx0 + JX) * C, x1 = (bx1 - JX + 1) * C, y0 = (by0 + JY) * C, y1 = (by1 - JY + 1) * C;
    const bw = x1 - x0, bh = y1 - y0, minH = Math.max(h, w) / 160;
    if (bw < 2 * minH || bh < minH || bh > h / 16 || bw > w * 0.5 || mass < 4 * minH) continue;  // thin = left-over ruling
    // mean blueness (blue minus red) of the blob's ink: ballpoint ink is bluer than printed black
    let inkN = 0, colN = 0;
    if (colour) for (let y = Math.max(0, y0); y < Math.min(h, y1); y++) for (let x = Math.max(0, x0); x < Math.min(w, x1); x++)
      if (ink[y * w + x] === 1) { inkN++; colN += colour[y * w + x] - 128; }
    const box = [x0, y0, x1, y1];
    box.pen = inkN ? colN / inkN : 0;
    boxes.push(box);
  }
  return boxes;
}

// Second look at what the page OCR skipped: Tesseract's page layout analysis often drops whole rows of
// a ruled form (two-line label cells, handwriting between lines), but reads the same strokes when given
// them alone. Each blob (with a margin) is cut out and read again; blobs that now give text become words
// of the page, the rest stay "unread". Coordinates are pixmap pixels.
export async function reocrBlobs(mupdf, pix, blobs, ocr, { pad = 10, maxBlobs = 80 } = {}) {
  const w = pix.getWidth(), h = pix.getHeight(), stride = pix.getStride(), n = pix.getNumberOfComponents(), px = pix.getPixels();
  const words = [], unread = [];
  for (const [k, b] of blobs.entries()) {
    if (k >= maxBlobs) { unread.push(b); continue; }
    const x0 = Math.max(0, Math.floor(b[0] - pad)), y0 = Math.max(0, Math.floor(b[1] - pad)), x1 = Math.min(w, Math.ceil(b[2] + pad)), y1 = Math.min(h, Math.ceil(b[3] + pad));
    // white frame around the crop helps Tesseract find the line
    const F = 20, cw = x1 - x0 + 2 * F, ch = y1 - y0 + 2 * F;
    const crop = new mupdf.Pixmap(mupdf.ColorSpace.DeviceRGB, [0, 0, cw, ch], false);
    const cp = crop.getPixels(), cs = crop.getStride();
    cp.fill(255);
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) for (let c = 0; c < 3; c++) cp[(y - y0 + F) * cs + (x - x0 + F) * 3 + c] = px[y * stride + x * n + c];
    let got = [];
    try { got = (await ocr(crop.asPNG())).flat(); } catch { got = []; }
    crop.destroy?.();
    const good = got.filter(t => (t.text.match(/[\p{L}\p{N}]/gu) ?? []).length >= 2);
    if (!good.length) { unread.push(b); continue; }
    for (const t of good) words.push({ text: t.text, bbox: [t.bbox[0] - F + x0, t.bbox[1] - F + y0, t.bbox[2] - F + x0, t.bbox[3] - F + y0], reocr: true });
  }
  return { words, unread };
}

// Put re-read words into the page's lines by vertical overlap (so "Kiraya verenin T.C. Kimlik No" and the
// number written next to it end up on one text line), then order lines top to bottom, words left to right.
export function mergeLines(lines, words) {
  if (!words.length) return lines;
  const out = lines.map(l => [...l]);
  const mid = b => (b[1] + b[3]) / 2;
  for (const wd of words) {
    let best = null, bestD = Infinity;
    for (const l of out) {
      const y0 = Math.min(...l.map(x => x.bbox[1])), y1 = Math.max(...l.map(x => x.bbox[3]));
      const m = mid(wd.bbox);
      if (m >= y0 && m <= y1) { const d = Math.abs(m - (y0 + y1) / 2); if (d < bestD) { bestD = d; best = l; } }
    }
    if (best) best.push(wd); else out.push([wd]);
  }
  for (const l of out) l.sort((a, b) => a.bbox[0] - b.bbox[0]);
  out.sort((a, b) => Math.min(...a.map(x => x.bbox[1])) - Math.min(...b.map(x => x.bbox[1])));
  return out;
}

// Blueness above which an unread blob is taken as pen (handwriting). On the one real photographed lease we
// have, handwritten values measured +7 to +9 and printed labels -3 to -11; to be checked on the synthetic
// photo set.
export const PEN_BLUE = 6;
// A row label that asks for personal data: "Kiraya verenin", "Kiracının", "T.C. Kimlik No", "Adı Soyadı" ...
const PII_LABEL = /kimlik|t\.?c\.?$|tckn|soyad|ad soyad|kiraya veren|kirac[ıi]|kefil|mal sahibi|telefon|^tel\b|gsm|iban|hesap no|vergi no|ikamet|adres|imza|vekil|davac[ıi]|daval[ıi]|borçlu|alacakl[ıi]/i;
// Labels whose handwritten value is always masked, read or not: ID numbers and names. Not addresses (the
// street stays readable; the text rules mask the building and door) and not party words alone.
const ID_NAME_LABEL = /k[iı]ml[iı]k|kımlık|tckn|t\.\s?c\.|\btc\b|soy\s?ad|ad[ıi]\s+soyad/i;
const median = a => { const b = [...a].sort((x, y) => x - y); return b.length ? b[b.length >> 1] : 0; };
const rowWords = (p, [x0, y0, x1, y1]) => {
  const m = (y1 - y0) * 0.5;
  return p.words.filter(w => w.bbox[2] <= x0 + 2 && w.bbox[3] > y0 - m && w.bbox[1] < y1 + m);
};

// Handwriting items for the review list, one per ink blob, each carrying its own box (no text offsets):
// * pen ink in a row labelled T.C. Kimlik No or Adı soyadı: masked, whatever the OCR made of it
//   (handwritten digits often come out as letters, so the text rules cannot be relied on there);
// * pen ink the OCR could not read at all, next to any personal-data label: masked;
// * other unreadable marks: listed for review, unmasked.
export function unreadSpans(doc) {
  const out = [];
  for (const p of doc.pages ?? []) {
    const add = (b, i, kind, masked, why) => out.push({
      id: `u${p.number}_${kind}${i}`, uid: `UNREAD:${p.number}:${kind}${i}`, entity_type: "UNREAD", start: p.end, end: p.end, text: "", score: 0.5,
      recognizer: kind === "p" ? "pen_in_id_row" : "unread_ink", explanation: why, flag_only: !masked, page: p.number, boxes: [[b[0], b[1], b[2], b[3]]] });
    const penBoxes = [];
    (p.pen ?? []).forEach((b, i) => {
      // strict row match: the blob's middle must sit inside the label line, so a tall blob
      // that spills over from a neighbouring (street) row does not count
      // (two-line label cells: the ink sits between "Kiraya verenin" and "T.C. Kimlik No.", so allow one line of slack)
      const lh = p.lineH ??= median(p.words.map(w => w.bbox[3] - w.bbox[1])) || 10;
      // errs towards masking: a TC number left readable is worse than a street hidden by mistake
      // PaddleOCR boxes are about a third taller than Tesseract's, so a full line of slack reaches the
      // street row below a TC row; there the blob's middle must sit within 0.6 line of the label instead
      const cy = (b[1] + b[3]) / 2;
      const words = p.engine === "paddle" ? p.words.filter(w => w.bbox[2] <= b[0] + 2 && cy > w.bbox[1] - 0.6 * lh && cy < w.bbox[3] + 0.6 * lh)
        : p.words.filter(w => w.bbox[2] <= b[0] + 2 && w.bbox[3] > b[1] - lh && w.bbox[1] < b[3] + lh);
      if (b[3] - b[1] <= 3.5 * lh && ID_NAME_LABEL.test(words.map(w => w.text).join(" "))) { penBoxes.push(b); add(b, i, "p", true, "handwriting in a row labelled T.C. Kimlik No / Adı soyadı"); }
    });
    (p.unread ?? []).forEach((b, i) => {
      if (penBoxes.some(q => q[0] < b[2] && q[2] > b[0] && q[1] < b[3] && q[3] > b[1])) return;
      const pen = b.pen >= PEN_BLUE, label = PII_LABEL.test(rowWords(p, b).map(w => w.text).join(" ").toLocaleLowerCase("tr"));
      add(b, i, "u", pen && label, pen ? (label ? "handwriting next to a personal-data label, not readable by OCR" : "handwriting the OCR could not read") : "marks the OCR could not read");
    });
  }
  return out;
}

// ---- spans -> boxes (port of redact.attach_boxes; errs towards over-masking)
export function attachBoxes(doc, spans) {
  for (const sp of spans) {
    if (sp.entity_type === "UNREAD") continue;  // boxes come from the page image, not from text
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
    // handwriting: OCR often drops the first or last letter of a word, so grow the box over pen ink
    // that touches it on the same line (not over tall blobs such as signatures)
    if (page.ocr && page.pen?.length && sp.entity_type !== "ADDRESS") sp.boxes = sp.boxes.map(b => {
      let [x0, y0, x1, y1] = b; const h = y1 - y0;
      for (const q of page.pen) {
        const vo = Math.min(y1, q[3]) - Math.max(y0, q[1]), gap = Math.max(x0, q[0]) - Math.min(x1, q[2]);
        if (q[3] - q[1] <= 2 * h && vo > 0.5 * Math.min(h, q[3] - q[1]) && gap < 0.8 * h)
          [x0, y0, x1, y1] = [Math.min(x0, q[0]), Math.min(y0, q[1]), Math.max(x1, q[2]), Math.max(y1, q[3])];
      }
      return [x0, y0, x1, y1];
    });
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

// Centre stamp: the Katip mark across the middle of the page, drawn on top of everything
// (so it shows on scans too) at low opacity through an ExtGState.
function stampMark(mupdf, pdf, page, mark, alpha = 0.08) {
  const obj = page.getObject();
  let res = obj.getInheritable("Resources");
  if (res.isNull()) { res = pdf.newDictionary(); }
  obj.put("Resources", res);
  let ext = res.get("ExtGState");
  if (ext.isNull()) { ext = pdf.newDictionary(); res.put("ExtGState", ext); }
  const gs = pdf.newDictionary();
  gs.put("Type", pdf.newName("ExtGState")); gs.put("ca", alpha); gs.put("CA", alpha);
  ext.put("KatipMark", pdf.addObject(gs));
  const [bx0, by0, bx1, by1] = page.getBounds(), W = bx1 - bx0, H = by1 - by0;
  const size = Math.min(W, H) * 0.42, ox = bx0 + (W - size) / 2, oy = by0 + (H - size) / 2, k = size / 32;
  const [a, b, c, d, e, f] = mupdf.Matrix.invert(page.getTransform());
  const pt = (x, y) => { const X = ox + x * k, Y = oy + y * k; return `${(a * X + c * Y + e).toFixed(2)} ${(b * X + d * Y + f).toFixed(2)}`; };
  const path = cmds => cmds.map(([op, ...v]) => op === "Z" ? "h" : op === "C" ? `${pt(v[0], v[1])} ${pt(v[2], v[3])} ${pt(v[4], v[5])} c`
                                              : `${pt(v[0], v[1])} ${op === "M" ? "m" : "l"}`).join(" ");
  const rgb = v => v.map(x => x.toFixed(3)).join(" ");
  const ops = `q /KatipMark gs ${rgb(mark.colors.top)} rg ${path(mark.top)} f ${rgb(mark.colors.bottom)} rg ${path(mark.bottom)} f ` +
              `${rgb(mark.colors.k)} RG ${(mark.stroke * k * Math.hypot(a, b)).toFixed(2)} w 1 J 1 j ${path(mark.k)} S Q\n`;
  const old = obj.get("Contents"), arr = pdf.newArray();
  arr.push(pdf.addStream(new TextEncoder().encode("q\n"), {}));
  if (old.isArray()) old.forEach(v => arr.push(v)); else if (!old.isNull()) arr.push(old);
  arr.push(pdf.addStream(new TextEncoder().encode("Q\n" + ops), {}));
  obj.put("Contents", arr);
}

// ---- true PDF redaction: remove glyphs + blank image pixels, then paint the mask colour,
// add the optional watermark line + link, and scrub metadata.
// opts.color: [r, g, b] in 0..1 (default black); opts.watermark: { text, url } or null;
// opts.mark: MARK from brand.js to stamp the Katip mark in the centre of every page, or null
export function redactPdf(mupdf, doc, spans, opts = {}) {
  const pdf = doc._doc, PAD = 1, color = opts.color ?? [0, 0, 0], wm = opts.watermark;
  const per = new Map();
  for (const sp of spans) if (sp.page != null) per.set(sp.page, [...(per.get(sp.page) ?? []), ...sp.boxes]);
  // OCR pages: close small gaps between boxes on one line, so letters between two masked words
  // of a handwritten name do not stay readable
  for (const [pno, boxes] of per) if (doc.pages?.[pno]?.ocr) per.set(pno, closeGaps(boxes));
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
  // Photographed or scanned pages: replace the page by its cleaned image (sheet only, shadows flattened,
  // show-through from the back of the sheet wiped). Ink from the other side can carry the names and
  // numbers we just masked on that page, mirrored and faint but readable with a contrast tweak.
  if (opts.cleanScans !== false) for (const p of doc.pages ?? []) if (p.ocr) cleanScanPage(mupdf, pdf, p.number, per.get(p.number) ?? [], color);
  if (opts.mark) for (let i = 0; i < pdf.countPages(); i++) stampMark(mupdf, pdf, pdf.loadPage(i), opts.mark);
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
    pdf.setMetaData(k, k === "info:Producer" || k === "info:Creator" ? "katip-mask" : "");
  try { pdf.getTrailer().get("Root").delete("Metadata"); } catch { /* no XMP */ }
  return pdf.saveToBuffer("garbage=4,compress,clean").asUint8Array().slice();
}

export function closeGaps(boxes) {
  const out = boxes.map(b => [...b]).sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  for (let merged = true; merged;) {
    merged = false;
    for (let i = 0; i < out.length && !merged; i++) for (let j = i + 1; j < out.length && !merged; j++) {
      const a = out[i], b = out[j], h = Math.min(a[3] - a[1], b[3] - b[1]);
      const vo = Math.min(a[3], b[3]) - Math.max(a[1], b[1]), gap = Math.max(a[0], b[0]) - Math.min(a[2], b[2]);
      if (vo > 0.5 * h && gap < 1.5 * h) {
        out[i] = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])];
        out.splice(j, 1); merged = true;
      }
    }
  }
  return out;
}

function cleanScanPage(mupdf, pdf, i, boxes, color) {
  const page = pdf.loadPage(i);
  if (page.getObject().get("Rotate")?.asNumber?.()) return;  // rotated pages keep the plain redaction
  const [x0, y0, x1, y1] = page.getBounds(), w = x1 - x0, h = y1 - y0, s = ocrScale(w, h);
  const pix = page.toPixmap(mupdf.Matrix.scale(s, s), mupdf.ColorSpace.DeviceRGB, false);
  if (!prepareScan(pix)) return;
  const res = pdf.newDictionary(), xo = pdf.newDictionary();
  xo.put("Im0", pdf.addImage(new mupdf.Image(pix)));
  res.put("XObject", xo);
  const np = pdf.addPage([0, 0, w, h], 0, res, `q ${w.toFixed(3)} 0 0 ${h.toFixed(3)} 0 0 cm /Im0 Do Q`);
  pdf.insertPage(i, np); pdf.deletePage(i + 1);
  // the masks went grey in the clean-up; paint them again, full colour, on top
  if (boxes.length) paintBoxes(mupdf, pdf, pdf.loadPage(i), boxes.map(([a, b, c, d]) => [a - x0 - 1, b - y0 - 1, c - x0 + 1, d - y0 + 1]), color);
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
export function pdfPagePngs(mupdf, bytes, pages) {
  const d = mupdf.Document.openDocument(bytes, "application/pdf");
  return pages.map(i => {
    const page = d.loadPage(i), [x0, y0, x1, y1] = page.getBounds(), s = ocrScale(x1 - x0, y1 - y0);
    const pix = page.toPixmap(mupdf.Matrix.scale(s, s), mupdf.ColorSpace.DeviceRGB, false);
    prepareScan(pix);
    return pix.asPNG().slice();
  });
}

// ---- scans and phone photos: what the OCR sees
// Render at 300 DPI for normal page sizes, but never wider than an A4 page at 300 DPI (3508 px on the
// long side): a phone photo wrapped in a PDF is often a 1152x2048 pt page holding a 72 ppi image, and
// 300 DPI would upscale it 4x, which makes Tesseract read handwriting and the wood grain under the paper
// as text.
const MAX_OCR_SIDE = 3508;
export function ocrScale(width, height) {
  return Math.min(OCR_DPI / 72, MAX_OCR_SIDE / Math.max(1, width, height));
}

// In place, on an RGB pixmap: (1) find the sheet of paper (bright, unsaturated) and whiten everything
// around it, so the floor or desk is not read as words; (2) divide by a blurred copy to flatten shadows
// and uneven light; (3) wipe faint grey (text showing through from the back of the sheet). Clean flatbed
// scans come out almost unchanged. Returns what it did, for the report.
export function prepareScan(pix) {
  const w = pix.getWidth(), h = pix.getHeight(), stride = pix.getStride(), n = pix.getNumberOfComponents();
  if (n < 3 || w < 64 || h < 64) return null;
  const px = pix.getPixels(), g = new Float32Array(w * h), paper = new Uint8Array(w * h), colour = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const o = y * stride + x * n, r = px[o], gg = px[o + 1], b = px[o + 2];
    const v = 0.299 * r + 0.587 * gg + 0.114 * b, sat = Math.max(r, gg, b) - Math.min(r, gg, b);
    g[y * w + x] = v;
    paper[y * w + x] = v > 165 && sat < 45 ? 1 : 0;
    colour[y * w + x] = Math.max(0, Math.min(255, 128 + b - r));  // blueness: ballpoint ink is bluer than printed black
  }
  // paper box: rows and columns that are at least 30% paper
  const rowHit = new Array(h).fill(0), colHit = new Array(w).fill(0);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (paper[y * w + x]) { rowHit[y]++; colHit[x]++; }
  const rows = rowHit.map((c, y) => c > 0.3 * w ? y : -1).filter(y => y >= 0);
  const cols = colHit.map((c, x) => c > 0.3 * h ? x : -1).filter(x => x >= 0);
  let box = [0, 0, w, h];
  if (rows.length && cols.length) {
    const b = [cols[0], rows[0], cols.at(-1) + 1, rows.at(-1) + 1];
    if ((b[2] - b[0]) * (b[3] - b[1]) >= 0.3 * w * h) box = b;  // a small "paper" is a guess gone wrong
  }
  // background estimate: box blur (integral image), radius ~2% of the long side
  const R = Math.max(8, Math.round(Math.max(w, h) / 50)), I = new Float64Array((w + 1) * (h + 1));
  for (let y = 0; y < h; y++) { let row = 0; for (let x = 0; x < w; x++) { row += g[y * w + x]; I[(y + 1) * (w + 1) + x + 1] = I[y * (w + 1) + x + 1] + row; } }
  let flattened = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let v = 255;
    if (x >= box[0] && x < box[2] && y >= box[1] && y < box[3]) {
      const ya = Math.max(0, y - R), yb = Math.min(h, y + R + 1), xa = Math.max(0, x - R), xb = Math.min(w, x + R + 1);
      const bg = (I[yb * (w + 1) + xb] - I[ya * (w + 1) + xb] - I[yb * (w + 1) + xa] + I[ya * (w + 1) + xa]) / ((yb - ya) * (xb - xa));
      v = Math.min(255, (g[y * w + x] / Math.max(1, bg)) * 255);
      if (v > 200) v = 255; else flattened++;
    }
    const o = y * stride + x * n;
    px[o] = px[o + 1] = px[o + 2] = v;
  }
  return { paper: box, cropped: box[2] - box[0] < w || box[3] - box[1] < h, ink: flattened / (w * h), colour };
}
