"""Score systems on Turkish PII test sets built by other teams (KVKK-Bench external track).

  python lab/legal/external/ext_bench.py run base mini nano rules newmind-kvkk-v2
  python lab/legal/external/ext_bench.py score            # -> external/results.json + RESULTS.md

Sets (test splits only, pinned to a Hub commit; nothing is redistributed, the script downloads them):
  nm6k      newmindai/nm-kvkk-pii-6K            Apache-2.0  602 synthetic docs (NewMind's own set: kvkk-v2 trained on its train split)
  werea     Werea-co/Werea-KVKK-Bench           Apache-2.0  240 synthetic test rows (girenit/girenit-KVKK-Bench is byte-identical)
  cagri     cagrigungor/turkish-pii-masking-benchmark  CC0  "tam" (mask everything, 350) + "negatif" (no PII, 200)
  piimask   promptrails/piimask-eval-tr-en      CC BY 4.0   400 docs: tr 180, tr-en 80, en 140 (en reported, not ranked)

Each set's labels are mapped to KVKK-Bench types in MAP below. A label mapped to None is outside the shared core:
it is left out of typed recall/precision (a prediction lying mostly inside such a value is neither right nor wrong),
but it still counts in "leak, all labels", the share of every labelled character the system leaves readable.
Matching is the KVKK-Bench rule (bench_score.matches / true_span).
"""
from __future__ import annotations

import csv, json, re, sys, time
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent)]
import bench_score as BS  # noqa: E402

PRED = HERE / "preds"
SETS = {   # key: (repo, revision, licence)
    "nm6k": ("newmindai/nm-kvkk-pii-6K", "0dfe459c402630ff137edeed75942d11bc9b3c21", "Apache-2.0"),
    "werea": ("Werea-co/Werea-KVKK-Bench", "e523d0e2865dd974b152590702b325518669eead", "Apache-2.0"),
    "cagri": ("cagrigungor/turkish-pii-masking-benchmark", "b2e6e68b260873cda53e90e623c1fa35d74fc7eb", "CC0-1.0"),
    "piimask": ("promptrails/piimask-eval-tr-en", "1a8426e6f34af0c44336ea1329798a219b83417e", "CC-BY-4.0"),
}

