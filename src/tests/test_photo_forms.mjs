// Photographed hand-filled forms (lab/photo_forms/make_photo_forms.py): run the browser pipeline
// (OCR -> detect -> boxes) and score by geometry, no OCR in the scoring:
//   leaked       a gold value whose box is less than 70% covered by masks
//   over-masked  a street/mahalle name that must stay readable and is more than 30% covered
//   node src/tests/test_photo_forms.mjs DIR [--address full|street] [--ner]
import { loadPyodide } from "../../node_modules/pyodide/pyodide.mjs";
import * as mupdf from "mupdf";
import { createWorker } from "tesseract.js";
import fs from "fs";
import * as E from "../engine.js";

const args = process.argv.slice(2), dir = args[0];
const address = args.includes("--address") ? args[args.indexOf("--address") + 1] : "street";
const zip = process.env.KATIP_PY_ZIP ?? new URL("../../docs/katip_py.zip", import.meta.url).pathname;
const py = await loadPyodide();
py.unpackArchive(new Uint8Array(fs.readFileSync(zip)), "zip", { extractDir: "/home/pyodide" });
py.runPython("import sys; sys.path.insert(0,'/home/pyodide')");
const here = new URL("../../", import.meta.url).pathname;
const tw = await createWorker("tur", 1, { langPath: here + "node_modules/@tesseract.js-data/tur/4.0.0_best_int", gzip: true, cacheMethod: "none" });
async function ocr(png) {
  const { data } = await tw.recognize(Buffer.from(png), {}, { blocks: true });
  const lines = [];
  for (const b of data.blocks ?? []) for (const p of b.paragraphs) for (const l of p.lines)
    lines.push(l.words.filter(w => w.text.trim() && w.confidence >= 0).map(w => ({ text: w.text, bbox: [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1] })));
  return lines.filter(l => l.length);
}
function coverage(box, masks) {
  const [x0, y0, x1, y1] = box, N = 24;
  let hit = 0;
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
    const x = x0 + (i + 0.5) * (x1 - x0) / N, y = y0 + (j + 0.5) * (y1 - y0) / N;
    if (masks.some(([a, b, c, d]) => x >= a - 1 && x <= c + 1 && y >= b - 1 && y <= d + 1)) hit++;
  }
  return hit / (N * N);
}
const files = fs.readdirSync(dir).filter(f => f.endsWith(".pdf")).sort();
const tot = {}, over = { n: 0, bad: 0 }, rows = [];
let falseMasks = 0;
for (const f of files) {
  const gold = JSON.parse(fs.readFileSync(`${dir}/${f.replace(".pdf", ".gold.json")}`));
  const doc = await E.parsePdf(mupdf, new Uint8Array(fs.readFileSync(`${dir}/${f}`)), ocr);
  const spans = E.pyDetect(py, doc.text, { threshold: 0.7, ocr_ranges: doc.pages.filter(p => p.ocr).map(p => [p.start, p.end]), address_detail: address })
    .filter(s => !s.flag_only);
  E.attachBoxes(doc, spans);
  if (E.unreadSpans) spans.push(...E.unreadSpans(doc).filter(u => !u.flag_only));
  const masks = spans.filter(s => s.page === 0).flatMap(s => s.boxes ?? []);
  const leaks = [];
  for (const g of gold.entities) {
    const t = tot[g.entity_type + (g.part === "signature block" ? " (signature block)" : "")] ??= { n: 0, leaked: 0 };
    t.n++;
    if (coverage(g.box, masks) < 0.7) { t.leaked++; leaks.push(g.entity_type); }
  }
  for (const v of gold.visible) { over.n++; if (coverage(v.box, masks) > 0.3) over.bad++; }
  const goldBoxes = [...gold.entities, ...gold.visible].map(g => g.box);
  falseMasks += masks.filter(m => !goldBoxes.some(b => m[0] < b[2] && m[2] > b[0] && m[1] < b[3] && m[3] > b[1])).length;
  rows.push(`${f}  leaked: ${leaks.join(", ") || "-"}`);
}
console.log(rows.join("\n"));
for (const [k, t] of Object.entries(tot)) console.log(`${k.padEnd(26)} ${t.n - t.leaked}/${t.n} masked, ${t.leaked} leaked`);
console.log(`street names kept readable  ${over.n - over.bad}/${over.n}`);
console.log(`masks on nothing personal   ${falseMasks} (${(falseMasks / files.length).toFixed(1)} per page)`);
await tw.terminate(); process.exit(0);
