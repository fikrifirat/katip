import { loadPyodide } from "../node_modules/pyodide/pyodide.mjs";
import fs from "fs";
const py = await loadPyodide();
py.unpackArchive(new Uint8Array(fs.readFileSync(new URL("../dist/katip_py.zip", import.meta.url))), "zip", { extractDir: "/home/pyodide" });
py.runPython("import sys; sys.path.insert(0,'/home/pyodide'); import local_detect");
const dir = process.argv[2]; const res = {};
let t0 = performance.now(), chars = 0;
for (const f of fs.readdirSync(dir).filter(f => f.endsWith(".txt")).sort()) {
  const text = fs.readFileSync(`${dir}/${f}`, "utf8"); chars += text.length;
  py.globals.set("T", text);
  res[f] = JSON.parse(py.runPython("local_detect.detect_json(T)"));
}
console.error(`browser-engine: ${Object.keys(res).length} docs, ${chars} chars, ${(performance.now()-t0).toFixed(0)} ms`);
fs.writeFileSync(process.argv[3], JSON.stringify(res));
