"""Experiment 1, encrypted: run Nano-FHE on real KVKK-Bench documents under CKKS at 128-bit security.

  python lab/encrypted/run_encrypted.py RUN [--batches 1] [--f 32]

RUN is a folder in lab/encrypted/runs/ (or "fitted" for the polynomial model without retraining).
Fills each batch (T = slots / f token positions) with names-track documents (court-filled and prose, seeded
shuffle), encrypts on the "client", runs both layers + classifier on the "server", decrypts, and compares
with the same model in plaintext: logit error, label agreement, and the spans the Katip pipeline produces.
Writes lab/encrypted/results/encrypted_<RUN>.json.
"""
from __future__ import annotations

import argparse, json, random, sys, time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "legal")]
import katiplab as K  # noqa: E402
import bench_eval as E  # noqa: E402
import ckks_nano as C  # noqa: E402
from dev_select import tagger_for  # noqa: E402
from nano_torch import TorchSession  # noqa: E402

WINDOW = 16


class CachedSession:
    """Answers Tagger with logits decrypted earlier, keyed by the token ids of the window."""
    def __init__(self, cache): self.cache = cache
    def get_inputs(self): return TorchSession(None).get_inputs()
    def run(self, _o, feed): return [self.cache[tuple(feed["input_ids"][0].tolist())][None]]


def windows_of(tg, text):
    """The token windows Tagger.word_labels will ask the model for."""
    seen = []
    class Rec:
        def get_inputs(self): return TorchSession(None).get_inputs()
        def run(self, _o, feed):
            ids = feed["input_ids"][0].tolist(); seen.append(ids)
            return [np.zeros((1, len(ids), 3), dtype=np.float32)]
    old = tg.sess; tg.sess = Rec(); tg.word_labels(text); tg.sess = old
    return seen


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("--batches", type=int, default=1)
    ap.add_argument("--f", type=int, default=32); ap.add_argument("--slots", type=int, default=32768)
    ap.add_argument("--take", type=int, default=1, help="1: first engine, 2: threaded + rotation reuse")
    ap.add_argument("--label", default="", help="suffix for the results file")
    ap.add_argument("--toy", action="store_true", help="insecure ring dimension 4096, for a quick code check only")
    a = ap.parse_args()
    tg = tagger_for(a.run); net = tg.sess.net
    lay = C.Layout(slots=a.slots, f=a.f, window=WINDOW)

    docs = E.gold({"court-filled", "prose"}); random.Random(0).shuffle(docs)
    chosen, wins, budget = [], [], lay.T * a.batches
    for d in docs:
        ws = windows_of(tg, d["text"])
        if sum(map(len, wins)) + sum(map(len, ws)) > budget: continue
        chosen.append(d); wins += ws
        if sum(map(len, wins)) > budget - 8: break
    print(f"{len(chosen)} documents, {len(wins)} windows, {sum(map(len, wins))} tokens, "
          f"{sum(len(d['text'].split()) for d in chosen)} words", flush=True)

    res = {"run": a.run, "take": a.take, "f": a.f, "T": lay.T, "window": WINDOW, "docs": [d["id"] for d in chosen],
           "tokens": sum(map(len, wins)), "words": sum(len(d["text"].split()) for d in chosen)}
    t0 = time.time(); ctx = C.make_context(lay.rotations(), ring_dim=4096, secure=False) if a.toy else C.make_context(lay.rotations())
    res["ring_dim"] = ctx.ring_dim; res["keygen_s"] = round(time.time() - t0, 1)
    print(f"ring dimension {ctx.ring_dim}, {ctx.slots} slots, keygen {res['keygen_s']}s", flush=True)
    res["keys"] = C.key_bytes(ctx); print("keys", res["keys"], flush=True)

    F = C.fold(net, 3.0)
    cl = C.Client(ctx, net, lay)
    srv = (C.ServerTake2 if a.take == 2 else C.Server)(ctx.cc, F, net.heads, lay)
    embs = cl.embed(wins)
    with torch.no_grad():
        plain = [net(torch.tensor([w]), torch.ones(1, len(w), dtype=torch.long))[0].double().numpy() for w in wins]
    cache, per_batch = {}, []
    for bi, batch in enumerate(lay.place([len(w) for w in wins])):
        b = {"windows": len(batch), "tokens": sum(L for *_, L in batch)}
        t0 = time.time(); cts = cl.encrypt(cl.matrix(embs, batch)); b["encrypt_s"] = round(time.time() - t0, 1)
        b["upload_MB"] = round(sum(C.ct_bytes(c) for c in cts) / 1e6, 1); b["upload_ciphertexts"] = len(cts)
        srv.timings, srv.counts = {}, {}
        t0 = time.time(); out = srv.run(cts, lay.masks(batch)); b["server_s"] = round(time.time() - t0, 1)
        b["server_breakdown_s"] = dict(srv.timings); b["ops"] = dict(srv.counts)
        b["download_MB"] = round(sum(C.ct_bytes(c) for c in out) / 1e6, 2)
        t0 = time.time(); dec = cl.decrypt(out, 3, batch); b["decrypt_s"] = round(time.time() - t0, 2)
        errs, agree, n = [], 0, 0
        for (wi, _, L), lg in zip(batch, dec):
            errs.append(float(np.abs(lg - plain[wi]).max())); agree += int((lg.argmax(1) == plain[wi].argmax(1)).sum()); n += L
            cache[tuple(wins[wi])] = lg.astype(np.float32)
        b["max_abs_logit_error"] = max(errs); b["token_label_agreement"] = agree / n
        print(f"  batch {bi + 1}: {json.dumps(b)}", flush=True)
        per_batch.append(b)
    res["batches"] = per_batch

    # Spans: the Katip pipeline on decrypted logits vs on plaintext logits of the same model.
    tg_plain = tagger_for(a.run)
    tg_enc = tagger_for(a.run); tg_enc.sess = CachedSession(cache)
    for mode in ("pipeline", "model"):
        p_plain, _ = E.run(tg_plain, chosen, mode); p_enc, _ = E.run(tg_enc, chosen, mode)
        res[f"{mode}_identical_docs"] = E.label_agreement(p_plain, p_enc)
        res[f"{mode}_score_plain"] = E.summary(E.BS.score(chosen, p_plain))
        res[f"{mode}_score_encrypted"] = E.summary(E.BS.score(chosen, p_enc))
    print(json.dumps({k: v for k, v in res.items() if k != "docs"}, indent=1), flush=True)
    out = HERE / "results"; out.mkdir(exist_ok=True)
    (out / f"encrypted_{a.run}{'_take%d' % a.take if a.take > 1 else ''}{a.label}.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
