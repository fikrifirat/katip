"""Pick the Nano-FHE recipe on dev data only (Wiki NER dev + Katip held-out synthetic), never on KVKK-Bench."""
import json, sys
from pathlib import Path
import torch
HERE = Path(__file__).resolve().parent; sys.path[:0] = [str(HERE)]
import bench_eval as E, katiplab as K, bench_score as BS
from nano_torch import nano_dir, load_nano, TorchSession
from fhe_ops import PolyFHE

def tagger_for(run):
    tg = K.Tagger(nano_dir())
    if run == "nano": return tg
    net = load_nano(ops=PolyFHE(), window=16)
    if run != "fitted": net.load_state_dict(torch.load(HERE / "runs" / run / "nano_fhe.pt"))
    tg.sess = TorchSession(net.eval()); return tg

if __name__ == "__main__":
    docs = E.dev_docs(); res = {}
    for run in sys.argv[1:]:
        tg = tagger_for(run); preds, _ = E.run(tg, docs, "pipeline"); row = BS.score(docs, preds)
        res[run] = {t: round(100 * x["f2"], 2) for t, x in row["tracks"].items()}
        print(run, res[run], flush=True)
