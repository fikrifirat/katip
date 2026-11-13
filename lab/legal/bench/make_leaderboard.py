"""Build the static leaderboard page from results/*.json:  python lab/legal/bench/make_leaderboard.py
Writes leaderboard.html (self-contained, no external requests) and LEADERBOARD_TABLE.md."""
import html, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
import sys; sys.path.insert(0, str(HERE.parent))
from bench_score import REAL_TRACKS
rows = [json.loads(p.read_text()) for p in sorted((HERE / "results").glob("*.json"))]
for r in rows:  # recompute the ranking from track scores, so rows made by older scorer versions rank the same way
    f = lambda keep: [x["f2"] for t, x in r["tracks"].items() if keep(t) and x["f2"] == x["f2"]]
    real, gen = f(lambda t: t in REAL_TRACKS), f(lambda t: t not in REAL_TRACKS)
    r["KVKK-F2"] = sum(real) / len(real) if real else float("nan"); r["F2 generated"] = sum(gen) / len(gen) if gen else float("nan")
pub = sorted([r for r in rows if r.get("split") == "public"], key=lambda r: -r["KVKK-F2"])
hid = sorted([r for r in rows if r.get("split") == "hidden"], key=lambda r: -r["KVKK-F2"])
BASELINES = {"presidio": "reference baseline", "kvkk-pii": "floor baseline"}
def mparams(r):
    p = r.get("params")
    return "" if p is None else ("0 (rules)" if p == 0 else f"{p / 1e6:.1f}M")
def speed(r): return f"{int(r['words_per_s']):,}" if r.get("words_per_s") else ""
def label(r): return r["name"] + (f" ({BASELINES[r['system']]})" if r.get("system") in BASELINES else "")
TR = ["court", "court-real", "court-filled", "prose", "petition", "contract", "correspondence", "health", "court-generated"]
def pct(x): return "" if x is None or x != x else f"{100 * x:.1f}"
def table_md(rs):
    tracks = [t for t in TR if any(t in r["tracks"] for r in rs)]
    out = ["| # | System | Params | Size MB | Words/s (CPU) | ms/page | Browser | KVKK-F2 (real text) | generated (check) | Leak % | " + " | ".join(tracks) + " |", "| --- " * (10 + len(tracks)) + "|"]
    for i, r in enumerate(rs, 1):
        out.append(f"| {i} | {label(r)} | {mparams(r)} | {r.get('size_mb') or ''} | {speed(r)} | {r.get('ms_per_page', '') or ''} | {'yes' if r.get('runs_in_browser') else 'no'} | **{pct(r['KVKK-F2'])}** | {pct(r.get('F2 generated'))} | {pct(r['leak_rate'])} | " +
                   " | ".join(pct(r["tracks"].get(t, {}).get("f2")) for t in tracks) + " |")
    return "\n".join(out)
machine = next((r["machine"] for r in rows if r.get("machine")), "")
md = "# KVKK-Bench-TR leaderboard (v0.1)\n\nBaselines: **Presidio + spaCy** (the standard open-source PII tool, reference baseline) and the **kvkk-pii** regex library (floor). Speed: words per second and ms per 500-word page on one CPU core-set (" + machine + "), same machine for every row; size is what you download to run it.\n\nTrack cells are F2 (%). KVKK-F2 = mean F2 over real-text tracks (the ranking). Generated tracks are a regression check: Katip's models were trained on the same generator. Leak = share of personal-data characters left readable.\n\n"
if hid: md += "## Hidden test (ranked)\n\n" + table_md(hid) + "\n\n"
md += "## Public split (self-reported, for development)\n\n" + table_md(pub) + "\n"
(HERE / "LEADERBOARD_TABLE.md").write_text(md)
def table_html(rs, title):
    tracks = [t for t in TR if any(t in r["tracks"] for r in rs)]
    h = f"<h2>{title}</h2><div class=scroll><table><thead><tr><th>#</th><th>System</th><th>Params</th><th>Size MB</th><th>Words/s (CPU)</th><th>ms/page</th><th>Browser</th><th>KVKK-F2 (real text)</th><th>generated (check)</th><th>Leak %</th>" + "".join(f"<th>{t}</th>" for t in tracks) + "</tr></thead><tbody>"
    for i, r in enumerate(rs, 1):
        h += (f"<tr><td>{i}</td><td>{html.escape(label(r))}</td><td>{mparams(r)}</td><td>{r.get('size_mb') or ''}</td><td>{speed(r)}</td><td>{r.get('ms_per_page', '') or ''}</td><td>{'yes' if r.get('runs_in_browser') else 'no'}</td><td class=main>{pct(r['KVKK-F2'])}</td><td>{pct(r.get('F2 generated'))}</td><td>{pct(r['leak_rate'])}</td>" +
              "".join(f"<td>{pct(r['tracks'].get(t, {}).get('f2'))}</td>" for t in tracks) + "</tr>")
    return h + "</tbody></table></div>"
body = (table_html(hid, "Hidden test (ranked)") if hid else "<p class=note>Hidden test: being built from 2025–26 court decisions.</p>") + table_html(pub, "Public split (self-reported, for development)")
page = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>KVKK-Bench-TR</title>
<style>:root{{--bg:#fcfcfb;--fg:#0b0b0b;--mut:#52514e;--line:#e6e5e0;--acc:#2a78d6}}@media (prefers-color-scheme:dark){{:root{{--bg:#1a1a19;--fg:#f0efec;--mut:#c3c2b7;--line:#33322f;--acc:#3987e5}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:24px 16px}}h1{{margin:0 0 4px}}p{{color:var(--mut)}}
.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{padding:6px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
th:nth-child(2),td:nth-child(2){{text-align:left}}th{{color:var(--mut);font-weight:600}}td.main{{font-weight:700;color:var(--acc)}}.note{{font-style:italic}}</style></head><body>
<h1>KVKK-Bench-TR</h1><p>Finding and masking personal data in Turkish documents (KVKK). Track cells are F2, recall weighted 4×. KVKK-F2, the ranking, is the mean over real-text tracks; generated documents are a regression check only, since Katip trains on the same generator. Leak is the share of personal-data characters left readable. Baselines: Presidio + spaCy (the standard open-source PII tool, reference baseline) and the kvkk-pii regex library (floor). Speed is measured on the same CPU machine for every row; size is what you download to run it. Version v0.1. Dataset card, scorer and how to submit: github.com/fikrifirat/katip (lab/legal/bench).</p>
{body}</body></html>"""
(HERE / "leaderboard.html").write_text(page)
print(md)
