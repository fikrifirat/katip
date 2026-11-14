"""Blind comparison sheet: Katip Emsal vs. a plain keyword search, graded by a lawyer who can't tell which is which.

    python lab/emsal/blind.py make  OUTDIR      # OUTDIR from emsal.py: writes blind_sheet.csv + blind_key.json
    python lab/emsal/blind.py score OUTDIR      # after the lawyer fills blind_sheet.csv

Systems (fixed before any grading):
  baseline  the official search's own first 10 results for the petition's top three words: roughly what a
            lawyer gets typing those words into the search box
  emsal     Katip Emsal's list: up to 5 General Assembly decisions, then up to 10 chamber decisions
The sheet holds the union, shuffled with a fixed seed; every row shows the decision and its best-matching
paragraph, chosen the same way for both systems. blind_key.json says which system listed each row; don't
send it to the grader.

Grades: relevance 0 = not useful, 1 = partly, 2 = on point; would cite = yes / no.
Score: for each system, mean relevance of its list (precision with partial credit), share of its decisions
graded 2, nDCG@10 with the grades as gains, and how many the lawyer would cite.
"""
import csv, json, math, random, sys
from pathlib import Path

def make(out: Path, seed: int = 20261115):
    r = json.loads((out / "results.json").read_text(encoding="utf-8"))
    by_id = {x["id"]: x for x in r["all_ranked"]}
    emsal = [x["id"] for x in r["genel_kurul"] + r["chambers"]]
    base = [i for i in r.get("baseline_query1_ids", []) if i in by_id][:10]
    key = {}
    for sysname, ids in (("emsal", emsal), ("baseline", base)):
        for k, i in enumerate(ids, 1):
            key.setdefault(i, {})[sysname] = k
    rows = list(key)
    random.Random(seed).shuffle(rows)
    with (out / "blind_sheet.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["row", "decision", "link", "best matching paragraph",
                    "relevance (0 not useful, 1 partly, 2 on point)", "would you cite it? (yes/no)", "notes"])
        for n, i in enumerate(rows, 1):
            x = by_id[i]
            w.writerow([n, x["citation"], x["url"], x["quote"][:600], "", "", ""])
    (out / "blind_key.json").write_text(json.dumps({"seed": seed, "rows": rows, "key": key}, indent=1), encoding="utf-8")
    print(f"{len(rows)} decisions ({len(emsal)} from Emsal, {len(base)} from baseline, "
          f"{len(set(emsal) & set(base))} in both) -> {out / 'blind_sheet.csv'}")

def ndcg(gains: list[float], k: int = 10) -> float:
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains[:k]))
    ideal = sorted(gains, reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal[:k]))
    return dcg / idcg if idcg else 0.0

def score(out: Path):
    k = json.loads((out / "blind_key.json").read_text(encoding="utf-8"))
    grades, cite = {}, {}
    with (out / "blind_sheet.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            i = k["rows"][int(row["row"]) - 1]
            g = row["relevance (0 not useful, 1 partly, 2 on point)"].strip()
            if g:
                grades[i] = float(g)
            cite[i] = row["would you cite it? (yes/no)"].strip().lower() in ("yes", "evet", "y", "e")
    res = {}
    for sysname in ("emsal", "baseline"):
        ids = sorted((i for i, v in k["key"].items() if sysname in v), key=lambda i: k["key"][i][sysname])
        g = [grades.get(i, 0.0) for i in ids]
        res[sysname] = {"n": len(ids), "graded": sum(i in grades for i in ids), "mean_relevance": round(sum(g) / len(g), 2) if g else None,
                        "on_point": sum(x == 2 for x in g), "would_cite": sum(cite.get(i, False) for i in ids),
                        "ndcg@10": round(ndcg(g), 3)}
    (out / "blind_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))

if __name__ == "__main__":
    {"make": make, "score": score}[sys.argv[1]](Path(sys.argv[2]))
