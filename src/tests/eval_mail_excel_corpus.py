"""Score the e-mail and Excel test set (make_mail_excel_corpus.py) through Katip Kalkan's masking path:
read -> detect (profile "ai") -> masked copy -> everything readable in the copy (local_formats.leak_text).

For each answer-key value: is it still readable in the masked copy? The same value in the sample's plain
.txt goes through the same path, so a value the container lost (masked in .txt, readable in .eml/.msg/.xlsx)
is the reader's fault, not the detector's.

  python3 src/tests/eval_mail_excel_corpus.py /tmp/mx-corpus [--json out.json]
KATIP_MODEL=none runs rules only; the default is the bundled Katip Mask Nano model.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("KATIP_HOME", tempfile.mkdtemp())
os.environ.setdefault("KATIP_SDK", "0")
sys.path.insert(0, str(Path(__file__).parents[2] / "connector"))
from katip_kalkan import core, engine, vault  # noqa: E402

squash = lambda s: re.sub(r"\s+", "", s).casefold()


def run(path: Path):
    kind, text, data, ocr, _ = engine.read_text(path)
    spans = core._detect(text, vault.open_vault("eval-" + path.name), "ai", ocr)
    out = engine.redact_bytes(kind, data, spans, "box")
    _, fmt = engine.load()
    readable = fmt.leak_text("eml" if kind == "msg" else kind, out)
    shown = fmt.extract("eml" if kind == "msg" else kind, out)
    return readable, shown, spans


def main(d: Path, js: str | None):
    key = json.loads((d / "answer_key.json").read_text(encoding="utf-8"))
    res = {}
    for name in sorted(key):
        readable, shown, spans = run(d / name)
        r = squash(readable)
        res[name] = {"left": [v for v in key[name]["mask"] if squash(v) in r],
                     "lost": [k for k in key[name]["keep"] if squash(k) not in squash(shown)],
                     "n": len(key[name]["mask"])}
    base = {key[n]["source"][0]: set(res[n]["left"]) for n in key if key[n].get("baseline")}
    rows = defaultdict(lambda: defaultdict(int))
    container_only = []
    for name, r in res.items():
        fmt = "txt (baseline)" if key[name].get("baseline") else name.rsplit(".", 1)[1] if not name.endswith(".eml") else "eml"
        rows[fmt]["files"] += 1
        rows[fmt]["values"] += r["n"]
        rows[fmt]["readable"] += len(r["left"])
        rows[fmt]["content lost"] += len(r["lost"])
        if not key[name].get("baseline"):
            for v in r["left"]:
                if not any(v in base.get(s, set()) for s in key[name]["source"]):
                    container_only.append((name, v))
                    rows[fmt]["readable, masked in .txt"] += 1
    print(f"{'format':16} {'files':>5} {'values':>6} {'masked':>7} {'readable':>8} {'only container':>14} {'content lost':>12}")
    for f in ["txt (baseline)", "eml", "msg", "xlsx"]:
        x = rows[f]
        print(f"{f:16} {x['files']:>5} {x['values']:>6} {x['values'] - x['readable']:>7} {x['readable']:>8} "
              f"{x['readable, masked in .txt']:>14} {x['content lost']:>12}")
    for name, v in container_only:
        print("  readable only in the container:", name, "|", v)
    for name, r in res.items():
        if r["lost"]:
            print("  content lost:", name, "|", r["lost"])
    if js:
        Path(js).write_text(json.dumps({"by_format": rows, "container_only": container_only, "files": res},
                                       ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(Path(a[0]), a[a.index("--json") + 1] if "--json" in a else None)
