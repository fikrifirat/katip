"""Two reference rows that show what the metrics mean (they are not models):  python lab/cite/references.py

  ref-quote       answers by quoting the expected article from the official text. The ceiling: it is always "right
                  article" and never invents; it misses "safe" only where the key fact sits in another article or
                  beyond the quoted part, or where the old law text itself mentions a repealed law.
  ref-fabricator  cites the right law with invented article numbers, plus the repealed 818 Borçlar Kanunu. The floor.
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from katip_cite import Checker

SHORT = {"4857": "İş Kanunu", "1475": "1475 sayılı İş Kanunu", "7036": "İş Mahkemeleri Kanunu", "6098": "TBK", "2004": "İİK",
         "6325": "6325 sayılı Kanun", "4721": "TMK", "5718": "MÖHUK", "5271": "CMK", "5237": "TCK", "6100": "HMK",
         "7201": "Tebligat Kanunu", "6698": "KVKK", "6458": "YUKK", "6735": "6735 sayılı Kanun", "5901": "Türk Vatandaşlığı Kanunu",
         "6502": "6502 sayılı Kanun", "634": "Kat Mülkiyeti Kanunu"}

if __name__ == "__main__":
    c = Checker()
    qs = [json.loads(l) for l in (HERE / "data" / "questions.jsonl").read_text().splitlines()]
    (HERE / "answers").mkdir(exist_ok=True)
    rows = {"ref-quote": [], "ref-fabricator": []}
    for q in qs:
        no, art = q["expect"][0].split(":")
        kind, num = ("ek", art[3:]) if art.startswith("ek ") else ("madde", art)
        _, _, a, _ = c.verify(no, kind, num, "", None)
        ref = f"{SHORT[no]} {'ek madde ' + num if kind == 'ek' else 'm. ' + num}"
        fake = f"{SHORT[no]} m. {900 + int(num.split('/')[0])}"
        for lang in ("tr", "en"):
            rows["ref-quote"].append({"id": q["id"], "lang": lang, "model": "ref-quote", "name": "Reference: quotes the expected article",
                                      "answer": f"{ref}: {a['t'][:1500]}", "seconds": 0, "base_url": "localhost"})
            rows["ref-fabricator"].append({"id": q["id"], "lang": lang, "model": "ref-fabricator", "name": "Reference: invents article numbers",
                                           "answer": f"{fake} ve 818 sayılı Borçlar Kanunu m. 12 gereğince.", "seconds": 0, "base_url": "localhost"})
    for k, rs in rows.items():
        (HERE / "answers" / f"{k}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs))
    print("wrote answers/ref-quote.jsonl and answers/ref-fabricator.jsonl")
