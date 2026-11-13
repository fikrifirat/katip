"""Study 5 machinery: score every system on every set, choose trust on dev, open test once, test H1-H4,
draw the charts and tag the errors. The notebook 07_legal_study.ipynb calls these functions in order.

Everything follows lab/legal/DESIGN.md. Results go to lab/results/legal/.
"""
from __future__ import annotations

import hashlib, json, math, os, random, re, sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import katiplab as K  # noqa: E402
import legal as L  # noqa: E402
import local_detect  # noqa: E402  (unpacked by katiplab)

OUT = K.RESULTS / "legal"; OUT.mkdir(parents=True, exist_ok=True)
LW = K.DATA / "legal_web"
TRUSTS = (0.3, 0.5, 0.7, 0.9)
SYSTEM_TYPES = ["PERSON", "ADDRESS", "TCKN", "PHONE", "EMAIL", "IBAN", "PLATE", "BIRTH_DATE"]
MAX_CHARS = 12000          # long AYM judgments are cut (spans beyond are dropped) to keep scoring time sane
SEEDS = (0, 1, 2, 3, 4)

# --------------------------------------------------------------------------------------------- sets
def _load(p, cap=None):
    rows = K.load_jsonl(p) if p.exists() else []
    out = []
    for r in rows[:cap]:
        t = r["text"][:MAX_CHARS]
        out.append({**r, "text": t, "spans": [s for s in r["spans"] if s[1] <= len(t)]})
    return out

def check_hashes():
    """The test files must be the ones build_dataset.py wrote (no edits after the fact)."""
    m = json.loads((LW / "manifest.json").read_text())
    for s in ("test", "aym_names"):
        h = hashlib.sha256((LW / f"{s}.jsonl").read_bytes()).hexdigest()
        assert h == m["sha256"][s], f"{s}.jsonl changed since it was built"
    return m

def dev_sets():
    return {"legal-web dev": _load(LW / "dev.jsonl", cap=400), "heldout": K.load_synth("heldout"), "wiki dev": K.load_wiki("dev")}

def test_sets():
    K.get_wikiner(); koc = L.get_legal()
    s = {"legal-web test": _load(LW / "test.jsonl"), "AYM real names": _load(LW / "aym_names.jsonl"),
         "TurkishLegalNER (filled)": koc["unseen"], "wiki test": K.load_wiki("test"),
         "blind (synthetic)": K.load_synth("blind"), "negatives": K.load_synth("negatives")}
    tl = K.DATA / "tlner_test.jsonl"
    if tl.exists(): s["TLNER (external, NC)"] = K.load_jsonl(tl)
    return {k: v for k, v in s.items() if v}

def get_tlner():
    """TLNER (incidelen/TLNER, CC BY-NC 4.0): evaluation only. Needs Hugging Face access (Kaggle/Colab)."""
    p = K.DATA / "tlner_test.jsonl"
    if p.exists(): return p
    from datasets import load_dataset
    ds = load_dataset("incidelen/TLNER", split="test")
    names = ds.features["ner_tags"].feature.names if hasattr(ds.features["ner_tags"], "feature") else None
    with p.open("w", encoding="utf-8") as f:
        for i, r in enumerate(ds):
            words, tags = r["tokens"], [names[t] if names else t for t in r["ner_tags"]]
            text, spans, cur = "", [], None
            for w, t in zip(words, tags):
                if text and w not in K._NOSPACE_BEFORE: text += " "
                a = len(text); text += w
                if t.endswith("PER") and t.startswith("B"): cur = [a, len(text), "PERSON"]; spans.append(cur)
                elif t.endswith("PER") and cur: cur[1] = len(text)
                else: cur = None
            f.write(json.dumps({"id": f"tlner-{i}", "text": text, "spans": spans}, ensure_ascii=False) + "\n")
    return p

# ---------------------------------------------------------------------------------- model span cache
_tg = None
def _init(d):
    global _tg; _tg = K.Tagger(d)
def _spans(text): return _tg(text)

def model_spans(model_dir, docs, workers=None):
    """The model's raw spans for every doc, computed once (trust only changes the merge, not the model)."""
    with Pool(workers or os.cpu_count(), initializer=_init, initargs=(str(model_dir),)) as p:
        return p.map(_spans, [d["text"] for d in docs], chunksize=4)

