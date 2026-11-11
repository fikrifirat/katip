"""Generate training text for the Katip name tagger from the synthetic templates.

Text-only (no PDF/scan rendering). Person names come from a wide pool: Faker tr_TR,
Katip's gazetteers, the dev-set names, and surnames composed from Turkish surname
morphemes. Every name used by the BLIND set (eval/synth_blind.py) is removed, so the
blind score measures names the model has never seen.

  python gen_train.py <katip-redact dir> <out.jsonl> <n_docs> <seed>
"""
import json, random, sys
from pathlib import Path

root = Path(sys.argv[1]); sys.path[:0] = [str(root / "eval"), str(root)]
import synth, synth_blind  # noqa: E402
from katip_redact.textutil import fold, wordlist  # noqa: E402

out, n, seed = Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
random.seed(seed); synth.Faker.seed(seed)
fk = synth.fk
BLIND = {fold(x) for x in synth_blind._F + synth_blind._L}

PRE = ["Kara", "Ak", "Demir", "Yıldız", "Gök", "Al", "Er", "Öz", "Tan", "Koç", "Kurt", "Şen", "Uz", "Bay", "Kılıç", "Çelik",
       "Taş", "Su", "Yaz", "Can", "Ay", "Gül", "Bal", "Dağ", "Kaya", "Ateş", "Bulut", "Sarı", "Ulu", "Yurt", "Ilgar", "Tuna"]
SUF = ["oğlu", "can", "soy", "er", "türk", "kaya", "han", "dağ", "lı", "li", "baş", "taş", "ok", "alp", "yiğit", "öz", "men",
       "tekin", "doğan", "bey", "göz", "kan", "yol", "el", "ay", "gil", "tepe", "kurt", "su", "sel"]
FIRST_EXTRA = ["Alp", "Berk", "Deniz", "Ece", "Ela", "Eren", "Hira", "İpek", "Kaan", "Lara", "Mert", "Nil", "Onur", "Pelin",
               "Selin", "Tuna", "Umay", "Yağmur", "Zeynep", "Arda", "Bora", "Cem", "Derin", "Efe", "Feza", "Hazal"]

def ok(x): return fold(x) not in BLIND
first_pool = sorted({w.title() for w in wordlist("first_names.txt")} | set(FIRST_EXTRA) | set(synth.UNSEEN_FIRST)
                    | {fk.first_name() for _ in range(3000)})
last_pool = sorted({w.title() for w in wordlist("last_names.txt")} | set(synth.UNSEEN_LAST) | {fk.last_name() for _ in range(3000)}
                   | {p + s for p in PRE for s in SUF})
first_pool = [x for x in first_pool if ok(x) and len(x) > 1]
last_pool = [x for x in last_pool if ok(x) and len(x) > 1]

def person():
    first, last = random.choice(first_pool), random.choice(last_pool)
    if random.random() < 0.15: first = f"{first} {random.choice(first_pool)}"
    style = random.choices(["title", "lastupper", "upper"], [0.5, 0.3, 0.2])[0]
    return synth.Person(first, last, False, style)
synth.person = person

# distractors: ordinary words in name-like positions (sentence starts, Title Case, ALL CAPS
# headings). Random draws from the general frequency list only, nothing taken from eval sets.
names_f = wordlist("first_names.txt") | wordlist("last_names.txt")
COMMON = [w for w in (root / "katip_redact/data/common_words.txt").read_text(encoding="utf-8").split()[:12000]
          if w.isalpha() and len(w) > 2 and fold(w) not in names_f]
up = synth.tr_upper
def cap(w): return up(w[0]) + w[1:]
def distractor():
    k = random.random(); ws = random.sample(COMMON, random.randint(1, 4))
    if k < 0.3: return up(" ".join(ws)) + random.choice([":", "", "\n"])
    if k < 0.6: return " ".join(cap(w) for w in ws) + random.choice([":", ",", "", " "])
    return cap(ws[0]) + " " + " ".join(random.sample(COMMON, random.randint(3, 9))) + random.choice([".", ",", ":"])

def augment(b):
    """Insert distractor lines at line breaks and shift the gold spans."""
    text, gold = b.text, b.gold
    cuts = [i + 1 for i, c in enumerate(text) if c == "\n"]
    ins = sorted(random.sample(cuts, min(len(cuts), random.randint(1, 4)))) if cuts else []
    out, shift, last, new_gold = [], 0, 0, []
    offs = []
    for c in ins:
        out.append(text[last:c]); d = distractor() + "\n"; out.append(d); offs.append((c, len(d))); last = c
    out.append(text[last:])
    for g in gold:
        sh = sum(n for c, n in offs if c <= g["start"])
        new_gold.append({**g, "start": g["start"] + sh, "end": g["end"] + sh})
    return "".join(out), new_gold

templates = {**synth.TEMPLATES, **synth.TEMPLATES_HARD}
names = list(templates)
with out.open("w", encoding="utf-8") as f:
    for i in range(n):
        b = synth.B(); templates[names[i % len(names)]](b)
        text, gold = augment(b) if random.random() < 0.7 else (b.text, b.gold)
        assert all(text[g["start"]:g["end"]] == g["text"] for g in gold)
        f.write(json.dumps({"text": text, "spans": [[g["start"], g["end"], g["entity_type"]] for g in gold]}, ensure_ascii=False) + "\n")
print(f"{n} docs, {len(first_pool)} first names, {len(last_pool)} last names, templates: {names}", file=sys.stderr)
