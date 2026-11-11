"""Compare the browser's spans (tests_parity_tagger.cjs output) with Python onnxruntime + the same bundle.
  KATIP_MODEL=<model dir> python3 ml/parity_py.py <browser.json> <folder with <id>.txt>
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import eval_system as E  # noqa: E402
b = json.load(open(sys.argv[1])); folder = Path(sys.argv[2]); diff = n = 0
for id_, spans in b.items():
    t = (folder / f"{id_}.txt").read_text(encoding="utf-8")
    py = {(s["entity_type"], s["start"], s["end"]) for s in E.local_detect.detect(t, extra=E.ner(t))}
    br = {tuple(x) for x in spans}; n += len(py)
    if py != br: diff += 1; print(id_, "py-only", py - br, "browser-only", br - py)
print(f"{len(b)} docs, {n} spans, {diff} differ")
