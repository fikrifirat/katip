// Python semantics for the parts of `re` and `str` the engine uses, so the TypeScript port behaves
// exactly like the Python engine. Regexes come pre-compiled from generated.ts (see sdk/tools/pyre2js.py).
// All offsets here are indices into the engine's working text, in which every code point is one UTF-16
// unit (see toWorkingText), so they equal Python's code point offsets.
import { TABLES, WORDS } from "./generated.js";

export interface PyMatch {
  /** start of group g (-1 when the group did not take part) */
  start(g?: number): number;
  end(g?: number): number;
  group(g?: number): string | undefined;
  readonly groups: number;
}

const compiled = new Map<string, RegExp>();

function get(name: string, mode: "g" | "y"): RegExp {
  const key = mode + name;
  let r = compiled.get(key);
  if (!r) {
    const t = TABLES.rx[name];
    if (!t) throw new Error(`katip-mask: unknown engine regex ${name}`);
    r = new RegExp(t.source, "du" + mode);
    compiled.set(key, r);
  }
  return r;
}

/** A regex built at run time from a JS source string (dynamic patterns), cached by source. */
export function dyn(source: string, mode: "g" | "y" = "g"): RegExp {
  const key = "\u0000" + mode + source;
  let r = compiled.get(key);
  if (!r) {
    r = new RegExp(source, "du" + mode);
    compiled.set(key, r);
    if (compiled.size > 5000) compiled.clear();
  }
  return r;
}

function wrap(m: RegExpExecArray, offset = 0): PyMatch {
  const idx = (m as RegExpExecArray & { indices: Array<[number, number] | undefined> }).indices;
  return {
    start: (g = 0) => (idx[g] ? idx[g]![0] + offset : -1),
    end: (g = 0) => (idx[g] ? idx[g]![1] + offset : -1),
    group: (g = 0) => m[g],
    groups: m.length - 1,
  };
}

type Rx = string | RegExp;
const R = (x: Rx, mode: "g" | "y") => (typeof x === "string" ? get(x, mode) : x);

/** re.finditer(pattern, text, pos, endpos) */
export function finditer(x: Rx, text: string, pos = 0, endpos?: number): PyMatch[] {
  const r = R(x, "g");
  const s = endpos === undefined || endpos >= text.length ? text : text.slice(0, endpos);
  const out: PyMatch[] = [];
  r.lastIndex = Math.max(0, pos);
  for (;;) {
    const m = r.exec(s);
    if (!m) break;
    if (m[0] === "") throw new Error("katip-mask: finditer on an empty match is not supported");
    out.push(wrap(m));
  }
  return out;
}

/** pattern.search(text, pos, endpos) */
export function search(x: Rx, text: string, pos = 0, endpos?: number): PyMatch | null {
  const r = R(x, "g");
  const s = endpos === undefined || endpos >= text.length ? text : text.slice(0, endpos);
  r.lastIndex = Math.max(0, pos);
  const m = r.exec(s);
  return m ? wrap(m) : null;
}

/** pattern.match(text, pos, endpos): anchored at pos */
export function match(x: Rx, text: string, pos = 0, endpos?: number): PyMatch | null {
  const r = R(x, "y");
  const s = endpos === undefined || endpos >= text.length ? text : text.slice(0, endpos);
  r.lastIndex = Math.max(0, pos);
  const m = r.exec(s);
  return m ? wrap(m) : null;
}

/** re.fullmatch(pattern, text) */
export function fullmatch(x: Rx, text: string): PyMatch | null {
  const t = typeof x === "string" ? TABLES.rx[x] : null;
  const src = t ? t.source : (x as RegExp).source;
  return match(dyn("(?:" + src + ")(?![\\s\\S])", "y"), text);
}

/** re.findall: whole matches, group 1, or tuples */
export function findall(x: Rx, text: string): Array<string | string[]> {
  return finditer(x, text).map(m =>
    m.groups === 0 ? m.group(0)! : m.groups === 1 ? m.group(1) ?? "" : Array.from({ length: m.groups }, (_, i) => m.group(i + 1) ?? ""));
}

/** re.sub(pattern, "", text) style replacement with a literal string */
export function sub(x: Rx, repl: string, text: string): string {
  let out = "", last = 0;
  for (const m of finditer(x, text)) {
    out += text.slice(last, m.start()) + repl;
    last = m.end();
  }
  return out + text.slice(last);
}

/** re.split(pattern, text): captured separators are kept, like Python */
export function split(x: Rx, text: string): Array<string | undefined> {
  const out: Array<string | undefined> = [];
  let last = 0;
  for (const m of finditer(x, text)) {
    out.push(text.slice(last, m.start()));
    for (let g = 1; g <= m.groups; g++) out.push(m.group(g));
    last = m.end();
  }
  out.push(text.slice(last));
  return out;
}

