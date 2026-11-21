"""Katip DD as an MCP server: deterministic search over the local index, no LLM inside.

    python lab/dd/mcp_dd.py          # stdio MCP server

Claude Desktop / Claude Code config:
    {"mcpServers": {"katip-dd": {"command": "python3", "args": ["/path/to/katip/lab/dd/mcp_dd.py"]}}}

Design rule (from fikri and Uğur, 21 Nov 2026): the tool returns the exact source record and
the official link, nothing summarised or paraphrased. An agent may write the DD report, but
every claim in it must point at a record this tool returned. Scores are string-similarity
scores, not probabilities, and "no hit" is not a clearance.

KVKK: the index holds personal data from public lists (ID numbers, parents' names). Running
this for yourself on your own computer is one thing. Serving it to another firm's agents
makes the operator a data controller or processor for that use (KVKK art. 5/2 exceptions,
purpose limitation, a processing agreement, VERBİS check). Not solved here; see README.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "connector"))

from katip_kalkan.mcp_proto import Server, Tool  # noqa: E402
from match import MATCH, REVIEW, ListIndex, TextIndex  # noqa: E402
from store import Store, now  # noqa: E402

SOURCES = ("masak", "ilan", "gazette")
_cache: dict = {}


def _indexes(st: Store):
    """Rebuild the in-memory index only when the store changed."""
    key = tuple((r["id"]) for r in st.runs(1))
    if _cache.get("key") != key:
        _cache.clear()
        _cache["key"] = key
        _cache["masak"] = ListIndex(st.records("masak"))
        for s in ("ilan", "gazette"):
            _cache[s] = TextIndex(st.records(s))
    return _cache


def _date(rec: dict) -> str:
    for k in ("date", "decision"):
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})|(\d{1,2})[./](\d{1,2})[./](\d{4})", rec.get(k) or "")
        if m:
            if m.group(1):
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            return f"{m.group(6)}-{int(m.group(5)):02d}-{int(m.group(4)):02d}"
    return ""


def _out(source: str, h, verbatim: bool) -> dict:
    r = h.record
    d = {"record_id": r["rid"], "source": source, "list": r.get("list", ""), "score": h.score, "band": h.band,
         "matched_on": h.matched, "listed_name": (r.get("names") or [r.get("title", "")])[0],
         "other_names": (r.get("names") or [])[1:], "id_numbers": [i for i in r.get("ids", []) if i],
         "birth": " ".join(str(r.get("birth", "")).split()), "nationality": r.get("nationality", ""),
         "organisation": r.get("organisation", ""), "decision": r.get("decision", ""), "date": _date(r),
         "source_url": r.get("url", ""), "gazette_url": r.get("gazette_url", ""), "notes": h.reasons}
    if r.get("csv_only"):
        d["notes"] = [*d["notes"], "row found only in MASAK's CSV file, not in its search data"]
    if verbatim:
        d["source_record"] = r.get("raw") or {"text": r.get("text", "")}
    return d


def dd_screen(name: str = "", birth_year: str = "", id_number: str = "", sources: list | None = None,
              lists: list | None = None, date_from: str = "", date_to: str = "", min_band: str = "review",
              limit: int = 10, verbatim: bool = True) -> dict:
    if not name and not id_number:
        raise ValueError("give a name or an id_number")
    st = Store()
    ix = _indexes(st)
    floor = {"match": MATCH, "review": REVIEW, "weak": 0.75}.get(min_band, REVIEW)
    want = [s for s in (sources or SOURCES) if s in SOURCES]
    hits = []
    if "masak" in want:
        hits += [("masak", h) for h in ix["masak"].search(name, birth=birth_year, id_no=id_number, limit=50, floor=floor)]
    for s in ("ilan", "gazette"):
        if s in want and name:
            hits += [(s, h) for h in ix[s].search(name, limit=50, floor=max(floor, REVIEW))]
    rows = [_out(s, h, verbatim) for s, h in hits]
    if lists:
        rows = [r for r in rows if r["list"] in lists or r["source"] != "masak"]
    if date_from:
        rows = [r for r in rows if r["date"] and r["date"] >= date_from]
    if date_to:
        rows = [r for r in rows if r["date"] and r["date"] <= date_to]
    rows.sort(key=lambda r: -r["score"])
    status = {s: {"data_as_of": (st.last_ok(s) or {}).get("finished"), "records": len(st.records(s))} for s in want}
    return {"query": {"name": name, "birth_year": birth_year, "id_number": bool(id_number), "sources": want},
            "checked_at": now(), "sources_status": status, "hits": rows[:limit],
            "how_to_read": ("score is name similarity, not probability. band 'match' >= %.2f, 'review' >= %.2f. "
                            "Confirm every hit against source_url. No hit means no close name in these sources "
                            "as of data_as_of; it is not a clearance." % (MATCH, REVIEW))}


def dd_record(record_id: str) -> dict:
    src = record_id.split(":", 1)[0]
    src = "masak" if src.startswith(("6415", "7262")) else src
    for r in Store().records(src if src in SOURCES else None):
        if r["rid"] == record_id:
            return {k: v for k, v in r.items()}
    raise KeyError(f"no record {record_id}")


def dd_sources() -> dict:
    st = Store()
    out = {}
    for s in SOURCES:
        last = st.last_ok(s)
        fails = [r for r in st.runs(50) if r["source"] == s and r["status"] != "ok"][:1]
        out[s] = {"records": len(st.records(s)), "data_as_of": (last or {}).get("finished"),
                  "lists": json.loads((last or {}).get("detail") or "{}").get("lists"),
                  "last_failure": ({"at": fails[0]["finished"], "status": fails[0]["status"],
                                    "error": json.loads(fails[0]["detail"] or "{}").get("error") or json.loads(fails[0]["detail"] or "{}").get("blocked")}
                                   if fails else None)}
    return out


SCREEN_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Person or company name, any casing, with or without Turkish letters."},
        "birth_year": {"type": "string", "description": "Optional. A different year on the list lowers the score."},
        "id_number": {"type": "string", "description": "Optional TCKN/VKN/YKN/passport number; exact match only."},
        "sources": {"type": "array", "items": {"type": "string", "enum": list(SOURCES)}},
        "lists": {"type": "array", "items": {"type": "string", "enum": ["6415-m5-bmgk", "6415-m6-yabanci", "6415-m7-ic", "7262-kitle-imha"]}},
        "date_from": {"type": "string", "description": "YYYY-MM-DD, on decision or notice date"},
        "date_to": {"type": "string", "description": "YYYY-MM-DD"},
        "min_band": {"type": "string", "enum": ["match", "review", "weak"], "default": "review"},
        "limit": {"type": "integer", "default": 10, "maximum": 50},
        "verbatim": {"type": "boolean", "default": True, "description": "Include the source row exactly as published."},
    },
}

INSTRUCTIONS = ("Katip DD searches a local index of Turkish public lists (MASAK asset freezes under Law 6415 "
                "art. 5/6/7 and Law 7262; Ticaret Sicili Gazetesi and ilan.gov.tr notices the user has added). "
                "Quote hits exactly as returned, with source_url. Never infer that a person is listed from a "
                "'review' hit without saying it needs checking. Never present 'no hits' as a clearance.")


def build() -> Server:
    ro = {"readOnlyHint": True, "openWorldHint": False}
    return Server("katip-dd", "0.1.0", INSTRUCTIONS, [
        Tool("dd_screen", "Screen a name", "Search a person or company in the local DD index. Returns exact source "
             "records with official links and match scores. Deterministic: no summarising.", SCREEN_SCHEMA, dd_screen, ro),
        Tool("dd_record", "Get one record", "Return one record exactly as stored, by record_id from dd_screen.",
             {"type": "object", "properties": {"record_id": {"type": "string"}}, "required": ["record_id"]}, dd_record, ro),
        Tool("dd_sources", "Source freshness", "What each source holds, when it was last fetched, and its last failure.",
             {"type": "object", "properties": {}}, dd_sources, ro),
    ])


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=os.environ.get("KATIP_LOG", "WARNING"))
    server = build()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            batch = msg if isinstance(msg, list) else [msg]
            resps = [r for r in (server.handle(m) for m in batch) if r is not None]
            resp = resps if isinstance(msg, list) else (resps[0] if resps else None)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
