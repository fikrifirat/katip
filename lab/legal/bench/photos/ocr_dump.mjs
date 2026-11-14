// KVKK-Bench photo track: run Katip's "Otomatik" OCR (PaddleOCR on handwriting/photos, else Tesseract) once
// over the photo set and save what every system needs, so the bench never re-runs OCR:
//   node lab/legal/bench/photos/ocr_dump.mjs DIR > lab/legal/bench/photos/ocr.jsonl
// One line per photo: OCR text, words with offsets and boxes (PDF points), pen-ink blobs, and the
// image-side masks Katip adds from ink alone (engine.unreadSpans; used only by Katip rows).
import * as mupdf from "mupdf";
import { createWorker } from "tesseract.js";
import fs from "fs";
const root = new URL("../../../../", import.meta.url).pathname;
const ort = await import("onnxruntime-web/wasm");
const E = await import(root + "src/engine.js");
const { createPaddleOcr, decodeImage } = await import(root + "src/paddle_ocr.js");

const dir = process.argv[2];
ort.env.wasm.numThreads = 1; ort.env.logLevel = "error";
const pd = root + "docs/vendor/paddleocr";
const pocr = await createPaddleOcr(ort, { det: fs.readFileSync(`${pd}/det/inference.onnx`), rec: fs.readFileSync(`${pd}/rec/inference.onnx`),
  dict: JSON.parse(fs.readFileSync(`${pd}/rec/dict.json`)), detLimit: 1600 });
const paddle = Object.assign(png => pocr.recognize(decodeImage(mupdf, Buffer.from(png))), { engine: "paddle" });
const tw = await createWorker("tur", 1, { langPath: root + "node_modules/@tesseract.js-data/tur/4.0.0_best_int", gzip: true, cacheMethod: "none" });
async function tess(png) {
  const { data } = await tw.recognize(Buffer.from(png), {}, { blocks: true });
  const lines = [];
  for (const b of data.blocks ?? []) for (const p of b.paragraphs) for (const l of p.lines)
    lines.push(l.words.filter(w => w.text.trim() && w.confidence >= 0).map(w => ({ text: w.text, bbox: [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1] })));
  return lines.filter(l => l.length);
}
const ocr = Object.assign(png => tess(png), { forPage: pg => pg.handwriting ? paddle : tess });
const r2 = a => a.map(v => Math.round(v * 100) / 100);
for (const f of fs.readdirSync(dir).filter(f => f.endsWith(".pdf")).sort()) {
  const t0 = performance.now();
  const doc = await E.parsePdf(mupdf, new Uint8Array(fs.readFileSync(`${dir}/${f}`)), ocr);
  const ms = performance.now() - t0;
  const ink = E.unreadSpans(doc).filter(u => !u.flag_only);   // also sets page.lineH
  process.stdout.write(JSON.stringify({
    id: f.replace(".pdf", ""), text: doc.text, ocr_ms: Math.round(ms),
    pages: doc.pages.map(p => ({ number: p.number, width: p.width, height: p.height, start: p.start, end: p.end, ocr: p.ocr, engine: p.engine,
      lineH: p.lineH, pen: (p.pen ?? []).map(r2), words: p.words.map(w => ({ text: w.text, start: w.start, end: w.end, bbox: r2(w.bbox) })) })),
    ink_masks: ink.map(u => ({ page: u.page, recognizer: u.recognizer, box: r2(u.boxes[0]) })),
  }) + "\n");
  process.stderr.write(".");
}
await tw.terminate(); process.exit(0);
