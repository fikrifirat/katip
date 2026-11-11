import json, sys
sys.argv = [sys.argv[0], "model2", "--q8"] + sys.argv[1:]
exec(open("eval_system.py").read().split("for d in [a for a")[0])
b = json.load(open("/tmp/browser_tagger.json")); diff = 0; n = 0
for id_, spans in b.items():
    t = open(f"/mnt/project-files/katip-redact/eval/blind/{id_}.txt", encoding="utf-8").read()
    py = {(s["entity_type"], s["start"], s["end"]) for s in local_detect.detect(t, extra=ner(t))}
    br = {tuple(x) for x in spans}; n += len(py)
    if py != br: diff += 1; print(id_, "py-only", py - br, "browser-only", br - py)
print(f"{len(b)} docs, {n} spans, {diff} differ")
