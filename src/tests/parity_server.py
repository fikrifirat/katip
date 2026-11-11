import json, sys, time, pathlib
from katip_redact.analyzer import detect
d = pathlib.Path(sys.argv[1]); res = {}
detect("ısınma")
t = time.time()
for f in sorted(d.glob("*.txt")):
    res[f.name] = [dict(entity_type=s.entity_type, start=s.start, end=s.end) for s in detect(f.read_text(), use_dictionary=False)]
print("server", round(time.time() - t, 2), "s", file=sys.stderr)
w = json.load(open(sys.argv[2])); diff = 0; n = 0
for k, v in res.items():
    a = {(s["entity_type"], s["start"], s["end"]) for s in v}
    b = {(s["entity_type"], s["start"], s["end"]) for s in w[k]}
    n += len(a)
    if a != b: diff += 1; print(k, "server-only", a - b, "wasm-only", b - a)
print(f"{len(res)} docs, {n} spans, {diff} docs differ")
