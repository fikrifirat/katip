"""Katip Emsal MVP: find Yargıtay decisions for a masked petition.

    pip install turk-hukuku-ictihat-mcp==0.5.1
    python lab/emsal/emsal.py PETITION.maskeli.udf --out OUTDIR
    python lab/emsal/emsal.py PETITION.txt --out OUTDIR --gold yargitay:464064700   # also score one known-good decision

What it does, in order:
  1. Reads a petition that Katip has ALREADY MASKED (.udf, .txt). Masked blocks (█) are dropped.
  2. Picks the petition's distinctive legal words and statute citations, on this computer.
  3. Writes a few short keyword queries from those words. Privacy guard: a query may only hold lowercase words
     that appear in the petition, no digits and no capitalised words, so names, numbers and places the mask
     missed cannot leave. Every query sent is listed in the report.
  4. Sends the queries to the official Bedesten service (the back end of mevzuat.adalet.gov.tr), through the
     MIT-licensed turk-hukuku-ictihat-mcp client: it names itself, sends one request at a time, and we space
     requests 3 seconds apart. It stops on a 429, a CAPTCHA or a login page.
  5. Fetches the full text of the best candidates, re-ranks them here against the whole petition (BM25 on
     five-letter word stems, plus statute overlap), and picks the paragraph that matches best as a quote.
  6. Verifies each decision: its esas and karar numbers must appear in the official text we fetched.
     Unverified decisions are dropped, never shown.

Outputs in OUTDIR: report.html (for the lawyer), results.json (everything, for the evaluation),
grading.csv (for a lawyer to grade the top 10), queries.txt (exactly what left this computer).
Nothing is written into the repository; keep OUTDIR outside it when the petition is real.
"""
from __future__ import annotations

import argparse, csv, html, json, math, re, sys, time, zipfile
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASK = "█"
GAP_SECONDS = 3.0
GK_PAGES = 3              # General Assembly decisions are few and weigh most: read three result pages
CACHE = Path.home() / ".cache" / "katip-emsal"     # public decision texts and word counts only          # one request every 3 s: Yargıtay's service throttled us at 1/s (lab/legal/crawl.py)

# ---------------------------------------------------------------- reading
def read_petition(path: Path) -> str:
    """Text of a .udf (UYAP: zip with content.xml, text in CDATA) or a plain text file."""
    if path.suffix.lower() == ".udf":
        with zipfile.ZipFile(path) as z:
            xml = z.read("content.xml").decode("utf-8", "replace")
        m = re.search(r"<!\[CDATA\[(.*?)\]\]>", xml, re.S)
        return m.group(1) if m else re.sub(r"<[^>]+>", " ", xml)
    return path.read_text(encoding="utf-8", errors="replace")

def unmask(text: str) -> str:
    """Drop masked blocks and placeholder tags, keep the readable text."""
    text = re.sub(MASK + r"+", " ", text)
    text = re.sub(r"\[[A-ZÇĞİÖŞÜ _]{2,30}\]", " ", text)          # [AD SOYAD], [TCKN] style placeholders
    return text

# ---------------------------------------------------------------- words
FOLD = str.maketrans("çğıöşüâîûÇĞIİÖŞÜÂÎÛ", "cgiosuaiuCGIIOSUAIU")
def fold(w: str) -> str:
    return w.translate(FOLD).lower()

def lower_tr(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()

WORD = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]+")

def stem(w: str) -> str:
    """First five letters of the folded word. Simple and well studied for Turkish retrieval
    (Can et al., 2008, 'Information retrieval on Turkish texts', JASIST 59(3))."""
    return fold(w)[:5]

