"""Browser-side detect(): katip_redact.analyzer.detect without Presidio/spaCy.

Same recognizers, same overlap priority, same adjacent merge, so a document
redacted in the browser gets the same spans as on the Katip server.
"""
from __future__ import annotations

import json

import re

from katip_redact.recognizers import ALL_ENTITIES, default_recognizers, is_lexical
from katip_redact.textutil import TR_LETTER, fold

# copied from analyzer.py at build time (see build.py) -> PRIORITY, FLAG_ONLY_DEFAULT,
# resolve_overlaps, _merge_adjacent
from katip_redact._analyzer_core import (FLAG_ONLY_DEFAULT, PRIORITY, _merge_adjacent,
                                         resolve_overlaps)
from presidio_analyzer import RecognizerResult

_RECS = None


def recognizers():
    global _RECS
    if _RECS is None:
        _RECS = default_recognizers()
    return _RECS


def _dictionary(text, results, mask_terms, allow_terms):
    """Local firm dictionary: plain lists kept in the browser (never uploaded)."""
    allow = {fold(t).strip() for t in allow_terms if t.strip()}
    kept = [r for r in results if fold(text[r.start:r.end]).strip() not in allow]
    ftext = "".join(f if len(f := fold(c)) == 1 else c for c in text)  # keep offsets aligned
    for term in mask_terms:
        t = fold(term).strip()
        if len(t) < 2:
            continue
        i = ftext.find(t)
        while i >= 0:
            before = ftext[i - 1] if i else " "
            after = ftext[i + len(t)] if i + len(t) < len(ftext) else " "
            if not before.isalnum() and not after.isalnum():
                r = RecognizerResult("PERSON", i, i + len(t), 0.99)
                r.recognition_metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: "local_dictionary",
                                          "explanation": "term in the local dictionary"}
                kept.append(r)
            i = ftext.find(t, i + 1)
    return kept


_TOK = re.compile(rf"[{TR_LETTER}]+")


def _add_model_span(text, results, s, e, score):
    """Combine a model PERSON span with the rules instead of letting the two compete:
    trim ordinary words off its edges (same lexicon test the name rules use), require
    a capital first letter, then widen an overlapping rule span, or add a new one when it looks like a full name
    (two or more capitalised tokens)."""
    toks = [(m.start() + s, m.end() + s) for m in _TOK.finditer(text[s:e])]
    while toks and is_lexical(text[toks[0][0]:toks[0][1]]):
        toks.pop(0)
    while toks and is_lexical(text[toks[-1][0]:toks[-1][1]]):
        toks.pop()
    if not toks or not text[toks[0][0]].isupper():
        return
    s, e = toks[0][0], toks[-1][1]
    hits = [r for r in results if r.entity_type == "PERSON" and r.start < e and r.end > s]
    for r in hits:
        r.start, r.end = min(r.start, s), max(r.end, e)
        r.recognition_metadata["explanation"] = (r.recognition_metadata.get("explanation", "") + " + model").strip()
    # a span the rules did not see at all must look like a full name: two or more name tokens
    if not hits and len(toks) >= 2 and all(text[a].isupper() for a, _ in toks):
        r = RecognizerResult("PERSON", s, e, score)
        r.recognition_metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: "name_tagger", "explanation": "on-device model"}
        results.append(r)


def detect(text, threshold=0.5, entities=None, mask_terms=(), allow_terms=(), extra=()):
    """extra: PERSON spans from an on-device model, as (start, end, score) tuples."""
    entities = list(entities or ALL_ENTITIES)
    results, seen = [], set()
    for rec in recognizers():
        if not any(e in entities for e in rec.supported_entities):
            continue
        for r in rec.analyze(text, entities, None) or []:
            key = (r.entity_type, r.start, r.end)
            if r.score >= threshold and key not in seen:
                seen.add(key)
                results.append(r)
    if "PERSON" in entities:
        for s, e, sc in extra:
            _add_model_span(text, results, s, e, sc)
    results = _dictionary(text, results, mask_terms, allow_terms)
    out = []
    for i, r in enumerate(_merge_adjacent(text, resolve_overlaps(results))):
        meta = r.recognition_metadata or {}
        out.append({"id": f"s{i:04d}", "entity_type": r.entity_type, "start": r.start, "end": r.end,
                    "text": text[r.start:r.end], "score": round(r.score, 3),
                    "recognizer": meta.get(RecognizerResult.RECOGNIZER_NAME_KEY, ""),
                    "explanation": meta.get("explanation", ""),
                    "flag_only": r.entity_type in FLAG_ONLY_DEFAULT})
    return out


# ---- vanilla baseline: the open-source kvkk-pii regex layer (MIT), mapped to Katip's types
BASELINE_MAP = {"TC_KIMLIK": "TCKN", "TELEFON": "PHONE", "PLAKA": "PLATE", "EMAIL": "EMAIL", "IBAN": "IBAN",
                "KISI": "PERSON", "ADRES": "ADDRESS", "VKN": "VKN", "KREDI": "CREDIT_CARD", "IP": "IP_ADDRESS",
                "SAGLIK": "HEALTH"}
_BASE = None


def detect_baseline(text, threshold=0.5, entities=None):
    global _BASE
    if _BASE is None:
        from kvkk_pii import PiiDetector
        _BASE = PiiDetector()
    entities = set(entities or ALL_ENTITIES)
    out, last = [], -1
    for e in sorted(_BASE.analyze(text).entities, key=lambda e: (e.start, -e.end)):
        t = next((v for k, v in BASELINE_MAP.items() if e.entity_type.startswith(k)), None)
        if not t or t not in entities or e.start < last:
            continue
        last = e.end
        out.append({"id": f"s{len(out):04d}", "entity_type": t, "start": e.start, "end": e.end, "text": text[e.start:e.end],
                    "score": round(float(getattr(e, "score", 1.0) or 1.0), 3), "recognizer": "kvkk-pii", "explanation": e.entity_type,
                    "flag_only": t in FLAG_ONLY_DEFAULT})
    return out


def detect_json(text, opts_json="{}"):
    o = json.loads(opts_json)
    if o.get("baseline") == "kvkk-pii":
        return json.dumps(detect_baseline(text, o.get("threshold", 0.5), o.get("entities")), ensure_ascii=False)
    return json.dumps(detect(text, o.get("threshold", 0.5), o.get("entities"), o.get("mask", []),
                             o.get("allow", []), o.get("extra", [])), ensure_ascii=False)
