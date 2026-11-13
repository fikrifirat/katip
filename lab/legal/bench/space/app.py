"""KVKK-Bench leaderboard (Hugging Face Space, Gradio).

  pip install -r requirements.txt && python app.py

Reads result rows from results/*.json. Inside the Katip repository it falls back to ../results.
"""
from __future__ import annotations

import datetime as dt
import html, json, math, os, re
from pathlib import Path

import gradio as gr
import pandas as pd

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" if (HERE / "results").exists() else HERE.parent / "results"
REQUESTS = HERE / "requests"
VERSION = "v0.1.2 preview"

# key: (name, link). Only these rows are shown; every other scored system stays in results/.
SYSTEMS = {   # key: (model name, credit line, model link, developer link)
    "berturk-v2": ("Katip Mask Base · tr v2", "by f1k · 110M, fine-tuned from BERTurk (dbmdz)", "https://huggingface.co/f1k/katip-tr-pii-berturk", "https://huggingface.co/f1k"),
    "tiny-f":     ("Katip Mask Nano · tr v1.1 (preview)", "by f1k · 2.5M, runs in the browser", "https://github.com/fikrifirat/katip/pull/7", "https://huggingface.co/f1k"),
    "akdeniz":    ("XLM-RoBERTa Base Turkish NER", "by akdeniz27 · fine-tuned from XLM-R (Meta AI)", "https://huggingface.co/akdeniz27/xlm-roberta-base-turkish-ner", "https://huggingface.co/akdeniz27"),
    "gliner":     ("GLiNER Multi PII v1", "by urchade · GLiNER, NAACL 2024", "https://huggingface.co/urchade/gliner_multi_pii-v1", "https://huggingface.co/urchade"),
    "savasy":     ("BERTurk NER", "by savasy · BERTurk (dbmdz) fine-tuned for Turkish NER", "https://huggingface.co/savasy/bert-base-turkish-ner-cased", "https://huggingface.co/savasy"),
    "cosmos-pii": ("ModernBERT-TR PII NER", "by COSMOS Lab, Yıldız Technical University", "https://huggingface.co/ytu-ce-cosmos/modernbert-tr-pii-ner", "https://huggingface.co/ytu-ce-cosmos"),
    "qwen-1.5b":  ("Qwen2.5 1.5B Instruct (zero-shot)", "by Qwen Team, Alibaba Cloud", "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct", "https://huggingface.co/Qwen"),
    "presidio":   ("Presidio", "by Microsoft · spaCy xx_ent_wiki_sm by Explosion", "https://github.com/microsoft/presidio", "https://github.com/microsoft"),
}
REAL_TRACKS = {"court", "court-real", "court-filled", "court-turkish", "court-foreign", "prose", "scan"}
IDS = {"TCKN", "VKN", "PHONE", "EMAIL", "IBAN", "CREDIT_CARD", "ADDRESS", "PLATE", "BIRTH_DATE", "IP_ADDRESS"}
KIND = {"qwen-1.5b": "llm", "presidio": "rules"}   # everything else: fine-tuned model
TYPES = {"model": "🔶 Fine-tuned model", "llm": "💬 Prompted LLM", "rules": "⚙️ Rule-based toolkit"}
BASELINES = {"presidio", "savasy"}   # reference points, marked with a tag
LICENCE = {"berturk-v2": "CC BY-SA 4.0", "tiny": "CC BY-NC 4.0", "tiny-f": "CC BY-NC 4.0", "akdeniz": "MIT", "gliner": "Apache-2.0",
           "cosmos-pii": "Apache-2.0", "qwen-1.5b": "Apache-2.0", "presidio": "MIT"}
SIZES = ["< 10 MB", "10–500 MB", "> 500 MB"]

