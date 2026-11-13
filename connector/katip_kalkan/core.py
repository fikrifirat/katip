"""What the connector does, independent of transport (MCP stdio, CLI)."""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

from . import engine, vault

MAX_BYTES = int(os.environ.get("KATIP_MAX_FILE_MB", 25)) * 1024 * 1024
# Claude's directory caps a tool result at 25k tokens; stay well under it and page the rest.
PAGE_CHARS = int(os.environ.get("KATIP_PAGE_CHARS", 40_000))


def _threshold() -> float:
    return float(os.environ.get("KATIP_THRESHOLD") or 0.7)


def _counts(spans):
    c: dict[str, int] = {}
    for s in spans:
        c[s["entity_type"]] = c.get(s["entity_type"], 0) + 1
    return c


DEFAULT_FOLDER = "~/Documents/katip-documents"


def _roots() -> list[Path]:
    out = []
    for r in os.environ.get("KATIP_ALLOWED_DIRS", "").split(os.pathsep):
        r = os.path.expandvars(r.strip())
        if r and "${" not in r:  # an unfilled ${user_config...} or ${HOME} means "not set"
            out.append(Path(r).expanduser().resolve())
    return out


def folder(create: bool = True) -> Path:
    """The user's Katip folder: the one picked in the settings, else ~/Documents/katip-documents.
    Created (private to this user) the first time it's needed, so the default works out of the box."""
    roots = _roots()
    f = roots[0] if roots else Path(os.environ.get("KATIP_FOLDER") or DEFAULT_FOLDER).expanduser().resolve()
    if create and not f.exists():
        f.mkdir(parents=True, mode=0o700, exist_ok=True)
    return f


def open_folder() -> dict:
    """Show the Katip folder in Finder / Explorer / the file manager."""
    import subprocess
    import sys
    f = folder()
    cmd = {"darwin": ["open"], "win32": ["explorer"]}.get(sys.platform, ["xdg-open"])
    try:
        subprocess.Popen(cmd + [str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        opened = True
    except OSError:
        opened = False
    return {"folder": str(f), "link": f.as_uri(), "opened": opened,
            "note": "Put client files here; Katip only opens files inside this folder."
            if _roots() else "Put client files here."}


def _resolve(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    if p.stat().st_size > MAX_BYTES:
        raise ValueError(f"file is larger than {MAX_BYTES // 2**20} MB")
    roots = _roots()
    if roots and not any(p.is_relative_to(r) for r in roots):
        raise PermissionError("file is outside the folders allowed in Katip's settings")
    return p


PROPAGATE = {"PERSON", "ADDRESS", "EMAIL", "PHONE", "TCKN", "IBAN", "VKN", "PLATE", "HEALTH"}


def _propagate(text: str, spans: list[dict], known: list[tuple[str, str]]) -> list[dict]:
    """Mask every occurrence of a value, not just the ones the detector caught.

    Sources: values detected elsewhere in this document, and values already in this
    matter's vault (so a name found in the petition is also hidden in the expert report).
    Matching is case-insensitive on whole words; overlaps are resolved by the masker."""
    import re
    cands = {(s["entity_type"], s["text"].strip()) for s in spans if s["entity_type"] in PROPAGATE}
    cands |= {(t, v) for t, v in known if t in PROPAGATE}
    out = list(spans)
    for typ, val in sorted(cands, key=lambda c: -len(c[1])):
        if len(val) < 4:
            continue
        pat = re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, val.split())) + r"(?!\w)", re.I)
        for m in pat.finditer(text):
            hit = [s for s in out if s["start"] < m.end() and m.start() < s["end"]]
            # an occurrence already covered as a whole is fine; one covered only in part ("Yiğitalp
            # [AD SOYAD-2]" when the model saw just the surname) is widened to the full value
            if any(s["start"] <= m.start() and s["end"] >= m.end() for s in hit):
                continue
            if any(s["entity_type"] != typ or s["start"] < m.start() or s["end"] > m.end() for s in hit):
                continue  # overlaps a different value: leave it to the detector
            out = [s for s in out if s not in hit]
            out.append({"id": f"p{len(out):04d}", "entity_type": typ, "start": m.start(), "end": m.end(),
                        "text": m.group(0), "score": 1.0, "recognizer": "katip_propagate"})
    return sorted(out, key=lambda s: s["start"])


def _leaks(masked: str, spans: list[dict]) -> list[str]:
    """Detected values still readable in the output, as whole words (a 6-digit registry number inside a
    16-digit Mersis number is not a leak; the browser's substring check would flag it)."""
    import re
    out = []
    for s in spans:
        words = s["text"].split()
        if len(re.sub(r"\W", "", s["text"])) < 4:
            continue
        pat = r"(?<!\w)" + r"\W*".join(re.escape(w) for w in words) + r"(?!\w)"
        if re.search(pat, masked, re.I):
            out.append(s["id"])
    return out


def _profile(profile: str | None) -> str:
    return profile or os.environ.get("KATIP_PROFILE") or "ai"  # an unset plugin setting arrives as ""


