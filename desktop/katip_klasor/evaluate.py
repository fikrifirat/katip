"""Test Katip on a firm's real documents, on this computer, and share only counts.

A lawyer opens a file in the review screen, turns on "Test", reads the whole document and marks
  * masks that are wrong (any masked value, not only the flagged ones), and
  * values Katip missed (select the text, pick its type).
Flag decisions count too: "Maskeleme" on a masked value is a false mask, "Maskele" on a missed
candidate is a miss. When the lawyer ticks "I read the whole document", the file counts.

Scores are for the detector as it ran, before the lawyer's review:
  predicted = the values Katip masked on its own (words the lawyer added with "Her zaman maskele" are
              misses, not detections)
  false     = predicted values the lawyer marked wrong
  missed    = every occurrence of a value the lawyer says should have been masked and wasn't
  found     = predicted - false

The export holds, per file: document type, format, OCR or not, profile, model, engine version, a size
bucket and per-type counts. Never a value, a file name, a case name or a position in the text.
"""
from __future__ import annotations

import json
import re
import time

from katip_kalkan import ner

from . import __version__, pipeline, store

DOC_TYPES = {
    "dilekce": "Dilekçe", "karar": "Karar / ara karar", "sozlesme": "Sözleşme", "rapor": "Bilirkişi / sağlık raporu",
    "tutanak": "Tutanak / ifade", "yazisma": "Yazışma / e-posta / ihtarname", "form": "Kimlik / resmî form",
    "vekaletname": "Vekâletname", "diger": "Diğer",
}
SIZE_BUCKETS = [(2_000, "<2k"), (10_000, "2k-10k"), (50_000, "10k-50k"), (10**12, ">50k")]


def empty() -> dict:
    return {"on": False, "complete": False, "doc_type": "", "wrong": [], "missed": [], "at": None}


def _ev(job: dict) -> dict:
    ev = job.get("eval") or empty()
    for k, v in empty().items():
        ev.setdefault(k, v)
    job["eval"] = ev
    return ev


def update(case: str, key: str, change: dict) -> dict:
    """change: on, complete, doc_type, wrong_add/wrong_remove ({type, start, end}), missed_add ({type, start, end}),
    missed_remove (index). Returns the job."""
    with pipeline._work_lock:
        jobs = store.load_jobs(case)
        job = jobs[key]
        ev = _ev(job)
        if "on" in change:
            ev["on"] = bool(change["on"])
        if "complete" in change:
            ev["complete"] = bool(change["complete"])
        if "doc_type" in change:
            if change["doc_type"] not in DOC_TYPES and change["doc_type"] != "":
                raise ValueError("unknown document type")
            ev["doc_type"] = change["doc_type"]
        for op in ("wrong_add", "wrong_remove"):
            if op in change:  # {type, start, end} of a masked value: every occurrence of that value counts
                w = change[op]
                a, b = int(w["start"]), int(w["end"])
                if not (0 <= a < b <= len(job["text"])):
                    raise ValueError("bad span")
                item = [str(w["type"]), pipeline.norm(job["text"][a:b])]
                if op == "wrong_add" and item not in ev["wrong"]:
                    ev["wrong"].append(item)
                elif op == "wrong_remove":
                    ev["wrong"] = [x for x in ev["wrong"] if x != item]
        if "missed_add" in change:
            if job.get("status") == "released":
                raise ValueError("Bu dosya maskeli klasöre kondu. Kaçan değeri işaretlemek için önce yeniden işleyin.")
            m = change["missed_add"]
            a, b, t = int(m["start"]), int(m["end"]), str(m["type"])
            text = job["text"]
            while a < b and text[a].isspace():
                a += 1
            while b > a and text[b - 1].isspace():
                b -= 1
            if not (0 <= a < b <= len(text)) or b - a > 200:
                raise ValueError("bad selection")
            ev["missed"].append({"type": t, "start": a, "end": b})
        if "missed_remove" in change:
            del ev["missed"][int(change["missed_remove"])]
        ev["at"] = time.time()
        store.save_jobs(case, jobs)
        return job


def _predicted(job: dict) -> list[dict]:
    return [s for s in job.get("spans", []) if s.get("recognizer") != "katip_term"]