// ------------------------------------------------------------------ str methods
const charRx = (k: string) => new RegExp("^" + TABLES.chars[k] + "$", "u");
const CH = {
  upper: charRx("upper"), lower: charRx("lower"), title: charRx("title"), digit: charRx("digit"),
  alnum: charRx("alnum"), alpha: charRx("alpha"), space: charRx("space"),
};
export const isUpperChar = (c: string) => CH.upper.test(c);
export const isLowerChar = (c: string) => CH.lower.test(c);
export const isSpaceChar = (c: string) => CH.space.test(c);
export const isAlnumChar = (c: string) => CH.alnum.test(c);
export const isDigitChar = (c: string) => CH.digit.test(c);

/** str.isupper() */
export function isupper(s: string): boolean {
  let cased = false;
  for (const c of s) {
    if (CH.lower.test(c) || CH.title.test(c)) return false;
    if (!cased && CH.upper.test(c)) cased = true;
  }
  return cased;
}
/** str.islower() */
export function islower(s: string): boolean {
  let cased = false;
  for (const c of s) {
    if (CH.upper.test(c) || CH.title.test(c)) return false;
    if (!cased && CH.lower.test(c)) cased = true;
  }
  return cased;
}
const every = (re: RegExp) => (s: string) => s.length > 0 && [...s].every(c => re.test(c));
export const isdigit = every(CH.digit);
export const isalnum = every(CH.alnum);
export const isalpha = every(CH.alpha);
export const isspace = every(CH.space);

/** str.strip(chars) / no argument: Python whitespace */
export function strip(s: string, chars?: string): string { return rstrip(lstrip(s, chars), chars); }
export function lstrip(s: string, chars?: string): string {
  let i = 0;
  const cs = chars === undefined ? null : [...chars];
  const arr = [...s];
  while (i < arr.length && (cs ? cs.includes(arr[i]!) : CH.space.test(arr[i]!))) i++;
  return arr.slice(i).join("");
}
export function rstrip(s: string, chars?: string): string {
  const cs = chars === undefined ? null : [...chars];
  const arr = [...s];
  let j = arr.length;
  while (j > 0 && (cs ? cs.includes(arr[j - 1]!) : CH.space.test(arr[j - 1]!))) j--;
  return arr.slice(0, j).join("");
}
/** str.split() with no argument */
export function splitWs(s: string): string[] {
  const out: string[] = [];
  let cur = "";
  for (const c of s) {
    if (CH.space.test(c)) { if (cur) out.push(cur); cur = ""; } else cur += c;
  }
  if (cur) out.push(cur);
  return out;
}
/** str.rfind(sub, 0, end) */
export const rfind = (s: string, sub: string, end: number) => (end - sub.length < 0 ? -1 : s.lastIndexOf(sub, end - sub.length));
/** Python's `a in b` for strings ("" is in every string) */
export const pyIn = (a: string, b: string) => b.includes(a);
export const startsWithAny = (s: string, prefixes: readonly string[]) => prefixes.some(p => s.startsWith(p));
export const endsWithAny = (s: string, suffixes: readonly string[]) => suffixes.some(p => s.endsWith(p));

/** str.lower() (JS toLowerCase implements the same Unicode mapping, final sigma included) */
export const lower = (s: string) => s.toLowerCase();
/** str.casefold() */
export function casefold(s: string): string {
  let out = "";
  for (const c of s) out += TABLES.casefold[c] ?? c.toLowerCase();
  return out;
}
export const upper = (s: string) => s.toUpperCase();

// ------------------------------------------------------------------ textutil
export const TR_UPPER = TABLES.consts.TR_UPPER!;
export const TR_LOWER = TABLES.consts.TR_LOWER!;
export const TR_LETTER = TABLES.consts.TR_LETTER!;
export const TR_LETTER_CLASS = TABLES.consts.TR_LETTER_CLASS!;
export const WORD_CLASS = TABLES.consts.WORD_CLASS!;
export const NOT_WORD_CLASS = WORD_CLASS.startsWith("[^") ? "[" + WORD_CLASS.slice(2) : "[^" + WORD_CLASS.slice(1);
export const SPACE_CLASS = TABLES.chars.space!;

