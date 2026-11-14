"""Training mixes with foreign clients in them. Only train-split name families are used (names.split()["train"]).

  swap_foreign(doc, rng, pool) -> doc with every PERSON in it renamed to one foreign person per original person
                                  (consistent inside the document: "Ayşe YILMAZ" ... "davalı Yılmaz" -> "Nino
                                  BERİDZE" ... "davalı Beridze"), case suffixes re-inflected to agree with the new
                                  name, and each TCKN replaced by a YKN (or, sometimes, a passport number with its cue)
  foreign_mix(seed, share) -> list of training docs: Katip's synthetic train set with `share` of documents swapped,
                              + TLNER train-split court sentences filled with foreign names, + generated petitions
"""
from __future__ import annotations

import random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import katiplab as K  # noqa: E402
import suffix as S  # noqa: E402
import names as N  # noqa: E402
import ids as I  # noqa: E402
import build as B  # noqa: E402

def _case_like(new: str, old: str) -> str:
    if old.isupper(): return N.upper_tr(new)
    return new

def swap_foreign(doc, rng, pool):
    text, spans = doc["text"], sorted(doc["spans"])
    persons = sorted({text[a:b] for a, b, t in spans if t == "PERSON"}, key=len, reverse=True)
    tokmap = {}                                    # folded original word -> new word
    for p in persons:
        ow = p.split()
        if all(K.fold(w) in tokmap for w in ow): continue
        if rng.random() < .4:                      # keep some people Turkish (judges, lawyers, the other side)
            for w in ow: tokmap.setdefault(K.fold(w), w)
            continue
        g = B.pick_group(rng); nw = N.sample_parts(rng, pool[g], g)
        firsts, last = nw[:-1], nw[-1]
        for i, w in enumerate(ow):
            if K.fold(w) in tokmap: continue
            tokmap[K.fold(w)] = last if i == len(ow) - 1 and len(ow) > 1 else (firsts[min(i, len(firsts) - 1)] if len(ow) > 1 else rng.choice([last, firsts[0]]))
    out, new_spans, pos = "", [], 0
    for a, b, t in spans:
        if a < pos: continue
        out += text[pos:a]
        val = text[a:b]
        if t == "PERSON":
            val = " ".join(_case_like(tokmap.get(K.fold(w), w), w) for w in val.split())
        elif t == "TCKN":
            if rng.random() < .8: val = I.ykn(rng); t = "YKN"
        na = len(out); out += val; new_spans.append([na, len(out), t]); pos = b
        if t == "PERSON":                          # "Yılmaz'ın" -> "Beridze'nin"
            m = re.match(r"(['’])([a-zçğıöşü]+)", text[pos:pos + 12])
            if m: out += m.group(1) + S.reinflect(m.group(2), val); pos += len(m.group(0))
    out += text[pos:]
    # T.C. Kimlik No labels before a YKN become Yabancı Kimlik No
    for a, b, t in sorted(new_spans, reverse=True):   # right to left, so earlier offsets stay valid
        if t != "YKN": continue
        m = re.search(r"(T\.C\. Kimlik No|TCKN|TC Kimlik No|T\.C\. KİMLİK NO|Kimlik No)\s*:\s*$", out[max(0, a - 25):a])
        if m:
            lab = "Yabancı Kimlik No"; s0 = max(0, a - 25) + m.start(1); e0 = max(0, a - 25) + m.end(1); d = len(lab) - (e0 - s0)
            out = out[:s0] + lab + out[e0:]
            new_spans = [[x + d if x >= e0 else x, y + d if y >= e0 else y, tt] for x, y, tt in new_spans]
    return {"id": doc.get("id", "") + "-foreign", "text": out, "spans": new_spans}

def foreign_mix(seed: int = 0, share: float = 0.25, synth=None):
    """Synthetic train set with `share` swapped + court/petition foreign training docs. Returns (docs, info)."""
    rng = random.Random(seed); pool = N.split(seed=0)["train"]
    synth = K.load_synth("train") if synth is None else synth
    idx = set(rng.sample(range(len(synth)), int(len(synth) * share)))
    mixed = [swap_foreign(d, rng, pool) if i in idx else d for i, d in enumerate(synth)]
    S_ = B.get()
    extra = S_["train-court-foreign"] + S_["train-petition-foreign"]
    return mixed, extra, {"synthetic": len(synth), "swapped": len(idx), "court": len(S_["train-court-foreign"]), "petition": len(S_["train-petition-foreign"])}

def write_berturk_extra(path=None, seed=0):
    """BERTurk v3 extra data: the swapped synthetic copies (added, not replacing: train_berturk.py loads the
    original synthetic set itself) + court and petition training docs."""
    import json
    synth, extra, info = foreign_mix(seed=seed)
    docs = [d for d in synth if d.get("id", "").endswith("-foreign")] + extra
    path = Path(path or K.DATA / "foreign" / "train_berturk_foreign.jsonl")
    with path.open("w", encoding="utf-8") as f:
        for d in docs: f.write(json.dumps({"text": d["text"], "spans": d["spans"]}, ensure_ascii=False) + "\n")
    print(f"wrote {path}: {len(docs)} docs ({info})")
    return path

if __name__ == "__main__":
    if "--berturk" in sys.argv: write_berturk_extra(); sys.exit()
    rng = random.Random(1); pool = N.split()["train"]
    for d in K.load_synth("train")[:2]:
        x = swap_foreign(d, rng, pool); print(x["text"][:600]); print([(x["text"][a:b], t) for a, b, t in x["spans"]][:8]); print("---")
