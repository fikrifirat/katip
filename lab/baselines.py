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
import json, os, re, sys
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
        ("PHONE", ("PHONE", "TEL", "TELEPHONE", "MOBILE", "GSM")), ("ADDRESS", ("ADDRESS", "ADRES", "STREET")), ("BIRTH_DATE", ("BIRTH", "DOB", "DOGUM", "DATEOFBIRTH")), ("CREDIT_CARD", ("CREDITCARD", "CREDIT_CARD", "CARD")),
        ("PLATE", ("PLATE", "PLAKA")), ("HEALTH", ("HEALTH", "MEDICAL", "SAGLIK")),
        ("PERSON", ("PERSON", "PER", "NAME", "FULLNAME", "AD_SOYAD", "AD", "SOYAD", "FIRST", "LAST"))]
def map_label(lab):
    """Off-the-shelf label -> Katip entity type (None = not PII we score)."""
    u = lab.upper().replace("B-", "").replace("I-", "")
    for t, keys in _MAP:
        if any(k == u or k in u.split("_") or (len(k) >= 4 and u.startswith(k)) for k in keys): return t
    return None

def _hf(model_id, labmap=None):
    """labmap: explicit {model label: our type}, checked against the model's id2label; labels left out keep their own
    name (masked text, never a typed hit). Without it, map_label guesses."""
    def make():
        from transformers import pipeline
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_id)
        if not tok.model_max_length or tok.model_max_length > 4096: tok.model_max_length = 512   # some cards leave it unset
        # stride: long documents are split into overlapping windows instead of overflowing the position table
        nlp = pipeline("token-classification", model=model_id, tokenizer=tok, aggregation_strategy="simple", stride=64)
        # labels with no counterpart (LOC, ORG, KVKK_SPECIAL, ...) keep their own name: the text still counts as masked, never as a typed hit
        def det(text, scores=False):
            # scores=True: (start, end, type, score) with the lowest piece score; for hybrids that pass spans to the rules
            out = []
            for e in sorted(nlp(text), key=lambda e: e["start"]):
                g = re.sub(r"^[BIES]-", "", e["entity_group"])   # BIOES models (privacy-filter) leave E-/S- on the group
                t = labmap.get(g, g) if labmap is not None else (map_label(g) or g)
                # some tokenizers return a word as several pieces ('İs','tan','bu','l'): join touching pieces of the same type
                if out and out[-1][2] == t and e["start"] - out[-1][1] <= 1 and not text[out[-1][1]:e["start"]].strip(" "):
                    out[-1] = (out[-1][0], e["end"], t, min(out[-1][3], float(e["score"])))
                else:
                    out.append((e["start"], e["end"], t, float(e["score"])))
            return out if scores else [x[:3] for x in out]
        det.params = sum(p.numel() for p in nlp.model.parameters())
        det.labels = sorted(set(nlp.model.config.id2label.values()))
        det.size_mb = round(sum(p.numel() * p.element_size() for p in nlp.model.parameters()) / 1e6, 1)  # weights as loaded
        if labmap is not None:
            groups = {re.sub(r"^[BIES]-", "", l) for l in det.labels} - {"O"}
            if set(labmap) - groups: raise ValueError(f"labmap names labels the model lacks: {sorted(set(labmap) - groups)}")
            det.unmapped = sorted(groups - set(labmap))
        return det
    return make

# Explicit label maps (14 Nov 2026), written from each model's config id2label. Left out on purpose: dates, times, cities and
# other places, organisations, account numbers of unknown kind, usernames, URLs: masked if found, but never a typed hit.
_OPENAI_PF = {"private_person": "PERSON", "private_address": "ADDRESS", "private_email": "EMAIL", "private_phone": "PHONE"}
_OPENMED_ML = {"FIRSTNAME": "PERSON", "MIDDLENAME": "PERSON", "LASTNAME": "PERSON", "SSN": "TCKN", "PHONE": "PHONE", "EMAIL": "EMAIL",
               "IBAN": "IBAN", "CREDITCARD": "CREDIT_CARD", "DATEOFBIRTH": "BIRTH_DATE", "STREET": "ADDRESS", "BUILDINGNUMBER": "ADDRESS",
               "SECONDARYADDRESS": "ADDRESS", "ZIPCODE": "ADDRESS", "VRM": "PLATE"}   # same schema in the Turkish OpenMed models
