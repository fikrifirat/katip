"""Build data/headings.json: article headings of the core Turkish codes, from Katip Cite's statute index.

    git show origin/cite-bench:lab/cite/data/statutes.json.gz > /tmp/statutes.json.gz
    python lab/emsal/build_headings.py /tmp/statutes.json.gz

The index (lab/cite on branch cite-bench) is built from github.com/onurcan-b/acik-mevzuat, a daily mirror of
mevzuat.adalet.gov.tr. Official legislation texts are not protected by copyright (FSEK art. 31).
In that index an article's heading sits at the end of the previous article's text; we cut it from there.
"""
import gzip, json, re, sys
from pathlib import Path

LAWS = {"5237": "TCK", "5271": "CMK", "6098": "TBK", "4721": "TMK", "6100": "HMK", "2004": "İİK", "6102": "TTK",
        "2577": "İYUK", "2709": "AY", "6698": "KVKK", "4857": "İş K", "5510": "SGK", "6284": "6284 s.K"}

def heading(prev_text: str) -> str:
    t = re.sub(r"\s*\[\d+\]", "", prev_text).strip()
    # the heading follows the last sentence end or closing parenthesis of the previous article
    m = re.search(r"(?:[.:;)]|\b[a-zçğıöşü]{1,2}\.)\s+([^:;)]{3,160}?)$", t)
    h = m.group(1) if m else ""
    h = re.sub(r"^.*\b(BÖLÜM|KISIM|KİTAP)\s+", "", h)        # 'İKİNCİ BÖLÜM Tutuklama Tutuklama nedenleri'
    return h.strip()

def main(src):
    d = json.load(gzip.open(src))
    out = {"source": d.get("source"), "commit": d.get("commit"), "laws": {}}
    for key, law in d["laws"].items():
        no = key.split("-")[0]
        if no not in LAWS:
            continue
        arts = (law.get("arts") or {}).get("madde") or {}
        have = out["laws"].get(LAWS[no])
        if have and have["n_articles"] >= len(arts):      # several entries per number (amending laws): keep the code itself
            continue
        nums = sorted((int(n) for n in arts if n.isdigit()))
        heads = {}
        for n in nums:
            prev = arts.get(str(n - 1))
            if prev:
                h = heading(prev.get("t", ""))
                if h:
                    heads[str(n)] = h
        out["laws"][LAWS[no]] = {"no": no, "title": law.get("title"), "n_articles": len(arts), "headings": heads}
    p = Path(__file__).with_name("data") / "headings.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(p, {k: len(v["headings"]) for k, v in out["laws"].items()})

if __name__ == "__main__":
    main(sys.argv[1])
