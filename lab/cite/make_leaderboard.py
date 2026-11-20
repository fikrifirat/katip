"""Build the Cite-Bench-TR leaderboard from results/*.json:  python lab/cite/make_leaderboard.py
Writes LEADERBOARD.md and leaderboard.html (self-contained: no fonts, scripts or requests from outside)."""
import html, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AREAS = {"is": "Labour", "kira": "Rent", "aile": "Family", "miras": "Inheritance", "icra": "Enforcement", "ceza": "Criminal",
         "usul": "Procedure & deadlines", "kvkk": "KVKK", "yabanci": "Foreigners", "tuketici": "Consumer & property"}


def pct(x, d=0):
    return "" if x is None or x != x else f"{100 * x:.{d}f}"


def load():
    rows = [json.loads(p.read_text()) for p in sorted((HERE / "results").glob("*.json"))]
    models = sorted([r for r in rows if not r["system"].startswith("ref-")], key=lambda r: -r["all"]["safe"])
    refs = [r for r in rows if r["system"].startswith("ref-")]
    return models, refs


def cells(r):
    a, L = r["all"], r["by_lang"]
    g = r["lang_gap"]
    return {
        "Model": r["name"], "Local": "yes" if r["runs_locally"] else "API",
        "Safe answers %": f"{pct(a['safe'])} [{pct(a['safe_ci'][0])}–{pct(a['safe_ci'][1])}]",
        "Right article %": pct(a["right_article"]), "Key fact %": pct(a["key_fact"]),
        "Wrong citations %": pct(a["wrong_rate"], 1), "Answers with a wrong citation %": pct(a["answers_with_wrong"]),
        "Stale rule": str(a["stale"]), "TR safe %": pct(L.get("tr", {}).get("safe")), "EN safe %": pct(L.get("en", {}).get("safe")),
        "TR−EN (p)": "" if g["tr_minus_en"] is None else f"{100 * g['tr_minus_en']:+.0f} ({g['mcnemar_p']:.2f})",
        "High-risk safe %": pct(r["by_risk"].get("high", {}).get("safe")),
        "Case-law cites / answer": f"{a['decision_citations_per_answer']:.2f}", "s / answer": f"{a['seconds_per_answer']:.1f}",
    }


def md(models, refs):
    cols = list(cells(models[0] if models else refs[0]).keys())
    out = ["# Cite-Bench-TR leaderboard (v0.1, draft questions)", "",
           "Each model answers 63 Turkish legal questions in Turkish and in English (126 answers). Katip Cite checks every statute "
           "citation against the official law text (offline index, snapshot in each results file). **Safe answer** = no wrong "
           "citation + cites an article a lawyer would expect + states the key fact where there is one. 95% bootstrap CIs; TR−EN is "
           "the paired difference with an exact McNemar p. Questions are Claude-drafted and await lawyer review.", "",
           "| # | " + " | ".join(cols) + " |", "|" + " --- |" * (len(cols) + 1)]
    for i, r in enumerate(models, 1):
        out.append(f"| {i} | " + " | ".join(cells(r).values()) + " |")
    for r in refs:
        out.append("| ref | " + " | ".join(cells(r).values()) + " |")
    out += ["", "## Safe answers by risk area (%)", "", "| Model | " + " | ".join(AREAS.values()) + " |", "|" + " --- |" * (len(AREAS) + 1)]
    for r in models:
        out.append(f"| {r['name']} | " + " | ".join(pct(r["by_area"].get(k, {}).get("safe")) for k in AREAS) + " |")
    return "\n".join(out) + "\n"


CSS = """:root{--bg:#fbfbf8;--fg:#16181a;--mut:#5d6166;--line:#e3e3dc;--acc:#b8e11a;--bad:#c0392b;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#121314;--fg:#ececea;--mut:#a0a4a8;--line:#2b2d30;--acc:#c6f135;--bad:#ff7a6b;--card:#1a1b1d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Inter,Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 60px}h1{font-size:26px;margin:0 0 6px}h2{font-size:18px;margin:34px 0 10px}
p{color:var(--mut);max-width:820px}.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}th{font-size:12px;color:var(--mut);font-weight:600}td.main{font-weight:700}
tr.ref td{color:var(--mut);font-style:italic}.k{display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--acc);margin-right:6px}
td.heat{color:#111}code{font-size:13px}"""


