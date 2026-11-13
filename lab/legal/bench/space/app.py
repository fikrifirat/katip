"""KVKK-Bench-TR leaderboard (Hugging Face Space, Gradio).

Reads result rows from ./results/*.json (or from the dataset repo named in RESULTS_REPO, if set) and shows:
leaderboard, per-track and per-type views, accuracy-vs-size chart, methodology, submission form, citation.
Run locally:  pip install -r requirements.txt && python app.py
"""
from __future__ import annotations

import datetime as dt
import json, math, os, re
from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
from gradio_leaderboard import ColumnFilter, Leaderboard, SearchColumns, SelectColumns

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
REQUESTS = HERE / "requests"
VERSION = "v0.1"

# ------------------------------------------------------------------------------------------ registry
# What we know about each system beyond its scores. Kind drives the colour and the filter.
SYSTEMS = {
    "rules":        {"kind": "Katip", "license": "AGPL-3.0", "link": "https://github.com/fikrifirat/katip"},
    "tiny":         {"kind": "Katip", "license": "CC BY-NC 4.0 (model)", "link": "https://huggingface.co/f1k/katip-tr-name-tagger-tiny"},
    "berturk-v2":   {"kind": "Katip", "license": "CC BY-SA 4.0 (model)", "link": "https://huggingface.co/f1k/katip-tr-pii-berturk"},
    "presidio":     {"kind": "Baseline", "license": "MIT", "link": "https://github.com/microsoft/presidio"},
    "kvkk-pii":     {"kind": "Baseline", "license": "MIT", "link": "https://pypi.org/project/kvkk-pii/"},
    "cosmos-pii":   {"kind": "Turkish PII model", "license": "Apache-2.0", "link": "https://huggingface.co/ytu-ce-cosmos/modernbert-tr-pii-ner"},
    "kvkk-pii-ner": {"kind": "Turkish PII model", "license": "Apache-2.0", "link": "https://huggingface.co/ersanbil/kvkk-pii-ner"},
    "openmed-tr":   {"kind": "Turkish PII model", "license": "Apache-2.0", "link": "https://huggingface.co/OpenMed/OpenMed-PII-Turkish-BiomedELECTRA-Large-335M-v1"},
    "gliner":       {"kind": "Multilingual PII model", "license": "Apache-2.0", "link": "https://huggingface.co/urchade/gliner_multi_pii-v1"},
    "savasy":       {"kind": "Turkish NER model", "license": "see card", "link": "https://huggingface.co/savasy/bert-base-turkish-ner-cased"},
    "akdeniz":      {"kind": "Turkish NER model", "license": "see card", "link": "https://huggingface.co/akdeniz27/xlm-roberta-base-turkish-ner"},
}
SHORT = {"rules": "Katip Rules v0.2", "tiny": "Katip Tiny", "berturk-v2": "Katip BERTurk v2", "presidio": "Presidio + spaCy",
         "kvkk-pii": "kvkk-pii regex", "cosmos-pii": "cosmos ModernBERT PII", "kvkk-pii-ner": "ersanbil kvkk-pii-ner",
         "openmed-tr": "OpenMed PII Turkish", "gliner": "GLiNER multi PII", "savasy": "savasy BERTurk NER", "akdeniz": "akdeniz XLM-R NER"}
