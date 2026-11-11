---
language: tr
license: cc-by-nc-4.0
library_name: transformers.js
pipeline_tag: token-classification
tags:
- ner
- pii
- kvkk
- turkish
- legal
- onnx
- privacy
- redaction
---

# katip-tr-name-tagger-tiny

A 2.5M-parameter Turkish person-name tagger that runs in the browser (2.6 MB int8 ONNX) and is
built to sit **next to rule-based PII detection**, not to replace it. It is the on-device model
behind [Katip Yerel](https://huggingface.co/spaces/fikrifirat/katip-yerel), a KVKK redaction tool
where the document never leaves the user's computer.

## What it improves

Measured on Katip's synthetic Turkish legal documents, PERSON values only. "Rules" is
Katip's rule engine (gazetteers, cue words, casing, Turkish suffix handling); "rules + tagger"
combines the two with the policy below.

| Set | Docs | Names | Rules | Rules + tagger | False names added |
| --- | --- | --- | --- | --- | --- |
| Blind (new names, 4 unseen document styles) | 80 | 365 | 98.4% | **99.7%** | 0 |
| Held-out dev | 60 | 275 | 95.3% | **97.5%** | 0 |
| Tuning set | 40 | 165 | 96.4% | 96.4% | 0 |
| Negatives (name-free legal prose) | 3 | 0 | 2 false names | 2 false names | 0 |

int8 and fp32 give identical results. Most of the gain is completing partially caught names
(for example the rules mask *Menişan* but leave the surname *Çakmakçı*).

**Honest caveats.** All data is synthetic. The blind set's names were excluded from training, but
12 of its 16 document styles share templates with the training data. The combination policy
(edge trimming + two-token rule) was chosen after looking at the blind set's false positives once,
so the blind set is no longer fully blind for that policy. Real documents will score lower.

## How it is meant to be used

Labels (`O`, `B-PER`, `I-PER`) are trained **per word on the word's first sub-token**, where words
are split with the regex in `config.json` → `katip.word_regex`
(`[\p{L}\p{N}][\p{L}\p{N}'’.-]*`). Feed words in order inside `[CLS] … [SEP]` windows of at most
256 tokens and read the logits at each word's first sub-token. The stock HF token-classification
pipeline splits differently and gives noisy output.

Combination policy used in the numbers above (see `local_detect.py` in the Space):

1. keep model spans with mean probability ≥ 0.5;
2. trim ordinary Turkish words off both edges (frequency-list lexicon with suffix handling);
3. if the span overlaps a rule PERSON span, widen that span to the union;
4. otherwise add it only if it has two or more capitalised tokens.

JavaScript (transformers.js 4), word-level: see `ner.js` in the Space.

```python
from transformers import AutoTokenizer, AutoModelForTokenClassification
tok = AutoTokenizer.from_pretrained("fikrifirat/katip-tr-name-tagger-tiny")
model = AutoModelForTokenClassification.from_pretrained("fikrifirat/katip-tr-name-tagger-tiny")
```

## Model

BERT, trained from scratch: 2 layers, hidden size 128, 2 heads, 512 FFN, 256 positions,
cased WordPiece vocabulary of 16,000 trained on the same corpus. 5 epochs, AdamW, one-cycle LR
1e-3, batch 32, about 6 minutes on 4 CPU cores. Dev word-level F1 0.95 on a harder augmented split.

## Training data

8,000 synthetic documents from Katip's 12 legal templates (petitions, judgments, leases,
employment contracts, invoices, privacy notices, powers of attorney, notices, e-mails,
minutes, chats, expert reports). Names drawn from Faker `tr_TR`, Katip's gazetteers and surnames
composed from Turkish morphemes, minus every name used by the blind set. 70% of documents get
distractor lines: ordinary words in Title Case, ALL CAPS headings and sentence starts, drawn from
the general OpenSubtitles frequency list (not from any evaluation set). Scripts: `ml/` in the
[source repository](https://github.com/fikrifirat/katip).

## Limits

- Person names only. Everything with a checksum or fixed shape (T.C. kimlik, VKN, IBAN, card,
  phone, plate, e-mail) is left to the rules.
- Synthetic legal Turkish only. Not tested on real case files, OCR noise beyond Katip's scans,
  or non-legal text.
- Not a privacy guarantee: always review redacted output before sending it.

## Licence

CC BY-NC 4.0: free for research, evaluation and other non-commercial use. For commercial or
production use (inside a product, a firm's own workflow or a hosted service), contact
fikrifirat@gmail.com or open an issue at https://github.com/fikrifirat/katip.
