"""A toy Katip masking endpoint, built to measure serving economics.

One HTTP endpoint (POST /v1/mask) runs the full katip-mask pipeline: Katip's rules, one name model and the
leak check, exactly as `Masker.mask()` does. Only the model step changes: instead of one ONNX call per
256-token window, every window from every request goes into one queue, and a single model worker runs
them in padded batches (dynamic batching). Two knobs set the batcher: --max-batch (windows per ONNX call)
and --max-wait-ms (how long the first window in a batch waits for company).

Scale to zero: with --idle-unload S the ONNX session is dropped after S seconds without work and loaded
again on the next window, so the first request after a quiet spell pays the model's cold start.

The SDK's own decoding runs unchanged: the server gives katip_mask.ner.NameModel a session object whose
run() hands the window to the batcher and waits for its row of logits.

    python lab/inference/katipserve.py --model mini --port 8811
    curl -s localhost:8811/v1/mask -d '{"text": "Davacı Ahmet YILMAZ ..."}'

Standard library plus numpy and onnxruntime (pip install "katip-mask[model]").
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import queue
import resource
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sdk" / "python" / "src"))

import numpy as np  # noqa: E402
import onnxruntime as ort  # noqa: E402
from katip_mask import Masker  # noqa: E402
from katip_mask.models import MODELS, model_path  # noqa: E402
from katip_mask.ner import NameModel, WordPiece  # noqa: E402


def rss_mb() -> float:
    """Resident memory of this process now (psutil if present, else the peak from getrusage)."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / 2**20
    except Exception:
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / 2**20 if sys.platform == "darwin" else peak / 1024


def model_files(name: str, precision: str) -> tuple[Path, Path]:
    """(model folder, ONNX file) for nano / mini / base at the SDK's pinned commit, int8 or fp32."""
    folder = model_path(name)  # downloaded once, verified by SHA-256
    if precision == "int8":
        return folder, folder / "onnx" / "model_quantized.onnx"
    # fp32 is published for Base only, outside the SDK's pinned file list
    from huggingface_hub import hf_hub_download
    onnx = hf_hub_download(MODELS[name]["repo"], "onnx/model.onnx", revision=MODELS[name]["revision"])
    return folder, Path(onnx)


class Batcher:
    """One model worker: a queue of windows, padded batches, lazy load and idle unload."""

    def __init__(self, onnx: Path, max_batch: int, max_wait_ms: float, threads: int, idle_unload: float | None):
        self.onnx, self.max_batch, self.max_wait = onnx, max_batch, max_wait_ms / 1000
        self.threads, self.idle_unload = threads, idle_unload
        self.q: queue.Queue = queue.Queue()
        self.sess = None
        self.lock = threading.Lock()
        self.last_used = time.monotonic()
        self.stats = {"loads": 0, "unloads": 0, "load_ms": [], "batches": 0, "windows": 0, "tokens": 0,
                      "padded_tokens": 0, "busy_s": 0.0, "batch_sizes": {}}
        threading.Thread(target=self._loop, daemon=True).start()
        if idle_unload:
            threading.Thread(target=self._reaper, daemon=True).start()

    # -- model lifecycle ---------------------------------------------------------------------------------
    def load(self) -> float:
        t = time.perf_counter()
        so = ort.SessionOptions()
        so.intra_op_num_threads = self.threads
        so.inter_op_num_threads = 1
        so.log_severity_level = 3
        sess = ort.InferenceSession(str(self.onnx), so, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in sess.get_inputs()}
        self.sess = sess
        ms = (time.perf_counter() - t) * 1000
        self.stats["loads"] += 1
        self.stats["load_ms"].append(round(ms, 1))
        return ms

    def unload(self) -> None:
        with self.lock:
            if self.sess is not None:
                self.sess = None
                gc.collect()
                self.stats["unloads"] += 1

    def _reaper(self) -> None:
        while True:
            time.sleep(min(1.0, self.idle_unload / 4))
            if self.sess is not None and self.q.empty() and time.monotonic() - self.last_used > self.idle_unload:
                self.unload()

    # -- batching ----------------------------------------------------------------------------------------
    def submit(self, ids: np.ndarray) -> np.ndarray:
        slot = {"ids": ids, "done": threading.Event(), "t": time.perf_counter()}
        self.q.put(slot)
        slot["done"].wait()
        if "error" in slot:
            raise slot["error"]
        return slot["logits"]

    def _take(self) -> list[dict]:
        batch = [self.q.get()]
        deadline = time.perf_counter() + self.max_wait
        while len(batch) < self.max_batch:
            left = deadline - time.perf_counter()
            try:
                batch.append(self.q.get(timeout=left) if left > 0 else self.q.get_nowait())
            except queue.Empty:
                break
        return batch

    def _loop(self) -> None:
        while True:
            batch = self._take()
            try:
                with self.lock:
                    if self.sess is None:
                        self.load()
                    t = time.perf_counter()
                    lens = [len(s["ids"]) for s in batch]
                    width = max(lens)
                    ids = np.zeros((len(batch), width), dtype=np.int64)  # [PAD] is 0 in all three vocabularies
                    mask = np.zeros_like(ids)
                    for i, s in enumerate(batch):
                        ids[i, :lens[i]] = s["ids"]
                        mask[i, :lens[i]] = 1
                    feed = {"input_ids": ids, "attention_mask": mask}
                    if "token_type_ids" in self.inputs:
                        feed["token_type_ids"] = np.zeros_like(ids)
                    logits = self.sess.run(None, feed)[0]
                    busy = time.perf_counter() - t
                st = self.stats
                st["batches"] += 1
                st["windows"] += len(batch)
                st["tokens"] += sum(lens)
                st["padded_tokens"] += width * len(batch)
                st["busy_s"] += busy
                st["batch_sizes"][len(batch)] = st["batch_sizes"].get(len(batch), 0) + 1
                for i, s in enumerate(batch):
                    s["logits"] = logits[i:i + 1, :lens[i]]
            except Exception as e:  # pragma: no cover - surfaced to the request
                for s in batch:
                    s["error"] = e
            self.last_used = time.monotonic()
            for s in batch:
                s["done"].set()


