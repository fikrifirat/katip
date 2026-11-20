"""Take 3: Nano-FHE on Belfort eML (CKKS on Belfort's GPU), the same page as the CPU runs.

  BELFORT_API_KEY=... python lab/encrypted/belfort/run_belfort.py [--minutes 30]

Spends credits: one deploy, max_lifetime 30 minutes (3 credits reserved, actual time billed in 10-minute steps).
Compiling, key upload and inference are free. The deploy is stopped as soon as the page is done.

Provider and end client run in this one process for the experiment, but keep their roles: the end client
generates the secret key and encrypts/decrypts; the provider side only ever handles the client token.
eML takes one encrypted fixed-shape input: 64 embedded tokens ([1, 64, 128]), plus a plaintext attention mask.
Short windows are packed together (the mask keeps them apart exactly); windows longer than 64 tokens are cut
into 64-token chunks with a stride of 32, each token taking its label from the chunk where it is most
central. The same packing runs in plaintext, so the encrypted output is compared like for like, and the
plaintext check also shows what the 64-token chunking costs against the CPU run.
"""
from __future__ import annotations

import argparse, json, os, secrets, sys, threading, time
from datetime import timedelta
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent), str(HERE.parent.parent / "legal")]
import bench_eval as E  # noqa: E402
import ckks_nano as C  # noqa: E402
from compile_eml import calibration  # noqa: E402
from dev_select import tagger_for  # noqa: E402
from eml_nano import EmlNano, T, segment_mask  # noqa: E402
from run_encrypted import CachedSession, windows_of  # noqa: E402

STRIDE = 32


def chunks(n):
    """Start offsets of 64-token chunks covering n tokens (n > T), stride 32."""
    starts = list(range(0, max(1, n - T) + 1, STRIDE))
    if starts[-1] + T < n: starts.append(n - T)
    return starts


def assemble(n, starts, outs):
    """Per token, take the chunk where it sits closest to the centre."""
    res = np.zeros((n, 3))
    for t in range(n):
        best = min((abs(t - (s + T / 2)), i) for i, s in enumerate(starts) if s <= t < s + T)[1]
        res[t] = outs[best][t - starts[best]]
    return res


def pack_inputs(net, wins):
    """Segments (whole windows <= 64 tokens, or 64-token chunks of longer ones) packed into 64-row inputs.
    Returns [(x [64,128], mask [64,64], [(window, chunk start, row offset, length)])]."""
    segs = []
    for wi, w in enumerate(wins):
        for s in (chunks(len(w)) if len(w) > T else [0]):
            segs.append((wi, s, min(T, len(w) - s)))
    inputs, cur, used = [], [], 0
    for seg in segs:
        if used + seg[2] > T:
            inputs.append(cur); cur, used = [], 0
        cur.append(seg); used += seg[2]
    if cur: inputs.append(cur)
    out = []
    with torch.no_grad():
        for segs_in in inputs:
            x = np.zeros((T, 128), dtype=np.float32); o = 0; placed = []
            for wi, s, L in segs_in:
                x[o:o + L] = net.embed(torch.tensor([wins[wi][s:s + L]]))[0].float().numpy()
                placed.append((wi, s, o, L)); o += L
            out.append((x, segment_mask([L for *_, L in segs_in]), placed))
    return out