def _load_common() -> dict[str, int]:
    """Rank of a word in everyday Turkish (OpenSubtitles list in the browser bundle, CC BY-SA 4.0)."""
    z = HERE.parents[1] / "docs" / "katip_py.zip"
    ranks: dict[str, int] = {}
    try:
        with zipfile.ZipFile(z) as f:
            lines = f.read("katip_redact/data/common_words.txt").decode("utf-8").splitlines()
    except (FileNotFoundError, KeyError):
        return ranks
    r = 0
    for line in lines:
        if line.startswith("# legal"):            # hand-added legal words at the end: not frequency ranked
            break
        if line.startswith("#") or not line.strip():
            continue
        r += 1
        ranks.setdefault(line.strip(), r)
    return ranks

COMMON = _load_common()

# Words every petition and decision uses. They say nothing about the legal issue, so they never become
# query words. Fixed list; see README for how it was made.
BOILERPLATE = set("""
dilekçe dilekçemiz dilekçenin müvekkil müvekkilin müvekkile müvekkilim müvekkilimin müvekkilimiz şüpheli şüphelinin
sanık sanığın davacı davalı vekil vekili vekilimiz müdafi müdafii avukat hakim hakimlik hakimliği hakimliğine mahkeme
mahkemesi mahkemesine savcılık savcılığı başsavcılığı soruşturma kovuşturma dosya dosyası dosyanın karar kararı
kararın kararına kararının karara kararla kararda tarih tarihinde tarihli sayılı sayı esas madde maddesi maddesinde
hukuka aykırı aykırılık aykırılığı itiraz itirazımız itirazımızın talep talebi talebimiz açıklama açıklamalar
açıklamalar sonuç gereği gereğince gerektiği gerekmektedir hususu hususunda hususları bulunmaktadır bulunmamaktadır
olduğu olduğunu olacağı olmadığı olması olmasına edilmiştir edilmesi edilmesine verilmesi verilmiştir verilen
yapılan yapılmış yapılması görülecektir görülmektedir anlaşılmaktadır anlaşılacaktır incelendiğinde neticesinde
nedeniyle nedenle itibaren ilişkin yönelik ilgili ayrıca ancak ilk olarak son olarak bağlamda şekilde şekildeki
şeklindeki kapsamında kapsamında hakkında hakkındaki tarafından tarafına herhangi hiçbir bütün tümü ise ile için
gibi kadar daha sonra önce saygılarımızla vekaleten arz ederiz ederim kabulü kabulüne açıktır barizdir keza nitekim
kaldı şöyle işbu hasıl gerekliliği yukarıda verdiğimiz ışığında saygılarımla kanun kanunu kanunun kanunda yargıtay
yargıtayın daire dairesi genel kurulu kurul ceza hukuk görüşüne göre uyarınca durumunda durumu halinde hali somut
olay olayın olgu olgular olgusu açısından yönünden itibariyle aleyhine lehine tespit tespitinde dikkate alındığında
""".split())
BOILERPLATE_STEMS = {stem(w) for w in BOILERPLATE if len(w) >= 6}

STATUTE = re.compile(r"\b(TCK|CMK|HMK|TBK|TMK|İİK|TTK|İYUK|KVKK|AY)(?:'[a-zçğıöşü]{1,4})?\s*(?:md\.?|m\.|madde(?:si)?)?\s*(\d{1,3})(?:\.\s*madde|/|\b)")

def statutes(text: str) -> list[str]:
    """Statute articles cited in the text, as 'TCK 191' keys (law + article number)."""
    out = []
    for m in STATUTE.finditer(text):
        law = fold(m.group(1)).upper()
        out.append(f"{law} {int(m.group(2))}")
    # "Ceza Muhakemeleri Kanunu ... 100. Madde" style
    for m in re.finditer(r"Ceza Muhakeme(?:si|leri)? Kanunu.{0,60}?(\d{1,3})\.\s*[Mm]adde", text):
        out.append(f"CMK {int(m.group(1))}")
    for m in re.finditer(r"Türk Ceza Kanunu.{0,60}?(\d{1,3})\.\s*[Mm]adde", text):
        out.append(f"TCK {int(m.group(1))}")
    return list(dict.fromkeys(out))

