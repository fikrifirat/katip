"""Katip Mask Mini: a 15-30 MB browser tagger taught by Katip Mask Base (knowledge distillation).

Runs on a free Kaggle/Colab GPU (about 1-2 h), never needed on a laptop:

  git clone -b legal-study https://github.com/fikrifirat/katip && cd katip/lab
  pip install -q -r requirements.txt onnx onnxruntime
  python mini/train_mini.py            # MODE=smoke python mini/train_mini.py  -> 5-minute check first

What it does, in order (all choices on dev, the test sets are scored once at the end):
  1. Training text: Katip's synthetic documents + Turkish Wiki NER *train* split (packed 8 sentences per doc)
     + TurkishLegalNER *train* split with its name slots refilled + the foreign-name training files.
     None of KVKK-Bench's test documents (TLNER test split, Wiki NER test split, fresh names) are used.
  2. Teacher: f1k/katip-mask-base (v2). Its per-word name probabilities are the soft labels.
  3. Students, trained from scratch with a 32k WordPiece vocabulary learned on this real + synthetic text
     (Nano's 16k vocabulary was learned on templates only), loss 1/2 gold CE + 1/2 T^2 KL at T = 2:
       mini-a 384x4 (~20 MB) · mini-b 384x6 (~23 MB) · mini-c 512x4 (~29 MB)
  4. Trust per student chosen on dev (Wiki NER dev + synthetic heldout, notebook 2's rule); the smallest model
     within 0.5 F2 points of the best dev score wins.
  5. Wiki NER test + synthetic blind/negatives scored once for the winner; results in mini/results.json.
Then run lab/legal/bench_run.py on the winner for KVKK-Bench (add a "mini" row there).

Licence: the training text includes Turkish Wiki NER (CC BY-SA 4.0), so Mini ships under CC BY-SA 4.0 like
Nano and Base. An Apache-2.0 Mini needs the clean teacher (no Wikipedia) and no --wiki text.
"""
import json, os, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import katiplab as K  # noqa: E402
import distill as D  # noqa: E402
import legal  # noqa: E402

MODE = os.environ.get("MODE", "full")
TEACHER = os.environ.get("TEACHER", "f1k/katip-mask-base")
STUDENTS = os.environ.get("STUDENTS", "mini-a,mini-b,mini-c").split(",") if MODE != "smoke" else [os.environ.get("STUDENTS", "mini-a").split(",")[0]]
VOCAB = int(os.environ.get("VOCAB", "32000"))       # Nano v2: STUDENTS=tiny VOCAB=16000
NAME = os.environ.get("NAME", "katip-mask-mini")
EPOCHS = 6 if MODE != "smoke" else 1
OUT = HERE / ("runs" if MODE != "smoke" else "runs_smoke")
OUT.mkdir(exist_ok=True)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

# 1 · training text
if not (K.DATA / "wikiner" / "train.jsonl").exists(): K.get_wikiner()
if not (K.DATA / "foreign" / "train-court-foreign.jsonl").exists():
    import subprocess; subprocess.run([sys.executable, str(HERE.parent / "foreign" / "build.py")], check=True)
synth = K.load_synth("train")
wiki = K.load_wiki("train"); random.Random(0).shuffle(wiki)
real = K.pack(wiki)
court = [d for d in legal.build("common", seed=0) if d.get("split") == "train"]
foreign = [d for f in ("train-court-foreign.jsonl", "train-petition-foreign.jsonl")
           if (K.DATA / "foreign" / f).exists() for d in K.load_jsonl(K.DATA / "foreign" / f)]
docs = synth + real + court + foreign
for d in docs: d["spans"] = [s for s in d["spans"] if s[2] == "PERSON"]
if MODE == "smoke": docs = synth[:300] + real[:100] + court[:50]
log(f"training text: {len(synth)} synthetic, {len(real)} Wiki NER, {len(court)} court, {len(foreign)} foreign -> {len(docs)} docs")

# 2 · teacher
if TEACHER == "none":     # local smoke test without a download: plain training, no soft labels
    tdir = None
elif Path(TEACHER).is_dir():
    tdir = TEACHER
else:
    from huggingface_hub import snapshot_download
    tdir = snapshot_download(TEACHER, allow_patterns=["config.json", "tokenizer*", "vocab.txt", "special_tokens_map.json", "*.safetensors"])
soft = D.soft_labels(tdir, docs, device="auto", bs=64, log=log) if tdir else None

# 3 · students
dev_sets = {"wiki dev": K.load_wiki("dev"), "heldout": K.load_synth("heldout")}
if MODE == "smoke": dev_sets = {k: v[:100] for k, v in dev_sets.items()}
cands = []
for arch in STUDENTS:
    out = OUT / f"{NAME}-{arch}"
    info = D.train_student(out, docs, soft=soft, arch=arch, kd_weight=0.5, temperature=2.0, epochs=EPOCHS,
                           vocab=VOCAB, device="auto", lr=float(os.environ.get("LR", "6e-4")), bs=64, log=log)
    trust, row = D.choose_trust(D.dev_table(K.Tagger(out), dev_sets))
    cands.append({"arch": arch, "dir": str(out), "int8_mb": info["int8_mb"], "trust": trust,
                  "wiki dev f2": row["wiki dev f2"], "wiki dev recall": row["wiki dev recall"],
                  "wiki dev precision": row["wiki dev precision"], "heldout recall": row["heldout recall"]})
    log(json.dumps(cands[-1]))

# 4 · pick: smallest within 0.5 F2 points of the best dev score
best = max(c["wiki dev f2"] for c in cands)
win = sorted([c for c in cands if c["wiki dev f2"] >= best - 0.005], key=lambda c: c["int8_mb"])[0]
log("winner:", win["arch"], win["int8_mb"], "MB, trust", win["trust"])

# 5 · test, once
tg = K.Tagger(Path(win["dir"]))
test_sets = {"wiki test": K.load_wiki("test"), "blind": K.load_synth("blind"), "negatives": K.load_synth("negatives")}
if MODE == "smoke": test_sets = {k: v[:100] for k, v in test_sets.items()}
res = K.evaluate("mini", K.pipeline(tg, trust=win["trust"]), test_sets)
summary = {k: {m: v for m, v in r.items() if not m.startswith("_")} for k, r in res.items()}
(OUT / f"{NAME}_results.json").write_text(json.dumps(
    {"mode": MODE, "teacher": TEACHER, "candidates": cands, "winner": win, "test": summary}, indent=1, default=float))
log(json.dumps(summary, default=float)[:800])