export const trLower = (s: string) => lower(s.replaceAll("I", "ı").replaceAll("İ", "i"));
export const trUpper = (s: string) => upper(s.replaceAll("i", "İ").replaceAll("ı", "I"));
export const normalize = (s: string) => s.normalize("NFC").replaceAll("̇", "");
const FOLD: Record<string, string> = { ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u", â: "a", î: "i", û: "u" };
/** Lower-case and strip Turkish diacritics (textutil.fold) */
export function fold(s: string): string {
  return trLower(normalize(s)).replace(/[çğıöşüâîû]/g, c => FOLD[c]!);
}

const lists = new Map<string, ReadonlySet<string>>();
/** textutil.wordlist(name): already folded at build time by the Python engine */
export function wordlist(name: string): ReadonlySet<string> {
  let s = lists.get(name);
  if (!s) {
    const raw = WORDS[name];
    if (raw === undefined) throw new Error(`katip-mask: unknown word list ${name}`);
    s = new Set(raw ? raw.split("\n") : []);
    lists.set(name, s);
  }
  return s;
}

export const isCapitalised = (tok: string) => tok.length > 0 && isUpperChar([...tok][0]!);
export function isAllCaps(tok: string): boolean {
  const letters = [...tok].filter(c => CH.alpha.test(c));
  return letters.length >= 2 && letters.every(c => CH.upper.test(c));
}

/** re.escape(value) matched case-insensitively (re.I), as a JS source fragment */
export function literalIgnoreCase(value: string): string {
  let out = "";
  for (const c of value) {
    const eq = TABLES.ignorecase[c];
    out += eq ? "[" + [...eq].map(cp).join("") + "]" : esc(c);
  }
  return out;
}
/** re.escape(value) matched exactly, as a JS source fragment */
export function literal(value: string): string {
  let out = "";
  for (const c of value) out += esc(c);
  return out;
}
const cp = (c: string) => "\\u{" + c.codePointAt(0)!.toString(16) + "}";
const esc = (c: string) => (/[A-Za-z0-9 ]/.test(c) ? c : cp(c));

/** Python's round(x, 3): round half to even on the exact binary value */
export function round3(x: number): number {
  const t = x * 16;
  if (Number.isInteger(t) && Math.abs(t) % 2 === 1) {  // exact tie at 3 decimals (odd multiple of 1/16)
    const k = Math.floor(x * 1000);
    return (k % 2 === 0 ? k : k + 1) / 1000;
  }
  return Number(x.toFixed(3));
}

/** Python sorted(key=...) with tuple keys: stable, element-wise comparison */
export function sortBy<T>(arr: readonly T[], key: (x: T) => Array<number | string | boolean>): T[] {
  const withKeys = arr.map((x, i) => ({ x, k: key(x), i }));
  withKeys.sort((a, b) => {
    for (let j = 0; j < a.k.length; j++) {
      const p = a.k[j]!, q = b.k[j]!;
      if (p < q) return -1;
      if (p > q) return 1;
    }
    return a.i - b.i;
  });
  return withKeys.map(w => w.x);
}

// ------------------------------------------------------------------ working text
// The engine runs on text where every code point is one UTF-16 unit, so offsets equal Python's.
// Characters outside the BMP (emoji, rare letters) are replaced by a BMP character of the same kind.
const ASTRAL = /[\u{10000}-\u{10FFFF}]/u;
const STAND_IN: Array<[RegExp, string]> = [
  [/\p{L}/u, "ꀀ"], [/\p{Nd}/u, "٠"], [/\p{N}/u, "Ⅰ"], [/\p{M}/u, "̀"], [/\p{P}/u, "⁂"],
  [/\p{S}/u, "⌂"], [/\p{Co}/u, ""], [/\p{Cf}/u, "​"],
];
export interface WorkingText { text: string; toUtf16: (i: number) => number; fromUtf16: (i: number) => number; }

export function toWorkingText(text: string): WorkingText {
  if (!ASTRAL.test(text)) return { text, toUtf16: i => i, fromUtf16: i => i };
  let out = "";
  const astralAt: number[] = [];  // working offsets of astral characters
  for (const c of text) {
    if (c.length === 2) {
      astralAt.push(out.length);
      out += STAND_IN.find(([re]) => re.test(c))?.[1] ?? "͸";
    } else out += c;
  }
  // working offset -> UTF-16 offset: add one for every astral character before it
  const toUtf16 = (i: number) => {
    let lo = 0, hi = astralAt.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (astralAt[mid]! < i) lo = mid + 1; else hi = mid; }
    return i + lo;
  };
  // UTF-16 offset -> working offset (an offset inside a surrogate pair maps to the character's start)
  const fromUtf16 = (u: number) => {
    let lo = 0, hi = out.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (toUtf16(mid) < u) lo = mid + 1; else hi = mid; }
    return toUtf16(lo) > u ? lo - 1 : lo;
  };
  return { text: out, toUtf16, fromUtf16 };
}