def detections(docs, cache, trust):
    if cache is None:  # rules only
        return [[(x["start"], x["end"], x["entity_type"]) for x in local_detect.detect(d["text"], extra=[])] for d in docs]
    return [[(x["start"], x["end"], x["entity_type"]) for x in local_detect.detect(d["text"], extra=c, trust=trust)]
            for d, c in zip(docs, cache)]

def model_only(cache):
    return [[(s, e, t) for s, e, _, t in c] for c in cache]

# --------------------------------------------------------------------------------------------- scoring
def score_dets(docs, dets, types=("PERSON",)):
    """Per type: summary, CI and the paired rows (one bool per gold value, in a fixed order)."""
    out = {}
    for typ in types:
        g, s, _ = K.score(docs, lambda text, _it=iter(dets): next(_it), etype=typ)
        if not g and not s: continue
        out[typ] = {**K.summary(g, s), **K.bootstrap_ci(g, s), "found": [bool(r["found"]) for r in g],
                    "doc": [r["doc"] for r in g], "gold_text": [r["text"] for r in g],
                    "false_spans": [(r["doc"], r["text"]) for r in s if r["false"]]}
    return out

def leak_rate(docs, dets, types=SYSTEM_TYPES):
    """Share of gold PII characters left readable, and share of documents with nothing left readable."""
    tot = left = clean = n = 0
    for d, x in zip(docs, dets):
        gold = [(a, b) for a, b, t in d["spans"] if t in types]
        if not gold: continue
        n += 1; masked = np.zeros(len(d["text"]), bool)
        for s, e, _ in x: masked[s:e] = True
        L_ = sum(b - a - masked[a:b].sum() for a, b in gold)
        tot += sum(b - a for a, b in gold); left += L_; clean += L_ == 0
    return {"leak_rate": left / tot if tot else float("nan"), "clean_doc_rate": clean / n if n else float("nan")}

# ------------------------------------------------------------------------------------- trust on dev
def select_trust(dev, cache):
    """DESIGN.md section 7, step 1-2 on dev: legal-dev PERSON precision >= 95% and heldout recall >= 99.5%,
    then the highest legal-dev recall. If no trust passes, the most precise one, flagged."""
    rows = []
    for t in TRUSTS:
        r = {s: score_dets(docs, detections(docs, cache[s], t))["PERSON"] for s, docs in dev.items()}
        rows.append({"trust": t, **{f"{s} {m}": r[s][m] for s in dev for m in ("recall", "precision", "f2")}})
    ok = [r for r in rows if r["legal-web dev precision"] >= .95 and r["heldout recall"] >= .995]
    if ok:
        best = max(ok, key=lambda r: (r["legal-web dev recall"], r["trust"]))
        return best["trust"], rows, True
    best = max(rows, key=lambda r: r["legal-web dev precision"])
    return best["trust"], rows, False

def _strip(r):
    return {k: v for k, v in r.items() if k not in ("found", "doc", "gold_text", "false_spans")}

def run_system(name, model_dir=None, detector=None, seed=None, size_mb=None, keep_rows=True):
    """Score one system: choose trust on dev (Katip models), then open every test set once.
    model_dir: a Katip model folder (rules + model).  detector: any text -> spans function (baselines).
    Writes results/legal/<name>.json and returns it."""
    dev, test = dev_sets(), test_sets()
    res = {"name": name, "seed": seed, "size_mb": size_mb}
    if model_dir is not None:
        model_dir = Path(model_dir); res["size_mb"] = K.Tagger(model_dir).size_mb
        cdev = {s: model_spans(model_dir, d) for s, d in dev.items()}
        trust, rows, passed = select_trust(dev, cdev)
        res.update(trust=trust, dev=rows, constraints_met=passed)
        ctest = {s: model_spans(model_dir, d) for s, d in test.items()}
        dets = {s: detections(d, ctest[s], trust) for s, d in test.items()}
        dets_model = {s: model_only(ctest[s]) for s, d in test.items()}
    elif detector is not None:
        dets = {s: [detector(x["text"]) for x in d] for s, d in test.items()}; dets_model = None
    else:  # rules only
        dets = {s: detections(d, None, None) for s, d in test.items()}; dets_model = None
    res["test"] = {}
    for s, docs in test.items():
        r = score_dets(docs, dets[s], SYSTEM_TYPES)
        res["test"][s] = {"types": {t: (v if keep_rows else _strip(v)) for t, v in r.items()}, **leak_rate(docs, dets[s])}
        if dets_model:
            res["test"][s]["model_only_PERSON"] = _strip(score_dets(docs, dets_model[s]).get("PERSON", {}))
    (OUT / f"{name}.json").write_text(json.dumps(res, ensure_ascii=False, default=float))
    return res