PERSONAL_NAMES = ["full_name", "first_name", "last_name", "middle_name", "maiden_name", "mothers_maiden_name"]
MAP = {
    "nm6k": {**{k: "PERSON" for k in PERSONAL_NAMES}, "national_id_number": "TCKN", "foreigner_id_number": "YKN",
             "passport_number": "PASSPORT", "phone_number": "PHONE", "fax_number": "PHONE", "email_address": "EMAIL",
             "kep_address": "EMAIL", "iban": "IBAN", "card_number": "CREDIT_CARD", "full_address": "ADDRESS",
             "street_line": "ADDRESS", "date_of_birth": "BIRTH_DATE", "license_plate": "PLATE", "ip_address": "IP_ADDRESS",
             "tax_id_number": "VKN", "medical_condition": "HEALTH", "medication": "HEALTH", "medical_procedure": "HEALTH",
             "disability_status": "HEALTH", "blood_type": "HEALTH", "political_opinion": "POLITICAL",
             "biometric_data_reference": "BIOMETRIC_GENETIC", "attire_info": "DRESS"},
    "werea": {"PERSON": "PERSON", "EMAIL": "EMAIL", "PHONE_TR": "PHONE", "ADDRESS": "ADDRESS", "HEALTH_DATA": "HEALTH",
              "TCKN": "TCKN", "PASSPORT_TR": "PASSPORT", "IBAN_TR": "IBAN", "CREDIT_CARD": "CREDIT_CARD", "IPV4": "IP_ADDRESS",
              "VEHICLE_PLATE_TR": "PLATE", "DATE_OF_BIRTH": "BIRTH_DATE", "BIOMETRIC_DATA": "BIOMETRIC_GENETIC",
              "GENETIC_DATA": "BIOMETRIC_GENETIC", "CRIMINAL_CONVICTION_SECURITY": "CRIMINAL_RECORD",
              "POLITICAL_OPINION": "POLITICAL", "RELIGION": "RELIGION", "UNION_MEMBERSHIP": "UNION", "SEXUAL_LIFE": "SEXUAL_LIFE"},
    "cagri": {"AD": "PERSON", "ANNE_ADI": "PERSON", "BABA_ADI": "PERSON", "ANNE_KIZLIK": "PERSON", "TCKN": "TCKN",
              "KART": "CREDIT_CARD", "EMAIL": "EMAIL", "PASAPORT_NO": "PASSPORT", "TEL": "PHONE", "DOGUM_TARIHI": "BIRTH_DATE",
              "IP_ADRES": "IP_ADDRESS", "IBAN": "IBAN", "ADRES": "ADDRESS", "PLAKA": "PLATE", "VERGI_NO": "VKN",
              "SAGLIK": "HEALTH", "KAN_GRUBU": "HEALTH", "ENGEL_DURUMU": "HEALTH", "CEZA_KAYDI": "CRIMINAL_RECORD",
              "BIYOMETRIK": "BIOMETRIC_GENETIC", "ETNIK_KOKEN": "ETHNICITY", "DIN": "RELIGION", "SENDIKA": "UNION"},
    "piimask": {"AD_SOYAD": "PERSON", "PERSON_NAME": "PERSON", "TELEFON": "PHONE", "PHONE": "PHONE", "EMAIL": "EMAIL",
                "E_POSTA": "EMAIL", "IBAN": "IBAN", "TC_KIMLIK_NO": "TCKN", "SSN": "TCKN", "ADRES": "ADDRESS", "ADDRESS": "ADDRESS",
                "DAIRE_NO": "ADDRESS", "DATE_OF_BIRTH": "BIRTH_DATE", "DOGUM_TARIHI": "BIRTH_DATE", "CREDIT_CARD_NO": "CREDIT_CARD",
                "PASAPORT_NO": "PASSPORT", "PLAKA": "PLATE", "VERGI_NO": "VKN"},
}
# predicted types accepted for a gold type (identity numbers are often mutually confusable by format)
ID = {"TCKN", "YKN", "FOREIGN_ID", "VKN"}
ACCEPT = {t: {t} for t in BS.TYPES} | {"TCKN": ID, "YKN": ID, "VKN": ID, "PASSPORT": {"PASSPORT", "FOREIGN_ID"}}


def _get(repo, rev, path):
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo, path, repo_type="dataset", revision=rev)

def _cagri_spans(inp, out):
    """Gold spans from (input, expected_output): each [TAG] in the output stands for one span of the input."""
    parts = re.split(r"\[([A-Z_]+)\]", out)
    lits, tags = parts[0::2], parts[1::2]
    rx = "".join(re.escape(l) + ("(.+?)" if i < len(tags) else "") for i, l in enumerate(lits))
    m = re.fullmatch(rx, inp, re.S)
    if not m: return None
    return [[m.start(i + 1), m.end(i + 1), t] for i, t in enumerate(tags)]

def load(key):
    repo, rev, _ = SETS[key]
    docs = []
    if key == "nm6k":
        for l in open(_get(repo, rev, "spans/test.jsonl"), encoding="utf-8"):
            r = json.loads(l)
            docs.append({"id": r["id"], "track": "nm6k-hard" if r["meta"]["hard"] else "nm6k-easy", "text": r["text"],
                         "spans": [[e["start"], e["end"], e["label"]] for e in r["entities"]]})
    elif key == "werea":
        for l in open(_get(repo, rev, "pii_synthetic.jsonl"), encoding="utf-8"):
            r = json.loads(l)
            if r["split"] == "test":
                docs.append({"id": r["id"], "track": "werea", "text": r["text"], "spans": [[e["start"], e["end"], e["label"]] for e in r["entities"]]})
    elif key == "cagri":
        bad = 0
        for r in csv.DictReader(open(_get(repo, rev, "benchmark_1000.csv"), encoding="utf-8-sig")):
            if r["kategori"] not in ("tam", "negatif"): continue      # whitelist/blacklist/out-of-scope rows test instruction-following
            sp = _cagri_spans(r["input"], r["expected_output"])
            if sp is None: bad += 1; continue
            docs.append({"id": f"cagri-{r['id']}", "track": f"cagri-{r['kategori']}", "text": r["input"], "spans": sp, "slices": r["ozellikler"]})
        if bad: print(f"cagri: {bad} rows whose output could not be aligned to the input were left out", file=sys.stderr)
    elif key == "piimask":
        for l in open(_get(repo, rev, "pii_eval_400.jsonl"), encoding="utf-8"):
            r = json.loads(l)
            docs.append({"id": f"piimask-{r['id']}", "track": f"piimask-{r['lang']}", "text": r["text"], "difficulty": r["difficulty"],
                         "spans": [[e["start"], e["end"], e["label"]] for e in r["entities"]]})
    return docs

