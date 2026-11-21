// Katip iOS engine bridge. Runs the katip-mask JS SDK (the same engine as the web app, the Python package and
// Katip Kalkan) inside an offline WKWebView. Swift calls window.katip.* with callAsyncJavaScript.
// Nothing here touches the network: models and the ONNX runtime are served from the app bundle by the
// katip-engine:// scheme handler, and the page's CSP allows no other origin.
import * as ort from "onnxruntime-web/wasm";
import { letter, letterInfo, letterPrompt } from "./letter.js";
import { Masker, MODELS, loadModelFromFiles, restore as restoreText, LeakError, PROFILES, LABELS_TR, VERSION, ENGINE_SHA256 } from "katip-mask";

ort.env.wasm.numThreads = 1;          // no SharedArrayBuffer without cross-origin isolation
ort.env.wasm.proxy = false;
ort.env.wasm.wasmPaths = new URL("ort/", location.href).href;

const models = new Map();
function nameModel(model) {
  if (!model) return Promise.resolve(null);
  if (!models.has(model)) {
    // The app's scheme handler serves only files whose SHA-256 matches sdk/spec/models.json (checked in Swift),
    // because WebCrypto may be missing in a custom-scheme page.
    const info = MODELS[model];
    if (!info) return Promise.reject(new Error(`unknown model ${model}`));
    const get = async f => {
      const r = await fetch(`models/${model}/${f}`);
      if (!r.ok) throw new Error(`${info.name}: ${f}: HTTP ${r.status}`);
      return new Uint8Array(await r.arrayBuffer());
    };
    const p = (async () => {
      const [config, tokenizer, onnx] = await Promise.all(["config.json", "tokenizer.json", "onnx/model_quantized.onnx"].map(get));
      return loadModelFromFiles(`${model}@${info.revision.slice(0, 7)}`, { config, tokenizer, onnx }, ort, info.trust);
    })();
    models.set(model, p);
    p.catch(() => models.delete(model));
  }
  return models.get(model);
}

async function mask({ text, profile = "ai", model = "mini", allow = [], deny = [], ocr = false }) {
  const m = new Masker({ profile, model: await nameModel(model), allow, deny });
  const t0 = performance.now();
  try {
    const r = await m.mask(text, ocr ? { ocrRanges: [[0, text.length]] } : {});
    return {
      ok: true, text: r.text, mapping: r.mapping, model: r.model, ms: Math.round(performance.now() - t0),
      spans: r.spans.map(s => ({ type: s.entityType, start: s.start, end: s.end, text: s.text, score: s.score, recognizer: s.recognizer })),
    };
  } catch (e) {
    if (e instanceof LeakError) return { ok: false, leak: true, kinds: e.kinds, lines: e.lines, error: e.message };
    throw e;
  }
}

// ---- .docx / .udf text, with a small ZIP reader (stored + deflate entries, via DecompressionStream) ----
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const u16 = (d, o) => d[o] | (d[o + 1] << 8);
const u32 = (d, o) => (d[o] | (d[o + 1] << 8) | (d[o + 2] << 16) | (d[o + 3] << 24)) >>> 0;

async function unzip(data, want) {
  let eocd = -1;
  for (let i = data.length - 22; i >= Math.max(0, data.length - 65557); i--) if (u32(data, i) === 0x06054b50) { eocd = i; break; }
  if (eocd < 0) throw new Error("not a ZIP file");
  const n = u16(data, eocd + 10);
  let p = u32(data, eocd + 16);
  const out = {};
  for (let k = 0; k < n; k++) {
    if (u32(data, p) !== 0x02014b50) throw new Error("bad ZIP directory");
    const method = u16(data, p + 10), csize = u32(data, p + 20), nlen = u16(data, p + 28), xlen = u16(data, p + 30), clen = u16(data, p + 32);
    const local = u32(data, p + 42);
    const name = new TextDecoder().decode(data.subarray(p + 46, p + 46 + nlen));
    p += 46 + nlen + xlen + clen;
    if (!want(name)) continue;
    const start = local + 30 + u16(data, local + 26) + u16(data, local + 28);
    const raw = data.subarray(start, start + csize);
    if (method === 0) out[name] = raw;
    else if (method === 8) out[name] = new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("deflate-raw"))).arrayBuffer());
    else throw new Error(`unsupported ZIP method ${method}`);
  }
  return out;
}

const unescapeXml = s => s.replace(/&(lt|gt|amp|quot|apos|#\d+|#x[0-9a-f]+);/gi, (_, e) =>
  ({ lt: "<", gt: ">", amp: "&", quot: '"', apos: "'" })[e.toLowerCase()] ??
  String.fromCodePoint(e[1].toLowerCase() === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10)));

// Same walk as src/py/local_formats.py _docx_scan: text runs, deleted text, paragraph ends, tabs, breaks.
const DOCX_PARTS = /^word\/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$/;
const TOKEN = /<w:(t|delText)\b([^>]*?)(?:\/>|>([\s\S]*?)<\/w:\1>)|<\/w:p>|<w:tab\b[^>]*\/>|<w:br\b[^>]*\/>/g;

async function extract({ base64, kind }) {
  const data = b64(base64);
  const dec = new TextDecoder("utf-8");
  if (kind === "udf") {
    const files = await unzip(data, n => n === "content.xml");
    const xml = dec.decode(files["content.xml"] ?? new Uint8Array());
    const m = /<content>\s*<!\[CDATA\[([\s\S]*?)\]\]>\s*<\/content>/.exec(xml);
    if (!m) throw new Error("UDF content.xml has no <content> block");
    return { text: m[1] };
  }
  if (kind === "docx") {
    const files = await unzip(data, n => DOCX_PARTS.test(n));
    const names = Object.keys(files).sort((a, b) => (a !== "word/document.xml") - (b !== "word/document.xml") || (a < b ? -1 : a > b));
    let text = "";
    for (const name of names) {
      for (const m of dec.decode(files[name]).matchAll(TOKEN)) {
        const tok = m[0];
        if (tok === "</w:p>") text += "\n";
        else if (tok.startsWith("<w:tab")) text += " ";
        else if (tok.startsWith("<w:br")) text += "\n";
        else text += unescapeXml(m[3] ?? "");
      }
    }
    return { text };
  }
  throw new Error(`unknown kind ${kind}`);
}

window.katip = {
  version: VERSION, engine: ENGINE_SHA256,
  profiles: PROFILES, labels: LABELS_TR,
  ready: () => ({ version: VERSION, engine: ENGINE_SHA256 }),
  warm: async ({ model = "mini" }) => { await nameModel(model); return true; },
  mask, extract,
  // "Letter explained" (Dutch letters; see letter.js and docs/cep.html)
  letter: args => letter(args, { mask, nameModel }),
  letterInfo: () => letterInfo(),
  letterPrompt: args => letterPrompt(args),
  restore: ({ text, mapping }) => {
    const out = restoreText(text, mapping);
    const left = [...out.matchAll(/\[[A-ZÇĞİÖŞÜÂ .\/()-]+-\d+\]/g)].map(m => m[0]).filter(p => !(p in mapping));
    return { text: out, unknown: [...new Set(left)] };
  },
};
