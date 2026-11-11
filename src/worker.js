// Runs Pyodide (Turkish recognizers), MuPDF (PDF) and optional NER off the UI thread.
// Documents arrive by postMessage and leave the same way; nothing here does network I/O
// except loading this site's own runtime and model files.
import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";
import * as mupdf from "./vendor/mupdf/dist/mupdf.js";
import * as E from "./engine.js";
import { loadNer, runNer } from "./ner.js";

let py, current = null, ocrSeq = 0, T = null;
const pendingOcr = new Map();
const progress = msg => postMessage({ type: "progress", msg });
const here = p => new URL(p, import.meta.url).href;

function ocrWith(lang) {
  return png => new Promise((resolve, reject) => {
    const id = ++ocrSeq; pendingOcr.set(id, { resolve, reject });
    postMessage({ type: "ocr", id, png, lang }, [png.buffer]);
  });
}

async function boot() {
  const t0 = performance.now();
  py = await loadPyodide({ indexURL: here("./vendor/pyodide/") });
  py.unpackArchive(await (await fetch(here("./katip_py.zip"))).arrayBuffer(), "zip", { extractDir: "/home/pyodide" });
  py.runPython("import sys; sys.path.insert(0,'/home/pyodide'); import local_detect, local_formats; local_detect.detect('Ahmet Yılmaz')");
  postMessage({ type: "ready", ms: Math.round(performance.now() - t0) });
}

function renderPages(bytes, max = 12, scale = 1.25) {
  const d = mupdf.Document.openDocument(bytes, "application/pdf"), out = [];
  for (let i = 0; i < Math.min(d.countPages(), max); i++)
    out.push(d.loadPage(i).toPixmap(mupdf.Matrix.scale(scale, scale), mupdf.ColorSpace.DeviceRGB, false).asPNG().slice());
  return out;
}

async function detectWithModel(text, s) {
  const t0 = performance.now();
  let extra = [];
  if (s.ner) {
    T ??= await import("./vendor/transformers/transformers.min.js");
    const ner = await loadNer(T, s.ner, new URL("./models/", import.meta.url).pathname, { mjs: here("./vendor/ort/ort-wasm-simd-threaded.asyncify.mjs"), wasm: here("./vendor/ort/ort-wasm-simd-threaded.asyncify.wasm") }, progress, s.nerDtype ?? "q8");
    progress("NER çalışıyor");
    extra = await runNer(T, ner, text, { minScore: s.threshold });
  }
  const tn = performance.now();
  const spans = E.pyDetect(py, text, { threshold: s.threshold, entities: s.entities, mask: s.mask ?? [], allow: s.allow ?? [], extra });
  return { spans, nerMs: Math.round(tn - t0), rulesMs: Math.round(performance.now() - tn), nerCount: extra.length };
}

async function analyze({ name, bytes, settings }) {
  const t0 = performance.now(), kind = E.kindOf(name), ocr = ocrWith(settings.ocrLang);
  let doc;
  if (kind === "pdf") doc = await E.parsePdf(mupdf, bytes, ocr, { onProgress: progress });
  else if (kind === "image") { progress("OCR"); doc = await E.parseImage(bytes.slice(), ocr); }
  else doc = { kind, text: E.pyExtract(py, kind, bytes) };
  const parseMs = Math.round(performance.now() - t0);
  progress("Kişisel veriler aranıyor");
  const r = await detectWithModel(doc.text, settings);
  current = { name, kind, bytes, doc };
  const previews = kind === "pdf" ? renderPages(bytes) : [];
  postMessage({ type: "analyzed", kind, text: doc.text, spans: r.spans, ocrPages: doc.ocrPages ?? 0, pages: doc.pages?.length ?? 1,
                timing: { parse: parseMs, ner: r.nerMs, rules: r.rulesMs }, nerCount: r.nerCount, previews }, previews.map(p => p.buffer));
}

async function redetect({ settings }) {
  const r = await detectWithModel(current.doc.text, settings);
  postMessage({ type: "redetected", spans: r.spans, timing: { ner: r.nerMs, rules: r.rulesMs }, nerCount: r.nerCount });
}

const mimeOf = n => ({ jpg: "image/jpeg", jpeg: "image/jpeg", tif: "image/tiff", tiff: "image/tiff", bmp: "image/bmp", webp: "image/webp" })[n.toLowerCase().split(".").pop()] ?? "image/png";
const MIME = { docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", udf: "application/zip", txt: "text/plain;charset=utf-8", pdf: "application/pdf", image: "image/png" };

async function redact({ spans, style, verifyOcr, ocrLang }) {
  const { name, kind, bytes, doc } = current, t0 = performance.now(), ocr = ocrWith(ocrLang);
  progress("Maskeleniyor");
  let out, outText = "", unchecked = false, previews = [];
  if (kind === "pdf") {
    E.attachBoxes(doc, spans);
    doc._doc = mupdf.Document.openDocument(bytes, "application/pdf");
    out = E.redactPdf(mupdf, doc, spans);
    outText = E.pdfText(mupdf, out);
    const scanned = doc.pages.filter(p => p.ocr).map(p => p.number);
    if (scanned.length && verifyOcr) {
      progress("Taranmış sayfalar tekrar okunuyor (sızıntı kontrolü)");
      for (const png of E.pdfPagePngs(mupdf, out, scanned)) outText += "\n" + (await ocr(png)).map(l => l.map(w => w.text).join(" ")).join("\n");
    } else unchecked = scanned.length > 0;
    previews = renderPages(out);
  } else if (kind === "image") {
    E.attachBoxes(doc, spans);
    out = E.redactImage(mupdf, bytes, spans, mimeOf(name));
    if (verifyOcr) { progress("Çıktı tekrar okunuyor (sızıntı kontrolü)"); outText = (await ocr(out.slice())).map(l => l.map(w => w.text).join(" ")).join("\n"); }
    else unchecked = true;
  } else {
    out = E.pyRedact(py, kind, bytes, spans, style);
    outText = E.pyExtract(py, kind, out);
  }
  const leaks = E.pyLeaks(py, outText, spans);
  const ext = kind === "image" ? "png" : name.split(".").pop();
  const outName = name.replace(/\.[^.]+$/, "") + ".maskeli." + ext;
  postMessage({ type: "redacted", out, mime: MIME[kind], outName, outText, leaks, unchecked, previews, ms: Math.round(performance.now() - t0) },
              [out.buffer, ...previews.map(p => p.buffer)]);
}

function maskedText({ spans }) {
  const r = E.pyRedact(py, "txt", new TextEncoder().encode(current.doc.text), spans, "label");
  postMessage({ type: "maskedText", text: new TextDecoder().decode(r) });
}
function original() { postMessage({ type: "original", bytes: current.bytes.slice(), name: current.name }); }
function forget() { current = null; postMessage({ type: "forgotten" }); }

onmessage = async ({ data }) => {
  try {
    if (data.type === "ocrResult") { const p = pendingOcr.get(data.id); pendingOcr.delete(data.id); data.error ? p.reject(new Error(data.error)) : p.resolve(data.lines); return; }
    await ({ analyze, redetect, redact, maskedText, original, forget })[data.type](data);
  } catch (e) { postMessage({ type: "error", msg: String(e?.message ?? e), stack: String(e?.stack ?? "").slice(0, 600) }); }
};
boot().catch(e => postMessage({ type: "error", msg: "Başlatılamadı: " + e }));
