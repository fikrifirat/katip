"""Free: compile the full conv-layout Nano-FHE on Belfort for a few T (no deploy)."""
import sys, time, json, threading, torch
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent), str(HERE.parent.parent.parent), str(HERE.parent.parent.parent / "legal")]
import belfort_ml, ckks_nano as C
from dev_select import tagger_for
from compile_eml import calibration
from eml_nano import segment_mask
from eml_nano_conv import EmlNanoConv, pack
tg = tagger_for("fitted"); net = tg.sess.net; model = EmlNanoConv(C.fold(net, 3.0)).eval()
Ts = [int(t) for t in sys.argv[1:]] or [64, 128]
tag = time.strftime("%H%M%S"); arts, out = {}, {}
for T in Ts:
    with torch.no_grad():
        calib = [torch.tensor(pack(net.embed(torch.tensor([w]))[0].float().numpy(), segment_mask([T], T=T))) for w in calibration(tg, 256, T)]
    t0 = time.time()
    arts[T] = belfort_ml.compile(model, calib[0], f"nano_conv_{T}_{tag}", str(HERE / "build" / f"conv{T}"), calibration_inputs=calib)
    print(T, "local compile", round(time.time() - t0), "s", flush=True)
def run(p, T):
    t0 = time.time()
    try:
        p.models.get(name=f"nano_conv_{T}_{tag}", create_from=arts[T], timeout=3600, use_composite_relu=False); out[T] = {"ok": True}
    except Exception as e:
        msg = str(e); i = msg.find("error:"); out[T] = {"ok": False, "err": msg[i:i + 400] if i >= 0 else msg[:400]}
    out[T]["s"] = round(time.time() - t0); out[T]["name"] = f"nano_conv_{T}_{tag}"; print(T, json.dumps(out[T]), flush=True)
with belfort_ml.Provider() as p:
    ths = [threading.Thread(target=run, args=(p, T)) for T in Ts]; [t.start() for t in ths]; [t.join() for t in ths]
    print("credits", p.credits.get())
(HERE / f"probe_conv_{tag}.json").write_text(json.dumps(out, indent=1))
