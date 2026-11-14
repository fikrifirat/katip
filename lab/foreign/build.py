"""Build the foreign-client sets: tests (sealed) and training mixes.

  python lab/foreign/build.py          # writes lab/data/foreign/*.jsonl (once; delete to rebuild)

Tests (names only from held-out families, never used in training):
  court-foreign       TurkishLegalNER *test* split (Yargıtay prose), the anonymised "..." slots filled with foreign
                      names. Same sentences and slots as court-turkish, so the two can be compared pairwise.
  court-turkish       the same slots filled with Katip's unseen Turkish names (the existing legal "unseen" pool)
  petition-foreign    generated petitions/statements about foreign clients: names, nationality cues, YKN, passport
                      and home-country ID numbers (generated text: a regression check, not a ranking track)
  negatives-foreign   name-free sentences full of words that look like foreign names but aren't: Arabic-origin
                      Turkish words (Hakim, Emir, Rahmet), places (Halep, Tahran, Tiflis), nationality words,
                      and numbers that aren't IDs (UYAP file numbers, "99" amounts)

Training mixes (names only from train families; TLNER *train* split only):
  train-court-foreign   TLNER train split, slots filled with a foreign/Turkish mix
  train-petition-foreign  generated petitions as above
  (synthetic Katip documents and Wiki NER get foreign names swapped in at train time: see mix.py)
"""
from __future__ import annotations

import json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import katiplab as K  # noqa: E402
import legal as L  # noqa: E402
import names as N  # noqa: E402
import ids as I  # noqa: E402

OUT = K.DATA / "foreign"
WEIGHTS = {"arab": .26, "persian": .14, "afghan": .08, "georgian": .09, "armenian": .08, "greek": .07, "slavic": .1, "azeri": .06, "western": .12}

def pick_group(rng):
    return rng.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]

def court(pool: dict, split: str, seed: int, turkish_share: float = 0.0):
    """TLNER sentences of one split with slots filled from `pool` ({group: families}).
    span_groups[i] is the origin group of spans[i] ('kept' = a name the court left readable, Turkish)."""
    rng = random.Random(seed); filled = []
    orig = L._name
    def name(r, first, last):
        if turkish_share and rng.random() < turkish_share:
            n = orig(r, first, last); filled.append((n, "turkish")); return n
        g = pick_group(rng); n = N.sample_name(rng, pool[g], g); filled.append((n, g)); return n
    L._name = name
    try: docs = L.build("unseen", seed)
    finally: L._name = orig
    out, k = [], 0
    for i, d in enumerate(docs):
        mine = filled[k:k + d["masked"]]; k += d["masked"]; j = 0; sg = []
        for a, b, _ in d["spans"]:
            if j < len(mine) and d["text"][a:b] == mine[j][0]: sg.append(mine[j][1]); j += 1
            else: sg.append("kept")
        assert j == len(mine), (i, mine, d["text"][:200])
        if d["split"] != split or not d["masked"]: continue
        out.append({"id": f"court-{split}-{i}", "text": d["text"], "spans": d["spans"], "masked": d["masked"], "kept": d["kept"], "span_groups": sg})
    return out

def court_turkish(split: str, seed: int):
    docs = L.build("unseen", seed)
    return [{"id": f"court-{split}-{i}", "text": d["text"], "spans": d["spans"], "masked": d["masked"], "kept": d["kept"]}
            for i, d in enumerate(docs) if d["split"] == split and d["masked"]]

# ------------------------------------------------------------------------------------------ petitions
CITY = ["İstanbul", "Ankara", "İzmir", "Gaziantep", "Hatay", "Şanlıurfa", "Mersin", "Konya", "Bursa", "Kayseri", "Antalya", "Trabzon"]
COURT = ["{c} {n}. Asliye Hukuk Mahkemesine", "{c} Nöbetçi İdare Mahkemesine", "{c} {n}. İş Mahkemesine", "{c} {n}. Aile Mahkemesine",
         "{c} {n}. Sulh Ceza Hakimliğine", "{c} Cumhuriyet Başsavcılığına", "{c} İl Göç İdaresi Müdürlüğüne", "{c} {n}. Ağır Ceza Mahkemesine"]