def heat(x):
    if x is None or x != x:
        return "<td></td>"
    h = int(x * 110)  # 0 red -> 110 green
    return f'<td class=heat style="background:hsl({h},70%,{62 if x < .5 else 58}%)">{pct(x)}</td>'


def page(models, refs):
    cols = list(cells(models[0] if models else refs[0]).keys())
    t = "<div class=scroll><table><thead><tr><th>#</th>" + "".join(f"<th>{html.escape(c)}</th>" for c in cols) + "</tr></thead><tbody>"
    for i, r in enumerate(models, 1):
        c = cells(r)
        t += f"<tr><td>{i}</td>" + "".join(f"<td{' class=main' if k.startswith('Safe') else ''}>{html.escape(v)}</td>" for k, v in c.items()) + "</tr>"
    for r in refs:
        t += "<tr class=ref><td>ref</td>" + "".join(f"<td>{html.escape(v)}</td>" for v in cells(r).values()) + "</tr>"
    t += "</tbody></table></div>"
    h = "<div class=scroll><table><thead><tr><th>Model</th>" + "".join(f"<th>{html.escape(v)}</th>" for v in AREAS.values()) + "</tr></thead><tbody>"
    for r in models + refs:
        h += f"<tr><td>{html.escape(r['name'])}</td>" + "".join(heat(r["by_area"].get(k, {}).get("safe")) for k in AREAS) + "</tr>"
    h += "</tbody></table></div>"
    ex = ""
    for r in models[:6]:
        for w in r["wrong_examples"][:4]:
            ex += f"<tr><td>{html.escape(r['name'])}</td><td>{w['id']} · {w['lang']}</td><td><code>{html.escape(w['text'][:70])}</code></td><td>{w['verdict']}</td><td>{html.escape(w['note'][:80])}</td></tr>"
    exs = ("<h2>Examples of wrong citations</h2><div class=scroll><table><thead><tr><th>Model</th><th>Question</th><th>Citation</th>"
           "<th>Verdict</th><th>Why</th></tr></thead><tbody>" + ex + "</tbody></table></div>") if ex else ""
    snap = (models + refs)[0]["index"] if models + refs else {}
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Cite-Bench-TR</title><style>{CSS}</style></head><body><main>
<h1><span class=k></span>Cite-Bench-TR: do AI models cite Turkish law correctly?</h1>
<p>63 questions in 10 risk areas, each asked in Turkish and in English (for foreign clients and expats). Every statute citation in
every answer is checked by <b>Katip Cite</b> against the official law text, offline, on a laptop. <b>Safe answer</b> = no wrong
citation, cites an article a lawyer would expect, and states the key fact (a deadline, a share, a threshold) where the question has one.
Brackets are 95% bootstrap intervals. Questions are drafts until a lawyer has reviewed them.</p>
{t}<h2>Safe answers by risk area (%)</h2>{h}{exs}
<p>Statute snapshot: {html.escape(str(snap.get('source')))} @ {html.escape(str(snap.get('commit'))[:10])} ({html.escape(str(snap.get('commit_date')))}).
Case-law citations (Yargıtay, Danıştay, AYM) are counted but not yet verified. Code: github.com/fikrifirat/katip, <code>lab/cite/</code>.</p>
</main></body></html>"""


if __name__ == "__main__":
    models, refs = load()
    (HERE / "LEADERBOARD.md").write_text(md(models, refs))
    (HERE / "leaderboard.html").write_text(page(models, refs))
    print(f"{len(models)} models + {len(refs)} reference rows -> LEADERBOARD.md, leaderboard.html")