# ------------------------------------------------------------------------------------------------ systems
def systems():
    import bench_run as BR
    from huggingface_hub import snapshot_download
    pat = ["config.json", "tokenizer*", "vocab.txt", "onnx/model_quantized.onnx", "katip_trust.json"]
    snap = lambda r: snapshot_download(r, allow_patterns=pat)
    return {
        "base": ("Katip Mask Base (f1k/katip-mask-base)", lambda: BR._katip(snap("f1k/katip-mask-base"), 0.5)),
        "mini": ("Katip Mask Mini (f1k/katip-mask-mini)", lambda: BR._katip(snap("f1k/katip-mask-mini"), BR._trust_file(snap("f1k/katip-mask-mini")))),
        "nano": ("Katip Mask Nano v1.1 (f1k/katip-mask-nano)", lambda: BR._katip(snap("f1k/katip-mask-nano"), 0.5)),
        "rules": ("Katip rules only", BR.SYSTEMS["rules"][1]),
        "newmind-kvkk-v2": ("newmindai/gliner2.5-kvkk-tr-v2 (stack21 labels, their extract_kvkk.py settings)", lambda: BR._baseline("newmind-kvkk-v2")),
        "presidio": ("Presidio + spaCy xx (vanilla)", lambda: BR._baseline("presidio")),
        **EXTRA,
    }

# ---- candidate models for the board (18 Nov 2026). Label maps written from each model's config / card; labels left
# out keep their own name: masked text, never a typed hit.
_WEREA = {"PERSON": "PERSON", "TCKN": "TCKN", "PHONE_TR": "PHONE", "EMAIL": "EMAIL", "ADDRESS": "ADDRESS", "HEALTH_DATA": "HEALTH",
          "PASSPORT_TR": "PASSPORT", "IBAN_TR": "IBAN", "CREDIT_CARD": "CREDIT_CARD", "IPV4": "IP_ADDRESS", "VEHICLE_PLATE_TR": "PLATE",
          "DATE_OF_BIRTH": "BIRTH_DATE", "BIOMETRIC_DATA": "BIOMETRIC_GENETIC", "GENETIC_DATA": "BIOMETRIC_GENETIC",
          "CRIMINAL_CONVICTION_SECURITY": "CRIMINAL_RECORD", "POLITICAL_OPINION": "POLITICAL", "RELIGION": "RELIGION",
          "UNION_MEMBERSHIP": "UNION", "SEXUAL_LIFE": "SEXUAL_LIFE"}
_HORIZON = {"PERSON": "PERSON", "NATIONAL_ID": "TCKN", "TAX_ID": "VKN", "PASSPORT": "PASSPORT", "PHONE": "PHONE", "EMAIL": "EMAIL",
            "CREDIT_CARD": "CREDIT_CARD", "DATE_OF_BIRTH": "BIRTH_DATE", "IP_ADDRESS": "IP_ADDRESS", "STREET_ADDRESS": "ADDRESS",
            "VEHICLE_ID": "PLATE", "BANK_ACCOUNT": "IBAN"}
_HUSH = {"person": "PERSON", "full address": "ADDRESS", "organization": "ORG", "date of birth": "BIRTH_DATE", "medical condition": "HEALTH",
         "religious belief": "RELIGION", "ethnic origin": "ETHNICITY", "political opinion": "POLITICAL", "sexual orientation": "SEXUAL_LIFE",
         "criminal record": "CRIMINAL_RECORD", "biometric data": "BIOMETRIC_GENETIC", "trade union membership": "UNION"}
