"""Mask a dropped file, flag what a person should look at, release the clean copy, restore an AI answer.

Detection, the case vault and the leak check are Kalkan's (katip_kalkan.core / engine / vault), so a file
masked here and the same file masked through the Claude connector get the same placeholders.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

from katip_kalkan import core, engine, vault

from . import layout, pdf, store

TERM = "TERM"  # a word the lawyer asked to always mask
_fmt_lock = threading.Lock()
_work_lock = threading.RLock()

OCR_NOTE = ("Bu metin bir taramadan ya da fotoğraftan okunmuştur (OCR). Asıl görüntü paylaşılmadı; "
            "okuma hataları olabilir.")


class Changed(RuntimeError):
    """The file changed after it was masked: mask it again before release."""


# ---------------------------------------------------------------- helpers
def matter(case: str) -> str:
    return "klasor:" + case


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).casefold()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _counts(spans) -> dict:
    c: dict[str, int] = {}
    for s in spans:
        c[s["entity_type"]] = c.get(s["entity_type"], 0) + 1
    return c


def _labels_ready():
    _, fmt = engine.load()
    fmt.ENTITY_LABELS_TR.setdefault(TERM, "Gizli")
    return fmt


def type_label(t: str) -> str:
    _labels_ready()
    return engine.label_name(t)


def apply_model(settings: dict) -> None:
    """Pick the on-device name model (Kalkan's ner.py reads KATIP_MODEL)."""
    if not os.environ.get("KATIP_MODEL_FIXED"):
        os.environ["KATIP_MODEL"] = settings.get("model") or "base"


def read_doc(p: Path):
    """engine.read_text, plus where each PDF page starts in the text (for "s.3" in the review list)."""
    kind = engine.kind_of(p)
    if kind != "pdf":
        k, text, data, ranges, readers = engine.read_text(p)
        return k, text, data, ranges, readers, [0]
    from katip_kalkan import ocr
    import pymupdf
    data = p.read_bytes()
    parts, ranges, readers, starts, pos = [], [], [], [], 0
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            t = page.get_text()
            if len(t.strip()) < 20:  # no text layer: same rule as engine.read_text
                t, reader = ocr.ocr_page(ocr.pixmap_rgb(page.get_pixmap(dpi=ocr.DPI)))
                ranges.append((pos, pos + len(t)))
                readers.append(reader)
            starts.append(pos)
            parts.append(t)
            pos += len(t) + 2
    return "pdf", "\n\n".join(parts), data, ranges, readers, starts


def _page(starts: list[int], at: int) -> int:
    n = 1
    for i, s in enumerate(starts):
        if at >= s:
            n = i + 1
    return n


def _overlaps(s, spans) -> bool:
    return any(o["start"] < s["end"] and s["start"] < o["end"] for o in spans)


def _occurrences(text: str, term: str):
    pat = re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, term.split())) + r"(?!\w)", re.I)
    return [(m.start(), m.end()) for m in pat.finditer(text)]


def _context(text: str, s: dict, width: int = 48) -> list[str]:
    a, b = s["start"], s["end"]
    before = text[max(0, a - width):a]
    after = text[b:b + width]
    clean = lambda x: re.sub(r"\s+", " ", x)  # noqa: E731
    return [("…" if a > width else "") + clean(before).lstrip(), text[a:b], clean(after).rstrip() + ("…" if b + width < len(text) else "")]


# ---------------------------------------------------------------- detection + flags
def detect(text: str, case: str, profile: str, ocr_ranges, settings: dict):
    """-> (spans that will be masked, candidates under the threshold that were not)."""
    _labels_ready()
    v = vault.open_vault(matter(case))
    terms = (settings.get("terms") or {}).get(case, {})
    keep = {norm(t) for t in terms.get("keep", [])}
    spans = core._detect(text, v, profile, ocr_ranges)
    spans = [s for s in spans if norm(s["text"]) not in keep]
    for term in terms.get("mask", []):
        for a, b in _occurrences(text, term):
            sp = {"id": f"t{a}", "entity_type": TERM, "start": a, "end": b, "text": text[a:b], "score": 1.0,
                  "recognizer": "katip_term"}
            if not _overlaps(sp, spans):
                spans.append(sp)
    spans.sort(key=lambda s: s["start"])
    types, addr = engine.profile_types(profile)
    low = engine.detect(text, float(settings.get("low", 0.3)), types, ocr_ranges=ocr_ranges, address_detail=addr)
    cands = [c for c in low if not _overlaps(c, spans) and norm(c["text"]) not in keep and len(c["text"].strip()) > 1]
    return spans, cands


