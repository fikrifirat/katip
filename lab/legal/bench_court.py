"""KVKK-Bench in court mode: the text track with address_detail="street" (Katip's court profile), as in PR #25.

  python lab/legal/bench_court.py rules mini-v2

Writes bench/results/court/<system>.json and bench/preds/court/<system>.jsonl (public split only); leaderboard rows are
not touched. Besides the usual score it reports how much of each gold ADDRESS stays readable, by the address's role
as the engine sees it (recognizers.address_role, plus the "address line under a name" cue):
  party     someone's own address  -> the court profile masks it whole
  property  the disputed property  -> kept readable on purpose (so it counts as "leak" against the bench gold)
  other     no role cue            -> street readable, house-level parts masked
"""
from __future__ import annotations

import json, sys, time
from collections import namedtuple
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench_run as R  # noqa: E402
from katip_redact import recognizers as REC  # noqa: E402  (from the engine zip, via katiplab)

Res = namedtuple("Res", "entity_type start end")


def role(text, s, e, pred):
    r = REC.address_role(text, s, e)
    if r is None and REC._under_a_name(text, s, [Res(t, a, b) for a, b, t in pred]):
        r = "party"
    return r or "other"


def run(key):
    R.DETECT_KW = {"address_detail": "street"}
    name, make = R.SYSTEMS[key]
    det, meta = make()
    gold = [r for p in sorted((R.BB.OUT / "public").glob("*.jsonl")) for r in R.BB.load(p)]
    for r in gold[:20]: det(r["text"])
    t0 = time.time(); pred = [{"id": r["id"], "spans": [list(x[:3]) for x in det(r["text"])]} for r in gold]
    secs = time.time() - t0
    roles = {}
    for g, p in zip(gold, pred):
        masked = np.zeros(len(g["text"]), bool)
        for a, b, _ in p["spans"]: masked[a:b] = True
        for s, e, t in g["spans"]:
            if t != "ADDRESS": continue
            x = roles.setdefault(role(g["text"], s, e, p["spans"]), [0, 0, 0])
            x[0] += e - s; x[1] += int((~masked[s:e]).sum()); x[2] += 1
    row = {"system": key, "name": name, "mode": "court (address_detail=street)", "split": "public", "version": R.BB.VERSION, **meta,
           "ms_per_doc": round(1000 * secs / len(gold), 1), **R.BS.score(gold, pred),
           "address_by_role": {k: {"addresses": n, "gold_chars": c, "readable_chars": l, "readable_rate": l / c} for k, (c, l, n) in roles.items()}}
    for d in ("results", "preds"): (HERE / "bench" / d / "court").mkdir(parents=True, exist_ok=True)
    (HERE / "bench" / "preds" / "court" / f"{key}.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pred))
    (HERE / "bench" / "results" / "court" / f"{key}.json").write_text(json.dumps(row, indent=1, default=float))
    R.DETECT_KW = {"address_detail": "full"}
    return row


if __name__ == "__main__":
    for k in sys.argv[1:]:
        r = run(k)
        print(f"{r['name']:45} KVKK-F2 {100 * r['KVKK-F2']:5.1f}  F2 gen {100 * r['F2 generated']:5.1f}  leak {100 * r['leak_rate']:5.2f}%  " +
              "  ".join(f"{k2} {100 * v['readable_rate']:.1f}% of {v['gold_chars']}" for k2, v in r["address_by_role"].items()), flush=True)
