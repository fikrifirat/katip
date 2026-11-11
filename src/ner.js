// On-device NER with transformers.js. Word-level: each word's first sub-token label
// decides, so spans map back to exact character offsets in the document text.
// Models are served from this site (models/<id>/), never fetched from a model hub,
// so the page's CSP (own origin only) stays intact.
const WORD = /[\p{L}\p{N}][\p{L}\p{N}'’.-]*/gu;
const cache = new Map();

export async function loadNer(T, id, baseUrl, wasmUrl, onProgress, dtype = "q8") {
  if (cache.has(id)) return cache.get(id);
  T.env.allowRemoteModels = false;
  T.env.allowLocalModels = true;
  T.env.localModelPath = baseUrl; // must be a path, not an http(s) URL, or transformers.js skips local files
  T.env.useBrowserCache = false;
  T.env.backends.onnx.wasm.wasmPaths = wasmUrl;
  T.env.backends.onnx.wasm.numThreads = 1;
  const p = (async () => {
    onProgress?.("NER modeli yükleniyor");
    const tokenizer = await T.AutoTokenizer.from_pretrained(id);
    const model = await T.AutoModelForTokenClassification.from_pretrained(id, { dtype, device: "wasm" });
    return { tokenizer, model, id2label: model.config.id2label };
  })();
  cache.set(id, p);
  try { return await p; } catch (e) { cache.delete(id); throw e; }
}

export async function runNer(T, ner, text, { minScore = 0.5, maxTokens = 500 } = {}) {
  const { tokenizer, model, id2label } = ner;
  const wrap = tokenizer.encode("", { add_special_tokens: true });  // [CLS] [SEP] for BERT-style models
  const cls = wrap[0], sep = wrap.at(-1), unk = tokenizer.unk_token_id ?? tokenizer.encode("[UNK]", { add_special_tokens: false })[0] ?? 1;
  maxTokens = model.config.katip?.max_tokens ?? maxTokens;
  const words = [...text.matchAll(WORD)].map(m => {
    const ids = tokenizer.encode(m[0], { add_special_tokens: false });
    return { s: m.index, e: m.index + m[0].length, ids: ids.length ? ids : [unk] };
  });
  const labels = new Array(words.length);
  for (let w0 = 0; w0 < words.length;) {
    const ids = [cls], first = [];
    let w = w0;
    while (w < words.length && ids.length + words[w].ids.length < maxTokens - 1) {
      first.push(ids.length); ids.push(...words[w].ids); w++;
    }
    if (w === w0) { labels[w0] = { l: "O", p: 1 }; w0++; continue; }
    ids.push(sep);
    const n = ids.length, big = BigInt64Array.from(ids, BigInt);
    const out = await model({
      input_ids: new T.Tensor("int64", big, [1, n]),
      attention_mask: new T.Tensor("int64", new BigInt64Array(n).fill(1n), [1, n]),
      token_type_ids: new T.Tensor("int64", new BigInt64Array(n), [1, n]),
    });
    const L = out.logits, k = L.dims[2], d = L.data;
    first.forEach((pos, j) => {
      let best = 0, mx = -Infinity, sum = 0;
      for (let c = 0; c < k; c++) if (d[pos * k + c] > mx) { mx = d[pos * k + c]; best = c; }
      for (let c = 0; c < k; c++) sum += Math.exp(d[pos * k + c] - mx);
      labels[w0 + j] = { l: id2label[best] ?? "O", p: 1 / sum };
    });
    w0 = w;
  }
  // merge B-PER + I-PER runs (same rule as ml/eval_system.py), drop a Turkish case suffix after an apostrophe
  const spans = [];
  let cur = null;
  words.forEach((wd, i) => {
    const { l, p } = labels[i], per = /PER(SON)?$/i.test(l);
    const gap = i ? text.slice(words[i - 1].e, wd.s) : "";
    if (per && cur && !/^B-/.test(l) && /^[ \t,]*$/.test(gap)) { cur.e = wd.e; cur.ps.push(p); }
    else { if (cur) spans.push(cur); cur = per ? { s: wd.s, e: wd.e, ps: [p] } : null; }
  });
  if (cur) spans.push(cur);
  return spans.map(c => {
    const t = text.slice(c.s, c.e), k = Math.min(...["'", "’"].map(q => t.includes(q) ? t.indexOf(q) : t.length));
    return [c.s, c.s + k, c.ps.reduce((x, y) => x + y, 0) / c.ps.length];
  }).filter(x => x[2] >= minScore);
}
