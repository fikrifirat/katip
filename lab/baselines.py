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
        # unmapped spans keep Presidio's label: they still count as masked text, never as a typed hit
        return [(a, b, _PRESIDIO.get(lab) or lab) for a, b, lab in json.loads(w.stdout.readline())]
    det("Ali Veli")  # fail early if the worker can't start
    return det

# Presidio's own entity names -> ours (DATE_TIME and LOCATION have no exact match and stay as they are)
_PRESIDIO = {"PERSON": "PERSON", "EMAIL_ADDRESS": "EMAIL", "IBAN_CODE": "IBAN", "PHONE_NUMBER": "PHONE", "CREDIT_CARD": "CREDIT_CARD",
             "IP_ADDRESS": "IP_ADDRESS"}
_MAP = [("TCKN", ("TCKN", "TC_KIMLIK", "NATIONAL_ID", "IDCARD", "ID_NUM", "SSN")), ("IBAN", ("IBAN",)), ("EMAIL", ("EMAIL", "MAIL")),
        ("PHONE", ("PHONE", "TEL")), ("ADDRESS", ("ADDRESS", "ADRES", "STREET")), ("BIRTH_DATE", ("BIRTH", "DOB", "DOGUM")),
        ("PLATE", ("PLATE", "PLAKA")), ("PERSON", ("PER", "NAME", "AD_SOYAD", "AD", "SOYAD", "FIRST", "LAST"))]
def map_label(lab):
    """Off-the-shelf label -> Katip entity type (None = not PII we score)."""
    u = lab.upper().replace("B-", "").replace("I-", "")
    for t, keys in _MAP:
        if any(k == u or k in u.split("_") or (len(k) >= 4 and u.startswith(k)) for k in keys): return t
    return None

def _hf(model_id):
    def make():
        from transformers import pipeline
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_id)
        if not tok.model_max_length or tok.model_max_length > 4096: tok.model_max_length = 512   # some cards leave it unset
        # stride: long documents are split into overlapping windows instead of overflowing the position table
        nlp = pipeline("token-classification", model=model_id, tokenizer=tok, aggregation_strategy="simple", stride=64)
        det = lambda text: [(e["start"], e["end"], t) for e in nlp(text) if (t := map_label(e["entity_group"]))]
        det.params = sum(p.numel() for p in nlp.model.parameters())
        det.labels = sorted(set(nlp.model.config.id2label.values()))
        det.size_mb = round(sum(p.numel() * p.element_size() for p in nlp.model.parameters()) / 1e6, 1)  # weights as loaded
        return det
    return make

def gliner():
    from gliner import GLiNER
    m = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
    det = lambda text: [(e["start"], e["end"], "PERSON") for e in m.predict_entities(text, ["person"], threshold=0.5)]
    det.params = sum(p.numel() for p in m.parameters())
    det.size_mb = round(sum(p.numel() * p.element_size() for p in m.parameters()) / 1e6, 1)
    return det

BASELINES = {"presidio": ("R1 Presidio + spaCy xx (vanilla)", presidio),
             "savasy": ("X1 savasy BERTurk NER", _hf("savasy/bert-base-turkish-ner-cased")),
             "akdeniz": ("X2 XLM-R Turkish NER", _hf("akdeniz27/xlm-roberta-base-turkish-ner")),
             "gliner": ("X3 GLiNER multi PII", gliner),
             # Turkish PII models published on Hugging Face (added 13 Nov 2026, before any of them was run)
             "cosmos-pii": ("X4 ytu-ce-cosmos ModernBERT-TR PII", _hf("ytu-ce-cosmos/modernbert-tr-pii-ner")),
             "kvkk-pii-ner": ("X5 ersanbil kvkk-pii-ner", _hf("ersanbil/kvkk-pii-ner")),
             "openmed-tr": ("X6 OpenMed PII Turkish (335M)", _hf("OpenMed/OpenMed-PII-Turkish-BiomedELECTRA-Large-335M-v1"))}

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
