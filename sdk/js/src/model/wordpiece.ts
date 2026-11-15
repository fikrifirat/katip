import { SPACE_CLASS } from "../engine/py.js";

// BERT WordPiece as configured in a tokenizer.json (BertNormalizer or NFC, BertPreTokenizer).
// TypeScript twin of WordPiece in sdk/python/src/katip_mask/ner.py; both are tested against each other.

export interface TokenizerJson {
  model: { type: string; vocab: Record<string, number>; continuing_subword_prefix?: string; max_input_chars_per_word?: number; unk_token?: string };
  normalizer?: { type?: string; normalizers?: Array<{ type: string }>; handle_chinese_chars?: boolean; lowercase?: boolean;
    strip_accents?: boolean | null; clean_text?: boolean } | null;
}

const isPunct = (c: string) => {
  const cp = c.codePointAt(0)!;
  return (cp >= 33 && cp <= 47) || (cp >= 58 && cp <= 64) || (cp >= 91 && cp <= 96) || (cp >= 123 && cp <= 126) || /\p{P}/u.test(c);
};
const isCjk = (cp: number) =>
  (cp >= 0x4e00 && cp <= 0x9fff) || (cp >= 0x3400 && cp <= 0x4dbf) || (cp >= 0x20000 && cp <= 0x2a6df) || (cp >= 0x2a700 && cp <= 0x2b73f) ||
  (cp >= 0x2b740 && cp <= 0x2b81f) || (cp >= 0x2b820 && cp <= 0x2ceaf) || (cp >= 0xf900 && cp <= 0xfaff) || (cp >= 0x2f800 && cp <= 0x2fa1f);
const SPACE = new RegExp("^" + SPACE_CLASS + "$", "u");  // Python str.isspace()

export class WordPiece {
  readonly vocab: Map<string, number>;
  readonly unk: number;
  readonly cls: number;
  readonly sep: number;
  private prefix: string;
  private maxChars: number;
  private nfc: boolean;
  private chinese: boolean;
  private lower: boolean;
  private stripAccents: boolean;
  private clean: boolean;

  constructor(tok: TokenizerJson) {
    const m = tok.model;
    if (m.type !== "WordPiece") throw new Error(`unsupported tokenizer model ${m.type}`);
    this.vocab = new Map(Object.entries(m.vocab));
    this.prefix = m.continuing_subword_prefix ?? "##";
    this.maxChars = m.max_input_chars_per_word ?? 100;
    this.unk = this.vocab.get(m.unk_token ?? "[UNK]")!;
    this.cls = this.vocab.get("[CLS]")!;
    this.sep = this.vocab.get("[SEP]")!;
    const norm = tok.normalizer ?? {};
    const kinds = norm.type === "Sequence" ? (norm.normalizers ?? []).map(n => n.type) : [norm.type];
    this.nfc = kinds.includes("NFC");
    const bert = norm.type === "BertNormalizer" ? norm : {};
    this.chinese = !!bert.handle_chinese_chars;
    this.lower = !!bert.lowercase || kinds.includes("Lowercase");
    this.stripAccents = bert.strip_accents ?? this.lower;
    this.clean = !!bert.clean_text;
  }

  private normalize(w: string): string {
    if (this.nfc) w = w.normalize("NFC");
    if (this.clean) {
      let o = "";
      for (const c of w) {
        const cp = c.codePointAt(0)!;
        if (cp === 0 || cp === 0xfffd || (/\p{C}/u.test(c) && !"\t\n\r".includes(c))) continue;
        o += "\t\n\r".includes(c) || /\p{Zs}/u.test(c) ? " " : c;
      }
      w = o;
    }
    if (this.chinese) w = [...w].map(c => (isCjk(c.codePointAt(0)!) ? ` ${c} ` : c)).join("");
    if (this.lower) w = w.toLowerCase();
    if (this.stripAccents) w = w.normalize("NFD").replace(/\p{Mn}/gu, "");
    return w;
  }

  private *pieces(word: string): Generator<string> {
    let cur = "";
    for (const ch of word) {
      if (SPACE.test(ch)) { if (cur) yield cur; cur = ""; }
      else if (isPunct(ch)) { if (cur) yield cur; cur = ""; yield ch; }
      else cur += ch;
    }
    if (cur) yield cur;
  }

  encode(word: string): number[] {
    const ids: number[] = [];
    for (const piece of this.pieces(this.normalize(word))) {
      const cps = [...piece];
      if (cps.length > this.maxChars) { ids.push(this.unk); continue; }
      let start = 0, sub: number[] = [];
      while (start < cps.length) {
        let end = cps.length, hit: number | undefined;
        while (start < end) {
          const s = (start === 0 ? "" : this.prefix) + cps.slice(start, end).join("");
          hit = this.vocab.get(s);
          if (hit !== undefined) break;
          end -= 1;
        }
        if (hit === undefined) { sub = [this.unk]; break; }
        sub.push(hit);
        start = end;
      }
      ids.push(...sub);
    }
    return ids;
  }
}
