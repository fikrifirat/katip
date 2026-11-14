"""Score rules-only vs rules + name tagger on eval sets (text), with the exact browser code:
the Pyodide bundle (katip_py.zip, unzipped in ./bundle) + an onnxruntime port of ner.js.

  python eval_system.py <model dir> <eval dir> [<eval dir> ...]
"""
import json, re, sys, time
from pathlib import Path
import numpy as np, onnxruntime as ort, regex
from tokenizers import Tokenizer
_b = Path(__import__('os').environ.get('KBUNDLE', Path(__file__).parent / 'bundle'))
if not (_b / "local_detect.py").exists():  # no unzipped build: use the one in docs/
    import tempfile, zipfile; _b = Path(tempfile.mkdtemp()); zipfile.ZipFile(Path(__file__).parents[1] / "docs" / "katip_py.zip").extractall(_b)
sys.path.insert(0, str(_b))
import local_detect  # noqa: E402

mdir = Path(sys.argv[1] if __name__ == "__main__" else __import__("os").environ["KATIP_MODEL"]); cfg = json.loads((mdir / "config.json").read_text())
tok = Tokenizer.from_file(str(mdir / "tokenizer.json"))
onnx_file = mdir / "onnx" / ("model_quantized.onnx" if "--q8" in sys.argv or __name__ != "__main__" else "model.onnx")
sess = ort.InferenceSession(str(onnx_file))
WORD = regex.compile(cfg["katip"]["word_regex"]); MAXTOK = cfg["katip"]["max_tokens"]
CLS, SEP, UNK = (tok.token_to_id(t) for t in ("[CLS]", "[SEP]", "[UNK]"))
id2label = {int(k): v for k, v in cfg["id2label"].items()}

def ner(text, min_score=float(__import__("os").environ.get("MINS", 0.5))):
    words = [(m.start(), m.end(), tok.encode(m.group(), add_special_tokens=False).ids or [UNK]) for m in WORD.finditer(text)]
    labels = [None] * len(words); w0 = 0
    while w0 < len(words):
        ids, first, w = [CLS], [], w0
        while w < len(words) and len(ids) + len(words[w][2]) < MAXTOK - 1:
            first.append(len(ids)); ids += words[w][2]; w += 1
        if w == w0: labels[w0] = ("O", 1.0); w0 += 1; continue
        ids.append(SEP); a = np.array([ids], dtype=np.int64)
        lg = sess.run(["logits"], {"input_ids": a, "attention_mask": np.ones_like(a), "token_type_ids": np.zeros_like(a)})[0][0]
        for j, pos in enumerate(first):
            z = lg[pos] - lg[pos].max(); p = np.exp(z) / np.exp(z).sum(); b = int(p.argmax())
            labels[w0 + j] = (id2label[b], float(p[b]))
        w0 = w
    spans, cur = [], None  # same merge as src/ner.js
    for i, (s, e, _) in enumerate(words):
        l, p = labels[i]; typ = None if l == "O" else TYPES.get(l[2:])
        gap = text[words[i - 1][1]:s] if i else ""
        if typ and cur and cur[3] == typ and l.startswith("I-") and re.fullmatch(r"[ \t,\n./:-]*" if typ == "ADDRESS" else r"[ \t,]*", gap):
            cur[1] = e; cur[2].append(p)
        else:
            if cur: spans.append(cur)
            cur = [s, e, [p], typ] if typ else None
    if cur: spans.append(cur)
    out = []
    for s, e, ps, typ in spans:
        t = text[s:e]
        if typ == "PERSON": e = s + min([t.find(c) for c in "'’" if c in t] or [len(t)])  # drop Turkish case suffix after apostrophe
        if sum(ps) / len(ps) >= min_score: out.append((s, e, sum(ps) / len(ps), typ))
    return out

TYPES = {"PER": "PERSON", "PERSON": "PERSON", "ADDR": "ADDRESS", "ADDRESS": "ADDRESS", "HEALTH": "HEALTH"}
sq = lambda s: re.sub(r"\s+", "", s).casefold()
def matches(a, b): x, y = sq(a), sq(b); return y in x or (x in y and len(x) >= max(3, len(y) * 0.5))

def score(d, use_ner):
    R = {"gold": 0, "found": 0, "unseen_gold": 0, "unseen_found": 0, "spans": 0, "fp": 0, "docs": 0, "ms": 0.0, "leaked_chars": 0}
    for f in sorted(Path(d).glob("*.txt")):
        text = f.read_text(encoding="utf-8"); gf = f.with_suffix(".gold.json")
        gold = [g for g in (json.loads(gf.read_text()) if gf.exists() else []) if g["entity_type"] == "PERSON"]
        t0 = time.time()
        extra = ner(text) if use_ner else []
        spans = [s for s in local_detect.detect(text, extra=extra) if s["entity_type"] == "PERSON"]
        R["ms"] += (time.time() - t0) * 1000; R["docs"] += 1
        allgold = [g for g in (json.loads(gf.read_text()) if gf.exists() else [])]
        for g in gold:
            ok = any(matches(s["text"], g["text"]) for s in spans)
            R["gold"] += 1; R["found"] += ok
            if g.get("unseen"): R["unseen_gold"] += 1; R["unseen_found"] += ok
        R["spans"] += len(spans)
        R["fp"] += sum(1 for s in spans if not any(matches(s["text"], g["text"]) or matches(g["text"], s["text"]) for g in allgold))
    return R

if __name__ == "__main__":
  for d in [a for a in sys.argv[2:] if not a.startswith("--")]:
    for use in (False, True):
        r = score(d, use)
        print(f"{Path(d).name:10} {'rules+tagger' if use else 'rules only  '}  PERSON recall {r['found']}/{r['gold']} = {r['found'] / max(1, r['gold']):.3f}"
              f"  unseen {r['unseen_found']}/{r['unseen_gold']}  false names {r['fp']}  ({r['ms'] / max(1, r['docs']):.0f} ms/doc)")
