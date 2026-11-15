// After detection: ID numbers by context, every occurrence of each detected value, and a fail-closed
// leak check. TypeScript twin of sdk/python/src/katip_mask/safety.py (same steps as Katip Kalkan).
import {
  NOT_WORD_CLASS, SPACE_CLASS, WORD_CLASS, casefold, dyn, finditer, literal, literalIgnoreCase, sortBy, splitWs, strip, trUpper,
} from "./engine/py.js";
import type { EngineSpan } from "./engine/detect.js";

export const BLOCK = "█";

export type RawSpan = Omit<EngineSpan, "flag_only"> & { flag_only?: boolean };

/** A detected value would stay readable in the masked text. Carries kinds and line numbers, never values. */
export class LeakError extends Error {
  constructor(public readonly kinds: string[], public readonly lines: number[]) {
    super(`masking refused: ${lines.length || "some"} detected value(s) would stay readable (types: ${kinds.join(", ")}; lines: ${lines.join(", ")})`);
    this.name = "LeakError";
  }
}

const id4 = (p: string, n: number) => p + String(n).padStart(4, "0");

export function idNumbers(text: string, spans: RawSpan[]): RawSpan[] {
  const out = [...spans];
  for (const m of finditer("safety._IDS", text)) {
    const [a, b] = m.group(1) !== undefined ? [m.start(1), m.end(1)] : [m.start(), m.end()];
    if (out.some(s => s.start < b && a < s.end)) continue;
    const typ = text.slice(a, a + 2) === "99" ? "YKN" : "TCKN";
    out.push({ id: id4("i", out.length), entity_type: typ, start: a, end: b, text: text.slice(a, b), score: 1.0,
      recognizer: "katip_id_context", explanation: "11 digits after an ID label" });
  }
  return sortBy(out, s => [s.start]);
}

const valuePattern = (value: string) =>
  dyn(`(?<!${WORD_CLASS})` + splitWs(value).map(literalIgnoreCase).join(SPACE_CLASS + "+") + `(?!${WORD_CLASS})`);

export function propagate(text: string, spans: RawSpan[]): RawSpan[] {
  const seen = new Set<string>(), cands: Array<[string, string]> = [];
  for (const s of spans) {
    const k = s.entity_type + "\u0000" + strip(s.text);
    if (!seen.has(k)) { seen.add(k); cands.push([s.entity_type, strip(s.text)]); }
  }
  let out = [...spans];
  for (const [typ, val] of sortBy(cands, c => [-c[1].length, c[0], c[1]])) {
    if (val.length < 4) continue;
    for (const m of finditer(valuePattern(val), text)) {
      const hit = out.filter(s => s.start < m.end() && m.start() < s.end);
      if (hit.some(s => s.start <= m.start() && s.end >= m.end())) continue;
      if (hit.some(s => s.entity_type !== typ || s.start < m.start() || s.end > m.end())) continue;
      out = out.filter(s => !hit.includes(s));
      out.push({ id: id4("p", out.length), entity_type: typ, start: m.start(), end: m.end(), text: m.group()!, score: 1.0,
        recognizer: "katip_propagate", explanation: "another occurrence of a detected value" });
    }
  }
  return sortBy(out, s => [s.start]);
}

const WORD_RX = new RegExp(WORD_CLASS, "gu");
function leakPattern(value: string): RegExp | null {
  if ((value.match(WORD_RX) ?? []).length < 4) return null;
  return dyn(`(?<!${WORD_CLASS})` + splitWs(value).map(literalIgnoreCase).join(NOT_WORD_CLASS + "*") + `(?!${WORD_CLASS})`);
}

function visible(text: string, spans: RawSpan[]): string {
  let out = "", pos = 0;
  for (const sp of sortBy(spans, s => [s.start, -s.end])) {
    if (sp.start < pos) continue;
    out += text.slice(pos, sp.start) + " _ ";
    pos = sp.end;
  }
  return out + text.slice(pos);
}