def make_flags(text: str, spans, cands, ocr_ranges, starts, settings: dict) -> list[dict]:
    unsure = float(settings.get("unsure", 0.7))
    groups: dict[tuple, dict] = {}

    def add(kind, s):
        key = (kind, s["entity_type"], norm(s["text"]))
        g = groups.get(key)
        if g:
            g["count"] += 1
            g["score"] = min(g["score"], s.get("score", 1.0))
            return
        groups[key] = {"kind": kind, "type": s["entity_type"], "type_label": type_label(s["entity_type"]),
                       "value": s["text"], "score": round(float(s.get("score", 1.0)), 2), "count": 1,
                       "context": _context(text, s), "page": _page(starts, s["start"]), "at": s["start"],
                       "decision": "mask"}

    for c in cands:
        add("missed", c)
    for s in spans:
        if s.get("recognizer") in ("katip_propagate", "katip_repair", "katip_id_context", "katip_term"):
            continue
        if s["entity_type"] == "PERSON" and len(s["text"].split()) == 1:
            add("lone", s)
        elif float(s.get("score", 1.0)) < unsure:
            add("unsure", s)
    flags = sorted(groups.values(), key=lambda f: ({"missed": 0, "lone": 1, "unsure": 2}[f["kind"]], f["at"]))
    for a, b in ocr_ranges:
        flags.append({"kind": "ocr", "type": "", "type_label": "", "value": "", "score": 1.0, "count": 1,
                      "context": ["", "", ""], "page": _page(starts, a), "at": a, "decision": "ok"})
    for i, f in enumerate(flags):
        f["id"] = f"f{i + 1}"
    return flags


def final_spans(job: dict) -> list[dict]:
    """The spans to mask after the review: drop values marked "Maskeleme", add candidates marked "Maskele"."""
    text, flags = job["text"], job["flags"]
    keep = {(f["type"], norm(f["value"])) for f in flags if f["kind"] in ("unsure", "lone") and f["decision"] == "keep"}
    add = {(f["type"], norm(f["value"])) for f in flags if f["kind"] == "missed" and f["decision"] == "mask"}
    out = [s for s in job["spans"] if (s["entity_type"], norm(s["text"])) not in keep]
    extra = [c for c in job["cands"] if (c["entity_type"], norm(c["text"])) in add and not _overlaps(c, out)]
    # every occurrence of an added value, not just the one the detector scored
    return core._propagate(text, sorted(out + extra, key=lambda s: s["start"]),
                           [(c["entity_type"], c["text"].strip()) for c in extra])


# ---------------------------------------------------------------- process
def job_key(root: Path, p: Path) -> str:
    return layout.nfc(str(p.relative_to(root / layout.INBOX)))


def process(root: Path, p: Path, settings: dict, force: bool = False) -> dict:
    """Mask one file from 1 Gelen and queue it for review (or release it, if nothing is flagged and the
    setting allows). Returns the job. The original file is only read."""
    with _work_lock:
        case = layout.case_of(root, p, layout.INBOX)
        data = p.read_bytes()
        digest = sha256(data)
        jobs = store.load_jobs(case)
        key = job_key(root, p)
        old = jobs.get(key)
        if old and old["sha"] == digest and not force:
            return old
        profile = (settings.get("profiles") or {}).get(case) or settings.get("default_profile") or "ai"
        apply_model(settings)
        safe = layout.safe_name(p) + p.suffix.lower()
        job = {"key": key, "case": case, "name": layout.nfc(p.name), "safe": safe, "sha": digest,
               "profile": profile, "at": time.time(), "outputs": [], "status": "working"}
        try:
            kind, text, _, ocr_ranges, readers, starts = read_doc(p)
            if not text.strip():
                raise ValueError("Belgede okunabilir metin bulunamadı.")
            spans, cands = detect(text, case, profile, ocr_ranges, settings)
            flags = make_flags(text, spans, cands, ocr_ranges, starts, settings)
            job.update(kind=kind, text=text, ocr=bool(ocr_ranges), readers=sorted(set(readers)), starts=starts,
                       spans=spans, cands=cands, flags=flags, counts=_counts(spans))
            # dry run of the leak check on a copy of the vault, so a file that can't be masked never waits in review
            core._mask_safely(text, vault.Vault(matter(case), json.loads(json.dumps(vault.open_vault(matter(case)).to_json()))), spans)
            job["status"] = "review" if flags else "ready"
        except Exception as e:  # noqa: BLE001 - shown to the lawyer on the file's row
            job.update(status="error", error=str(e), kind=job.get("kind") or engine.KINDS.get(p.suffix.lower(), "?"))
        jobs[key] = job
        store.save_jobs(case, jobs)
        store.audit("masked" if job["status"] != "error" else "error", case, file=safe, sha256=digest,
                    kind=job.get("kind"), profile=profile, counts=job.get("counts", {}),
                    detail=f"{len(job.get('flags', []))} yer işaretlendi" if job["status"] != "error" else "maskelenemedi")
        if job["status"] == "ready" and settings.get("auto_release"):
            return release(root, case, key, settings, who="auto")
        return job


