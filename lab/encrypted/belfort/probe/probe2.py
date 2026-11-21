"""Free probes, round 2: token-wise layers as 1x1 convolutions on [1, C, T] (the CNN layout Belfort supports)."""
import sys, time, json, threading
from pathlib import Path
from typing import Annotated
import torch
from torch import nn
import torch.nn.functional as Fn
import belfort_ml
from belfort_ml import Secret
HERE = Path(__file__).resolve().parent
torch.manual_seed(0)

class Vec(nn.Module):
    def __init__(s): super().__init__(); s.a = nn.Linear(128, 128)
    def forward(s, x: Annotated[torch.Tensor, Secret]): return s.a(x)

class C1(nn.Module):
    def __init__(s, o=128): super().__init__(); s.a = nn.Conv1d(128, o, 1)
    def forward(s, x: Annotated[torch.Tensor, Secret]): return s.a(x)

class FFc(nn.Module):
    def __init__(s): super().__init__(); s.a = nn.Conv1d(128, 512, 1); s.b = nn.Conv1d(512, 3, 1)
    def forward(s, x: Annotated[torch.Tensor, Secret]):
        h = s.a(x); return s.b(h * h)

class Shift(nn.Module):
    """q * shift(k, r) summed per head, for a few offsets: the attention score in conv form."""
    def __init__(s, R=2):
        super().__init__(); s.q = nn.Conv1d(128, 128, 1); s.k = nn.Conv1d(128, 128, 1); s.R = R
        s.sh = nn.Conv1d(128, 128 * (2 * R + 1), 2 * R + 1, padding=R, groups=128, bias=False)
        with torch.no_grad():
            s.sh.weight.zero_()
            for c in range(128):
                for j in range(2 * R + 1): s.sh.weight[c * (2 * R + 1) + j, 0, j] = 1.0
        s.red = nn.Conv1d(128 * (2 * R + 1), 2 * (2 * R + 1), 1, bias=False)
    def forward(s, x: Annotated[torch.Tensor, Secret]):
        q = s.q(x); k = s.k(x)
        ks = s.sh(k)
        qq = q.repeat_interleave(2 * s.R + 1, 1)
        return s.red(qq * ks)

class Prod(nn.Module):
    def __init__(s): super().__init__(); s.a = nn.Conv1d(128, 128, 1); s.b = nn.Conv1d(128, 128, 1)
    def forward(s, x: Annotated[torch.Tensor, Secret], m: torch.Tensor): return s.a(x) * s.b(x) * m

class Prod2(nn.Module):
    def __init__(s): super().__init__(); s.a = nn.Conv1d(128, 128, 1); s.b = nn.Conv1d(128, 128, 1)
    def forward(s, x: Annotated[torch.Tensor, Secret]): return s.a(x) * s.b(x)

class DW(nn.Module):
    """shift by r with a depthwise conv, then multiply with q, reduce channels per head with a 1x1 conv."""
    def __init__(s, R=2):
        super().__init__(); s.q = nn.Conv1d(128, 128, 1); s.k = nn.Conv1d(128, 128, 1)
        s.sh = nn.ModuleList()
        for j in range(2 * R + 1):
            c = nn.Conv1d(128, 128, 2 * R + 1, padding=R, groups=128, bias=False)
            with torch.no_grad(): c.weight.zero_(); c.weight[:, 0, j] = 1.0
            s.sh.append(c)
        s.red = nn.Conv1d(128, 2, 1, bias=False)
    def forward(s, x: Annotated[torch.Tensor, Secret]):
        q = s.q(x); k = s.k(x)
        return torch.cat([s.red(q * c(k)) for c in s.sh], 1)

T = 64
CASES = [("prod2_64", Prod2(), (torch.randn(1, 128, 64),)), ("dw_64", DW(), (torch.randn(1, 128, 64),)),("vec", Vec(), (torch.randn(1, 128),)), ("c1_64", C1(), (torch.randn(1, 128, 64),)),
         ("c1_256", C1(), (torch.randn(1, 128, 256),)), ("ff_64", FFc(), (torch.randn(1, 128, 64),)),
         ("prod_64", Prod(), (torch.randn(1, 128, 64), torch.rand(1, 128, 64))),
         ("shift_64", Shift(), (torch.randn(1, 128, 64),))]
if len(sys.argv) > 1: CASES = [c for c in CASES if c[0] in sys.argv[1:]]
tag = time.strftime("%H%M%S"); out = {}; arts = {}
for name, model, ex in CASES:
    try: arts[name] = belfort_ml.compile(model.eval(), ex if len(ex) > 1 else ex[0], f"probe_{name}_{tag}", str(HERE / "build" / name))
    except Exception as e: out[name] = {"ok": False, "local": True, "err": str(e)[:300]}; print(name, out[name], flush=True)
def run(provider, name):
    t0 = time.time()
    try:
        provider.models.get(name=f"probe_{name}_{tag}", create_from=arts[name], timeout=1800, use_composite_relu=False)
        out[name] = {"ok": True, "s": round(time.time() - t0)}
    except Exception as e:
        msg = str(e); i = msg.find("error:"); out[name] = {"ok": False, "s": round(time.time() - t0), "err": (msg[i:i + 300] if i >= 0 else msg[:300])}
    print(name, json.dumps(out[name]), flush=True)
with belfort_ml.Provider() as p:
    ths = [threading.Thread(target=run, args=(p, n)) for n in arts]; [t.start() for t in ths]; [t.join() for t in ths]
    print("credits", p.credits.get())
(HERE / f"probe2_{tag}.json").write_text(json.dumps(out, indent=1))