def domain(stat: list[str]) -> str:
    laws = {s.split()[0] for s in stat}
    return "ceza" if laws & {"TCK", "CMK"} else "hukuk"

# ---------------------------------------------------------------- query writing
@dataclass
class Term:
    word: str          # surface form used in the query (most frequent form in the petition)
    stem: str
    tf: int            # times the stem occurs in the petition
    df: int = -1       # Yargıtay decisions containing the word (from the service), -1 = not looked up
    idf: float = 0.0
    score: float = 0.0

def candidate_terms(text: str, k: int = 20) -> list[Term]:
    """Candidate issue words, chosen on this computer: lowercase in the petition (names are capitalised, so
    they never qualify), 4+ letters, not petition boilerplate, not among the 2,000 commonest everyday words.
    Grouped by five-letter stem; ordered by how often the stem occurs."""
    forms: Counter = Counter(m.group(0) for m in WORD.finditer(text) if not m.group(0)[0].isupper())
    by_stem: dict[str, Counter] = {}
    for w, n in forms.items():
        if len(w) < 4 or lower_tr(w) in BOILERPLATE or stem(w) in BOILERPLATE_STEMS:
            continue
        r = COMMON.get(fold(w))
        if r is not None and r <= 2000:
            continue
        by_stem.setdefault(stem(w), Counter())[w] += n
    terms = []
    for s_, fs in by_stem.items():
        word = min(fs, key=lambda w: (-fs[w], len(w)))
        terms.append(Term(word, s_, sum(fs.values())))
    terms.sort(key=lambda t: (-t.tf, len(t.word), t.word))
    return terms[:k]

def weight_terms(terms: list[Term], df: dict[str, int], n_docs: int, min_df: int = 300) -> list[Term]:
    """tf-idf with the document frequency measured on Yargıtay's own collection. Words in fewer than
    `min_df` decisions are too specific to search with (AND queries with them come back empty), and words
    in more than a third of all decisions say nothing about the issue."""
    out = []
    for t in terms:
        t.df = df.get(t.word, 0)
        if t.df < min_df or t.df > n_docs / 3:
            continue
        t.idf = round(math.log(n_docs / t.df), 3)
        t.score = round((1 + math.log(t.tf)) * t.idf, 3)
        out.append(t)
    out.sort(key=lambda t: (-t.score, t.word))
    return out

SAFE_QUERY_WORD = re.compile(r"^[a-zçğıöşüâîû]{4,}$")

def safe_query(words: list[str], petition: str, public: str = "") -> str:
    """The only door out. Every word must be lowercase letters, at least 4 long, and appear as written in
    the masked petition or in `public` (official statute headings). Anything else raises, so a bug cannot
    leak a name or a number."""
    for w in words:
        pat = r"(?<![\wçğıöşü])" + re.escape(w) + r"(?![\wçğıöşü])"
        if not SAFE_QUERY_WORD.match(w) or not (re.search(pat, petition) or re.search(pat, public)):
            raise ValueError(f"refusing to send query word {w!r}")
    return " ".join(words)

# Which of the top 7 terms go together: every term appears in two or three queries, every pair at most once.
DESIGN = [(0, 1, 2), (0, 3, 4), (0, 5, 6), (1, 3, 5), (1, 4, 6), (2, 3, 6)]

def write_queries(terms: list[Term], petition: str) -> list[str]:
    """Short AND queries of three petition words each. Three words keeps recall (more and the service
    often finds nothing); the fixed design spreads the top seven words over six queries."""
    t = [x.word for x in terms]
    return [safe_query([t[i] for i in c], petition) for c in DESIGN if max(c) < len(t)]

HEADINGS_FILE = HERE / "data" / "headings.json"
HEADINGS = json.loads(HEADINGS_FILE.read_text(encoding="utf-8"))["laws"] if HEADINGS_FILE.exists() else {}
STOP_HEAD = {"veya", "ile", "için", "olan", "ve", "ya", "da", "de", "ait", "dair", "gibi", "madde", "maddeler"}

