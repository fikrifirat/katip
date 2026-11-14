"""What the connector does, independent of transport (MCP stdio, CLI)."""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

from . import engine, names, vault
from .i18n import msg

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
            "note": msg("folder_note")}


def _nfc(p: Path) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", str(p))  # macOS stores names decomposed (NFD); compare composed


def _files(limit: int = 500) -> list[Path]:
    root = folder()
    out = []
    for p in sorted(root.rglob("*")):
        if len(out) >= limit:
            break
        rel = p.relative_to(root)
        if p.is_file() and not any(part.startswith(".") for part in rel.parts) and len(rel.parts) <= 4 \
                and p.suffix.lower() in engine.KINDS and ".maskeli" not in p.name:
            out.append(p)
    return out


def _by_id(file_id: str) -> Path:
    files = _files()
    if file_id == "latest" and files:  # the file the user just dropped into the folder
        return max(files, key=lambda p: p.stat().st_mtime)
    for p in files:
        if names.file_id(p) == file_id:
            return p
    raise FileNotFoundError(msg("no_id"))


def list_files() -> dict:
    """Files in the Katip folder with ids and *safe* names: the real file names never reach the model."""
    root = folder()
    items = []
    for p in _files():
        st = p.stat()
        items.append({"file_id": names.file_id(p), "name": names.safe_title(p.stem) + p.suffix.lower(),
                      "kind": engine.KINDS[p.suffix.lower()], "size_kb": round(st.st_size / 1024),
                      "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)), "_mtime": st.st_mtime,
                      **({"subfolder": len(p.relative_to(root).parts) - 1} if p.parent != root else {})})
    items.sort(key=lambda f: f.pop("_mtime"), reverse=True)  # newest first: "the file I just added"
    return {"folder": "your Katip folder", "files": items,
            "note": msg("list_note")}


def _target(path: str | None, file_id: str | None) -> Path:
    if file_id:
        return _by_id(file_id)
    if not path:
        raise ValueError(msg("need_file"))
    return _resolve(path)


