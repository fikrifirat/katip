"""katiplab: the small toolkit behind the Katip lab notebooks.

Everything the notebooks need lives here so each notebook cell stays short and readable:

  paths ............ ROOT, LAB, DATA, RUNS, RESULTS
  data ............. get_wikiner(), load_jsonl(), load_synth(), pack()
  detection ........ Tagger (onnxruntime port of the browser's ner.js), rules(), pipeline()
  scoring .......... score(), summary(), bootstrap_ci(), paired_bootstrap(), name_origin()
  training ......... train_tiny()  (same architecture and recipe as ml/train.py, plus real-text mixing)

Nothing here sends data anywhere. The only network call is get_wikiner(), which downloads a public
dataset (CC BY-SA 4.0) from GitHub once.
"""
from __future__ import annotations

import gzip, hashlib, json, math, os, random, re, sys, tempfile, time, urllib.request, zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np

# ----------------------------------------------------------------------------------------------- paths
def _find_root() -> Path:
    for p in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parent.parent]:
        if (p / "ml" / "eval_system.py").exists() and (p / "docs" / "katip_py.zip").exists():
            return p
    raise SystemExit("Run the notebooks from inside the katip repository (lab/ folder).")

ROOT = _find_root()
LAB = ROOT / "lab"
DATA, RUNS, RESULTS = LAB / "data", LAB / "runs", LAB / "results"
for _d in (DATA, RUNS, RESULTS): _d.mkdir(parents=True, exist_ok=True)
SYNTH = ROOT / "ml" / "berturk" / "data"          # synthetic sets as *.jsonl.gz
TINY = ROOT / "hf" / "model"                      # published katip-tr-name-tagger-tiny
BERTURK = ROOT / "ml" / "berturk" / "out"         # your local BERTurk run, if you trained it

# ----------------------------------------------------------------------------------------- the rules
# The exact detection code the browser runs (Pyodide bundle), unzipped once into a temp folder.
_zip = ROOT / "docs" / "katip_py.zip"
# keyed by the zip's hash, so a newer rule bundle is never shadowed by a stale unzipped copy
_bundle = Path(tempfile.gettempdir()) / f"katiplab_bundle_{__import__('hashlib').sha1(_zip.read_bytes()).hexdigest()[:10]}"
if not (_bundle / "local_detect.py").exists():
    zipfile.ZipFile(ROOT / "docs" / "katip_py.zip").extractall(_bundle)
sys.path.insert(0, str(_bundle))
import local_detect  # noqa: E402
from katip_redact.textutil import fold  # noqa: E402

# ------------------------------------------------------------------------------------------------ data
WIKINER_URL = ("https://raw.githubusercontent.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset/main/"
               "Turkish-Wiki-NER-Dataset/{split}.conll")
_NOSPACE_BEFORE = set(".,;:!?)]}%'’\"")