def heading_words(key: str) -> list[str]:
    law, art = key.split()
    h = (HEADINGS.get(law) or {}).get("headings", {}).get(art, "")
    return [w for w in (lower_tr(x) for x in WORD.findall(h)) if len(w) >= 4 and w not in STOP_HEAD]

def statute_queries(stat: list[str], df: dict[str, int], n_docs: int, petition: str = "") -> tuple[list[str], str]:
    """When the petition cites two articles of the same code, the argument is usually 'this act falls under
    article B, not A' (dealing vs personal use, theft vs fraud). Precedents on that line use the words of
    both article headings, not the petition's facts. Query: the heading word that only A has plus the one
    that only B has, each the one the petition itself uses most (same five-letter stem; boilerplate stems
    do not count), ties broken by how common the word is in decisions. Heading words are public text, so
    they may leave the computer."""
    ptf = Counter(stem(w) for w in WORD.findall(petition))
    use = lambda w: 0 if stem(w) in BOILERPLATE_STEMS else ptf.get(stem(w), 0)
    queries, public = [], []
    for i, a in enumerate(stat):
        for b in stat[i + 1:]:
            if a.split()[0] != b.split()[0]:
                continue
            wa, wb = heading_words(a), heading_words(b)
            public += wa + wb
            only_a = sorted({w for w in wa if w not in wb}, key=lambda w: (-use(w), -df.get(w, 0)))
            only_b = sorted({w for w in wb if w not in wa}, key=lambda w: (-use(w), -df.get(w, 0)))
            if only_a and only_b and use(only_a[0]) and use(only_b[0]):
                queries.append(f"{only_a[0]} {only_b[0]}")
    return queries, " ".join(public)

# ---------------------------------------------------------------- search (the only network part)
class Bedesten:
    """Thin wrapper over turk-hukuku-ictihat-mcp's Yargıtay client, with our slower pace and a request log."""
    def __init__(self, gap: float = GAP_SECONDS, log=print, cache: Path | None = CACHE):
        from turk_hukuku_ictihat import ortak, yargitay
        ortak.ARALIK = max(ortak.ARALIK, gap)
        self.y, self.ortak, self.log, self.sent = yargitay, ortak, log, []
        # Public data only (word counts, decision texts): cached so a second run asks the court's service again
        # for nothing it already answered. Searches are not cached: they carry the petition's words.
        self.cache = cache
        if cache:
            (cache / "texts").mkdir(parents=True, exist_ok=True)
        self.counts = json.loads((cache / "counts.json").read_text()) if cache and (cache / "counts.json").exists() else {}

    def search(self, query: str, chamber: str | None = None, pages: int = 1) -> list[dict]:
        """The service returns 10 results a page, whatever page size we ask for."""
        out, total = [], 0
        for page in range(1, pages + 1):
            body = {"phrase": self.ortak.ve_sorgusu(query), "itemTypeList": ["YARGITAYKARARI"],
                    "pageSize": 10, "pageNumber": page}
            if chamber:
                body["birimAdi"] = chamber
            self.sent.append({"kind": "search", "query": query, "chamber": chamber, "page": page})
            d = self.y._post("searchDocuments", body, sayfali=True)
            total = d.get("total", 0)
            rows = d.get("emsalKararList") or []
            for k in rows:
                out.append({"id": str(k["documentId"]), "chamber": k.get("birimAdi") or "", "esas": k.get("esasNo") or "",
                            "karar": k.get("kararNo") or "", "date": k.get("kararTarihiStr") or ""})
            if len(out) >= total or not rows:
                break
        self.log(f"  search [{chamber or 'all chambers'}] {query!r}: {total} hits, kept {len(out)}")
        return out

    def count(self, word: str) -> int:
        """How many Yargıtay decisions contain this one word (one request, one result row)."""
        if word in self.counts:
            return self.counts[word]
        self.sent.append({"kind": "count", "query": word, "chamber": None})
        d = self.y._post("searchDocuments", {"phrase": self.ortak.ve_sorgusu(word), "itemTypeList": ["YARGITAYKARARI"],
                                             "pageSize": 1, "pageNumber": 1}, sayfali=True)
        self.counts[word] = int(d.get("total") or 0)
        if self.cache:
            (self.cache / "counts.json").write_text(json.dumps(self.counts, ensure_ascii=False))
        return self.counts[word]

    def text(self, doc_id: str) -> str:
        f = self.cache / "texts" / f"{doc_id}.txt" if self.cache else None
        if f and f.exists():
            return f.read_text(encoding="utf-8")
        self.sent.append({"kind": "fetch", "id": doc_id})
        t = self.y.karar(doc_id).get("metin") or ""
        if f and t:
            f.write_text(t, encoding="utf-8")
        return t