def set_decision(case: str, key: str, flag_id: str, decision: str) -> dict:
    if decision not in ("mask", "keep", "ok"):
        raise ValueError("decision must be mask, keep or ok")
    with _work_lock:
        jobs = store.load_jobs(case)
        job = jobs[key]
        f = next(f for f in job["flags"] if f["id"] == flag_id)
        f["decision"] = decision
        store.save_jobs(case, jobs)
        return job


# ---------------------------------------------------------------- release
def _labeled_redact(kind: str, data: bytes, spans: list[dict]) -> bytes:
    """local_formats.redact with the case vault's labels, so a name is [AD SOYAD-1] in every file of the case."""
    fmt = _labels_ready()
    with _fmt_lock:
        orig = fmt._label
        fmt._label = lambda sp, counters, seen: sp["label"]
        try:
            return fmt.redact(kind, data, json.dumps(spans, ensure_ascii=False), "label")
        finally:
            fmt._label = orig


def _out_text(name: str, blob: bytes) -> str:
    ext = name.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return pdf.text_of(blob)
    if ext in ("docx", "udf"):
        _, fmt = engine.load()
        return fmt.extract(ext, blob)
    return blob.decode("utf-8", errors="replace")


def outputs_for(job: dict, data: bytes, spans: list[dict], v) -> list[tuple[str, bytes]]:
    kind, text = job["kind"], job["text"]
    base = layout.safe_name(Path(job["name"])) + ".maskeli"
    masked = v.mask(text, spans)
    if kind == "txt":
        ext = Path(job["name"]).suffix.lower() or ".txt"
        return [(base + ext, masked.encode("utf-8"))]
    if kind == "docx":
        return [(base + ".docx", _labeled_redact("docx", data, spans))]
    if kind == "udf":
        # UYAP needs the same-length blocks; AI tools can't open .udf, so a Word copy with placeholders goes too
        return [(base + ".udf", _labeled_redact("udf", data, spans)), (base + ".docx", core._docx(masked))]
    if kind == "pdf" and not job.get("ocr"):
        return [(base + ".pdf", pdf.redact(data, spans))]
    # scans and photos: the masked text only (a blacked-out image is v2)
    return [(base + ".docx", core._docx(OCR_NOTE + "\n\n" + masked))]


def release(root: Path, case: str, key: str, settings: dict, who: str = "") -> dict:
    """Write the reviewed, masked copies to 2 Maskeli/<case>/. Each output is read back and checked: if any
    detected value is still readable, nothing is written and the file goes to Hata."""
    with _work_lock:
        jobs = store.load_jobs(case)
        job = jobs[key]
        src = root / layout.INBOX / key
        data = src.read_bytes()
        if sha256(data) != job["sha"]:
            raise Changed("Dosya maskelendikten sonra değişmiş; yeniden maskeleniyor.")
        v = vault.open_vault(matter(case))
        spans = final_spans(job)
        _, spans = core._mask_safely(job["text"], v, spans)
        for s in spans:
            s["label"] = v.label_for(s["entity_type"], s["text"])
        outs = outputs_for(job, data, spans, v)
        for name, blob in outs:
            seen = _out_text(name, blob)
            bad = [s for s in spans if (pat := core._leak_pat(s["text"])) and pat.search(seen)]
            if bad:
                kinds = ", ".join(sorted({engine.label_name(s["entity_type"]) for s in bad}))
                job.update(status="error", error=f"Maskeli kopyada hâlâ okunan değer var ({kinds}); paylaşılmadı.")
                store.save_jobs(case, jobs)
                store.audit("error", case, file=job["safe"], sha256=job["sha"], kind=job["kind"], detail="sızıntı kontrolü başarısız, paylaşılmadı")
                return job
        v.save()
        out_dir = layout.case_dir(root, layout.OUT, case)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, blob in outs:
            (out_dir / name).write_bytes(blob)
        decided = {k: sum(1 for f in job["flags"] if f["decision"] == k) for k in ("mask", "keep", "ok")}
        job.update(status="released", outputs=[n for n, _ in outs], released_at=time.time(), counts=_counts(spans))
        store.save_jobs(case, jobs)
        store.audit("released", case, file=job["safe"], sha256=job["sha"], kind=job["kind"], profile=job["profile"],
                    counts=job["counts"], detail=f"onaylayan: {who or '?'}; çıktılar: {', '.join(job['outputs'])}; "
                    f"işaretli yerler: {decided['mask']} maskelendi, {decided['keep']} açık bırakıldı"
                    + (f", {decided['ok']} taranmış sayfaya bakıldı" if decided['ok'] else ""))
        return job


