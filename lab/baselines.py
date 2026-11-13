"""Off-the-shelf baselines for the legal study (lab/legal/DESIGN.md, systems R1, X1-X3).

  python lab/baselines.py                 # every baseline whose dependencies are installed
  python lab/baselines.py presidio gliner # or name them

R1  presidio   vanilla Presidio Analyzer + spaCy xx_ent_wiki_sm (multilingual), default recognizers,
               no Katip code. pip install presidio-analyzer spacy, then the xx_ent_wiki_sm wheel from
               https://github.com/explosion/spacy-models/releases
X1  savasy     savasy/bert-base-turkish-ner-cased (Hugging Face), PER spans
X2  akdeniz    akdeniz27/xlm-roberta-base-turkish-ner (Hugging Face), PER spans
X3  gliner     urchade/gliner_multi_pii-v1, zero-shot label "person" (pip install gliner)

Each is scored alone and merged with Katip's rules (R0 ∪ X), on the same sets as score_legal.py.
Writes lab/results/baselines.json.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import katiplab as K  # noqa: E402
import legal as L  # noqa: E402

def presidio():
    import subprocess
    w = subprocess.Popen([sys.executable, "-I", str(Path(__file__).parent / "presidio_worker.py")], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)
    def det(text):
        w.stdin.write(json.dumps(text) + "\n"); w.stdin.flush()
        return [tuple(x) for x in json.loads(w.stdout.readline())]
    det("Ali Veli")  # fail early if the worker can't start
    return det

def _hf(model_id):
    def make():
        from transformers import pipeline
        nlp = pipeline("token-classification", model=model_id, aggregation_strategy="simple")
        return lambda text: [(e["start"], e["end"], "PERSON") for e in nlp(text) if e["entity_group"] in ("PER", "PERSON")]
    return make

def gliner():
    from gliner import GLiNER
    m = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
    return lambda text: [(e["start"], e["end"], "PERSON") for e in m.predict_entities(text, ["person"], threshold=0.5)]

BASELINES = {"presidio": ("R1 Presidio + spaCy xx (vanilla)", presidio),
             "savasy": ("X1 savasy BERTurk NER", _hf("savasy/bert-base-turkish-ner-cased")),
             "akdeniz": ("X2 XLM-R Turkish NER", _hf("akdeniz27/xlm-roberta-base-turkish-ner")),
             "gliner": ("X3 GLiNER multi PII", gliner)}

def with_rules(det):
    r = K.rules()
    return lambda text: r(text) + det(text)

if __name__ == "__main__":
    want = sys.argv[1:] or list(BASELINES)
    K.get_wikiner()
    sets = {**{f"legal {k}": v for k, v in L.get_legal().items()}, "wiki test": K.load_wiki("test"),
            "blind": K.load_synth("blind"), "negatives": K.load_synth("negatives")}
    out_p = K.RESULTS / "baselines.json"
    out = json.loads(out_p.read_text()) if out_p.exists() else {}
    for key in want:
        name, make = BASELINES[key]
        try: det = make()
        except Exception as e:  # missing package or model download blocked
            print(f"skip {name}: {type(e).__name__}: {str(e)[:120]}"); continue
        for label, d in ((name, det), (f"{name} + Katip rules", with_rules(det))):
            r = K.evaluate(label, d, sets)
            out[label] = {s: {k: v for k, v in x.items() if k != "_rows"} for s, x in r.items()}
            print(label, {s: f"{100*x['recall']:.1f}% / {100*x['precision']:.1f}% / {x['false']}" for s, x in r.items()}, flush=True)
            out_p.write_text(json.dumps(out, indent=1, default=float))
    print("wrote", out_p)
