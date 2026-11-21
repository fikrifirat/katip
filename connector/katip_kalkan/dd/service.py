"""Katip DD operations shared by the CLI (lab/dd/dd.py), the Kalkan MCP server and the relay.

Deterministic: every hit is a stored source record with its official link and a similarity
score. Nothing is summarised.

Redaction (``redact=True``, the default for AI hosts): listed people's ID numbers, parents'
names and any 11-digit number in a notice are removed before the result reaches the model.
The listed name, dates, list, decision and links stay, because the lawyer asked about that
name. The lawyer opens ``source_url`` for the full record. ``redact=False`` is for the
lawyer's own terminal.
"""
from __future__ import annotations

import json
import re

from .match import MATCH, REVIEW, ListIndex, TextIndex
from .net import Blocked, PoliteClient
from .normalize import id_tokens, mask_ids, vkn_ok
from .sources import gazette, ilan, masak
from .store import Store, now

SOURCES = ("masak", "ilan", "gazette")
LISTS = list(masak.LISTS)
_PRIVATE_FIELDS = ("tckn_vkn", "anne_adı", "baba_adı")
_cache: dict = {}

HOW_TO_READ = ("score is name similarity, not probability. band 'match' >= %.2f, 'review' >= %.2f. Confirm every hit "
               "against source_url. No hit means no close name in these sources as of data_as_of; it is not a "
               "clearance." % (MATCH, REVIEW))


def _indexes(st: Store) -> dict:
    """Rebuild the in-memory indexes only when the store changed."""
    key = tuple(r["id"] for r in st.runs(1))
    if _cache.get("key") != key or _cache.get("path") != str(st.path):
        _cache.clear()
        _cache.update(key=key, path=str(st.path), masak=ListIndex(st.records("masak")),
                      ilan=TextIndex(st.records("ilan")), gazette=TextIndex(st.records("gazette")))
    return _cache


def _company_vkn(rec: dict, value: str) -> bool:
    """A listed company's 10-digit tax number stays visible; a person's numbers never do."""
    toks = id_tokens(value)
    return rec.get("kind") != "person" and bool(toks) and all(vkn_ok(t) for t in toks)


def _date(rec: dict) -> str:
    for k in ("date", "decision"):
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})|(\d{1,2})[./](\d{1,2})[./](\d{4})", rec.get(k) or "")
        if m:
            if m.group(1):
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            return f"{m.group(6)}-{int(m.group(5)):02d}-{int(m.group(4)):02d}"
    return ""


def _hit(source: str, h, verbatim: bool, redact: bool, id_number: str) -> dict:
    r = h.record
    ids = [i for i in r.get("ids", []) if i]
    d = {"record_id": r["rid"], "source": source, "list": r.get("list", ""), "score": h.score, "band": h.band,
         "matched_on": h.matched, "listed_name": (r.get("names") or [r.get("title", "")])[0],
         "other_names": (r.get("names") or [])[1:], "birth": " ".join(str(r.get("birth", "")).split()),
         "nationality": r.get("nationality", ""), "organisation": r.get("organisation", ""),
         "decision": r.get("decision", ""), "date": _date(r), "source_url": r.get("url", ""),
         **({"gazette_issue": r["issue"], "gazette_page": r.get("gazette_page", "")} if source == "gazette" and r.get("issue") else {}),
         "gazette_url": r.get("gazette_url", ""), "notes": list(h.reasons)}
    if r.get("full_text") is False and not any("title/summary" in n for n in d["notes"]):
        d["notes"].append("title/summary only: notice page was not opened, check the full notice")
    if r.get("csv_only"):
        d["notes"].append("row found only in MASAK's CSV file, not in its search data")
    if redact:
        d["notes"] = [mask_ids(n) for n in d["notes"]]
        if d["matched_on"].startswith("ID "):
            d["matched_on"] = "ID number"
        if id_number:
            want = set(id_tokens(id_number))
            d["id_number_matches"] = any(set(id_tokens(i)) & want for i in ids)
        d["id_numbers_on_record"] = len(ids)
    else:
        d["id_numbers"] = ids
    if verbatim:
        src = dict(r.get("raw") or {"text": r.get("text", "")})
        if redact:
            for k in _PRIVATE_FIELDS:
                if src.get(k) and not (k == "tckn_vkn" and _company_vkn(r, src[k])):
                    src[k] = "[gizlendi]"
            if "text" in src:
                src["text"] = mask_ids(src["text"])
        d["source_record"] = src
    return d


def screen(name: str = "", birth_year: str = "", id_number: str = "", sources: list | None = None,
           lists: list | None = None, date_from: str = "", date_to: str = "", min_band: str = "review",
           limit: int = 10, verbatim: bool = True, redact: bool = True, store: Store | None = None) -> dict:
    if not (name or "").strip() and not (id_number or "").strip():
        raise ValueError("give a name or an id_number")
    st = store or Store()
    ix = _indexes(st)
    floor = {"match": MATCH, "review": REVIEW, "weak": 0.75}.get(min_band, REVIEW)
    want = [s for s in (sources or SOURCES) if s in SOURCES]
    hits = []
    if "masak" in want:
        hits += [("masak", h) for h in ix["masak"].search(name, birth=birth_year, id_no=id_number, limit=50, floor=floor)]
    for s in ("ilan", "gazette"):
        if s in want and name:
            hits += [(s, h) for h in ix[s].search(name, limit=50, floor=max(floor, REVIEW))]
    rows = [_hit(s, h, verbatim, redact, id_number) for s, h in hits]
    if lists:
        rows = [r for r in rows if r["list"] in lists or r["source"] != "masak"]
    if date_from:
        rows = [r for r in rows if r["date"] and r["date"] >= date_from]
    if date_to:
        rows = [r for r in rows if r["date"] and r["date"] <= date_to]
    rows.sort(key=lambda r: -r["score"])
    status = {s: {"data_as_of": (st.last_ok(s) or {}).get("finished"), "records": len(st.records(s))} for s in want}
    empty = [s for s, v in status.items() if not v["records"]]
    return {"query": {"name": name, "birth_year": birth_year, "id_number_given": bool(id_number), "sources": want},
            "checked_at": now(), "sources_status": status, "hits": rows[:limit],
            "not_covered": empty, "how_to_read": HOW_TO_READ}


