"""How often does Katip Cite catch a wrong statute citation, and how often does it cry wolf?

Builds a labelled set of citations from the index itself, writes each into a sentence in the forms
lawyers and models use, and checks what the checker says:

  OK                 an article that exists and is in force
  NO_SUCH_ARTICLE    an article number past the law's last article
  ARTICLE_REPEALED   an article the official text marks Mülga
  LAW_REPEALED       an article of a repealed law (e.g. 818 BK, 1086 HUMK)
  UNKNOWN_LAW        a law number no Turkish law has
  NUMBER_NAME_CLASH  one law's number with another law's name

Forms: "6098 sayılı Kanun'un 344. maddesi", "<official title> m. 344", "TBK m. 344", "Article 344 of Law No. 6098".

What this measures and what it doesn't: the labels come from the same index the checker reads, so this tests finding
the citation and the decision logic, not whether the index matches the official text (make_questions.py read 80
articles by hand for that, and review/audit.csv audits real model answers). Real answers have messier wording than
these templates; the audit is the check on that.

Run:  python lab/cite/catch_rate.py [--checker path/to/katip_cite.py] [--seed 7] [--out results/catch_rate.json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
WRONG = ("NO_SUCH_ARTICLE", "ARTICLE_REPEALED", "LAW_REPEALED", "UNKNOWN_LAW", "NUMBER_NAME_CLASH")
N = {"OK": 300, "NO_SUCH_ARTICLE": 150, "ARTICLE_REPEALED": 150, "LAW_REPEALED": 150, "UNKNOWN_LAW": 100,
     "NUMBER_NAME_CLASH": 80}


def load(path: Path):
    spec = importlib.util.spec_from_file_location("katip_cite_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def build(kc, ck, rng: random.Random) -> list[dict]:
    """Labelled cases. Only laws whose number names one law (no duplicates, no decree-laws) are used, so the label
    is unambiguous."""
    single = {}
    for slug, l in ck.laws.items():
        if "KARARNAME" in l["title"] or l["removed_provisions_file"]:
            continue
        if len([s for s in ck.by_no.get(l["no"], []) if not ck.laws[s]["removed_provisions_file"]]) == 1:
            single[slug] = l
    abbr = defaultdict(list)                       # law no -> short aliases (TBK, İİK...)
    for no, names in kc.ALIASES.items():
        abbr[no] += [n for n in names if len(n) <= 6 and n.isupper()]

    def arts(l, status):
        return [k for k, a in l["arts"]["madde"].items() if k.isdigit() and a["s"] == status]

    def forms(l, n, allow_title=True):
        no = l["no"]
        other = rng.randint(1, max(1, int(n) - 1)) if int(n) > 1 else 2
        out = [("tr_number", f"{no} sayılı Kanun'un {n}. maddesi"),
               ("tr_number_messy", rng.choice([f"{no} sayılı Kanunun {n} inci maddesi", f"{no} s. Kanun md. {n}/1",
                                               f"{no} sayılı Kanun m. {n}/2-a"])),
               ("en_number", f"Article {n} of Law No. {no}"),
               ("en_number_messy", rng.choice([f"Art. {n} of Law No. {no}", f"Law No. {no}, Article {n}"]))]
        if allow_title and ck.alias.get(kc.norm(l["title"])) == no:
            out.append(("tr_title", f"{kc.tr_title(l['title'])} m. {n}"))
        for a in abbr.get(no, [])[:1]:
            out.append(("abbreviation", f"{a} m. {n}"))
            out.append(("abbreviation_messy", rng.choice([f"{a}'nın {n}. maddesi", f"{a} md. {n}/1", f"{a} {n}",
                                                          f"{a} m. {other}, {n}" if other != int(n) else f"{a} m. {n}"])))
        return out

    in_force = [l for l in single.values() if l["status"] == "in_force" and arts(l, "in_force")]
    repealed_laws = [l for l in single.values() if l["status"] != "in_force" and l["arts"]["madde"]]
    with_mulga = [l for l in in_force if arts(l, "repealed")]
    cases = []

    def add(label, l_or_none, n, form, text):
        cases.append({"label": label, "law": l_or_none["no"] if l_or_none else None, "article": str(n),
                      "form": form, "citation": text})

    # core codes are what lawyers cite most: half of the OK and Mülga cases come from laws with an abbreviation
    core = [l for l in in_force if abbr.get(l["no"])]
    for i in range(N["OK"]):
        l = rng.choice(core if i % 2 else in_force)
        n = rng.choice(arts(l, "in_force"))
        add("OK", l, n, *rng.choice(forms(l, n)))
    for _ in range(N["NO_SUCH_ARTICLE"]):
        l = rng.choice(in_force)
        n = max(int(k) for k in l["arts"]["madde"] if k.isdigit()) + rng.randint(1, 40)
        add("NO_SUCH_ARTICLE", l, n, *rng.choice(forms(l, n)))
    core_mulga = [l for l in with_mulga if abbr.get(l["no"])]
    for i in range(N["ARTICLE_REPEALED"]):
        l = rng.choice(core_mulga if i % 2 and core_mulga else with_mulga)
        n = rng.choice(arts(l, "repealed"))
        add("ARTICLE_REPEALED", l, n, *rng.choice(forms(l, n)))
    for _ in range(N["LAW_REPEALED"]):
        l = rng.choice(repealed_laws)
        n = rng.choice([k for k in l["arts"]["madde"] if k.isdigit()])
        # a repealed law's title is often reused by its successor, so cite it by number or by its own abbreviation
        add("LAW_REPEALED", l, n, *rng.choice(forms(l, n, allow_title=False)))
    unused = [n for n in range(1000, 7600) if str(n) not in ck.by_no]
    for _ in range(N["UNKNOWN_LAW"]):
        no, n = rng.choice(unused), rng.randint(1, 120)
        form, text = rng.choice([("tr_number", f"{no} sayılı Kanun'un {n}. maddesi"),
                                 ("en_number", f"Article {n} of Law No. {no}")])
        cases.append({"label": "UNKNOWN_LAW", "law": str(no), "article": str(n), "form": form, "citation": text})
    named = [l for l in in_force if ck.alias.get(kc.norm(l["title"])) == l["no"]]
    for _ in range(N["NUMBER_NAME_CLASH"]):
        a, b = rng.sample(named, 2)
        while kc.PREDECESSOR.get(a["no"]) == b["no"] or kc.PREDECESSOR.get(b["no"]) == a["no"]:
            a, b = rng.sample(named, 2)
        n = rng.choice(arts(b, "in_force"))
        cases.append({"label": "NUMBER_NAME_CLASH", "law": a["no"], "article": str(n), "form": "tr_number+title",
                      "citation": f"{a['no']} sayılı {kc.tr_title(b['title'])}'nun {n}. maddesi"})
    for c in cases:
        c["text"] = (f"This is governed by {c['citation']}." if c["form"].startswith("en")
                     else f"Bu konuda {c['citation']} uygulanır.")
    return cases


def run(ck, cases: list[dict]) -> list[dict]:
    for c in cases:
        found = [x for x in ck.extract(c["text"]) if x.kind == "statute"]
        hit = next((x for x in found if (x.article or "").split("/")[0].split()[-1] == c["article"]), None)
        c["found"] = hit is not None
        c["verdict"] = hit.verdict if hit else "NOT_FOUND"
    return cases


def summarise(cases: list[dict]) -> dict:
    by = defaultdict(list)
    for c in cases:
        by[c["label"]].append(c)
    out = {}
    for label, cs in by.items():
        n = len(cs)
        row = {"n": n, "found %": round(100 * sum(c["found"] for c in cs) / n, 1),
               "verdicts": dict(Counter(c["verdict"] for c in cs).most_common())}
        if label == "OK":
            row["false alarm %"] = round(100 * sum(c["verdict"] in WRONG for c in cs) / n, 1)
            row["unverified %"] = round(100 * sum(c["verdict"] == "UNVERIFIED" for c in cs) / n, 1)
        else:
            row["flagged as wrong %"] = round(100 * sum(c["verdict"] in WRONG for c in cs) / n, 1)
            row["exact reason %"] = round(100 * sum(c["verdict"] == label for c in cs) / n, 1)
        forms = defaultdict(list)
        for c in cs:
            forms[c["form"]].append(c["verdict"] == label)
        row["exact by form %"] = {f: round(100 * sum(v) / len(v), 1) for f, v in sorted(forms.items())}
        out[label] = row
    wrong = [c for c in cases if c["label"] != "OK"]
    out["ALL WRONG"] = {"n": len(wrong), "flagged as wrong %": round(100 * sum(c["verdict"] in WRONG for c in wrong)
                                                                     / len(wrong), 1)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--checker", type=Path, default=HERE / "katip_cite.py")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=HERE / "results" / "catch_rate.json")
    a = ap.parse_args()
    kc = load(a.checker)
    ck = kc.default_checker() if hasattr(kc, "default_checker") else kc.Checker()
    cases = run(ck, build(kc, ck, random.Random(a.seed)))
    summary = summarise(cases)
    misses = [c for c in cases if c["verdict"] != c["label"]]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"seed": a.seed, "checker": a.checker.name, "index": ck.meta, "summary": summary,
                                 "misses": misses}, ensure_ascii=False, indent=1), encoding="utf-8")
    for label, row in summary.items():
        print(label, json.dumps({k: v for k, v in row.items() if k != "verdicts"}, ensure_ascii=False))
    print(f"{len(misses)} of {len(cases)} cases got another verdict than their label; see {a.out}")


if __name__ == "__main__":
    main()