for _k, _v in SHORT.items(): SYSTEMS[_k]["short"] = _v
BASELINE_NOTE = {"presidio": "reference baseline", "kvkk-pii": "floor baseline"}
REAL_TRACKS = ["court", "court-real", "court-filled", "prose", "scan"]
TRACKS = {  # name -> (title, plain-words explanation)
    "court": ("Court decisions 2025–26 (hidden)", "Yargıtay and Danıştay decisions. Courts publish them with names removed (\"...\"); we put realistic fake names, ID numbers and addresses back in the gaps."),
    "court-real": ("AYM judgments, real names (hidden)", "Constitutional Court judgments with the names the court itself published: judges, applicant, lawyer."),
    "court-filled": ("Yargıtay sentences", "2,918 Supreme Court sentences (TurkishLegalNER). Every anonymised name is refilled with a rare name, in court casing (Ahmet YILMAZ), with the case suffix fixed (Kaya'nın)."),
    "prose": ("Real Turkish sentences", "1,000 Wikipedia sentences with person names marked by people (Turkish Wiki NER). Real writing, not templates."),
    "petition": ("Petitions (generated)", "Dilekçe, ihtarname, icra takip talebi, vekaletname."),
    "contract": ("Contracts (generated)", "Kira and iş sözleşmesi, aydınlatma metni, fatura."),
    "correspondence": ("Messages (generated)", "E-posta, mesaj, mektup, tutanak, zabıt."),
    "health": ("Health (generated)", "Epikriz and bilirkişi raporu: KVKK art. 6 health data."),
    "court-generated": ("Court decisions (generated)", "Template court decisions."),
}

# Column -> tooltip. Shown on hover over the column header and in the metric guide.
TIPS = {
    "Rank": "Position by KVKK-F2. Systems whose confidence intervals overlap are effectively tied.",
    "System": "The model or tool, exactly as we ran it. Click the name to open its page.",
    "Kind": "Katip = this project. Baseline = what you get from standard open-source tools. Others = public models.",
    "KVKK-F2": "The ranking score, 0–100. How well the system finds personal data in REAL text, with a missed item counting 4× a false alarm (because a leak is worse than an extra black box). Averaged over the real-text tracks.",
    "vs Presidio": "Points of KVKK-F2 above (+) or below (−) the reference baseline, Presidio + spaCy: what a team gets from the standard open-source tool with no Turkish work.",
    "Leak %": "Lower is better. Of all the characters that are personal data, the share left readable after masking. A half-masked name counts as half a leak.",
    "Clean docs %": "Share of documents where NOTHING personal was left readable. This is what a lawyer actually needs.",
    "Court names": "Names found in real Yargıtay sentences (court-filled track), %.",
    "Real prose": "Names found in real Wikipedia sentences, %. Shows whether the system generalises beyond legal templates.",
    "Generated (check)": "F2 on generated documents. A regression check only, never ranked: Katip's models were trained on documents from the same generator.",
    "Precision": "Of everything the system masked, the share that really was personal data. Low precision = lots of unnecessary black boxes.",
    "Params": "Number of learned weights, in millions. Rules have none.",
    "Size MB": "What you download to run it (for Katip: the int8 ONNX file the browser loads, plus 0.3 MB of rules).",
    "Words/s": "Speed on a laptop CPU: words processed per second. Higher is faster. Compare only rows measured on the same machine.",
    "ms/page": "Milliseconds to process a 500-word page on CPU.",
    "In browser": "Runs entirely inside a web page (no server, no upload). The document never leaves the computer.",
    "Licence": "Licence of the model or tool. Check it before commercial use.",
}
GLOSSARY_TR = {
    "KVKK-F2": "Gerçek metinde kişisel verileri bulma puanı; kaçırılan bir veri, fazladan maskelenen bir kelimeden 4 kat ağır sayılır.",
    "Leak %": "Maskelemeden sonra okunabilir kalan kişisel veri oranı (karakter bazında). Düşük olan iyi.",
    "Clean docs %": "Hiçbir kişisel verinin okunabilir kalmadığı belgelerin oranı.",
    "In browser": "Tamamen tarayıcıda çalışır; belge bilgisayardan çıkmaz.",
}

