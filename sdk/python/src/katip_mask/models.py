"""Katip Mask models: download once from Hugging Face at a pinned commit, verify every file's SHA-256,
then run fully offline.

Cache: $KATIP_MASK_CACHE, else $XDG_CACHE_HOME/katip-mask, else ~/.cache/katip-mask. The layout is
<cache>/<model>/<revision>/<file>, the same as the JavaScript SDK in Node, so both share one download.
Set KATIP_MASK_OFFLINE=1 to forbid downloads; set KATIP_MASK_ENDPOINT (or HF_ENDPOINT) for a mirror.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from importlib import resources
from pathlib import Path

SPEC = json.loads(resources.files("katip_mask.spec").joinpath("models.json").read_text("utf-8"))
MODELS: dict[str, dict] = SPEC["models"]
FILES = ("config.json", "tokenizer.json", "onnx/model_quantized.onnx")


class ModelError(RuntimeError):
    pass


def cache_dir() -> Path:
    if os.environ.get("KATIP_MASK_CACHE"):
        return Path(os.environ["KATIP_MASK_CACHE"]).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "katip-mask"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _url(info: dict, file: str) -> str:
    endpoint = (os.environ.get("KATIP_MASK_ENDPOINT") or os.environ.get("HF_ENDPOINT") or SPEC["endpoint"]).rstrip("/")
    return f"{endpoint}/{info['repo']}/resolve/{info['revision']}/{file}"


def model_path(name: str, *, download: bool = True, progress=None) -> Path:
    """Folder with the verified files of a Katip Mask model ("mini", "nano" or "base"), downloading
    them first if needed (unless download=False or KATIP_MASK_OFFLINE=1)."""
    if name not in MODELS:
        raise ModelError(f"unknown model {name!r}: use one of {', '.join(MODELS)} or a local folder")
    info = MODELS[name]
    folder = cache_dir() / name / info["revision"]
    offline = not download or os.environ.get("KATIP_MASK_OFFLINE", "").lower() in ("1", "true", "yes")
    for file in FILES:
        want = info["files"][file]
        dst = folder / file
        if dst.exists() and dst.stat().st_size == want["size"] and _sha256(dst) == want["sha256"]:
            continue
        if offline:
            raise ModelError(f"{info['name']} is not downloaded and downloads are off: run `katip-mask download {name}`"
                             f" while online, or point KATIP_MASK_CACHE at a folder that has it")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if progress:
            progress(f"downloading {info['name']}: {file} ({want['size'] / 1e6:.1f} MB)")
        fd, tmp = tempfile.mkstemp(dir=dst.parent, prefix=".part-")
        try:
            h = hashlib.sha256()
            req = urllib.request.Request(_url(info, file), headers={"User-Agent": "katip-mask"})
            with urllib.request.urlopen(req, timeout=60) as r, os.fdopen(fd, "wb") as out:
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    h.update(chunk)
                    out.write(chunk)
            if h.hexdigest() != want["sha256"]:
                raise ModelError(f"{info['name']}: {file} does not match its pinned SHA-256; refusing to use it")
            os.replace(tmp, dst)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return folder


def download_model(name: str, progress=print) -> Path:
    """Download and verify a model now (e.g. while building a container image), so later runs work offline."""
    return model_path(name, download=True, progress=progress)
