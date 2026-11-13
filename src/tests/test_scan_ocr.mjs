// Printed scans and page images (eval/blind *.scan.pdf, *.png) through the browser pipeline with a chosen
// OCR, to check that the photo/handwriting OCR does not do worse on ordinary printed scans.
//   node src/tests/test_scan_ocr.mjs DIR [--ocr tesseract|paddle|auto]
// Scores: gold values not detected, and gold values still readable after redaction. The leak check
// re-reads the masked page with Tesseract for both engines, so the reader is the same.
import { loadPyodide } from "../../node_modules/pyodide/pyodide.mjs";
import * as mupdf from "mupdf";
import { createWorker } from "tesseract.js";
import fs from "fs";
import * as E from "../engine.js";

const args = process.argv.slice(2), dir = args[0];
const engine = args.includes("--ocr") ? args[args.indexOf("--ocr") + 1] : "tesseract";
const here = new URL("../../", import.meta.url).pathname;
const py = await loadPyodide();
py.unpackArchive(new Uint8Array(fs.readFileSync(process.env.KATIP_PY_ZIP ?? here + "docs/katip_py.zip")), "zip", { extractDir: "/home/pyodide" });
py.runPython("import sys; sys.path.insert(0,'/home/pyodide')");
const tw = await createWorker("tur", 1, { langPath: here + "node_modules/@tesseract.js-data/tur/4.0.0_best_int", gzip: true, cacheMethod: "none" });
async function tess(png) {
  const { data } = await tw.recognize(Buffer.from(png), {}, { blocks: true });
  const lines = [];
  for (const b of data.blocks ?? []) for (const p of b.paragraphs) for (const l of p.lines)
    lines.push(l.words.filter(w => w.text.trim() && w.confidence >= 0).map(w => ({ text: w.text, bbox: [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1] })));
  return lines.filter(l => l.length);
}
let ocr = tess;
if (engine !== "tesseract") {
  const ort = await import("onnxruntime-web/wasm");
  ort.env.wasm.numThreads = 1; ort.env.logLevel = "error";
  const { createPaddleOcr, decodeImage } = await import("../paddle_ocr.js");
  const pd = process.env.PADDLE_DIR ?? here + "docs/vendor/paddleocr";
  const p = await createPaddleOcr(ort, { det: fs.readFileSync(`${pd}/det/inference.onnx`), rec: fs.readFileSync(`${pd}/rec/inference.onnx`), dict: JSON.parse(fs.readFileSync(`${pd}/rec/dict.json`)) });
  const paddle = Object.assign(png => p.recognize(decodeImage(mupdf, Buffer.from(png))), { engine: "paddle" });
  ocr = engine === "auto" ? Object.assign(png => tess(png), { forPage: pg => (pg.handwriting ? paddle : tess) }) : paddle;
}
const sq = s => s.replace(/\s+/g, "").toLocaleLowerCase("tr");
const files = fs.readdirSync(dir).filter(f => f.endsWith(".scan.pdf") || f.endsWith(".png")).sort();
const st = {};
for (const f of files) {
  const gold = JSON.parse(fs.readFileSync(`${dir}/${f.split(".")[0]}.gold.json`)).map(g => g.text).filter(v => v && sq(v).length >= 4);
  const bytes = new Uint8Array(fs.readFileSync(`${dir}/${f}`)), pdf = f.endsWith(".pdf"), t0 = performance.now();
  const doc = pdf ? await E.parsePdf(mupdf, bytes, ocr) : await E.parseImage(bytes, ocr, null, mupdf);
  const ms = performance.now() - t0;
  const spans = E.pyDetect(py, doc.text, { ocr_ranges: doc.pages.filter(p => p.ocr).map(p => [p.start, p.end]), address_detail: "full" }).filter(s => !s.flag_only);
  E.attachBoxes(doc, spans); spans.push(...E.unreadSpans(doc).filter(u => !u.flag_only));
  let outText = "";
  if (pdf) { const out = E.redactPdf(mupdf, doc, spans); for (const png of E.pdfPagePngs(mupdf, out, doc.pages.map(p => p.number))) outText += (await tess(png)).map(l => l.map(w => w.text).join(" ")).join("\n"); }
  else outText = (await tess(E.redactImage(mupdf, bytes, spans))).map(l => l.map(w => w.text).join(" ")).join("\n");
  const covered = v => spans.some(sp => sp.text && (sq(sp.text).includes(sq(v)) || (sq(v).includes(sq(sp.text)) && sq(sp.text).length >= 4)));
  const leaks = gold.filter(v => sq(outText).includes(sq(v))), missed = gold.filter(v => !covered(v));
  const s = st[pdf ? "scan.pdf" : "png"] ??= { docs: 0, gold: 0, missed: 0, leaked: 0, ms: 0 };
  s.paddle = (s.paddle ?? 0) + doc.pages.filter(p => p.engine === "paddle").length;
  s.docs++; s.gold += gold.length; s.missed += missed.length; s.leaked += leaks.length; s.ms += ms;
  if (leaks.length) console.log(f, "still readable:", leaks.join(" | "));
}
for (const [k, s] of Object.entries(st)) console.log(`${engine} ${k.padEnd(9)} docs ${s.docs}  gold ${s.gold}  not detected ${s.missed}  readable after masking ${s.leaked}  OCR ${(s.ms / s.docs / 1000).toFixed(1)} s/doc  pages read by PaddleOCR ${s.paddle}`);
await tw.terminate(); process.exit(0);