# ---------------------------------------------------------------- ranking
def tokens(s: str) -> list[str]:
    return [stem(w) for w in WORD.findall(s) if len(w) >= 3 and lower_tr(w) not in BOILERPLATE]

def paragraphs(text: str, size: int = 90) -> list[str]:
    """Decision text cut into ~90-word windows on paragraph breaks (decisions have long paragraphs)."""
    out = []
    for p in re.split(r"\n\s*\n|\n(?=[A-ZÇĞİÖŞÜ0-9])", text):
        w = p.split()
        for i in range(0, len(w), size):
            chunk = " ".join(w[i:i + size])
            if len(chunk) > 80:
                out.append(chunk)
    return out or [text[:800]]

class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.2, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avg = sum(map(len, docs)) / max(1, len(docs))
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.tf = [Counter(d) for d in docs]

    def score(self, q: Counter, i: int) -> float:
        tf, dl, s = self.tf[i], len(self.docs[i]), 0.0
        for t, qn in q.items():
            f = tf.get(t)
            if f:
                s += qn * self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg))
        return s

def outcome(text: str) -> str:
    t = text[-1500:].upper()
    if "BOZULMASINA" in t: return "bozma"
    if "ONANMASINA" in t: return "onama"
    if "DÜZELTİLEREK" in t: return "düzelterek onama"
    if "REDDİNE" in t: return "ret"
    return ""

def verify(hit: dict, text: str) -> bool:
    """The esas and karar numbers we will show must both appear in the official text we fetched."""
    def present(no: str) -> bool:
        if not no or "/" not in no:
            return False
        y, n = no.split("/", 1)
        # older General Assembly numbers carry the chamber: '2012/10-1335 E.'
        return re.search(rf"(?<!\d){re.escape(y)}\s*/\s*(?:\d{{1,2}}\s*-\s*)?{re.escape(n)}(?!\d)", text) is not None
    return present(hit["esas"]) and present(hit["karar"])

@dataclass
class Result:
    id: str
    citation: str
    url: str
    chamber: str
    esas: str
    karar: str
    date: str
    queries: list = field(default_factory=list)
    rrf: float = 0.0
    bm25: float = 0.0
    statute_overlap: float = 0.0
    score: float = 0.0
    verified: bool = False
    outcome: str = ""
    quote: str = ""

def citation(h: dict) -> str:
    ch = h["chamber"]
    ch = ch if ch.lower().startswith("yargıtay") else f"Yargıtay {ch}"
    return f"{ch}, E. {h['esas']}, K. {h['karar']}, T. {h['date']}"

