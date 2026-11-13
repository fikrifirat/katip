"""Browser-side detect(): katip_redact.analyzer.detect without Presidio/spaCy.

Same recognizers, same overlap priority, same adjacent merge, so a document
redacted in the browser gets the same spans as on the Katip server.
"""
from __future__ import annotations

import json

import re

from katip_redact.recognizers import (ALL_ENTITIES, default_recognizers, drop_place_names, is_lexical, ocr_form_values, ocr_name_repeats, ocr_tckn,
                                      split_addresses)
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


def _add_model_span(text, results, s, e, score, trust=None):
    """Combine a model PERSON span with the rules instead of letting the two compete:
    trim ordinary words off its edges (same lexicon test the name rules use), require
    a capital first letter, then widen an overlapping rule span, or add a new one when it looks like a full name
    (two or more capitalised tokens).

    trust: for a strong model (BERTurk), spans scored at or above it keep their edges (first names such as
    Esila are also in the ordinary-word list) and may be a single capitalised word. Either way a single word
    is accepted when it is part of a name already found in the document (Esila after Esila Boztepe)."""
    toks = [(m.start() + s, m.end() + s) for m in _TOK.finditer(text[s:e])]
    sure = trust is not None and score >= trust
    if not sure:
        while toks and is_lexical(text[toks[0][0]:toks[0][1]]):
            toks.pop(0)
        while toks and is_lexical(text[toks[-1][0]:toks[-1][1]]):
            toks.pop()
    if not toks or not text[toks[0][0]].isupper():
        return
    if all(fold(text[a:b]) in _person_stop() for a, b in toks):
        return  # place, institution or title words (Halep, Tahran, Hakim): not a name, whatever the model says
    s, e = toks[0][0], toks[-1][1]
    hits = [r for r in results if r.entity_type == "PERSON" and r.start < e and r.end > s]
    for r in hits:
        r.start, r.end = min(r.start, s), max(r.end, e)
        r.recognition_metadata["explanation"] = (r.recognition_metadata.get("explanation", "") + " + model").strip()
    if hits:
        return
    capital = all(text[a].isupper() for a, _ in toks)
    known = len(toks) == 1 and text[s:e].casefold() in _known_name_words(text, results)
    # one ordinary word opening a sentence ("Emir komuta zinciri...", "Selam verip...", "Rahmetli murisin...") is
    # not taken from the model alone; inside a sentence, or once the name is known in the document, it still is
    lone_word = (len(toks) == 1 and not known and is_lexical(text[s:e])
                 and re.search(r"(?:^|[.!?:;\n(\"“]\s*)$", text[max(0, s - 4):s]) is not None)
    if capital and (len(toks) >= 2 or (sure and not lone_word) or known):
        r = RecognizerResult("PERSON", s, e, score)
        r.recognition_metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: "name_tagger", "explanation": "on-device model"}
        results.append(r)


_STOP = None


def _person_stop():
    global _STOP
    if _STOP is None:
        _STOP = next((r.stop for r in recognizers() if hasattr(r, "stop")), frozenset())
    return _STOP


def _known_name_words(text, results):
    return {text[m.start() + r.start:m.end() + r.start].casefold()
            for r in results if r.entity_type == "PERSON" for m in _TOK.finditer(text[r.start:r.end])}


def _add_model_typed(text, results, typ, s, e, score):
    """ADDRESS / HEALTH span from a multi-type model: widen an overlapping rule span of the same
    type (the model often sees the whole address when the rules stop at the street), else add it,
    but only where nothing else was found and, for an address, when it has two or more words
    (district names such as Ilgın or Çankaya are also first names and surnames)."""
    while s < e and text[s] in " \t\n,.;:-":
        s += 1
    while e > s and text[e - 1] in " \t\n,;:-":
        e -= 1
    if e - s < 3:
        return
    hits = [r for r in results if r.entity_type == typ and r.start < e and r.end > s]
    for r in hits:
        a, b = min(r.start, s), max(r.end, e)
        # never widen over a value of another type (a name or ID next to the address)
        if any(o.entity_type != typ and o.start < b and o.end > a and not (o.start < r.end and o.end > r.start) for o in results):
            continue
        r.start, r.end = a, b
        r.recognition_metadata["explanation"] = (r.recognition_metadata.get("explanation", "") + " + model").strip()
    if hits:
        return
    if any(r.start < e and r.end > s for r in results):
        return
    if typ == "ADDRESS" and len(_TOK.findall(text[s:e])) < 2:
        return
    r = RecognizerResult(typ, s, e, score)
    r.recognition_metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: "pii_tagger", "explanation": "on-device model"}
    results.append(r)


def _result(typ, s, e, score, why, name="katip_postprocess"):
    r = RecognizerResult(typ, s, e, score)
    r.recognition_metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: name, "explanation": why}
    return r


def detect(text, threshold=0.5, entities=None, mask_terms=(), allow_terms=(), extra=(), trust=None,
           ocr_ranges=(), address_detail="street"):
    """extra: spans from an on-device model, as (start, end, score) or (start, end, score, type) tuples;
    a span without a type is a PERSON span.
    ocr_ranges: (start, end) ranges of the text that came from OCR (scans, photos): there an 11-digit
    number that fails the TCKN checksum is still masked, since handwritten digits are often misread.
    address_detail: "street" masks building, block, door and flat and leaves mahalle, street, district and
    province readable; "full" masks the whole address."""
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
    # names first, so a new address/health span can see them
    for x in sorted(extra, key=lambda x: (len(x) > 3 and x[3] not in (None, "PERSON"))):
        s, e, sc = x[:3]
        typ = x[3] if len(x) > 3 and x[3] else "PERSON"
        if typ not in entities:
            continue
        if typ == "PERSON":
            _add_model_span(text, results, s, e, sc, trust)
        else:
            _add_model_typed(text, results, typ, s, e, sc)
    if "TCKN" in entities:
        results += [_result("TCKN", s, e, sc, why, "tckn_ocr") for s, e, sc, why in ocr_tckn(text, ocr_ranges) if sc >= threshold]
    results += [_result(t, s, e, sc, why, "form_row_ocr") for t, s, e, sc, why in ocr_form_values(text, ocr_ranges)
                if sc >= threshold and t in (entities or ALL_ENTITIES)]
    results = drop_place_names(text, results)
    results = _dictionary(text, results, mask_terms, allow_terms)
    merged = _merge_adjacent(text, resolve_overlaps(results))
    if ocr_ranges and (not entities or "PERSON" in entities):
        rep = [_result("PERSON", s, e, sc, why, "name_repeat_ocr") for s, e, sc, why in ocr_name_repeats(text, ocr_ranges, merged)]
        if rep:
            merged = _merge_adjacent(text, resolve_overlaps(merged + rep))
    if address_detail == "street":
        merged = split_addresses(text, merged, _result)
    out = []
    for i, r in enumerate(merged):
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
                             o.get("allow", []), o.get("extra", []), o.get("trust"), o.get("ocr_ranges", []),
                             o.get("address_detail", "street")), ensure_ascii=False)
