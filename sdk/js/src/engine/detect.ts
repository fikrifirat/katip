// TypeScript port of local_detect.py and the overlap rules of analyzer.py (vendored at
// sdk/python/src/katip_mask/_engine/). Same recognizers, same overlap priority, same merges.
import {
  DIGIT_SLASH_CLASS, NOT_WORD_CLASS, TR_LETTER_CLASS, casefold, dyn, finditer, fold, isupper, isUpperChar, isAlnumChar, literal, match, pyIn, rfind, round3,
  search, sortBy, fullmatch, wordlist, strip, startsWithAny,
} from "./py.js";
import { TABLES } from "./generated.js";
import {
  ALL_ENTITIES, RecognizerResult, defaultRecognizers, dropPlaceNames, isLexical, ocrFormValues, ocrNameRepeats, ocrTckn,
  splitAddresses, type Recognizer, PersonRecognizer,
} from "./recognizers.js";

// ---- analyzer core (copied from analyzer.py into _analyzer_core.py at build time)
export const PRIORITY: Record<string, number> = {
  TCKN: 0, YKN: 0, PASSPORT: 1, FOREIGN_ID: 1, IBAN: 1, CREDIT_CARD: 2, VKN: 3, EMAIL: 4, ADDRESS: 5, PHONE: 6, PLATE: 7, PERSON: 8,
  BIRTH_DATE: 9, IP_ADDRESS: 10, HEALTH: 11, RELIGION: 11, POLITICAL: 11, UNION: 11, ETHNICITY: 11, SEXUAL_LIFE: 11,
  BIOMETRIC_GENETIC: 11, CRIMINAL_RECORD: 12,
};
export const FLAG_ONLY_DEFAULT = new Set(["CRIMINAL_RECORD"]);

export function resolveOverlaps(results: RecognizerResult[]): RecognizerResult[] {
  const ranked = sortBy(results, r => [PRIORITY[r.entity_type] ?? 99, -r.score, -(r.end - r.start)]);
  const kept: RecognizerResult[] = [];
  for (const r of ranked) if (kept.every(k => r.end <= k.start || r.start >= k.end)) kept.push(r);
  return sortBy(kept, r => [r.start]);
}

function mergeAdjacent(text: string, results: RecognizerResult[]): RecognizerResult[] {
  const out: RecognizerResult[] = [];
  for (const r of results) {
    const prev = out.at(-1);
    const gap = prev ? text.slice(prev.end, r.start) : "";
    if (prev && prev.entity_type === r.entity_type && strip(gap, " \t") === "" && !gap.includes("\n") && r.start - prev.end <= 2) {
      prev.end = r.end;
      prev.score = Math.max(prev.score, r.score);
    } else out.push(r);
  }
  return out;
}

let RECS: Recognizer[] | null = null;
const recognizers = () => (RECS ??= defaultRecognizers());

function dictionary(text: string, results: RecognizerResult[], maskTerms: readonly string[], allowTerms: readonly string[]): RecognizerResult[] {
  const allow = new Set(allowTerms.filter(t => strip(t)).map(t => strip(fold(t))));
  const kept = results.filter(r => !allow.has(strip(fold(text.slice(r.start, r.end)))));
  let ftext = "";
  for (const c of text) { const f = fold(c); ftext += [...f].length === 1 ? f : c; }
  for (const term of maskTerms) {
    const t = strip(fold(term));
    if ([...t].length < 2) continue;
    let i = ftext.indexOf(t);
    while (i >= 0) {
      const before = i ? ftext[i - 1]! : " ";
      const after = i + t.length < ftext.length ? ftext[i + t.length]! : " ";
      if (!isAlnumChar(before) && !isAlnumChar(after)) {
        const r = new RecognizerResult("PERSON", i, i + t.length, 0.99);
        r.recognition_metadata = { recognizer_name: "local_dictionary", explanation: "term in the local dictionary" };
        kept.push(r);
      }
      i = ftext.indexOf(t, i + 1);
    }
  }
  return kept;
}

type Extra = [number, number, number, string?];

