"""Train katip-tr-name-tagger: a tiny BERT token classifier for Turkish person names.

Word-level BIO labels (B-PER/I-PER/O) on the first sub-token of each word, the same
word split the browser uses (ner.js), so offsets map back exactly. Trained from
scratch on synthetic legal documents (gen_train.py); exported to ONNX for
transformers.js (fp32 + int8).

  python train.py train.jsonl dev.jsonl <out dir>
"""
import json, math, random, sys, time
from pathlib import Path
import regex, torch
from tokenizers import Tokenizer, decoders, models, normalizers, pre_tokenizers, processors, trainers
from transformers import BertConfig, BertForTokenClassification

torch.manual_seed(0); random.seed(0); torch.set_num_threads(4)
train_p, dev_p, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
(out / "onnx").mkdir(parents=True, exist_ok=True)
WORD = regex.compile(r"[\p{L}\p{N}][\p{L}\p{N}'’.-]*")
LABELS = ["O", "B-PER", "I-PER"]
MAXTOK = 256
load = lambda p: [json.loads(l) for l in p.open(encoding="utf-8")]
train, dev = load(train_p), load(dev_p)

# ---- tokenizer (cased WordPiece)
tok = Tokenizer(models.WordPiece(unk_token="[UNK]"))
tok.normalizer = normalizers.NFC()
tok.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
tok.decoder = decoders.WordPiece()
tok.train_from_iterator((d["text"] for d in train), trainers.WordPieceTrainer(vocab_size=16000, min_frequency=2,
                        special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]))
CLS, SEP, PAD, UNK = (tok.token_to_id(t) for t in ("[CLS]", "[SEP]", "[PAD]", "[UNK]"))
tok.post_processor = processors.TemplateProcessing(single="[CLS] $A [SEP]", special_tokens=[("[CLS]", CLS), ("[SEP]", SEP)])
tok.save(str(out / "tokenizer.json"))

def word_ids(w):
    ids = tok.encode(w, add_special_tokens=False).ids
    return ids or [UNK]

def examples(doc, jitter=False):
    text, spans = doc["text"], [s for s in doc.get("spans", []) if s[2] == "PERSON"]
    words = [(m.start(), m.end(), m.group()) for m in WORD.finditer(text)]
    lab = []
    for s, e, _ in words:
        l = 0
        for a, b, _t in spans:
            if s < b and e > a:  # overlaps a name
                l = 1 if s <= a else 2
                break
        lab.append(l)
    seqs, i = [], (random.randrange(0, 40) if jitter and len(words) > 80 else 0)
    if i: i = min(i, len(words) - 1)
    while i < len(words):
        ids, labs, j = [CLS], [-100], i
        while j < len(words):
            wi = word_ids(words[j][2])
            if len(ids) + len(wi) >= MAXTOK - 1: break
            labs += [lab[j]] + [-100] * (len(wi) - 1); ids += wi; j += 1
        if j == i: j += 1; continue
        ids.append(SEP); labs.append(-100)
        seqs.append((ids, labs)); i = j
    return seqs

def batches(seqs, bs, shuffle):
    order = list(range(len(seqs)))
    if shuffle: random.shuffle(order)
    for k in range(0, len(order), bs):
        chunk = [seqs[o] for o in order[k:k + bs]]
        n = max(len(c[0]) for c in chunk)
        ids = torch.full((len(chunk), n), PAD); labs = torch.full((len(chunk), n), -100); mask = torch.zeros((len(chunk), n), dtype=torch.long)
        for r, (a, b) in enumerate(chunk):
            ids[r, :len(a)] = torch.tensor(a); labs[r, :len(b)] = torch.tensor(b); mask[r, :len(a)] = 1
        yield ids, mask, labs

cfg = BertConfig(vocab_size=tok.get_vocab_size(), hidden_size=128, num_hidden_layers=2, num_attention_heads=2, intermediate_size=512,
                 max_position_embeddings=MAXTOK, num_labels=3, id2label=dict(enumerate(LABELS)), label2id={l: i for i, l in enumerate(LABELS)},
                 hidden_dropout_prob=0.1, attention_probs_dropout_prob=0.1)
model = BertForTokenClassification(cfg)
print("params", sum(p.numel() for p in model.parameters()))
dev_seqs = [s for d in dev for s in examples(d)]
EPOCHS, BS = 5, 32
steps = EPOCHS * math.ceil(sum(len(examples(d)) for d in train[:300]) / 300 * len(train) / BS)
opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.01)
sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-3, total_steps=steps + 50, pct_start=0.1)

def evaluate():
    model.eval(); tp = fp = fn = 0
    with torch.no_grad():
        for ids, mask, labs in batches(dev_seqs, 64, False):
            pred = model(input_ids=ids, attention_mask=mask).logits.argmax(-1)
            m = labs != -100
            p, g = (pred[m] > 0), (labs[m] > 0)
            tp += int((p & g).sum()); fp += int((p & ~g).sum()); fn += int((~p & g).sum())
    model.train(); pr, rc = tp / max(1, tp + fp), tp / max(1, tp + fn)
    return pr, rc, 2 * pr * rc / max(1e-9, pr + rc)

t0, step = time.time(), 0
for ep in range(EPOCHS):
    seqs = [s for d in train for s in examples(d, jitter=True)]
    for ids, mask, labs in batches(seqs, BS, True):
        loss = model(input_ids=ids, attention_mask=mask, labels=labs).loss
        loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); opt.zero_grad()
        if step < steps + 49: sched.step()
        step += 1
    pr, rc, f1 = evaluate()
    print(f"epoch {ep + 1}: steps {step} loss {loss.item():.4f} dev word-level P {pr:.4f} R {rc:.4f} F1 {f1:.4f} ({time.time() - t0:.0f}s)", flush=True)

model.eval()
model.save_pretrained(out / "pytorch")
cfgd = json.loads(cfg.to_json_string()); cfgd["architectures"] = ["BertForTokenClassification"]; cfgd["model_type"] = "bert"
cfgd["katip"] = {"word_regex": r"[\p{L}\p{N}][\p{L}\p{N}'’.-]*", "max_tokens": MAXTOK, "labels": "word-level BIO on first sub-token"}
(out / "config.json").write_text(json.dumps(cfgd, indent=1))
(out / "tokenizer_config.json").write_text(json.dumps({"tokenizer_class": "BertTokenizer", "do_lower_case": False, "model_max_length": MAXTOK,
    "cls_token": "[CLS]", "sep_token": "[SEP]", "unk_token": "[UNK]", "pad_token": "[PAD]", "mask_token": "[MASK]"}, indent=1))

class Wrap(torch.nn.Module):
    def __init__(s, m): super().__init__(); s.m = m
    def forward(s, input_ids, attention_mask, token_type_ids): return s.m(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids).logits
x = torch.tensor([[CLS, 10, 11, SEP]]); m1 = torch.ones_like(x); tt = torch.zeros_like(x)
torch.onnx.export(Wrap(model), (x, m1, tt), str(out / "onnx/model.onnx"), input_names=["input_ids", "attention_mask", "token_type_ids"],
                  output_names=["logits"], dynamic_axes={k: {0: "batch", 1: "seq"} for k in ("input_ids", "attention_mask", "token_type_ids", "logits")},
                  opset_version=17, dynamo=False)
from onnxruntime.quantization import QuantType, quantize_dynamic
quantize_dynamic(str(out / "onnx/model.onnx"), str(out / "onnx/model_quantized.onnx"), weight_type=QuantType.QInt8)
print("exported", {p.name: p.stat().st_size for p in (out / "onnx").iterdir()})