# Masking dimensions: what a masking tool has to catch. Each is scored as F2 (missing counts 4x more than over-masking).
# (header, tracks, types, weight in Overall, measured on real text?)
GEN_TRACKS = {"petition", "contract", "correspondence", "health", "court-generated", "petition-foreign"}
DIMS = {
    "tr_names": ("🇹🇷 Names", {"court", "court-real", "court-filled", "court-turkish", "petition", "contract", "correspondence", "health", "court-generated"}, {"PERSON"}, 25, True),
    "foreign":  ("🌍 Names", {"court-foreign", "petition-foreign"}, {"PERSON"}, 10, True),
    "everyday": ("📰 Names", {"prose"}, {"PERSON"}, 10, True),
    "tckn":     ("🪪 TCKN", GEN_TRACKS, {"TCKN"}, 10, False),
    "ids":      ("🔢 Other IDs", GEN_TRACKS, {"VKN", "YKN", "PASSPORT", "FOREIGN_ID", "IBAN", "CREDIT_CARD", "PLATE", "BIRTH_DATE"}, 10, False),
    "contact":  ("📞 Contact", GEN_TRACKS, {"PHONE", "EMAIL", "IP_ADDRESS"}, 10, False),
    "address":  ("🏠 Address", GEN_TRACKS, {"ADDRESS"}, 15, False),
    "health":   ("🩺 Health", GEN_TRACKS, {"HEALTH", "RELIGION", "ETHNICITY", "POLITICAL", "UNION", "SEXUAL_LIFE", "CRIMINAL_RECORD",
                                             "BIOMETRIC_GENETIC", "PHILOSOPHICAL", "ASSOCIATION", "DRESS"}, 10, False),
}
DIM_HELP = {
    "tr_names": "Turkish names in real Yargıtay decisions, in court casing (Ahmet YILMAZ) and with suffixes (Kaya'nın). Source: TurkishLegalNER test split (Koç University, Apache-2.0).",
    "foreign":  "Foreign clients' names (Arabic, Persian, Afghan, Georgian, Russian, Western…) in the same real Yargıtay sentences. Source: TurkishLegalNER test split (Koç University, Apache-2.0).",
    "everyday": "Names in ordinary Turkish sentences (Wikipedia), outside legal writing. Source: Turkish Wiki NER (Altinok 2023, CC BY-SA 4.0).",
    "tckn":     "T.C. kimlik numbers.",
    "ids":      "Tax numbers, foreigner IDs (YKN), passports, IBANs, card numbers, plates, birth dates.",
    "contact":  "Phone numbers, e-mail and IP addresses.",
    "address":  "Home and office addresses.",
    "health":   "Health and other KVKK article 6 special categories.",
}
COLUMNS = {  # key -> (header, tooltip, shown by default)
    "rank":    ("#", "Position, ranked by Overall.", True),
    "type":    ("T", "🔶 fine-tuned model · 💬 LLM asked by prompt · ⚙️ rule-based toolkit. Rows tagged baseline are standard reference points.", True),
    "model":   ("Model", "Click to open the model page.", True),
    "overall": ("Overall ⬆", "The ranking number, 0–100: the weighted average of the real-text masking dimensions (weights in the guide below). ◇ columns are previews and join the average once they have real test data.", True),
    **{k: (v[0] + ("" if v[4] else " ◇"), DIM_HELP[k] + " Score: F2, where missing one counts 4× more than masking too much." +
           ("" if v[4] else " ◇ Preview: measured on documents we generated, which Katip's models were also trained on, so not yet in Overall."), v[4])
       for k, v in DIMS.items()},
    "leak":    ("Leaked ⬇", "After masking, how much of the personal data in real text you could still read (by characters). Lower is better.", True),
    "params":  ("Params", "How many learned weights the model has.", False),
    "size":    ("Size", "What you download to run it. Small means it fits on a laptop or in a browser tab.", True),
    "speed":   ("ms/page", "Milliseconds to mask one page on a laptop CPU (Apple M-series, 12 cores).", True),
    "offline": ("Offline", "Runs on your own machine with no internet connection, so documents never leave the firm.", True),
    "browser": ("Browser", "Runs inside a web page: nothing to install, and the document never leaves your computer.", True),
    "licence": ("Licence", "Licence of the model. NC = no commercial use.", True),
}
NUM = ("overall", *DIMS, "leak")
SECONDARY = ("leak", "params", "size", "speed", "offline", "browser", "licence")

# Document types a firm feeds in (the dataset taxonomy). Pick some and every score is recomputed on just those documents.
DOC_TYPES = {
    "⚖️ Court decisions": {"court", "court-real", "court-filled", "court-turkish", "court-foreign"},
    "📰 General text": {"prose"},
    "📝 Petitions ◇": {"petition", "petition-foreign"},
    "📄 Contracts ◇": {"contract"},
    "✉️ Letters & e-mail ◇": {"correspondence"},
    "🩺 Health records ◇": {"health"},
    "🏛️ Court filings ◇": {"court-generated"},
}
DOC_HELP = "Which documents the scores come from. ◇ = generated by us (not yet real), so these only count when no real type is selected."

