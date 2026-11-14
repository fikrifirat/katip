// Times one Katip Mask model in this browser with the app's own stack (transformers.js + onnxruntime-web wasm,
// 1 thread, q8, ner.js runNer), the way docs/worker.js runs it, but on the main thread.
// cold_ms: page script start -> runtime import -> model load -> first runNer result (no browser cache).
// Per page: the demo samples' .txt files, run warm 3 times each; ms per page = median ms per 500 words.
import { loadNer, runNer } from "./ner.js";
// onnxruntime's wasm heap is not in the JS heap: capture the module's exported memories to read their size
const MEMS = [];
const M0 = WebAssembly.Memory;
WebAssembly.Memory = function (d) { const m = new M0(d); MEMS.push(m); return m; };
WebAssembly.Memory.prototype = M0.prototype;
for (const k of ["instantiate", "instantiateStreaming"]) {
  const f = WebAssembly[k];
  WebAssembly[k] = async (...a) => { const r = await f.apply(WebAssembly, a), ex = (r.instance ?? r).exports;
    for (const v of Object.values(ex ?? {})) if (v instanceof M0 && !MEMS.includes(v)) MEMS.push(v); return r; };
}
const out = document.getElementById("out"), log = s => { out.textContent += s + "\n"; };
const id = new URLSearchParams(location.search).get("model");
const SAMPLES = ["aydinlatma_01", "dilekce_01", "karar_01", "kira_sozlesmesi_01", "ihtarname_01", "epikriz_01",
  "eposta_01", "fatura_01", "mesaj_01", "zabit_01"];
const words = t => (t.match(/[\p{L}\p{N}][\p{L}\p{N}'’.-]*/gu) || []).length;
const median = a => { const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
async function mem() {
  const r = { js_heap_mb: performance.memory ? +(performance.memory.usedJSHeapSize / 2 ** 20).toFixed(1) : null };
  r.wasm_mb = +(MEMS.reduce((n, m) => n + m.buffer.byteLength, 0) / 2 ** 20).toFixed(1);
  if (self.crossOriginIsolated && performance.measureUserAgentSpecificMemory) {
    try { const m = await performance.measureUserAgentSpecificMemory(); r.ua_total_mb = +(m.bytes / 2 ** 20).toFixed(1); } catch (e) { r.ua_error = String(e); }
  }
  return r;
}
async function main() {
  if (!id) return;
  const t0 = performance.now();
  const texts = await Promise.all(SAMPLES.map(s => fetch(`samples/${s}.txt`).then(r => r.text())));
  const tFetch = performance.now();
  const mem0 = await mem();
  const t1 = performance.now();
  const T = await import("./vendor/transformers/transformers.min.js");
  const tImport = performance.now();
  const here = p => new URL(p, location.href).href;
  const ner = await loadNer(T, id, new URL("./models/", location.href).pathname,
    { mjs: here("./vendor/ort/ort-wasm-simd-threaded.asyncify.mjs"), wasm: here("./vendor/ort/ort-wasm-simd-threaded.asyncify.wasm") }, null, "q8");
  const tLoad = performance.now();
  const first = await runNer(T, ner, texts[0]);
  const tFirst = performance.now();
  const r = { model: id, ua: navigator.userAgent, cores: navigator.hardwareConcurrency, threads: 1, dtype: "q8",
    isolated: self.crossOriginIsolated, date: new Date().toISOString(),
    cold: { runtime_import_ms: Math.round(tImport - t1), model_load_ms: Math.round(tLoad - tImport),
      first_result_ms: Math.round(tFirst - tLoad), total_ms: Math.round(tFirst - t1 + (tFetch - t0)), first_spans: first.length } };
  log(JSON.stringify(r.cold));
  const runs = [];
  for (let k = 0; k < SAMPLES.length; k++) {
    const ms = [];
    for (let i = 0; i < 3; i++) { const a = performance.now(); await runNer(T, ner, texts[k]); ms.push(performance.now() - a); }
    const w = words(texts[k]), m = median(ms);
    runs.push({ sample: SAMPLES[k], words: w, median_ms: +m.toFixed(1), ms_per_500_words: +(m / w * 500).toFixed(1) });
    log(`${SAMPLES[k]} ${w}w ${m.toFixed(1)} ms`);
  }
  // one long "page": samples joined to ~500 words, as a real multi-window document
  const page = texts.join("\n\n"), pw = words(page), pm = [];
  for (let i = 0; i < 3; i++) { const a = performance.now(); await runNer(T, ner, page); pm.push(performance.now() - a); }
  r.samples = runs;
  r.ms_per_page_samples_median = +median(runs.map(x => x.ms_per_500_words)).toFixed(1);
  r.joined = { words: pw, median_ms: +median(pm).toFixed(1), ms_per_500_words: +(median(pm) / pw * 500).toFixed(1) };
  r.memory_before_load = mem0;
  r.memory_after = await mem();
  log(JSON.stringify({ per_page: r.ms_per_page_samples_median, joined: r.joined, mem: r.memory_after }));
  window.RESULT = r;
  await fetch("result", { method: "POST", body: JSON.stringify(r) });
  document.title = "done " + id;
}
main().catch(e => { log("ERROR " + e.stack); document.title = "error"; });
