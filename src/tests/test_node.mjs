// End-to-end in Node: every format in eval/blind -> redact -> leak check against gold values.
import { loadPyodide } from "../node_modules/pyodide/pyodide.mjs";
import * as mupdf from "mupdf";
import { createWorker } from "tesseract.js";
import fs from "fs";
import * as E from "../engine.js";

const py = await loadPyodide();
py.unpackArchive(new Uint8Array(fs.readFileSync(new URL("../dist/katip_py.zip", import.meta.url))), "zip", { extractDir: "/home/pyodide" });
py.runPython("import sys; sys.path.insert(0,'/home/pyodide')");
let tw = null;
async function ocr(png) {
  tw ??= await createWorker("tur", 1, { langPath: new URL("../node_modules/@tesseract.js-data/tur/4.0.0_best_int", import.meta.url).pathname, gzip: true, cacheMethod: "none" });
  const { data } = await tw.recognize(Buffer.from(png), {}, { blocks: true });
  const lines = [];
  for (const b of data.blocks ?? []) for (const p of b.paragraphs) for (const l of p.lines)
    lines.push(l.words.filter(w => w.text.trim() && w.confidence >= 0).map(w => ({ text: w.text, bbox: [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1] })));
  return lines.filter(l => l.length);
}
const dir = process.argv[2], only = process.argv[3] ? new RegExp(process.argv[3]) : null;
const files = fs.readdirSync(dir).filter(f => !f.endsWith(".json") && (!only || only.test(f))).sort();
const stats = {};
for (const f of files) {
  const t0 = performance.now();
  const kind = E.kindOf(f), bytes = new Uint8Array(fs.readFileSync(`${dir}/${f}`));
  const goldFile = `${dir}/${f.split(".")[0]}.gold.json`;
  const gold = fs.existsSync(goldFile) ? JSON.parse(fs.readFileSync(goldFile)) : null;
  let doc, outBytes, outText;
  if (kind === "pdf") {
    doc = await E.parsePdf(mupdf, bytes, ocr);
  } else if (kind === "image") {
    doc = await E.parseImage(bytes, ocr);
  } else doc = { kind, text: E.pyExtract(py, kind, bytes) };
  const spans = E.pyDetect(py, doc.text).filter(s => !s.flag_only);
  if (kind === "pdf") { E.attachBoxes(doc, spans); outBytes = E.redactPdf(mupdf, doc, spans); outText = E.pdfText(mupdf, outBytes);
    if (doc.ocrPages) for (const png of E.pdfPagePngs(mupdf, outBytes, doc.pages.filter(p => p.ocr).map(p => p.number)))
      outText += (await ocr(png)).map(l => l.map(w => w.text).join(" ")).join("\n"); }
  else if (kind === "image") { E.attachBoxes(doc, spans); outBytes = E.redactImage(mupdf, bytes, spans); outText = (await ocr(outBytes)).map(l => l.map(w => w.text).join(" ")).join("\n"); }
  else { outBytes = E.pyRedact(py, kind, bytes, spans, "box"); outText = E.pyExtract(py, kind === "txt" ? "txt" : kind, outBytes); }
  const sq = s => s.replace(/\s+/g, "").toLocaleLowerCase("tr");
  // gold leak: gold values (by the document's author) still readable in the output
  let goldVals = gold ? (gold.entities ?? gold.spans ?? gold).map(g => g.text ?? g.value).filter(Boolean) : [];
  const leaks = outText == null ? [] : goldVals.filter(v => sq(v).length >= 4 && sq(outText).includes(sq(v)));
  const covered = v => spans.some(sp => sq(sp.text).includes(sq(v)) || sq(v).includes(sq(sp.text)) && sq(sp.text).length >= 4);
  const missed = goldVals.filter(v => !covered(v));
  const key = f.endsWith(".scan.pdf") ? "scan.pdf" : kind;
  const s = stats[key] ??= { docs: 0, gold: 0, leaked: 0, missed: 0, ms: 0 };
  s.missed += missed.length;
  s.docs++; s.gold += goldVals.length; s.leaked += leaks.length; s.ms += performance.now() - t0;
  if (leaks.length) console.log(f, "LEAK", leaks.slice(0, 5));
  if (outBytes && process.env.SAVE) fs.mkdirSync(process.env.SAVE, { recursive: true });
  if (outBytes && process.env.SAVE) fs.writeFileSync(`${process.env.SAVE}/${f}`, outBytes);
}
for (const [k, s] of Object.entries(stats)) console.log(k.padEnd(9), `docs ${s.docs}  gold values ${s.gold}  not detected ${s.missed}  still readable after redaction ${s.leaked} (${(100 * s.leaked / Math.max(1, s.gold)).toFixed(1)}%)  avg ${(s.ms / s.docs) | 0} ms/doc`);
await tw?.terminate(); process.exit(0);