def load_rows():
    rows = []
    for p in RESULTS.glob("*.json"):
        r = json.loads(p.read_text())
        if r.get("system") not in SYSTEMS or r.get("split", "public") != "public" or r.get("version") not in ("v0.1.2",): continue
        if r["system"] == "presidio" and not r.get("size_mb"): r["size_mb"] = 11.0   # spaCy xx_ent_wiki_sm
        r["kind"] = KIND.get(r["system"], "model")
        rows.append(r)
    return score(rows, list(DOC_TYPES))

def score(rows, doc_types):
    """Fill each row's dimension scores, Overall and leak from the selected document types only, then rank."""
    sel = set().union(*(DOC_TYPES[d] for d in doc_types)) if doc_types else set()
    real_sel = bool(sel & REAL_TRACKS)
    ok = lambda x: x is not None and x == x
    f2 = lambda p, rc: 5 * p * rc / (4 * p + rc) if p + rc else 0.0
    for r in rows:
        tr = r["tracks"]
        for k, (_, tracks, types, w, _) in DIMS.items():
            g = f = pw = 0
            for t, x in tr.items():
                if t in tracks and t in sel and not (real_sel and DIMS[k][4] and t not in REAL_TRACKS):   # real text wins when selected
                    for ty, v in x["types"].items():
                        if ty in types and v["gold"]: g += v["gold"]; f += v["gold"] * v["recall"]; pw += v["gold"] * v["precision"]
            r[k] = f2(pw / g, f / g) if g else float("nan")
        # Overall: real-text dimensions only when any real document type is selected, otherwise the generated ones
        have = [(DIMS[k][3], r[k]) for k in DIMS if ok(r[k]) and (DIMS[k][4] or not real_sel)]
        r["overall"] = sum(w * v for w, v in have) / sum(w for w, _ in have) if have else float("nan")
        lk = [x["leak_rate"] for t, x in tr.items() if t in sel and (t in REAL_TRACKS or not real_sel) and ok(x["leak_rate"])]
        r["leak"] = sum(lk) / len(lk) if lk else float("nan")
    rows.sort(key=lambda r: -(r["overall"] if r["overall"] == r["overall"] else -1))
    for i, r in enumerate(rows, 1): r["rank"] = i
    return rows

def pct(x):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}"

def size(mb):
    if not mb: return "–"
    return f"{mb * 1000:.0f} KB" if mb < 1 else f"{mb:.0f} MB" if mb < 1000 else f"{mb / 1000:.1f} GB"

def params(n):
    if n is None: return "–"
    if n == 0: return "0 (rules)"
    return f"{n / 1e6:.0f}M" if n < 1e9 else f"{n / 1e9:.1f}B"

def size_bucket(mb):
    mb = mb or 0
    return SIZES[0] if mb < 10 else SIZES[1] if mb <= 500 else SIZES[2]

def cell(r, k, best):
    if k in NUM: return f"<b>{pct(r[k])}</b>" if r[k] == best[k] else pct(r[k])
    name, by, link, dev = SYSTEMS[r["system"]]
    tag = "<span class='tag'>baseline</span>" if r["system"] in BASELINES else ""
    return {"rank": str(r["rank"]), "type": f"<span title='{TYPES[r['kind']]}'>{TYPES[r['kind']].split()[0]}</span>",
            "model": f"<a href='{link}' target='_blank'>{html.escape(name)}</a>{tag}<div class='repo'><a href='{dev}' target='_blank'>{html.escape(by)}</a></div>",
            "params": params(r.get("params")), "size": size(r.get("size_mb")),
            "speed": f"{r['ms_per_page']:,.0f}" if r.get("ms_per_page") else "–",
            "offline": "✓" if r.get("runs_locally", True) else "", "browser": "✓" if r.get("runs_in_browser") else "", "licence": LICENCE.get(r["system"], "–")}[k]

