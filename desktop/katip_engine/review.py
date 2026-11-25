"""The review queue: masking candidates the lawyer judges, and what Katip learns from the verdicts.

Every time Katip masks (the engine for the app, `katip-engine mcp` for Claude), two kinds of candidates are kept:
  unsure  a name Katip masked with a low score ("is this personal data?")
  missed  a word the model scored just under the threshold that nothing masked ("should Katip have masked it?")
The lawyer's verdict (mask / allow / later) goes into the firm's own lists, which every later detection uses as
mask_terms and allow_terms. Candidates hold real client values, so the file is encrypted with the vault key and
never leaves this Mac; a case's candidates go when the case is forgotten, and all expire with the case keys.

More kinds (precedent grades, DD matches, document types) are planned; see desktop/macos/DESIGN.md, v0.4.
"""
from __future__ import annotations

import fcntl
import json
import os
import secrets
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

UNSURE_BELOW = 0.80  # a masked name under this score is worth a look
MISSED_FROM = 0.20   # a model word between this and the threshold, masked by nothing, may be a missed name
MAX_OPEN = 400
WINDOW = 70          # characters of context on each side
VERDICTS = ("mask", "allow", "later")
_AAD = b"katip-review"
_lock = threading.Lock()
_ctx = threading.local()
_orig: dict = {}
_source = "app"


class NotFound(LookupError):
    """No candidate with that id (judged on another screen, or expired)."""


class Unreadable(RuntimeError):
    """The file is there but can't be decrypted (the Keychain refused, or the key changed). Masking stops rather
    than run without the names the lawyer told Katip to always mask; the app offers to start the lists again."""


def path() -> Path:
    from katip_kalkan.vault import katip_home
    return katip_home() / "engine-review.bin"


def _key(text: str) -> str:
    t = " ".join(text.split()).replace("I", "ı").replace("İ", "i")
    return t.casefold()


# -- storage: one encrypted file, shared by the engine and Claude's MCP process ------------------------------
_cipher = None
_memory: dict | None = None  # when the vault keeps nothing on disk, neither does the queue


def _aes():
    """The vault key, asked for once per process (each ask is a Keychain call)."""
    global _cipher
    if _cipher is None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from katip_kalkan import vault
        _cipher = AESGCM(vault._key())
    return _cipher


def _on_disk() -> bool:
    from katip_kalkan import vault
    return vault.persistent()


def _empty() -> dict:
    return {"candidates": {}, "learned": {"mask": [], "allow": []}, "origins": {}}


def _load() -> dict:
    global _memory
    if not _on_disk():
        _memory = _memory or _empty()
        d = _memory
    else:
        try:
            blob = path().read_bytes()
        except FileNotFoundError:
            return _empty()
        try:
            d = json.loads(_aes().decrypt(blob[:12], blob[12:], _AAD))
        except Exception as e:  # noqa: BLE001 - never treat this as "empty": that would forget the mask list
            raise Unreadable("Katip can't read its learned lists on this Mac") from e
    from katip_kalkan import vault
    cutoff = time.time() - vault.ttl_seconds()
    d["candidates"] = {k: c for k, c in d.get("candidates", {}).items() if c["last_seen"] > cutoff}
    d.setdefault("learned", {"mask": [], "allow": []})
    d.setdefault("origins", {})
    return d


def reset() -> None:
    """Start the lists again after they became unreadable; the old file is kept aside, not deleted."""
    global _cipher
    with _lock:
        p = path()
        if p.exists():
            os.replace(p, p.with_name(f"{p.name}.unreadable-{int(time.time())}"))
        _cipher = None


def _save(d: dict) -> None:
    if not _on_disk():
        return  # _memory is d itself
    nonce = secrets.token_bytes(12)
    blob = nonce + _aes().encrypt(nonce, json.dumps(d, ensure_ascii=False).encode(), _AAD)
    p = path()
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".review-")  # mode 0600
    with os.fdopen(fd, "wb") as fh:
        fh.write(blob)
    os.replace(tmp, p)