def run(petition_path: Path, out: Path, top: int = 10, fetch: int = 30, gold: list[str] | None = None,
        top_gk: int = 5, fetch_gk: int = 80,
        extra_queries: list[str] | None = None, gap: float = GAP_SECONDS, log=print) -> dict:
    raw = read_petition(petition_path)
    text = unmask(raw)
    stat = statutes(text)
    dom = domain(stat)
    cand = candidate_terms(text)
    gk = "Ceza Genel Kurulu" if dom == "ceza" else "Hukuk Genel Kurulu"
    log(f"statutes: {stat}  domain: {dom}")
    log("candidate words: " + ", ".join(f"{t.word}({t.tf})" for t in cand))

    api = Bedesten(gap=gap, log=log)
    n_docs = api.count(safe_query(["karar"], "karar"))        # size of the collection, for idf
    df = {t.word: api.count(safe_query([t.word], text)) for t in cand}
    terms = weight_terms(cand, df, n_docs)[:12]
    log(f"collection: {n_docs} decisions; key terms: " + ", ".join(f"{t.word}(df {t.df}, {t.score})" for t in terms))
    queries = write_queries(terms, text)
    words = sorted({w for k in stat for w in heading_words(k)})
    public = " ".join(words)
    for w in words:
        if w not in df:
            df[w] = api.count(safe_query([w], text, public))
    sq, _ = statute_queries(stat, df, n_docs, text)
    queries += [safe_query(q.split(), text, public) for q in sq]
    log(f"statute queries: {sq}")
    for q in extra_queries or []:
        queries.append(safe_query(q.split(), text))
    runs: list[tuple[str, str | None, list[dict]]] = []
    for q in queries:
        for ch, pages in ((None, 1), (gk, GK_PAGES)):
            try:
                runs.append((q, ch, api.search(q, ch, pages)))
            except Exception as e:                      # a stop from the site ends the search politely
                log(f"  search failed ({e}); stopping searches"); break
    # reciprocal rank fusion over all result lists (Cormack et al., SIGIR 2009), k = 60
    pool: dict[str, dict] = {}
    for q, ch, hits in runs:
        for r, h in enumerate(hits, 1):
            p = pool.setdefault(h["id"], {**h, "rrf": 0.0, "queries": []})
            p["rrf"] += 1 / (60 + r)
            p["queries"].append(f"{q} [{ch or 'all'}]")
    baseline = [h["id"] for h in runs[0][2]] if runs else []        # B1: the service's own order for query 1
    cands = sorted(pool.values(), key=lambda h: -h["rrf"])
    gold_ids = [g.split(":")[-1] for g in (gold or [])]
    # Two tracks, because lawyers want both: General Assembly decisions that set the principle on the legal
    # issue, and chamber decisions with similar facts. Each track gets its own fetch budget.
    is_gk = lambda h: "genel kurul" in lower_tr(h["chamber"])
    gk_c = [h for h in cands if is_gk(h)][:fetch_gk]
    ch_c = [h for h in cands if not is_gk(h)][:fetch]
    to_fetch = gk_c + ch_c
    # the baseline's top 10 too, so the blind grading sheet can quote them the same way (blind.py)
    have = {h["id"] for h in to_fetch}
    to_fetch += [pool[i] for i in baseline[:10] if i not in have]
    log(f"pool: {len(pool)} decisions from {len(runs)} searches; fetching {len(gk_c)} {gk} + {len(ch_c)} chamber")

    texts: dict[str, str] = {}
    for h in to_fetch:
        try:
            texts[h["id"]] = api.text(h["id"])
        except Exception as e:
            log(f"  fetch {h['id']} failed ({e}); stopping fetches"); break

    # re-rank on this computer
    ids = [i for i in texts if texts[i]]
    win_ids, wins = [], []
    for i in ids:
        for p in paragraphs(texts[i]):
            win_ids.append(i); wins.append(p)
    bm = BM25([tokens(p) for p in wins])
    q = Counter(tokens(text))
    best: dict[str, tuple[float, str]] = {}
    for j, i in enumerate(win_ids):
        s = bm.score(q, j)
        if s > best.get(i, (-1, ""))[0]:
            best[i] = (s, wins[j])
    top_bm = max([s for s, _ in best.values()] or [1]) or 1
    results = []
    for h in to_fetch:
        i = h["id"]
        if i not in best:
            continue
        t = texts[i]
        dstat = set(statutes(t))
        overlap = len(dstat & set(stat)) / len(stat) if stat else 0.0
        bm_n = best[i][0] / top_bm
        r = Result(id=i, citation=citation(h), url=f"https://mevzuat.adalet.gov.tr/ictihat/{i}", chamber=h["chamber"],
                   esas=h["esas"], karar=h["karar"], date=h["date"], queries=h["queries"], rrf=round(h["rrf"], 4),
                   bm25=round(bm_n, 3), statute_overlap=round(overlap, 3),
                   score=round(bm_n + 0.25 * overlap, 3), verified=verify(h, t), outcome=outcome(t),
                   quote=best[i][1][:700])
        results.append(r)
    results.sort(key=lambda r: -r.score)
    gk_ranked = [r for r in results if r.verified and "genel kurul" in lower_tr(r.chamber)]
    ch_ranked = [r for r in results if r.verified and "genel kurul" not in lower_tr(r.chamber)]
    shown = gk_ranked[:top_gk] + ch_ranked[:top]

    def rank_in(lst: list[str], g: str) -> int | None:
        return lst.index(g) + 1 if g in lst else None
    fused = [h["id"] for h in cands]
    gold_report = {g: {"in_pool": g in pool, "fetched": g in texts, "rank_baseline_query1": rank_in(baseline, g),
                       "rank_fusion_only": rank_in(fused, g),
                       "rank_emsal_genel_kurul": rank_in([r.id for r in gk_ranked], g),
                       "rank_emsal_chambers": rank_in([r.id for r in ch_ranked], g)} for g in gold_ids}

    report = {
        "petition": petition_path.name, "when": time.strftime("%Y-%m-%d %H:%M"), "statutes": stat, "domain": dom,
        "collection_size": n_docs, "candidates": [asdict(t) for t in cand], "terms": [asdict(t) for t in terms], "queries": queries, "requests": api.sent,
        "pool_size": len(pool), "fetched": len(texts), "unverified_dropped": sum(not r.verified for r in results),
        "baseline_query1_top10": [citation(h) for h in (runs[0][2][:10] if runs else [])],
        "baseline_query1_ids": baseline[:10],
        "genel_kurul": [asdict(r) for r in gk_ranked[:top_gk]], "chambers": [asdict(r) for r in ch_ranked[:top]],
        "results": [asdict(r) for r in shown], "all_ranked": [asdict(r) for r in results], "gold": gold_report,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "queries.txt").write_text(
        "Everything this run sent to bedesten.adalet.gov.tr, in order. Word counts and decision texts already in\n"
        "the local cache (~/.cache/katip-emsal) were sent on an earlier run and are not repeated here.\n\n" +
        "\n".join(f"{x['kind']}: {x.get('query') or x.get('id')}" + (f"  [{x['chamber']}]" if x.get('chamber') else "")
                  + (f"  page {x['page']}" if x.get('page', 1) > 1 else "")
                  for x in api.sent) + "\n", encoding="utf-8")
    with (out / "grading.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "decision", "link", "quote", "relevance (0 not, 1 partly, 2 on point)",
                    "would you cite it? (yes/no)", "supports or against the petition", "notes"])
        for k, r in enumerate(shown, 1):
            w.writerow([k, r.citation, r.url, r.quote[:400], "", "", "", ""])
    (out / "report.html").write_text(render_html(report), encoding="utf-8")
    return report