def _detect(text: str, v, profile: str, ocr_ranges=()) -> list[dict]:
    types, addr = engine.profile_types(profile)
    known = [(k.split("|", 1)[0], v.values[lab]) for k, lab in v.labels.items() if k.split("|", 1)[0] in types]
    spans = engine.detect(text, _threshold(), types, ocr_ranges=ocr_ranges, address_detail=addr)
    return _propagate(text, spans, known)


_read_cache: dict = {}


def _read(p: Path):
    """read_text with a small cache, so paging through a long scan runs OCR once."""
    key = (str(p), p.stat().st_mtime, p.stat().st_size)
    if key not in _read_cache:
        if len(_read_cache) > 8:
            _read_cache.clear()
        _read_cache[key] = engine.read_text(p)
    return _read_cache[key]


def mask_file(path: str, matter: str = "default", page: int = 1, profile: str | None = None) -> dict:
    """Read a file on this device, mask it, return only the masked text."""
    p = _resolve(path)
    profile = _profile(profile)
    kind, text, _, ocr_ranges, readers = _read(p)
    v = vault.open_vault(matter)
    spans = _detect(text, v, profile, ocr_ranges)
    masked = v.mask(text, spans)
    leaks = _leaks(masked, spans)
    if leaks:  # never hand over text that still contains a detected value
        raise RuntimeError(f"leak check failed on {len(leaks)} values; nothing was returned")
    doc_id = hashlib.sha256(f"{matter}|{p}|{p.stat().st_mtime}".encode()).hexdigest()[:12]
    v.docs[doc_id] = {"at": time.time(), "kind": kind}
    v.save()
    pages = max(1, -(-len(masked) // PAGE_CHARS))
    page = min(max(1, page), pages)
    chunk = masked[(page - 1) * PAGE_CHARS: page * PAGE_CHARS]
    return {
        "doc_id": doc_id,
        "matter": matter,
        "file_name": f"belge{p.suffix.lower()}",  # the real name can be personal data ("Ayşe_Kaya_epikriz.pdf")
        "kind": kind,
        "profile": f"{profile} ({engine.PROFILES[profile]['label']})",
        **({"ocr": f"{len(readers)} page(s) read with local OCR ({', '.join(sorted(set(readers)))}); "
                   "check unusual spellings, OCR can misread letters"} if readers else {}),
        "masked_text": chunk,
        "page": page, "pages": pages,
        "entity_counts": _counts(spans),
        "placeholders": sorted(set(v.labels[f"{s['entity_type']}|{vault._norm(s['text'])}"] for s in spans)),
        "vault": "encrypted on this device" if vault.persistent() else "memory only (install `cryptography` to keep it)",
        "note": ("Placeholders like [AD SOYAD-1] stand for real values kept only on the user's device. "
                 "Keep them exactly as written in your answer so Katip can restore them locally."),
    }


def write_redacted(path: str, matter: str = "default", output_path: str | None = None,
                   profile: str | None = None) -> dict:
    """Write a masked copy of the file next to the original (same format), return its path only."""
    p = _resolve(path)
    kind, text, data, ocr_ranges, _ = _read(p)
    if kind in ("pdf", "image"):
        raise ValueError("burn-in PDF and photo redaction runs in the Katip app (MuPDF); use mask_file for the text")
    v = vault.open_vault(matter)
    spans = _detect(text, v, _profile(profile), ocr_ranges)
    for s in spans:  # register labels so restore works for this copy too
        v.label_for(s["entity_type"], s["text"])
    v.save()
    out = Path(output_path).expanduser() if output_path else p.with_name(f"{p.stem}.maskeli{p.suffix}")
    if out.exists():
        raise FileExistsError(f"{out} already exists; pick another output_path")
    out.write_bytes(engine.redact_bytes(kind, data, spans, "box"))
    return {"output_path": str(out), "entity_counts": _counts(spans)}


def restore_to_file(text: str, output_path: str, matter: str = "default") -> dict:
    """Swap placeholders back to real values and write the result to a local file.
    Returns only the path and a count: the real values never go back to the model."""
    v = vault.open_vault(matter)
    restored, n = v.unmask(text)
    out = Path(output_path).expanduser()
    if out.exists():
        raise FileExistsError(f"{out} already exists; pick another output_path")
    out.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(restored)
    return {"output_path": str(out), "placeholders_restored": n}


def forget_matter(matter: str) -> dict:
    return {"deleted": vault.forget(matter)}


def status() -> dict:
    from . import ner, ocr
    return {"engine": ner.describe(),
            "ocr": ", ".join(ocr.available()) or "none (scans and photos can't be read)",
            "default_profile": _profile(None), "threshold": _threshold(),
            "vault": "encrypted on this device" if vault.persistent() else "memory only",
            "expired_vaults_purged": vault.purge_expired(),
            "folder": str(folder()), "folder_link": folder().as_uri(),
            "allowed_dirs": os.pathsep.join(map(str, _roots())) or "any"}
