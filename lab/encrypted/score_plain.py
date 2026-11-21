"""KVKK-Bench public names tracks (court-filled, prose) for Nano and its FHE-friendly variants, in plaintext.

  python lab/encrypted/score_plain.py nano fitted kd_singles
Writes lab/encrypted/results/plaintext_scores.json. The encrypted run (run_encrypted.py) checks that the
encrypted model produces the same spans as the "fitted" row here.
"""
import json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path[:0] = [str(HERE)]
import bench_eval as E
from dev_select import tagger_for

if __name__ == "__main__":
    out = HERE / "results" / "plaintext_scores.json"; out.parent.mkdir(exist_ok=True)
    res = json.loads(out.read_text()) if out.exists() else {}
    docs = E.gold({"court-filled", "prose"})
    for run in sys.argv[1:]:
        tg = tagger_for(run); res[run] = {}
        for mode in ("pipeline", "model"):
            r, _ = E.evaluate(tg, mode, docs=docs); res[run][mode] = r
        t0 = time.time(); [tg.word_labels(d["text"]) for d in docs[:200]]
        res[run]["ms_per_doc_plaintext"] = round(1000 * (time.time() - t0) / 200, 2)
        print(run, json.dumps(res[run]), flush=True)
    out.write_text(json.dumps(res, indent=1))