_GUARD = {"AD": "PERSON", "ANNE_ADI": "PERSON", "BABA_ADI": "PERSON", "ANNE_KIZLIK": "PERSON", "TCKN": "TCKN", "KART": "CREDIT_CARD",
          "EMAIL": "EMAIL", "PASAPORT_NO": "PASSPORT", "TEL": "PHONE", "DOGUM_TARIHI": "BIRTH_DATE", "IP_ADRES": "IP_ADDRESS", "IBAN": "IBAN",
          "ADRES": "ADDRESS", "PLAKA": "PLATE", "VERGI_NO": "VKN", "SAGLIK": "HEALTH", "KAN_GRUBU": "HEALTH", "ENGEL_DURUMU": "HEALTH",
          "CEZA_KAYDI": "CRIMINAL_RECORD", "BIYOMETRIK": "BIOMETRIC_GENETIC", "ETNIK_KOKEN": "ETHNICITY", "DIN": "RELIGION", "SENDIKA": "UNION"}

def _chunks(text, max_words):
    """(offset, piece) pieces of at most ~max_words words, cut at line ends or sentence ends."""
    out, start, words = [], 0, 0
    for m in re.finditer(r"[^\n.!?]*(?:[.!?]+(?=\s)|\n|$)", text):
        if not m.group(): continue
        n = len(m.group().split())
        if words and words + n > max_words:
            out.append((start, text[start:m.start()])); start, words = m.start(), 0
        words += n
    if start < len(text): out.append((start, text[start:]))
    return out

def _hushmark():
    from gliner import GLiNER
    m = GLiNER.from_pretrained("lokomotifai/hushmark-tr-289m"); m.eval()
    def det(text):
        out = []
        for off, piece in _chunks(text, 200):            # card: inputs up to 384 tokens, longer inputs chunked by the caller
            for e in m.predict_entities(piece, list(_HUSH), threshold=0.5):
                out.append((off + e["start"], off + e["end"], _HUSH[e["label"]]))
        return out
    n = sum(p.numel() for p in m.parameters())
    return det, {"params": int(n), "size_mb": round(n * 4 / 1e6, 1), "runs_locally": True, "runs_in_browser": False,
                 "size_note": "model only: Hushmark's ID validators are not part of the release"}

def align_masked(inp, out):
    """Character spans of `inp` that a masking model replaced with [TAG] in `out`. Returns (spans, how):
    'exact' template match; 'loose' the same with case, spacing and edge punctuation relaxed; 'diff' a word-level
    diff, when the model also rewrote other text."""
    sp = _cagri_spans(inp, out)
    if sp is not None: return sp, "exact"
    parts = re.split(r"\[([A-Z_]+)\]", out.strip())
    lits, tags = parts[0::2], parts[1::2]
    lit = lambda l: r"\s*".join(re.escape(w) for w in l.split()) if l.strip() else ""
    rx = "".join(lit(l) + (r"\s*(.+?)\s*" if i < len(tags) else "") for i, l in enumerate(lits))
    m = re.fullmatch(r"\W*" + rx + r"\W*", inp.strip(), re.S | re.I) if tags else None
    if m:
        off = inp.index(inp.strip()[:1]) if inp.strip() else 0
        return [[off + m.start(i + 1), off + m.end(i + 1), t] for i, t in enumerate(tags)], "loose"
    import difflib
    wi = [(x.start(), x.end(), x.group()) for x in re.finditer(r"\S+", inp)]
    wo = re.findall(r"\[[A-Z_]+\]|[^\s\[]+|\[", out)
    key = lambda w: re.sub(r"\W", "", w).casefold()
    sm = difflib.SequenceMatcher(None, [key(w[2]) for w in wi], [key(w) if not re.fullmatch(r"\[[A-Z_]+\]", w) else w for w in wo], autojunk=False)
    res = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "replace" and i2 > i1:
            tg = [w[1:-1] for w in wo[j1:j2] if re.fullmatch(r"\[[A-Z_]+\]", w)]
            if tg: res.append([wi[i1][0], wi[i2 - 1][1], tg[0]])
    return res, "diff"

