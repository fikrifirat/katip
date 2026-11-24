"""Turn lab/inference/results/*.json into the tables in RESULTS.md (prints Markdown).

Costs: a machine's list price per hour divided by the measured work it does in that hour. Two ways:
  * "measured box": the Mac's own measured pages/s on 4 model threads, priced as if it were each machine.
  * "CPU-seconds": the server's measured CPU time per page (all threads, rules included) times the
    machine's price per vCPU-second. This assumes a cloud vCPU does the work of one Mac core, which we
    have not measured; a slower vCPU raises the cost in proportion.
Both price a machine kept busy all hour. At utilisation u the cost per page is divided by u.

    python lab/inference/report.py > /tmp/tables.md
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

R = Path(__file__).resolve().parent / "results"

# Public list prices read on 24 Nov 2026 (sources in RESULTS.md). Laptop: 36-month straight-line, 24/7.
# Each machine keeps its own currency; nothing is converted.
MACHINES = [
    # name, vCPU, price per hour, currency
    ("AWS c7g.xlarge, London (Graviton3)", 4, 0.1717, "$"),
    ("Hetzner CAX21 (shared ARM)", 4, 0.0176, "€"),
    ("Hetzner CCX23 (dedicated AMD)", 4, 0.1178, "€"),
    ("MacBook Pro 14 M5 Pro, £2,499 over 36 months", 12, 2499 / (36 * 730), "£"),
]

# KVKK-Bench v0.1.2, published on the model cards (re-scored 19 Nov 2026)
BENCH = {"nano": {"overall": 85.9, "f2": 80.8, "leaked": 7.0, "mb": 2.6},
         "mini": {"overall": 93.0, "f2": 89.0, "leaked": 4.3, "mb": 31.1},
         "base": {"overall": 96.1, "f2": 93.2, "leaked": 3.1, "mb": 110.8}}


def load(name):
    p = R / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def money(x, cur):
    return f"{cur}{x:.4f}" if x < 0.1 else f"{cur}{x:.3f}" if x < 1 else f"{cur}{x:.2f}"


def main():
    cap = load("capacity") or []
    sat = {r["model"]: r for r in cap if r["mode"] == "closed"}
    print("## Capacity (4 model threads, max batch 16, max wait 5 ms)\n")
    print("| Model | Pages/s | Tokens/s | CPU cores used | CPU-s per 1k pages | p50 at sat. ms | p95 at sat. ms | Mean batch |")
    print("|---|---|---|---|---|---|---|---|")
    for m, r in sat.items():
        print(f"| {m} | {r['pages_per_s']} | {r['tokens_per_s']} | {r['cpu_cores_used']} | {r['cpu_s_per_1k_pages']} | "
              f"{r['p50_ms']} | {r['p95_ms']} | {r['mean_batch']} |")
    print("\n## Latency under open-loop load (share of saturation)\n")
    print("| Model | Load | Offered req/s | Pages/s | p50 ms | p95 ms | p99 ms | Mean batch |")
    print("|---|---|---|---|---|---|---|---|")
    for r in cap:
        if r["mode"] == "open":
            print(f"| {r['model']} | {int(r['load'] * 100)}% | {r['offered_rate']:.1f} | {r['pages_per_s']} | {r['p50_ms']} | "
                  f"{r['p95_ms']} | {r['p99_ms']} | {r['mean_batch']} |")

    th = load("threads") or []
    if th:
        print("\n## Threads (closed loop, 32 clients)\n")
        print("| Model | Threads | Pages/s | CPU cores used | CPU-s per 1k pages | p95 ms |")
        print("|---|---|---|---|---|---|")
        for r in th:
            print(f"| {r['model']} | {r['threads']} | {r['pages_per_s']} | {r['cpu_cores_used']} | {r['cpu_s_per_1k_pages']} | {r['p95_ms']} |")

    bt = load("batching") or []
    if bt:
        print("\n## Batching window (open loop at 60% of the default setting's capacity)\n")
        print("| Model | Max batch | Max wait ms | Mean batch | p50 ms | p95 ms | Saturation pages/s |")
        print("|---|---|---|---|---|---|---|")
        for r in bt:
            print(f"| {r['model']} | {r['max_batch']} | {r['max_wait_ms']} | {r['mean_batch']} | {r['p50_ms']} | {r['p95_ms']} | "
                  f"{r['saturation_pages_per_s']} |")

    cold = load("cold") or []
    if cold:
        print("\n## Cold start and memory (median of runs)\n")
        print("| Model | Spawn to ready ms | First request ms | Process cold total ms | Warm request ms | Model reload request ms | ONNX load ms | RSS idle MB | RSS loaded MB | RSS after unload MB |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        by = {}
        for r in cold:
            by.setdefault(r["model"], []).append(r)
        for m, rs in by.items():
            med = lambda k: statistics.median(r[k] for r in rs)  # noqa: E731
            loads = [x for r in rs for x in (r["session_load_ms"] or [])]
            print(f"| {m} | {med('spawn_to_ready_ms'):.0f} | {med('first_request_ms'):.0f} | {med('process_cold_ms'):.0f} | "
                  f"{med('warm_request_ms'):.0f} | {med('model_reload_request_ms'):.0f} | "
                  f"{statistics.median(loads):.0f} | {med('rss_idle_mb'):.0f} | {med('rss_loaded_mb'):.0f} | {med('rss_after_unload_mb'):.0f} |"
                  if loads else
                  f"| {m} | {med('spawn_to_ready_ms'):.0f} | {med('first_request_ms'):.0f} | {med('process_cold_ms'):.0f} | "
                  f"{med('warm_request_ms'):.0f} | – | – | {med('rss_idle_mb'):.0f} | {med('rss_loaded_mb'):.0f} | – |")

    if sat:
        print("\n## Cost per 1,000 pages, machine fully busy\n")
        print("Measured box = the Mac's measured pages/s priced at each machine's hourly rate. "
              "CPU-seconds = measured CPU time per page x price per vCPU-second.\n")
        head = "| Model | " + " | ".join(f"{n}: box / CPU-s" for n, *_ in MACHINES) + " | per 1M tokens (CPU-s, AWS) |"
        print(head)
        print("|" + "---|" * (len(MACHINES) + 2))
        for m, r in sat.items():
            cells = []
            for name, vcpu, ph, cur in MACHINES:
                box = ph / (r["pages_per_s"] * 3600) * 1000
                cpu = r["cpu_s_per_1k_pages"] * ph / vcpu / 3600
                cells.append(f"{money(box, cur)} / {money(cpu, cur)}")
            aws = MACHINES[0]
            tok = r["cpu_s_per_1m_tokens"] * aws[2] / aws[1] / 3600 if r.get("cpu_s_per_1m_tokens") else None
            print(f"| {m} | " + " | ".join(cells) + f" | {money(tok, '$') if tok else '–'} |")

    rec = load("recall")
    par = load("parity")
    if rec:
        print("\n## Names on the synthetic blind + held-out sets (profile ai)\n")
        print(json.dumps(rec, indent=1, ensure_ascii=False))
    if par:
        print("\n## Batch invariance\n")
        print(json.dumps(par, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
