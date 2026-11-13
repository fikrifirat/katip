"""Foreign client names as they appear in Turkish legal documents: transliterated into Latin script, with the
inconsistent spellings Turkish lawyers, translators and the Göç İdaresi actually produce.

Groups (who Turkish lawyers now represent, per a practising Ankara lawyer, Nov 2026):
  arab        Syrian, Iraqi, Levantine, Gulf, Egyptian           curated Latin forms + spelling-variant rules
  persian     Iranian                                            curated Latin forms + variant rules
  afghan      Afghan (Dari/Pashto)                               curated Latin forms + variant rules
  georgian    Georgian                                           Faker ka_GE (Georgian script) -> 2 romanisations
  armenian    Armenian                                           Faker hy_AM (Armenian script) -> 2 romanisations
  greek       Greek                                              Faker el_GR (Greek script) -> 2 romanisations
  slavic      Russian, Ukrainian                                 Faker ru_RU, uk_UA (Cyrillic) -> 2 romanisations
  azeri       Azerbaijani                                        Faker az_AZ (Latin, with ə)
  western     American, British, French, German, Italian, Spanish, Dutch   Faker en_US, en_GB, fr_FR, de_DE, it_IT, es_ES, nl_NL

Sources and licences: Faker's person providers (MIT, https://github.com/joke2k/faker); the curated Arabic,
Persian and Afghan lists are written for this lab (CC0). Wikidata given/family names (CC0) are the planned
next source; Wikidata was not reachable from the build machine, see README. We deliberately do NOT use the
`names-dataset` package: its data comes from the 2021 Facebook scrape of 533M accounts.

Held-out split: a name *family* (a base name and every spelling of it) goes wholly to train or wholly to test,
so "unseen" really means the model never saw any spelling of that name.

  families(group)              -> {"first": [[variant, ...], ...], "last": [[variant, ...], ...]}
  split(seed=0, test_share=.3) -> {"train": {group: fam}, "test": {group: fam}, "common": {group: fam}}
  sample_name(rng, fam, group) -> "Mhd Abdulrahman EL-HASAN" (a full name in a court casing)
"""
from __future__ import annotations

import importlib, random, re, unicodedata

GROUPS = ["arab", "persian", "afghan", "georgian", "armenian", "greek", "slavic", "azeri", "western"]
GROUP_TR = {"arab": "Arap (Suriye, Irak, ...)", "persian": "İranlı", "afghan": "Afgan", "georgian": "Gürcü",
            "armenian": "Ermeni", "greek": "Yunan", "slavic": "Rus / Ukraynalı", "azeri": "Azerbaycanlı",
            "western": "Batılı (ABD, AB)"}
NATIONALITY_TR = {"arab": ["Suriye", "Irak", "Ürdün", "Lübnan", "Mısır", "Suudi Arabistan", "Libya", "Filistin"],
                  "persian": ["İran"], "afghan": ["Afganistan"], "georgian": ["Gürcistan"], "armenian": ["Ermenistan"],
                  "greek": ["Yunanistan"], "slavic": ["Rusya Federasyonu", "Ukrayna"], "azeri": ["Azerbaycan"],
                  "western": ["Amerika Birleşik Devletleri", "Almanya", "Fransa", "İngiltere", "İtalya", "İspanya", "Hollanda"]}