def table(rows, cols):
    if not rows: return "<p class='empty'>No model matches the filters.</p>"
    best = {k: (min if k == "leak" else max)((r[k] for r in rows if r[k] == r[k]), default=None) for k in NUM}
    cls = lambda k: " class='l'" if k in ("model",) else " class='l sec'" if k == "licence" else " class='sec'" if k in SECONDARY else " class='ov'" if k == "overall" else " class='gen'" if k in DIMS and not DIMS[k][4] else ""
    head = "".join(f'<th{cls(k)} title="{html.escape(COLUMNS[k][1])}">{COLUMNS[k][0]}</th>' for k in cols)
    body = "".join("<tr>" + "".join(f"<td{cls(k)}>{cell(r, k, best)}</td>" for k in cols) + "</tr>" for r in rows)
    return f"<div class='wrap'><table class='lb'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"

def pick(rows, query, types, sizes, browser_only):
    q = (query or "").lower().strip()
    keep = {k for k, v in TYPES.items() if v in types}
    return [r for r in rows if r["kind"] in keep and size_bucket(r.get("size_mb")) in sizes
            and ("Runs in browser" not in (browser_only or []) or r.get("runs_in_browser"))
            and ("Commercial use OK" not in (browser_only or []) or "NC" not in LICENCE.get(r["system"], ""))
            and (not q or q in " ".join(SYSTEMS[r["system"]][:2]).lower())]

def chart(rows, x):
    import plotly.graph_objects as go
    key, title = ("size_mb", "Size (MB, log)") if x == "Size" else ("ms_per_page", "ms per page (log)")
    fig = go.Figure()
    for kind, label in TYPES.items():
        pts = [r for r in rows if r["kind"] == kind and r.get(key)]
        if not pts: continue
        fig.add_scatter(x=[r[key] for r in pts], y=[100 * r["overall"] for r in pts], mode="markers+text", name=label,
                        text=[SYSTEMS[r["system"]][0].split(" (")[0].split(" · ")[0] for r in pts], textposition="top center",
                        marker=dict(size=13, color={"model": "#f59e0b", "llm": "#8b5cf6", "rules": "#64748b"}[kind]),
                        hovertemplate="%{text}<br>Score %{y:.1f}<br>%{x}<extra></extra>")
    fig.update_layout(xaxis=dict(type="log", title=title), yaxis=dict(title="Score (KVKK-F2)", range=[0, 105]),
                      height=480, margin=dict(l=50, r=20, t=30, b=50), legend=dict(orientation="h", y=1.08),
                      template="plotly_white")
    return fig

ABOUT = """
**KVKK-Bench** measures how well tools find personal data in Turkish text, so it can be masked before a document is shared,
for example with a cloud AI. Every tool gets the same documents and the same scorer.

**Test data (v0.1.1, public)**
* 327 Yargıtay sentences from the *test split* of [TurkishLegalNER](https://github.com/koc-lab/turkish-legal-ner) (Koç University, Apache-2.0), used twice:
  the anonymised name slots are refilled once with unseen Turkish names (🇹🇷) and once with unseen foreign names (🌍), 1,011 names each.
* 1,000 Turkish Wikipedia sentences with hand-marked names: [Turkish Wiki NER](https://huggingface.co/datasets/turkish-nlp-suite/turkish-wikiNER) (Altinok 2023, CC BY-SA 4.0).
* 380 generated legal documents with ID numbers, IBANs, phones, addresses and health data. These feed the ◇ preview columns only.

Thanks to the dataset authors, and to every model developer credited under the model names.

A hidden test of 2025–26 court decisions is in preparation and will replace the public score.

**Metrics.** *Overall* is a weighted average of the real-text columns, each scored as F2. A value counts as found if the mask covers it, or at least half of it, with the right type.
*Leaked* is the share of personal-data characters left readable. Hover a column name for its definition.

**Links:** [dataset card](https://github.com/fikrifirat/katip/blob/legal-study/lab/legal/bench/README.md) ·
[scorer](https://github.com/fikrifirat/katip/blob/legal-study/lab/legal/bench_score.py) ·
[all results](https://github.com/fikrifirat/katip/tree/legal-study/lab/legal/bench/results) ·
[report a label error](https://github.com/fikrifirat/katip/issues/new/choose)

```
@misc{kvkkbenchtr2026, title={KVKK-Bench: a benchmark for personal-data masking in Turkish documents},
  author={{Katip contributors}}, year={2026}, url={https://github.com/fikrifirat/katip}}
```
"""

