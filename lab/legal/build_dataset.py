"""Turn raw crawled decisions into the legal-web dataset (lab/legal/DESIGN.md, sections 3.2-3.3).

  python lab/legal/build_dataset.py

Reads lab/data/legal_web/raw.jsonl and writes, under lab/data/legal_web/:
  train.jsonl, dev.jsonl, test.jsonl   slot-filled decisions: {"id", "court", "year", "text", "spans", "n_slots", "by_type"}
  aym_names.jsonl                      AYM judgments whose title names the applicant, NOT slot-filled:
                                       gold = every mention of that name (recall only: other names are unlabelled)
  manifest.json                        IDs per split, counts, SHA-256 of each test file
Splits: decisions sharing a court + esas number stay together; the group's latest year decides the split
(<= 2023 train, 2024 dev, >= 2025 test). Train fills use the train name pool, dev and test the disjoint one.
"""
from __future__ import annotations

import hashlib, json, random, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import katiplab as K  # noqa: E402,F401  (unpacks the name lists slotfill uses)
import slotfill as F  # noqa: E402

D = K.DATA / "legal_web"
MAX_CHARS = 6000  # long decisions are cut into windows at paragraph breaks

def split_of(year):
    if year is None: return None
    return "train" if year <= 2023 else "dev" if year == 2024 else "test"

def windows(text, n=MAX_CHARS):
    paras, cur, out = text.split("\n"), "", []
    for p in paras:
        if len(cur) + len(p) + 1 > n and cur: out.append(cur); cur = ""
        cur += (p + "\n")
    if cur.strip(): out.append(cur)
    return out

_TITLE_NAME = re.compile(r"^(.+?)\s+(?:VE\s+DİĞERLERİ\s+)?BAŞVURUSU", re.I)
_NOT_PERSON = re.compile(r"\b(A\.?Ş|LTD|ŞİRKET|DERNEĞ|VAKF|SENDİKA|PARTİ|BELEDİYE|KOOPERATİF|TİC|SAN\.|HOLDİNG|[A-ZÇĞİÖŞÜ]\.[A-ZÇĞİÖŞÜ]?\.?$)", re.I)
def aym_name(title: str | None) -> str | None:
    """'MEHMET HASAN ALTAN BAŞVURUSU [GK]' -> 'MEHMET HASAN ALTAN'; initials and companies -> None."""
    m = _TITLE_NAME.match((title or "").strip())
    if not m: return None
    name = m.group(1).strip()
    if _NOT_PERSON.search(name) or len(name.split()) < 2 or any(len(w.rstrip(".")) < 2 for w in name.split()): return None
    return name

def name_mentions(text, name):
    """Every mention of the full name, any casing, case suffix excluded."""
    words = [re.escape(F.lower_tr(w)) for w in name.split()]
    pat = re.compile(r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)")
    low = F.lower_tr(text)  # lower_tr keeps string length for Turkish letters
    assert len(low) == len(text)
    return [[m.start(), m.end(), "PERSON"] for m in pat.finditer(low)]

def main(seed: int = 0):
    raw = [json.loads(l) for l in (D / "raw.jsonl").open(encoding="utf-8")]
    seen, docs = set(), []
    for r in raw:  # exact-duplicate texts (same decision under two IDs) are dropped
        h = hashlib.sha1(re.sub(r"\s+", " ", r["text"]).encode()).hexdigest()
        if h in seen: continue
        seen.add(h); docs.append(r)
    groups = defaultdict(list)
    for r in docs: groups[(r["court"], r.get("esas_no") or r["id"])].append(r)
    split = {}
    for g, rs in groups.items():
        ys = [r["year"] for r in rs if r.get("year")]
        s = split_of(max(ys)) if ys else None
        for r in rs: split[(r["court"], r["id"])] = s
    pools = {"train": F.Pool("train"), "dev": F.Pool("test"), "test": F.Pool("test")}
    rng = random.Random(seed)
    out = {k: [] for k in ("train", "dev", "test")}
    aym = []
    for r in docs:
        s = split[(r["court"], r["id"])]
        if s is None: continue
        if r["court"] == "aym":
            name = aym_name(r.get("title"))
            if name and s != "train":
                spans = name_mentions(r["text"], name)
                if spans: aym.append({"id": f"aym-{r['id']}", "court": "aym", "year": r["year"], "text": r["text"],
                                      "spans": spans, "applicant": name}); continue
        named = aym_name(r.get("title")) if r["court"] == "aym" else None
        for i, w in enumerate(windows(r["text"])):
            f = F.fill(w, rng, pools[s])
            if named:  # train-split AYM judgment: label the published applicant name too
                f["spans"] = sorted(f["spans"] + name_mentions(f["text"], named))
            if not f["spans"]: continue
            out[s].append({"id": f"{r['court']}-{r['id']}-{i}", "court": r["court"], "year": r["year"], **f})
    manifest = {"seed": seed, "counts": {}, "by_type": {}, "sha256": {}}
    for s, rows in {**out, "aym_names": aym}.items():
        p = D / f"{s}.jsonl"
        with p.open("w", encoding="utf-8") as fh:
            for row in rows: fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        manifest["counts"][s] = {"docs": len(rows), "courts": dict(Counter(r["court"] for r in rows))}
        manifest["by_type"][s] = dict(sum((Counter(t for _, _, t in r["spans"]) for r in rows), Counter()))
        manifest["sha256"][s] = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest.setdefault("ids", {})[s] = sorted({r["id"] for r in rows})
    (D / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    print(json.dumps({k: manifest[k] for k in ("counts", "by_type")}, indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main()
