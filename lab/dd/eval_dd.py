"""Evaluate Katip DD matching on the local MASAK snapshot.

    python lab/dd/eval_dd.py [--seed 7] [--n 400] [--out lab/dd/results/eval.json]

Labelled set, built from the snapshot with a fixed seed:

* Positives: listed records, split 50/50 into dev and test by record. For each, queries a
  person would plausibly type: the exact name, ASCII without Turkish letters, reversed word
  order, one middle name dropped, one typo, a transliteration variant (Mohammed/Muhammed,
  ou/u, w/v, kh/h, sh/ş), and one of the record's listed aliases.
  Correct = the right record is returned at or above a band.
* Decoys (near misses that should NOT be called a match): a listed person's first name(s)
  with a different common Turkish surname; common Turkish full names; ordinary Turkish
  company names; a listed company name with its distinctive word replaced. Each decoy is
  checked to be absent from the list after folding.

Thresholds are chosen on dev and reported on test. Only aggregate numbers are written:
the snapshot holds real people's data and no name from it goes into the results file.

Limits, stated plainly: the query variants are synthetic. Real users make other mistakes,
and real near-misses (a namesake with the same birth year) are harder than these decoys.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import match  # noqa: E402
from match import ListIndex  # noqa: E402
from normalize import fold, tokens  # noqa: E402
from store import Store  # noqa: E402

TR_FIRST = ["Mehmet", "Ahmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "İsmail", "Osman", "Yusuf",
            "Murat", "Ömer", "Ramazan", "Halil", "Süleyman", "Abdullah", "Mahmut", "Recep", "Fatma", "Ayşe",
            "Emine", "Hatice", "Zeynep", "Elif", "Meryem", "Şerife", "Zehra", "Sultan", "Hanife", "Merve",
            "Özlem", "Gülsüm", "Burak", "Emre", "Can", "Deniz", "Ece", "Selin", "Kerem", "Cem"]
TR_LAST = ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Yıldırım", "Öztürk", "Aydın", "Özdemir",
           "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek", "Polat",
           "Korkmaz", "Erdoğan", "Güneş", "Bulut", "Aksoy", "Uçar", "Tekin", "Ünal", "Kaplan", "Sarı",
           "Turan", "Karaca", "Eren", "Acar", "Bozkurt", "Ateş", "Bayram", "Keskin", "Uysal"]
CO_WORDS = ["Anadolu", "Marmara", "Ege", "Toros", "Kuzey", "Yıldız", "Doğuş", "Akdeniz", "Başkent", "Güven",
            "Atlas", "Mavi", "Kartal", "Lale", "Zirve", "Pınar", "Çınar", "Umut", "Ufuk", "Bereket"]
CO_SECT = ["İnşaat", "Gıda", "Tekstil", "Lojistik", "Enerji", "Turizm", "Otomotiv", "Yazılım", "Madencilik", "Tarım"]
CO_FORM = ["A.Ş.", "Ltd. Şti.", "Sanayi ve Ticaret A.Ş.", "San. ve Tic. Ltd. Şti."]

TRANSLIT = [("mohammed", "muhammed"), ("muhammad", "mohamed"), ("mohamed", "muhammed"), ("ou", "u"),
            ("w", "v"), ("kh", "h"), ("sh", "ş"), ("j", "c"), ("y", "i"), ("abdel", "abdul"), ("abdul", "abdel"),
            ("ahmed", "ahmet"), ("mahmoud", "mahmut"), ("ali", "aly"), ("hussein", "hüseyin"), ("osama", "usame")]


def ascii_tr(s: str) -> str:
    return s.translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"))


def typo(name: str, rnd: random.Random) -> str | None:
    words = name.split()
    idx = [i for i, w in enumerate(words) if len(w) >= 5]
    if not idx:
        return None
    i = rnd.choice(idx)
    w = words[i]
    p = rnd.randrange(1, len(w) - 1)
    op = rnd.choice(["sub", "del", "swap"])
    if op == "sub":
        w = w[:p] + rnd.choice("aeiklmnrst") + w[p + 1:]
    elif op == "del":
        w = w[:p] + w[p + 1:]
    else:
        w = w[:p] + w[p + 1] + w[p] + w[p + 2:]
    words[i] = w
    return " ".join(words)


def variants(rec: dict, rnd: random.Random) -> dict[str, str]:
    name = " ".join(rec["names"][0].split())
    out = {"exact": name, "ascii_lower": ascii_tr(name).lower()}  # ascii_tr maps İ->I first
    w = name.split()
    if len(w) >= 2:
        out["reordered"] = " ".join(w[-1:] + w[:-1])
    if len(w) >= 3:
        out["middle_dropped"] = " ".join([w[0]] + w[2:])
    t = typo(name, rnd)
    if t:
        out["typo"] = t
    low = name.translate(str.maketrans({"İ": "i", "I": "ı"})).lower()
    for a, b in TRANSLIT:
        if a in low:
            out["translit"] = low.replace(a, b, 1)
            break
    if len(rec["names"]) > 1:
        out["alias"] = rnd.choice(rec["names"][1:])
    return out


def decoys(records: list[dict], rnd: random.Random, n: int) -> list[tuple[str, str]]:
    listed = {fold(x) for r in records for x in r["names"]}
    listed_tok = {" ".join(sorted(tokens(x))) for r in records for x in r["names"]}
    out, tries = [], 0

    def ok(q):
        return fold(q) not in listed and " ".join(sorted(tokens(q))) not in listed_tok

    persons = [r for r in records if r["kind"] == "person" and len(r["names"][0].split()) >= 2]
    while len(out) < n and tries < n * 50:
        tries += 1
        kind = rnd.choice(["same_first_other_surname", "common_tr_name", "tr_company", "company_word_swapped"])
        if kind == "same_first_other_surname" and persons:
            r = rnd.choice(persons)
            first = " ".join(r["names"][0].split()[:-1])
            q = f"{first} {rnd.choice(TR_LAST)}"
        elif kind == "common_tr_name":
            q = f"{rnd.choice(TR_FIRST)} {rnd.choice(TR_LAST)}"
        elif kind == "tr_company":
            q = f"{rnd.choice(CO_WORDS)} {rnd.choice(CO_SECT)} {rnd.choice(CO_FORM)}"
        else:
            orgs = [r for r in records if r["kind"] != "person" and len(tokens(r["names"][0])) >= 2]
            if not orgs:
                continue
            ws = rnd.choice(orgs)["names"][0].split()
            ws[0] = rnd.choice(CO_WORDS)
            q = " ".join(ws)
        if ok(q):
            out.append((kind, q))
    return out


def evaluate(idx: ListIndex, pos: list[tuple[str, str, str]], neg: list[tuple[str, str]]):
    """Return raw scores so thresholds can be swept without re-searching."""
    P = []
    for rid, kind, q in pos:
        hits = idx.search(q, limit=10, floor=0.5)
        s = next((h.score for h in hits if h.record["rid"] == rid), 0.0)
        top1 = bool(hits) and hits[0].record["rid"] == rid
        P.append({"kind": kind, "score": s, "top1": top1})
    N = []
    for kind, q in neg:
        hits = idx.search(q, limit=1, floor=0.5)
        N.append({"kind": kind, "score": hits[0].score if hits else 0.0})
    return P, N


def rates(P, N, match_t, review_t):
    def frac(xs, f):
        return round(sum(1 for x in xs if f(x)) / len(xs), 4) if xs else None
    by = {}
    for k in sorted({p["kind"] for p in P}):
        sub = [p for p in P if p["kind"] == k]
        by[k] = {"n": len(sub), "recall_match": frac(sub, lambda p: p["score"] >= match_t),
                 "recall_review": frac(sub, lambda p: p["score"] >= review_t), "top1": frac(sub, lambda p: p["top1"])}
    nb = {}
    for k in sorted({x["kind"] for x in N}):
        sub = [x for x in N if x["kind"] == k]
        nb[k] = {"n": len(sub), "false_match": frac(sub, lambda x: x["score"] >= match_t),
                 "flagged_review": frac(sub, lambda x: x["score"] >= review_t)}
    tp_m = sum(1 for p in P if p["score"] >= match_t)
    fp_m = sum(1 for x in N if x["score"] >= match_t)
    tp_r = sum(1 for p in P if p["score"] >= review_t)
    fp_r = sum(1 for x in N if x["score"] >= review_t)
    return {
        "positives": len(P), "decoys": len(N),
        "recall_match": frac(P, lambda p: p["score"] >= match_t),
        "recall_review": frac(P, lambda p: p["score"] >= review_t),
        "top1": frac(P, lambda p: p["top1"]),
        "decoy_false_match_rate": frac(N, lambda x: x["score"] >= match_t),
        "decoy_flag_rate_review": frac(N, lambda x: x["score"] >= review_t),
        "precision_match_on_this_mix": round(tp_m / (tp_m + fp_m), 4) if tp_m + fp_m else None,
        "precision_review_on_this_mix": round(tp_r / (tp_r + fp_r), 4) if tp_r + fp_r else None,
        "by_query_kind": by, "by_decoy_kind": nb,
    }


def pick_thresholds(P, N):
    """On dev: MATCH = lowest threshold with no decoy above it, REVIEW = the highest
    threshold that still catches >= 99% of positives (recall first, for screening)."""
    neg_max = max((x["score"] for x in N), default=0)
    grid = [round(0.80 + i * 0.005, 3) for i in range(41)]
    match_t = next((t for t in grid if t > neg_max), 1.0)
    review_t = max((t for t in grid if sum(p["score"] >= t for p in P) / len(P) >= 0.99), default=0.80)
    return min(match_t, 1.0), min(review_t, match_t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n", type=int, default=400, help="records sampled for positives")
    ap.add_argument("--decoys", type=int, default=800)
    ap.add_argument("--out", default=str(Path(__file__).with_name("results") / "eval.json"))
    a = ap.parse_args()
    st = Store()
    records = st.records("masak")
    if not records:
        sys.exit("no MASAK snapshot; run `dd.py update --source masak` first")
    rnd = random.Random(a.seed)
    idx = ListIndex(records)
    sample = rnd.sample(records, min(a.n, len(records)))
    half = len(sample) // 2
    split = {"dev": sample[:half], "test": sample[half:]}
    negs = decoys(records, rnd, a.decoys)
    neg_split = {"dev": negs[: len(negs) // 2], "test": negs[len(negs) // 2:]}
    raw = {}
    for name, recs in split.items():
        pos = [(r["rid"], k, q) for r in recs for k, q in variants(r, rnd).items()]
        raw[name] = evaluate(idx, pos, neg_split[name])
    match_t, review_t = pick_thresholds(*raw["dev"])
    res = {
        "snapshot": {"records": len(records), "fetched": (st.last_ok("masak") or {}).get("finished"),
                     "lists": sorted({r["list"] for r in records})},
        "seed": a.seed,
        "shipped_thresholds": {"match": match.MATCH, "review": match.REVIEW},
        "dev_chosen_thresholds": {"match": match_t, "review": review_t},
        "test_at_shipped": rates(*raw["test"], match.MATCH, match.REVIEW),
        "test_at_dev_chosen": rates(*raw["test"], match_t, review_t),
        "dev_at_shipped": rates(*raw["dev"], match.MATCH, match.REVIEW),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    t = res["test_at_shipped"]
    print(f"test @ shipped (match {match.MATCH}, review {match.REVIEW}): recall match {t['recall_match']}, "
          f"recall review {t['recall_review']}, top1 {t['top1']}, decoy false match {t['decoy_false_match_rate']}, "
          f"decoy flagged {t['decoy_flag_rate_review']}")
    print("dev-chosen:", res["dev_chosen_thresholds"])
    print(json.dumps({k: v for k, v in t.items() if k.startswith("by_")}, indent=1))


if __name__ == "__main__":
    main()
