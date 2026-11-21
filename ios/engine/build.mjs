// Builds the offline engine bundle for the iOS app into ios/Katip/Resources/Engine:
//   index.html, engine.js (katip-mask SDK + bridge), ort/ (onnxruntime-web wasm), models/{mini,nano}/...,
//   nl/ (Pyodide and docs/katip_nl.zip, for Dutch letters)
// Models are copied from docs/models (the same files the web app serves) and checked against sdk/spec/models.json.
// Run from the repo root:  (cd sdk/js && npm ci && npm run build) && node ios/engine/build.mjs
import { build } from "../../sdk/js/node_modules/esbuild/lib/main.js";
import { createHash } from "node:crypto";
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync, copyFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
const out = join(root, "ios/Katip/Resources/Engine");
const sdk = join(root, "sdk/js");
const ortDist = join(sdk, "node_modules/onnxruntime-web/dist");

rmSync(out, { recursive: true, force: true });
mkdirSync(join(out, "ort"), { recursive: true });

await build({
  entryPoints: [join(here, "bridge.js")],
  bundle: true, format: "esm", platform: "browser", target: "safari16.4", minify: true,
  outfile: join(out, "engine.js"), conditions: ["browser"], legalComments: "eof",
  alias: { "katip-mask": join(sdk, "dist/index.js"), "onnxruntime-web/wasm": join(ortDist, "ort.wasm.min.mjs") },
  // #runtime in the SDK resolves through its package.json "imports" with the browser condition.
  logLevel: "warning",
});

for (const f of ["ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm"]) copyFileSync(join(ortDist, f), join(out, "ort", f));
copyFileSync(join(here, "index.html"), join(out, "index.html"));
// Pyodide + the Dutch recognizers, for "Letter explained"; loaded only when a Dutch letter arrives
mkdirSync(join(out, "nl"), { recursive: true });
for (const f of ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"])
  copyFileSync(join(root, "docs/vendor/pyodide", f), join(out, "nl", f));
copyFileSync(join(root, "docs/katip_nl.zip"), join(out, "nl/katip_nl.zip"));
copyFileSync(join(root, "sdk/spec/profiles.json"), join(out, "profiles.json"));

const spec = JSON.parse(readFileSync(join(root, "sdk/spec/models.json"), "utf8"));
const manifest = {};
for (const name of ["mini", "nano"]) {
  const info = spec.models[name];
  manifest[name] = {};
  for (const [file, want] of Object.entries(info.files)) {
    const src = join(root, "docs/models", `katip-mask-${name}`, file);
    const data = readFileSync(src);
    const sha = createHash("sha256").update(data).digest("hex");
    if (sha !== want.sha256 || data.length !== want.size) throw new Error(`${src} does not match sdk/spec/models.json`);
    mkdirSync(dirname(join(out, "models", name, file)), { recursive: true });
    cpSync(src, join(out, "models", name, file));
    manifest[name][file] = want.sha256;
  }
}
// Read by the Swift scheme handler, which refuses any model file whose hash differs.
writeFileSync(join(out, "models/manifest.json"), JSON.stringify(manifest, null, 1) + "\n");
console.log(`engine built in ${out}`);
