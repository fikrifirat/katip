"""The re-identification map ("vault"): placeholder -> real value, kept only on this device.

* One vault per matter (dosya), so every document of the same case uses the same
  placeholders: "Ahmet Yılmaz" is [AD SOYAD-1] in the petition and in the expert report.
* Stored encrypted at rest with AES-256-GCM. The key lives in the macOS Keychain when
  available, otherwise in ~/.katip/key with 0600 permissions.
* File names are an HMAC of the matter name, because a matter name ("Yılmaz boşanma")
  can itself be personal data.
* If the `cryptography` package is missing, vaults are never written to disk: they live
  in memory for the session only. We fail private, not open.
* Vaults expire (KATIP_VAULT_DAYS, default 30) and `forget` deletes them.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover - exercised by test with a monkeypatch
    AESGCM = None

KEYCHAIN_SERVICE = "katip-kalkan-vault"
_memory: dict[str, dict] = {}


def katip_home() -> Path:
    p = Path(os.environ.get("KATIP_HOME", Path.home() / ".katip"))
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p


def _keychain_get() -> bytes | None:
    if sys.platform != "darwin" or os.environ.get("KATIP_NO_KEYCHAIN"):
        return None
    r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return base64.b64decode(r.stdout.strip())
    key = AESGCM.generate_key(bit_length=256)
    r = subprocess.run(["security", "add-generic-password", "-s", KEYCHAIN_SERVICE, "-a", "katip",
                        "-w", base64.b64encode(key).decode()], capture_output=True)
    return key if r.returncode == 0 else None


def _key() -> bytes:
    k = _keychain_get()
    if k:
        return k
    f = katip_home() / "key"
    if not f.exists():
        fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(secrets.token_bytes(32))
    return f.read_bytes()


def persistent() -> bool:
    return AESGCM is not None and not os.environ.get("KATIP_VAULT_MEMORY_ONLY")


def _file_id(matter: str) -> str:
    # keyed hash: the on-disk name reveals nothing about the matter
    return hmac.new(_key(), matter.encode(), hashlib.sha256).hexdigest()[:32]


def _path(matter: str) -> Path:
    d = katip_home() / "vault"
    d.mkdir(exist_ok=True, mode=0o700)
    return d / f"{_file_id(matter)}.bin"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).casefold()


class Vault:
    def __init__(self, matter: str, data: dict | None = None):
        self.matter = matter
        d = data or {}
        self.labels: dict[str, str] = d.get("labels", {})        # "TYPE|norm text" -> label
        self.values: dict[str, str] = d.get("values", {})        # label -> original text (first seen form)
        self.counters = defaultdict(int, d.get("counters", {}))
        self.docs: dict[str, dict] = d.get("docs", {})           # doc_id -> {name, at}
        self.created = d.get("created", time.time())

    # ---------------------------------------------------------------- masking
    def label_for(self, entity_type: str, text: str) -> str:
        from .engine import label_name
        key = f"{entity_type}|{_norm(text)}"
        if key not in self.labels:
            self.counters[entity_type] += 1
            label = f"[{label_name(entity_type)}-{self.counters[entity_type]}]"
            self.labels[key] = label
            self.values[label] = text.strip()
        return self.labels[key]

    def mask(self, text: str, spans: list[dict]) -> str:
        out, pos = [], 0
        for sp in sorted(spans, key=lambda s: (s["start"], -s["end"])):
            if sp["start"] < pos:
                continue
            out.append(text[pos:sp["start"]])
            out.append(self.label_for(sp["entity_type"], sp["text"]))
            pos = sp["end"]
        out.append(text[pos:])
        return "".join(out)

    def unmask(self, text: str) -> tuple[str, int]:
        if not self.values:
            return text, 0
        pat = re.compile("|".join(re.escape(k) for k in sorted(self.values, key=len, reverse=True)))
        n = 0

        def sub(m):
            nonlocal n
            n += 1
            return self.values[m.group(0)]
        return pat.sub(sub, text), n

    # ---------------------------------------------------------------- storage
    def to_json(self) -> dict:
        return {"labels": self.labels, "values": self.values, "counters": dict(self.counters),
                "docs": self.docs, "created": self.created}

    def save(self) -> None:
        if not persistent():
            _memory[self.matter] = self.to_json()
            return
        nonce = secrets.token_bytes(12)
        blob = AESGCM(_key()).encrypt(nonce, json.dumps(self.to_json()).encode(), self.matter.encode())
        p = _path(self.matter)
        tmp = p.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(b"KV1" + nonce + blob)
        os.replace(tmp, p)


def ttl_seconds() -> float:
    return float(os.environ.get("KATIP_VAULT_DAYS", 30)) * 86400


def open_vault(matter: str) -> Vault:
    matter = matter or "default"
    if not persistent():
        return Vault(matter, _memory.get(matter))
    p = _path(matter)
    if not p.exists():
        return Vault(matter)
    raw = p.read_bytes()
    if raw[:3] != b"KV1":
        raise RuntimeError("unknown vault format")
    data = json.loads(AESGCM(_key()).decrypt(raw[3:15], raw[15:], matter.encode()))
    if time.time() - data.get("created", 0) > ttl_seconds():
        p.unlink()
        return Vault(matter)
    return Vault(matter, data)


def forget(matter: str) -> bool:
    matter = matter or "default"
    hit = _memory.pop(matter, None) is not None
    if persistent():
        p = _path(matter)
        if p.exists():
            p.unlink()
            hit = True
    return hit


def purge_expired() -> int:
    if not persistent():
        return 0
    n = 0
    for p in (katip_home() / "vault").glob("*.bin") if (katip_home() / "vault").exists() else []:
        if time.time() - p.stat().st_mtime > ttl_seconds():
            p.unlink()
            n += 1
    return n


# ---------------------------------------------------------------- share codes (ChatGPT path)
def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


DROP_AAD = b"katip-drop-v1"


def seal_for_relay(masked_text: str) -> tuple[bytes, bytes, bytes]:
    """Encrypt masked text with a fresh one-time key. Returns (key, nonce, ciphertext).
    The relay only ever stores nonce+ciphertext; the key travels in the share code."""
    if AESGCM is None:
        raise RuntimeError("sharing needs the `cryptography` package")
    key, nonce = AESGCM.generate_key(bit_length=128), secrets.token_bytes(12)
    return key, nonce, AESGCM(key).encrypt(nonce, masked_text.encode(), DROP_AAD)


def open_sealed(key: bytes, nonce: bytes, ct: bytes) -> str:
    return AESGCM(key).decrypt(nonce, ct, DROP_AAD).decode()
