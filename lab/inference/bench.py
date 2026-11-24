"""Load generator and experiments for the toy Katip endpoint (katipserve.py).

Each experiment starts the server in its own process, replays one-page documents built from Katip's
synthetic test sets (blind + held-out, no real personal data) and writes JSON to lab/inference/results/.

    python lab/inference/bench.py parity      # batched server = SDK Masker.mask, document by document
    python lab/inference/bench.py capacity    # saturation throughput and open-loop p50/p95 per model
    python lab/inference/bench.py batching    # max batch x max wait at a fixed load
    python lab/inference/bench.py threads     # throughput per CPU core
    python lab/inference/bench.py cold        # process and model cold start, memory
    python lab/inference/bench.py recall      # int8 vs fp32 on the blind set's gold spans

Open loop: arrivals follow a Poisson process at a fixed rate, and latency is measured from the time a
request was due, so a slow server can't hide its queue (no coordinated omission).
"""
from __future__ import annotations

import gzip
import http.client
import json
import random
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / "results"
WORDS_PER_PAGE = 500  # Katip's page, as on the model cards

VARIANTS = [("nano", "int8"), ("mini", "int8"), ("base", "int8"), ("base", "fp32")]


# -- workload ---------------------------------------------------------------------------------------------
def documents(split: str) -> list[dict]:
    with gzip.open(ROOT / "ml" / "berturk" / "data" / f"{split}.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def pages(n: int = 200, seed: int = 0) -> list[str]:
    """n one-page documents: synthetic blind and held-out documents joined until 500 words."""
    docs = [d["text"] for d in documents("blind") + documents("heldout")]
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        parts, words = [], 0
        while words < WORDS_PER_PAGE:
            t = rng.choice(docs)
            parts.append(t)
            words += len(t.split())
        out.append("\n\n".join(parts))
    return out


# -- server process ---------------------------------------------------------------------------------------
class Server:
    def __init__(self, model: str, precision: str = "int8", port: int = 8811, **opts):
        self.port = port
        cmd = [sys.executable, str(HERE / "katipserve.py"), "--model", model, "--precision", precision,
               "--port", str(port)]
        for k, v in opts.items():
            if v is True:
                cmd.append("--" + k.replace("_", "-"))
            elif v is not None and v is not False:
                cmd += ["--" + k.replace("_", "-"), str(v)]
        self.t_spawn = time.perf_counter()
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(f"server did not start: {' '.join(cmd)}")
        self.ready = json.loads(line)
        self.spawn_to_ready_ms = (time.perf_counter() - self.t_spawn) * 1000

    def get(self, path: str) -> dict:
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        c.request("GET", path)
        return json.loads(c.getresponse().read())

    def post(self, path: str, body: dict | None = None) -> dict:
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=300)
        c.request("POST", path, json.dumps(body or {}).encode(), {"Content-Type": "application/json"})
        return json.loads(c.getresponse().read())

    def stop(self):
        self.proc.terminate()
        self.proc.wait(10)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.stop()


_local = threading.local()


def send(port: int, text: str, _retry: bool = True) -> dict:
    """One request on this thread's keep-alive connection; reconnects once if the server went away."""
    try:
        return _send(port, text)
    except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError):
        if not _retry:
            raise
        return send(port, text, _retry=False)


def _send(port: int, text: str) -> dict:
    c = getattr(_local, "conn", None)
    if c is None or getattr(_local, "port", None) != port:
        c = _local.conn = http.client.HTTPConnection("127.0.0.1", port, timeout=300)
        _local.port = port
    body = json.dumps({"text": text}).encode()
    try:
        c.request("POST", "/v1/mask", body, {"Content-Type": "application/json"})
        r = json.loads(c.getresponse().read())
    except (http.client.HTTPException, ConnectionError, OSError):
        _local.conn = None
        raise
    if "error" in r:
        raise RuntimeError(r["error"])
    return r