CSS = """
.gradio-container{max-width:1320px !important}
.intro p{margin:2px 0} .links a{margin-right:14px}
.wrap{overflow-x:auto}
table.lb{width:100%;border-collapse:collapse;border:none !important;font-size:.85rem;font-variant-numeric:tabular-nums}
table.lb th,table.lb td{padding:7px 6px;border:none !important;border-bottom:1px solid var(--border-color-primary) !important;text-align:right;background:none !important;white-space:nowrap}
table.lb th{font-weight:600;cursor:help;position:sticky;top:0;background:var(--background-fill-secondary) !important}
table.lb .l{text-align:left} table.lb td:nth-child(-n+2),table.lb th:nth-child(-n+2){text-align:center;width:28px}
table.lb tbody tr:hover td{background:var(--background-fill-secondary) !important}
table.lb a{text-decoration:none}
table.lb .sec{opacity:.6;font-size:.82rem} table.lb .gen{opacity:.55;font-style:italic} table.lb th.sec{border-left:none} table.lb td.ov{font-size:1rem} table.lb .tag{font-size:.68rem;color:#64748b;border:1px solid #cbd5e1;border-radius:4px;padding:0 4px;margin-left:6px;vertical-align:1px} table.lb .repo{font-size:.74rem;margin-top:1px} table.lb .repo a{color:#888!important;text-decoration:none;font-weight:400}
table.lb th.sec:first-of-type{padding-left:18px}
.empty{opacity:.7;padding:20px 0}
"""

def submit(model_id):
    model_id = (model_id or "").strip()
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", model_id): return "Enter a Hugging Face model id, e.g. `user/model`."
    REQUESTS.mkdir(exist_ok=True)
    p = REQUESTS / f"{model_id.replace('/', '__')}.json"
    p.write_text(json.dumps({"model": model_id, "status": "PENDING", "version": VERSION,
                             "submitted": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}))
    repo, token = os.environ.get("REQUESTS_REPO"), os.environ.get("HF_TOKEN")
    if repo and token:
        try:
            from huggingface_hub import HfApi
            HfApi(token=token).upload_file(path_or_fileobj=str(p), path_in_repo=p.name, repo_id=repo, repo_type="dataset")
        except Exception:
            return "Couldn't queue it. Please open a GitHub issue instead."
    return f"Queued **{model_id}**."

TRACK_NAMES = {"court-turkish": "🇹🇷 Real court text, Turkish names", "court-foreign": "🌍 Real court text, foreign names",
               "court-filled": "Real court text (Yargıtay sentences)", "prose": "📰 Real general text (Wikipedia sentences)",
               "petition-foreign": "Generated petitions for foreign clients",
               "petition": "Generated petitions", "contract": "Generated contracts", "correspondence": "Generated e-mails & chats",
               "health": "Generated health records", "court-generated": "Generated court decisions", "no-pii": "Text with no personal data"}

def by_test(rows, track):
    out = []
    for r in rows:
        x = r["tracks"].get(track)
        if not x: continue
        f = lambda v, nd=1: None if v is None or v != v else round(100 * v, nd)
        d = {"Model": SYSTEMS[r["system"]][0], "Found %": f(x["recall"]), "Precision %": f(x["precision"]), "Leaked %": f(x["leak_rate"]),
             "Docs fully clean %": f(x["clean_doc_rate"]), "False alarms / 1,000 words": round(x["false_per_1k_words"], 1)}
        for ty, v in x["types"].items():
            if v["gold"]: d[f"{ty} found % ({v['gold']})"] = f(v["recall"], 0)
        out.append(d)
    return pd.DataFrame(out)

BY_TEST_HELP = """**Found** = share of personal data the tool masked. **Precision** = share of masks that were really personal data.
**Leaked** = share of personal data still readable. **Docs fully clean** = documents with nothing left readable.
**False alarms** = masks on words that weren't personal data, per 1,000 words. The type columns show how much of each kind was found (the number in brackets is how many there are)."""