def unpack(wins, inputs, outs):
    """Label scores per window: short windows directly, long ones from the chunk where each token is most central."""
    per = {}
    for (_, _, placed), y in zip(inputs, outs):
        for wi, s, o, L in placed:
            per.setdefault(wi, []).append((s, y[o:o + L]))
    cache = {}
    for wi, w in enumerate(wins):
        parts = sorted(per[wi], key=lambda p: p[0])
        if len(parts) == 1: res = parts[0][1]
        else: res = assemble(len(w), [p[0] for p in parts], [p[1] for p in parts])
        cache[tuple(w)] = np.asarray(res, dtype=np.float32)
    return cache


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--minutes", type=int, default=30)
    ap.add_argument("--plaintext-only", action="store_true", help="run the chunked model in plaintext, no network")
    a = ap.parse_args()
    tg = tagger_for("fitted"); net = tg.sess.net
    model_t = EmlNano(C.fold(net, 3.0)).eval()

    ids = json.loads((HERE.parent / "results" / "encrypted_fitted.json").read_text())["docs"]
    docs = [d for d in E.gold({"court-filled", "prose"}) if d["id"] in set(ids)]
    wins = [w for d in docs for w in windows_of(tg, d["text"])]
    jobs = pack_inputs(net, wins)
    print(f"{len(docs)} documents, {len(wins)} windows, {len(jobs)} eML calls of 64 tokens", flush=True)

    with torch.no_grad():
        plain = [model_t(torch.tensor(x)[None], torch.tensor(m))[0].numpy() for x, m, _ in jobs]

    res = {"documents": len(docs), "calls": len(jobs), "tokens": sum(map(len, wins))}
    if not a.plaintext_only:
        import belfort_ml
        from belfort_ml_client import Client
        out_dir = HERE / "build"
        with torch.no_grad():
            calib = [(net.embed(torch.tensor([w])).float(), torch.tensor(segment_mask([T]))) for w in calibration(tg)]
        artifacts = belfort_ml.compile(model_t, calib[0], "katip_nano_fhe", str(out_dir), calibration_inputs=calib)
        with belfort_ml.Provider() as provider:
            res["credits_before"] = provider.credits.get()
            t0 = time.time()
            model = provider.models.get(name="katip_nano_fhe", create_from=artifacts, timeout=1800, use_composite_relu=False)
            res["server_compile_s"] = round(time.time() - t0, 1)
            print("compiled on Belfort in", res["server_compile_s"], "s", flush=True)
            token = model.create_client(label="katip-experiment", ttl_seconds=86400)
            seed = secrets.token_bytes(32)
            client = Client(token.token, secret_seed=seed)
            prep = {}
            def prepare():
                t = time.time(); client.prepare(); prep["s"] = round(time.time() - t, 1)
            th = threading.Thread(target=prepare); th.start()
            t0 = time.time(); model.wait_for_keys(token); res["key_upload_s"] = round(time.time() - t0, 1)
            print("keys uploaded in", res["key_upload_s"], "s", flush=True)
            t0 = time.time()
            with model.deploy(key_set=token, max_lifetime=timedelta(minutes=a.minutes)) as deploy:
                res["deploy_start_s"] = round(time.time() - t0, 1)
                th.join(); res["client_prepare_s"] = prep.get("s")
                print("deploy ready in", res["deploy_start_s"], "s", flush=True)
                enc, lat, wall = [], [], []
                t_page = time.time()
                for x, m, _ in jobs:
                    t = time.time(); ans = client.infer([x.reshape(-1).tolist(), m.reshape(-1).tolist()]); wall.append(time.time() - t)
                    enc.append(np.array(ans["values"]).reshape(T, 3)); lat.append(ans.get("latency_ms"))
                res["page_wall_s"] = round(time.time() - t_page, 1)
            client.close()
            res["gpu_latency_ms"] = {"mean": float(np.mean(lat)), "min": float(np.min(lat)), "max": float(np.max(lat))}
            res["wall_per_call_s"] = {"mean": float(np.mean(wall)), "max": float(np.max(wall))}
            res["credits_after"] = provider.credits.get()
        err = max(float(np.abs(e - p).max()) for e, p in zip(enc, plain))
        agree = np.mean([(e.argmax(1) == p.argmax(1)).mean() for e, p in zip(enc, plain)])
        res["max_abs_logit_error"] = err; res["call_label_agreement"] = float(agree)
        outs = enc
    else:
        outs = plain

    # Assemble per window, then score with the Katip pipeline, against the same chunking in plaintext.
    per_window = lambda o: unpack(wins, jobs, o)
    tp = tagger_for("fitted"); tp.sess = CachedSession(per_window(plain))
    te = tagger_for("fitted"); te.sess = CachedSession(per_window(outs))
    td = tagger_for("fitted")                      # the CPU runs' model, full windows, no 64-token packing
    for mode in ("pipeline", "model"):
        pp, _ = E.run(tp, docs, mode); pe, _ = E.run(te, docs, mode); pd, _ = E.run(td, docs, mode)
        res[f"{mode}_identical_docs_vs_plain_chunked"] = E.label_agreement(pp, pe)
        res[f"{mode}_identical_docs_chunked_vs_cpu_model"] = E.label_agreement(pd, pp)
    print(json.dumps(res, indent=1, default=str), flush=True)
    (HERE.parent / "results" / ("belfort_plaintext_check.json" if a.plaintext_only else "belfort_run.json")).write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