function addModelSpan(text: string, results: RecognizerResult[], s: number, e: number, score: number, trust: number | null) {
  let toks = finditer("local_detect._TOK", text.slice(s, e)).map(m => [m.start() + s, m.end() + s] as [number, number]);
  const sure = trust !== null && score >= trust;
  if (!sure) {
    while (toks.length && isLexical(text.slice(toks[0]![0], toks[0]![1]))) toks.shift();
    while (toks.length && isLexical(text.slice(toks.at(-1)![0], toks.at(-1)![1]))) toks.pop();
  }
  if (!toks.length || !isUpperChar(text[toks[0]![0]]!)) return;
  if (toks.every(([a, b]) => personStop().has(fold(text.slice(a, b))))) return;
  s = toks[0]![0]; e = toks.at(-1)![1];
  const hits = results.filter(r => r.entity_type === "PERSON" && r.start < e && r.end > s);
  for (const r of hits) {
    r.start = Math.min(r.start, s); r.end = Math.max(r.end, e);
    r.recognition_metadata.explanation = strip((r.recognition_metadata.explanation ?? "") + " + model");
  }
  if (hits.length) return;
  const capital = toks.every(([a]) => isUpperChar(text[a]!));
  const known = toks.length === 1 && knownNameWords(text, results).has(casefold(text.slice(s, e)));
  const mid = search("inline.sentence_start", text.slice(Math.max(0, s - 4), s)) === null;
  const loneWord = toks.length === 1 && !known && isLexical(text.slice(s, e)) &&
    !(pyIn(text.slice(e, e + 1), "'’") && mid) && !(mid && !neverLoneName(text.slice(s, e), score));
  if (capital && (toks.length >= 2 || (sure && !loneWord) || known)) {
    const r = new RecognizerResult("PERSON", s, e, score);
    r.recognition_metadata = { recognizer_name: "name_tagger", explanation: "on-device model" };
    results.push(r);
  }
}

function joinModelNames(text: string, extra: readonly Extra[]): Extra[] {
  const out: Extra[] = [];
  for (const x of sortBy(extra, x => [x[0]])) {
    const typ = x.length > 3 ? x[3] ?? null : null;
    const prev = out.at(-1);
    const ptyp = prev ? (prev.length > 3 ? prev[3] ?? null : null) : null;
    if (prev && (typ === null || typ === "PERSON") && (ptyp === null || ptyp === "PERSON") && 0 < x[0] - prev[1] && x[0] - prev[1] <= 2 &&
      strip(text.slice(prev[1], x[0]), " ") === "" &&
      ![[prev[0], prev[1]], [x[0], x[1]]].some(([a, b]) => personStop().has(fold(text.slice(a, b))) || stopwords().has(fold(text.slice(a, b))))) {
      out[out.length - 1] = (prev.length > 3 ? [prev[0], x[1], Math.min(prev[2], x[2]), prev[3]] : [prev[0], x[1], Math.min(prev[2], x[2])]) as Extra;
    } else out.push([...x] as Extra);
  }
  return out;
}

function nameRepeats(text: string, results: RecognizerResult[]): RecognizerResult[] {
  const words = new Map<string, number>();
  for (const r of results) {
    if (r.entity_type !== "PERSON") continue;
    const toks = finditer("local_detect._TOK", text.slice(r.start, r.end));
    if (toks.length < 2) continue;
    for (const m of toks) {
      const w = m.group()!, f = fold(w);
      if ([...w].length >= 3 && isUpperChar(w[0]!) && !isupper(w) && !stopwords().has(f) && !personStop().has(f) && !isLexical(w))
        words.set(w, r.score);
    }
  }
  const covered: Array<[number, number]> = results.filter(r => r.entity_type === "PERSON").map(r => [r.start, r.end]);
  const out: RecognizerResult[] = [];
  for (const [w, sc] of words) {
    const rx = dyn(`(?<!${TR_LETTER_CLASS})${literal(w)}(?!${TR_LETTER_CLASS})`);
    for (const m of finditer(rx, text)) {
      const a = m.start(), b = m.end();
      if (covered.some(([x, y]) => x < b && y > a)) continue;
      const nxt = match("inline.next_word", text.slice(b, b + 40));
      if (nxt && isUpperChar(nxt.group(1)![0]!) && isLexical(nxt.group(1)!)) continue;
      covered.push([a, b]);
      out.push(mk("PERSON", a, b, sc, "same name word found earlier in the document", "name_repeat"));
    }
  }
  return out;
}

const stopwords = () => wordlist("stopwords_caps.txt");
const LONE_NAME_SCORE = Number(TABLES.consts.LONE_NAME_SCORE);

function neverLoneName(tok: string, score: number): boolean {
  const f = fold(tok);
  if (wordlist("stopwords_caps.txt").has(f) || personStop().has(f) || isupper(tok) || fullmatch("inline.roman", tok)) return true;
  if (!wordlist("common_words.txt").has(f)) return isLexical(tok);
  return score < LONE_NAME_SCORE;
}

