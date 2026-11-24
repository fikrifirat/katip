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
import time

from .match import MATCH, REVIEW, ListIndex, TextIndex
from .net import Blocked, PoliteClient
from .normalize import fold, id_tokens, mask_ids, vkn_ok
from .sources import gazette, ilan, masak
from .store import Store, now

SOURCES = ("masak", "ilan", "gazette")
LISTS = list(masak.LISTS)
_PRIVATE_FIELDS = ("tckn_vkn", "anne_adı", "baba_adı")
_cache: dict = {}

HOW_TO_READ = ("score is name similarity, not probability. band 'match' >= %.2f, 'review' >= %.2f. Confirm every hit "
               "against source_url. No hit means no close name in these sources as of data_as_of; it is not a "
               "clearance. Checked here: MASAK asset-freeze lists (6415 art. 5, 6, 7; 7262), ilan.gov.tr notices and "
               "Ticaret Sicili Gazetesi pages you looked up. NOT checked: US OFAC, EU, UK OFSI and other UN sanctions "
               "lists, PEP lists, court and enforcement records." % (MATCH, REVIEW))



_NO_PLAYWRIGHT = {"status": "unavailable", "error": "Playwright is not installed on this computer: pip install playwright "
                  "(it uses Google Chrome; the Claude Desktop extension installs it on first start)"}
_NO_BROWSER = {"status": "no_browser", "error": "Google Chrome is not installed on this computer. Install it from "
               "https://www.google.com/chrome/ and try again (or run: python -m playwright install chromium)."}


def _no_browser(e: Exception) -> bool:
    """Neither Google Chrome nor Playwright's own Chromium is on this computer."""
    msg = str(e)
    return "Executable doesn't exist" in msg or "is not found at" in msg or "Chromium distribution 'chrome'" in msg

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
         **({"gazette_issue": r["issue"], "gazette_page": r.get("gazette_page", ""),
            "citation": gazette_citation({"date": r.get("date", ""), "issue": r["issue"], "page": r.get("gazette_page", "")}),
            "verify": GAZETTE_VERIFY} if source == "gazette" and r.get("issue") else {}),
         "gazette_url": r.get("gazette_url", ""), "notes": list(h.reasons)}
    if r.get("listing_only"):
        d["notes"].append("listed in the Gazette site's search results only: the gazette page was not read, its text "
                          "is unknown; cite it as listed (issue/page) and verify on ticaretsicil.gov.tr")
        d["citation"] = r.get("url", "")
    elif r.get("full_text") is False and not any("title/summary" in n for n in d["notes"]):
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
        try:
            docs, info = ilan_browser.search(target, max_ads=min(max_ads, 20), headed=headed)
        except Exception as e:  # noqa: BLE001
            if "ERR_CERT" not in str(e):
                raise
            # ilan.gov.tr sends no intermediate certificate; Chrome usually fetches it, once it did not
            time.sleep(10)
            docs, info = ilan_browser.search(target, max_ads=min(max_ads, 20), headed=headed)
    except ImportError:
        return _NO_PLAYWRIGHT
    except Exception as e:  # noqa: BLE001
        if _no_browser(e):
            return _NO_BROWSER
        st.log_failure("ilan", started, "tls_error" if "ERR_CERT" in str(e) else "error", {"error": repr(e)[:300]})
        return {"status": "tls_error" if "ERR_CERT" in str(e) else "error", "error": repr(e)[:300]}
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
    # re-adding a file replaces its old notices, also when the file's bytes changed (saved again)
    files_done = {str(r.get("url", "")).split("#", 1)[0] for r in new}
    keep = [r for r in st.records("gazette") if str(r.get("url", "")).split("#", 1)[0] not in files_done]
    stats = st.replace_source("gazette", keep + new, {"files": [str(f) for f in files]}, started)
    return {"status": "ok", "files": len(files), "notices": len(new), "store_records": stats["n"]}


