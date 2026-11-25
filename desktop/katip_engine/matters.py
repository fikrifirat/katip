"""The list of cases that have a key on this Mac, for the app's Cases screen.

Kalkan stores each case's key under a hash of its label, so the labels themselves are not recoverable from the
vault. The engine keeps them here, encrypted with the same key as the vault, because a lawyer may type a client's
name as the label.
"""
from __future__ import annotations

import json
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path

_lock = threading.Lock()


def path() -> Path:
    from katip_kalkan.vault import katip_home
    return katip_home() / "engine-matters.bin"


def _aes():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from katip_kalkan import vault
    return AESGCM(vault._key())


def load() -> dict[str, float]:
    try:
        blob = path().read_bytes()
        return json.loads(_aes().decrypt(blob[:12], blob[12:], b"katip-matters"))
    except Exception:  # noqa: BLE001 - missing, or written with a key that is gone
        return {}


def _save(d: dict[str, float]) -> None:
    nonce = secrets.token_bytes(12)
    blob = nonce + _aes().encrypt(nonce, json.dumps(d).encode(), b"katip-matters")
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".matters-")  # mode 0600
    with os.fdopen(fd, "wb") as fh:
        fh.write(blob)
    os.replace(tmp, p)


def touch(matter: str) -> None:
    try:
        with _lock:
            d = load()
            d[matter] = time.time()
            _save(d)
    except Exception:  # noqa: BLE001 - the list is a convenience; masking must never fail because of it
        pass


def drop(matter: str) -> None:
    with _lock:
        d = load()
        if d.pop(matter, None) is not None:
            _save(d)


def listing() -> list[dict]:
    """Cases whose key still exists: entries past the vault's lifetime are dropped (the vault deleted them)."""
    from katip_kalkan import vault
    ttl, now = vault.ttl_seconds(), time.time()
    with _lock:
        d = load()
        live = {m: t for m, t in d.items() if t + ttl > now}
        if len(live) != len(d):
            _save(live)
    return [{"matter": m, "last_used": t, "expires": t + ttl} for m, t in sorted(live.items(), key=lambda kv: -kv[1])]