# ------------------------------------------------------------------------------------- curated lists (CC0)
# One canonical spelling per family; variants() derives the rest. Most frequent first (the first 15 of each
# list form the "common" pool, which training always sees).
ARAB_FIRST = """Mohammad Ahmad Ali Mahmoud Khaled Omar Youssef Ibrahim Abdulrahman Hassan Hussein Mustafa Abdullah Bilal
Jamal Walid Samir Nabil Rami Fadi Tarek Ziad Bassam Hisham Imad Kamal Mazen Majed Nizar Osama Qasim Raed Saeed Salah Talal
Wael Yasser Zakaria Adnan Anas Ayman Basel Firas Ghassan Hamza Haitham Hazem Iyad Jihad Karim Louay Marwan Moaz Muhannad Nidal
Obada Riyad Safwan Shadi Tamer Yaman Zuhair Abdulkarim Abdulaziz Abdulqader Abdelhamid Abdulsalam Abdulwahab Abdulmajid
Fatima Aisha Maryam Zainab Khadija Amina Huda Rania Hiba Lina Nour Rana Reem Salma Samar Sara Yasmin Dima Ghada Hanan Iman
Jumana Lama Lubna Majd Manal Mays Nada Najwa Nisreen Rasha Ruba Sawsan Suha Wafaa Widad Zeina Asmaa Batoul Duaa Raghad Shahd""".split()
ARAB_LAST = """Al-Ahmad Al-Hassan Al-Hussein Al-Ali Al-Khalil Al-Omar Al-Mahmoud Al-Abdullah Al-Saleh Al-Ibrahim Al-Hamoud
Al-Masri Al-Halabi Al-Shami Al-Homsi Al-Hamwi Al-Idlibi Al-Dimashqi Al-Kurdi Al-Turkmani Al-Najjar Al-Haddad Al-Khatib
Al-Sheikh Al-Rifai Al-Zoubi Al-Bitar Al-Jabri Al-Attar Al-Hakim Al-Daher Al-Assaf Al-Qassem Al-Mousa Al-Issa Al-Yousef
Al-Rashid Al-Tamimi Al-Obaidi Al-Jubouri Al-Dulaimi Al-Shammari Al-Zubaidi Al-Rubaie Al-Ani Al-Tikriti Al-Samarrai
Haddad Khoury Nasrallah Hamdan Darwish Mansour Barakat Saleh Qasim Othman Suleiman Habib Sabbagh Kabbani Ghanem Shaaban
Hijazi Jaber Kanaan Makhlouf Nassar Qabbani Sabbah Tlass Zaher Hammoud Kassab Sawaf Dabbagh Chalabi Hariri Atassi Mardini""".split()
PERSIAN_FIRST = """Mohammad Ali Hossein Reza Mehdi Amir Hamid Saeed Mohsen Majid Ahmad Hassan Mahmoud Javad Abbas Morteza Mostafa
Masoud Behzad Bahram Dariush Farhad Kourosh Siavash Arash Babak Kaveh Payam Pouya Ramin Shahram Omid Navid Peyman
Hooman Kamran Mehran Farshid Ehsan Alireza Mohammadreza Amirhossein Gholamreza Hamidreza Esmaeil Yousef Nima Sina Soroush
Fatemeh Zahra Maryam Sara Narges Mahsa Neda Shirin Parisa Leila Nazanin Roya Mina Samira Elham Fereshteh Golnaz Mitra
Azadeh Shabnam Taraneh Yasaman Bahareh Niloufar Sepideh Somayeh Mahboubeh Marzieh Zeinab Hoda Ladan Pegah Negin Setareh""".split()
PERSIAN_LAST = """Mohammadi Hosseini Ahmadi Rezaei Mousavi Jafari Karimi Rahimi Hashemi Ghasemi Sadeghi Ebrahimi Moradi
Kazemi Heidari Ghorbani Salehi Rostami Abbasi Najafi Shirazi Esfahani Tehrani Tabrizi Mashhadi Kermani Yazdi Hamedani
Ahmadinejad Rafsanjani Khamenei Larijani Zarif Rouhani Khatami Bakhtiari Farahani Golestani Kashani Naderi Nasiri Navabi
Hosseinzadeh Alizadeh Hassanzadeh Rezazadeh Taghizadeh Mirzazadeh Ghorbanzadeh Hajizadeh Akbarpour Hassanpour Alipour
Rahimpour Karimpour Ghanbarpour Mohammadpour Shahpour Jahanpour Esmaeilpour Rahnama Tavakoli Mirzaei Sharifi Zamani
Mahdavi Amini Bagheri Daneshvar Farahmand Nikpour Pakzad Rahmani Safavi Sobhani Tehranchi Vahidi Yazdani""".split()
AFGHAN_FIRST = """Ahmad Mohammad Abdul Ghulam Khan Rahmatullah Hamidullah Najibullah Zabihullah Ezatullah Habibullah
Sayed Mirwais Ahmadshah Gul Wali Nasir Hekmat Ajmal Shafiq Rahim Karim Jawad Fawad Javid Farid Hamid Masoud Wahid Zalmai
Bibi Gulalai Malalai Fereshta Shabana Zarghona Nazia Mursal Freshta Hila Mariam Fatima Zahra Sima Roya Nilofar Laila""".split()
AFGHAN_LAST = """Ahmadzai Popal Durrani Noorzai Hotak Stanikzai Barakzai Alokozai Achakzai Mohmand Safi Shinwari Wardak
Karzai Ghani Sultani Hakimi Rahimi Karimi Amiri Haidari Hashimi Rasuli Sadat Naziri Akbari Azizi Nazari Qaderi Yousufzai
Mangal Zadran Kakar Niazi Sherzad Jalali Mohammadi Ahmadi Rahmani Habibi Nabizada Hussaini Sharifi Faizi Wahidi Samadi""".split()