def score_job(job: dict) -> dict:
    """Per-type found / false / missed for one file, from the lawyer's marks and flag decisions."""
    ev = _ev(job)
    text = job["text"]
    pred = _predicted(job)
    wrong = {tuple(w) for w in ev["wrong"]}
    for f in job.get("flags", []):
        if f["kind"] in ("unsure", "lone") and f["decision"] == "keep":
            wrong.add((f["type"], pipeline.norm(f["value"])))
    found: dict[str, int] = {}
    false: dict[str, int] = {}
    for s in pred:
        bucket = false if (s["entity_type"], pipeline.norm(s["text"])) in wrong else found
        bucket[s["entity_type"]] = bucket.get(s["entity_type"], 0) + 1

    # misses: every unmasked occurrence of a value the lawyer says should be masked
    miss_vals: dict[tuple, str] = {}
    for m in ev["missed"]:
        miss_vals[(m["type"], pipeline.norm(text[m["start"]:m["end"]]))] = text[m["start"]:m["end"]]
    for f in job.get("flags", []):
        if f["kind"] == "missed" and f["decision"] == "mask":
            miss_vals[(f["type"], pipeline.norm(f["value"]))] = f["value"]
    for s in job.get("spans", []):
        if s.get("recognizer") == "katip_term":
            miss_vals[("TERM", pipeline.norm(s["text"]))] = s["text"]
    hit = [s for s in pred if (s["entity_type"], pipeline.norm(s["text"])) not in wrong]
    missed: dict[str, int] = {}
    seen: set[tuple[int, int]] = set()
    for (t, _), value in miss_vals.items():
        for a, b in pipeline._occurrences(text, value):
            if (a, b) in seen or pipeline._overlaps({"start": a, "end": b}, hit):
                continue
            seen.add((a, b))
            missed[t] = missed.get(t, 0) + 1
    return {"found": found, "false": false, "missed": missed}


def _size(n: int) -> str:
    return next(label for limit, label in SIZE_BUCKETS if n < limit)


def record(job: dict) -> dict:
    ev = _ev(job)
    return {"doc_type": ev["doc_type"] or "diger", "format": job.get("kind"), "ocr": bool(job.get("ocr")),
            "profile": job.get("profile"), "size": _size(len(job.get("text", ""))), **score_job(job)}


def _add(dst: dict, src: dict) -> None:
    for k, v in src.items():
        dst[k] = dst.get(k, 0) + v


def metrics(found: int, false: int, missed: int) -> dict:
    recall = found / (found + missed) if found + missed else None
    precision = found / (found + false) if found + false else None
    f2 = (5 * precision * recall / (4 * precision + recall)) if recall and precision else (0.0 if recall == 0 else None)
    r = lambda x: None if x is None else round(100 * x, 1)  # noqa: E731
    return {"found": found, "false": false, "missed": missed, "recall": r(recall), "precision": r(precision), "f2": r(f2)}


def report(cases: list[str]) -> dict:
    """All completed test files of these cases, as counts only."""
    files = []
    for case in cases:
        for job in store.load_jobs(case).values():
            ev = job.get("eval") or {}
            if ev.get("on") and ev.get("complete") and job.get("status") != "error":
                files.append(record(job))
    files.sort(key=lambda f: (f["doc_type"], f["format"] or "", f["size"]))  # no order that hints at a case
    by_type: dict[str, dict] = {}
    for f in files:
        for part in ("found", "false", "missed"):
            for t, n in f[part].items():
                by_type.setdefault(t, {"found": 0, "false": 0, "missed": 0})[part] += n
    tot = {"found": 0, "false": 0, "missed": 0}
    for v in by_type.values():
        _add(tot, v)
    return {
        "katip_eval": 1,
        "made": time.strftime("%Y-%m-%d"),
        "app": f"katip-klasor {__version__}",
        "model": ner.describe(),
        "files": len(files),
        "total": metrics(**tot),
        "by_type": {t: metrics(**v) for t, v in sorted(by_type.items())},
        "documents": files,
        "note": "Sayılar yalnızca bu bilgisayarda, avukatın işaretlerinden hesaplandı. Değer, dosya adı ya da dava adı "
                "içermez. · Counts only, computed on this computer from the lawyer's marks. No values, file names or "
                "case names.",
    }


def check_no_values(rep: dict, job_texts: list[str]) -> None:
    """Refuse to export if any string in the report is a value from the documents (belt and braces)."""
    blob = json.dumps(rep, ensure_ascii=False)
    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', blob)
    allowed = set(DOC_TYPES) | {"<2k", "2k-10k", "10k-50k", ">50k"}
    for s in strings:
        if s in allowed or len(s) < 4:
            continue
        if any(s in t for t in job_texts) and not re.fullmatch(r"[A-Z_]+|[a-z_]+", s):
            raise ValueError("rapor belgeden bir değer içeriyor; dışa aktarılmadı")
