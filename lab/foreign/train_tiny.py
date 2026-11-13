"""Train Katip Tiny with and without foreign clients in the data: same recipe, seed, real text and synthetic
documents (pii-names-tiny, notebook 02's selected setting: all 17,967 Wiki NER sentences); the only change is the
foreign mix (mix.py). CPU is enough (2.6M parameters).

  python lab/foreign/train_tiny.py control     # lab/runs/tiny_r_seed0   (pii-names-tiny recipe)
  python lab/foreign/train_tiny.py foreign     # lab/runs/tiny_f_seed0   (+ foreign mix)
  python lab/foreign/train_tiny.py both --threads 2
"""
import os, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
if "--threads" in sys.argv:
    n = int(sys.argv[sys.argv.index("--threads") + 1]); os.cpu_count = lambda: n
import katiplab as K  # noqa: E402
import mix as M  # noqa: E402

def run(kind, seed=0):
    out = K.RUNS / f"tiny_{'r' if kind == 'control' else 'f'}_seed{seed}"
    if (out / "train_info.json").exists(): print("done already:", out); return out
    K.get_wikiner()
    wiki = K.load_wiki("train"); random.Random(seed).shuffle(wiki); real = K.pack(wiki)
    synth = K.load_synth("train")
    if kind == "foreign":
        synth, extra, info = M.foreign_mix(seed=seed); real = real + extra; print("foreign mix:", info)
    K.train_tiny(out, real_docs=real, synth_docs=synth, seed=seed)
    return out

if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "both"
    for k in (["control", "foreign"] if kind == "both" else [kind]): run(k)
