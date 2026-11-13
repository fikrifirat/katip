"""Collect public Turkish court decisions for the legal study (lab/legal/DESIGN.md, section 3.1).

  pip install turk-hukuku-ictihat-mcp==0.5.1
  python lab/legal/crawl.py                 # all three courts, default targets
  python lab/legal/crawl.py --quick         # 30 decisions per court, to check it works
  python lab/legal/crawl.py --court aym     # one court
  python lab/legal/crawl.py --court yargitay --gap 3 --max-stops 10   # Yargıtay throttles at 1 req/s

Sources: Yargıtay (Bedesten API behind mevzuat.adalet.gov.tr), Danıştay (karararama.danistay.gov.tr),
AYM individual applications (kararlarbilgibankasi.anayasa.gov.tr). Requests go through the MIT-licensed
turk-hukuku-ictihat-mcp client: it names itself in the User-Agent, keeps one request per second per
site and stops on a CAPTCHA, a 429 or a redirect to a login page. We never solve or skip a CAPTCHA.

Output: lab/data/legal_web/raw.jsonl (git-ignored), one decision per line:
  {"court", "id", "chamber", "esas_no", "karar_no", "date", "year", "title", "url", "query", "text"}
The crawl resumes where it stopped. Raw text stays on this machine; only IDs are ever committed.
"""
from __future__ import annotations

import argparse, json, re, sys, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "lab" / "data" / "legal_web" / "raw.jsonl"

# Fixed before crawling (pre-registered): everyday topics where decisions name people.
QUERIES = {
    "yargitay": ["tazminat", "boşanma", "nafaka", "velayet", "işe iade", "kıdem tazminatı", "kira", "tahliye", "miras",
                 "tapu iptal", "itirazın iptali", "icra", "trafik kazası", "kasten yaralama", "hırsızlık", "dolandırıcılık",
                 "tehdit", "hakaret", "uyuşturucu", "kişisel verilerin", "sigorta", "ortaklığın giderilmesi",
                 "menfi tespit", "vekalet ücreti", "konkordato"],
    "danistay": ["imar", "kamulaştırma", "disiplin", "ihale", "vergi", "ruhsat", "atama", "memur", "öğrenci",
                 "tam yargı", "ecrimisil", "sağlık", "sosyal güvenlik", "polis", "belediye"],
    "aym": ["adil yargılanma", "ifade özgürlüğü", "mülkiyet hakkı", "kişi özgürlüğü", "özel hayat", "kötü muamele",
            "yaşam hakkı", "eşitlik", "toplantı", "din özgürlüğü", "makul süre", "kişisel veri"],
}
TARGET = {"yargitay": 4000, "danistay": 2500, "aym": 1200}
PER_PAGE = 50

def _year(s: str | None) -> int | None:
    m = re.search(r"(19|20)\d\d", s or "")
    return int(m.group(0)) if m else None

def _client(court):
    from turk_hukuku_ictihat import anayasa, danistay, yargitay
    return {"yargitay": yargitay, "danistay": danistay, "aym": anayasa}[court]

_lock = threading.Lock()
def _write(rec):
    with _lock, OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

MAX_STOPS = 3
def _wait(e, stops):  # wait at least what the site asked, longer after each stop
    return max(getattr(e, "bekleme", 120), 60 * stops)

def crawl(court: str, target: int, have: set, log=print):
    from turk_hukuku_ictihat.ortak import ErisimDurdu
    api, n, stops = _client(court), sum(1 for k in have if k[0] == court), 0
    per_query = max(1, target // len(QUERIES[court]) + 1)
    for q in QUERIES[court]:
        got, page = 0, 1
        while got < per_query and n < target:
            try:
                res = api.ara(q, adet=PER_PAGE, sayfa=page)
            except ErisimDurdu as e:
                stops += 1; log(f"[{court}] site asked us to stop ({e}); waiting {_wait(e, stops)} s")
                if stops >= MAX_STOPS: log(f"[{court}] stopped {stops} times, giving up on this court"); return n
                time.sleep(_wait(e, stops)); continue
            except Exception as e:
                log(f"[{court}] search '{q}' p{page} failed: {e}"); break
            hits = res.get("sonuclar") or []
            if not hits: break
            for h in hits:
                key = (court, str(h["id"]))
                if key in have: continue
                try:
                    doc = api.karar(h["id"])
                except ErisimDurdu as e:
                    stops += 1; log(f"[{court}] stop on fetch ({e}); waiting {_wait(e, stops)} s")
                    if stops >= MAX_STOPS: log(f"[{court}] stopped {stops} times, giving up on this court"); return n
                    time.sleep(_wait(e, stops)); continue
                except Exception as e:
                    log(f"[{court}] fetch {h['id']} failed: {e}"); continue
                text = doc.get("metin")
                if not text or len(text) < 300: continue
                date = h.get("karar_tarihi")
                _write({"court": court, "id": str(h["id"]), "chamber": h.get("mahkeme") or h.get("birim"),
                        "esas_no": h.get("esas_no") or h.get("basvuru_no"), "karar_no": h.get("karar_no"),
                        "date": date, "year": _year(date), "title": h.get("baslik"), "url": doc.get("kaynak") or h.get("kaynak"),
                        "query": q, "text": text})
                have.add(key); n += 1; got += 1
                if n % 50 == 0: log(f"[{court}] {n}/{target}")
                if got >= per_query or n >= target: break
            page += 1
    log(f"[{court}] done: {n}")
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--court", choices=list(QUERIES), action="append")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--gap", type=float, default=1.0, help="seconds between requests to one site (Yargıtay needs ~3)")
    ap.add_argument("--max-stops", type=int, default=3, help="give up on a court after this many rate-limit stops")
    a = ap.parse_args()
    global MAX_STOPS
    MAX_STOPS = a.max_stops
    from turk_hukuku_ictihat import ortak
    ortak.ARALIK = max(ortak.ARALIK, a.gap)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    have = set()
    if OUT.exists():
        for line in OUT.open(encoding="utf-8"):
            r = json.loads(line); have.add((r["court"], r["id"]))
    courts = a.court or list(QUERIES)
    targets = {c: (30 if a.quick else TARGET[c]) for c in courts}
    # one thread per court: each site keeps its own 1 request/second limit
    ts = [threading.Thread(target=crawl, args=(c, targets[c], have)) for c in courts]
    for t in ts: t.start()
    for t in ts: t.join()
    counts = {}
    for line in OUT.open(encoding="utf-8"):
        c = json.loads(line)["court"]; counts[c] = counts.get(c, 0) + 1
    print("raw.jsonl:", counts)

if __name__ == "__main__":
    sys.exit(main())