def record(record_id: str, redact: bool = True, store: Store | None = None) -> dict:
    st = store or Store()
    src = record_id.split(":", 1)[0]
    src = "masak" if src.startswith(("6415", "7262")) else src
    for r in st.records(src if src in SOURCES else None):
        if r["rid"] == record_id:
            out = dict(r)
            if redact:
                out.pop("ids", None)
                raw = dict(out.get("raw") or {})
                for k in _PRIVATE_FIELDS:
                    if raw.get(k) and not (k == "tckn_vkn" and _company_vkn(r, raw[k])):
                        raw[k] = "[gizlendi]"
                if raw:
                    out["raw"] = raw
                if out.get("text"):
                    out["text"] = mask_ids(out["text"])
            return out
    raise KeyError(f"no record {record_id}")


def sources_status(store: Store | None = None) -> dict:
    st = store or Store()
    out = {}
    for s in SOURCES:
        last = st.last_ok(s)
        fails = [r for r in st.runs(50) if r["source"] == s and r["status"] != "ok"][:1]
        fd = json.loads(fails[0]["detail"] or "{}") if fails else {}
        out[s] = {"records": len(st.records(s)), "data_as_of": (last or {}).get("finished"),
                  "lists": json.loads((last or {}).get("detail") or "{}").get("lists"),
                  "last_failure": ({"at": fails[0]["finished"], "status": fails[0]["status"],
                                    "error": fd.get("error") or fd.get("blocked")} if fails else None)}
    out["how_to_add"] = {"masak": "dd_update (fetches the four lists, about 10 polite requests)",
                         "ilan": "dd_ilan_lookup with one named target (opens ilan.gov.tr in a real browser here)",
                         "gazette": "save Ticaret Sicili Gazetesi PDFs and run: katip-kalkan dd add-gazette FOLDER"}
    return out


def update(source: str = "masak", interval: float = 2.0, store: Store | None = None) -> dict:
    """Fetch one source. Only MASAK has a fetcher that works from any connection."""
    fetchers = {"masak": masak.fetch, "ilan": ilan.fetch}
    if source not in fetchers:
        raise ValueError(f"no fetcher for {source}; ilan.gov.tr uses dd_ilan_lookup, the Gazette uses add-gazette")
    st, client, started = store or Store(), PoliteClient(min_interval=interval), now()
    try:
        records, detail = fetchers[source](client)
    except Blocked as e:
        st.log_failure(source, started, "blocked", {"error": str(e), "log": client.log[-5:]})
        return {"source": source, "status": "blocked", "error": str(e), "changed": False}
    except Exception as e:  # noqa: BLE001
        st.log_failure(source, started, "error", {"error": repr(e)[:500], "log": client.log[-5:]})
        return {"source": source, "status": "error", "error": repr(e)[:300], "changed": False}
    stats = st.replace_source(source, records, detail, started)
    return {"source": source, "status": "ok", **stats, "data_as_of": now()}


def _merge(st: Store, source: str, new: list[dict], detail: dict, started: str) -> dict:
    keep = {d["rid"]: d for d in st.records(source)}
    keep.update({d["rid"]: d for d in new})
    return st.replace_source(source, list(keep.values()), detail, started)


def ilan_lookup(target: str, max_ads: int = 20, headed: bool = False, store: Store | None = None) -> dict:
    """One named target on ilan.gov.tr, in a real browser on this computer (Playwright)."""
    from .sources import ilan_browser

    if len((target or "").split()) < 1 or len(target.strip()) < 3:
        raise ValueError("give the name of one person or company")
    st, started = store or Store(), now()
    try:
        docs, info = ilan_browser.search(target, max_ads=min(max_ads, 20), headed=headed)
    except ImportError:
        return {"status": "unavailable", "error": "Playwright is not installed on this computer: pip install playwright "
                "(uses Google Chrome, or run: python -m playwright install chromium)"}
    if info.get("blocked"):
        st.log_failure("ilan", started, "blocked", info)
        return {"status": "blocked", "error": info["blocked"]}
    stats = _merge(st, "ilan", docs, {k: v for k, v in info.items() if k != "log"}, started)
    return {"status": "ok", "results_on_site": info.get("ads_in_results"), "kept": len(docs),
            "opened_full_text": info.get("opened"), "store_records": stats["n"],
            "next": "call dd_screen with the same name to see which notices mention it"}


def add_gazette(paths, use_ocr: bool = False, store: Store | None = None) -> dict:
    from pathlib import Path

    files = []
    for p in map(Path, paths):
        files += sorted(p.glob("*.pdf")) if p.is_dir() else [p]
    st, started = store or Store(), now()
    try:
        new = gazette.ingest(files, ocr=use_ocr)
    except ImportError as e:
        return {"status": "unavailable", "error": f"{e.name or e} is not installed. Reading Gazette PDFs needs "
                "PyMuPDF, and scanned pages need OCR: pip install 'katip-kalkan[ocr]' (or: pip install pymupdf rapidocr "
                "onnxruntime)"}
    stats = _merge(st, "gazette", new, {"files": [str(f) for f in files]}, started)
    return {"status": "ok", "files": len(files), "notices": len(new), "store_records": stats["n"]}
