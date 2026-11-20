"""Katip Emsal inside Kalkan: find Yargıtay decisions for a masked document, and collect the lawyer's grades.

Two rules make this safe to run next to client documents:

* **Only short keyword queries leave the computer.** A query word must be 3+ lowercase letters, no digits,
  and must not be (part of) any real value Katip masked for this matter. The document, its masked text and
  any quote from it never leave. Every request is logged in ~/.katip/emsal/requests.log.
* **Nothing unverified is shown.** A decision is listed only if its esas and karar numbers appear in the
  official text fetched from the court's service.

Source: Bedesten (bedesten.adalet.gov.tr), the Ministry of Justice service behind mevzuat.adalet.gov.tr,
asked politely: one request at a time, at least 2.5 s apart, a User-Agent that names Katip, and a hard
stop on HTTP 429/403, a CAPTCHA or a login page. Decision texts are public and cached in ~/.katip/emsal/texts.

Grades (geri_bildirim) are stored only on this computer, in ~/.katip/emsal/grades.jsonl, and hold only
public data: the decision id, the query words, the grade and the lawyer's note. They become training and
evaluation data only if the lawyer sends that file (see `katip-kalkan feedback`).

Ranking is the lab version (lab/emsal/emsal.py, PR #26): reciprocal rank fusion over the result lists,
then BM25 on five-letter stems against the masked document, plus statute overlap. It was tuned on one
petition; treat the order as a starting point, not a verdict.
"""
from __future__ import annotations

import base64, gzip, html, json, math, os, re, threading, time, urllib.error, urllib.request, uuid
from collections import Counter
from pathlib import Path

from . import __version__

API = "https://bedesten.adalet.gov.tr/emsal-karar"
PAGE = "https://mevzuat.adalet.gov.tr/ictihat"
UA = f"katip-kalkan/{__version__} (+https://github.com/fikrifirat/katip; precedent search for lawyers)"
GAP = float(os.environ.get("KATIP_EMSAL_GAP", "2.5"))
HERE = Path(__file__).resolve().parent


def home() -> Path:
    p = Path(os.environ.get("KATIP_HOME", Path.home() / ".katip")) / "emsal"
    (p / "texts").mkdir(parents=True, exist_ok=True)
    return p


class Stopped(RuntimeError):
    """The court's service asked us to stop (429/403/CAPTCHA). We stop for this session."""


# ------------------------------------------------------------------ polite client
_lock = threading.Lock()
_last = 0.0
_stopped: str | None = None


def _post(endpoint: str, data: dict) -> dict:
    global _last, _stopped
    if _stopped:
        raise Stopped(_stopped)
    body = json.dumps({"data": data, **({"paging": True} if endpoint == "searchDocuments" else {})}).encode()
    req = urllib.request.Request(f"{API}/{endpoint}", data=body, method="POST", headers={
        "Content-Type": "application/json; charset=UTF-8", "Accept": "application/json", "User-Agent": UA})
    with _lock:
        wait = _last + GAP - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                _stopped = f"the court's service answered HTTP {e.code}; Katip stops asking for this session"
                raise Stopped(_stopped) from None
            raise
        finally:
            _last = time.monotonic()
    if raw.lstrip().startswith("<") or "captcha" in raw[:2000].lower():
        _stopped = "the court's service returned a web page (CAPTCHA or login) instead of data; Katip stops asking"
        raise Stopped(_stopped)
    d = json.loads(raw)
    meta = d.get("metadata") or {}
    if meta.get("FMTY") == "ERROR":
        raise ValueError(meta.get("FMTE") or "Bedesten error")
    return d.get("data") or {}


def _log(endpoint: str, data: dict) -> None:
    line = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "endpoint": endpoint,
            **{k: data[k] for k in ("phrase", "birimAdi", "pageNumber", "documentId") if k in data}}
    with (home() / "requests.log").open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def search(words: list[str], chamber: str | None = None, page: int = 1) -> tuple[int, list[dict]]:
    body = {"phrase": " ".join("+" + w for w in words), "itemTypeList": ["YARGITAYKARARI"],
            "pageSize": 10, "pageNumber": page}
    if chamber:
        body["birimAdi"] = chamber
    _log("searchDocuments", body)            # logged before it is sent, so the log shows every attempt
    d = _post("searchDocuments", body)
    rows = [{"id": str(k["documentId"]), "chamber": k.get("birimAdi") or "", "esas": k.get("esasNo") or "",
             "karar": k.get("kararNo") or "", "date": k.get("kararTarihiStr") or ""}
            for k in d.get("emsalKararList") or []]
    return int(d.get("total") or 0), rows