_PIIRANHA = {"GIVENNAME": "PERSON", "SURNAME": "PERSON", "IDCARDNUM": "TCKN", "SOCIALNUM": "TCKN", "TAXNUM": "VKN", "TELEPHONENUM": "PHONE",
             "EMAIL": "EMAIL", "CREDITCARDNUMBER": "CREDIT_CARD", "DATEOFBIRTH": "BIRTH_DATE", "STREET": "ADDRESS", "BUILDINGNUM": "ADDRESS",
             "ZIPCODE": "ADDRESS"}
_PIILOT = {"p_nm": "PERSON", "p_rrn": "TCKN", "p_ph": "PHONE", "p_em": "EMAIL", "p_add": "ADDRESS"}
_OPENMED_SC = {"first_name": "PERSON", "last_name": "PERSON", "ssn": "TCKN", "tax_id": "VKN", "phone_number": "PHONE", "fax_number": "PHONE",
               "email": "EMAIL", "credit_debit_card": "CREDIT_CARD", "date_of_birth": "BIRTH_DATE", "street_address": "ADDRESS",
               "postcode": "ADDRESS", "license_plate": "PLATE"}
_CONLL = {"PER": "PERSON"}

def gliner2_pii():
    from gliner2 import GLiNER2
    m = GLiNER2.from_pretrained("fastino/gliner2-privacy-filter-PII-multi")
    def det(text):
        r = m.extract_entities(text, ["person"], threshold=0.5, include_spans=True)
        return [(e["start"], e["end"], "PERSON") for e in r.get("entities", {}).get("person", [])]
    det.params = sum(p.numel() for p in m.parameters())
    det.size_mb = round(sum(p.numel() * p.element_size() for p in m.parameters()) / 1e6, 1)
    return det

# Full card label set (42 types) mapped to KVKK-Bench types; the card has no plate or health/medical label.
_GLINER2_FULL = {"person": "PERSON", "date_of_birth": "BIRTH_DATE", "email": "EMAIL", "phone_number": "PHONE",
                 "address": "ADDRESS", "national_id_number": "TCKN", "government_id": "TCKN", "passport_number": "PASSPORT",
                 "tax_id": "VKN", "tax_number": "VKN", "iban": "IBAN", "bank_account": "IBAN",
                 "card_number": "CREDIT_CARD", "payment_card": "CREDIT_CARD"}

def gliner2_pii_full():
    from gliner2 import GLiNER2
    m = GLiNER2.from_pretrained("fastino/gliner2-privacy-filter-PII-multi")
    labels = list(_GLINER2_FULL)
    def det(text):
        r = m.extract_entities(text, labels, threshold=0.5, include_spans=True)
        return [(e["start"], e["end"], _GLINER2_FULL[lab]) for lab, es in r.get("entities", {}).items()
                if lab in _GLINER2_FULL for e in es]
    det.params = sum(p.numel() for p in m.parameters())
    det.size_mb = round(sum(p.numel() * p.element_size() for p in m.parameters()) / 1e6, 1)
    return det

def gliner():
    from gliner import GLiNER
    m = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
    det = lambda text: [(e["start"], e["end"], "PERSON") for e in m.predict_entities(text, ["person"], threshold=0.5)]
    det.params = sum(p.numel() for p in m.parameters())
    det.size_mb = round(sum(p.numel() * p.element_size() for p in m.parameters()) / 1e6, 1)
    return det


LLM_TYPES = ["PERSON", "TCKN", "VKN", "PHONE", "EMAIL", "IBAN", "CREDIT_CARD", "ADDRESS", "PLATE", "BIRTH_DATE", "HEALTH"]
LLM_PROMPT = ("You mask personal data in Turkish documents under KVKK. List every piece of personal data in the text below, "
              "copied exactly as it appears. Types: " + ", ".join(LLM_TYPES) + ". PERSON is a person's name (not companies, courts "
              "or places); ADDRESS is a street address. Answer with JSON only: [{\"text\": \"...\", \"type\": \"...\"}]. "
              "If there is none, answer [].\n\nText:\n")