# ---------------------------------------------------------------- report
def render_html(rep: dict) -> str:
    e = html.escape
    def items(lst):
        rows = []
        for k, r in enumerate(lst, 1):
            rows.append(f"""<li><p class=c><b>{k}. <a href="{e(r['url'])}">{e(r['citation'])}</a></b>
<span class=tag>{e(r['outcome'] or 'sonuç okunamadı')}</span> <span class=tag>numaralar resmi metinle doğrulandı</span></p>
<blockquote>{e(r['quote'])}</blockquote>
<p class=m>Puan {r['score']} · metin benzerliği {r['bm25']} · ortak kanun maddesi {r['statute_overlap']} · {len(r['queries'])} aramada çıktı</p></li>""")
        return "".join(rows) or "<li>Sonuç bulunamadı.</li>"
    q = "".join(f"<li><code>{e(x)}</code></li>" for x in rep["queries"])
    return f"""<!doctype html><html lang=tr><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Katip Emsal sonuçları</title>
<style>:root{{--bg:#fff;--fg:#1d1d1b;--mute:#666;--line:#ddd;--acc:#3a6e00}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151515;--fg:#eee;--mute:#aaa;--line:#333;--acc:#b5e06b}}}}
body{{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;max-width:820px;margin:auto;padding:16px}}
a{{color:var(--acc)}} blockquote{{border-left:3px solid var(--line);margin:8px 0;padding:4px 12px;color:var(--fg)}}
.m,.note{{color:var(--mute);font-size:14px}} .tag{{font-size:12px;border:1px solid var(--line);border-radius:10px;padding:1px 8px;margin-left:6px}}
ol{{padding-left:0;list-style:none}} li{{margin:0 0 22px}} code{{font-size:14px}}</style>
<h1>Katip Emsal: dilekçeye uygun Yargıtay kararları</h1>
<p class=note>Dilekçe: {e(rep['petition'])} · {e(rep['when'])} · Atıf yapılan maddeler: {e(', '.join(rep['statutes']) or 'yok')}</p>
<p>Aşağıdaki kararlar resmi kaynaktan (mevzuat.adalet.gov.tr) alındı. Her kararın esas ve karar numarası resmi metinde
geçiyor; geçmeyen {rep['unverified_dropped']} karar listeden çıkarıldı. Alıntılar kararın kendi metninden, kelimesi kelimesine.
Bu bir arama aracıdır, hukuki görüş değildir: kararı okumadan atıf yapmayın.</p>
<h2>İlke kararları: Genel Kurul</h2>
<p class=note>Hukuki meseleyi (atıf yapılan maddeler arasındaki ayrımı) tartışan Genel Kurul kararları.</p>
<ol>{items(rep['genel_kurul'])}</ol>
<h2>Benzer olaylı daire kararları</h2>
<p class=note>Dilekçedeki olgulara en çok benzeyen daire kararları.</p>
<ol>{items(rep['chambers'])}</ol>
<h2>Bilgisayarınızdan çıkan aramalar</h2>
<p class=note>Yalnızca bu kelimeler gönderildi (maskelenmiş dilekçeden, küçük harfli kelimeler; isim ve rakam gönderilmez).
Tam liste: queries.txt</p><ul>{q}</ul>
</html>"""

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("petition", type=Path, help="masked petition (.udf or .txt)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--fetch", type=int, default=30, help="chamber decisions to fetch in full for re-ranking")
    ap.add_argument("--fetch-gk", type=int, default=80, help="General Assembly decisions to fetch in full")
    ap.add_argument("--gold", action="append", help="a known-good decision id (yargitay:<documentId>) to score")
    ap.add_argument("--query", action="append", help="an extra query written by the lawyer (lowercase words)")
    ap.add_argument("--gap", type=float, default=GAP_SECONDS)
    a = ap.parse_args(argv)
    if MASK not in read_petition(a.petition) and "[" not in read_petition(a.petition):
        print("This petition has no masked parts. Mask it with Katip first.", file=sys.stderr)
        return 2
    rep = run(a.petition, a.out, a.top, a.fetch, a.gold, fetch_gk=a.fetch_gk, extra_queries=a.query, gap=a.gap)
    print(f"\n{len(rep['results'])} decisions -> {a.out / 'report.html'}")
    if rep["gold"]:
        print("gold:", json.dumps(rep["gold"], ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
