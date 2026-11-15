// Python SDK vs JavaScript SDK on the parity corpus: every case must give the same masked text, the same
// spans and the same placeholder mapping (or the same LeakError). Cases: python sdk/parity/golden.py.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Masker, LeakError } from "../dist/index.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const file = process.env.KATIP_PARITY_CASES ?? path.join(here, "../../parity/cases.jsonl");

// Python offsets count code points; JS offsets count UTF-16 units
const cpToUtf16 = (text, i) => [...text].slice(0, i).join("").length;

test("Python and JavaScript give identical results on the parity corpus", { skip: !fs.existsSync(file) && "no cases file" }, () => {
  const lines = fs.readFileSync(file, "utf8").split("\n").filter(Boolean);
  let failures = 0;
  for (const line of lines) {
    const c = JSON.parse(line);
    const m = new Masker({ profile: c.cfg.profile, ...(c.cfg.threshold !== undefined && { threshold: c.cfg.threshold }), allow: c.cfg.allow ?? [], deny: c.cfg.deny ?? [],
      style: c.cfg.style ?? "label", addressDetail: c.cfg.address_detail ?? undefined });
    const ocr = c.cfg.ocr ? [[0, c.input.length]] : [];
    let got;
    try {
      const r = m._maskWithModelSpans(c.input, c.cfg.extra ?? [], c.cfg.trust ?? null, { ocrRanges: ocr });
      got = { text: r.text, mapping: r.mapping, spans: r.spans.map(s => ({ entity_type: s.entityType, start: s.start, end: s.end, text: s.text,
        score: s.score, recognizer: s.recognizer, explanation: s.explanation })) };
    } catch (e) {
      if (!(e instanceof LeakError)) throw e;
      got = { error: { kinds: e.kinds, lines: e.lines } };
    }
    const want = c.expect.error ? c.expect : { ...c.expect, spans: c.expect.spans.map(s => ({ ...s, start: cpToUtf16(c.input, s.start), end: cpToUtf16(c.input, s.end) })) };
    try { assert.deepStrictEqual(got, want); } catch (e) {
      failures++;
      if (failures <= 5) console.error(`MISMATCH ${c.name} ${JSON.stringify(c.cfg).slice(0, 160)}\n${String(e.message).slice(0, 2500)}`);
    }
  }
  assert.equal(failures, 0, `${failures} of ${lines.length} cases differ`);
  console.log(`${lines.length} cases identical`);
});