let STOP: ReadonlySet<string> | null = null;
const personStop = () => (STOP ??= (recognizers().find(r => r instanceof PersonRecognizer) as PersonRecognizer | undefined)?.stop ?? new Set<string>());

function knownNameWords(text: string, results: RecognizerResult[]): Set<string> {
  const out = new Set<string>();
  for (const r of results) {
    if (r.entity_type !== "PERSON") continue;
    for (const m of finditer("local_detect._TOK", text.slice(r.start, r.end)))
      out.add(casefold(text.slice(m.start() + r.start, m.end() + r.start)));
  }
  return out;
}

function addModelTyped(text: string, results: RecognizerResult[], typ: string, s: number, e: number, score: number) {
  while (s < e && pyIn(text[s]!, " \t\n,.;:-")) s += 1;
  while (e > s && pyIn(text[e - 1]!, " \t\n,;:-")) e -= 1;
  if (e - s < 3) return;
  const hits = results.filter(r => r.entity_type === typ && r.start < e && r.end > s);
  for (const r of hits) {
    const a = Math.min(r.start, s), b = Math.max(r.end, e);
    if (results.some(o => o.entity_type !== typ && o.start < b && o.end > a && !(o.start < r.end && o.end > r.start))) continue;
    r.start = a; r.end = b;
    r.recognition_metadata.explanation = strip((r.recognition_metadata.explanation ?? "") + " + model");
  }
  if (hits.length) return;
  if (results.some(r => r.start < e && r.end > s)) return;
  if (typ === "ADDRESS" && finditer("local_detect._TOK", text.slice(s, e)).length < 2) return;
  const r = new RecognizerResult(typ, s, e, score);
  r.recognition_metadata = { recognizer_name: "pii_tagger", explanation: "on-device model" };
  results.push(r);
}

function mk(typ: string, s: number, e: number, score: number, why: string, name = "katip_postprocess"): RecognizerResult {
  const r = new RecognizerResult(typ, s, e, score);
  r.recognition_metadata = { recognizer_name: name, explanation: why };
  return r;
}

// ---- case details: the types of the stricter masking profiles
export const CASE_TYPES = ["CASE_NO", "BAR_NO", "DATE", "PLACE", "INSTITUTION"];

export function citationWindows(text: string): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  for (const m of finditer("local_detect._HIGH_COURT", text)) {
    let lim = text.indexOf("\n", m.end());
    lim = Math.min(lim >= 0 ? lim : text.length, m.end() + 260);
    const end = search("local_detect._CITE_END", text, m.end(), lim);
    const e = end ? end.end() : lim;
    let b = m.start();
    const line = rfind(text, "\n", b) + 1;
    const pre = text.slice(Math.max(line, b - 140), b);
    if (search("local_detect._CITE_BEFORE", pre)) b = Math.max(line, b - 140);
    out.push([b, e]);
  }
  return out;
}

function caseResults(text: string, entities: readonly string[]): RecognizerResult[] {
  const out: RecognizerResult[] = [];
  const cites = citationWindows(text);
  const add = (typ: string, s: number, e: number, sc: number, why: string) => {
    if (cites.some(([a, b]) => a <= s && e <= b)) return;
    out.push(mk(typ, s, e, sc, why, "case_details"));
  };
  if (entities.includes("CASE_NO"))
    for (let i = 0; i < 4; i++)
      for (const m of finditer(`local_detect._CASE_RES.${i}`, text)) {
        const g = m.groups ? 1 : 0;
        add("CASE_NO", m.start(g), m.end(g), 0.85, "case, file or document number");
      }
  if (entities.includes("CASE_NO")) {
    // the same number written again elsewhere is masked too, so one copy never gives the other away
    const seen = new Set(out.filter(r => r.entity_type === "CASE_NO").map(r => text.slice(r.start, r.end)));
    for (const v of seen)
      for (const m of finditer(dyn(`(?<!${DIGIT_SLASH_CLASS})${literal(v)}(?!${DIGIT_SLASH_CLASS})`), text))
        if (!out.some(r => r.start <= m.start() && m.start() < r.end))
          add("CASE_NO", m.start(), m.end(), 0.8, "same case number found earlier in the document");
  }
  if (entities.includes("BAR_NO"))
    for (const m of [...finditer("local_detect._BAR_RE", text), ...finditer("local_detect._STAFF_RE", text)])
      add("BAR_NO", m.start(1), m.end(1), 0.85, "bar or registry number");
  if (entities.includes("DATE"))
    for (let i = 0; i < 2; i++) for (const m of finditer(`local_detect._DATE_RES.${i}`, text)) add("DATE", m.start(), m.end(), 0.8, "date");
  if (entities.includes("INSTITUTION"))
    for (const m of finditer("local_detect._INST_RE", text)) add("INSTITUTION", m.start(), m.end(), 0.75, "court, company or institution name");
  if (entities.includes("PLACE")) {
    const places = wordlist("_place_words");
    for (const m of finditer("local_detect._TOK", text)) {
      const w = fold(m.group()!);
      if (places.has(w) && isUpperChar(text[m.start()]!)) add("PLACE", m.start(), m.end(), 0.75, "province or district");
    }
  }
  return out;
}

