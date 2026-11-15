// Bundled by test/browser.test.mjs with esbuild for the browser (conditions: browser).
import * as ort from "onnxruntime-web";
import { Masker } from "katip-mask";

ort.env.wasm.wasmPaths = "/ort/";
ort.env.wasm.numThreads = 1;

window.run = async (texts, model) => {
  const out = { rules: texts.map(t => new Masker({ profile: "ai" }).maskSync(t)) };
  if (model) {
    const m = await Masker.create({ profile: "ai", model, modelBaseUrl: location.origin + "/models", ort });
    out.model = [];
    for (const t of texts) out.model.push(await m.mask(t));
    // second load must come from Cache Storage, verified again
    await Masker.create({ profile: "ai", model, modelBaseUrl: location.origin + "/models", ort });
  }
  const strip = r => ({ text: r.text, spans: r.spans, mapping: r.mapping });
  return { rules: out.rules.map(strip), model: out.model?.map(strip) };
};