# ------------------------------------------------------------------------------------------ statistics
def load_results():
    return {p.stem: json.loads(p.read_text()) for p in sorted(OUT.glob("*.json")) if not p.stem.startswith("_")}

def system_runs(R, system):
    """All seeds of one trained system, e.g. 'M2' -> [R['M2_s0'], R['M2_s1'], ...]."""
    return [R[k] for k in sorted(R) if re.fullmatch(rf"{re.escape(system)}_s\d+", k)]

def found(run, s, typ="PERSON"):
    return np.array(run["test"][s]["types"][typ]["found"], dtype=float)

def docs_of(run, s, typ="PERSON"):
    return run["test"][s]["types"][typ]["doc"]

def mcnemar(a, b):
    only_b = int(((b == 1) & (a == 0)).sum()); only_a = int(((a == 1) & (b == 0)).sum()); n = only_a + only_b
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(only_a, only_b) + 1)) / 2 ** n) if n else 1.0
    return {"only_a": only_a, "only_b": only_b, "p": p}

def hier_diff(runs_a, runs_b, s, B=2000, seed=0, typ="PERSON"):
    """Mean-over-seeds recall difference B - A on set s. Resample seeds, then documents (same docs for both)."""
    rng = np.random.default_rng(seed)
    FA = np.stack([found(r, s, typ) for r in runs_a]); FB = np.stack([found(r, s, typ) for r in runs_b])
    doc = np.array(docs_of(runs_a[0], s, typ)); ids = np.unique(doc); idx = [np.where(doc == i)[0] for i in ids]
    d0 = FB.mean() - FA.mean(); diffs = []
    for _ in range(B):
        sa = rng.integers(0, len(FA), len(FA)); sb = rng.integers(0, len(FB), len(FB))
        k = np.concatenate([idx[i] for i in rng.integers(0, len(ids), len(ids))])
        diffs.append(FB[sb][:, k].mean() - FA[sa][:, k].mean())
    diffs = np.array(diffs)
    return {"diff": float(d0), "ci": [float(np.quantile(diffs, .025)), float(np.quantile(diffs, .975))], "boot": diffs}

def holm(ps: dict, alpha=0.05):
    order = sorted(ps, key=ps.get); out, m, stop = {}, len(ps), False
    for i, k in enumerate(order):
        adj = min(1.0, ps[k] * (m - i)); stop = stop or adj > alpha
        out[k] = {"p": ps[k], "p_holm": adj, "reject": not stop}
    return out

