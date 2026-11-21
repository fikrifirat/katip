"""Free: which part of model A trips Belfort's compiler? Compile A1 (qkv only) and A3 (final layer only) variants."""
import sys, time, json, threading, torch, numpy as np
from pathlib import Path
from typing import Annotated
from torch import nn
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent), str(HERE.parent.parent.parent), str(HERE.parent.parent.parent / "legal")]
import belfort_ml, ckks_nano as C
from belfort_ml import Secret
from dev_select import tagger_for
from eml_split import conv1, blocks, H
F0, F1 = C.fold(tagger_for("fitted").sess.net, 3.0)

class A1(nn.Module):           # u (128) -> q0 k0 v0 (384)
    def __init__(s): super().__init__(); s.qkv = conv1(np.concatenate([F0.Wq, F0.Wk, F0.Wv]), np.concatenate([F0.bq, F0.bk, F0.bv]))
    def forward(s, z: Annotated[torch.Tensor, Secret]): return s.qkv(z)

class A3(nn.Module):           # [h1; a1] (256) -> scores (3, or padded)
    def __init__(s, pad=False):
        super().__init__(); s.y = conv1(blocks(2 * H, [(F1.Ax, 0), (F1.Ba, 1)]), F1.c1); s.w1 = conv1(F1.W1, F1.b1)
        P = (lambda W: np.concatenate([W, np.zeros((H - W.shape[0],) + W.shape[1:], dtype=np.float32)])) if pad else (lambda W: W)
        s.ay = conv1(P(F1.Ay), P(F1.c2)); s.bs = conv1(P(F1.Bs))
    def forward(s, z: Annotated[torch.Tensor, Secret]):
        y = s.y(z); hp = s.w1(y); return s.ay(y) + s.bs(hp * hp)

class A3s(nn.Module):          # same, but squares y-side only through B-like tail: scores via 128-ch then a 3-ch conv
    def __init__(s):
        super().__init__(); s.y = conv1(blocks(2 * H, [(F1.Ax, 0), (F1.Ba, 1)]), F1.c1); s.w1 = conv1(F1.W1, F1.b1)
        s.ay = conv1(np.eye(H, dtype=np.float32) * 0 + np.eye(H, dtype=np.float32)); s.bs = conv1(np.zeros((H, 512), dtype=np.float32) + 0.0)
        s.out = None
    def forward(s, z: Annotated[torch.Tensor, Secret]):
        y = s.y(z); hp = s.w1(y); return s.ay(y) + s.bs(hp * hp)

tag = time.strftime("%H%M%S")
CASES = [("a1", A1(), torch.randn(1, 128, 64)), ("a3", A3(), torch.randn(1, 256, 64)), ("a3pad", A3(True), torch.randn(1, 256, 64))]
arts, out = {}, {}
for n, m, x in CASES: arts[n] = belfort_ml.compile(m.eval(), x, f"split_{n}_{tag}", str(HERE / "build" / f"split_{n}"))
def run(p, n):
    t = time.time()
    try: p.models.get(name=f"split_{n}_{tag}", create_from=arts[n], timeout=3600, use_composite_relu=False); out[n] = {"ok": True}
    except Exception as e: msg = str(e); i = msg.find("error:"); out[n] = {"ok": False, "err": msg[i:i + 250]}
    out[n]["s"] = round(time.time() - t); out[n]["name"] = f"split_{n}_{tag}"; print(n, json.dumps(out[n]), flush=True)
with belfort_ml.Provider() as p:
    ths = [threading.Thread(target=run, args=(p, n)) for n in arts]; [t.start() for t in ths]; [t.join() for t in ths]