# Spelling-variant rules for Arabic/Persian/Afghan Latin forms: (pattern, [replacements]). Each rule fires with
# some probability, so each family gets a handful of attested-looking spellings.
_FIXED = {  # whole-word families that rules don't capture well
    "Mohammad": ["Mohammad", "Mohammed", "Muhammad", "Muhammed", "Mohamad", "Mohamed", "Muhamed", "Mhd", "Mhd.", "Mohd", "Muhamad"],
    "Hossein": ["Hossein", "Hosein", "Hussein", "Hüseyin", "Hosseyn", "Hossain", "Husain"],
    "Hussein": ["Hussein", "Husein", "Hüseyin", "Hussain", "Husayn", "Hossein"],
    "Youssef": ["Youssef", "Yousef", "Yusuf", "Yousif", "Yussef", "Yosef", "Youcef"],
    "Reza": ["Reza", "Rıza", "Riza", "Rezā"],
    "Fatemeh": ["Fatemeh", "Fateme", "Fatima", "Fatma", "Fatemah"],
    "Esmaeil": ["Esmaeil", "Esmail", "Ismail", "İsmail", "Esmaeel", "Smail"],
    "Sayed": ["Sayed", "Seyed", "Seyyed", "Sayyid", "Seyit", "Said", "Syed"],
    "Abdul": ["Abdul", "Abdal", "Abdel", "Abdül", "Abd"],
    "Omar": ["Omar", "Umar", "Ömer", "Omer"],
    "Osama": ["Osama", "Usama", "Usame", "Ossama"],
    "Aisha": ["Aisha", "Aysha", "Ayşe", "Aicha", "Aishah", "Ayesha"],
    "Zainab": ["Zainab", "Zeinab", "Zeynep", "Zaynab", "Zeyneb"],
    "Khadija": ["Khadija", "Khadijah", "Hatice", "Hadija", "Khadeeja"],
    "Mostafa": ["Mostafa", "Mustafa", "Moustafa", "Mostapha"],
    "Mustafa": ["Mustafa", "Moustafa", "Mostafa", "Mustapha"],
}
_RULES = [
    (r"^Abd(?:ul|el|al)?(?=[A-Z])", lambda m, r: r.choice(["Abdul", "Abdel", "Abdül", "Abdal", "Abd al-", "Abd Al-", "Abdul ", "Abdel "])),
    (r"^Abdulr", lambda m, r: r.choice(["Abdulr", "Abdurr", "Abdur", "Abdel R", "Abd al-R", "Abdul R", "Abdelr"])),
    (r"^Al-", lambda m, r: r.choice(["Al-", "Al-", "Al ", "El-", "El ", "el-", "al-", "Al", "El"])),
    (r"ou", lambda m, r: r.choice(["ou", "u", "o"])),
    (r"oo", lambda m, r: r.choice(["oo", "u", "ou"])),
    (r"ee", lambda m, r: r.choice(["ee", "i"])),
    (r"(?<=[a-z])([bcdfghjklmnprstvz])\1", lambda m, r: r.choice([m.group(0), m.group(1)])),
    (r"kh|Kh", lambda m, r: r.choice([m.group(0), m.group(0)[0] if r.random() < .3 else ("H" if m.group(0)[0] == "K" else "h")])),
    (r"gh|Gh", lambda m, r: r.choice([m.group(0), "q" if m.group(0)[0] == "g" else "Q", "ğ" if m.group(0)[0] == "g" else "G"])),
    (r"q|Q", lambda m, r: r.choice([m.group(0), "k" if m.group(0) == "q" else "K"])),
    (r"sh|Sh", lambda m, r: r.choice([m.group(0), "ş" if m.group(0)[0] == "s" else "Ş", "ch" if m.group(0)[0] == "s" else "Ch"])),
    (r"j|J", lambda m, r: r.choice([m.group(0), "c" if m.group(0) == "j" else "C", "dj" if m.group(0) == "j" else "Dj"])),
    (r"(?<=[a-z])a(?=d$|r$|n$)", lambda m, r: r.choice(["a", "e"])),
    (r"(?<=[a-z])e(?=d$|r$|n$)", lambda m, r: r.choice(["e", "a"])),
    (r"a$", lambda m, r: r.choice(["a", "ah", "e"])),
    (r"eh$", lambda m, r: r.choice(["eh", "e"])),
    (r"zadeh$", lambda m, r: r.choice(["zadeh", "zade", "zâde", "zada", "-zadeh", "zadé"])),
    (r"pour$", lambda m, r: r.choice(["pour", "pur", "poor", "pûr"])),
    (r"nejad$", lambda m, r: r.choice(["nejad", "nezhad", "nejat", "nezad", "nijad"])),
    (r"(?<=[a-z]{3})i$", lambda m, r: r.choice(["i", "i", "i", "y", "ee"])),
    (r"aei$|ai$", lambda m, r: r.choice([m.group(0), "ayi", "ai", "aee", "ei"])),
    (r"w|W", lambda m, r: r.choice([m.group(0), "v" if m.group(0) == "w" else "V"])),
]