# ---------------------------------------------------------------- restore
_FOLD = str.maketrans("İIŞĞÜÖÇÂÎÛışğüöçâîû", "IISGUOCAIUisguocaiu")


def unmask(v, text: str) -> tuple[str, int]:
    """Kalkan's unmask, also accepting placeholders written without Turkish letters ([T.C. KIMLIK NO-1]),
    which is how they appear in a masked PDF and how some AI tools copy them back."""
    table = dict(v.values)
    for label, value in v.values.items():
        table.setdefault(label.translate(_FOLD), value)
    if not table:
        return text, 0
    pat = re.compile("|".join(re.escape(k) for k in sorted(table, key=len, reverse=True)))
    n = 0

    def sub(m):
        nonlocal n
        n += 1
        return table[m.group(0)]
    return pat.sub(sub, text), n


def _answer_text(p: Path) -> str:
    data = p.read_bytes()
    if p.suffix.lower() == ".docx":
        _, fmt = engine.load()
        return fmt.extract("docx", data)
    return data.decode("utf-8", errors="replace")


class Ambiguous(ValueError):
    """The placeholders match more than one case: putting another client's names in would be worse than none."""


def best_case(root: Path, text: str, hint: str | None = None) -> str | None:
    """The case whose key fits the answer. Placeholders repeat across cases ([AD SOYAD-1] is in every one),
    so without a case folder or a choice in the window, a case is picked only when it is the only one that fits."""
    if hint and hint != layout.GENERAL:
        return hint
    hits = [c for c in layout.cases(root) + [layout.GENERAL] if unmask(vault.open_vault(matter(c)), text)[1]]
    if len(hits) > 1:
        raise Ambiguous("Bu cevaptaki etiketler birden fazla davada var (" + ", ".join(hits) + "). Davayı seçin "
                        "ya da cevabı o davanın klasörüne koyun.")
    return hits[0] if hits else None


def restore_text(root: Path, text: str, case: str | None, name: str = "cevap", ext: str = ".docx") -> dict:
    case = best_case(root, text, case)
    if not case:
        return {"restored": 0, "case": None, "path": None}
    restored, n = unmask(vault.open_vault(matter(case)), text)
    out_dir = layout.case_dir(root, layout.RESTORED, case)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}.geri{ext}"
    i = 2
    while out.exists():
        out = out_dir / f"{name}.geri ({i}){ext}"
        i += 1
    out.write_bytes(core._docx(restored) if ext == ".docx" else restored.encode("utf-8"))
    os.chmod(out, 0o600)
    store.audit("restored", case, file=layout.safe_name(out) + ext, detail=f"{n} etiket geri kondu")
    return {"restored": n, "case": case, "path": str(out), "name": out.name}


def restore_file(root: Path, p: Path) -> dict:
    """Restore an answer dropped in 3 Yapay zekâ cevapları (once per version of the file)."""
    with _work_lock:
        hint = layout.case_of(root, p, layout.ANSWERS)
        digest = sha256(p.read_bytes())
        done = store.load_jobs("__restores__")
        key = layout.nfc(str(p.relative_to(root / layout.ANSWERS)))
        if done.get(key) == digest:
            return {"skipped": True}
        try:
            res = restore_text(root, _answer_text(p), hint, layout.nfc(p.stem), p.suffix.lower())
        except Ambiguous as e:
            return {"restored": 0, "error": str(e)}  # not marked done: tried again once it's in a case folder
        done[key] = digest
        store.save_jobs("__restores__", done)
        return res


def forget(case: str) -> None:
    with _work_lock:
        vault.forget(matter(case))
        store.forget_case(case)
        store.audit("forgotten", case, detail="dava anahtarı ve kontrol verisi silindi")
