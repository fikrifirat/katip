"""KVKK-Bench `special-health` track (DATA_PLAN.md §1): rule pre-labels for human review. HIDDEN track.

Reads the local crawls (git-ignored, raw decision text never leaves this machine):
  lab/data/legal_web/raw.jsonl          Yargıtay / Danıştay / AYM, query-driven crawl
  lab/data/legal_web/health_raw.jsonl   Yargıtay health queries (crawl.py --health)
Dedupes on (court, id), slot-fills the court's anonymised person slots with synthetic test-pool names
(slotfill.fill, same as the court track), then marks HEALTH candidates with rules. Writes
  lab/data/legal_web/health_review.jsonl   one row per strong-cue decision, strongest first (local only)

Row format (one JSON object per line):
  id, court, chamber, date, url, query       provenance (url is the public decision page)
  real_names                                 true for AYM: names the court published itself are left as they are and
                                             are NOT pre-labelled; the reviewer adds them as PERSON
  text                                       slot-filled decision text
  spans: [{start, end, type, source, needs_review, surface}]
         type   HEALTH | PERSON | TCKN | PHONE | EMAIL | IBAN | PLATE | BIRTH_DATE | ADDRESS
         source "fill" (exact: inserted by slot fill) or "rule:<name>" (a guess)
         needs_review  false for fill spans, true for every rule span
  cues: {rule: count}, strength               strength = number of strong-rule hits (rows are sorted on it)
  review_status "todo"                        reviewer sets "done" or "reject" (not health / unusable)
  reviewer_note ""
Review = fix HEALTH edges, delete false ones, add missed ones; check PERSON slots. Guide: ~1 min per doc.
Nothing here is scored until review_status is "done".

  python lab/legal/health_prelabel.py [--min-strength 1]
"""
from __future__ import annotations

import argparse, json, random, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import katiplab as K  # noqa: E402
import slotfill as S  # noqa: E402

WEB = K.DATA / "legal_web"
INPUTS = [WEB / "raw.jsonl", WEB / "health_raw.jsonl"]
OUT = WEB / "health_review.jsonl"
SEED = 20261114

L = "A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛû"
W = rf"[{L}][{L}'’-]*"                      # one word
NP = rf"(?:{W}\s+){{0,4}}{W}"               # up to 5 words
NUM = r"\d{1,3}(?:[.,]\d{1,2})?"
RATE = rf"(?:%\s?{NUM}|{NUM}\s?%|yüzde\s+{NUM})"
CONDITIONS = (r"kanser\w*|tümör\w*|lösemi\w*|lenfoma\w*|HIV|AIDS|hepatit\w*|tüberküloz\w*|verem\w*|epilep\w*|şizofren\w*|"
              r"depresyon\w*|bipolar|psikoz\w*|psikotik|demans\w*|alzheimer\w*|parkinson\w*|diyabet\w*|şeker hastalığı\w*|"
              r"otizm\w*|zek[aâ] geriliği\w*|mental retardasyon\w*|akıl hastalığı\w*|akıl hastası|ruh hastalığı\w*|"
              r"parapleji\w*|tetrapleji\w*|hemipleji\w*|felç\w*|inme|serebral palsi\w*|multipl skleroz\w*|"
              r"kalp krizi\w*|miyokard enfarktüsü\w*|beyin kanaması\w*|kafa travması\w*|travma sonrası stres bozukluğu\w*|"
              r"madde bağımlılığı\w*|alkol bağımlılığı\w*|uyuşturucu bağımlılığı\w*|kronik böbrek yetmezliği\w*|"
              r"diyaliz\w*|görme kaybı\w*|işitme kaybı\w*|amputasyon\w*|ampütasyon\w*")