@contextmanager
def _store():
    """Read, change, write, with a file lock: the app's engine and Claude's MCP process share the file."""
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(p.with_suffix(".lock"), "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            d = _load()
            yield d
            _save(d)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def learned() -> dict:
    with _lock:
        return _load()["learned"]


_recent: list = []  # (text hash, kind, key) already counted: paging re-detects the same text


# -- collecting ---------------------------------------------------------------------------------------------
def _context(text: str, a: int, b: int, hide: list[tuple[int, int]]) -> str:
    """text[a:b] with every other detected value replaced by •••."""
    out, i = [], a
    for s, e in sorted(hide):
        if e <= a or s >= b:
            continue
        out.append(text[i:max(s, a)])
        out.append("•••")
        i = min(e, b)
    out.append(text[i:b])
    return " ".join("".join(out).split())


def collect(text: str, final: list[dict], raw, threshold: float, matter: str) -> None:
    found = []
    for s in final:
        if s.get("entity_type") == "PERSON" and float(s.get("score", 1)) < UNSURE_BELOW \
                and s.get("recognizer") != "local_dictionary":
            found.append(("unsure", s["start"], s["end"], float(s["score"]), "PERSON"))
    taken = [(s["start"], s["end"]) for s in final]
    for r in raw:
        st, en, score = int(r[0]), int(r[1]), float(r[2])
        etype = r[3] if len(r) > 3 and r[3] else "PERSON"
        value = text[st:en].strip()
        if not (MISSED_FROM <= score < threshold) or etype != "PERSON" or len(value) < 3 or not value[0].isupper():
            continue
        if any(st < e and en > s for s, e in taken):
            continue
        found.append(("missed", st, en, score, etype))
        taken.append((st, en))
    import hashlib
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    from katip_kalkan import engine as kengine
    abbreviation = getattr(kengine, "_abbreviation", lambda _s: False)
    found = [f for f in found if not abbreviation(text[f[1]:f[2]])]
    found = [f for f in found if (h, f[0], _key(text[f[1]:f[2]].strip())) not in _recent]
    if not found:
        return
    _recent.extend((h, f[0], _key(text[f[1]:f[2]].strip())) for f in found)
    del _recent[:-500]
    hide = [(s["start"], s["end"]) for s in final]
    now = time.time()
    with _store() as d:
        lex = {_key(t) for t in d["learned"]["mask"] + d["learned"]["allow"]}
        by_key = {(c["kind"], c["key"]): c for c in d["candidates"].values()}
        for kind, st, en, score, etype in found:
            value = text[st:en].strip()
            k = _key(value)
            if k in lex:
                continue
            c = by_key.get((kind, k))
            if c:
                if c["status"] == "open":
                    c.update(seen=c["seen"] + 1, last_seen=now, score=min(c["score"], round(score, 2)))
                continue
            cid = secrets.token_hex(6)
            c = {"id": cid, "kind": kind, "key": k, "text": value, "entity_type": etype, "score": round(score, 2),
                 "before": ("…" if st > WINDOW else "") + _context(text, max(0, st - WINDOW), st, hide),
                 "after": _context(text, en, min(len(text), en + WINDOW), hide) + ("…" if en + WINDOW < len(text) else ""),
                 "matter": matter, "source": _source, "seen": 1, "created": now, "last_seen": now,
                 "status": "open", "later": False, "verdict": None}
            d["candidates"][cid] = c
            by_key[(kind, k)] = c
        opened = sorted((c for c in d["candidates"].values() if c["status"] == "open"), key=lambda c: c["last_seen"])
        for c in opened[:-MAX_OPEN] if len(opened) > MAX_OPEN else []:
            del d["candidates"][c["id"]]


# -- the lawyer's verdicts ------------------------------------------------------------------------------------
_PUBLIC = ("id", "kind", "text", "entity_type", "score", "before", "after", "matter", "source", "seen", "created",
           "later")


def listing() -> dict:
    with _lock:
        try:
            d = _load()
        except Unreadable:
            return {"open": [], "judged": 0, "learned": {"mask": [], "allow": []}, "unreadable": True}
    cs = d["candidates"].values()
    open_ = sorted((c for c in cs if c["status"] == "open"),
                   key=lambda c: (c["later"], c["kind"] != "missed", -c["seen"], -c["last_seen"]))
    return {"open": [{k: c[k] for k in _PUBLIC} for c in open_],
            "judged": sum(c["status"] == "judged" for c in cs),
            "learned": d["learned"], "unreadable": False}


def _drop_term(d: dict, text: str) -> None:
    k = _key(text)
    for lst in ("mask", "allow"):
        d["learned"][lst] = [t for t in d["learned"][lst] if _key(t) != k]
    d.get("origins", {}).pop(k, None)


def judge(cid: str, verdict: str) -> dict:
    if verdict not in VERDICTS:
        from .settings import Invalid
        raise Invalid(f"verdict must be one of {', '.join(VERDICTS)}")
    with _store() as d:
        c = d["candidates"].get(cid)
        if not c:
            raise NotFound(cid)
        if verdict == "later":
            c["later"] = True
        elif verdict == "allow" and c["kind"] == "missed":
            # it wasn't masked anyway: close it without putting the word on the never-mask list
            c.update(status="judged", verdict=verdict, judged_at=time.time(), added=False)
        else:
            _drop_term(d, c["text"])
            d["learned"][verdict].append(c["text"])
            d["origins"][_key(c["text"])] = c["matter"]
            c.update(status="judged", verdict=verdict, judged_at=time.time(), added=True)
    return listing()


def undo(cid: str) -> dict:
    with _store() as d:
        c = d["candidates"].get(cid)
        if not c:
            raise NotFound(cid)
        if c["status"] == "judged" and c.get("added", True):
            _drop_term(d, c["text"])
        c.update(status="open", verdict=None, later=False)
    return listing()


def forget_learned(lst: str, text: str) -> dict:
    if lst not in ("mask", "allow"):
        from .settings import Invalid
        raise Invalid("list must be mask or allow")
    with _store() as d:
        d["learned"][lst] = [t for t in d["learned"][lst] if _key(t) != _key(text)]
    return listing()


def drop_matter(matter: str) -> None:
    """Forgetting a case forgets its candidates and the words learned from them (KVKK erasure)."""
    with _store() as d:
        d["candidates"] = {k: c for k, c in d["candidates"].items() if c["matter"] != matter}
        gone = {k for k, m in d["origins"].items() if m == matter}
        for lst in ("mask", "allow"):
            d["learned"][lst] = [t for t in d["learned"][lst] if _key(t) not in gone]
        for k in gone:
            d["origins"].pop(k, None)


# -- hooking Kalkan's detection ----------------------------------------------------------------------------------
def _wrap_detect(orig):
    def detect(text, threshold=0.5, entities=None, mask_terms=(), allow_terms=(), *a, **kw):
        lex = learned()  # Unreadable propagates: never mask without the firm's "always mask" list
        raw: list = []
        from katip_kalkan import ner
        try:
            m = ner.get()
        except Exception:  # noqa: BLE001 - the model's own failure is engine.detect's to report
            m = None
        spied = m is not None and "spans" not in vars(m)
        if spied:
            inner = m.spans

            def spy(t, min_score=0.5):
                got = inner(t, min_score=min(min_score, MISSED_FROM))
                raw.extend(got)
                return [g for g in got if g[2] >= min_score]
            m.spans = spy
        try:
            spans = orig(text, threshold, entities, [*mask_terms, *lex["mask"]], [*allow_terms, *lex["allow"]], *a, **kw)
        finally:
            if spied:
                del m.spans
        try:
            collect(text, spans, raw, threshold, getattr(_ctx, "matter", "default"))
        except Exception:  # noqa: BLE001 - the queue is a help; masking must never fail because of it
            pass
        return spans
    return detect


def _wrap_core(orig):
    def _detect(text, v, *a, **kw):
        _ctx.matter = getattr(v, "matter", "default")
        try:
            return orig(text, v, *a, **kw)
        finally:
            _ctx.matter = "default"
    return _detect


def _wrap_forget(orig):
    def forget_matter(matter, *a, **kw):
        out = orig(matter, *a, **kw)
        try:
            drop_matter(matter)
        except Exception:  # noqa: BLE001
            pass
        return out
    return forget_matter


def install(source: str) -> None:
    """Hook Kalkan's detection in this process: apply the learned lists and collect candidates."""
    global _source
    _source = source
    from katip_kalkan import core, engine
    for mod, name, wrap in ((engine, "detect", _wrap_detect), (core, "_detect", _wrap_core),
                            (core, "forget_matter", _wrap_forget)):
        fn = getattr(mod, name)
        if not getattr(fn, "_katip_review", False):  # each one on its own: a reloaded module is wrapped again
            _orig[(mod.__name__, name)] = fn
            w = wrap(fn)
            w._katip_review = True
            setattr(mod, name, w)


def uninstall() -> None:
    import sys
    for (modname, name), fn in _orig.items():
        setattr(sys.modules[modname], name, fn)
    _orig.clear()
    global _cipher, _memory
    _cipher, _memory = None, None
    _recent.clear()
