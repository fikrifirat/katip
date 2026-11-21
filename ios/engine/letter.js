// "Letter explained" for the iOS engine: the same flow as docs/cep.html. A Dutch letter is masked with the
// katip_nl recognizers (lab/nl/katip_nl, stdlib Python) running in Pyodide, which is loaded from the app bundle
// only the first time a Dutch letter arrives; letter types, deadlines and the prompt come from src/letters.js.
// Turkish letters go through the katip-mask SDK like every other document. Nothing here touches the network.
import { TYPES, LAW, HELP, classifyLetter, guessLanguage, letterPrompt } from "../../src/letters.js";
import NL_LABELS from "../../docs/katip_nl_labels.json";

let py = null;
function pyodide() {
  return py ??= (async () => {
    const base = new URL("nl/", location.href).href;
    const { loadPyodide } = await import(/* @vite-ignore */ base + "pyodide.mjs");
    const p = await loadPyodide({ indexURL: base });
    p.unpackArchive(await (await fetch(base + "katip_nl.zip")).arrayBuffer(), "zip", { extractDir: "/home/pyodide" });
    p.runPython("import sys; sys.path.insert(0, '/home/pyodide'); import katip_nl.recognizers");
    return p;
  })().catch(e => { py = null; throw e; });
}

async function detectNl(text, { names = [], allow = [], deny = [] }) {
  const p = await pyodide();
  p.globals.set("_T", text);
  p.globals.set("_O", JSON.stringify({ extra: names, mask: deny, allow }));
  return JSON.parse(p.runPython(`import json
from katip_nl import recognizers as _nl
_o = json.loads(_O)
json.dumps(_nl.detect(_T, 0.5, None, [tuple(x) for x in _o["extra"]], "full", _o["mask"], _o["allow"]), ensure_ascii=False)`));
}

// [NAAM-1] style placeholders; a surname gets the label of the full name seen before it (same rule as worker.js)
function render(text, spans) {
  const counters = {}, seen = new Map(), out = [], mapping = {};
  let pos = 0;
  const norm = s => s.split(/\s+/).filter(Boolean).join(" ").toLowerCase();
  for (const sp of [...spans].sort((a, b) => a.start - b.start)) {
    if (sp.start < pos) continue;
    const typ = sp.entity_type, k = typ + "|" + norm(sp.ref || sp.text);
    if (!seen.has(k) && typ === "PERSON") {
      for (const [kk, lab] of seen) if (kk.startsWith("PERSON|") && kk.endsWith(" " + k.slice(7))) { seen.set(k, lab); break; }
    }
    if (!seen.has(k)) { counters[typ] = (counters[typ] ?? 0) + 1; seen.set(k, `[${NL_LABELS[typ]?.tag ?? typ}-${counters[typ]}]`); }
    const lab = seen.get(k);
    if (!(lab in mapping)) mapping[lab] = sp.text;
    out.push(text.slice(pos, sp.start), lab); pos = sp.end;
  }
  out.push(text.slice(pos));
  return { text: out.join(""), mapping };
}

/**
 * text: the letter. mask(args): the SDK path for Turkish letters (bridge.js). nameModel: the loaded Mini/Nano or null.
 * Returns the masked letter, its map and spans, the language, and Katip's guess of the letter type. Fails closed
 * like the SDK: if a detected value would stay readable, no text is returned.
 */
export async function letter({ text, model = "mini", allow = [], deny = [] }, { mask, nameModel }) {
  const lang = guessLanguage(text) === "nl" ? "nl" : "tr";
  if (lang === "tr") {
    const r = await mask({ text, profile: "ai", model, allow, deny });
    return { ...r, lang, type: "other", why: [] };
  }
  const t0 = performance.now();
  const m = await nameModel(model);
  // the Turkish name model still helps on Dutch letters (Turkish and other foreign names); only confident names go in
  const names = m ? (await m.spans(text, 0.8)).filter(x => x[3] === "PERSON") : [];
  // Python counts code points, JS counts UTF-16 units: they differ only when the text has emoji or other astral characters
  const astral = /[\uD800-\uDFFF]/.test(text);
  const cp2u = astral ? (() => { const a = [0]; for (const ch of text) a.push(a.at(-1) + ch.length); return a; })() : null;
  const u2cp = i => astral ? cp2u.findIndex(x => x >= i) : i;
  const spans = (await detectNl(text, { names: names.map(([s, e, p, t]) => [u2cp(s), u2cp(e), p, t]), allow, deny }))
    .filter(s => !s.flag_only)
    .map(s => astral ? { ...s, start: cp2u[s.start], end: cp2u[s.end] } : s);
  const r = render(text, spans);
  const lower = r.text.toLowerCase();
  const leaked = [...new Set(spans.filter(s => s.text.trim().length > 1 && lower.includes(s.text.toLowerCase())).map(s => s.entity_type))];
  if (leaked.length) return { ok: false, leak: true, kinds: leaked, lines: [], error: "a detected value would stay readable" };
  const c = classifyLetter(text);
  return {
    ok: true, lang, type: c.type, why: c.why, text: r.text, mapping: r.mapping, model: m ? m.name : null, ms: Math.round(performance.now() - t0),
    spans: spans.map(s => ({ type: s.entity_type, start: s.start, end: s.end, text: s.text, score: s.score, recognizer: s.recognizer })),
  };
}

export const letterInfo = () => ({ order: Object.keys(TYPES), types: TYPES, law: LAW, help: HELP.nl, labels: NL_LABELS });
export { letterPrompt };