# ------------------------------------------------------------------------------------------ data
def load_rows():
    repo = os.environ.get("RESULTS_REPO")
    if repo:  # results stored in a HF dataset repo, written by the evaluator
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(repo, repo_type="dataset", local_dir=str(RESULTS), allow_patterns=["*.json"])
        except Exception as e:  # keep serving the bundled results
            print("could not refresh results:", e)
    rows = [json.loads(p.read_text()) for p in sorted(RESULTS.glob("*.json"))]
    out = []
    for r in rows:
        if r["system"] == "presidio" and not r.get("size_mb"): r["size_mb"] = 11.0   # spaCy xx_ent_wiki_sm; Presidio's own code is tiny
        tr = r["tracks"]
        f = lambda keep: [x["f2"] for t, x in tr.items() if keep(t) and x["f2"] == x["f2"]]
        real, gen = f(lambda t: t in REAL_TRACKS), f(lambda t: t not in REAL_TRACKS)
        r["kvkk_f2"] = sum(real) / len(real) if real else float("nan")
        r["gen_f2"] = sum(gen) / len(gen) if gen else float("nan")
        cl = [x["clean_doc_rate"] for t, x in tr.items() if t in REAL_TRACKS and x["clean_doc_rate"] == x["clean_doc_rate"]]
        lk = [x["leak_rate"] for t, x in tr.items() if t in REAL_TRACKS and x["leak_rate"] == x["leak_rate"]]
        pr = [x["precision"] for t, x in tr.items() if t in REAL_TRACKS]
        r["clean_real"] = sum(cl) / len(cl) if cl else float("nan")
        r["leak_real"] = sum(lk) / len(lk) if lk else float("nan")
        r["prec_real"] = sum(pr) / len(pr) if pr else float("nan")
        out.append(r)
    return out

def _p(x, nd=1):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(100 * x, nd)

def link(r):
    meta = SYSTEMS.get(r["system"], {})
    name = meta.get("short", r["name"]) + (f" ({BASELINE_NOTE[r['system']]})" if r["system"] in BASELINE_NOTE else "")
    return f"[{name}]({meta['link']})" if meta.get("link") else name

def main_table(rows, split):
    rs = sorted([r for r in rows if r.get("split") == split], key=lambda r: -(r["kvkk_f2"] if r["kvkk_f2"] == r["kvkk_f2"] else -1))
    data = []
    base = next((r["kvkk_f2"] for r in rs if r["system"] == "presidio"), None)
    for i, r in enumerate(rs, 1):
        meta = SYSTEMS.get(r["system"], {})
        data.append({
            "Rank": i, "System": link(r), "Kind": meta.get("kind", "Other"),
            "KVKK-F2": _p(r["kvkk_f2"]),
            "vs Presidio": None if base is None else round(100 * (r["kvkk_f2"] - base), 1), "Leak %": _p(r["leak_real"], 2), "Clean docs %": _p(r["clean_real"]),
            "Court names": _p(r["tracks"].get("court-filled", {}).get("recall")),
            "Real prose": _p(r["tracks"].get("prose", {}).get("recall")),
            "Generated (check)": _p(r["gen_f2"]), "Precision": _p(r["prec_real"]),
            "Params": None if r.get("params") is None else round(r["params"] / 1e6, 1),
            "Size MB": r.get("size_mb"), "Words/s": r.get("words_per_s"), "ms/page": r.get("ms_per_page"),
            "In browser": bool(r.get("runs_in_browser")), "Licence": meta.get("license", ""),
        })
    cols = list(TIPS)
    return pd.DataFrame(data, columns=cols)

def track_table(rows, split, track):
    data = []
    for r in rows:
        if r.get("split") != split or track not in r["tracks"]: continue
        x = r["tracks"][track]
        data.append({"System": link(r), "F2": _p(x["f2"]), "Recall": _p(x["recall"]), "Precision": _p(x["precision"]),
                     "Leak %": _p(x["leak_rate"], 2), "Clean docs %": _p(x["clean_doc_rate"]),
                     "False alarms / 1k words": round(x.get("false_per_1k_words", float("nan")), 2)})
    return pd.DataFrame(data).sort_values("F2", ascending=False, na_position="last") if data else pd.DataFrame()

def type_table(rows, split, track):
    data = []
    for r in rows:
        if r.get("split") != split or track not in r["tracks"]: continue
        row = {"System": link(r)}
        for t, v in r["tracks"][track]["types"].items():
            if v["gold"]: row[f"{t} ({v['gold']})"] = _p(v["recall"])
        data.append(row)
    return pd.DataFrame(data)