def gazette_lookup(target: str, office: str, max_pages: int = 3, court: bool = False, store: Store | None = None) -> dict:
    """One named target on the Ticaret Sicili Gazetesi, through the lawyer's own login on this computer.

    The first run opens Chrome on a new, empty profile for the lawyer's e-Devlet login; the site's
    cookies are then kept encrypted for a few hours (KATIP_TSG_SESSION_HOURS, default 8) and later
    runs search headless. Saves up to ``max_pages`` free gazette pages and reads them with OCR.
    """
    from pathlib import Path

    from .sources import gazette_browser
    from .store import home

    try:
        saved, info = gazette_browser.lookup(target, office, out_dir=home() / "tsg", max_pages=min(max_pages, 5),
                                            court=court)
    except ImportError:
        return _NO_PLAYWRIGHT
    except Exception as e:  # noqa: BLE001
        if _no_browser(e):
            return _NO_BROWSER
        return {"status": "error", "error": repr(e)[:300],
                "note": "the run stopped; Katip tried to log out on the site and deleted the browser profile"}
    listed = info.get("notices", [])
    # Pages saved by an earlier lookup were not asked for again. Those already in the store count as
    # read; one that is on disk but not in the store is read now.
    st0 = store or Store()
    in_store = {str(r.get("url", "")).split("#", 1)[0] for r in st0.records("gazette") if r.get("kind") == "notice"}
    cached = [Path(c) for c in info.get("cached", [])]
    fetched = len(saved)
    saved = list(saved) + [c for c in cached if str(c) not in in_store]
    read = {p.name for p in saved} | {c.name for c in cached}
    out = {"status": "blocked" if info.get("blocked") and not read else "ok", "results_on_site": info.get("results"),
           "saved_pages": fetched, "pages_from_earlier_lookups": len(cached), "listed_only": sum(1 for n in listed if n["file"] not in read),
           "login": info.get("session"), "logged_out": info.get("logged_out"), "blocked": info.get("blocked"),
           **({"security_code": info["security_code"]} if info.get("security_code") else {}),
           **({"site_requests": info["site_requests"]} if info.get("site_requests") else {}),
           "notices_on_site": [{**{k: n[k] for k in ("date", "issue", "page", "type", "unvan", "row")},
                                "read": n["file"] in read, "citation": gazette_citation(n)} for n in listed],
           "verify": GAZETTE_VERIFY,
           "how_to_read": ("notices_on_site is the site's full result list. read=false rows were listed by the site "
                           "but their gazette page was not downloaded, so their text is unknown: report them as "
                           "listed, not as read. 'row' is the site's own table row, verbatim; do not infer facts "
                           "(share structure, officers) that are not in it.")}
    out["court_notices"] = ("included (court and bankruptcy-office notices)" if court else
                            "NOT included: court notices (konkordato, iflas) are a separate search on the site; "
                            "call dd_gazette_lookup again with court=true to list them")
    if saved:
        ing = add_gazette(saved, use_ocr=True, store=store)
        out["notices"] = ing.get("notices")
        if ing.get("status") != "ok":
            out.update(status=ing["status"], error=ing.get("error"))
    if listed:
        _keep_listing(listed, target, store)
    out["next"] = "call dd_screen with the same name: it returns read notices and listed-only rows"
    return out


GAZETTE_VERIFY = ("No public link per notice: verify on www.ticaretsicil.gov.tr > İlan Görüntüleme (e-Devlet login) "
                  "with the registry office and trade name, or by issue number and page.")


def gazette_citation(n: dict) -> str:
    d = n.get("date", "")
    dt = ".".join(reversed(d.split("-"))) if d else ""
    return f"TTSG {dt}, sayı {n.get('issue', '')}, s. {n.get('page', '')}".strip()


def _keep_listing(listed: list[dict], target: str, store: Store | None) -> None:
    """Every row of the site's result list becomes a record, so dd_screen shows all of them; rows whose
    page Katip has read are shown through the read notices instead."""
    st, started = store or Store(), now()
    recs = st.records("gazette")
    pages_read = {(r.get("issue"), r.get("gazette_page")) for r in recs if r.get("kind") == "notice"}
    new = {}
    for n in listed:
        if (n["issue"], n["page"]) in pages_read:
            continue
        rid = f"gazette:list:{n['issue']}:{n['page']}:{fold(n['unvan'])[:60]}"
        new[rid] = {"rid": rid, "source": "gazette", "kind": "listing", "title": n["unvan"], "names": [n["unvan"]],
                    "text": " · ".join([n["unvan"], n.get("type", ""), *[c for c in n.get("row") or [] if c != n["unvan"]]]), "issue": n["issue"],
                    "gazette_page": n["page"], "date": n["date"], "full_text": False, "listing_only": True,
                    "decision": n.get("type", ""), "url": gazette_citation(n), "sicil_no": n.get("sicil_no", ""),
                    "office": n.get("office", "")}
    keep = [r for r in recs if r["rid"] not in new
            and not (r.get("kind") == "listing" and (r.get("issue"), r.get("gazette_page")) in pages_read)]
    st.replace_source("gazette", keep + list(new.values()), {"listing_for": target}, started)


def gazette_logout() -> dict:
    """Log out of the Ticaret Sicili Gazetesi now and delete the kept login."""
    from .sources import gazette_browser
    try:
        return gazette_browser.logout()
    except ImportError:
        gazette_browser.session_delete()
        return {"status": "ok", "note": "Playwright is missing, so the site was not told; the kept login was deleted"}