export function leaks(text: string, spans: RawSpan[]): string[] {
  const vis = visible(text, spans);
  const out: string[] = [];
  for (const s of spans) {
    const p = leakPattern(s.text);
    if (p) { p.lastIndex = 0; if (p.exec(vis)) out.push(s.id); }
  }
  return out;
}

export function repair(text: string, spans: RawSpan[], leaked: string[]): RawSpan[] {
  let out = [...spans];
  for (const sid of leaked) {
    const src = out.find(s => s.id === sid) ?? spans.find(s => s.id === sid)!;
    const pat = leakPattern(src.text)!;
    for (const m of finditer(pat, text)) {
      const hit = out.filter(s => s.start < m.end() && m.start() < s.end);
      if (hit.some(s => s.start <= m.start() && s.end >= m.end())) continue;
      const a = Math.min(m.start(), ...hit.map(s => s.start)), b = Math.max(m.end(), ...hit.map(s => s.end));
      out = out.filter(s => !hit.includes(s));
      out.push({ id: id4("r", out.length), entity_type: src.entity_type, start: a, end: b, text: text.slice(a, b), score: 1.0,
        recognizer: "katip_repair", explanation: "covers a value that was still readable" });
    }
  }
  return sortBy(out, s => [s.start]);
}

const SPACE_RUN = new RegExp(SPACE_CLASS + "+", "gu");
const norm = (s: string) => casefold(strip(s).replace(SPACE_RUN, " "));

/** Replace spans by placeholders. Spans carry offsets into `text` (any unit, as long as they agree). */
export function render(text: string, spans: Array<{ entity_type: string; start: number; end: number; text: string }>, style: "label" | "block",
  labels: Record<string, string>): { text: string; mapping: Record<string, string> } {
  const counters = new Map<string, number>(), keys = new Map<string, string>(), mapping: Record<string, string> = {};
  let out = "", pos = 0;
  for (const sp of sortBy(spans, s => [s.start, -s.end])) {
    if (sp.start < pos) continue;
    out += text.slice(pos, sp.start);
    if (style === "block") out += BLOCK.repeat(6);
    else {
      const key = sp.entity_type + "|" + norm(sp.text);
      if (!keys.has(key)) {
        const n = (counters.get(sp.entity_type) ?? 0) + 1;
        counters.set(sp.entity_type, n);
        const label = `[${trUpper(labels[sp.entity_type] ?? sp.entity_type)}-${n}]`;
        keys.set(key, label);
        mapping[label] = strip(sp.text);
      }
      out += keys.get(key);
    }
    pos = sp.end;
  }
  return { text: out + text.slice(pos), mapping };
}

/** Repair leaks (3 rounds) and return the final spans, or throw LeakError. */
export function safeSpans(text: string, spans: RawSpan[]): RawSpan[] {
  for (let round = 0; round < 3; round++) {
    const leaked = leaks(text, spans);
    if (!leaked.length) return spans;
    spans = repair(text, spans, leaked);
  }
  const bad = new Set(leaks(text, spans));
  const badSpans = spans.filter(s => bad.has(s.id));
  const kinds = [...new Set(badSpans.map(s => s.entity_type))].sort();
  const lines = [...new Set(badSpans.map(s => text.slice(0, s.start).split("\n").length))].sort((a, b) => a - b);
  throw new LeakError(kinds, lines);
}

/** Put original values back in place of the placeholders. */
export function restore(text: string, mapping: Record<string, string>): string {
  const keys = Object.keys(mapping);
  if (!keys.length) return text;
  const rx = dyn(sortBy(keys, k => [-k.length]).map(literal).join("|"));
  let out = "", last = 0;
  for (const m of finditer(rx, text)) { out += text.slice(last, m.start()) + mapping[m.group()!]; last = m.end(); }
  return out + text.slice(last);
}
