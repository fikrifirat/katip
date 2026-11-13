"""KVKK-Bench-TR leaderboard (Hugging Face Space, Gradio).

  pip install -r requirements.txt && python app.py

Reads result rows from results/*.json. Inside the Katip repository it falls back to ../results.
"""
from __future__ import annotations

import datetime as dt
import html, json, math, os, re
from pathlib import Path

import gradio as gr

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" if (HERE / "results").exists() else HERE.parent / "results"
REQUESTS = HERE / "requests"
VERSION = "v0.1 preview"

# key: (name, link). Only these rows are shown; every other scored system stays in results/.
SYSTEMS = {
    "berturk-v2": ("Katip", "https://huggingface.co/f1k/katip-tr-pii-berturk"),
    "tiny":       ("Katip Tiny", "https://huggingface.co/f1k/katip-tr-name-tagger-tiny"),
    "akdeniz":    ("akdeniz27/xlm-roberta-base-turkish-ner", "https://huggingface.co/akdeniz27/xlm-roberta-base-turkish-ner"),
    "gliner":     ("urchade/gliner_multi_pii-v1", "https://huggingface.co/urchade/gliner_multi_pii-v1"),
    "cosmos-pii": ("ytu-ce-cosmos/modernbert-tr-pii-ner", "https://huggingface.co/ytu-ce-cosmos/modernbert-tr-pii-ner"),
    "qwen-1.5b":  ("Qwen/Qwen2.5-1.5B-Instruct (prompted)", "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct"),
    "presidio":   ("Presidio + spaCy (baseline)", "https://github.com/microsoft/presidio"),
}
REAL_TRACKS = {"court", "court-real", "court-filled", "prose", "scan"}
IDS = {"TCKN", "VKN", "PHONE", "EMAIL", "IBAN", "CREDIT_CARD", "ADDRESS", "PLATE", "BIRTH_DATE", "IP_ADDRESS"}

COLUMNS = {  # header -> tooltip
    "Score": "F2 on real Turkish text (court decisions and everyday sentences). Recall counts 4× precision, because a missed name is worse than an extra mask.",
    "Names": "Share of person names masked in the real-text tests.",
    "IDs": "Share of T.C. kimlik, tax and phone numbers, IBANs, e-mails, addresses and plates masked. Measured on generated documents, so not part of the score.",
    "Leaked": "Share of personal data still readable after masking, real text. Lower is better.",
    "Size": "Download size.",
    "Browser": "Runs inside the web browser, so the document never leaves the computer.",
}

def load_rows():
    rows = []
    for p in RESULTS.glob("*.json"):
        r = json.loads(p.read_text())
        if r.get("system") not in SYSTEMS or r.get("split", "public") != "public": continue
        tr = r["tracks"]
        ok = lambda x: x is not None and x == x
        mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
        def recall(tracks, types):
            g = f = 0
            for t, x in tr.items():
                if t in tracks:
                    for ty, v in x["types"].items():
                        if ty in types and v["gold"]: g += v["gold"]; f += v["gold"] * v["recall"]
            return f / g if g else float("nan")
        r["score"] = mean([x["f2"] for t, x in tr.items() if t in REAL_TRACKS and ok(x["f2"])])
        r["names"] = recall(REAL_TRACKS, {"PERSON"})
        r["ids"] = recall(set(tr), IDS)
        r["leak"] = mean([x["leak_rate"] for t, x in tr.items() if t in REAL_TRACKS and ok(x["leak_rate"])])
        if r["system"] == "presidio" and not r.get("size_mb"): r["size_mb"] = 11.0   # spaCy xx_ent_wiki_sm
        rows.append(r)
    return sorted(rows, key=lambda r: -(r["score"] if r["score"] == r["score"] else -1))

def pct(x):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}"

def size(mb):
    if not mb: return "–"
    return f"{mb * 1000:.0f} KB" if mb < 1 else f"{mb:.0f} MB" if mb < 1000 else f"{mb / 1000:.1f} GB"

