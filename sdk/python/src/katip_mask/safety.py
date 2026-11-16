"""After detection: catch ID numbers by context, mask every occurrence of each detected value, and refuse
to return text in which a detected value is still readable.

Same steps as Katip Kalkan (connector/katip_kalkan/core.py), so the SDK masks a document the way the
connector does. The guarantee is narrow on purpose: every value the detector found is hidden
everywhere it occurs, or masking fails. A value the detector never found is not covered by it.
"""
from __future__ import annotations

import re
from collections import defaultdict

from ._engine.textutil import tr_upper

BLOCK = "█"


class LeakError(RuntimeError):
    """A detected value would still be readable in the masked text. Carries the kinds and line numbers of
    what could not be hidden, never the values themselves."""

    def __init__(self, kinds: list[str], lines: list[int]):
        self.kinds, self.lines = kinds, lines
        super().__init__(f"masking refused: {len(lines) or 'some'} detected value(s) would stay readable "
                         f"(types: {', '.join(kinds)}; lines: {', '.join(map(str, lines))})")


_IDS = re.compile(r"(?<!\d)99\d{9}(?!\d)|(?i:(?:t\.?\s?c\.?\s*kimlik|tckn|ykn|yabanc[ıi]\s+kimlik)"
                  r"[^\d\n]{0,25})(\d{11})(?!\d)")


def id_numbers(text: str, spans: list[dict]) -> list[dict]:
    """ID numbers whose checksum fails (a typo, an OCR slip, an old foreigner number) are still masked:
    any 11-digit number starting with 99 is a YKN, and an 11-digit number right after "T.C. kimlik",
    "TCKN", "YKN" or "yabancı kimlik" is an ID."""
    out = list(spans)
    for m in _IDS.finditer(text):
        a, b = (m.start(1), m.end(1)) if m.group(1) else (m.start(), m.end())
        if any(s["start"] < b and a < s["end"] for s in out):
            continue
        typ = "YKN" if text[a:a + 2] == "99" else "TCKN"
        out.append({"id": f"i{len(out):04d}", "entity_type": typ, "start": a, "end": b, "text": text[a:b],
                    "score": 1.0, "recognizer": "katip_id_context", "explanation": "11 digits after an ID label"})
    return sorted(out, key=lambda s: s["start"])


def _value_pattern(value: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, value.split())) + r"(?!\w)", re.I)


def propagate(text: str, spans: list[dict]) -> list[dict]:
    """Mask every occurrence of a detected value, not only the ones the detector caught.
    Case-insensitive, whole words; values shorter than 4 characters are not propagated."""
    cands = {(s["entity_type"], s["text"].strip()) for s in spans}
    out = list(spans)
    for typ, val in sorted(cands, key=lambda c: (-len(c[1]), c[0], c[1])):
        if len(val) < 4:
            continue
        for m in _value_pattern(val).finditer(text):
            hit = [s for s in out if s["start"] < m.end() and m.start() < s["end"]]
            if any(s["start"] <= m.start() and s["end"] >= m.end() for s in hit):
                continue
            if any(s["entity_type"] != typ or s["start"] < m.start() or s["end"] > m.end() for s in hit):
                continue  # overlaps a different value: leave it to the detector
            out = [s for s in out if s not in hit]
            out.append({"id": f"p{len(out):04d}", "entity_type": typ, "start": m.start(), "end": m.end(),
                        "text": m.group(0), "score": 1.0, "recognizer": "katip_propagate",
                        "explanation": "another occurrence of a detected value"})
    return sorted(out, key=lambda s: s["start"])


def _leak_pattern(value: str) -> re.Pattern | None:
    if len(re.sub(r"\W", "", value)) < 4:
        return None
    return re.compile(r"(?<!\w)" + r"\W*".join(re.escape(w) for w in value.split()) + r"(?!\w)", re.I)


