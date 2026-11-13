"""How well does slotfill.find_slots tell person slots from other slots? Checked against TurkishLegalNER,
where every '...' token carries the annotators' tag. Prints a confusion table and person-slot P/R."""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).parent.parent))
import katiplab as K  # noqa: E402,F401  (unpacks the bundle the name lists come from)
import legal as L  # noqa: E402
import slotfill as F  # noqa: E402

def run():
    L._read("train"); L._read("test")
    c = Counter()
    for split in ("train", "test"):
        W = (K.DATA / "legalner" / f"{split}.words.txt").read_text(encoding="utf-8").splitlines()
        T = (K.DATA / "legalner" / f"{split}.tags.txt").read_text(encoding="utf-8").splitlines()
        for w, t in zip(W, T):
            ws, ts = w.split(), t.split()
            text, offs = "", []
            for x in ws:
                if text: text += " "
                offs.append(len(text)); text += x
            slots = {s.start: s.kind for s in F.find_slots(text)}
            for o, x, tag in zip(offs, ws, ts):
                if x.startswith("..."):
                    gold = "PER" if tag.endswith("PER") else ("O" if tag == "O" else "other entity")
                    c[(gold, slots.get(o, "not a slot"))] += 1
    tp = c[("PER", "PERSON")]; fn = sum(v for (g, p), v in c.items() if g == "PER" and p != "PERSON")
    fp = sum(v for (g, p), v in c.items() if g != "PER" and p == "PERSON")
    return c, tp / (tp + fn), tp / (tp + fp)

if __name__ == "__main__":
    c, r, p = run()
    for k, v in sorted(c.items(), key=lambda x: -x[1]): print(f"{k[0]:13} -> {k[1]:11} {v}")
    print(f"\nperson slots: recall {100 * r:.1f}%  precision {100 * p:.1f}%")
