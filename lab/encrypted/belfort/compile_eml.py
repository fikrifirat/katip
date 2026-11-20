"""Compile Nano-FHE for Belfort eML (local step: traces to MLIR, no network, no credits).

  python lab/encrypted/belfort/compile_eml.py [out_dir]
Calibration: up to 512 real 64-token windows from Katip's training sources (synthetic train + Wiki NER train),
never from the bench.
"""
import random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import torch, katiplab as K
import ckks_nano as C
from dev_select import tagger_for
from train_fhe import sequences
from eml_nano import EmlNano, T, segment_mask

def calibration(tg, n=512):
    wiki = K.load_wiki("train"); random.Random(1).shuffle(wiki)
    docs = list(K.load_synth("train"))[:400] + K.pack(wiki)[:400]
    ws = [ids[:T] for ids, _ in sequences(tg, docs) if len(ids) >= T]
    random.Random(2).shuffle(ws)
    return ws[:n]

if __name__ == "__main__":
    import belfort_ml
    out = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "build")
    tg = tagger_for("fitted"); net = tg.sess.net
    model = EmlNano(C.fold(net, 3.0)).eval()
    with torch.no_grad():
        calib = [(net.embed(torch.tensor([w])).float(), torch.tensor(segment_mask([T]))) for w in calibration(tg)]
    print(len(calib), "calibration windows", flush=True)
    art = belfort_ml.compile(model, calib[0], "katip_nano_fhe", out, calibration_inputs=calib)
    print("compiled:", art)
