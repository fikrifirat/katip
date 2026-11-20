// Python/JS parity for the document-type classifier: same features, same answer, same confidence.
//   node src/tests/doctype_parity.mjs        (needs python3 on PATH)
import { readFileSync, readdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { loadModel, classify, fnv1a } from "../doctype.js";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const packs = path.join(repo, "connector/katip_kalkan/doctype_packs");
const model = JSON.parse(readFileSync(path.join(packs, "tr.model.json"), "utf8"));
const pack = JSON.parse(readFileSync(path.join(packs, "tr.pack.json"), "utf8"));
const m = loadModel(model, readFileSync(path.join(packs, model.weights)).buffer.slice(0), pack);

if (fnv1a("a") !== 0xe40c292c) throw new Error("fnv1a mismatch");
const files = readdirSync(path.join(repo, "docs/samples")).filter((f) => f.endsWith(".txt")).sort();
const py = JSON.parse(execFileSync("python3", ["-c", `
import json, sys, pathlib
sys.path.insert(0, ${JSON.stringify(path.join(repo, "connector"))})
from katip_kalkan import doctype as D
d = pathlib.Path(${JSON.stringify(path.join(repo, "docs/samples"))})
print(json.dumps({f: D.classify((d / f).read_text(encoding="utf-8"), "tr") for f in ${JSON.stringify(files)}}))
`], { maxBuffer: 1 << 26 }).toString());
let bad = 0;
for (const f of files) {
  const js = classify(m, readFileSync(path.join(repo, "docs/samples", f), "utf8"));
  const p = py[f];
  if (js.type !== p.type || Math.abs(js.confidence - p.confidence) > 0.002) { bad++; console.log("MISMATCH", f, js.type, js.confidence, p.type, p.confidence); }
}
console.log(`${files.length - bad}/${files.length} documents identical in Python and JS`);
process.exit(bad ? 1 : 0);
