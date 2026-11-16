// On-device name model with ONNX Runtime: same decoding as src/ner.js, Katip Kalkan and the Python SDK.
import { WordPiece, type TokenizerJson } from "./wordpiece.js";

/** The subset of onnxruntime-node / onnxruntime-web that the SDK uses. */
export interface OrtLike {
  InferenceSession: { create(model: Uint8Array, options?: Record<string, unknown>): Promise<OrtSession> };
  Tensor: new (type: "int64", data: BigInt64Array, dims: number[]) => unknown;
}
export interface OrtSession {
  inputNames: readonly string[];
  outputNames: readonly string[];
  run(feeds: Record<string, unknown>): Promise<Record<string, { data: ArrayLike<number>; dims: readonly number[] }>>;
}

export interface ModelFiles { config: Uint8Array; tokenizer: Uint8Array; onnx: Uint8Array }

const WORD = /[\p{L}\p{N}](?:[\p{L}\p{N}]|['’.-])*/gu;
const TYPES: Record<string, string> = { PER: "PERSON", PERSON: "PERSON", ADDR: "ADDRESS", ADDRESS: "ADDRESS", HEALTH: "HEALTH" };
const GLUE_ADDR = /^[ \t,\n./:-]*$/u, GLUE = /^[ \t,]*$/u;

export type ModelSpan = [number, number, number, string];

export class NameModel {
  private constructor(readonly name: string, private ort: OrtLike, private session: OrtSession, private tok: WordPiece,
    private id2label: Record<number, string>, private maxTokens: number, readonly trust: number) {}

  static async load(name: string, files: ModelFiles, ort: OrtLike, trust?: number, sessionOptions: Record<string, unknown> = {}): Promise<NameModel> {
    const dec = new TextDecoder();
    const config = JSON.parse(dec.decode(files.config));
    const tok = new WordPiece(JSON.parse(dec.decode(files.tokenizer)) as TokenizerJson);
    const session = await ort.InferenceSession.create(files.onnx, { executionProviders: ["cpu"], logSeverityLevel: 3, ...sessionOptions });
    const id2label: Record<number, string> = {};
    for (const [k, v] of Object.entries(config.id2label as Record<string, string>)) id2label[Number(k)] = v;
    return new NameModel(name, ort, session, tok, id2label, Number(config.katip?.max_tokens ?? 500), trust ?? Number(config.katip?.trust ?? 0.5));
  }

  /** [start, end, score, type] in offsets of `text`; `text` must have one UTF-16 unit per code point. */
  async spans(text: string, minScore = 0.5): Promise<ModelSpan[]> {
    const words = [...text.matchAll(WORD)].map(m => {
      const ids = this.tok.encode(m[0]);
      return { s: m.index!, e: m.index! + m[0].length, ids: ids.length ? ids : [this.tok.unk] };
    });
    const labels: Array<[string, number]> = words.map(() => ["O", 1]);
    for (let w0 = 0; w0 < words.length;) {
      const ids = [this.tok.cls], first: number[] = [];
      let w = w0;
      while (w < words.length && ids.length + words[w]!.ids.length < this.maxTokens - 1) {
        first.push(ids.length);
        ids.push(...words[w]!.ids);
        w++;
      }
      if (w === w0) { w0++; continue; }
      ids.push(this.tok.sep);
      const n = ids.length;
      const feeds: Record<string, unknown> = {
        input_ids: new this.ort.Tensor("int64", BigInt64Array.from(ids, BigInt), [1, n]),
        attention_mask: new this.ort.Tensor("int64", new BigInt64Array(n).fill(1n), [1, n]),
      };
      if (this.session.inputNames.includes("token_type_ids")) feeds.token_type_ids = new this.ort.Tensor("int64", new BigInt64Array(n), [1, n]);
      const out = await this.session.run(feeds);
      const logits = out[this.session.outputNames[0]!]!;
      const k = logits.dims[2]!, d = logits.data;
      first.forEach((pos, j) => {
        let best = 0, mx = -Infinity;
        for (let c = 0; c < k; c++) if (d[pos * k + c]! > mx) { mx = d[pos * k + c]!; best = c; }
        let sum = 0;
        for (let c = 0; c < k; c++) sum += Math.exp(d[pos * k + c]! - mx);
        labels[w0 + j] = [this.id2label[best] ?? "O", 1 / sum];
      });
      w0 = w;
    }
    const spans: Array<{ s: number; e: number; ps: number[]; t: string }> = [];
    let cur: { s: number; e: number; ps: number[]; t: string } | null = null;
    words.forEach((wd, i) => {
      const [l, p] = labels[i]!;
      const typ = l === "O" ? null : TYPES[l.replace(/^[BI]-/, "")] ?? null;
      const gap = i ? text.slice(words[i - 1]!.e, wd.s) : "";
      if (typ && cur && cur.t === typ && l.startsWith("I-") && (typ === "ADDRESS" ? GLUE_ADDR : GLUE).test(gap)) { cur.e = wd.e; cur.ps.push(p); }
      else { if (cur) spans.push(cur); cur = typ ? { s: wd.s, e: wd.e, ps: [p], t: typ } : null; }
    });
    if (cur) spans.push(cur);
    const out: ModelSpan[] = [];
    for (const c of spans) {
      const t = text.slice(c.s, c.e);
      let k = t.length;
      if (c.t === "PERSON") for (const q of ["'", "’"]) if (t.includes(q)) k = Math.min(k, t.indexOf(q));
      const score = c.ps.reduce((a, b) => a + b, 0) / c.ps.length;
      if (score >= minScore && k) out.push([c.s, c.s + k, score, c.t]);
    }
    return out;
  }
}