OPEN = [
    "Davacı\t\t: {P} ({ID})",
    "Davacı\t\t: {P}, {nat} uyruklu ({ID})",
    "Başvurucu\t: {P} ({ID})",
    "Müşteki\t\t: {P} - {nat} vatandaşı, {ID}",
    "Şüpheli\t\t: {P} ({nat} uyruklu, {ID})",
    "İtiraz Eden\t: {P} ({ID})",
    "Davalı\t\t: {P} ({ID})",
]
BODY = [
    "Müvekkilim {nat} vatandaşı {P}, {d} tarihinde yasal yollarla Türkiye'ye giriş yapmış olup, bu tarihten itibaren {c} ilinde ikamet etmektedir.",
    "Müvekkil {P}, {nat} uyruklu olup geçici koruma statüsünde bulunmaktadır.",
    "Davalı işveren, {nat} uyruklu işçi {P}'yi kayıt dışı çalıştırmıştır.",
    "Tanık {P} ({ID}) beyanında olayı gördüğünü ifade etmiştir.",
    "{nat} vatandaşı olan müvekkilim {P} ile davalı {P2} {d} tarihinde {c} ilinde evlenmişlerdir.",
    "Müvekkilimin eşi {P2} ve çocukları da {nat} vatandaşıdır.",
    "Müvekkil {P} adına düzenlenen ikamet izni {d} tarihinde sona ermiştir.",
    "Tercüman {P2} huzurunda alınan ifadesinde müvekkil {P} suçlamaları kabul etmemiştir.",
    "{P}'nin {nat} makamlarınca verilmiş {ID2} bilgileri dosyaya sunulmuştur.",
    "Kira sözleşmesi kiracı {P} ({ID}) ile kiraya veren arasında akdedilmiştir.",
]
CLOSE = ["Davacı {P} Vekili\nAv. {L}", "Başvurucu\n{P}", "Müşteki Vekili\nAv. {L}", "Saygılarımızla.\n{P} vekili Av. {L}"]
TR_LAWYERS = ("Selin Kaya", "Elif Demir", "Mehmet Aydın", "Zeynep Arslan", "Burak Çelik", "Ayşe Yıldız", "Emre Şahin")

def _render(template: str, vals: dict):
    """Fill {X} slots, track spans. vals: key -> (text, [(a, b, TYPE)] relative to text)."""
    out, spans, i = "", [], 0
    while i < len(template):
        j = template.find("{", i)
        if j < 0: out += template[i:]; break
        out += template[i:j]; k = template.index("}", j); key = template[j + 1:k]
        txt, sp = vals[key]; base = len(out); out += txt
        spans += [(base + a, base + b, t) for a, b, t in sp]; i = k + 1
    return out, spans

def petition(rng, pool, group=None):
    g = group or pick_group(rng); nat = rng.choice(N.NATIONALITY_TR[g])
    p1 = N.sample_name(rng, pool[g], g); g2 = g if rng.random() < .7 else pick_group(rng); p2 = N.sample_name(rng, pool[g2], g2)
    idt, ids_ = I.id_phrase(rng, nat); idt2, ids2 = I.id_phrase(rng, nat)
    lawyer = rng.choice(TR_LAWYERS)
    vals = {"P": (p1, [(0, len(p1), "PERSON")]), "P2": (p2, [(0, len(p2), "PERSON")]), "ID": (idt, ids_), "ID2": (idt2, ids2),
            "L": (lawyer, [(0, len(lawyer), "PERSON")]), "nat": (nat, []), "c": (rng.choice(CITY), []), "n": (str(rng.randint(1, 30)), []),
            "d": (f"{rng.randint(1, 28):02d}.{rng.randint(1, 12):02d}.{rng.randint(2012, 2025)}", [])}
    parts = [rng.choice(COURT).replace("{c}", "{c}"), "", rng.choice(OPEN), "Vekili\t\t: Av. {L}", "", "AÇIKLAMALAR\t:", ""]
    parts += ["\t" + b for b in rng.sample(BODY, rng.randint(2, 4))]
    parts += ["", rng.choice(CLOSE)]
    text, spans = _render("\n".join(parts), vals)
    # the same key reused: _render re-inserts the value and its spans each time
    return {"text": text, "spans": [list(s) for s in spans], "group": g}

