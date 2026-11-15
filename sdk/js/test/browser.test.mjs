// Runs the package in headless Chromium (esbuild bundle + onnxruntime-web) and checks it produces exactly
// what Node produces, rules and model. Needs Playwright with Chromium and the model in the local cache
// (`npx katip-mask download nano`); skipped otherwise.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join, dirname, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { Masker, MODELS, cacheDir } from "../dist/index.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const MODEL = process.env.KATIP_MASK_BROWSER_MODEL ?? "nano";
const require = createRequire(import.meta.url);
let chromium, esbuild;
try { ({ chromium } = require("playwright")); esbuild = await import("esbuild"); } catch { /* skipped below */ }
const modelDir = join(cacheDir(), MODEL, MODELS[MODEL].revision);
const samples = join(ROOT, "..", "..", "docs", "samples");
const TEXTS = readdirSync(samples).filter(f => f.endsWith(".txt")).sort().slice(0, 12)
  .map(f => readFileSync(join(samples, f), "utf8")).concat(["😀 Davacı Ahmet YILMAZ, KİMLİK NO 10000000146, Peter Aufschnaiter"]);

test("browser output equals Node output", { skip: !chromium && "playwright not installed", timeout: 300_000 }, async () => {
  const withModel = existsSync(join(modelDir, "onnx", "model_quantized.onnx"));
  const bundle = await esbuild.build({
    entryPoints: [join(HERE, "browser", "page.mjs")], bundle: true, write: false, format: "esm", platform: "browser",
    conditions: ["browser"], alias: { "katip-mask": ROOT }, external: ["*.wasm"], logLevel: "silent",
  });
  const ortDist = join(ROOT, "node_modules", "onnxruntime-web", "dist");
  const server = createServer((req, res) => {
    const url = new URL(req.url, "http://x");
    let body = null, type = "application/octet-stream";
    if (url.pathname === "/") { body = '<!doctype html><meta charset="utf-8"><script type="module" src="/app.js"></script>'; type = "text/html"; }
    else if (url.pathname === "/app.js") { body = bundle.outputFiles[0].contents; type = "text/javascript"; }
    else if (url.pathname.startsWith("/ort/")) { const p = join(ortDist, url.pathname.slice(5)); if (existsSync(p)) { body = readFileSync(p); type = extname(p) === ".wasm" ? "application/wasm" : "text/javascript"; } }
    else if (url.pathname.startsWith(`/models/${MODEL}/`)) { const p = join(modelDir, url.pathname.slice(`/models/${MODEL}/`.length)); if (existsSync(p)) body = readFileSync(p); }
    res.writeHead(body ? 200 : 404, { "content-type": type, "cross-origin-opener-policy": "same-origin", "cross-origin-embedder-policy": "require-corp" });
    res.end(body ?? "");
  });
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.waitForFunction(() => typeof window.run === "function", null, { timeout: 30_000 });
    const got = await page.evaluate(([t, m]) => window.run(t, m), [TEXTS, withModel ? MODEL : null]);
    assert.deepEqual(errors, []);
    const plain = r => JSON.parse(JSON.stringify({ text: r.text, spans: r.spans, mapping: r.mapping }));
    assert.deepEqual(got.rules, TEXTS.map(t => plain(new Masker({ profile: "ai" }).maskSync(t))));
    if (withModel) {
      process.env.KATIP_MASK_OFFLINE = "1";
      const m = await Masker.create({ profile: "ai", model: MODEL });
      delete process.env.KATIP_MASK_OFFLINE;
      const want = [];
      for (const t of TEXTS) want.push(plain(await m.mask(t)));
      const round = x => JSON.parse(JSON.stringify(x, (k, v) => (k === "score" ? Math.round(v * 1e6) / 1e6 : v)));
      assert.equal(got.model.length, TEXTS.length);
      assert.deepEqual(round(got.model), round(want));
    } else test.skip?.(`model ${MODEL} not in ${cacheDir()}`);
  } finally {
    await browser.close();
    server.close();
  }
});