# -- load ---------------------------------------------------------------------------------------------------
def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarise(srv: Server, lat: list[float], words: list[int], parts: list[dict], wall: float, before: dict,
              after: dict, errors: int, **extra) -> dict:
    b0, b1 = before.get("batcher") or {}, after.get("batcher") or {}
    tokens = b1.get("tokens", 0) - b0.get("tokens", 0)
    batches = b1.get("batches", 0) - b0.get("batches", 0)
    windows = b1.get("windows", 0) - b0.get("windows", 0)
    busy = b1.get("busy_s", 0) - b0.get("busy_s", 0)
    padded = b1.get("padded_tokens", 0) - b0.get("padded_tokens", 0)
    n = len(lat)
    cpu = after.get("cpu_s", 0) - before.get("cpu_s", 0)
    pages_done = sum(words) / WORDS_PER_PAGE
    return {**extra, "cpu_cores_used": round(cpu / wall, 2),
            "cpu_s_per_1k_pages": round(cpu / pages_done * 1000, 1) if pages_done else None,
            "cpu_s_per_1m_tokens": round(cpu / tokens * 1e6, 1) if tokens else None, "model": after["model"], "requests": n, "errors": errors, "wall_s": round(wall, 2),
            "req_per_s": round(n / wall, 2), "pages_per_s": round(sum(words) / WORDS_PER_PAGE / wall, 2),
            "tokens_per_s": round(tokens / wall, 1),
            "p50_ms": round(pct(lat, .5), 1), "p95_ms": round(pct(lat, .95), 1), "p99_ms": round(pct(lat, .99), 1),
            "mean_batch": round(windows / batches, 2) if batches else None,
            "model_busy_share": round(busy / wall, 3), "padding_share": round(1 - tokens / padded, 3) if padded else None,
            "model_ms_p50": round(pct([p["model"] for p in parts], .5), 1),
            "rules_ms_p50": round(pct([p["rules"] for p in parts], .5), 1),
            "rss_mb": after.get("rss_mb"), "rss_peak_mb": after.get("rss_peak_mb")}


def closed_loop(srv: Server, docs: list[str], concurrency: int, seconds: float, **extra) -> dict:
    """Saturation: `concurrency` clients send back to back."""
    lat, words, parts, errors = [], [], [], [0]
    stop = time.perf_counter() + seconds
    lock = threading.Lock()

    def client(i):
        rng = random.Random(i)
        while time.perf_counter() < stop:
            t = time.perf_counter()
            try:
                r = send(srv.port, rng.choice(docs))
            except Exception:
                with lock:
                    errors[0] += 1
                continue
            with lock:
                lat.append((time.perf_counter() - t) * 1000)
                words.append(r["words"])
                parts.append(r["timing_ms"])

    before = srv.get("/metrics")
    t0 = time.perf_counter()
    with ThreadPoolExecutor(concurrency) as ex:
        list(ex.map(client, range(concurrency)))
    wall = time.perf_counter() - t0
    return summarise(srv, lat, words, parts, wall, before, srv.get("/metrics"), errors[0], mode="closed",
                     concurrency=concurrency, **extra)


def open_loop(srv: Server, docs: list[str], rate: float, seconds: float, seed: int = 1, **extra) -> dict:
    """Poisson arrivals at `rate` requests/s; latency counted from each request's due time."""
    rng = random.Random(seed)
    due, t = [], 0.0
    while True:
        t += rng.expovariate(rate)
        if t > seconds:
            break
        due.append(t)
    lat, words, parts, errors = [], [], [], [0]
    lock = threading.Lock()
    before = srv.get("/metrics")
    t0 = time.perf_counter()

    def fire(i):
        wait = t0 + due[i] - time.perf_counter()
        if wait > 0:
            time.sleep(wait)
        try:
            r = send(srv.port, docs[i % len(docs)])
        except Exception:
            with lock:
                errors[0] += 1
            return
        with lock:
            lat.append((time.perf_counter() - (t0 + due[i])) * 1000)
            words.append(r["words"])
            parts.append(r["timing_ms"])

    with ThreadPoolExecutor(256) as ex:
        list(ex.map(fire, range(len(due))))
    wall = max(time.perf_counter() - t0, seconds)
    return summarise(srv, lat, words, parts, wall, before, srv.get("/metrics"), errors[0], mode="open",
                     offered_rate=rate, **extra)


