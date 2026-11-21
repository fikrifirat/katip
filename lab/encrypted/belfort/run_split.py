"""Take 3 on Belfort, split design (see eml_split.py). Same page as the CPU runs: 25 documents, 24 calls of 64 tokens.

  python lab/encrypted/belfort/run_split.py --compile-only     # free: compile both models on Belfort
  python lab/encrypted/belfort/run_split.py [--minutes 30]     # spends credits: three deploys, stopped when done
"""
from __future__ import annotations

import argparse, json, secrets, sys, threading, time
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
from eml_nano import EmlNano, segment_mask  # noqa: E402
from eml_split import H, SCALES, attention, build, forward_split  # noqa: E402
from run_encrypted import CachedSession, windows_of  # noqa: E402
import run_belfort as RB  # noqa: E402

T = 64


def calib_inputs(net, models, n=128):
    """Real inputs for each model from training windows (never the bench), as the split forward produces them."""
    ws = calibration(tagger_for("fitted"), n, T); got = {k: [] for k in models}
    def caller(k): return lambda z: (got[k].append(torch.tensor(z)), models[k](torch.tensor(z))[0].numpy())[1]
    with torch.no_grad():
        for w in ws: forward_split(caller("Q"), caller("B"), caller("F"), net.embed(torch.tensor([w]))[0].float().numpy(), segment_mask([T]))
    return got


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--minutes", type=int, default=30)
    ap.add_argument("--compile-only", action="store_true"); a = ap.parse_args()
    import belfort_ml
    from belfort_ml_client import Client
    tg = tagger_for("fitted"); net = tg.sess.net; F = C.fold(net, 3.0)
    models_t = build(F); ref = EmlNano(F).eval()           # scaled: encrypted values stay within about +-2
    NAMES = {"Q": "katip_split_q2", "B": "katip_split_b2", "F": "katip_split_f2"}
    OUT = {"Q": 3 * H, "B": 4 * H, "F": 3}
    RB.T, RB.STRIDE = T, T // 2

    ids = json.loads((HERE.parent / "results" / "encrypted_fitted.json").read_text())["docs"]
    docs = [d for d in E.gold({"court-filled", "prose"}) if d["id"] in set(ids)]
    wins = [w for d in docs for w in windows_of(tg, d["text"])]
    jobs = RB.pack_inputs(net, wins)
    with torch.no_grad():
        plain = [ref(torch.tensor(x)[None], torch.tensor(m))[0].numpy() for x, m, _ in jobs]
    res = {"design": "split: server = all weight layers encrypted, client = attention mixing", "documents": len(docs),
           "calls": len(jobs), "round_trips_per_call": 3, "eml_models": 3, "tokens": sum(map(len, wins))}
    print(f"{len(docs)} documents, {len(jobs)} calls of {T} tokens, 3 round trips each", flush=True)

    cal = calib_inputs(net, models_t)
    arts = {k: belfort_ml.compile(models_t[k], cal[k][0], NAMES[k], str(HERE / "build" / NAMES[k]), calibration_inputs=cal[k]) for k in NAMES}
    with belfort_ml.Provider() as provider:
        res["credits_before"] = provider.credits.get()
        models, errs = {}, {}
        def get(k):
            t = time.time()
            try: models[k] = provider.models.get(name=NAMES[k], create_from=arts[k], timeout=3600, use_composite_relu=False)
            except Exception as e: errs[k] = str(e)[:500]
            res[f"server_compile_{k}_s"] = round(time.time() - t, 1)
        ths = [threading.Thread(target=get, args=(k,)) for k in arts]; [t.start() for t in ths]; [t.join() for t in ths]
        print("compiled:", {k: res[f"server_compile_{k}_s"] for k in arts}, "errors:", errs, flush=True)
        if errs: raise SystemExit(1)
        if a.compile_only: return

        clients, tokens = {}, {}
        t0 = time.time()
        for k, m in models.items():
            tokens[k] = m.create_client(label=f"katip-split-{k}", ttl_seconds=86400)
            clients[k] = Client(tokens[k].token, secret_seed=secrets.token_bytes(32))
        # client.prepare publishes the keys and then waits for a deploy to hold them, so it runs in threads
        # and is joined only after the deploys start (joining first deadlocks: no deploy, no ready client)
        prep = {k: threading.Thread(target=c.prepare) for k, c in clients.items()}; [t.start() for t in prep.values()]
        t0 = time.time()
        for k, m in models.items(): m.wait_for_keys(tokens[k])
        res["key_upload_s"] = round(time.time() - t0, 1); print("keys ready", res, flush=True)

        # Belfort runs one deploy per account at a time, so the page runs in three stages, one model each:
        # every call's Q step, then every call's B step, then every F step. The calls are independent, so the
        # result is the same as running each call through all three; the client does attention between stages.
        lat = {k: [] for k in NAMES}; stage_s = {}; deploy_s = {}; stage_err = {}
        def run_stage(k, inputs, n_out):
            while any(d.status in ("starting", "ready", "stopping") for d in provider.deploys.list()):
                time.sleep(10)                                   # the previous stage's deploy must be gone first
            t0 = time.time(); outs = []
            with models[k].deploy(key_set=tokens[k], max_lifetime=timedelta(minutes=a.minutes)) as d:
                deploy_s[k] = round(time.time() - t0, 1); print(f"deploy {k} ready in {deploy_s[k]} s", flush=True)
                prep[k].join()
                t1 = time.time()
                for i, z in enumerate(inputs):
                    ans = clients[k].infer([z.reshape(-1).tolist()]); lat[k].append(ans.get("latency_ms"))
                    outs.append(np.array(ans["values"], dtype=np.float32).reshape(n_out, T))
                    with torch.no_grad(): want = models_t[k](torch.tensor(z))[0].numpy()
                    err = float(np.abs(outs[-1] - want).max()); stage_err.setdefault(k, []).append(err)
                    print(f"  {k} call {i + 1}/{len(inputs)}: {ans.get('latency_ms')} ms on the GPU, max error {err:.2e} (scaled units)", flush=True)
                stage_s[k] = round(time.time() - t1, 1)
            print(f"stage {k}: {stage_s[k]} s for {len(inputs)} calls; deploy stopped after {round(time.time() - t0, 1)} s", flush=True)
            return outs
        xs = [x for x, _, _ in jobs]; ms = [m for _, m, _ in jobs]; S = SCALES
        f32 = lambda a: np.asarray(a, dtype=np.float32)
        q0 = [o * S["Q"]["s_out"] for o in run_stage("Q", [f32(x.T[None] / S["Q"]["s_in"]) for x in xs], OUT["Q"])]
        a0 = [attention(q, m) for q, m in zip(q0, ms)]
        ob = [o * S["B"]["s_out"] for o in run_stage("B", [f32(np.concatenate([x.T, a])[None] / S["B"]["s_in"]) for x, a in zip(xs, a0)], OUT["B"])]
        a1 = [attention(o[H:], m) for o, m in zip(ob, ms)]
        of = [o * S["F"]["s_out"] for o in run_stage("F", [f32(np.concatenate([o[:H], a])[None] / S["F"]["s_in"]) for o, a in zip(ob, a1)], OUT["F"])]
        enc = [o.T for o in of]
        res["stage_max_error_scaled"] = {k: max(v) for k, v in stage_err.items()}
        res["deploy_start_s"] = deploy_s; res["stage_s"] = stage_s
        res["page_wall_s"] = round(sum(stage_s.values()), 1)
        res["client_attention"] = "plaintext, on the client, between stages"
        for c in clients.values(): c.close()
        res["deploy_total_s"] = round(time.time() - t0, 1)
        res["gpu_latency_ms"] = {k: {"mean": float(np.mean(v)), "sum": float(np.sum(v)), "n": len(v)} for k, v in lat.items() if v and v[0] is not None}
        res["credits_after"] = provider.credits.get()

    real = [np.array([o + t for _, _, o, L in pl for t in range(L)]) for _, _, pl in jobs]   # rows that hold tokens
    res["max_abs_logit_error"] = max(float(np.abs(e[r] - p[r]).max()) for e, p, r in zip(enc, plain, real))
    res["token_label_agreement"] = float(np.mean(np.concatenate([e[r].argmax(1) == p[r].argmax(1) for e, p, r in zip(enc, plain, real)])))
    np.savez_compressed(HERE.parent / "results" / "belfort_split_outputs.npz", enc=np.array(enc), plain=np.array(plain))
    tp = tagger_for("fitted"); tp.sess = CachedSession(RB.unpack(wins, jobs, plain))
    te = tagger_for("fitted"); te.sess = CachedSession(RB.unpack(wins, jobs, enc))
    td = tagger_for("fitted")
    for mode in ("pipeline", "model"):
        pp, _ = E.run(tp, docs, mode); pe, _ = E.run(te, docs, mode); pd, _ = E.run(td, docs, mode)
        res[f"{mode}_identical_docs_vs_plain"] = E.label_agreement(pp, pe)
        res[f"{mode}_identical_docs_vs_cpu_model"] = E.label_agreement(pd, pe)
    print(json.dumps(res, indent=1, default=str), flush=True)
    (HERE.parent / "results" / "belfort_split_run.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
