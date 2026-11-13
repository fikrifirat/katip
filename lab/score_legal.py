"""Score models on real court prose with known names (lab/legal.py) next to Wiki NER test. No training.

  python lab/score_legal.py                      # every model this lab has on disk, at its chosen trust
  python lab/score_legal.py ml/berturk/out:0.9   # or name folders, each with an optional :trust

Writes lab/results/legal.json and prints one table.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import katiplab as K  # noqa: E402
import legal as L  # noqa: E402

def chosen_trust(name, default):
    """The dev-chosen trust from notebooks 02/04, if they were run."""
    for f, key in (("02_selected.json", None), ("04_test.json", "trust")):
        p = K.RESULTS / f
        if not p.exists(): continue
        d = json.loads(p.read_text())
        if key is None and name == "pii-names-tiny": return d["trust"]
        if key and name in d.get(key, {}): return d[key][name]
    return default

sel = json.loads((K.RESULTS / "02_selected.json").read_text()) if (K.RESULTS / "02_selected.json").exists() else None
PRESET = [  # name, folder, trust (None = rules + model as the published Tiny ships)
    ("Tiny (published)", K.TINY, None),
    ("pii-names-tiny", K.ROOT / sel["model_dirs"][0] if sel else None, chosen_trust("pii-names-tiny", 0.5)),
    ("Cosmos tiny (pretrained)", K.RUNS / "ft_turkish-tiny-bert-uncased", chosen_trust("Cosmos tiny (pretrained)", 0.5)),
    ("DistilBERTurk (pretrained)", K.RUNS / "ft_distilbert-base-turkish-cased", chosen_trust("DistilBERTurk (pretrained)", 0.5)),
    ("BERTurk v1 (synthetic only, as shipped)", K.BERTURK, 0.9),
    ("BERTurk-R (names only, lab)", K.RUNS / "teacher_berturk_r", chosen_trust("teacher BERTurk-R", 0.5)),
]
if len(sys.argv) > 1:
    PRESET = []
    for a in sys.argv[1:]:
        d, _, t = a.partition(":"); PRESET.append((Path(d).name, Path(d).resolve(), float(t) if t else None))

K.get_wikiner()
sets = {**{f"legal {k}": v for k, v in L.get_legal().items()}, "wiki test": K.load_wiki("test")}
rows = [("Rules only", K.rules(), None, 0.3)]
for name, d, t in PRESET:
    if d is None or not (Path(d) / "config.json").exists():
        print(f"skip {name}: no model at {d}"); continue
    tg = K.Tagger(d); rows.append((f"{name} @ trust {t}", K.pipeline(tg, trust=t), t, tg.size_mb))

out = {}
print(f"\n{'model':52} {'MB':>6}  {'legal common':>22}  {'legal unseen':>22}  {'wiki test':>9}")
print(f"{'':52} {'':>6}  {'recall / prec / false':>22}  {'recall / prec / false':>22}  {'recall':>9}")
for name, det, t, mb in rows:
    r = K.evaluate(name, det, sets); out[name] = {"trust": t, "size_mb": mb, **{s: {k: v for k, v in x.items() if k != "_rows"} for s, x in r.items()}}
    c, u, w = r["legal common"], r["legal unseen"], r["wiki test"]
    f = lambda x: f"{100 * x['recall']:5.1f}% / {100 * x['precision']:5.1f}% / {x['false']:4d}"
    print(f"{name:52} {mb:6.1f}  {f(c):>22}  {f(u):>22}  {100 * w['recall']:8.1f}%", flush=True)
(K.RESULTS / "legal.json").write_text(json.dumps(out, indent=1, default=float))
print("\nwrote", K.RESULTS / "legal.json")