def _to_text(raw_html: str) -> str:
    s = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", "", raw_html)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|tr|li|h[1-6])>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"\n[ \t]+", "\n", s)).strip()


def decision_text(doc_id: str) -> str:
    if not re.fullmatch(r"\d{1,15}", doc_id):
        raise ValueError("decision id must be digits")
    f = home() / "texts" / f"{doc_id}.txt.gz"
    if f.exists():
        return gzip.decompress(f.read_bytes()).decode("utf-8")
    _log("getDocumentContent", {"documentId": doc_id})
    d = _post("getDocumentContent", {"documentId": doc_id})
    c = d.get("content")
    if not c or "html" not in (d.get("mimeType") or "text/html"):
        return ""
    t = _to_text(base64.b64decode(c).decode("utf-8", "replace"))
    f.write_bytes(gzip.compress(t.encode("utf-8")))
    return t


# ------------------------------------------------------------------ the privacy door
FOLD = str.maketrans("çğıöşüâîûÇĞIİÖŞÜÂÎÛ", "cgiosuaiuCGIIOSUAIU")
WORD = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]+")
SAFE = re.compile(r"^[a-zçğıöşüâîû]{3,40}$")


def fold(w: str) -> str:
    return w.replace("I", "ı").replace("İ", "i").lower().translate(FOLD)


def secret_words(matter: str) -> set[str]:
    """Every word of every real value Katip has masked for this matter (names, addresses, ...), folded."""
    try:
        from . import vault
        v = vault.open_vault(matter)
        return {fold(w) for val in v.values.values() for w in WORD.findall(val) if len(w) >= 3}
    except Exception:
        return set()


def safe_words(query: str, secrets: set[str]) -> list[str]:
    """The only door out. Splits a query into words and refuses the whole query if any word could identify
    someone: capitals, digits or punctuation other than spaces, or a word of a value masked in this matter."""
    q = query.strip()
    if not q or re.search(r"[^a-zçğıöşüâîû\s]", q):
        raise ValueError(f"query must be lowercase words only (no names, capitals, digits or signs): {q[:40]!r}")
    words = q.split()
    if not 1 <= len(words) <= 5:
        raise ValueError("a query has 1 to 5 words")
    for w in words:
        if not SAFE.match(w):
            raise ValueError(f"word too short or not plain letters: {w!r}")
        if fold(w) in secrets:
            raise ValueError("a query word matches a value Katip masked in this matter; it was not sent")
    return words


# ------------------------------------------------------------------ statutes (for the contrast query)
STATUTE = re.compile(r"\b(TCK|CMK|HMK|TBK|TMK|İİK|TTK|İYUK)(?:'[a-zçğıöşü]{1,4})?\s*(?:md\.?|m\.|madde(?:si)?)?\s*(\d{1,3})(?:\.\s*madde|/|\b)")
LAWNO = {"TCK": "5237", "CMK": "5271", "HMK": "6100", "TBK": "6098", "TMK": "4721", "İİK": "2004", "TTK": "6102", "İYUK": "2577"}


def statutes(text: str) -> list[str]:
    out = [f"{m.group(1)} {int(m.group(2))}" for m in STATUTE.finditer(text)]
    for law, rx in (("CMK", r"Ceza Muhakeme(?:si|leri)? Kanunu"), ("TCK", r"Türk Ceza Kanunu")):
        out += [f"{law} {int(m.group(1))}" for m in re.finditer(rx + r".{0,60}?(\d{1,3})\.\s*[Mm]adde", text)]
    return list(dict.fromkeys(out))


_HEADS: dict[str, dict[str, str]] | None = None