def conll_to_docs(path: Path) -> list[dict]:
    """CoNLL (word<TAB>BIO-tag per line, blank line between sentences) -> [{"text", "spans": [[a, b, TYPE]]}].
    Words are joined with single spaces, except no space before closing punctuation."""
    sents, cur = [], []
    for line in path.open(encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            if cur: sents.append(cur); cur = []
            continue
        w, t = line.split("\t") if "\t" in line else line.rsplit(" ", 1)
        cur.append((w, t))
    if cur: sents.append(cur)
    docs = []
    for s in sents:
        text, spans, open_span = "", [], None
        for w, t in s:
            if text and w not in _NOSPACE_BEFORE: text += " "
            a = len(text); text += w; b = len(text)
            if t.startswith("B-") or (t.startswith("I-") and not (open_span and open_span[2] == t[2:])):
                if open_span: spans.append(open_span)
                open_span = [a, b, t[2:]]
            elif t.startswith("I-"):
                open_span[1] = b
            else:
                if open_span: spans.append(open_span); open_span = None
        if open_span: spans.append(open_span)
        docs.append({"text": text, "spans": spans})
    return docs

def get_wikiner(force: bool = False) -> dict:
    """Download Turkish Wiki NER (Altinok 2023, CC BY-SA 4.0) once and convert it to jsonl.
    Returns {split: {"sentences", "persons", "sha256"}} and writes data/wikiner/MANIFEST.json."""
    d = DATA / "wikiner"; d.mkdir(exist_ok=True); manifest = {}
    for split in ("train", "dev", "test"):
        raw = d / f"{split}.conll"
        if force or not raw.exists():
            urllib.request.urlretrieve(WIKINER_URL.format(split=split), raw)
        docs = conll_to_docs(raw)
        with (d / f"{split}.jsonl").open("w", encoding="utf-8") as f:
            for i, doc in enumerate(docs):
                f.write(json.dumps({"id": f"wiki-{split}-{i}", **doc}, ensure_ascii=False) + "\n")
        manifest[split] = {"sentences": len(docs), "persons": sum(t == "PERSON" for x in docs for *_, t in x["spans"]),
                           "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()[:16]}
    (d / "MANIFEST.json").write_text(json.dumps({"source": WIKINER_URL, "licence": "CC BY-SA 4.0", **manifest}, indent=1))
    return manifest

def load_jsonl(path) -> list[dict]:
    path = Path(path); op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8") as f:
        docs = [json.loads(l) for l in f]
    for i, d in enumerate(docs): d.setdefault("id", f"{path.name.split('.')[0]}-{i}")
    return docs

def load_synth(name: str) -> list[dict]:
    """Katip's synthetic sets: train, dev, blind, heldout, negatives."""
    return load_jsonl(SYNTH / f"{name}.jsonl.gz")

def load_wiki(split: str) -> list[dict]:
    return load_jsonl(DATA / "wikiner" / f"{split}.jsonl")

def pack(sentences: list[dict], k: int = 8) -> list[dict]:
    """Join k sentences into one pseudo-document (newline-separated) so they train like Katip's documents."""
    out = []
    for i in range(0, len(sentences), k):
        text, spans = "", []
        for d in sentences[i:i + k]:
            if text: text += "\n"
            o = len(text); text += d["text"]; spans += [[a + o, b + o, t] for a, b, t in d["spans"]]
        out.append({"text": text, "spans": spans})
    return out

# ------------------------------------------------------------------------------------------- the model
import onnxruntime as ort  # noqa: E402
import regex  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

_TYPES = {"PER": "PERSON", "PERSON": "PERSON", "ADDR": "ADDRESS", "ADDRESS": "ADDRESS", "HEALTH": "HEALTH"}

class Tagger:
    """onnxruntime port of src/ner.js (same as ml/eval_system.ner), for any model folder with
    config.json, tokenizer.json and onnx/model_quantized.onnx (or onnx/model.onnx)."""

    def __init__(self, model_dir, quantized: bool = True):
        self.dir = Path(model_dir)
        self.cfg = json.loads((self.dir / "config.json").read_text())
        self.tok = Tokenizer.from_file(str(self.dir / "tokenizer.json"))
        f = self.dir / "onnx" / ("model_quantized.onnx" if quantized else "model.onnx")
        so = ort.SessionOptions(); so.intra_op_num_threads = 1   # one thread, like the browser
        self.sess = ort.InferenceSession(str(f), so)
        self.onnx_file = f
        self.word = regex.compile(self.cfg["katip"]["word_regex"]); self.maxtok = self.cfg["katip"]["max_tokens"]
        self.CLS, self.SEP, self.UNK = (self.tok.token_to_id(t) for t in ("[CLS]", "[SEP]", "[UNK]"))
        self.id2label = {int(k): v for k, v in self.cfg["id2label"].items()}
        self.inputs = {i.name for i in self.sess.get_inputs()}

    @property
    def size_mb(self) -> float:
        return self.onnx_file.stat().st_size / 1e6

    def word_labels(self, text: str):
        """[(start, end, label, prob)] for every word, in the browser's 256-token windows."""
        words = [(m.start(), m.end(), self.tok.encode(m.group(), add_special_tokens=False).ids or [self.UNK])
                 for m in self.word.finditer(text)]
        labels, w0 = [None] * len(words), 0
        while w0 < len(words):
            ids, first, w = [self.CLS], [], w0
            while w < len(words) and len(ids) + len(words[w][2]) < self.maxtok - 1:
                first.append(len(ids)); ids += words[w][2]; w += 1
            if w == w0: labels[w0] = ("O", 1.0); w0 += 1; continue
            ids.append(self.SEP); a = np.array([ids], dtype=np.int64)
            feed = {"input_ids": a, "attention_mask": np.ones_like(a), "token_type_ids": np.zeros_like(a)}
            lg = self.sess.run(["logits"], {k: v for k, v in feed.items() if k in self.inputs})[0][0]
            for j, pos in enumerate(first):
                z = lg[pos] - lg[pos].max(); p = np.exp(z) / np.exp(z).sum(); b = int(p.argmax())
                labels[w0 + j] = (self.id2label[b], float(p[b]))
            w0 = w
        return [(s, e, *labels[i]) for i, (s, e, _) in enumerate(words)]

    def __call__(self, text: str, min_score: float = 0.5):
        """Spans [(start, end, mean_prob, TYPE)], merged exactly like src/ner.js."""
        wl = self.word_labels(text); spans, cur = [], None
        for i, (s, e, l, p) in enumerate(wl):
            typ = None if l == "O" else _TYPES.get(l[2:])
            gap = text[wl[i - 1][1]:s] if i else ""
            if typ and cur and cur[3] == typ and l.startswith("I-") and re.fullmatch(
                    r"[ \t,\n./:-]*" if typ == "ADDRESS" else r"[ \t,]*", gap):
                cur[1] = e; cur[2].append(p)
            else:
                if cur: spans.append(cur)
                cur = [s, e, [p], typ] if typ else None
        if cur: spans.append(cur)
        out = []
        for s, e, ps, typ in spans:
            t = text[s:e]
            if typ == "PERSON": e = s + min([t.find(c) for c in "'’" if c in t] or [len(t)])  # drop case suffix
            if sum(ps) / len(ps) >= min_score: out.append((s, e, sum(ps) / len(ps), typ))
        return out

# ----------------------------------------------------------------------------------------- detectors
# A detector is any function text -> list of (start, end, TYPE). Three ways to find names:
def model_only(tagger):
    return lambda text: [(s, e, t) for s, e, _, t in tagger(text)]

def rules():
    return lambda text: [(d["start"], d["end"], d["entity_type"]) for d in local_detect.detect(text, extra=[])]

def pipeline(tagger, trust=None):
    """Rules + model with the browser's merge policy (what the demo actually runs)."""
    return lambda text: [(d["start"], d["end"], d["entity_type"])
                         for d in local_detect.detect(text, extra=tagger(text), trust=trust)]

# --------------------------------------------------------------------------------------------- scoring
_sq = lambda s: re.sub(r"\s+", "", s).casefold()
def matches(a: str, b: str) -> bool:
    """Katip's matching rule: detected a covers gold b, or a is a big enough part of b."""
    x, y = _sq(a), _sq(b)
    return y in x or (x in y and len(x) >= max(3, len(y) * 0.5))

_FIRST = {fold(w) for w in (_bundle / "katip_redact/data/first_names.txt").read_text(encoding="utf-8").split()}
_LAST = {fold(w) for w in (_bundle / "katip_redact/data/last_names.txt").read_text(encoding="utf-8").split()}
def name_origin(name: str) -> str:
    """'turkish' if any word of the name (case suffix removed) is in Katip's Turkish name lists, else 'other'.
    A rough proxy: it is used only to split results, never by a detector being scored... except the rules,
    which use the same lists. Keep that in mind when reading the split."""
    for w in re.split(r"\s+", name):
        w = re.split(r"['’]", w)[0]
        if fold(w) in _FIRST or fold(w) in _LAST: return "turkish"
    return "other"

def score(docs: list[dict], detect, etype: str = "PERSON"):
    """Run a detector over docs. Returns (gold_rows, span_rows, seconds):
       gold_rows: one per gold value  {doc, text, found, origin}
       span_rows: one per detected span of etype {doc, text, false, kind} (kind: 'other entity' or 'plain words')"""
    gold_rows, span_rows, t0 = [], [], time.perf_counter()
    for d in docs:
        text = d["text"]
        gold = [text[a:b] for a, b, t in d["spans"] if t == etype]
        other = [text[a:b] for a, b, t in d["spans"] if t != etype]
        found = [text[s:e] for s, e, t in detect(text) if t == etype]
        for g in gold:
            gold_rows.append({"doc": d["id"], "text": g, "found": any(matches(f, g) for f in found), "origin": name_origin(g)})
        for f in found:
            false = not any(matches(f, g) or matches(g, f) for g in gold)
            kind = ("other entity" if any(matches(f, o) or matches(o, f) for o in other) else "plain words") if false else ""
            span_rows.append({"doc": d["id"], "text": f, "false": false, "kind": kind})
    return gold_rows, span_rows, time.perf_counter() - t0

def summary(gold_rows, span_rows) -> dict:
    g, f = len(gold_rows), sum(r["found"] for r in gold_rows)
    s, fp = len(span_rows), sum(r["false"] for r in span_rows)
    p, r = (s - fp) / s if s else float("nan"), f / g if g else float("nan")
    return {"gold": g, "found": f, "recall": r, "spans": s, "false": fp, "precision": p,
            "f1": 2 * p * r / (p + r) if s and g and (p + r) else float("nan"),
            "f2": 5 * p * r / (4 * p + r) if s and g and (4 * p + r) else float("nan")}

def _by_doc(rows, key):
    agg = defaultdict(lambda: [0, 0])
    for r in rows: agg[r["doc"]][0] += 1; agg[r["doc"]][1] += bool(r[key])
    return agg

def bootstrap_ci(gold_rows, span_rows, B: int = 2000, seed: int = 0, alpha: float = 0.05) -> dict:
    """95% CI for recall and precision, resampling whole documents (names in one document are not independent)."""
    rng = np.random.default_rng(seed)
    gd, sd = _by_doc(gold_rows, "found"), _by_doc(span_rows, "false")
    ids = sorted(set(gd) | set(sd)); n = len(ids)
    if not n: return {"recall_ci": [float("nan")] * 2, "precision_ci": [float("nan")] * 2}
    G = np.array([gd.get(i, [0, 0]) for i in ids]).reshape(n, 2); S = np.array([sd.get(i, [0, 0]) for i in ids]).reshape(n, 2)
    rec, pre = [], []
    for _ in range(B):
        k = rng.integers(0, n, n); g, s = G[k].sum(0), S[k].sum(0)
        rec.append(g[1] / g[0] if g[0] else np.nan); pre.append((s[0] - s[1]) / s[0] if s[0] else np.nan)
    import warnings
    def q(v):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return [float(np.nanquantile(v, alpha / 2)), float(np.nanquantile(v, 1 - alpha / 2))]
    return {"recall_ci": q(rec), "precision_ci": q(pre)}

def paired_bootstrap(gold_a, gold_b, B: int = 5000, seed: int = 0) -> dict:
    """Recall difference B - A on the same gold values, with a document-level paired bootstrap.
    p is the share of resamples where B is not better than A (one-sided)."""
    assert [r["text"] for r in gold_a] == [r["text"] for r in gold_b], "score both systems on the same docs"
    per = defaultdict(lambda: [0, 0, 0])
    for a, b in zip(gold_a, gold_b): per[a["doc"]][0] += 1; per[a["doc"]][1] += a["found"]; per[a["doc"]][2] += b["found"]
    M = np.array(list(per.values())); rng = np.random.default_rng(seed); diffs = []
    for _ in range(B):
        s = M[rng.integers(0, len(M), len(M))].sum(0); diffs.append((s[2] - s[1]) / s[0])
    d = (M[:, 2].sum() - M[:, 1].sum()) / M[:, 0].sum()
    # McNemar's exact test on the discordant names, as a second opinion
    only_b = sum(b["found"] and not a["found"] for a, b in zip(gold_a, gold_b))
    only_a = sum(a["found"] and not b["found"] for a, b in zip(gold_a, gold_b))
    n = only_a + only_b
    p_mcnemar = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(only_a, only_b) + 1)) / 2 ** n) if n else 1.0
    return {"diff": float(d), "ci": [float(np.quantile(diffs, .025)), float(np.quantile(diffs, .975))],
            "p_bootstrap": float(np.mean(np.array(diffs) <= 0)), "only_a": only_a, "only_b": only_b, "p_mcnemar": p_mcnemar}