export interface EngineSpan {
  id: string; entity_type: string; start: number; end: number; text: string; score: number;
  recognizer: string; explanation: string; flag_only: boolean;
}

export interface EngineOptions {
  threshold?: number;
  entities?: readonly string[] | null;
  maskTerms?: readonly string[];
  allowTerms?: readonly string[];
  /** model spans: [start, end, score] or [start, end, score, type] in working-text offsets */
  extra?: readonly Extra[];
  trust?: number | null;
  ocrRanges?: ReadonlyArray<[number, number]>;
  addressDetail?: "street" | "full";
}

/** local_detect.detect */
export function detect(text: string, o: EngineOptions = {}): EngineSpan[] {
  const threshold = o.threshold ?? 0.5;
  const entities = o.entities && o.entities.length ? [...o.entities] : [...ALL_ENTITIES];
  const ocrRanges = (o.ocrRanges ?? []).map(([a, b]) => [a, b] as [number, number]);
  let results: RecognizerResult[] = [];
  const seen = new Set<string>();
  for (const rec of recognizers()) {
    if (!rec.supported_entities.some(e => entities.includes(e))) continue;
    for (const r of rec.analyze(text, entities) ?? []) {
      const key = `${r.entity_type}|${r.start}|${r.end}`;
      if (r.score >= threshold && !seen.has(key)) { seen.add(key); results.push(r); }
    }
  }
  const extra = joinModelNames(text, o.extra ?? []);
  for (const x of sortBy(extra, x => [x.length > 3 && x[3] !== undefined && x[3] !== null && x[3] !== "PERSON"])) {
    const [s, e, sc] = x;
    const typ = x.length > 3 && x[3] ? x[3] : "PERSON";
    if (!entities.includes(typ)) continue;
    if (typ === "PERSON") addModelSpan(text, results, s, e, sc, o.trust ?? null);
    else addModelTyped(text, results, typ, s, e, sc);
  }
  if (entities.includes("PERSON")) results.push(...nameRepeats(text, results));
  if (entities.includes("TCKN"))
    results.push(...ocrTckn(text, ocrRanges).filter(([, , sc]) => sc >= threshold).map(([s, e, sc, why]) => mk("TCKN", s, e, sc, why, "tckn_ocr")));
  results.push(...ocrFormValues(text, ocrRanges).filter(([t, , , sc]) => sc >= threshold && entities.includes(t))
    .map(([t, s, e, sc, why]) => mk(t, s, e, sc, why, "form_row_ocr")));
  results = dropPlaceNames(text, results);
  if (CASE_TYPES.some(t => entities.includes(t))) results.push(...caseResults(text, entities).filter(r => r.score >= threshold));
  results = dictionary(text, results, o.maskTerms ?? [], o.allowTerms ?? []);
  let merged = mergeAdjacent(text, resolveOverlaps(results));
  if (ocrRanges.length && entities.includes("PERSON")) {
    const rep = ocrNameRepeats(text, ocrRanges, merged).map(([s, e, sc, why]) => mk("PERSON", s, e, sc, why, "name_repeat_ocr"));
    if (rep.length) merged = mergeAdjacent(text, resolveOverlaps([...merged, ...rep]));
  }
  if ((o.addressDetail ?? "street") === "street") merged = splitAddresses(text, merged, mk);
  return merged.map((r, i) => ({
    id: `s${String(i).padStart(4, "0")}`, entity_type: r.entity_type, start: r.start, end: r.end, text: text.slice(r.start, r.end),
    score: round3(r.score), recognizer: r.recognition_metadata?.recognizer_name ?? "", explanation: r.recognition_metadata?.explanation ?? "",
    flag_only: FLAG_ONLY_DEFAULT.has(r.entity_type),
  }));
}

void NOT_WORD_CLASS; void startsWithAny;