def heading(key: str) -> str:
    """Article heading from Katip Cite's statute index: it sits at the end of the previous article's text."""
    global _HEADS
    if _HEADS is None:
        _HEADS = {}
        try:
            idx = json.load(gzip.open(HERE / "data" / "statutes.json.gz", "rt", encoding="utf-8"))["laws"]
            for law, no in LAWNO.items():
                best = max((l for k, l in idx.items() if k.split("-")[0] == no),
                           key=lambda l: len((l.get("arts") or {}).get("madde") or {}), default=None)
                arts = ((best or {}).get("arts") or {}).get("madde") or {}
                for n, a in arts.items():
                    if n.isdigit():
                        t = re.sub(r"\s*\[\d+\]", "", a.get("t", "")).strip()
                        m = re.search(r"(?:[.:;)]|\b[a-zçğıöşü]{1,2}\.)\s+([^:;)]{3,160}?)$", t)
                        if m:
                            _HEADS.setdefault(law, {})[str(int(n) + 1)] = re.sub(r"^.*\b(BÖLÜM|KISIM|KİTAP)\s+", "", m.group(1))
        except (OSError, ValueError, KeyError):
            pass
    law, art = key.split()
    return (_HEADS.get(law) or {}).get(art, "")


def contrast_queries(stat: list[str], text: str) -> list[str]:
    """Two cited articles of one code ('TCK 188' and 'TCK 191') usually mean the argument is 'B, not A'.
    Decisions on that line use the heading words of both, so: the heading word only A has plus the one only
    B has, each the one the document uses most. Heading words are public text."""
    tf = Counter(fold(w)[:5] for w in WORD.findall(text))
    stop = {"veya", "ile", "için", "olan", "dair", "gibi", "madde", "kabul", "etmek", "almak"}
    words = lambda k: [w for w in (x.replace("I", "ı").replace("İ", "i").lower() for x in WORD.findall(heading(k)))
                       if len(w) >= 4 and w not in stop]
    out = []
    for i, a in enumerate(stat):
        for b in stat[i + 1:]:
            if a.split()[0] != b.split()[0]:
                continue
            wa, wb = words(a), words(b)
            oa = sorted({w for w in wa if w not in wb}, key=lambda w: -tf[fold(w)[:5]])
            ob = sorted({w for w in wb if w not in wa}, key=lambda w: -tf[fold(w)[:5]])
            if oa and ob and tf[fold(oa[0])[:5]] and tf[fold(ob[0])[:5]]:
                out.append(f"{oa[0]} {ob[0]}")
    return out[:2]


# ------------------------------------------------------------------ ranking
BOILER = set("""müvekkil müvekkilin şüpheli sanık davacı davalı vekil vekili müdafi avukat hakim mahkeme mahkemesi
savcılık soruşturma kovuşturma dosya karar kararı kararın tarih tarihinde sayılı esas madde maddesi hukuka aykırı
itiraz talep açıklama sonuç gereği hususu olduğu olduğunu olması edilmiştir edilmesi verilmesi yapılan ilişkin
yönelik ilgili ayrıca ancak şekilde kapsamında hakkında tarafından herhangi hiçbir için gibi kadar daha sonra önce
yargıtay daire dairesi genel kurulu ceza hukuk göre uyarınca somut olay""".split())


def stem(w: str) -> str:
    return fold(w)[:5]


def tokens(s: str) -> list[str]:
    return [stem(w) for w in WORD.findall(s) if len(w) >= 3 and w.lower() not in BOILER]


def windows(text: str, size: int = 90) -> list[str]:
    out = []
    for p in re.split(r"\n\s*\n|\n(?=[A-ZÇĞİÖŞÜ0-9])", text):
        w = p.split()
        out += [" ".join(w[i:i + size]) for i in range(0, len(w), size) if len(" ".join(w[i:i + size])) > 80]
    return out or [text[:800]]


def bm25(docs: list[list[str]], q: Counter, k1: float = 1.2, b: float = 0.75) -> list[float]:
    n, avg = len(docs), sum(map(len, docs)) / max(1, len(docs))
    df = Counter(t for d in docs for t in set(d))
    idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    out = []
    for d in docs:
        tf, s = Counter(d), 0.0
        for t, qn in q.items():
            f = tf.get(t)
            if f:
                s += qn * idf[t] * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avg))
        out.append(s)
    return out