def _rule_variants(base: str, rng: random.Random, n: int = 6) -> list[str]:
    out = {base}
    for _ in range(n * 4):
        v = base
        for pat, rep in _RULES:
            if rng.random() < .35: v = re.sub(pat, lambda m: rep(m, rng), v, count=1)
        v = re.sub(r"\s+", " ", v).strip()
        if len(v) >= 2: out.add(v)
        if len(out) >= n: break
    return sorted(out, key=lambda x: (x != base, x))

# --------------------------------------------------------------------------- romanising native-script names
_KA = {"ა": "a", "ბ": "b", "გ": "g", "დ": "d", "ე": "e", "ვ": "v", "ზ": "z", "თ": "t", "ი": "i", "კ": "k", "ლ": "l", "მ": "m",
       "ნ": "n", "ო": "o", "პ": "p", "ჟ": ("zh", "j"), "რ": "r", "ს": "s", "ტ": "t", "უ": "u", "ფ": "p", "ქ": "k", "ღ": ("gh", "ğ"),
       "ყ": ("q", "k"), "შ": ("sh", "ş"), "ჩ": ("ch", "ç"), "ც": "ts", "ძ": "dz", "წ": "ts", "ჭ": ("ch", "ç"), "ხ": ("kh", "h"),
       "ჯ": ("j", "c"), "ჰ": "h"}