def mean_recall(runs, s, typ="PERSON"):
    v = [r["test"][s]["types"][typ]["recall"] for r in runs]
    return {"mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0, "min": float(min(v)), "max": float(max(v)), "n": len(v)}

def hypotheses(R=None):
    """Test H1-H4 exactly as DESIGN.md section 4 states them. Returns a dict and writes _verdict.json."""
    R = R or load_results()
    B0, M1, M2, MV = (system_runs(R, x) for x in ("B0", "M1", "M2", "M2-vol"))
    real = [s for s in ("wiki test", "legal-web test", "AYM real names", "TLNER (external, NC)") if B0 and s in B0[0]["test"]]
    V = {"seeds": {k: len(v) for k, v in (("B0", B0), ("M1", M1), ("M2", M2), ("M2-vol", MV))}}
    # H1: synthetic minus real > 0, for B0 and M1, on every real set (independent sets -> independent bootstraps)
    h1 = {}
    for nm, runs in (("B0", B0), ("M1", M1)):
        for s in real:
            syn = np.stack([found(r, "blind (synthetic)") for r in runs]).mean(0)
            re_ = np.stack([found(r, s) for r in runs]).mean(0)
            rng = np.random.default_rng(0)
            d = [syn[rng.integers(0, len(syn), len(syn))].mean() - re_[rng.integers(0, len(re_), len(re_))].mean() for _ in range(2000)]
            h1[f"{nm} | {s}"] = {"diff": float(syn.mean() - re_.mean()), "ci": [float(np.quantile(d, .025)), float(np.quantile(d, .975))]}
    V["H1"] = {"detail": h1, "pass": all(v["ci"][0] > 0 for v in h1.values())}
    ps = {}
    def comp(a, b, s, margin=0.0):
        h = hier_diff(a, b, s); p = float(np.mean(h["boot"] <= margin))
        mc = [mcnemar(found(x, s), found(y, s)) for x, y in zip(a, b)]
        return {"diff": h["diff"], "ci": h["ci"], "p": p, "mcnemar_per_seed": mc}
    # H2: M1 > B0 on wiki test and AYM real names (both must hold -> the larger p counts)
    h2 = {s: comp(B0, M1, s) for s in ("wiki test", "AYM real names") if B0 and M1 and s in B0[0]["test"]}
    if h2: ps["H2"] = max(v["p"] for v in h2.values()); V["H2"] = {"detail": h2}
    # H3: M2 - M1 >= +1 point on legal-web test and AYM real names, precision drop <= 0.5 point
    if M1 and M2:
        h3 = {s: comp(M1, M2, s, margin=0.01) for s in ("legal-web test", "AYM real names") if s in M1[0]["test"]}
        prec = {s: float(np.mean([r["test"][s]["types"]["PERSON"]["precision"] for r in M2]) -
                         np.mean([r["test"][s]["types"]["PERSON"]["precision"] for r in M1])) for s in h3}
        ps["H3"] = max(v["p"] for v in h3.values())
        wiki = comp(M1, M2, "wiki test")
        V["H3"] = {"detail": h3, "precision_change": prec, "precision_ok": all(v >= -0.005 for v in prec.values()),
                   "H3-wiki non-inferiority": {**{k: wiki[k] for k in ("diff", "ci")}, "pass": wiki["ci"][0] > -0.02}}
    if M2 and MV:
        hv = comp(MV, M2, "legal-web test"); ps["H3-vol"] = hv["p"]; V["H3-vol"] = {"detail": hv}
    # H4: slot-filled legal test vs AYM real names, every system within 3 points, rankings agree
    sysmeans = {}
    for k in sorted({re.sub(r"_s\d+$", "", k) for k in R}):
        runs = system_runs(R, k) or ([R[k]] if k in R else [])
        if runs and all(s in runs[0]["test"] for s in ("legal-web test", "AYM real names")):
            sysmeans[k] = (mean_recall(runs, "legal-web test")["mean"], mean_recall(runs, "AYM real names")["mean"])
    if len(sysmeans) >= 3:
        a = np.array([v[0] for v in sysmeans.values()]); b = np.array([v[1] for v in sysmeans.values()])
        tau = _kendall(a, b); gaps = {k: v[0] - v[1] for k, v in sysmeans.items()}
        worst = max(gaps, key=lambda k: abs(gaps[k]))
        runs = system_runs(R, worst) or [R[worst]]
        F1 = np.stack([found(r, "legal-web test") for r in runs]).mean(0); F2 = np.stack([found(r, "AYM real names") for r in runs]).mean(0)
        rng = np.random.default_rng(0)
        g = np.array([F1[rng.integers(0, len(F1), len(F1))].mean() - F2[rng.integers(0, len(F2), len(F2))].mean() for _ in range(2000)])
        ps["H4"] = float(np.mean(np.abs(g) > 0.03))
        V["H4"] = {"recall (slot-filled, real names)": sysmeans, "gap": gaps, "kendall_tau": tau, "tau_ok": tau >= 0.8, "worst": worst}
    V["holm"] = holm(ps) if ps else {}
    for h in ("H2", "H3", "H3-vol", "H4"):
        if h not in V or h not in V["holm"]: continue
        ok = V["holm"][h]["reject"]
        if h == "H2": ok = ok and all(v["ci"][0] > 0 for v in V["H2"]["detail"].values())
        if h == "H3": ok = ok and V["H3"]["precision_ok"]
        if h == "H4": ok = ok and V["H4"]["tau_ok"]
        V[h]["pass"] = bool(ok)
    (OUT / "_verdict.json").write_text(json.dumps(V, indent=1, default=lambda o: None if isinstance(o, np.ndarray) else float(o)))
    return V

def _kendall(a, b):
    n, s = len(a), 0
    for i in range(n):
        for j in range(i + 1, n): s += np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
    return float(s / (n * (n - 1) / 2))

def select_model(R=None):
    """DESIGN.md section 7 over trained systems, on dev only (seed means)."""
    R = R or load_results(); cands = []
    for sysname in sorted({re.sub(r"_s\d+$", "", k) for k in R if re.search(r"_s\d+$", k)}):
        runs = system_runs(R, sysname)
        if not all(r.get("dev") for r in runs): continue
        dv = [next(x for x in r["dev"] if x["trust"] == r["trust"]) for r in runs]
        m = lambda k: float(np.mean([x[k] for x in dv]))
        size = runs[0]["size_mb"]
        cands.append({"system": sysname, "size_mb": size, "legal dev recall": m("legal-web dev recall"),
                      "legal dev precision": m("legal-web dev precision"), "heldout recall": m("heldout recall"),
                      "browser ok": size <= 150, "constraints ok": size <= 150 and m("legal-web dev precision") >= .95 and m("heldout recall") >= .995})
    ok = [c for c in cands if c["constraints ok"]] or cands
    best = max(ok, key=lambda c: (round(c["legal dev recall"], 3), -c["size_mb"])) if ok else None
    return best, cands

# ------------------------------------------------------------------------------------------ error tags
TITLES = re.compile(r"(Av\.|Avukat|Hâkim|Hakim|Bilirkişi|Raportör|Üye|Başkan|Savcı|Dr\.)\s*$")
WORDNAMES = {"Gül", "Can", "Bayram", "Barış", "Umut", "Deniz", "Ümit", "Şeker", "Bahar", "Yıldız", "Güneş", "Kaya", "Demir", "Doğan",
             "Aslan", "Kurt", "Bulut", "Çiçek", "Savaş", "Ay", "Toprak", "Su", "Nur", "Sevgi"}
def tag_error(text, a, b):
    s = text[a:b]; tags = []
    if s.isupper(): tags.append("ALL CAPS")
    if re.match(r"['’]", text[b:b + 1]): tags.append("case suffix")
    if re.fullmatch(r"(?:[A-ZÇĞİÖŞÜ]\.\s?)+", s.strip()): tags.append("initials only")
    if TITLES.search(text[max(0, a - 14):a]): tags.append("after a title")
    if any(w.strip("'’") in WORDNAMES for w in s.split()) : tags.append("name is also a word")
    if "\n" in s or "\n" in text[max(0, a - 2):a]: tags.append("line break")
    if not K.name_origin(s) == "turkish": tags.append("not in Turkish name lists")
    return tags or ["other"]

def error_analysis(R=None, systems=("B0_s0", "M1_s0", "M2_s0"), s="legal-web test", n_docs=200, seed=0):
    """Tag every PERSON miss and false name of the given runs on n_docs sampled test documents."""
    R = R or load_results(); docs = {d["id"]: d for d in test_sets()[s]}
    pick = set(random.Random(seed).sample(sorted(docs), min(n_docs, len(docs))))
    out = {}
    for name in systems:
        if name not in R: continue
        t = R[name]["test"][s]["types"]["PERSON"]; c, ex = Counter(), defaultdict(list)
        for d, g, f in zip(t["doc"], t["gold_text"], t["found"]):
            if f or d not in pick: continue
            text = docs[d]["text"]; a = text.find(g)
            for tg in tag_error(text, a, a + len(g)): c["miss: " + tg] += 1; ex["miss: " + tg].append(text[max(0, a - 40):a + len(g) + 20])
        for d, sp in t["false_spans"]:
            if d not in pick: continue
            text = docs[d]["text"]; a = text.find(sp)
            for tg in tag_error(text, a, a + len(sp)): c["false: " + tg] += 1; ex["false: " + tg].append(text[max(0, a - 40):a + len(sp) + 20])
        out[name] = {"counts": dict(c), "examples": {k: v[:10] for k, v in ex.items()}}
    (OUT / "_errors.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out