def size_chart(rows, split):
    rs = [r for r in rows if r.get("split") == split and r["kvkk_f2"] == r["kvkk_f2"]]
    fig = go.Figure()
    colours = {"Katip": "#2a78d6", "Baseline": "#eb6834", "Turkish PII model": "#1baf7a", "Multilingual PII model": "#6250d6", "Turkish NER model": "#e87ba4"}
    for kind, c in colours.items():
        k = [r for r in rs if SYSTEMS.get(r["system"], {}).get("kind") == kind]
        if not k: continue
        fig.add_trace(go.Scatter(
            x=[max(r.get("size_mb") or 0.1, 0.1) for r in k], y=[100 * r["kvkk_f2"] for r in k], mode="markers+text", name=kind,
            text=[SYSTEMS.get(r["system"], {}).get("short", r["name"]) for r in k], textposition=["top center" if i % 2 == 0 else "bottom center" for i in range(len(k))],
            marker=dict(size=13, color=c, line=dict(width=2, color="white")),
            hovertemplate="<b>%{text}</b><br>KVKK-F2 %{y:.1f}<br>%{x:.1f} MB<extra></extra>"))
    fig.update_layout(xaxis=dict(type="log", title="Download size (MB, log scale) — smaller is easier to run privately"),
                      yaxis=dict(title="KVKK-F2 on real text (higher is better)", range=[-6, 102]),
                      height=460, margin=dict(l=40, r=20, t=30, b=50), legend=dict(orientation="h", y=-0.2),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig

# ------------------------------------------------------------------------------------------ copy
INTRO = f"""
<div class="hero">
  <h1>🛡️ KVKK-Bench-TR</h1>
  <p class="sub">Which tool actually removes personal data from Turkish documents? · <i>Türkçe belgelerde kişisel verileri hangi araç gerçekten maskeliyor?</i></p>
  <p>Law firms, hospitals and HR teams want to use AI on their documents, but under <b>KVKK</b> (Law No. 6698) sending a client's
  name, T.C. kimlik number or health record to a cloud service can be a violation. The safe path is to <b>mask personal data first,
  on your own computer</b>. This leaderboard measures how well each masking tool does that on <b>real Turkish text</b>: court
  decisions, everyday prose and the documents lawyers handle, with special attention to <b>KVKK art. 6</b> sensitive data such as health.</p>
  <p>We rank on <b>real text only</b>, we count a <b>missed name as worse than an extra black box</b>, and we report <b>what was left readable</b>.
  Every system gets the same documents and the same scorer. Size and speed are listed so you can pick something that runs privately on a laptop.</p>
  <p class="small">Version {VERSION} · public split (the hidden court test is being built from 2025–26 decisions) · dataset card and scorer: <a href="https://github.com/fikrifirat/katip/tree/legal-study/lab/legal/bench">github.com/fikrifirat/katip</a></p>
</div>
"""

def guide_html():
    chips = "".join(f'<span class="chip" data-tip="{v}">{k} ⓘ</span>' for k, v in TIPS.items()
                    if k in ("KVKK-F2", "Leak %", "Clean docs %", "Generated (check)", "Precision", "Size MB", "Words/s", "In browser"))
    return f'<div class="guide"><b>What the columns mean</b> (hover): {chips}</div>'

ABOUT = """
## Why this exists

Turkish PII models are appearing on Hugging Face, but each one reports scores on its **own** data, usually synthetic
documents or a validation split. None of them shares a test with another, so nobody can say which one to trust. Our own
study shows why that matters: a BERTurk model trained on synthetic documents finds **100%** of names in synthetic tests
and **40.7%** in real sentences. A score only means something on text the model has never seen and that looks like real work.

## What we measure

| Column | In plain words | Türkçe |
| --- | --- | --- |
| **KVKK-F2** | How well personal data is found in **real** text. Missing something counts 4× as much as masking too much. 0–100, higher is better. This is the ranking. | Gerçek metinde kişisel veriyi bulma puanı |
| **Leak %** | After masking, the share of personal-data characters you can still read. Lower is better. | Okunabilir kalan kişisel veri oranı |
| **Clean docs %** | Documents with nothing personal left readable. | Tamamen temizlenmiş belge oranı |
| **Court names / Real prose** | Share of names found in real court sentences / real Wikipedia sentences. | Bulunan isim oranı |
| **Generated (check)** | Score on generated documents. Shown, never ranked: Katip trained on the same generator. | Kontrol amaçlı, sıralamaya girmez |
| **Precision** | Of what was masked, how much really was personal data. | Doğru maskeleme oranı |
| **Params / Size MB** | Model weights (millions) / what you download to run it. | Model büyüklüğü |
| **Words/s, ms/page** | Speed on a laptop CPU. A page = 500 words. | Hız |
| **In browser** | Runs inside a web page; the document never leaves the computer. | Tarayıcıda çalışır |

**Matching.** A masked span counts if it covers the true value, or at least half of it (3+ characters), and has the right type.
Strict exact-match numbers are in the result files. **Entity types:** person names, T.C. kimlik, tax number, phone, e-mail, IBAN,
card number, address, plate, birth date, and the KVKK art. 6 special categories (health, religion, ethnicity, political opinion,
union, sexual life, criminal record, biometric/genetic, association, dress).

## The data

* **Yargıtay sentences**: TurkishLegalNER (Çetindağ et al. 2022, Apache-2.0). Courts publish decisions anonymised, so the "..."
  slots are refilled with rare names in court casing, with Turkish case suffixes fixed to agree.
* **Real Turkish sentences**: Turkish Wiki NER test (Altinok 2023, CC BY-SA 4.0).
* **Generated documents**: 16 document styles from Katip's generator (petitions, contracts, messages, health records).
* **Hidden test (coming)**: Yargıtay and Danıştay decisions from 2025–26 with slots filled, and Constitutional Court (AYM)
  judgments with the real names the court published. Hidden so nobody can train on it; refreshed every year.

Every value we insert is synthetic. Court decisions have no copyright in Turkey (FSEK art. 31).

## Baselines

* **Presidio + spaCy** (unmodified): the most widely used open-source PII tool. *Reference baseline.*
* **kvkk-pii** regex library: what pattern matching alone gives. *Floor.*

## Known limits

The generated tracks are small in v0.1 and come from one generator. Court decisions aren't client files. There are very
few art. 6 examples yet. One annotator so far; v0.2 adds a second annotator and reports agreement. Read the dataset card for the full list.

## Found a mistake?

Open an issue with the *Benchmark label error* template on GitHub: give the document id, the offsets and the fix. If you see
real personal data that shouldn't be in the benchmark, tick *privacy*; we remove it within 7 days. Every fix gets a version
number and all systems are re-scored. Scores never change silently.
"""

SUBMIT = """
## Submit a system

**Ranked (recommended).** Give us a Hugging Face model repo (token classification, or any repo with a `predict(text) -> [[start, end, TYPE], ...]`
function in `kvkk_bench.py`). We run it **offline** on the hidden test, so your model never sees the test text and nobody sees your weights
beyond what is public. Results appear here with the date and the exact revision.

**Self-reported.** Run the public split yourself and send the predictions file:

```
{"id": "tlner-legal-unseen-12", "spans": [[45, 58, "PERSON"], [76, 87, "TCKN"]]}
```

Score it locally first: `python bench_score.py gold.jsonl predictions.jsonl` (in the Katip repository, `lab/legal/`).
Self-reported rows are marked as such and are never mixed into the ranked table.
"""

CITATION = """@misc{kvkkbenchtr2026,
  title  = {KVKK-Bench-TR: a benchmark for personal-data masking in Turkish documents},
  author = {{Katip contributors}},
  year   = {2026},
  url    = {https://github.com/fikrifirat/katip}
}"""

CSS = """
.hero{padding:8px 4px 0} .hero h1{font-size:2.1rem;margin:0} .hero .sub{font-size:1.1rem;margin:.2rem 0 .8rem;opacity:.85}
.hero p{max-width:980px;line-height:1.55} .small{font-size:.85rem;opacity:.7}
.guide{margin:.2rem 0 .6rem;line-height:2.2} .chip{display:inline-block;margin:0 6px 0 0;padding:1px 10px;border-radius:999px;
 border:1px solid var(--border-color-primary);font-size:.85rem;position:relative;cursor:help;white-space:nowrap}
.chip:hover::after{content:attr(data-tip);position:absolute;left:0;top:120%;z-index:50;width:300px;white-space:normal;
 background:var(--background-fill-primary);color:var(--body-text-color);border:1px solid var(--border-color-primary);
 padding:8px 10px;border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.15);font-size:.82rem;line-height:1.4}
.stat{border:1px solid var(--border-color-primary);border-radius:12px;padding:10px 14px} .stat b{font-size:1.4rem;display:block}
"""
# Native tooltips on every column header: put the explanation in the header cell's title attribute.
HEAD = "<script>const KB_TIPS=" + json.dumps(TIPS) + """;
function kbTips(){document.querySelectorAll('th, th *').forEach(el=>{const t=(el.innerText||'').trim().replace(/[▲▼↑↓⇅]/g,'').trim();
 if(KB_TIPS[t]){const th=el.closest('th')||el; th.title=KB_TIPS[t]; th.style.cursor='help';}});}
new MutationObserver(kbTips).observe(document.documentElement,{childList:true,subtree:true});</script>"""

# ------------------------------------------------------------------------------------------ app
def save_request(model_id, contact, notes):
    model_id = (model_id or "").strip()
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", model_id):
        return "Please give a Hugging Face model id like `user/model-name`."
    REQUESTS.mkdir(exist_ok=True)
    req = {"model": model_id, "contact": (contact or "").strip()[:200], "notes": (notes or "").strip()[:1000],
           "status": "PENDING", "submitted": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", "version": VERSION}
    p = REQUESTS / f"{model_id.replace('/', '__')}.json"
    p.write_text(json.dumps(req, indent=1))
    repo, token = os.environ.get("REQUESTS_REPO"), os.environ.get("HF_TOKEN")
    if repo and token:
        try:
            from huggingface_hub import HfApi
            HfApi(token=token).upload_file(path_or_fileobj=str(p), path_in_repo=p.name, repo_id=repo, repo_type="dataset",
                                           commit_message=f"submission: {model_id}")
        except Exception as e:
            return f"Saved locally but could not queue it ({e}). Please open a GitHub issue instead."
    return f"✅ **{model_id}** is queued. We run it offline on the hidden test and post the result here, usually within a week."

def build():
    rows = load_rows()
    has_hidden = any(r.get("split") == "hidden" for r in rows)
    split = "hidden" if has_hidden else "public"
    df = main_table(rows, split)
    with gr.Blocks(title="KVKK-Bench-TR", css=CSS, head=HEAD, theme=gr.themes.Soft(primary_hue="blue")) as demo:
        gr.HTML(INTRO)
        if len(df):
            best = df.iloc[0]
            small = df[df["In browser"]].sort_values("KVKK-F2", ascending=False)
            clean = lambda md: re.sub(r"^\[(.*?)\]\(.*\)$", r"\1", md)
            best_name, small_name = clean(best["System"]), clean(small.iloc[0]["System"]) if len(small) else "–"
            with gr.Row():
                gr.HTML(f'<div class="stat">Best on real text<b>{best_name}</b>KVKK-F2 {best["KVKK-F2"]}, {best["vs Presidio"]:+} points over Presidio</div>')
                gr.HTML(f'<div class="stat">Best that runs in a browser<b>{small_name}</b>{small.iloc[0]["Size MB"] if len(small) else ""} MB download, nothing leaves the computer</div>')
                gr.HTML(f'<div class="stat">Systems compared<b>{len(df)}</b>{"hidden test" if has_hidden else "public split (hidden test coming)"}</div>')
        with gr.Tabs():
            with gr.Tab("🏆 Leaderboard"):
                gr.HTML(guide_html())
                Leaderboard(
                    value=df, datatype=["number", "markdown", "str"] + ["number"] * 12 + ["bool", "str"],
                    select_columns=SelectColumns(default_selection=[c for c in df.columns if c not in ("Licence", "Precision", "ms/page")],
                                                 cant_deselect=["Rank", "System", "KVKK-F2"], label="Columns to show"),
                    search_columns=SearchColumns(primary_column="System", secondary_columns=["Kind"], placeholder="Search a model, e.g. berturk or cosmos", label="Search"),
                    filter_columns=[ColumnFilter("Kind", type="checkboxgroup", label="Kind of system"),
                                    ColumnFilter("In browser", type="boolean", label="Only systems that run in the browser (document never leaves the computer)", default=False),
                                    ColumnFilter("Size MB", type="slider", min=0.0, default=[0.0, max(500, float(df["Size MB"].fillna(0).max() or 1))], max=max(500, float(df["Size MB"].fillna(0).max() or 1)), label="Max download size (MB)")],
                    hide_columns=[], height=520)
                gr.Markdown("Ranking = **KVKK-F2 on real text**. *Generated (check)* is shown but never ranked. Hover a column name for what it means. "
                            "Speeds are comparable only between rows measured on the same machine (recorded in each result file).")
            with gr.Tab("📈 Accuracy vs size"):
                gr.Markdown("Up and to the left is best: high accuracy on real text, small enough to run privately on a laptop or in a browser tab.")
                gr.Plot(size_chart(rows, split))
            with gr.Tab("📂 By document type"):
                choices = [(TRACKS.get(t, (t, ""))[0], t) for t in TRACKS if any(t in r["tracks"] for r in rows if r.get("split") == split)]
                dd = gr.Dropdown(choices=choices, value=choices[0][1] if choices else None, label="Track")
                expl = gr.Markdown(TRACKS[choices[0][1]][1] if choices else "")
                tt = gr.Dataframe(track_table(rows, split, choices[0][1]) if choices else pd.DataFrame(), datatype="markdown", interactive=False, wrap=True)
                dd.change(lambda t: (TRACKS.get(t, ("", ""))[1], track_table(rows, split, t)), dd, [expl, tt])
            with gr.Tab("🔤 By data type"):
                gr.Markdown("Recall (%) for each kind of personal data. The number in brackets is how many such values the track contains. "
                            "KVKK art. 6 special categories (HEALTH, UNION, …) are the most sensitive and the rarest.")
                dd2 = gr.Dropdown(choices=choices, value=choices[0][1] if choices else None, label="Track")
                ty = gr.Dataframe(type_table(rows, split, choices[0][1]) if choices else pd.DataFrame(), datatype="markdown", interactive=False, wrap=True)
                dd2.change(lambda t: type_table(rows, split, t), dd2, ty)
            with gr.Tab("📖 About & method"):
                gr.Markdown(ABOUT)
                with gr.Accordion("Türkçe özet", open=False):
                    gr.Markdown("\n".join(f"* **{k}**: {v}" for k, v in GLOSSARY_TR.items()) +
                                "\n\nKVKK-Bench-TR, Türkçe belgelerdeki kişisel verileri maskeleyen araçları **gerçek metin** üzerinde karşılaştırır. "
                                "Kaçırılan bir isim, fazladan karartılan bir kelimeden daha ağır sayılır.")
            with gr.Tab("🚀 Submit"):
                gr.Markdown(SUBMIT)
                with gr.Row():
                    mid = gr.Textbox(label="Hugging Face model id", placeholder="user/model-name")
                    contact = gr.Textbox(label="Contact (optional)", placeholder="GitHub handle or e-mail")
                notes = gr.Textbox(label="Notes (optional)", placeholder="Labels it predicts, how to call it, licence", lines=3)
                out = gr.Markdown()
                gr.Button("Queue for evaluation", variant="primary").click(save_request, [mid, contact, notes], out)
            with gr.Tab("📝 Citation"):
                gr.Markdown("If you use the benchmark, please cite it, and TurkishLegalNER (Çetindağ, Yazıcıoğlu & Koç 2022) and Turkish Wiki NER (Altinok 2023).")
                gr.Code(CITATION, language=None, label="BibTeX")
    return demo

if __name__ == "__main__":
    build().launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
