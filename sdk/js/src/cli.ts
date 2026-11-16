#!/usr/bin/env node
// katip-mask command line (Node): same commands and output as the Python CLI.
import { readFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { LeakError, Masker, MODELS, PROFILES, VERSION, downloadModel, restore, type ModelName, type Profile, type Span } from "./index.js";

const USAGE = `katip-mask ${VERSION}: mask Turkish personal data (KVKK) on this machine

  katip-mask mask <file|-> [--profile court|ai|anon] [--model mini|nano|base] [--json] [--style label|block]
                           [--threshold 0.5] [--allow TERM]... [--deny TERM]... [--address street|full]
  katip-mask detect <file|-> [same options]
  katip-mask restore <file|-> --mapping result.json
  katip-mask download mini|nano|base`;

const read = (f: string) => readFileSync(f === "-" ? 0 : f, "utf8");

async function main(argv: string[]): Promise<number> {
  const { values: o, positionals: [cmd, arg] } = parseArgs({
    args: argv, allowPositionals: true,
    options: {
      profile: { type: "string", default: "court" }, model: { type: "string" }, json: { type: "boolean" }, style: { type: "string" },
      threshold: { type: "string" }, allow: { type: "string", multiple: true }, deny: { type: "string", multiple: true },
      address: { type: "string" }, mapping: { type: "string" }, help: { type: "boolean", short: "h" }, version: { type: "boolean" },
    },
  });
  if (o.version) { console.log(`katip-mask ${VERSION}`); return 0; }
  if (o.help || !cmd || !arg) { console.log(USAGE); return o.help ? 0 : 2; }
  if (cmd === "download") {
    if (!(arg in MODELS)) throw new Error(`unknown model ${arg}`);
    await downloadModel(arg as ModelName, { onProgress: m => console.error(m) });
    return 0;
  }
  if (cmd === "restore") {
    if (!o.mapping) throw new Error("--mapping is required");
    const m = JSON.parse(read(o.mapping));
    process.stdout.write(restore(read(arg), m.mapping ?? m));
    return 0;
  }
  if (cmd !== "mask" && cmd !== "detect") { console.log(USAGE); return 2; }
  if (!(o.profile! in PROFILES)) throw new Error(`unknown profile ${o.profile}`);
  const masker = await Masker.create({
    profile: o.profile as Profile, model: (o.model as ModelName) ?? null, style: o.style as "label" | "block" | undefined,
    threshold: o.threshold === undefined ? undefined : Number(o.threshold), allow: o.allow ?? [], deny: o.deny ?? [],
    addressDetail: o.address as "street" | "full" | undefined, onProgress: m => console.error(m),
  });
  const text = read(arg);
  if (cmd === "detect") {
    for (const s of await masker.detect(text)) console.log(JSON.stringify(snake(text)(s)));
    return 0;
  }
  try {
    const r = await masker.mask(text);
    if (o.json) console.log(JSON.stringify({ text: r.text, spans: r.spans.map(snake(text)), mapping: r.mapping, profile: r.profile, model: r.model }, null, 1));
    else process.stdout.write(r.text);
    return 0;
  } catch (e) {
    if (e instanceof LeakError) { console.error(`katip-mask: ${e.message}`); return 3; }
    throw e;
  }
}

main(process.argv.slice(2)).then(code => process.exit(code), e => { console.error(`katip-mask: ${e?.message ?? e}`); process.exit(1); });

/** The Python CLI's JSON exactly (snake_case, code point offsets), so the two CLIs are interchangeable. */
function snake(text: string) {
  const cp = (i: number) => [...text.slice(0, i)].length;
  return ({ entityType, start, end, ...rest }: Span) => ({ entity_type: entityType, start: cp(start), end: cp(end), ...rest });
}
