"""Look at the Katip folder every few seconds: mask new files in 1 Gelen, restore new answers in 3.

A plain scan instead of OS file events: it needs no extra service, works the same on Mac and Windows and on
network drives, and a file is only picked up once its size has stopped changing (a copy in progress or a
download still being written is left alone)."""
from __future__ import annotations

import threading
import time
import traceback
from pathlib import Path

from . import layout, pipeline, store


class Watcher:
    def __init__(self, interval: float = 3.0, on_change=None):
        self.interval = interval
        self.on_change = on_change or (lambda: None)
        self._seen: dict[str, tuple[int, float]] = {}
        self._stop = threading.Event()
        self._kick = threading.Event()
        self.busy: str | None = None
        self.last_error: str | None = None

    def _stable(self, p: Path) -> bool:
        st = p.stat()
        sig = (st.st_size, st.st_mtime)
        prev = self._seen.get(str(p))
        self._seen[str(p)] = sig
        return prev == sig and st.st_size > 0

    def scan_once(self, wait_stable: bool = True) -> int:
        settings = store.load_settings()
        root = layout.ensure(store.folder(settings))
        done = 0
        for p in layout.files_in(root, layout.INBOX, layout.INPUT_EXT):
            if wait_stable and not self._stable(p):
                continue
            case = layout.case_of(root, p, layout.INBOX)
            job = store.load_jobs(case).get(pipeline.job_key(root, p))
            if job and job["sha"] == pipeline.sha256(p.read_bytes()):
                continue
            self.busy = layout.nfc(p.name)
            self.on_change()
            try:
                pipeline.process(root, p, settings)
            finally:
                self.busy = None
            done += 1
            self.on_change()
        for p in layout.files_in(root, layout.ANSWERS, layout.ANSWER_EXT):
            if wait_stable and not self._stable(p):
                continue
            res = pipeline.restore_file(root, p)
            if res.get("error"):
                self.last_error = f"{layout.nfc(p.name)}: {res['error']}"
            elif not res.get("skipped"):
                done += 1
                self.on_change()
        return done

    def kick(self) -> None:
        self._kick.set()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self.last_error = None
                self.scan_once()
            except Exception:  # noqa: BLE001 - keep watching; the error shows in the window
                self.last_error = traceback.format_exc(limit=3)
            self._kick.wait(self.interval)
            self._kick.clear()

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self.run, name="katip-watcher", daemon=True)
        t.start()
        return t

    def stop(self) -> None:
        self._stop.set()
        self._kick.set()