def llm(model_id, max_new_tokens=384):
    """A small instruction-tuned LLM asked to list the personal data; each listed string is masked wherever it occurs."""
    def make():
        import re, torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        dev = os.environ.get("KATIP_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16 if dev != "cpu" else torch.float32).to(dev).eval()
        def det(text):
            msgs = [{"role": "user", "content": LLM_PROMPT + text[:6000]}]
            ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt")
            ids = (ids["input_ids"] if hasattr(ids, "keys") else ids).to(dev)   # transformers 5 returns a BatchEncoding
            with torch.no_grad():
                out = model.generate(ids, max_new_tokens=max_new_tokens, do_sample=False)
            ans = tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
            m = re.search(r"\[.*\]", ans, re.S)
            try: items = json.loads(m.group(0)) if m else []
            except Exception: items = [{"text": t, "type": ty} for t, ty in re.findall(r'"text"\s*:\s*"([^"]+)"\s*,\s*"type"\s*:\s*"([A-Z_]+)"', ans)]
            spans = []
            for it in items if isinstance(items, list) else []:
                if not isinstance(it, dict): continue
                v, ty = str(it.get("text", "")).strip(), str(it.get("type", "")).upper()
                if len(v) < 2 or ty not in LLM_TYPES: continue
                for mm in re.finditer(r"(?<!\w)" + re.escape(v) + r"(?!\w)", text): spans.append((mm.start(), mm.end(), ty))
            return spans
        det.params = sum(p.numel() for p in model.parameters())
        det.size_mb = round(det.params * 2 / 1e6, 0)   # fp16 weights
        return det
    return make

BASELINES = {"presidio": ("R1 Presidio + spaCy xx (vanilla)", presidio),
             "savasy": ("X1 savasy BERTurk NER", _hf("savasy/bert-base-turkish-ner-cased")),
             "akdeniz": ("X2 XLM-R Turkish NER", _hf("akdeniz27/xlm-roberta-base-turkish-ner")),
             "gliner": ("X3 GLiNER multi PII", gliner),
             # Turkish PII models published on Hugging Face (added 13 Nov 2026, before any of them was run)
             "cosmos-pii": ("X4 ytu-ce-cosmos ModernBERT-TR PII", _hf("ytu-ce-cosmos/modernbert-tr-pii-ner")),
             "kvkk-pii-ner": ("X5 ersanbil kvkk-pii-ner", _hf("ersanbil/kvkk-pii-ner")),
             "qwen-1.5b": ("L1 Qwen2.5-1.5B-Instruct, prompted (local LLM)", llm("Qwen/Qwen2.5-1.5B-Instruct")),
             "openmed-tr": ("X6 OpenMed PII Turkish (335M)", _hf("OpenMed/OpenMed-PII-Turkish-BiomedELECTRA-Large-335M-v1")),
             # model-selection audit, 14 Nov 2026: most-downloaded PII / Turkish token-classification models on HF, explicit label maps
             "openai-pf": ("openai/privacy-filter", _hf("openai/privacy-filter", _OPENAI_PF)),
             "openmed-pf-v2": ("OpenMed privacy-filter multilingual v2", _hf("OpenMed/privacy-filter-multilingual-v2", _OPENMED_ML)),
             "openmed-pf": ("OpenMed privacy-filter multilingual", _hf("OpenMed/privacy-filter-multilingual", _OPENMED_ML)),
             "gliner2-pii": ("fastino GLiNER2 PII multi", gliner2_pii),
             "gliner2-pii-full": ("fastino GLiNER2 PII multi, full label set", gliner2_pii_full),
             "openmed-tr-33m": ("OpenMed PII Turkish ClinicalE5 33M", _hf("OpenMed/OpenMed-PII-Turkish-ClinicalE5-Small-33M-v1", _OPENMED_ML)),
             "xlmr-conll": ("XLM-R large CoNLL03 English", _hf("FacebookAI/xlm-roberta-large-finetuned-conll03-english", _CONLL)),
             "piiranha": ("piiranha v1", _hf("iiiorg/piiranha-v1-detect-personal-information", _PIIRANHA)),
             "piilot": ("PIILOT NER", _hf("ParkJunSeong/PIILOT_NER_Model", _PIILOT)),
             "openmed-sc-44m": ("OpenMed PII SuperClinical 44M", _hf("OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1", _OPENMED_SC)),
             "openmed-sc-434m": ("OpenMed PII SuperClinical 434M", _hf("OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1", _OPENMED_SC))}

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