def _guard(repo):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(2)
    tok = AutoTokenizer.from_pretrained(repo); m = AutoModelForCausalLM.from_pretrained(repo, dtype=torch.float32).eval()
    eot = tok.convert_tokens_to_ids("<end_of_turn>")
    INSTR = "Metindeki tüm kişisel verileri uygun etiketlerle maskele."   # the card's full-masking instruction
    stats = {"pieces": 0, "exact": 0, "loose": 0, "diff": 0}
    def mask(piece):
        prompt = f"{tok.bos_token}<start_of_turn>user\n{INSTR}\n\nMetin: {piece}<end_of_turn>\n<start_of_turn>model\n"
        x = tok(prompt, return_tensors="pt", add_special_tokens=False)
        with torch.inference_mode():
            y = m.generate(**x, max_new_tokens=min(700, 2 * x["input_ids"].shape[1]), do_sample=False, eos_token_id=eot, pad_token_id=tok.eos_token_id)
        return tok.decode(y[0, x["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    def det(text):
        out = []
        for off, piece in _chunks(text, 120):            # trained with a 768-token context
            core = piece.strip()
            if not core: continue
            lead = piece.index(core)
            sp, how = align_masked(core, mask(core))
            stats["pieces"] += 1; stats[how] += 1
            out += [(off + lead + a, off + lead + b, _GUARD.get(t, t)) for a, b, t in sp]
        return out
    det.stats = stats
    n = sum(p.numel() for p in m.parameters())
    return det, {"params": int(n), "size_mb": round(n * 4 / 1e6, 1), "runs_locally": True, "runs_in_browser": False,
                 "size_note": "fp32 on CPU; text-to-text model, spans recovered by aligning its output to the input", "_stats": stats}

def _hf_tc(repo, labmap):
    def make():
        import baselines as BL
        det = BL._hf(repo, labmap)()
        return det, {"params": int(det.params), "size_mb": det.size_mb, "runs_locally": True, "runs_in_browser": False,
                     "size_note": "weights as loaded (fp32)", "unmapped_labels": det.unmapped}
    return make

EXTRA = {
    "horizon-pii-base": ("Horizon-Labs/pii-redactor-base (mmBERT)", _hf_tc("Horizon-Labs/pii-redactor-base", _HORIZON)),
    "werea-pii-150m": ("Werea-co/Werea-KVKK-PII-150M (ModernBERT-TR)", _hf_tc("Werea-co/Werea-KVKK-PII-150M", _WEREA)),
    "girenit-pii-150m": ("girenit/girenit-KVKK-PII-150M (ModernBERT-TR)", _hf_tc("girenit/girenit-KVKK-PII-150M", _WEREA)),
    "hushmark-tr-289m": ("lokomotifai/hushmark-tr-289m (GLiNER, model only)", _hushmark),
    "pii-guard-270m": ("cagrigungor/pii-guard-turkish-270m (Gemma 3 270M, text-to-text)", lambda: _guard("cagrigungor/pii-guard-turkish-270m")),
    "halilneed-pii": ("halilneed/turkish-pii-detection (Gemma 3 270M, text-to-text)", lambda: _guard("halilneed/turkish-pii-detection")),
}

def run(keys, sets):
    SYS = systems(); PRED.mkdir(exist_ok=True)
    data = {s: load(s) for s in sets}
    for k in keys:
        det, meta = SYS[k][1]()
        for s, docs in data.items():
            f = PRED / f"{k}__{s}.jsonl"
            part = PRED / f"{k}__{s}.partial.jsonl"     # resumable: one line per document as it is done
            done = {json.loads(l)["id"]: l for l in part.read_text().splitlines()} if part.exists() else {}
            t0 = time.time()
            with part.open("a", encoding="utf-8") as fo:
                for i, d in enumerate(docs):
                    if d["id"] in done: continue
                    fo.write(json.dumps({"id": d["id"], "spans": [list(x[:3]) for x in det(d["text"])]}, ensure_ascii=False) + "\n"); fo.flush()
                    if i % 50 == 0: print(f"  {k} {s} {i}/{len(docs)} {time.time() - t0:.0f}s", flush=True)
            secs = time.time() - t0 + (json.loads(part.read_text().splitlines()[0]).get("_secs", 0) if False else 0)
            rows = {json.loads(l)["id"]: l for l in part.read_text().splitlines()}
            f.write_text("".join(rows[d["id"]] + "\n" for d in docs)); part.unlink()
            (PRED / f"{k}__{s}.meta.json").write_text(json.dumps({**{a: (dict(b) if isinstance(b, dict) else b) for a, b in meta.items()}, "name": SYS[k][0], "secs": secs, "docs": len(docs)}, default=float))
            print(f"{k:16} {s:8} {len(docs)} docs  {secs:.0f}s", flush=True)

# ------------------------------------------------------------------------------------------------ scoring
def _doc_counts(d, ps, mp):
    """Per-document counts so a bootstrap can resample documents."""
    text = d["text"]
    core = [(s, e, mp[l]) for s, e, l in d["spans"] if mp.get(l)]
    allg = [(s, e) for s, e, _ in d["spans"]]
    out_scope = [(s, e) for s, e, l in d["spans"] if not mp.get(l)]
    c = defaultdict(float)
    masked = np.zeros(len(text), bool)
    for a, b, _ in ps: masked[max(0, a):min(len(text), b)] = True
    for s, e, t in core:
        c["g"] += 1; c[f"g:{t}"] += 1
        hit = any(pt in ACCEPT[t] and BS.matches(text[a:b], text[s:e]) for a, b, pt in ps)
        c["f"] += hit; c[f"f:{t}"] += hit
        c["fu"] += any(BS.matches(text[a:b], text[s:e]) for a, b, _ in ps)       # found under any type
        c["lc"] += e - s; c["lc_left"] += int((~masked[s:e]).sum())
    for s, e in allg:
        c["la"] += e - s; c["la_left"] += int((~masked[s:e]).sum())
    for a, b, pt in ps:
        c["pu"] += 1; c["pu_ok"] += BS.true_span(text, a, b, allg)               # any-type precision vs every label
        if pt not in BS.TYPES or pt not in set(mp.values()): continue   # a type this set never labels: neutral
        if out_scope and BS.true_span(text, a, b, out_scope) and not BS.true_span(text, a, b, [(s, e) for s, e, _ in core]):
            continue                                                             # mostly inside a value outside the core: neutral
        c["p"] += 1; c["p_ok"] += BS.true_span(text, a, b, [(s, e) for s, e, gt in core if pt in ACCEPT[gt]])
    c["words"] = len(text.split()); c["docs"] = 1; c["clean"] = float(bool(core) and all(not (~masked[s:e]).any() for s, e, _ in core))
    c["has_core"] = float(bool(core))
    return c

def _agg(cs):
    t = defaultdict(float)
    for c in cs:
        for k, v in c.items(): t[k] += v
    r = t["f"] / t["g"] if t["g"] else float("nan"); p = t["p_ok"] / t["p"] if t["p"] else 1.0
    return {"recall": r, "precision": p, "f2": BS.f2(p, r) if t["g"] else float("nan"),
            "recall_any_type": t["fu"] / t["g"] if t["g"] else float("nan"),
            "precision_any_label": t["pu_ok"] / t["pu"] if t["pu"] else 1.0,
            "leak_core": t["lc_left"] / t["lc"] if t["lc"] else float("nan"),
            "leak_all_labels": t["la_left"] / t["la"] if t["la"] else float("nan"),
            "false_masks_per_1k_words": 1000 * (t["pu"] - t["pu_ok"]) / max(1, t["words"]),
            "clean_doc_rate": t["clean"] / t["has_core"] if t["has_core"] else float("nan"),
            "gold_core": int(t["g"]), "gold_all": None, "docs": int(t["docs"]),
            "types": {k[2:]: {"gold": int(t[k]), "recall": t["f:" + k[2:]] / t[k]} for k in sorted(t) if k.startswith("g:")}}

def score(keys=None):
    res = {"sets": {k: {"repo": v[0], "revision": v[1], "licence": v[2]} for k, v in SETS.items()}, "map": MAP, "systems": {}}
    keys = keys or sorted({f.name.split("__")[0] for f in PRED.glob("*__*.jsonl")})
    per_doc = {}
    for k in keys:
        res["systems"][k] = {"tracks": {}}
        for s in SETS:
            f = PRED / f"{k}__{s}.jsonl"
            if not f.exists(): continue
            meta = json.loads((PRED / f"{k}__{s}.meta.json").read_text())
            res["systems"][k]["name"] = meta["name"]; res["systems"][k]["size_mb"] = meta.get("size_mb")
            docs = load(s); P = {json.loads(l)["id"]: json.loads(l)["spans"] for l in f.read_text().splitlines()}
            cs = [(d["track"], d["id"], _doc_counts(d, P.get(d["id"], []), MAP[s])) for d in docs]
            per_doc[(k, s)] = cs
            res["systems"][k]["tracks"][s] = {**_agg([c for _, _, c in cs]), "ms_per_doc": round(1000 * meta["secs"] / meta["docs"], 1)}
            for tr in sorted({t for t, _, _ in cs}):
                res["systems"][k]["tracks"][tr] = _agg([c for t, _, c in cs if t == tr])
    # paired bootstrap over documents: difference in F2 between every system and newmind-kvkk-v2, per set
    rng = np.random.default_rng(20261118)
    for s in SETS:
        if ("newmind-kvkk-v2", s) not in per_doc: continue
        sub = {"cagri": "cagri-tam", "piimask": "piimask-tr"}.get(s)   # compare on the Turkish 'mask all' rows only
        ref = [x for x in per_doc[("newmind-kvkk-v2", s)] if not sub or x[0] == sub]
        n = len(ref)
        idx = [rng.integers(0, n, n) for _ in range(2000)]
        for k in keys:
            if k == "newmind-kvkk-v2" or (k, s) not in per_doc: continue
            mine = [x for x in per_doc[(k, s)] if not sub or x[0] == sub]
            diffs = []
            for ix in idx:
                diffs.append(_agg([mine[i][2] for i in ix])["f2"] - _agg([ref[i][2] for i in ix])["f2"])
            lo, hi = np.percentile(diffs, [2.5, 97.5])
            res["systems"][k]["tracks"][sub or s]["f2_minus_newmind_ci95"] = [float(lo), float(hi)]
    (HERE / "results.json").write_text(json.dumps(res, indent=1, default=float, ensure_ascii=False))
    return res

if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "run":
        sets = [a[6:] for a in args if a.startswith("--set=")] or list(SETS)
        run([a for a in args if not a.startswith("--")], sets)
    elif cmd == "score":
        r = score(args or None)
        for k, v in r["systems"].items():
            print(k, {t: round(100 * x["f2"], 1) for t, x in v["tracks"].items()})


# ---- checksum analysis: synthetic sets often use numbers that fail the official check digits, which Katip's rules
# require (a TCKN/YKN that fails the algorithm cannot be a real one; a card number that fails Luhn cannot be a real card).
def _digits(s): return [int(c) for c in s if c.isdigit()]
def tckn_ok(s):
    d = _digits(s)
    return len(d) == 11 and d[0] != 0 and (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10 == d[9] and sum(d[:10]) % 10 == d[10]
def vkn_ok(s):
    d = _digits(s)
    if len(d) != 10: return False
    t = 0
    for i in range(9):
        x = (d[i] + 10 - (i + 1)) % 10
        y = (x * 2 ** (10 - (i + 1))) % 9 if x else 0
        t += 9 if x and y == 0 else y
    return (10 - t % 10) % 10 == d[9]
def luhn_ok(s):
    d = _digits(s)[::-1]
    return 13 <= len(d) <= 19 and sum(x if i % 2 == 0 else (2 * x - 9 if 2 * x > 9 else 2 * x) for i, x in enumerate(d)) % 10 == 0
CHECK = {"TCKN": tckn_ok, "YKN": tckn_ok, "VKN": vkn_ok, "CREDIT_CARD": luhn_ok}

def checksum_split(keys):
    """Recall on identity / card numbers, split by whether the gold value passes its check digits.
    Values written out in words are left out (no digits to check)."""
    out = {}
    for s in SETS:
        docs = load(s)
        for k in keys:
            f = PRED / f"{k}__{s}.jsonl"
            if not f.exists(): continue
            P = {json.loads(l)["id"]: json.loads(l)["spans"] for l in f.read_text().splitlines()}
            c = defaultdict(lambda: [0, 0])
            for d in docs:
                if s == "piimask" and d["track"] == "piimask-en": continue
                t, ps = d["text"], P.get(d["id"], [])
                for a, b, l in d["spans"]:
                    ty = MAP[s].get(l)
                    if ty not in CHECK or len(_digits(t[a:b])) < 8: continue
                    v = "valid" if CHECK[ty](t[a:b]) else "invalid"
                    c[(ty, v)][0] += 1
                    c[(ty, v)][1] += any(pt in ACCEPT[ty] and BS.matches(t[x:y], t[a:b]) for x, y, pt in ps)
            out.setdefault(s, {})[k] = {f"{ty} {v}": {"gold": g, "recall": h / g} for (ty, v), (g, h) in sorted(c.items())}
    return out


# ---- report
COLS = [("nm6k", "nm-kvkk-pii-6K test (602)"), ("piimask-tr", "piimask TR (180)"), ("piimask-tr-en", "piimask TR-EN (80)"),
        ("cagri-tam", "PII-masking 'mask all' (350)"), ("werea", "Werea test (240)")]
HOME = {"newmind-kvkk-v2": "nm6k", "werea-pii-150m": "werea", "girenit-pii-150m": "werea", "pii-guard-270m": "cagri-tam", "halilneed-pii": "cagri-tam"}
ORDER = ["base", "mini", "nano", "rules", "newmind-kvkk-v2", "horizon-pii-base", "hushmark-tr-289m", "werea-pii-150m", "girenit-pii-150m",
         "pii-guard-270m", "halilneed-pii", "presidio"]

def report(res):
    S = res["systems"]; keys = [k for k in ORDER if k in S] + [k for k in S if k not in ORDER]
    pct = lambda x: "–" if x != x else f"{100 * x:.1f}"
    L = ["# KVKK-Bench external track: test sets built by other teams", "",
         "Scores of every system on four public Turkish PII test sets that Katip did not build. All four sets are synthetic",
         "(generated by their authors; none contains real documents). Werea-co/Werea-KVKK-Bench and girenit/girenit-KVKK-Bench",
         "are byte-identical, so they are one column. Cells: **F2** on the types both sides label (recall weighted 4×), then",
         "**leak** (share of those personal-data characters left readable). † = the system was trained on that set's own",
         "training split, or by that set's authors (in-distribution).", ""]
    L.append("| System | " + " | ".join(c for _, c in COLS) + " | false masks / 1k words on PII-free text (200) |")
    L.append("|---|" + "---|" * (len(COLS) + 1))
    for k in keys:
        tr = S[k]["tracks"]; row = [S[k].get("name", k)]
        for c, _ in COLS:
            x = tr.get(c)
            row.append("" if not x else f"{pct(x['f2'])} · {pct(x['leak_core'])}{' †' if HOME.get(k) == c else ''}")
        n = tr.get("cagri-negatif"); row.append(f"{n['false_masks_per_1k_words']:.1f}" if n else "")
        L.append("| " + " | ".join(row) + " |")
    L += ["", "## Per-type recall (nm-kvkk-pii-6K test, piimask TR)", ""]
    for c in ["nm6k", "piimask-tr"]:
        types = sorted({t for k in keys if c in S[k]["tracks"] for t in S[k]["tracks"][c]["types"]},
                       key=lambda t: -max(S[k]["tracks"][c]["types"].get(t, {"gold": 0})["gold"] for k in keys if c in S[k]["tracks"]))
        L.append(f"**{c}**\n")
        L.append("| Type (gold) | " + " | ".join(k for k in keys if c in S[k]["tracks"]) + " |")
        L.append("|---|" + "---|" * sum(c in S[k]["tracks"] for k in keys))
        for t in types:
            g = next(S[k]["tracks"][c]["types"][t]["gold"] for k in keys if c in S[k]["tracks"] and t in S[k]["tracks"][c]["types"])
            L.append(f"| {t} ({g}) | " + " | ".join(pct(S[k]["tracks"][c]["types"].get(t, {}).get("recall", float("nan"))) for k in keys if c in S[k]["tracks"]) + " |")
        L.append("")
    L += ["## Precision and the other labels", "",
          "| System | set | recall | precision | recall, any type | precision vs every label | leak, all labels |", "|---|---|---|---|---|---|---|"]
    for k in keys:
        for c, _ in COLS:
            x = S[k]["tracks"].get(c)
            if x: L.append(f"| {k} | {c} | {pct(x['recall'])} | {pct(x['precision'])} | {pct(x['recall_any_type'])} | {pct(x['precision_any_label'])} | {pct(x['leak_all_labels'])} |")
    return "\n".join(L) + "\n"
