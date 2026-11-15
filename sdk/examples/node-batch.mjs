// Mask every .txt file in a folder for court filing, writing <name>.masked.txt and <name>.mapping.json.
//   npm install katip-mask onnxruntime-node
//   node node-batch.mjs ./evrak
import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { Masker, LeakError } from "katip-mask";

const dir = process.argv[2] ?? ".";
const masker = await Masker.create({ profile: "court", model: "mini", onProgress: console.error });
for (const name of (await readdir(dir)).filter(f => f.endsWith(".txt") && !f.endsWith(".masked.txt"))) {
  const path = join(dir, name);
  try {
    const r = await masker.mask(await readFile(path, "utf8"));
    await writeFile(path.replace(/\.txt$/, ".masked.txt"), r.text);
    await writeFile(path.replace(/\.txt$/, ".mapping.json"), JSON.stringify(r.mapping, null, 1));
    console.log(`${name}: ${r.spans.length} values masked`);
  } catch (e) {
    if (!(e instanceof LeakError)) throw e;
    console.error(`${name}: not written (${e.message})`);
  }
}