_HY = {"ա": "a", "բ": "b", "գ": "g", "դ": "d", "ե": "e", "զ": "z", "է": "e", "ը": ("y", "ı"), "թ": "t", "ժ": ("zh", "j"), "ի": "i",
       "լ": "l", "խ": ("kh", "h"), "ծ": "ts", "կ": "k", "հ": "h", "ձ": "dz", "ղ": ("gh", "ğ"), "ճ": ("ch", "ç"), "մ": "m", "յ": "y",
       "ն": "n", "շ": ("sh", "ş"), "ո": "o", "չ": ("ch", "ç"), "պ": "p", "ջ": ("j", "c"), "ռ": "r", "ս": "s", "վ": "v", "տ": "t",
       "ր": "r", "ց": "ts", "ւ": "v", "փ": "p", "ք": "k", "օ": "o", "ֆ": "f", "և": "ev"}
_GR = {"α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
       "ν": "n", "ξ": ("x", "ks"), "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": ("y", "i"), "φ": "f",
       "χ": ("ch", "h"), "ψ": "ps", "ω": "o"}
_GR2 = [("ου", ("ou", "u")), ("αι", ("ai", "e")), ("ει", ("ei", "i")), ("οι", ("oi", "i")), ("αυ", ("av", "af")),
        ("ευ", ("ev", "ef")), ("μπ", ("mp", "b")), ("ντ", ("nt", "d")), ("γκ", ("gk", "g")), ("γγ", ("ng", "ng"))]
_CY = {"а": "a", "б": "b", "в": "v", "г": ("g", "g"), "ґ": "g", "д": "d", "е": "e", "є": ("ye", "ye"), "ё": ("yo", "yo"),
       "ж": ("zh", "j"), "з": "z", "и": ("i", "i"), "і": "i", "ї": ("yi", "yi"), "й": ("y", "y"), "к": "k", "л": "l", "м": "m",
       "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": ("kh", "h"), "ц": "ts",
       "ч": ("ch", "ç"), "ш": ("sh", "ş"), "щ": ("shch", "şç"), "ъ": "", "ы": ("y", "ı"), "ь": "", "э": "e", "ю": "yu", "я": "ya"}

def _strip_accents(s): return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def romanise(word: str, table: dict, scheme: int, digraphs=()) -> str:
    """scheme 0 = English-style (sh, ch, kh, j), 1 = Turkish-style (ş, ç, h, c)."""
    w = _strip_accents(word).lower() if table is _GR else word.lower()
    if "ա" in table: w = w.replace("ու", "u")
    for g, rep in digraphs: w = w.replace(g, rep[scheme])
    out = []
    for c in w:
        r = table.get(c, c); out.append(r[scheme] if isinstance(r, tuple) else r)
    s = "".join(out).replace("ʼ", "").replace("'", "")
    return s[:1].upper() + s[1:] if s else s

def _native_families(locale: str, table, digraphs=(), extra=None) -> dict:
    P = importlib.import_module(f"faker.providers.person.{locale}").Provider
    def uniq(x): return list(dict.fromkeys(x.keys() if isinstance(x, dict) else x))
    first = uniq(getattr(P, "first_names_male", ())) + uniq(getattr(P, "first_names_female", ()))
    last = uniq(getattr(P, "last_names", ())) + uniq(getattr(P, "last_names_male", ())) + uniq(getattr(P, "last_names_female", ()))
    male = set(uniq(getattr(P, "first_names_male", ())))
    rom = lambda w: sorted({romanise(w, table, 0, digraphs), romanise(w, table, 1, digraphs)})
    malef = [rom(w) for w in dict.fromkeys(male) if " " not in w]
    first = [rom(w) for w in dict.fromkeys(first) if " " not in w]
    lastf = []
    for w in dict.fromkeys(last):
        if " " in w or "-" in w: continue
        v = {romanise(w, table, 0, digraphs), romanise(w, table, 1, digraphs)}
        if extra: v |= extra(romanise(w, table, 0, digraphs))
        lastf.append(sorted(v))
    return {"first": [f for f in first if len(f[0]) > 1], "last": [f for f in lastf if len(f[0]) > 1], "male": [f for f in malef if len(f[0]) > 1]}