def _visible(text: str, spans: list[dict]) -> str:
    """The text that stays readable after masking; each masked span becomes " _ " ("_" is a word character,
    so a value can't be matched across the gap, and placeholder text is never searched)."""
    out, pos = [], 0
    for sp in sorted(spans, key=lambda s: (s["start"], -s["end"])):
        if sp["start"] < pos:
            continue
        out.append(text[pos:sp["start"]])
        out.append(" _ ")
        pos = sp["end"]
    out.append(text[pos:])
    return "".join(out)


def leaks(text: str, spans: list[dict]) -> list[str]:
    """Ids of detected values still readable after masking (whole words, case-insensitive)."""
    visible = _visible(text, spans)
    out = []
    for s in spans:
        pat = _leak_pattern(s["text"])
        if pat and pat.search(visible):
            out.append(s["id"])
    return out


def repair(text: str, spans: list[dict], leaked: list[str]) -> list[dict]:
    """Cover every remaining occurrence of a leaked value; an occurrence that overlaps other spans is merged
    with them into one span of the leaked value's type."""
    out = list(spans)
    for sid in leaked:
        src = next((s for s in out if s["id"] == sid), None) or next(s for s in spans if s["id"] == sid)
        pat = _leak_pattern(src["text"])
        for m in pat.finditer(text):
            hit = [s for s in out if s["start"] < m.end() and m.start() < s["end"]]
            if any(s["start"] <= m.start() and s["end"] >= m.end() for s in hit):
                continue
            a = min([m.start()] + [s["start"] for s in hit])
            b = max([m.end()] + [s["end"] for s in hit])
            out = [s for s in out if s not in hit]
            out.append({"id": f"r{len(out):04d}", "entity_type": src["entity_type"], "start": a, "end": b,
                        "text": text[a:b], "score": 1.0, "recognizer": "katip_repair",
                        "explanation": "covers a value that was still readable"})
    return sorted(out, key=lambda s: s["start"])


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).casefold()


def render(text: str, spans: list[dict], style: str, labels: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Replace spans by placeholders. style "label": "[AD SOYAD-1]", the same placeholder for the same value
    (case and spacing ignored), reversible with the returned mapping. style "block": "██████"."""
    counters: dict[str, int] = defaultdict(int)
    keys: dict[str, str] = {}
    mapping: dict[str, str] = {}
    out, pos = [], 0
    for sp in sorted(spans, key=lambda s: (s["start"], -s["end"])):
        if sp["start"] < pos:
            continue
        out.append(text[pos:sp["start"]])
        if style == "block":
            out.append(BLOCK * 6)
        else:
            key = f"{sp['entity_type']}|{_norm(sp['text'])}"
            if key not in keys:
                counters[sp["entity_type"]] += 1
                label = f"[{tr_upper(labels.get(sp['entity_type'], sp['entity_type']))}-{counters[sp['entity_type']]}]"
                keys[key] = label
                mapping[label] = sp["text"].strip()
            out.append(keys[key])
        pos = sp["end"]
    out.append(text[pos:])
    return "".join(out), mapping


def mask_safely(text: str, spans: list[dict], style: str, labels: dict[str, str]) -> tuple[str, list[dict], dict[str, str]]:
    """Mask, check that no detected value is still readable, repair and re-check (3 rounds), else LeakError."""
    for _ in range(3):
        leaked = leaks(text, spans)
        if not leaked:
            masked, mapping = render(text, spans, style, labels)
            return masked, spans, mapping
        spans = repair(text, spans, leaked)
    bad = [s for s in spans if s["id"] in set(leaks(text, spans))]
    raise LeakError(sorted({s["entity_type"] for s in bad}), sorted({text.count("\n", 0, s["start"]) + 1 for s in bad}))


def restore(text: str, mapping: dict[str, str]) -> str:
    """Put the original values back in place of the placeholders (e.g. in an AI model's answer)."""
    if not mapping:
        return text
    pat = re.compile("|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
    return pat.sub(lambda m: mapping[m.group(0)], text)