def _resolve(path: str) -> Path:
    import unicodedata
    p = Path(os.path.expandvars(path)).expanduser().resolve()
    for form in ("NFC", "NFD"):  # a name typed composed may be stored decomposed, and vice versa
        if not p.is_file():
            q = Path(unicodedata.normalize(form, str(p)))
            p = q if q.is_file() else p
    if not p.is_file():
        raise FileNotFoundError(msg("not_found"))  # don't echo the path: it can hold a client name
    if p.stat().st_size > MAX_BYTES:
        raise ValueError(msg("too_big", mb=MAX_BYTES // 2**20))
    roots = _roots()
    if roots and not any(_nfc(p).startswith(_nfc(r).rstrip("/") + "/") for r in roots):
        raise PermissionError(msg("outside"))
    return p


# Every detected type is propagated: a passport number, a religion or a case number written once in a
# context the detector understands is often repeated later where it doesn't (0.3.1 refused such files).


def _propagate(text: str, spans: list[dict], known: list[tuple[str, str]]) -> list[dict]:
    """Mask every occurrence of a value, not just the ones the detector caught.

    Sources: values detected elsewhere in this document, and values already in this
    matter's vault (so a name found in the petition is also hidden in the expert report).
    Matching is case-insensitive on whole words; overlaps are resolved by the masker."""
    import re
    cands = {(s["entity_type"], s["text"].strip()) for s in spans}
    cands |= set(known)
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


def _leak_pat(value: str):
    import re
    if len(re.sub(r"\W", "", value)) < 4:
        return None
    return re.compile(r"(?<!\w)" + r"\W*".join(re.escape(w) for w in value.split()) + r"(?!\w)", re.I)


def _leaks(masked: str, spans: list[dict]) -> list[str]:
    """Detected values still readable in the output, as whole words (a 6-digit registry number inside a
    16-digit Mersis number is not a leak; the browser's substring check would flag it)."""
    out = []
    for s in spans:
        pat = _leak_pat(s["text"])
        if pat and pat.search(masked):
            out.append(s["id"])
    return out


def _repair(text: str, spans: list[dict], leaked: list[str]) -> list[dict]:
    """Cover every remaining occurrence of a leaked value. An occurrence that overlaps other spans is
    merged with them into one span of the leaked value's type, so nothing is left half-masked."""
    out = list(spans)
    for sid in leaked:
        src = next((s for s in out if s["id"] == sid), None) or next(s for s in spans if s["id"] == sid)
        pat = _leak_pat(src["text"])
        for m in pat.finditer(text):
            hit = [s for s in out if s["start"] < m.end() and m.start() < s["end"]]
            if any(s["start"] <= m.start() and s["end"] >= m.end() for s in hit):
                continue
            a = min([m.start()] + [s["start"] for s in hit])
            b = max([m.end()] + [s["end"] for s in hit])
            out = [s for s in out if s not in hit]
            out.append({"id": f"r{len(out):04d}", "entity_type": src["entity_type"], "start": a, "end": b,
                        "text": text[a:b], "score": 1.0, "recognizer": "katip_repair"})
    return sorted(out, key=lambda s: s["start"])


def _mask_safely(text: str, v, spans: list[dict]) -> tuple[str, list[dict]]:
    """Mask, check that no detected value is still readable, repair and re-check. Raises with the kinds
    and line numbers of what could not be hidden (never the values)."""
    masked = v.mask(text, spans)
    for _ in range(3):
        leaks = _leaks(masked, spans)
        if not leaks:
            return masked, spans
        spans = _repair(text, spans, leaks)
        masked = v.mask(text, spans)
    bad = [s for s in spans if s["id"] in set(_leaks(masked, spans))]
    where = sorted({engine.label_name(s["entity_type"]) for s in bad})
    raise RuntimeError(msg("leak", n=len(bad), kinds=", ".join(where)))


def _profile(profile: str | None) -> str:
    return profile or os.environ.get("KATIP_PROFILE") or "ai"  # an unset plugin setting arrives as ""


_IDS = None


def _id_numbers(text: str, spans: list[dict]) -> list[dict]:
    """ID numbers whose checksum fails (a typo, an OCR slip, an old foreigner number) are still masked:
    any 11-digit number starting with 99 is a YKN, and an 11-digit number right after "T.C. kimlik",
    "TCKN", "YKN" or "yabancı kimlik" is an ID. Lawyers were fined for unmasked IDs."""
    import re
    global _IDS
    if _IDS is None:
        _IDS = re.compile(r"(?<!\d)99\d{9}(?!\d)|(?i:(?:t\.?\s?c\.?\s*kimlik|tckn|ykn|yabanc[ıi]\s+kimlik)"
                          r"[^\d\n]{0,25})(\d{11})(?!\d)")
    out = list(spans)
    for m in _IDS.finditer(text):
        a, b = (m.start(1), m.end(1)) if m.group(1) else (m.start(), m.end())
        if any(s["start"] < b and a < s["end"] for s in out):
            continue
        typ = "YKN" if text[a:a + 2] == "99" else "TCKN"
        out.append({"id": f"i{len(out):04d}", "entity_type": typ, "start": a, "end": b, "text": text[a:b],
                    "score": 1.0, "recognizer": "katip_id_context"})
    return sorted(out, key=lambda s: s["start"])


def _detect(text: str, v, profile: str, ocr_ranges=()) -> list[dict]:
    types, addr = engine.profile_types(profile)
    known = [(k.split("|", 1)[0], v.values[lab]) for k, lab in v.labels.items() if k.split("|", 1)[0] in types]
    spans = engine.detect(text, _threshold(), types, ocr_ranges=ocr_ranges, address_detail=addr)
    return _propagate(text, _id_numbers(text, spans), known)


_read_cache: dict = {}


def _read(p: Path):
    """read_text with a small cache, so paging through a long scan runs OCR once."""
    key = (str(p), p.stat().st_mtime, p.stat().st_size)
    if key not in _read_cache:
        if len(_read_cache) > 8:
            _read_cache.clear()
        _read_cache[key] = engine.read_text(p)
    return _read_cache[key]


def mask_file(path: str | None = None, matter: str = "default", page: int = 1, profile: str | None = None,
              file_id: str | None = None) -> dict:
    """Read a file on this device, mask it, return only the masked text."""
    p = _target(path, file_id)
    profile = _profile(profile)
    kind, text, _, ocr_ranges, readers = _read(p)
    v = vault.open_vault(matter)
    spans = _detect(text, v, profile, ocr_ranges)
    masked, spans = _mask_safely(text, v, spans)  # never hands over text that still contains a detected value
    doc_id = hashlib.sha256(f"{matter}|{p}|{p.stat().st_mtime}".encode()).hexdigest()[:12]
    v.docs[doc_id] = {"at": time.time(), "kind": kind}
    v.save()
    pages = max(1, -(-len(masked) // PAGE_CHARS))
    page = min(max(1, page), pages)
    chunk = masked[(page - 1) * PAGE_CHARS: page * PAGE_CHARS]
    return {
        "doc_id": doc_id,
        "file_id": names.file_id(p),
        "matter": matter,
        "file_name": names.safe_title(p.stem) + p.suffix.lower(),  # real names can be personal data
        "kind": kind,
        "profile": f"{profile} ({engine.PROFILES[profile]['label']})",
        **({"ocr": msg("ocr", n=len(readers), readers=", ".join(sorted(set(readers))))} if readers else {}),
        "masked_text": chunk,
        "page": page, "pages": pages,
        "entity_counts": _counts(spans),
        "placeholders": sorted(set(v.labels[f"{s['entity_type']}|{vault._norm(s['text'])}"] for s in spans)),
        "vault": "encrypted on this device" if vault.persistent() else "memory only (install `cryptography` to keep it)",
        "note": msg("placeholders"),
    }


def write_redacted(path: str | None = None, matter: str = "default", output_path: str | None = None,
                   profile: str | None = None, file_id: str | None = None) -> dict:
    """Write a masked copy of the file next to the original (same format). Returns its id and safe name;
    the path would repeat the original file name."""
    p = _target(path, file_id)
    kind, text, data, ocr_ranges, _ = _read(p)
    if kind in ("pdf", "image"):
        raise ValueError(msg("no_burn"))
    v = vault.open_vault(matter)
    spans = _detect(text, v, _profile(profile), ocr_ranges)
    _, spans = _mask_safely(text, v, spans)
    for s in spans:  # register labels so restore works for this copy too
        v.label_for(s["entity_type"], s["text"])
    v.save()
    out = Path(output_path).expanduser() if output_path else p.with_name(f"{p.stem}.maskeli{p.suffix}")
    if out.exists():
        raise FileExistsError(msg("exists"))
    out.write_bytes(engine.redact_bytes(kind, data, spans, "box"))
    return {"saved": "next to the original, with .maskeli in its name", "file_id": names.file_id(out),
            "name": names.safe_title(out.stem) + out.suffix.lower(), "entity_counts": _counts(spans)}


def restore_to_file(text: str, output_path: str, matter: str = "default") -> dict:
    """Swap placeholders back to real values and write the result to a local file.
    Returns only the path and a count: the real values never go back to the model."""
    v = vault.open_vault(matter)
    restored, n = v.unmask(text)
    out = Path(output_path).expanduser()
    if out.exists():
        raise FileExistsError(msg("exists"))
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