# ------------------------------------------------------------------------------------------ negatives
NEG = [
    "Hakim, tarafların beyanlarını dinledikten sonra duruşmayı {d} tarihine erteledi.",
    "Mahkeme heyeti emir ve talimatlara uyulmadığını tespit etmiştir.",
    "Davalı idarenin işlemi hukuka, hakkaniyete ve kanunun açık lafzına aykırıdır.",
    "Müvekkilin Halep'ten Gaziantep'e geldiği, ardından Hatay'a yerleştiği anlaşılmaktadır.",
    "Tahran, Tebriz ve Meşhed konsoloslukları ile yazışma yapılmıştır.",
    "Tiflis Büyükelçiliği ile Batum Başkonsolosluğu'ndan belge istenmiştir.",
    "Erivan'dan gelen tercüme belgeleri dosyaya konulmuştur.",
    "Atina ve Selanik'teki noterlik işlemleri apostil şerhi taşımaktadır.",
    "Şam, Humus, Hama, İdlib ve Kamışlı bölgelerinden göç eden aileler geçici koruma altındadır.",
    "Bağdat, Musul, Kerkük ve Erbil'den gelen başvurular ayrıca değerlendirilir.",
    "Suriyeli, Iraklı, İranlı, Afgan, Gürcü, Ermeni ve Rum vatandaşların başvuruları aynı usule tabidir.",
    "Arap, Fars, Peştun ve Özbek dillerinde tercüman görevlendirilmiştir.",
    "Rahmetli murisin terekesi mirasçılar arasında paylaştırılmıştır.",
    "Vakıf senedinde hayır işlerine tahsis edilen gelirler belirtilmiştir.",
    "Kadı sicilleri ve şer'iye kayıtları tarihi belge niteliğindedir.",
    "Hayat sigortası poliçesindeki lehtar değişikliği geçersizdir.",
    "Selam verip mahkeme salonuna giren tanık yemin etmiştir.",
    "Nur içinde yatsın diyerek söze başlayan tanık, murisin vasiyetinden söz etmiştir.",
    "Şeriat mahkemesi kararlarının tenfizi kamu düzenine aykırılık nedeniyle reddedilmiştir.",
    "Tenfiz davasında yabancı mahkeme kararının kesinleştiği belgelenmelidir.",
    "El yazısı ile düzenlenen vasiyetnamenin el ile yazıldığı bilirkişi raporuyla doğrulanmıştır.",
    "Al sana dedikten sonra sanığın müştekiye tokat attığı tanık beyanlarından anlaşılmaktadır.",
    "Emir komuta zinciri içinde verilen talimatın hukuka aykırılığı açıktır.",
    "Kerim ve Rahim sıfatlarıyla anılan dini vakfın tüzüğü incelenmiştir.",
    "UYAP üzerinden {f} esas sayılı dosyaya ulaşılmıştır.",
    "Dosya No: {f}, Karar No: {f2}.",
    "Davacı adına {m} TL tazminat ödenmesine karar verilmiştir.",
    "Yabancılar ve Uluslararası Koruma Kanunu'nun 46. maddesi uyarınca ikamet izni verilir.",
    "Türk Vatandaşlığı Kanunu'nun 11. maddesi uyarınca başvuru tarihinden geriye doğru beş yıl ikamet şarttır.",
    "Türk Medeni Kanunu ve Türk Borçlar Kanunu hükümleri birlikte değerlendirilmelidir.",
    "Pasaport ve vize işlemleri için Göç İdaresi Başkanlığı'na başvurulmuştur.",
    "Pasaportun geçerlilik süresi dolduğundan yenisinin çıkarılması gerekmektedir.",
    "Yabancı kimlik numarası bulunmayan kişiler pasaport bilgileriyle işlem yapabilir.",
    "Geçici koruma kimlik belgesi kaybolan kişiler en yakın il göç idaresine başvurmalıdır.",
    "Dubai, Doha, Beyrut ve Amman üzerinden yapılan transferler incelenmiştir.",
    "Kabil ve Herat'tan gelen sığınmacılar için ayrı kabul merkezi kurulmuştur.",
]

def negatives(rng, n=200):
    out = []
    for i in range(n):
        lines = []
        for t in rng.sample(NEG, 5):
            lines.append(t.replace("{d}", f"{rng.randint(1, 28):02d}.{rng.randint(1, 12):02d}.{rng.randint(2020, 2026)}")
                          .replace("{f}", f"{rng.randint(2015, 2026)}/{rng.randint(1, 99999)}").replace("{f2}", f"{rng.randint(2015, 2026)}/{rng.randint(1, 9999)}")
                          .replace("{m}", f"{rng.randint(1, 99)}.{rng.randint(100, 999)},00"))
        out.append({"id": f"neg-foreign-{i}", "text": " ".join(lines), "spans": []})
    return out

def write(name, docs):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for d in docs: f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return docs

def get(force: bool = False) -> dict:
    names = ["court-foreign", "court-turkish", "petition-foreign", "negatives-foreign", "train-court-foreign", "train-petition-foreign"]
    if not force and all((OUT / f"{n}.jsonl").exists() for n in names):
        return {n: K.load_jsonl(OUT / f"{n}.jsonl") for n in names}
    sp = N.split(seed=0)
    out = {
        # three fills of each test sentence (different names, same slots); ids "court-test-<i>#<k>": bootstrap by <i>
        "court-foreign": [dict(d, id=f"{d['id']}#{k}") for k in range(3) for d in court(sp["test"], "test", seed=11 + k)],
        "court-turkish": [dict(d, id=f"{d['id']}#{k}") for k in range(3) for d in court_turkish("test", seed=11 + k)],
        "petition-foreign": [{"id": f"pet-foreign-{i}", **petition(random.Random(1000 + i), sp["test"])} for i in range(300)],
        "negatives-foreign": negatives(random.Random(7)),
        "train-court-foreign": court(sp["train"], "train", seed=21, turkish_share=0.3),
        "train-petition-foreign": [{"id": f"trpet-foreign-{i}", **petition(random.Random(50_000 + i), sp["train"])} for i in range(1500)],
    }
    for n, d in out.items(): write(n, d)
    # the held-out families, so anyone can check no test name leaked into training
    (OUT / "heldout_families.json").write_text(json.dumps(sp["test"], ensure_ascii=False))
    return out

if __name__ == "__main__":
    s = get(force="--force" in sys.argv)
    for n, d in s.items():
        print(f"{n:24} {len(d):5} docs  {sum(len(x['spans']) for x in d):6} spans")
