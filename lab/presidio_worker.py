"""Runs vanilla Presidio in its own process (Katip's browser bundle ships a small presidio_analyzer stub
that would shadow the real package). Reads texts as JSON lines on stdin, writes spans as JSON lines."""
import json, sys
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
nlp = NlpEngineProvider(nlp_configuration={"nlp_engine_name": "spacy", "models": [{"lang_code": "tr", "model_name": "xx_ent_wiki_sm"}],
                                           "ner_model_configuration": {"model_to_presidio_entity_mapping": {"PER": "PERSON", "LOC": "LOCATION", "ORG": "ORGANIZATION"}}}).create_engine()
eng = AnalyzerEngine(nlp_engine=nlp, supported_languages=["tr"])
for line in sys.stdin:
    t = json.loads(line)
    print(json.dumps([(r.start, r.end, r.entity_type) for r in eng.analyze(text=t, language="tr")]), flush=True)
