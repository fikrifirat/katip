"""Minimal stand-in for the two presidio_analyzer classes recognizers.py uses.

Lets katip_redact/recognizers.py run unchanged inside Pyodide (no spaCy, no
Presidio wheels in the browser). Behaviour matches what AnalyzerEngine does
for our recognizers: run each, filter by score, drop exact duplicates.
"""


class RecognizerResult:
    RECOGNIZER_NAME_KEY = "recognizer_name"

    def __init__(self, entity_type, start, end, score, analysis_explanation=None, recognition_metadata=None):
        self.entity_type, self.start, self.end, self.score = entity_type, start, end, score
        self.recognition_metadata = recognition_metadata or {}


class EntityRecognizer:
    def __init__(self, supported_entities, name=None, supported_language="en", **_):
        self.supported_entities = supported_entities
        self.name = name or type(self).__name__
        self.supported_language = supported_language
        self.load()

    def load(self):
        pass
