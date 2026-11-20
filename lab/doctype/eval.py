"""Score the document-type classifier, with 95% bootstrap intervals, against a keyword baseline.

    python lab/doctype/eval.py                                   # shipped pack, all sets
    python lab/doctype/eval.py --models lab/doctype/runs/family_split --sets test_family test_family_clean

Test sets (none of them shares a template or a sentence with templates_tr.py):
  test_family        synthetic, family 2 only: a writing style held out from training (augmented: OCR, ASCII…)
  test_family_clean  the same family without augmentation
  samples            docs/samples/*.txt: 80 synthetic docs from Katip's earlier, separate generator (16 types)
  forms              KVKK-Bench forms-id (legal-study branch): 306 petitions/forms, 34 bodies, separate generator.
                     The file carries a "do not train on this" canary; we only score on it.
  legalner_karar     real Yargıtay decision text (TurkishLegalNER, Apache-2.0): 8 consecutive sentences per
                     chunk, so mostly mid-document pages with no header. Real text, one class (karar).
  wiki_diger         real Turkish Wikipedia sentences (Turkish Wiki NER, CC BY-SA 4.0), 10 per chunk. Non-legal
                     text: the right answer is "diger" (other), or a low-confidence abstain.
External files are downloaded once into lab/doctype/data/external/ (git-ignored).
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "connector"))
from katip_kalkan import doctype as D  # noqa: E402

DATA, EXT = HERE / "data", HERE / "data" / "external"
SAMPLES_MAP = {"aydinlatma": "aydinlatma_metni", "bilirkisi": "bilirkisi_raporu", "dilekce": "dilekce", "epikriz": "saglik_raporu",
               "eposta": "yazisma", "fatura": "fatura", "icra": "icra_takip_talebi", "ihtarname": "ihtarname",
               "is_sozlesmesi": "is_sozlesmesi", "karar": "karar", "kira_sozlesmesi": "kira_sozlesmesi", "mektup": "yazisma",
               "mesaj": "mesajlasma", "tutanak": "tutanak", "vekaletname": "vekaletname", "zabit": "durusma_zapti"}
# forms-id body -> our type. Every petition to a court, enforcement office, bar or authority is "dilekce";
# the specific kinds we model separately keep their own label.
FORMS_MAP = {"cevap": "cevap_dilekcesi", "istinaf": "kanun_yolu", "suc-duyurusu": "suc_duyurusu",
             "icra-takip": "icra_takip_talebi", "vekaletname": "vekaletname", "ihtarname": "ihtarname",
             "kvkk-basvuru": "kvkk_basvuru"}
URLS = {
    "forms": "https://raw.githubusercontent.com/fikrifirat/katip/legal-study/lab/legal/bench/forms/forms-id.jsonl",
    "legalner": "https://raw.githubusercontent.com/koc-lab/turkishlegalner/main/data/train_and_test/test.words.txt",
    "wiki": "https://raw.githubusercontent.com/turkish-nlp-suite/Turkish-Wiki-NER-Dataset/main/Turkish-Wiki-NER-Dataset/test.conll",
}


def _get(key: str) -> Path:
    EXT.mkdir(parents=True, exist_ok=True)
    p = EXT / URLS[key].rsplit("/", 1)[1]
    if not p.exists():
        urllib.request.urlretrieve(URLS[key], p)
    return p


def _detok(words: list[str]) -> str:
    out = ""
    for w in words:
        out += ("" if not out or w in set(".,;:!?)]}%'’\"") else " ") + w
    return out


def load_set(name: str) -> list[dict]:
    if name.startswith("test_family") or (DATA / f"{name}.jsonl.gz").exists():
        with gzip.open(DATA / f"{name}.jsonl.gz", "rt", encoding="utf-8") as fh:
            return [json.loads(l) for l in fh]
    if name == "samples":
        rows = []
        for p in sorted((ROOT / "docs/samples").glob("*.txt")):
            kind = re.sub(r"_\d+$", "", p.stem)
            rows.append({"text": p.read_text(encoding="utf-8"), "label": SAMPLES_MAP[kind], "group": kind})
        return rows
    if name == "forms":
        rows = []
        for l in _get("forms").read_text(encoding="utf-8").splitlines():
            x = json.loads(l)
            if "template" not in x:
                continue
            body = x["template"].split("/")[0]
            rows.append({"text": x["text"], "label": FORMS_MAP.get(body, "dilekce"), "group": body})
        return rows
    if name == "legalner_karar":
        sents = [l.strip() for l in _get("legalner").read_text(encoding="utf-8").splitlines() if l.strip()]
        return [{"text": "\n".join(_detok(s.split()) for s in sents[i:i + 8]), "label": "karar", "group": "yargitay"}
                for i in range(0, len(sents) - 7, 8)]
    if name == "wiki_diger":
        sents, cur = [], []
        for line in _get("wiki").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                if cur:
                    sents.append(_detok(cur)); cur = []
                continue
            cur.append(line.split("\t")[0])
        r = random.Random(0)
        r.shuffle(sents)
        return [{"text": " ".join(sents[i:i + 10]), "label": "diger", "group": "wiki"} for i in range(0, min(len(sents), 3000), 10)]
    raise SystemExit(f"unknown set {name}")


# ------------------------------------------------------------------ keyword baseline (what a regex on the title gets)
KEYWORDS = [  # checked in order on the first 400 normalised characters
    ("odeme emri", "odeme_emri"), ("takip talebi", "icra_takip_talebi"), ("takip talepnamesi", "icra_takip_talebi"),
    ("ihtarname", "ihtarname"), ("ihtar", "ihtarname"), ("vekaletname", "vekaletname"), ("bilirkisi", "bilirkisi_raporu"),
    ("durusma tutanagi", "durusma_zapti"), ("durusma zapti", "durusma_zapti"), ("celse", "durusma_zapti"),
    ("tutanak", "tutanak"), ("teblig mazbatasi", "tebligat"), ("tebligat", "tebligat"), ("davetiye", "tebligat"),
    ("kira", "kira_sozlesmesi"), ("is sozlesmesi", "is_sozlesmesi"), ("hizmet akdi", "is_sozlesmesi"),
    ("sozlesme", "sozlesme"), ("yonetim kurulu", "sirket_karari"), ("genel kurul", "sirket_karari"),
    ("fatura", "fatura"), ("makbuz", "fatura"), ("aydinlatma", "aydinlatma_metni"), ("kisisel verilerin", "aydinlatma_metni"),
    ("basvuru formu", "kvkk_basvuru"), ("epikriz", "saglik_raporu"), ("rapor", "saglik_raporu"),
    ("cevap", "cevap_dilekcesi"), ("istinaf", "kanun_yolu"), ("temyiz", "kanun_yolu"), ("savciligi", "suc_duyurusu"),
    ("yargitay", "karar"), ("karar", "karar"), ("mahkemesi", "dilekce"), ("kimden:", "yazisma"), ("konu:", "yazisma"),
]


def keyword_baseline(text: str) -> str:
    t = D.normalise(text)[:400]
    for k, lab in KEYWORDS:
        if k in t:
            return lab
    return "diger"


# ------------------------------------------------------------------ metrics
def metrics(gold: list[str], pred: list[str]) -> dict:
    n = len(gold)
    acc = sum(g == p for g, p in zip(gold, pred)) / n
    labs = sorted(set(gold))
    f1s = []
    for l in labs:
        tp = sum(g == l and p == l for g, p in zip(gold, pred))
        fp = sum(g != l and p == l for g, p in zip(gold, pred))
        fn = sum(g == l and p != l for g, p in zip(gold, pred))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return {"n": n, "acc": acc, "macro_f1": sum(f1s) / len(f1s)}


def bootstrap(gold, pred, B=1000, seed=0):
    r = random.Random(seed); n = len(gold); accs, f1s = [], []
    for _ in range(B):
        ix = [r.randrange(n) for _ in range(n)]
        m = metrics([gold[i] for i in ix], [pred[i] for i in ix])
        accs.append(m["acc"]); f1s.append(m["macro_f1"])
    accs.sort(); f1s.sort()
    q = lambda v: (round(v[int(.025 * B)] * 100, 1), round(v[int(.975 * B)] * 100, 1))
    return {"acc_ci": q(accs), "macro_f1_ci": q(f1s)}


def evaluate(rows, model_root=None):
    p = D.Pack("tr", model_root=model_root)
    D._packs["tr"] = p
    gold, pred, raw, conf, base = [], [], [], [], []
    t0 = time.perf_counter()
    for r in rows:
        res = D.classify(r["text"], "tr")
        gold.append(r["label"]); pred.append(res["type"]); raw.append(res.get("guess") or res["type"]); conf.append(res["confidence"])
    ms = (time.perf_counter() - t0) * 1000 / len(rows)
    base = [keyword_baseline(r["text"]) for r in rows]
    out = {**metrics(gold, pred), **bootstrap(gold, pred), "abstain_rate": sum(x == "diger" and g != "diger" for x, g in zip(pred, gold)) / len(rows),
           "acc_no_abstain": metrics(gold, raw)["acc"],
           "coverage": sum(x != "diger" or g == "diger" for x, g in zip(pred, gold)) / len(rows),
           "acc_when_answered": (lambda kept: sum(gold[i] == pred[i] for i in kept) / max(1, len(kept)))(
               [i for i, x in enumerate(pred) if x != "diger"]), "keyword_baseline": metrics(gold, base), "ms_per_doc": round(ms, 1)}
    errs = Counter((g, x) for g, x in zip(gold, pred) if g != x)
    out["top_confusions"] = [f"{g} -> {x}: {c}" for (g, x), c in errs.most_common(8)]
    if rows and "group" in rows[0]:
        by = defaultdict(lambda: [0, 0])
        for r, x in zip(rows, pred):
            by[r["group"]][0] += r["label"] == x; by[r["group"]][1] += 1
        out["by_group"] = {k: f"{a}/{b}" for k, (a, b) in sorted(by.items())}
    per = defaultdict(lambda: [0, 0])
    for g, x in zip(gold, pred):
        per[g][0] += g == x; per[g][1] += 1
    out["per_type"] = {k: f"{a}/{b}" for k, (a, b) in sorted(per.items())}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=None, help="folder with tr.model.json (default: the shipped pack)")
    ap.add_argument("--sets", nargs="+", default=["samples", "forms", "legalner_karar", "wiki_diger"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = {}
    for s in a.sets:
        rows = load_set(s)
        res[s] = evaluate(rows, Path(a.models) if a.models else None)
        m = res[s]
        print(f"{s:18s} n={m['n']:5d} acc {m['acc']*100:5.1f} {m['acc_ci']}  macroF1 {m['macro_f1']*100:5.1f} {m['macro_f1_ci']}  "
              f"argmax {m['acc_no_abstain']*100:5.1f}  keywords {m['keyword_baseline']['acc']*100:5.1f}  abstain {m['abstain_rate']*100:4.1f}%  "
              f"precision-when-typed {m['acc_when_answered']*100:5.1f}  {m['ms_per_doc']} ms/doc")
        for c in m["top_confusions"][:5]:
            print("     ", c)
    if a.out:
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