def evaluate(name: str, detect, sets: dict) -> dict:
    """Score one detector on several sets -> {set: summary + CI + ms/doc}. Keeps the raw rows in ._rows."""
    out = {}
    for sname, docs in sets.items():
        g, s, secs = score(docs, detect)
        out[sname] = {**summary(g, s), **bootstrap_ci(g, s), "ms_per_doc": 1000 * secs / max(1, len(docs)), "_rows": (g, s)}
    return out

# -------------------------------------------------------------------------------------------- training
WORD_RE = r"[\p{L}\p{N}][\p{L}\p{N}'’.-]*"

def train_tiny(out, real_docs=(), synth_docs=None, seed: int = 0, epochs: int = 5, maxtok: int = 256,
               vocab: int = 16000, log=print) -> dict:
    """Train katip-tr-name-tagger-tiny exactly like ml/train.py (2 layers, 128 hidden, own 16k WordPiece,
    word-level B/I-PER labels, OneCycle 1e-3, 5 epochs), with optional real documents mixed in.
    Exports onnx/model.onnx and onnx/model_quantized.onnx (int8) in the browser layout."""
    import torch
    from tokenizers import decoders, models, normalizers, pre_tokenizers, processors, trainers
    from transformers import BertConfig, BertForTokenClassification

    out = Path(out); (out / "onnx").mkdir(parents=True, exist_ok=True)
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.set_num_threads(min(8, os.cpu_count() or 4))
    synth_docs = load_synth("train") if synth_docs is None else synth_docs
    train = list(synth_docs) + list(real_docs)
    word = regex.compile(WORD_RE); labels = ["O", "B-PER", "I-PER"]

    tok = Tokenizer(models.WordPiece(unk_token="[UNK]"))
    tok.normalizer = normalizers.NFC(); tok.pre_tokenizer = pre_tokenizers.BertPreTokenizer(); tok.decoder = decoders.WordPiece()
    tok.train_from_iterator((d["text"] for d in train), trainers.WordPieceTrainer(
        vocab_size=vocab, min_frequency=2, special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]))
    CLS, SEP, PAD, UNK = (tok.token_to_id(t) for t in ("[CLS]", "[SEP]", "[PAD]", "[UNK]"))
    tok.post_processor = processors.TemplateProcessing(single="[CLS] $A [SEP]", special_tokens=[("[CLS]", CLS), ("[SEP]", SEP)])
    tok.save(str(out / "tokenizer.json"))
    cache = {}
    def wids(w):
        if w not in cache: cache[w] = tok.encode(w, add_special_tokens=False).ids or [UNK]
        return cache[w]

    def examples(doc, jitter):
        text = doc["text"]; spans = [s for s in doc["spans"] if s[2] == "PERSON"]
        words = [(m.start(), m.end(), m.group()) for m in word.finditer(text)]
        lab = []
        for s, e, _ in words:
            l = 0
            for a, b, _t in spans:
                if s < b and e > a: l = 1 if s <= a else 2; break
            lab.append(l)
        seqs, i = [], (random.randrange(0, 40) if jitter and len(words) > 80 else 0)
        i = min(i, max(0, len(words) - 1))
        while i < len(words):
            ids, labs, j = [CLS], [-100], i
            while j < len(words):
                wi = wids(words[j][2])
                if len(ids) + len(wi) >= maxtok - 1: break
                labs += [lab[j]] + [-100] * (len(wi) - 1); ids += wi; j += 1
            if j == i: i += 1; continue
            seqs.append((ids + [SEP], labs + [-100])); i = j
        return seqs

    def batches(seqs, bs):
        order = list(range(len(seqs))); random.shuffle(order)
        for k in range(0, len(order), bs):
            chunk = [seqs[o] for o in order[k:k + bs]]; n = max(len(c[0]) for c in chunk)
            ids = torch.full((len(chunk), n), PAD); labs = torch.full((len(chunk), n), -100); mask = torch.zeros((len(chunk), n), dtype=torch.long)
            for r, (a, b) in enumerate(chunk):
                ids[r, :len(a)] = torch.tensor(a); labs[r, :len(b)] = torch.tensor(b); mask[r, :len(a)] = 1
            yield ids, mask, labs

    cfg = BertConfig(vocab_size=tok.get_vocab_size(), hidden_size=128, num_hidden_layers=2, num_attention_heads=2,
                     intermediate_size=512, max_position_embeddings=maxtok, num_labels=3,
                     id2label=dict(enumerate(labels)), label2id={l: i for i, l in enumerate(labels)})
    model = BertForTokenClassification(cfg)
    BS = 32
    n_seqs = sum(len(examples(d, False)) for d in train)
    steps = epochs * math.ceil(n_seqs / BS)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-3, total_steps=steps + 50, pct_start=0.1)
    log(f"{len(train)} docs ({len(real_docs)} real) · {n_seqs} sequences · {sum(p.numel() for p in model.parameters()):,} params · {steps} steps")
    t0, step = time.time(), 0
    model.train()
    for ep in range(epochs):
        seqs = [s for d in train for s in examples(d, True)]
        for ids, mask, labs in batches(seqs, BS):
            loss = model(input_ids=ids, attention_mask=mask, labels=labs).loss
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); opt.zero_grad()
            if step < steps + 49: sched.step()
            step += 1
        log(f"  epoch {ep + 1}/{epochs}  loss {loss.item():.4f}  ({time.time() - t0:.0f}s)")
    model.eval()
    cfgd = json.loads(cfg.to_json_string()); cfgd["architectures"] = ["BertForTokenClassification"]; cfgd["model_type"] = "bert"
    cfgd["katip"] = {"word_regex": WORD_RE, "max_tokens": maxtok, "labels": "word-level BIO on first sub-token",
                     "lab": {"real_docs": len(real_docs), "synth_docs": len(synth_docs), "seed": seed, "epochs": epochs}}
    (out / "config.json").write_text(json.dumps(cfgd, indent=1))
    (out / "tokenizer_config.json").write_text(json.dumps({"tokenizer_class": "BertTokenizer", "do_lower_case": False,
        "model_max_length": maxtok, "cls_token": "[CLS]", "sep_token": "[SEP]", "unk_token": "[UNK]", "pad_token": "[PAD]", "mask_token": "[MASK]"}, indent=1))

    class Wrap(torch.nn.Module):
        def __init__(s, m): super().__init__(); s.m = m
        def forward(s, input_ids, attention_mask, token_type_ids):
            return s.m(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids).logits
    x = torch.tensor([[CLS, 10, 11, SEP]])
    torch.onnx.export(Wrap(model), (x, torch.ones_like(x), torch.zeros_like(x)), str(out / "onnx/model.onnx"),
                      input_names=["input_ids", "attention_mask", "token_type_ids"], output_names=["logits"],
                      dynamic_axes={k: {0: "batch", 1: "seq"} for k in ("input_ids", "attention_mask", "token_type_ids", "logits")},
                      opset_version=17, dynamo=False)
    import logging; logging.getLogger().setLevel(logging.ERROR)
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(str(out / "onnx/model.onnx"), str(out / "onnx/model_quantized.onnx"), weight_type=QuantType.QInt8)
    info = {"seconds": round(time.time() - t0), "int8_mb": round((out / "onnx/model_quantized.onnx").stat().st_size / 1e6, 2)}
    (out / "train_info.json").write_text(json.dumps({**cfgd["katip"]["lab"], **info}, indent=1))
    log(f"  saved {out.name}: int8 {info['int8_mb']} MB, {info['seconds']} s")
    return info