def verified(h: dict, text: str) -> bool:
    def present(no: str) -> bool:
        if "/" not in no:
            return False
        y, n = no.split("/", 1)
        return re.search(rf"(?<!\d){re.escape(y)}\s*/\s*(?:\d{{1,2}}\s*-\s*)?{re.escape(n)}(?!\d)", text) is not None
    return present(h["esas"]) and present(h["karar"])


def outcome(text: str) -> str:
    t = text[-1500:].upper()
    for key, label in (("BOZULMASINA", "bozma"), ("DÜZELTİLEREK", "düzelterek onama"), ("ONANMASINA", "onama"),
                       ("REDDİNE", "ret")):
        if key in t:
            return label
    return ""


def citation(h: dict) -> str:
    ch = h["chamber"] if h["chamber"].lower().startswith("yargıtay") else f"Yargıtay {h['chamber']}"
    return f"{ch}, E. {h['esas']}, K. {h['karar']}, T. {h['date']}"


# ------------------------------------------------------------------ the tool
def find(queries: list[str], matter: str = "default", reference: str = "", domain: str | None = None,
         limit: int = 8, fetch: int = 8) -> dict:
    """queries: 1-5 short lowercase keyword queries (written by Claude from the masked text, or by Katip).
    reference: masked text to rank against (never sent anywhere). domain: 'ceza' or 'hukuk' adds a pass
    over that General Assembly."""
    if os.environ.get("KATIP_EMSAL_ONLINE", "1").strip().lower() in ("0", "false", "no", "off"):
        raise PermissionError("Yargıtay kararı arama Katip ayarlarında kapalı (precedent_search); açılırsa yalnızca "
                              "anahtar kelimeler gönderilir. · Precedent search is turned off in Katip's settings.")
    secrets = secret_words(matter)
    stat = statutes(reference) if reference else []
    qs = list(dict.fromkeys([q for q in queries if q.strip()] + contrast_queries(stat, reference)))[:6]
    checked = [safe_words(q, secrets) for q in qs]           # raises before anything is sent
    domain = domain or ("ceza" if any(s.split()[0] in ("TCK", "CMK") for s in stat) else None)
    gk = {"ceza": "Ceza Genel Kurulu", "hukuk": "Hukuk Genel Kurulu"}.get(domain or "")
    pool: dict[str, dict] = {}
    totals, stopped = [], None
    try:
        for words in checked:
            for ch in (None, gk) if gk else (None,):
                total, rows = search(words, ch)
                totals.append({"query": " ".join(words), "chamber": ch or "tüm daireler", "hits": total})
                for r, h in enumerate(rows, 1):
                    p = pool.setdefault(h["id"], {**h, "rrf": 0.0, "queries": []})
                    p["rrf"] += 1 / (60 + r)
                    p["queries"].append(" ".join(words))
    except Stopped as e:
        stopped = str(e)
    cands = sorted(pool.values(), key=lambda h: -h["rrf"])
    gk_c = [h for h in cands if "genel kurul" in h["chamber"].lower()][: fetch // 2]
    to_fetch = gk_c + [h for h in cands if h not in gk_c][: fetch - len(gk_c)]
    texts = {}
    for h in to_fetch:
        if stopped:
            break
        try:
            texts[h["id"]] = decision_text(h["id"])
        except Stopped as e:
            stopped = str(e)
    ref = reference or " ".join(qs)
    q = Counter(tokens(ref))
    ranked = []
    for h in to_fetch:
        t = texts.get(h["id"]) or ""
        if not t or not verified(h, t):
            continue
        ws = windows(t)
        scores = bm25([tokens(w) for w in ws], q)
        j = max(range(len(ws)), key=lambda i: scores[i])
        overlap = len(set(statutes(t)) & set(stat)) / len(stat) if stat else 0.0
        ranked.append({**h, "best": scores[j], "quote": ws[j][:500], "overlap": overlap, "outcome": outcome(t)})
    top = max([r["best"] for r in ranked] or [1]) or 1
    for r in ranked:
        r["score"] = round(r["best"] / top + 0.25 * r["overlap"], 3)
    ranked.sort(key=lambda r: -r["score"])
    run_id = uuid.uuid4().hex[:10]
    results = []
    for k, r in enumerate(ranked[:limit], 1):
        results.append({"result_id": f"{run_id}-{k}", "decision": citation(r),
                        "general_assembly": "genel kurul" in r["chamber"].lower(),
                        "link": f"{PAGE}/{r['id']}", "outcome": r["outcome"], "quote": r["quote"],
                        "score": r["score"], "found_by": sorted(set(r["queries"]))})
    with (home() / "runs.jsonl").open("a", encoding="utf-8") as f:   # public data only: for grading later
        f.write(json.dumps({"run_id": run_id, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "queries": qs,
                            "statutes": stat, "results": [{**x, "decision_id": x["link"].rsplit("/", 1)[1]}
                                                          for x in results]}, ensure_ascii=False) + "\n")
    out = {"run_id": run_id, "results": results, "queries_sent": totals, "statutes_in_document": stat,
           "checked": len(texts), "dropped_unverified": len([h for h in to_fetch if texts.get(h["id"])]) - len(ranked),
           "note": ("Only the queries in queries_sent left this computer. Every decision's esas/karar numbers were "
                    "found in the official text. The quote is from the decision, word for word. Read the decision "
                    "before citing it. Ask the lawyer to grade the ones they read (geri_bildirim): grades stay on "
                    "this computer and make the next search better.")}
    if stopped:
        out["stopped"] = stopped
    return out


GRADES = {0: "işe yaramaz", 1: "kısmen", 2: "tam isabet"}


def grade(result_id: str, relevance: int, would_cite: bool | None = None, note: str = "", matter: str = "default") -> dict:
    """Store the lawyer's grade for one result, on this computer only."""
    if relevance not in GRADES:
        raise ValueError("relevance must be 0, 1 or 2")
    run_id = result_id.rsplit("-", 1)[0]
    found = None
    p = home() / "runs.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["run_id"] == run_id:
                found = next((x for x in r["results"] if x["result_id"] == result_id), None)
                queries = r["queries"]
    if not found:
        raise ValueError("no such result_id on this computer; run emsal_ara first")
    if re.search(r"\d{5,}", note or "") or {fold(w) for w in WORD.findall(note or "") if len(w) >= 3} & secret_words(matter):
        raise ValueError("the note holds an ID number or a value Katip masked; describe why the decision fits, without client details")
    rec = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "result_id": result_id, "decision_id": found["decision_id"],
           "decision": found["decision"], "queries": queries, "rank": int(result_id.rsplit("-", 1)[1]),
           "relevance": relevance, "would_cite": would_cite, "note": (note or "")[:500]}
    with (home() / "grades.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    n = sum(1 for _ in (home() / "grades.jsonl").open(encoding="utf-8"))
    return {"saved": True, "grade": GRADES[relevance], "grades_on_this_computer": n,
            "where": "~/.katip/emsal/grades.jsonl (only public decision ids, query words and your note)"}


def feedback(export: str | None = None) -> dict:
    """Summary of the grades on this computer; with export, write them (and the runs they grade) to one
    JSON file the lawyer can read and then send to Katip by e-mail. Nothing is uploaded automatically."""
    h = home()
    grades = [json.loads(l) for l in (h / "grades.jsonl").read_text(encoding="utf-8").splitlines()] \
        if (h / "grades.jsonl").exists() else []
    by_rank: dict[int, list[int]] = {}
    for g in grades:
        by_rank.setdefault(g["rank"], []).append(g["relevance"])
    out = {"grades": len(grades), "decisions": len({g["decision_id"] for g in grades}),
           "mean_relevance": round(sum(g["relevance"] for g in grades) / len(grades), 2) if grades else None,
           "on_point": sum(g["relevance"] == 2 for g in grades),
           "mean_by_rank": {k: round(sum(v) / len(v), 2) for k, v in sorted(by_rank.items())}}
    if export:
        runs_wanted = {g["result_id"].rsplit("-", 1)[0] for g in grades}
        runs = [json.loads(l) for l in (h / "runs.jsonl").read_text(encoding="utf-8").splitlines()] \
            if (h / "runs.jsonl").exists() else []
        bundle = {"format": "katip-emsal-feedback/1", "katip_version": __version__, "summary": out,
                  "grades": grades, "runs": [r for r in runs if r["run_id"] in runs_wanted],
                  "contains": "public decision ids and texts' quotes, query words, grades, notes; no document text"}
        Path(export).expanduser().write_text(json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")
        out["exported_to"] = str(Path(export).expanduser())
    return out