def _hy_extra(w):   # -yan is also written -ian, -jan (German), -yants
    return {re.sub(r"yan$", "ian", w), re.sub(r"yan$", "jan", w)} if w.endswith("yan") else set()
def _gr_extra(w):
    out = set()
    if w.endswith("opoulos"): out |= {w[:-7] + "opulos", w[:-7] + "opoulo"}
    if w.endswith("idis"): out |= {w[:-4] + "ides", w[:-4] + "idhis"}
    if w.endswith("akis"): out |= {w[:-4] + "akes"}
    return out
def _cy_extra(w):
    out = set()
    for a, b in (("ov", "ow"), ("ov", "off"), ("ev", "yev"), ("in", "ine"), ("ko", "ko"), ("ova", "ova")):
        if w.endswith(a): out.add(w[: -len(a)] + b)
    return out

def _latin_families(locales) -> dict:
    first, last, male = {}, {}, {}
    for loc in locales:
        P = importlib.import_module(f"faker.providers.person.{loc}").Provider
        for attr, dst in (("first_names_male", first), ("first_names_male", male), ("first_names_female", first), ("last_names", last)):
            xs = getattr(P, attr, ())
            for w in (xs.keys() if isinstance(xs, dict) else xs):
                if " " in w or len(w) < 2 or "'" in w: continue
                variants = {w}
                a = _strip_accents(w)
                if a != w: variants.add(a)            # Müller -> Muller, François -> Francois
                if loc == "de_DE" and "ü" in w: variants.add(w.replace("ü", "ue"))
                if loc == "de_DE" and "ö" in w: variants.add(w.replace("ö", "oe"))
                if "ß" in w: variants.add(w.replace("ß", "ss"))
                if "ə" in w.lower(): variants.add(w.replace("ə", "e").replace("Ə", "E"))   # Azeri ə is typed e in Turkey
                dst.setdefault(a.lower(), set()).update(variants)
    return {"first": [sorted(v) for v in first.values()], "last": [sorted(v) for v in last.values()], "male": [sorted(v) for v in male.values()]}

_FEMALE_START = {"arab": "Fatima", "persian": "Fatemeh", "afghan": "Bibi"}

def _curated(first, last, seed, female_start) -> dict:
    rng = random.Random(seed)
    fam = lambda base: _FIXED.get(base) or _rule_variants(base, rng)
    first = list(dict.fromkeys(first)); k = first.index(female_start)
    return {"first": [fam(w) for w in first], "last": [fam(w) for w in dict.fromkeys(last)], "male": [fam(w) for w in first[:k]]}