def table(rows):
    best = {k: (min if k == "leak" else max)((r[k] for r in rows if r[k] == r[k]), default=None) for k in ("score", "names", "ids", "leak")}
    b = lambda r, k: f"<b>{pct(r[k])}</b>" if r[k] == best[k] else pct(r[k])
    head = "<th>#</th><th class='l'>Model</th>" + "".join(f'<th title="{html.escape(t)}">{c}</th>' for c, t in COLUMNS.items())
    body = "".join(
        f"<tr><td>{i}</td><td class='l'><a href='{SYSTEMS[r['system']][1]}' target='_blank'>{html.escape(SYSTEMS[r['system']][0])}</a></td>"
        f"<td>{b(r, 'score')}</td><td>{b(r, 'names')}</td><td>{b(r, 'ids')}</td><td>{b(r, 'leak')}</td>"
        f"<td>{size(r.get('size_mb'))}</td><td>{'✓' if r.get('runs_in_browser') else ''}</td></tr>"
        for i, r in enumerate(rows, 1))
    return f"<table class='lb'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

ABOUT = """
**KVKK-Bench-TR** measures how well tools find personal data in Turkish text, so it can be masked before a document is shared,
for example with a cloud AI. Every tool gets the same documents and the same scorer.

**Test data (v0.1, public)**
* 566 Yargıtay sentences from [TurkishLegalNER](https://github.com/koc-lab/turkish-legal-ner). The anonymised names are refilled with synthetic names.
* 1,000 Turkish Wikipedia sentences with hand-marked names ([Turkish Wiki NER](https://huggingface.co/datasets/turkish-nlp-suite/turkish-wikiNER)).
* 80 generated legal documents with ID numbers, IBANs, phones and addresses. These are used for the IDs column only.

A hidden test of 2025–26 court decisions is in preparation and will replace the public score.

**Metrics.** *Score* is F2, averaged over the real-text tests. A value counts as found if the mask covers it, or at least half of it, with the right type.
*Leaked* is the share of personal-data characters left readable. Hover a column name for its definition.

**Links:** [dataset card](https://github.com/fikrifirat/katip/blob/legal-study/lab/legal/bench/README.md) ·
[scorer](https://github.com/fikrifirat/katip/blob/legal-study/lab/legal/bench_score.py) ·
[all results](https://github.com/fikrifirat/katip/tree/legal-study/lab/legal/bench/results) ·
[report a label error](https://github.com/fikrifirat/katip/issues/new/choose)

```
@misc{kvkkbenchtr2026, title={KVKK-Bench-TR: a benchmark for personal-data masking in Turkish documents},
  author={{Katip contributors}}, year={2026}, url={https://github.com/fikrifirat/katip}}
```
"""

CSS = """
.gradio-container{max-width:980px !important}
table.lb{width:100%;border-collapse:collapse;border:none !important;font-size:.95rem;font-variant-numeric:tabular-nums}
table.lb th,table.lb td{padding:8px 10px;border:none !important;border-bottom:1px solid var(--border-color-primary) !important;text-align:right;background:none !important}
table.lb th{font-weight:600;cursor:help} table.lb .l{text-align:left} table.lb td:first-child,table.lb th:first-child{text-align:left;width:28px}
table.lb a{text-decoration:none}
table.lb,table.lb tr,table.lb th,table.lb td{border-left:0 !important;border-right:0 !important;border-top:0 !important}
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

def build():
    rows = load_rows()
    with gr.Blocks(title="KVKK-Bench-TR", css=CSS, theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"# KVKK-Bench-TR\nPersonal-data masking for Turkish documents. Ranked by Score on real text. *{VERSION}*")
        with gr.Tabs():
            with gr.Tab("Leaderboard"):
                gr.HTML(table(rows))
            with gr.Tab("About"):
                gr.Markdown(ABOUT)
            with gr.Tab("Submit"):
                gr.Markdown("Enter a Hugging Face token-classification model. We evaluate it offline and add it to the table.")
                mid = gr.Textbox(label="Model id", placeholder="user/model")
                out = gr.Markdown()
                gr.Button("Submit").click(submit, mid, out)
    return demo

if __name__ == "__main__":
    build().launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
