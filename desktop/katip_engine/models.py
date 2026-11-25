"""Name models: which are on this Mac, and downloading Mini or Base with progress.

Downloads go through the pinned katip-mask SDK, which checks every file against its SHA-256 before use. Nano is
included with Kalkan, so the engine always works offline.
"""
from __future__ import annotations

import threading
from pathlib import Path

ORDER = ("nano", "mini", "base")
_lock = threading.Lock()
_job: dict | None = None


def _spec(name: str) -> dict:
    from katip_mask import models
    return models.MODELS[name]


def size_bytes(name: str) -> int:
    return sum(f["size"] for f in _spec(name)["files"].values())


def downloaded(name: str, verify: bool = False) -> bool:
    """On this Mac? A size check for listings (cheap enough to poll); verify=True hashes every file, as the SDK
    does before a model is used."""
    if name == "nano":
        return True  # bundled with Kalkan
    if name not in ORDER:  # a model folder the lawyer added
        return is_model_folder(Path(name))
    from katip_mask import models
    if verify:
        try:
            models.model_path(name, download=False)
            return True
        except Exception:  # noqa: BLE001 - missing or not matching its fingerprint
            return False
    info = _spec(name)
    folder = models.cache_dir() / name / info["revision"]
    return all((folder / f).is_file() and (folder / f).stat().st_size == w["size"] for f, w in info["files"].items())


def is_model_folder(folder: Path) -> bool:
    return (folder / "config.json").is_file() and (folder / "tokenizer.json").is_file() and \
        (folder / "onnx" / "model_quantized.onnx").is_file()


def _folder_mb(folder: Path) -> float:
    try:
        return round(sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) / 1e6, 1)
    except OSError:
        return 0.0


def delete(name: str) -> None:
    """Remove a downloaded Mini or Base (it can be downloaded again); Nano is part of the app."""
    import shutil

    from katip_mask import models
    shutil.rmtree(models.cache_dir() / name, ignore_errors=True)


def listing(current: str, custom: list[str] = ()) -> dict:
    out = []
    for n in ORDER:
        out.append({"name": n, "size_mb": round(size_bytes(n) / 1e6, 1), "downloaded": downloaded(n),
                    "included": n == "nano", "recommended": n == "base", "current": n == current, "custom": False})
    for p in custom:
        f = Path(p)
        ok = is_model_folder(f)
        out.append({"name": p, "size_mb": _folder_mb(f) if ok else 0.0, "downloaded": ok, "included": False,
                    "recommended": False, "current": p == current, "custom": True})
    with _lock:
        job = dict(_job) if _job else None
    return {"current": current, "models": out, "download": job}


def _fetch(name: str, progress) -> Path:
    """Download with byte progress: the SDK writes each file to a .part- file next to its final place."""
    from katip_mask import models
    info = _spec(name)
    folder = models.cache_dir() / name / info["revision"]
    total = size_bytes(name)
    stop = threading.Event()

    def watch():
        while not stop.wait(0.25):
            done = sum(p.stat().st_size for p in folder.glob("*") if p.is_file()) if folder.is_dir() else 0
            progress(min(done, total), total)

    t = threading.Thread(target=watch, daemon=True)
    t.start()
    try:
        return models.model_path(name, download=True)
    finally:
        stop.set()
        t.join()
        progress(total, total)


def start_download(name: str, on_done=None) -> dict:
    """Start downloading in the background; GET /v1/models shows how far it got."""
    global _job
    if name not in ORDER:
        raise ValueError(f"model must be one of {', '.join(ORDER)}")
    with _lock:
        if _job and _job["state"] == "running":
            return dict(_job)
        _job = {"name": name, "state": "running", "done": 0, "total": size_bytes(name), "error": None}
        job = dict(_job)

    def progress(done: int, total: int):
        with _lock:
            _job.update(done=done, total=total)

    def run():
        try:
            _fetch(name, progress)
            if on_done:
                on_done(name)  # switch first, so whoever sees "done" also sees the new model in the settings
            with _lock:
                _job.update(state="done", done=_job["total"])
        except Exception as e:  # noqa: BLE001 - offline, mirror down, fingerprint mismatch
            with _lock:
                _job.update(state="failed", error=e.__class__.__name__)

    threading.Thread(target=run, daemon=True).start()
    return job