# (name, strong?, regex, group holding the span)
RULES = [
    ("rate", True, re.compile(rf"(?:maluliyet|malûliyet|engel(?:lilik)?|özür(?:lülük)?|sakatlık|meslekte kazanma gücü(?:nün)?(?: kaybı)?|"
                              rf"çalışma gücü(?: kaybı)?|iş göremezlik)\s*(?:oranı(?:nın|na|nı)?\s*)?(?:\w+\s+){{0,2}}{RATE}", re.I), 0),
    ("rate_rev", True, re.compile(rf"{RATE}\s*(?:oranında\s*)?(?:\w+\s+){{0,2}}(?:maluliyet|malûliyet|engel(?:li|lilik)?|özür(?:lü)?|"
                                  rf"sakat(?:lık)?|meslekte kazanma gücü|çalışma gücü|iş göremezlik)\w*", re.I), 0),
    ("diagnosis", True, re.compile(rf"({NP})\s+(?:tanı(?:sı|sıyla|sı ile|sının|sına|sını)|teşhis(?:i|iyle|i ile|inin|ine|ini)|"
                                   rf"tanılı|teşhisli)\b"), 1),
    ("fracture", True, re.compile(rf"(?:{W}\s+){{0,2}}{W}\s+(?:kırığı|kırıkları|fraktürü|çıkığı|yaralanması)\w*", re.I), 0),
    ("surgery", True, re.compile(rf"(?:{W}\s+){{0,2}}{W}\s+ameliyatı\w*", re.I), 0),
    ("condition", True, re.compile(rf"\b(?:{CONDITIONS})\b", re.I), 0),
    ("psych", True, re.compile(r"\bpsikiyatri(?:k)?\s+(?:tedavi|rahatsızlı|hastalı|bozukluğ)\w*", re.I), 0),
    ("epikriz", True, re.compile(r"\bepikriz\w*", re.I), 0),
    # weak: health context, kept as candidates but they do not make a doc strong
    ("report", False, re.compile(r"\b(?:Adli Tıp|sağlık kurulu|heyet)\s+raporu\w*", re.I), 0),
    ("treatment", False, re.compile(r"\b(?:tedavi(?:si|sine|sini)?\s+(?:gördüğü|görmüş|altında)|hastanede\s+yatarak)\b", re.I), 0),
]
STOP_START = {"ve", "ile", "bu", "şu", "o", "bir", "olan", "olarak", "da", "de", "ki", "için", "göre", "dair", "ilişkin",
              "davacının", "davacıya", "davalının", "sanığın", "mağdurun", "müştekinin", "başvurucunun", "kişinin",
              "işçinin", "sigortalının", "hastanın", "çocuğun", "eşinin", "yapılan", "konulan", "verilen", "alınan",
              "tarihli", "raporda", "raporunda", "raporuna", "sonucunda", "nedeniyle", "dolayı", "üzerine", "kesin"}

def _trim(text, a, b):
    """Drop leading function words and punctuation from a rule span."""
    while a < b:
        m = re.match(rf"\s*({W})\s+", text[a:b])
        if not m or S.lower_tr(m.group(1)) not in STOP_START: break
        a += m.end()
    while a < b and not text[a].isalnum() and text[a] != "%": a += 1
    while b > a and not text[b - 1].isalnum() and text[b - 1] != "%": b -= 1
    return a, b

def health_spans(text):
    hits, cues = [], Counter()
    for name, strong, rx, g in RULES:
        for m in rx.finditer(text):
            a, b = _trim(text, m.start(g), m.end(g))
            if b - a < 3: continue
            hits.append([a, b, name, strong]); cues[name] += 1
    hits.sort(key=lambda h: (h[0], -h[1]))
    merged = []
    for h in hits:  # merge overlaps, keep the strongest rule name
        if merged and h[0] < merged[-1][1]:
            m = merged[-1]; m[1] = max(m[1], h[1])
            if h[3] and not m[3]: m[2], m[3] = h[2], True
        else: merged.append(h)
    return merged, cues

def load():
    seen, rows = set(), []
    for p in INPUTS:
        if not p.exists(): continue
        for line in p.open(encoding="utf-8"):
            r = json.loads(line)
            k = (r["court"], str(r["id"]))
            if k in seen or not r.get("text"): continue
            seen.add(k); rows.append(r)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-strength", type=int, default=1)
    a = ap.parse_args()
    rng, pool = random.Random(SEED), S.Pool("test")
    docs = load()
    out, by_court, n_fill, n_rule = [], Counter(), 0, 0
    for r in docs:
        real = r["court"] == "aym"
        if real: text, fills = r["text"], []
        else:
            f = S.fill(r["text"], rng, pool); text = f["text"]
            fills = [s for s in f["spans"] if s[2] in S.PII]
        hs, cues = health_spans(text)
        strength = sum(1 for h in hs if h[3])
        if strength < a.min_strength: continue
        spans = [{"start": s, "end": e, "type": t, "source": "fill", "needs_review": False, "surface": text[s:e]}
                 for s, e, t in fills]
        hs = [h for h in hs if not any(h[0] < s["end"] and s["start"] < h[1] for s in spans)]
        spans += [{"start": s, "end": e, "type": "HEALTH", "source": f"rule:{n}", "needs_review": True, "surface": text[s:e]}
                  for s, e, n, _ in hs]
        spans.sort(key=lambda s: s["start"])
        n_fill += len(fills); n_rule += len(hs); by_court[r["court"]] += 1
        out.append({"id": f"{r['court']}-{r['id']}", "court": r["court"], "chamber": r.get("chamber"), "date": r.get("date"),
                    "url": r.get("url"), "query": r.get("query"), "real_names": real, "text": text, "spans": spans,
                    "cues": dict(cues), "strength": strength, "review_status": "todo", "reviewer_note": ""})
    out.sort(key=lambda d: -d["strength"])
    with OUT.open("w", encoding="utf-8") as f:
        for d in out: f.write(json.dumps(d, ensure_ascii=False) + "\n")
    words = sum(len(d["text"].split()) for d in out)
    print(f"{len(docs)} decisions after dedupe -> {len(out)} strong (strength >= {a.min_strength}): {dict(by_court)}")
    print(f"HEALTH candidates {n_rule} (all needs_review), fill PII spans {n_fill}; {words:,} words, "
          f"median strength {sorted(d['strength'] for d in out)[len(out) // 2] if out else 0}")
    print(f"-> {OUT} (local only)")

if __name__ == "__main__":
    main()
