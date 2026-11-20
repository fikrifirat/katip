"""Mask text with numbered placeholders ([NAAM-1], [BSN-1]) and restore them later.

The value table stays on this computer (a JSON file next to the output, or wherever --vault points);
only the masked text should ever go to a cloud model."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .labels import tag
from .recognizers import detect


def mask(text, spans=None, **kw):
    """Returns (masked_text, table, spans). Same value -> same placeholder; flag-only spans stay readable."""
    spans = detect(text, **kw) if spans is None else spans
    table, rev, counters, out, pos = {}, {}, {}, [], 0
    for s in spans:
        if s["flag_only"]:
            continue
        val = s["text"]
        key = (s["entity_type"], re.sub(r"\s+", " ", s.get("ref") or val).strip().lower())
        if key not in rev:
            t = tag(s["entity_type"])
            counters[t] = counters.get(t, 0) + 1
            ph = f"[{t}-{counters[t]}]"
            rev[key] = ph
            table[ph] = s.get("ref") or val
        out.append(text[pos:s["start"]])
        out.append(rev[key])
        pos = s["end"]
    out.append(text[pos:])
    return "".join(out), table, spans


def restore(text, table):
    for ph in sorted(table, key=len, reverse=True):
        text = text.replace(ph, table[ph])
    return text


def save_table(table, path):
    Path(path).write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")


def load_table(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
