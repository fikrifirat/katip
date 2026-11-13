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
    return float(os.environ.get("KATIP_THRESHOLD", 0.7))


def _counts(spans):
    c: dict[str, int] = {}
    for s in spans:
        c[s["entity_type"]] = c.get(s["entity_type"], 0) + 1
    return c


def _resolve(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    if p.stat().st_size > MAX_BYTES:
        raise ValueError(f"file is larger than {MAX_BYTES // 2**20} MB")
    roots = [Path(r).expanduser().resolve() for r in os.environ.get("KATIP_ALLOWED_DIRS", "").split(os.pathsep) if r]
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
    taken = [(s["start"], s["end"]) for s in spans]
    out = list(spans)
    for typ, val in sorted(cands, key=lambda c: -len(c[1])):
        if len(val) < 4:
            continue
        pat = re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, val.split())) + r"(?!\w)", re.I)
        for m in pat.finditer(text):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            out.append({"id": f"p{len(out):04d}", "entity_type": typ, "start": m.start(), "end": m.end(),
                        "text": m.group(0), "score": 1.0, "recognizer": "katip_propagate"})
    return out


def _detect(text: str, v) -> list[dict]:
    known = [(k.split("|", 1)[0], v.values[lab]) for k, lab in v.labels.items()]
    return _propagate(text, engine.detect(text, _threshold()), known)


def mask_file(path: str, matter: str = "default", page: int = 1) -> dict:
    """Read a file on this device, mask it, return only the masked text."""
    p = _resolve(path)
    kind, text, _ = engine.read_text(p)
    v = vault.open_vault(matter)
    spans = _detect(text, v)
    masked = v.mask(text, spans)
    leaks = engine.leaked(masked, spans)
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
        "masked_text": chunk,
        "page": page, "pages": pages,
        "entity_counts": _counts(spans),
        "placeholders": sorted(set(v.labels[f"{s['entity_type']}|{vault._norm(s['text'])}"] for s in spans)),
        "vault": "encrypted on this device" if vault.persistent() else "memory only (install `cryptography` to keep it)",
        "note": ("Placeholders like [AD SOYAD-1] stand for real values kept only on the user's device. "
                 "Keep them exactly as written in your answer so Katip can restore them locally."),
    }


def write_redacted(path: str, matter: str = "default", output_path: str | None = None) -> dict:
    """Write a masked copy of the file next to the original (same format), return its path only."""
    p = _resolve(path)
    kind, text, data = engine.read_text(p)
    if kind == "pdf":
        raise ValueError("burn-in PDF redaction runs in the Katip app (MuPDF); use mask_file for PDF text")
    v = vault.open_vault(matter)
    spans = _detect(text, v)
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
    return {"engine": "katip rules (local, offline)", "threshold": _threshold(),
            "vault": "encrypted on this device" if vault.persistent() else "memory only",
            "expired_vaults_purged": vault.purge_expired(),
            "allowed_dirs": os.environ.get("KATIP_ALLOWED_DIRS") or "any"}
