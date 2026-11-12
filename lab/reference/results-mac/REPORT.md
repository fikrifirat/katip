# Katip Tiny-R: a 2.6 MB Turkish name tagger that works on real text

**Problem.** Katip's 2.6 MB name tagger found 99.7% of names on Katip's synthetic blind set, but only 15% of names in real Turkish sentences (Turkish Wiki NER test, 1,000 human-annotated sentences). It had learned the templates of the synthetic documents rather than what a Turkish name looks like.

**Method.** Same architecture (2 layers, 128 hidden, 2.5 M parameters), same recipe as `ml/train.py`; the only change is 17,967 real sentences from Turkish Wiki NER train mixed into the 8,000 synthetic training documents, and model names scored ≥ 0.5 allowed to skip the two-word rule in the merge step. Configuration chosen on Wiki NER dev by a rule written before training (2026-11-12T01:38:33+00:00); test scored once.

| | Tiny (published) | Tiny-R | 
| --- | --- | --- |
| Wiki NER test, name recall (95% CI) | 14.8% [11.1%–18.9%] | **55.5% [51.2%–60.1%]** |
| Wiki NER test, name precision | 69.6% | 61.2% |
| Blind set (synthetic), name recall | 99.7% [99.1%–100.0%] | 99.5% [98.6%–100.0%] |
| Blind set (synthetic), name precision | 100.0% | 98.3% |
| Held-out set (synthetic), name recall | 97.5% [94.8%–99.6%] | 100.0% [100.0%–100.0%] |
| False names on name-free legal prose | 2 | 2 |
| Model size (int8 ONNX) | 2.57 MB | 2.57 MB |

Real-text recall change: +40.7 points (paired bootstrap 95% CI +35.9 to +45.5; McNemar p = 8.8e-76; 269 names found only by Tiny-R, 3 only by the published model). Mean over 1 seed(s).

**Control.** The published model with the same trust setting (0.5) reaches 34.4% real-text recall but at 28.9% precision and 39 false names on name-free legal prose, so the gain comes from the model, not the setting.

**Pre-registered hypotheses.** H1 real text +15 pts, p<0.05: pass (+40.7 points, p=8.8e-76); H2 blind recall >= 99.0%: pass (99.5%); H3 false names (name-free) <= 5: pass (2); H4 int8 <= 3.0 MB: pass (2.57 MB).

**Limits.** Wikipedia is not legal text: most of its names are public figures, many foreign. It measures whether the model recognises names in natural Turkish prose, not Katip's accuracy on case files. Turkish Wiki NER is CC BY-SA 4.0; check the licence terms before publishing a model trained on it. All timings are single-thread onnxruntime on one laptop.