"""Score any Katip model folder on real text the way notebook 04 does: pick the trust setting on the dev
sets, then open the Wiki NER test set once. Names only (PERSON).

  python lab/score_model.py ml/berturk/out

Prints a dev table, the chosen trust, and test recall/precision with 95% CIs; writes
lab/results/score_<folder>.json. Use the chosen trust as KATIP_TRUST for ml/benchmark.py and in
docs/models/registry.json.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import katiplab as K  # noqa: E402
import distill as D  # noqa: E402

model_dir = Path(sys.argv[1]).resolve()
K.get_wikiner()
tagger = K.Tagger(model_dir)
dev_sets = {"wiki dev": K.load_wiki("dev"), "heldout": K.load_synth("heldout")}
rows = D.dev_table(tagger, dev_sets)
print(f"{'use':10} {'trust':>5}  wiki dev recall/precision  heldout recall")
for r in rows:
    print(f"{r['use']:10} {str(r['trust']):>5}  {100 * r['wiki dev recall']:5.1f}% / {100 * r['wiki dev precision']:5.1f}%      {100 * r['heldout recall']:5.1f}%")
trust, _ = D.choose_trust(rows)
print(f"\nchosen trust on dev: {trust}  (rule: heldout recall >= 96.5%, best Wiki dev F2)")

test_sets = {"wiki test": K.load_wiki("test"), "blind": K.load_synth("blind"), "negatives": K.load_synth("negatives")}
r = K.evaluate("pipeline", K.pipeline(tagger, trust=trust), test_sets)
w, b, n = r["wiki test"], r["blind"], r["negatives"]
print(f"wiki test  recall {100 * w['recall']:.1f}% [{100 * w['recall_ci'][0]:.1f}–{100 * w['recall_ci'][1]:.1f}]  "
      f"precision {100 * w['precision']:.1f}%  {w['ms_per_doc']:.1f} ms/sentence")
print(f"blind      recall {100 * b['recall']:.1f}%  precision {100 * b['precision']:.1f}%")
print(f"negatives  false names {n['false']}")
print(f"size       {tagger.size_mb:.1f} MB")
out = K.RESULTS / f"score_{model_dir.parent.name}_{model_dir.name}.json"
out.write_text(json.dumps({"model_dir": str(model_dir.relative_to(K.ROOT)) if model_dir.is_relative_to(K.ROOT) else model_dir.name,
                           "trust": trust, "size_mb": tagger.size_mb, "dev": rows,
                           "test": {s: {k: v for k, v in x.items() if k != "_rows"} for s, x in r.items()}}, indent=1, default=float))
print("wrote", out)