def build():
    rows = load_rows()
    empty = {k for k in DIMS if not any(r[k] == r[k] for r in rows)}   # dimensions with no test data yet (e.g. foreign names)
    default = [k for k, v in COLUMNS.items() if v[2] and k not in empty]
    optional = [k for k in COLUMNS if k not in ("rank", "type", "model") and k not in empty]
    with gr.Blocks(title="KVKK-Bench", css=CSS, theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"# 🛡️ KVKK-Bench\n"
                    "Lawyers, doctors and HR teams want to use AI on their documents, but under **KVKK** sending a client's name, "
                    "T.C. kimlik number or health record to a cloud service can be a violation. The safe way is to **mask personal data "
                    "on your own computer first**. This leaderboard tests which tools do that best on real Turkish text: same documents, same scorer for everyone.\n\n"
                    f"<span class='links'>[📄 Dataset card](https://github.com/fikrifirat/katip/blob/legal-study/lab/legal/bench/README.md)"
                    "[⚖️ Scorer](https://github.com/fikrifirat/katip/blob/legal-study/lab/legal/bench_score.py)"
                    f"[📊 Raw results](https://github.com/fikrifirat/katip/tree/legal-study/lab/legal/bench/results)</span> "
                    f"· {len(rows)} models · *{VERSION}*", elem_classes="intro")
        with gr.Tabs():
            with gr.Tab("🏅 Leaderboard"):
                with gr.Row():
                    q = gr.Textbox(placeholder="🔍 Search models", show_label=False, scale=3)
                    browser = gr.CheckboxGroup(["Runs in browser", "Commercial use OK"], value=[], show_label=False, scale=1)
                docs = gr.CheckboxGroup(list(DOC_TYPES), value=list(DOC_TYPES), label="Documents", info=DOC_HELP)
                with gr.Row():
                    types = gr.CheckboxGroup(list(TYPES.values()), value=list(TYPES.values()), label="Model type")
                    sizes = gr.CheckboxGroup(SIZES, value=SIZES, label="Size")
                with gr.Accordion("Columns", open=False):
                    cols = gr.CheckboxGroup([(COLUMNS[k][0].rstrip(" ⬆⬇*"), k) for k in optional],
                                            value=[k for k in default if k in optional], show_label=False)
                out = gr.HTML(table(rows, default))
                live = [k for k in DIMS if k not in empty]
                now = sum(DIMS[k][3] for k in live if DIMS[k][4])
                gr.Markdown(
                    "**Overall** = weighted average of the masking columns, each scored as F2 (a miss counts 4× more than an extra mask): " +
                    " · ".join(f"{DIMS[k][0]} {round(100 * DIMS[k][3] / now)}%" for k in live if DIMS[k][4]) +
                    ". ID, contact, address and health columns are hidden until we have real labelled documents for them (our generated ones would favour Katip); open **Columns** to see the ◇ previews.",
                    elem_classes="guide")
                def show(qv, tv, sv, bv, cv, dv):
                    rs = pick(score(rows, dv), qv, tv, sv, bv)
                    shown = [k for k in COLUMNS if k in cv and not (k in DIMS and not any(r[k] == r[k] for r in rs))]
                    return table(rs, ["rank", "type", "model"] + shown)
                for c in (q, types, sizes, browser, cols, docs):
                    c.change(show, [q, types, sizes, browser, cols, docs], out)
            with gr.Tab("📂 By test"):
                tracks = [t for t in TRACK_NAMES if any(t in r["tracks"] for r in rows)]
                dd = gr.Dropdown([(TRACK_NAMES[t], t) for t in tracks], value=tracks[0] if tracks else None, label="Test set")
                df = gr.Dataframe(by_test(rows, tracks[0]) if tracks else pd.DataFrame(), interactive=False, wrap=True)
                dd.change(lambda t: by_test(rows, t), dd, df)
                gr.Markdown(BY_TEST_HELP)
            with gr.Tab("📈 Score vs size/speed"):
                x = gr.Radio(["Size", "Speed"], value="Size", label="X axis")
                plot = gr.Plot(chart(rows, "Size"))
                x.change(lambda v: chart(rows, v), x, plot)
                gr.Markdown("Top-left is best: high score, small and fast.")
            with gr.Tab("📝 About"):
                gr.Markdown(ABOUT)
            with gr.Tab("🚀 Submit"):
                gr.Markdown("Enter a Hugging Face token-classification model. We evaluate it offline and add it to the table.")
                mid = gr.Textbox(label="Model id", placeholder="user/model")
                res = gr.Markdown()
                gr.Button("Submit", variant="primary").click(submit, mid, res)
    return demo

if __name__ == "__main__":
    build().launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
