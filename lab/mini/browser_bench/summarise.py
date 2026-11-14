"""Turn runs.jsonl (one line per cold page load, written by serve_bench.py) into results.json: medians per model.
One page = 500 words. Memory is what the tab holds after the run: JS heap + onnxruntime's wasm heap."""
import json, statistics as st, pathlib
HERE = pathlib.Path(__file__).parent
runs = [json.loads(l) for l in open(HERE / "runs.jsonl") if l.strip()]
out = {"note": "Chrome 156 (Claude desktop browser pane, hidden tab), Apple M-series, 12 cores; transformers.js + "
        "onnxruntime-web wasm, 1 thread, int8 (q8), no browser cache, the app's ner.js. One page = 500 words. "
        "Medians over cold page loads.", "models": {}}
for m in sorted({r["model"] for r in runs}, key=["katip-mask-nano", "katip-mask-mini", "katip-mask-base"].index):
    R = [r for r in runs if r["model"] == m]
    med = lambda f: round(st.median(f(r) for r in R), 1)
    out["models"][m] = {
        "runs": len(R),
        "cold_runtime_import_ms": med(lambda r: r["cold"]["runtime_import_ms"]),
        "cold_model_load_ms": med(lambda r: r["cold"]["model_load_ms"]),
        "cold_first_result_ms": med(lambda r: r["cold"]["first_result_ms"]),
        "cold_total_ms": med(lambda r: r["cold"]["total_ms"]),
        "ms_per_page_samples_median": med(lambda r: r["ms_per_page_samples_median"]),
        "ms_per_page_joined_948_words": med(lambda r: r["joined"]["ms_per_500_words"]),
        "pages_per_s": round(1000 / st.median(r["joined"]["ms_per_500_words"] for r in R), 2),
        "js_heap_mb_after": med(lambda r: r["memory_after"]["js_heap_mb"]),
        "wasm_heap_mb_after": med(lambda r: r["memory_after"]["wasm_mb"]),
        "per_sample_ms_per_page_range": [min(s["ms_per_500_words"] for r in R for s in r["samples"]),
                                         max(s["ms_per_500_words"] for r in R for s in r["samples"])],
    }
json.dump(out, open(HERE / "results.json", "w"), indent=1)
for m, v in out["models"].items():
    print(m, {k: v[k] for k in v})
