// Katip Algıla in the browser / iOS WebView: the same document-type classifier as
// connector/katip_kalkan/doctype.py, byte for byte (FNV-1a hashing; parity: src/tests/doctype_parity.mjs).
// No network I/O here. Load the pack once: loadModel(modelJson, weightsArrayBuffer, packJson).
const HEAD = 3000, TAIL = 1000;
const FOLD = { "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u",
               "Ç": "C", "Ğ": "G", "I": "I", "Ö": "O", "Ş": "S", "Ü": "U", "Â": "A", "Î": "I", "Û": "U" };
const enc = new TextEncoder();

export function fnv1a(s) {
  let h = 0x811c9dc5;
  for (const b of enc.encode(s)) { h ^= b; h = Math.imul(h, 0x01000193) >>> 0; }
  return h >>> 0;
}

export function normalise(text) {
  let cps = Array.from(text.normalize("NFC"));
  if (cps.length > HEAD + TAIL) cps = [...cps.slice(0, HEAD), "\n", ...cps.slice(cps.length - TAIL)];
  let t = cps.join("").replace(/I/g, "ı").replace(/İ/g, "i").toLowerCase();
  t = Array.from(t, (c) => FOLD[c] ?? c).join("");
  return t.normalize("NFKD").replace(/\p{Mn}/gu, "");
}

export const KINDS = ["w", "b", "c", "l", "h"];

export function tokens(text, kinds = KINDS) {
  const k = new Set(kinds), t = normalise(text), feats = [];
  for (const line of t.split("\n")) {
    const ws = (line.match(/[a-z0-9]+/g) || []).map((w) => w.replace(/[0-9]+/g, "0"));
    if (!ws.length) continue;
    if (k.has("l")) { feats.push("l:" + ws[0]); if (ws.length > 1) feats.push("l2:" + ws[0] + "_" + ws[1]); }
    ws.forEach((w, i) => {
      if (k.has("w")) feats.push("w:" + w);
      if (i && k.has("b")) feats.push("b:" + ws[i - 1] + "_" + w);
      if (k.has("c") && w.length > 3 && w !== "0") {
        const p = "<" + w + ">";
        for (const n of [3, 4]) for (let j = 0; j + n <= p.length; j++) feats.push("c:" + p.slice(j, j + n));
      }
    });
  }
  if (k.has("h")) for (const w of Array.from(t).slice(0, 300).join("").match(/[a-z0-9]+/g) || []) feats.push("h:" + w.replace(/[0-9]+/g, "0"));
  return feats;
}

export function featurize(text, dim, kinds = KINDS) {
  const counts = new Map();
  for (const f of tokens(text, kinds)) {
    const h = fnv1a(f), i = h % dim, sign = (h >>> 31) & 1 ? 1 : -1;
    counts.set(i, (counts.get(i) || 0) + sign);
  }
  const vec = new Map(); let norm = 0;
  for (const [i, v] of counts) if (v) { const x = Math.sign(v) * Math.log1p(Math.abs(v)); vec.set(i, x); norm += x * x; }
  norm = Math.sqrt(norm) || 1;
  for (const [i, v] of vec) vec.set(i, v / norm);
  return vec;
}

export function loadModel(model, weights, pack) {
  const w = new Int8Array(weights);
  if (w.length !== model.dim * model.labels.length) throw new Error("doctype weights damaged");
  const names = Object.fromEntries((pack?.types || []).map((t) => [t.id, t.name]));
  return { ...model, w, names, threshold: pack?.threshold ?? 0.5, kinds: model.kinds || KINDS };
}

export function classify(m, text, k = 3) {
  const C = m.labels.length, acc = new Float64Array(C);
  if (text.trim().length < 40) return { type: "diger", confidence: 0, abstained: true, top: [], name: m.names.diger };
  for (const [i, v] of featurize(text, m.dim, m.kinds)) {
    const base = i * C;
    for (let c = 0; c < C; c++) acc[c] += m.w[base + c] * v;
  }
  const z = Array.from(acc, (a, c) => a * m.scale[c] + m.bias[c]);
  const mx = Math.max(...z), e = z.map((x) => Math.exp(x - mx)), s = e.reduce((a, b) => a + b, 0);
  const p = e.map((x) => x / s), order = p.map((_, i) => i).sort((a, b) => p[b] - p[a]);
  const best = m.labels[order[0]], conf = p[order[0]], abstain = conf < m.threshold;
  const type = abstain ? "diger" : best;
  return { type, guess: best, confidence: Math.round(conf * 1000) / 1000, abstained: abstain, name: m.names[type],
           top: order.slice(0, k).map((i) => ({ type: m.labels[i], p: Math.round(p[i] * 1000) / 1000, name: m.names[m.labels[i]] })) };
}