def warm(srv: Server, docs: list[str], n: int = 8):
    for d in docs[:n]:
        send(srv.port, d)


def save(name: str, data):
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote results/{name}.json", flush=True)


def log(row: dict):
    keys = ("model", "mode", "concurrency", "offered_rate", "max_batch", "max_wait_ms", "threads", "req_per_s",
            "pages_per_s", "tokens_per_s", "p50_ms", "p95_ms", "mean_batch", "rss_mb")
    print("  " + " ".join(f"{k}={row[k]}" for k in keys if k in row), flush=True)


# -- experiments --------------------------------------------------------------------------------------------
def exp_parity():
    """The batched server must give the SDK's own output: same masked text for every document."""
    sys.path.insert(0, str(ROOT / "sdk" / "python" / "src"))
    from katip_mask import Masker
    import re
    docs = [d["text"] for d in documents("blind") + documents("heldout")] + pages(20)
    tag = re.compile(r"\[[A-ZÇĞİÖŞÜ .]+-\d+\]")
    out = {}
    for model, prec in VARIANTS:
        runs = []
        for mb, mw in [(1, 0), (16, 20), (16, 20)]:  # unbatched, then batched twice (different neighbours)
            with Server(model, prec, max_batch=mb, max_wait_ms=mw) as srv:
                with ThreadPoolExecutor(16) as ex:  # concurrent, so windows really share batches
                    runs.append(list(ex.map(lambda d: send(srv.port, d)["text"], docs)))
                m = srv.get("/metrics")["batcher"]
        alone, b1, b2 = runs
        row = {"documents": len(docs), "mean_batch": round(m["windows"] / m["batches"], 2),
               "masks_unbatched": sum(len(tag.findall(t)) for t in alone),
               "batched_vs_unbatched_docs_different": sum(a != b for a, b in zip(alone, b1)),
               "batched_vs_unbatched_masks_changed": sum(abs(len(tag.findall(a)) - len(tag.findall(b)))
                                                         for a, b in zip(alone, b1)),
               "batched_run1_vs_run2_docs_different": sum(a != b for a, b in zip(b1, b2))}
        if prec == "int8":  # the SDK itself runs one window per call
            ref = Masker("ai", model=model)
            row["unbatched_vs_sdk_docs_different"] = sum(ref.mask(d).text != a for d, a in zip(docs, alone))
        out[f"{model}-{prec}"] = row
        print(model, prec, row, flush=True)
    save("parity", out)


def exp_capacity(seconds: float = 20):
    docs = pages()
    rows = []
    for model, prec in [("rules", "int8")] + VARIANTS:
        with Server(model, prec, max_batch=16, max_wait_ms=5, threads=4) as srv:
            warm(srv, docs)
            sat = closed_loop(srv, docs, concurrency=32, seconds=seconds, precision=prec)
            log(sat)
            rows.append(sat)
            cap = sat["req_per_s"]
            for load in (0.25, 0.5, 0.75, 0.9):
                r = open_loop(srv, docs, rate=cap * load, seconds=seconds, precision=prec, load=load)
                log(r)
                rows.append(r)
    save("capacity", rows)


