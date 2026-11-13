"""Fetch Turkish first names and surnames that Katip has never seen, for the 🇹🇷 court-names test.

  python lab/legal/bench/fresh_names.py        # needs internet (QLever Wikidata endpoint); writes bench/names/tr_fresh.json

Source: Wikidata (CC0), given names (P735) and family names (P734) of Turkish citizens (P27 = Q43).
A name is kept only if no word of it appears in Katip's name lexicons, in any synthetic training/dev set, or in
Turkish Wiki NER train: so a model can't score by remembering it. The rest of the bench is unchanged.
"""
from __future__ import annotations
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent)]
import katiplab as K  # noqa: E402
from katip_redact.textutil import fold  # noqa: E402

ENDPOINT = "https://qlever.cs.uni-freiburg.de/api/wikidata"   # QLever's Wikidata mirror: query.wikidata.org times out (504) on this aggregate
Q = """PREFIX wd: <http://www.wikidata.org/entity/> PREFIX wdt: <http://www.wikidata.org/prop/direct/> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?l (COUNT(?p) AS ?n) WHERE {{ ?p wdt:P27 wd:Q43; wdt:P31 wd:Q5; wdt:{prop} ?x. ?x rdfs:label ?l. FILTER(LANG(?l) = "tr") }}
GROUP BY ?l HAVING (COUNT(?p) >= 2) ORDER BY DESC(?n) LIMIT 6000"""
WORD = re.compile(r"[A-ZÇĞİÖŞÜ][a-zçğıöşüâîû]{2,}")

def fetch(prop):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": Q.format(prop=prop)})
    req = urllib.request.Request(url, headers={"User-Agent": "kvkk-bench/0.1 (benchmark builder)", "Accept": "application/sparql-results+json"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as f: return [(b["l"]["value"], int(b["n"]["value"])) for b in json.load(f)["results"]["bindings"]]
        except Exception as e: print("retry", e); time.sleep(10 * (i + 1))
    raise SystemExit("Wikidata unreachable")

def seen():
    out = set(K._FIRST) | set(K._LAST)
    docs = [d for n in ("train", "dev", "extra_synth", "heldout", "blind") for d in K.load_synth(n)] + K.load_wiki("train")
    for d in docs:
        for a, b, t in d["spans"]:
            if t == "PERSON": out |= {fold(w.strip(".,'’\"")) for w in d["text"][a:b].split()}
    return out

if __name__ == "__main__":
    S = seen(); res = {}
    for key, prop in (("first", "P735"), ("last", "P734")):
        names = [(l, n) for l, n in fetch(prop) if WORD.fullmatch(l) and fold(l) not in S]
        res[key] = [l for l, _ in names]
        print(key, len(res[key]), res[key][:25])
    res["source"] = f"Wikidata (CC0) via {ENDPOINT}: labels of P735/P734 of Turkish citizens, minus every word Katip's lexicons or training sets contain"
    (HERE / "names").mkdir(exist_ok=True)
    (HERE / "names" / "tr_fresh.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
