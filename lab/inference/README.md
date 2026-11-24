# Serving Katip like an inference product

A small experiment: put Katip's masking pipeline behind one HTTP endpoint, load it like a service, and
measure what a Katip API would cost to run. Findings: [RESULTS.md](RESULTS.md).

| File | What it does |
| --- | --- |
| `katipserve.py` | The endpoint. `POST /v1/mask` runs the full `katip-mask` pipeline (rules, one name model, leak check). The model step goes through a request queue and a dynamic batcher (`--max-batch`, `--max-wait-ms`). `--lazy` and `--idle-unload S` give scale to zero: the ONNX session loads on the first request and is dropped after S idle seconds. `GET /metrics` reports batches, tokens, CPU time and memory. |
| `bench.py` | Load generator and experiments. Replays one-page documents built from Katip's synthetic blind and held-out sets (no real personal data), closed loop for saturation and open loop (Poisson arrivals, latency from the due time) for p50/p95. |
| `report.py` | Turns `results/*.json` into the tables in RESULTS.md, with machine prices. |
| `results/` | Raw JSON from the runs in RESULTS.md, and the run log. |

## Run it

From the repository root, in a Python with `numpy`, `onnxruntime` and `huggingface_hub`
(`pip install "katip-mask[model]" huggingface_hub psutil`):

```bash
python lab/inference/katipserve.py --model mini --port 8811 &
curl -s localhost:8811/v1/mask -d '{"text": "Davacı Ahmet YILMAZ, T.C. 12345678950"}'

python lab/inference/bench.py parity        # batched server vs the SDK, document by document
python lab/inference/bench.py cold recall capacity threads batching   # about 30 minutes
python lab/inference/report.py
```

Models come from Hugging Face at the commits pinned in `sdk/python/src/katip_mask/spec/models.json`, checked
by SHA-256. Base fp32 (`onnx/model.onnx`, 440 MB) is the only fp32 file published, so int8 vs fp32 is compared
on Base.

## What this is not

A toy. One process, one model worker, Python HTTP. The point is the method and first numbers, not a
production server: there is no auth, no TLS, no autoscaler and no GPU.