_CACHE: dict = {}
def families(group: str) -> dict:
    if group in _CACHE: return _CACHE[group]
    if group == "arab": f = _curated(ARAB_FIRST, ARAB_LAST, 1, _FEMALE_START["arab"])
    elif group == "persian": f = _curated(PERSIAN_FIRST, PERSIAN_LAST, 2, _FEMALE_START["persian"])
    elif group == "afghan": f = _curated(AFGHAN_FIRST, AFGHAN_LAST, 3, _FEMALE_START["afghan"])
    elif group == "georgian": f = _native_families("ka_GE", _KA)
    elif group == "armenian": f = _native_families("hy_AM", {**_HY, **{k.upper(): v for k, v in _HY.items()}}, extra=_hy_extra)
    elif group == "greek": f = _native_families("el_GR", _GR, _GR2, extra=_gr_extra)
    elif group == "slavic":
        a, b = _native_families("ru_RU", _CY, extra=_cy_extra), _native_families("uk_UA", _CY, extra=_cy_extra)
        f = {k: a[k] + b[k] for k in a}
    elif group == "azeri": f = _latin_families(["az_AZ"])
    elif group == "western": f = _latin_families(["en_US", "en_GB", "fr_FR", "de_DE", "it_IT", "es_ES", "nl_NL"])
    else: raise KeyError(group)
    # Azerbaijani/German lists carry some Turkish or Arabic names (Abbas, Abdullah); a family whose every spelling
    # is in Katip's Turkish name lists isn't foreign for this test, so drop it.
    from katiplab import _FIRST, _LAST, fold
    tr = _FIRST | _LAST
    for k in ("first", "last", "male"):
        seen, keep = set(), []
        for v in f[k]:
            key = fold(v[0])
            if key in seen or all(fold(x) in tr for x in v): continue
            seen.add(key); keep.append(v)
        f[k] = keep
    _CACHE[group] = f
    return f

COMMON_N = 15     # the first N families of a curated list (most frequent) are the "common" pool

def split(seed: int = 0, test_share: float = 0.3) -> dict:
    """Family-level split. common = the most frequent names (always in train); test = held-out families only."""
    out = {"train": {}, "test": {}, "common": {}}
    for g in GROUPS:
        fam = families(g); rng = random.Random(f"{seed}-{g}")
        tr, te, co = {}, {}, {}
        for k in ("first", "last"):
            xs = list(fam[k])
            curated = g in ("arab", "persian", "afghan")
            head = xs[:COMMON_N] if curated else []
            rest = xs[COMMON_N:] if curated else xs[:]
            rng.shuffle(rest)
            n_te = int(round(len(rest) * test_share))
            te[k], tr[k] = rest[:n_te], head + rest[n_te:]
            co[k] = head if head else tr[k][:COMMON_N]
        males = {tuple(v) for v in fam["male"]}
        for dst in (tr, te, co): dst["male"] = [v for v in dst["first"] if tuple(v) in males] or dst["first"]
        out["train"][g], out["test"][g], out["common"][g] = tr, te, co
    return out

# ------------------------------------------------------------------------------------- full names in court casing
def upper_tr(s): return s.replace("i", "İ").replace("ı", "I").upper()

def sample_parts(rng: random.Random, fam: dict, group: str) -> list[str]:
    """Name words in reading order, before casing: ['Mhd', 'Khaled', 'Al-Ali']."""
    pick = lambda k: rng.choice(rng.choice(fam[k]))
    is_male = rng.random() < .6
    words = [pick("male") if is_male else pick("first")]
    if group in ("arab", "afghan") and rng.random() < .35: words.append(pick("male"))        # father's name: Mohammad Khaled Al-Ali
    if group == "persian" and is_male and rng.random() < .2: words.append(pick("male"))      # Mohammad Reza
    if group == "arab" and is_male and rng.random() < .1: words += [rng.choice(["bin", "ibn", "Bin"]), pick("male")]
    if group == "slavic" and rng.random() < .3:                                               # patronymic
        p = re.sub(r"[aeiouy]$", "", pick("male")); words.append(p + (rng.choice(["ovich", "eviç", "ovic"]) if is_male else rng.choice(["ovna", "evna"])))
    if group == "western" and rng.random() < .15: words.append(pick("first"))
    return " ".join(words).split() + [pick("last")]

def sample_name(rng: random.Random, fam: dict, group: str) -> str:
    """A full name the way it is typed in Turkish petitions: 'Mhd Abdulrahman EL-HASAN', 'Nino BERİDZE'."""
    w = sample_parts(rng, fam, group); first, last = " ".join(w[:-1]), w[-1]
    r = rng.random()
    if r < .4: return f"{first} {last}"
    if r < .8: return f"{first} {upper_tr(last)}"
    return upper_tr(f"{first} {last}")
