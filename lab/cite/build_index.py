"""Build Katip Cite's statute index from Açık Mevzuat (github.com/onurcan-b/acik-mevzuat), a daily, automated
mirror of every Turkish law (Kanun) on the Ministry of Justice's UYAP/Bedesten service.

    git clone --depth 1 https://github.com/onurcan-b/acik-mevzuat ../acik-mevzuat
    python lab/cite/build_index.py ../acik-mevzuat

Writes lab/cite/data/statutes.json.gz: for every law, its number, title, status (in force / repealed) and the set of
article numbers with their status; for the core laws (CORE below) also each article's text, so the checker can test
whether a cited article is about what the sentence claims. Law texts are official texts (not copyrighted, FSEK art. 31);
we keep the source commit so every verdict can be traced to a dated snapshot.
"""
import gzip, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "statutes.json.gz"

# Laws whose article text we keep (the rest: existence and status only). Chosen for the bench's risk areas.
CORE = {"1475", "2709", "4721", "6098", "6100", "4857", "5237", "5271", "2004", "6102", "6698", "6458", "6735", "5901",
        "6502", "634", "7201", "6325", "7036", "1136", "5718", "2577", "5510", "492", "2644", "1512", "5275", "5395",
        "4734", "3194", "7338", "6356"}

# Article headings in the mirror's text: "MADDE 1-", "Madde 2 -", "MADDE 61. -", "Madde 87 (Mülga: ...)", "MADDE 428 İşyerinin".
# A bare "MADDE 428 X" (no dash) is accepted only in capitals; in-text references are lower case ("5 inci maddesi").
HEAD = re.compile(r"(?<![\wçğıöşüÇĞİÖŞÜ])(?:(EK\s+MADDE|GEÇİCİ\s+MADDE|MADDE|Ek\s+Madde|Geçici\s+Madde|Madde)\s+(\d{1,4})"
                  r"(?:\s*/\s*([A-Za-zÇĞÖŞÜçğöşü])(?![A-Za-zçğıöşüÇĞİÖŞÜ]))?\s*\.?\s*(?:[-–—]|(?=\(\s*(?:Mülga|MÜLGA|Ek|Değişik)))"
                  r"|(EK\s+MADDE|GEÇİCİ\s+MADDE|MADDE)\s+(\d{1,4})\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]))")
MULGA = re.compile(r"^\s*\(\s*(Mülga|MÜLGA)")


def kind_of(word):
    w = word.upper().replace(" ", "")
    return "ek" if w.startswith("EK") else "gecici" if w.startswith("GEÇİCİ") else "madde"


def parse(text):
    """Return {kind: {num: {"s": status, "t": text}}} from a law's normalised text."""
    body = text.split("\n---\n", 1)[-1]
    flat = re.sub(r"\s+", " ", body.replace("\u00ad", ""))
    arts = {"madde": {}, "ek": {}, "gecici": {}}
    ms = list(HEAD.finditer(flat))
    for i, m in enumerate(ms):
        word, n = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(5))
        k, num = kind_of(word), n + (("/" + m.group(3).upper()) if m.group(3) else "")
        seg = flat[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(flat)].strip()
        status = "repealed" if MULGA.match(seg) else "in_force"
        if num in arts[k] and arts[k][num]["s"] == "in_force":
            continue  # keep the first in-force occurrence; later hits are usually amendment notes quoting the heading
        arts[k][num] = {"s": status, "t": seg[:4000]}
    return arts


def main(src):
    src = Path(src)
    commit = subprocess.run(["git", "-C", str(src), "log", "-1", "--format=%H %cI"], capture_output=True, text=True).stdout.split()
    laws = {}
    for meta_p in sorted((src / "kanunlar").glob("*/ustveri.json")):
        meta = json.loads(meta_p.read_text())
        text = (meta_p.parent / "metin.md").read_text()
        no, slug = meta["law_number"], meta["slug"]
        arts = parse(text)
        removed_file = "yururlukten-kaldirilmis" in slug or "yururlukten-kaldirilan" in slug
        laws[slug] = {
            "no": no, "title": meta["title"], "type": meta["source_type"],
            "status": "repealed" if meta["effective_status"] != "in_force" else "in_force",
            "removed_provisions_file": removed_file,
            "source": meta["source_url"], "accepted": meta.get("accepted_date"),
            "arts": {k: {n: ({"s": a["s"], "t": a["t"]} if no in CORE and not removed_file else {"s": a["s"]})
                         for n, a in v.items()} for k, v in arts.items()},
        }
    idx = {"source": "github.com/onurcan-b/acik-mevzuat", "commit": commit[0] if commit else None,
           "commit_date": commit[1] if len(commit) > 1 else None, "laws": laws}
    OUT.parent.mkdir(exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(laws)} laws, {sum(len(l['arts']['madde']) for l in laws.values()):,} articles -> {OUT} "
          f"({OUT.stat().st_size / 1e6:.1f} MB), snapshot {idx['commit'][:10]} {idx['commit_date']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../acik-mevzuat")