class BatchedSession:
    """Stands in for ort.InferenceSession inside the SDK's NameModel: one window in, its logits out."""

    def __init__(self, batcher: Batcher):
        self.batcher = batcher

    def run(self, _outputs, feed):
        return [self.batcher.submit(feed["input_ids"][0])]


def make_model(folder: Path, batcher: Batcher, label: str) -> NameModel:
    m = object.__new__(NameModel)  # the SDK class, without its own eager ONNX session
    m.np = np
    m.folder = folder
    m.name = label
    m.config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    m.id2label = {int(k): v for k, v in m.config["id2label"].items()}
    m.tok = WordPiece(json.loads((folder / "tokenizer.json").read_text(encoding="utf-8")))
    m.inputs = {"input_ids", "attention_mask"}
    m.max_tokens = int((m.config.get("katip") or {}).get("max_tokens", 500))
    m.sess = BatchedSession(batcher)
    return m


class Service:
    def __init__(self, args):
        self.started = time.perf_counter()
        self.profile = args.profile
        self.model_name = args.model
        self.masker = Masker(args.profile)  # rules; the model spans come from the batched model below
        self.batcher = self.model = None
        if args.model != "rules":
            folder, onnx = model_files(args.model, args.precision)
            self.batcher = Batcher(onnx, args.max_batch, args.max_wait_ms, args.threads, args.idle_unload)
            self.model = make_model(folder, self.batcher, f"{args.model}-{args.precision}")
            self.masker._trust = MODELS[args.model]["trust"]
            if not args.lazy:
                self.batcher.load()
        self.label = f"{args.model}-{args.precision}" if args.model != "rules" else "rules"
        self.lock = threading.Lock()
        self.served = 0
        self.rss_peak = rss_mb()

    def mask(self, text: str) -> dict:
        t0 = time.perf_counter()
        b = self.batcher
        before = (b.stats["windows"], b.stats["tokens"]) if b else (0, 0)
        cold = bool(b and b.sess is None)
        extra = [list(x) for x in self.model.spans(text, self.masker.threshold)] if self.model else []
        t1 = time.perf_counter()
        res = self.masker._mask(text, extra=extra)
        t2 = time.perf_counter()
        words = len(text.split())
        with self.lock:
            self.served += 1
            self.rss_peak = max(self.rss_peak, rss_mb()) if self.served % 50 == 0 else self.rss_peak
        return {"text": res.text, "spans": len(res.spans), "model": self.label, "words": words,
                "timing_ms": {"model": round((t1 - t0) * 1000, 2), "rules": round((t2 - t1) * 1000, 2),
                              "total": round((t2 - t0) * 1000, 2)},
                "cold": cold}

    def metrics(self) -> dict:
        ru = resource.getrusage(resource.RUSAGE_SELF)
        out = {"model": self.label, "served": self.served, "rss_mb": round(rss_mb(), 1),
               "cpu_s": round(ru.ru_utime + ru.ru_stime, 3),
               "rss_peak_mb": round(max(self.rss_peak, rss_mb()), 1),
               "uptime_s": round(time.perf_counter() - self.started, 1)}
        if self.batcher:
            st = dict(self.batcher.stats)
            st["loaded"] = self.batcher.sess is not None
            out["batcher"] = st
        return out


def handler(svc: Service):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, code: int, body: dict):
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/healthz":
                self._send(200, {"ok": True})
            elif self.path == "/metrics":
                self._send(200, svc.metrics())
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path == "/admin/unload" and svc.batcher:
                svc.batcher.unload()
                return self._send(200, svc.metrics())
            if self.path != "/v1/mask":
                return self._send(404, {"error": "not found"})
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                self._send(200, svc.mask(str(body["text"])))
            except Exception as e:
                self._send(500, {"error": f"{e.__class__.__name__}: {e}"})

    return H


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", default="mini", choices=["nano", "mini", "base", "rules"])
    ap.add_argument("--precision", default="int8", choices=["int8", "fp32"])
    ap.add_argument("--profile", default="ai", choices=["ai", "court", "anon"])
    ap.add_argument("--max-batch", type=int, default=16)
    ap.add_argument("--max-wait-ms", type=float, default=5.0)
    ap.add_argument("--threads", type=int, default=4, help="onnxruntime intra-op threads (CPU cores for the model)")
    ap.add_argument("--idle-unload", type=float, default=None, help="unload the model after this many idle seconds")
    ap.add_argument("--lazy", action="store_true", help="load the model on the first request, not at start")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8811)
    args = ap.parse_args(argv)
    svc = Service(args)
    srv = ThreadingHTTPServer((args.host, args.port), handler(svc))
    srv.daemon_threads = True
    print(json.dumps({"ready": True, "port": args.port, "model": svc.label,
                      "startup_ms": round((time.perf_counter() - svc.started) * 1000, 1)}), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