def exp_batching(seconds: float = 20):
    docs = pages()
    rows = []
    for model in ("mini", "base"):
        with Server(model, max_batch=16, max_wait_ms=5, threads=4) as srv:
            warm(srv, docs)
            cap = closed_loop(srv, docs, 32, seconds / 2)["req_per_s"]
        rate = round(cap * 0.6, 2)  # a fixed offered load, 60% of the default setting's capacity
        for mb, mw in [(1, 0), (4, 2), (8, 5), (16, 5), (16, 20), (32, 50)]:
            with Server(model, max_batch=mb, max_wait_ms=mw, threads=4) as srv:
                warm(srv, docs)
                r = open_loop(srv, docs, rate, seconds, max_batch=mb, max_wait_ms=mw)
                s = closed_loop(srv, docs, 32, seconds / 2, max_batch=mb, max_wait_ms=mw)
                r["saturation_req_per_s"] = s["req_per_s"]
                r["saturation_pages_per_s"] = s["pages_per_s"]
                log(r)
                rows.append(r)
    save("batching", rows)


def exp_threads(seconds: float = 15):
    docs = pages()
    rows = []
    for model, prec in VARIANTS:
        for th in (1, 2, 4, 6):
            with Server(model, prec, max_batch=16, max_wait_ms=5, threads=th) as srv:
                warm(srv, docs)
                r = closed_loop(srv, docs, 32, seconds, precision=prec, threads=th)
                log(r)
                rows.append(r)
    save("threads", rows)


def exp_cold(repeats: int = 5):
    docs = pages()
    rows = []
    for model, prec in [("rules", "int8")] + VARIANTS:
        for i in range(repeats):
            srv = Server(model, prec, lazy=True, idle_unload=600)
            try:
                idle = srv.get("/metrics")
                t = time.perf_counter()
                first = send(srv.port, docs[0])
                first_ms = (time.perf_counter() - t) * 1000
                cold_process_ms = srv.spawn_to_ready_ms + first_ms
                t = time.perf_counter()
                warm_r = send(srv.port, docs[0])
                warm_ms = (time.perf_counter() - t) * 1000
                loaded = srv.get("/metrics")
                srv.post("/admin/unload")
                unloaded = srv.get("/metrics")
                t = time.perf_counter()
                send(srv.port, docs[0])
                reload_ms = (time.perf_counter() - t) * 1000
                b = srv.get("/metrics").get("batcher") or {}
                row = {"model": loaded["model"], "run": i,
                       "spawn_to_ready_ms": round(srv.spawn_to_ready_ms, 1),
                       "first_request_ms": round(first_ms, 1), "process_cold_ms": round(cold_process_ms, 1),
                       "warm_request_ms": round(warm_ms, 1), "model_reload_request_ms": round(reload_ms, 1),
                       "session_load_ms": b.get("load_ms"),
                       "rss_idle_mb": idle["rss_mb"], "rss_loaded_mb": loaded["rss_mb"],
                       "rss_after_unload_mb": unloaded["rss_mb"], "first_was_cold": first["cold"]}
                print(" ", row, flush=True)
                rows.append(row)
            finally:
                srv.stop()
    save("cold", rows)


def exp_recall():
    """Agreement of int8 and fp32 Base, and names found on the blind set (rules + model, profile ai)."""
    sys.path.insert(0, str(ROOT / "sdk" / "python" / "src"))
    docs = documents("blind") + documents("heldout")
    out = {}
    spans = {}
    for model, prec in [("rules", "int8")] + VARIANTS:
        with Server(model, prec, max_batch=1, max_wait_ms=0) as srv:
            res = [send(srv.port, d["text"]) for d in docs]
            label = res[0]["model"]
        spans[label] = [r["text"] for r in res]
        names = found = 0
        for d, r in zip(docs, res):
            for s, e, t in d["spans"]:
                if t == "PERSON":
                    names += 1
                    found += d["text"][s:e] not in r["text"]
        out[label] = {"documents": len(docs), "names": names, "names_hidden": found}
        print(label, out[label], flush=True)
    a, b = spans["base-int8"], spans["base-fp32"]
    out["base_int8_vs_fp32_same_output"] = sum(x == y for x, y in zip(a, b))
    save("recall", out)


if __name__ == "__main__":
    which = sys.argv[1:] or ["parity"]
    for w in which:
        globals()[f"exp_{w}"]()
