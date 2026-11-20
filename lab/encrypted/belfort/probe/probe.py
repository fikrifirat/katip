"""Free probes: which shapes does Belfort's compiler (HEIR) accept? Compiles only, never deploys."""
import sys, time, json, threading
from pathlib import Path
from typing import Annotated
import torch
from torch import nn
import belfort_ml
from belfort_ml import Secret

HERE = Path(__file__).resolve().parent
torch.manual_seed(0)

class Lin(nn.Module):
    def __init__(s): super().__init__(); s.a = nn.Linear(128, 128)
    def forward(s, x: Annotated[torch.Tensor, Secret]): return s.a(x)

class FF(nn.Module):
    def __init__(s): super().__init__(); s.a = nn.Linear(128, 512); s.b = nn.Linear(512, 3)
    def forward(s, x: Annotated[torch.Tensor, Secret]):
        h = s.a(x); return s.b(h * h)

class QK(nn.Module):
    def __init__(s): super().__init__(); s.q = nn.Linear(128, 64); s.k = nn.Linear(128, 64)
    def forward(s, x: Annotated[torch.Tensor, Secret]): return s.q(x) @ s.k(x).transpose(-1, -2)

class Attn(nn.Module):
    def __init__(s): super().__init__(); s.q = nn.Linear(128, 64); s.k = nn.Linear(128, 64); s.v = nn.Linear(128, 64)
    def forward(s, x: Annotated[torch.Tensor, Secret], mask: torch.Tensor):
        sc = s.q(x) @ s.k(x).transpose(-1, -2) + 1.0
        return (sc * sc * mask) @ s.v(x)

def case(name, model, T, three_d=False, mask=False):
    x = torch.randn(1, T, 128) if three_d else torch.randn(T, 128)
    ex = (x, torch.rand(T, T)) if mask else (x,)
    return name, model, ex

CASES = [
    case("lin_64_2d", Lin(), 64), case("lin_64_3d", Lin(), 64, True), case("lin_63_2d", Lin(), 63),
    case("ff_64_2d", FF(), 64), case("qk_64_2d", QK(), 64), case("qk_63_2d", QK(), 63),
    case("attn_64_2d", Attn(), 64, mask=True), case("attn_63_2d", Attn(), 63, mask=True),
]
if len(sys.argv) > 1: CASES = [c for c in CASES if c[0] in sys.argv[1:]]
tag = time.strftime("%H%M%S")
out = {}
arts = {}
for name, model, ex in CASES:            # local tracing is not thread-safe: one at a time
    try: arts[name] = belfort_ml.compile(model.eval(), ex if len(ex) > 1 else ex[0], f"probe_{name}_{tag}", str(HERE / "build" / name))
    except Exception as e: out[name] = {"ok": False, "local": True, "err": str(e)[:300]}; print(name, out[name], flush=True)
def run(provider, name, model, ex):
    t0 = time.time(); art = arts[name]
    try:
        m = provider.models.get(name=f"probe_{name}_{tag}", create_from=art, timeout=1800, use_composite_relu=False)
        out[name] = {"ok": True, "s": round(time.time() - t0)}
    except Exception as e:
        msg = str(e); i = msg.find("error:")
        out[name] = {"ok": False, "s": round(time.time() - t0), "err": (msg[i:i + 300] if i >= 0 else msg[:300])}
    print(name, json.dumps(out[name]), flush=True)
with belfort_ml.Provider() as p:
    ths = [threading.Thread(target=run, args=(p, *c)) for c in CASES if c[0] in arts]
    [t.start() for t in ths]; [t.join() for t in ths]
    print("credits", p.credits.get())
(HERE / f"probe_{tag}.json").write_text(json.dumps(out, indent=1))
