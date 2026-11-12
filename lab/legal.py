"""Real Turkish court prose with known names: TurkishLegalNER (Çetindağ, Yazıcıoğlu & Koç 2022,
Apache-2.0, 2,918 Yargıtay sentences) marks each person, but courts publish decisions anonymised, so
~90% of those names are "...". We put a name back into every masked slot, re-inflect the case suffix
that followed it (…'nin -> Kaya'nın) and keep the slot as the gold span. Names the court left
readable stay as they are.

Two name pools, so the score can't hide behind easy names:
  common  - the most frequent Turkish first names and surnames (what most documents contain)
  unseen  - names from Katip's blind set, never used in any training data (rare, hard)
Casing follows court style: "Ahmet Yılmaz" 40%, "Ahmet YILMAZ" 40%, "AHMET YILMAZ" 20%.
"""
import gzip, json, random, re, urllib.request
from pathlib import Path
import katiplab as K
import suffix as S

URL = "https://raw.githubusercontent.com/koc-lab/turkishlegalner/main/data/train_and_test/{split}.{kind}.txt"
COMMON_FIRST = ("Mehmet Mustafa Ahmet Ali Hüseyin Hasan İbrahim İsmail Osman Yusuf Murat Ömer Ramazan Halil Süleyman "
                "Abdullah Mahmut Recep Salih Fatih Kemal Hakan Emre Burak Serkan Fatma Ayşe Emine Hatice Zeynep Elif "
                "Meryem Şerife Zehra Sultan Hanife Merve Havva Zeliha Esra Fadime Özlem Hacer Melek Yasemin Gülsüm "
                "Hülya Leyla Derya Sevim Ebru").split()
COMMON_LAST = ("Yılmaz Kaya Demir Şahin Çelik Yıldız Yıldırım Öztürk Aydın Özdemir Arslan Doğan Kılıç Aslan Çetin "
               "Kara Koç Kurt Özkan Şimşek Polat Özcan Korkmaz Çakır Erdoğan Yavuz Can Acar Şen Aktaş Güler Yalçın "
               "Güneş Bozkurt Bulut Keskin Ünal Turan Gül Özer Işık Kaplan Avcı Sarı Tekin Taş Köse Yüksel Ateş "
               "Aksoy").split()
TITLES = {"Av", "Av.", "Avukat", "Tetkik", "Hakimi", "Hâkimi", "Hakim", "Hâkim", ".", "Sayın", "Dr", "Dr."}
NOSPACE_BEFORE = set(".,;:!?)]}%") | {"'", "’"}

def upper_tr(s): return s.replace("i", "İ").replace("ı", "I").upper()
def lower_tr(s): return s.replace("I", "ı").replace("İ", "i").lower()
def title_tr(w): return w[:1] + lower_tr(w[1:]) if w.isupper() else w

def _blind_names():
    first, last = set(), set()
    for d in K.load_synth("blind"):
        for a, b, t in d["spans"]:
            if t != "PERSON": continue
            ws = d["text"][a:b].split()
            if len(ws) >= 2:
                first.add(title_tr(ws[0])); last.add(title_tr(ws[-1]))
    return sorted(first), sorted(last)

def _read(split):
    d = K.DATA / "legalner"; d.mkdir(parents=True, exist_ok=True); out = {}
    for kind in ("words", "tags"):
        p = d / f"{split}.{kind}.txt"
        if not p.exists(): urllib.request.urlretrieve(URL.format(split=split, kind=kind), p)
        out[kind] = p.read_text(encoding="utf-8").splitlines()
    return [(w.split(), t.split()) for w, t in zip(out["words"], out["tags"]) if w.strip()]

def _name(rng, first, last):
    f, l = rng.choice(first), rng.choice(last); r = rng.random()
    return f"{f} {l}" if r < .4 else f"{f} {upper_tr(l)}" if r < .8 else upper_tr(f"{f} {l}")

def build(pool="common", seed=0):
    """-> list of {"text", "spans": [[a, b, "PERSON"]], "masked": n_filled, "kept": n_readable}"""
    rng = random.Random(seed)
    first, last = (COMMON_FIRST, COMMON_LAST) if pool == "common" else _blind_names()
    docs = []
    for split in ("train", "test"):
        for words, tags in _read(split):
            text, spans, filled, kept, i = "", [], 0, 0, 0
            prev_name = None
            while i < len(words):
                w, t = words[i], tags[i]
                # glue a separated apostrophe + suffix onto the previous word, re-inflected if that was a filled name
                if w in ("'", "’") and i + 1 < len(words) and re.fullmatch(r"[a-zçğıöşü]+", words[i + 1]):
                    suf = words[i + 1]
                    if prev_name: suf = S.reinflect(suf, prev_name)
                    text += w + suf; i += 2; prev_name = None; continue
                a_ = re.fullmatch(r"(['’])([a-zçğıöşü]+)", w)
                if a_:   # "'in" as its own token: glue it on, agreeing with a filled name
                    text += a_.group(1) + (S.reinflect(a_.group(2), prev_name) if prev_name else a_.group(2))
                    i += 1; prev_name = None; continue
                m = re.fullmatch(r"(\.\.\.)(['’])([a-zçğıöşü]+)", w)
                is_per = t.endswith("PER")
                if is_per and (w == "..." or m):
                    name = _name(rng, first, last)
                    if text and not text.endswith((" ", "\n", "(")): text += " "
                    a = len(text); text += name; spans.append([a, len(text), "PERSON"]); filled += 1
                    if m: text += m.group(2) + S.reinflect(m.group(3), name); prev_name = None
                    else: prev_name = name
                    i += 1; continue
                if is_per and w not in TITLES and w[:1].isupper() and "..." not in w:
                    if text and w not in NOSPACE_BEFORE: text += " "
                    a = len(text); text += w
                    # extend over following readable PER words
                    while i + 1 < len(words) and tags[i + 1].endswith("PER") and tags[i + 1][0] in "IE" and words[i + 1][:1].isupper() and words[i + 1] not in TITLES:
                        i += 1; text += " " + words[i]
                    spans.append([a, len(text), "PERSON"]); kept += 1; prev_name = text[a:]
                    i += 1; continue
                if text and w not in NOSPACE_BEFORE and not text.endswith("("): text += " "
                text += w; prev_name = None; i += 1
            docs.append({"text": text, "spans": spans, "masked": filled, "kept": kept})
    return docs

def get_legal(seed=0):
    """Write data/legal/{common,unseen}.jsonl once and return {pool: docs}."""
    d = K.DATA / "legal"; d.mkdir(parents=True, exist_ok=True); out = {}
    for pool in ("common", "unseen"):
        p = d / f"{pool}.jsonl"
        if not p.exists():
            with p.open("w", encoding="utf-8") as f:
                for i, doc in enumerate(build(pool, seed)): f.write(json.dumps({"id": f"legal-{pool}-{i}", **doc}, ensure_ascii=False) + "\n")
        out[pool] = K.load_jsonl(p)
    return out
