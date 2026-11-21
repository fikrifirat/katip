"""MASAK asset-freeze lists (Law 6415 art. 5, 6, 7 and Law 7262).

The public pages on masak.hmb.gov.tr are a React app. Its own search box calls an open JSON
endpoint, which we call the same way: one POST per sanction type, empty name filter.
robots.txt allows everything. We also read the CSV files linked from the list pages, to check
that the endpoint and the downloadable files agree (coverage check, see ``crosscheck``).
"""
from __future__ import annotations

import csv
import hashlib
import io
import re

from normalize import fold, split_aliases

SOURCE = "masak"
BASE = "https://masak.hmb.gov.tr"
API = BASE + "/portal/v2/masak/mvd/malvarligi-dondurulanlar"
PAGES_API = BASE + "/portal/v2/pages"

# label -> (exact sanction-type string the endpoint expects, public page with the decisions)
LISTS = {
    "6415-m5-bmgk": ("BMGK Yaptırımları Kapsamında (6415 sayılı kanun 5. Maddesine istinaden)",
                     BASE + "/5-maddeye-iliskin-bakanlar-kurulu-kararlari"),
    "6415-m6-yabanci": ("Yabancı ülke talebi (6415 sayılı kanun 6. Maddesine istinaden)",
                        BASE + "/6-maddeye-iliskin-bakanlar-kurulu-kararlari"),
    "6415-m7-ic": ("İç Dondurma (6415 sayılı kanun 7. Maddesine istinaden)", BASE + "/7madde"),
    "7262-kitle-imha": ("7262 Sayılı Kanun Kapsamında", BASE + "/"),
}
LIST_PAGES = {"6415-m5-bmgk": "5-maddeye-iliskin-bakanlar-kurulu-kararlari",
              "6415-m6-yabanci": "6-maddeye-iliskin-bakanlar-kurulu-kararlari",
              "6415-m7-ic": "7madde"}


def _rg_link(karar: str) -> str:
    """'2021-04-07 / 31447' (Resmî Gazete date / issue) -> link to that day's Resmî Gazete."""
    m = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", karar or "")
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"https://www.resmigazete.gov.tr/eskiler/{y}/{mo}/{y}{mo}{d}.htm"


def to_record(row: dict, label: str, page: str) -> dict:
    name = (row.get("ad_soyad_unvan") or "").strip()
    aliases = split_aliases(row.get("diger_adlari") or "")
    person = bool(row.get("anne_adı") or row.get("baba_adı") or re.search(r"\d", row.get("dogum_tarihi") or ""))
    rid = f"{label}:{row.get('sira_no')}:{hashlib.sha1(fold(name).encode()).hexdigest()[:8]}"
    return {
        "rid": rid,
        "source": SOURCE,
        "list": label,
        "kind": "person" if person else "unknown",
        "names": [name, *[a for a in aliases if fold(a) != fold(name)]],
        "ids": [row.get("tckn_vkn") or ""],
        "birth": row.get("dogum_tarihi") or "",
        "birthplace": row.get("dogum_yeri") or "",
        "nationality": ", ".join(x for x in {row.get("uyrugu") or "", row.get("diger_uyruk") or ""} if x),
        "organisation": (row.get("orgutu") or "").strip(),
        "sanction": row.get("yaptirim_turu") or "",
        "decision": row.get("karar_sayisi") or "",
        "url": page,
        "gazette_url": _rg_link(row.get("karar_sayisi") or ""),
        "raw": row,
    }


def fetch(client) -> tuple[list[dict], dict]:
    records, detail = [], {"lists": {}}
    for label, (yaptirim, page) in LISTS.items():
        r = client.post_json(API, {"ad": "", "uyruk": "", "orgut": "", "yaptirim": yaptirim})
        d = r.json()
        rows = d.get("data") or []
        detail["lists"][label] = {"reported": d.get("numRows"), "received": len(rows)}
        records += [to_record(row, label, page) for row in rows]
    # when each list page last changed, and its newest decision: freshness evidence
    for label, slug in LIST_PAGES.items():
        try:
            p = client.get(f"{PAGES_API}?slug={slug}&_fields=modified,content").json()[0]
            text = re.sub(r"<[^>]+>", " ", p["content"]["rendered"])
            dates = re.findall(r"(\d{2})\.(\d{2})\.(\d{4})\s*[-/]\s*\d{4,5}", text)
            newest = max((f"{y}-{m}-{dd}" for dd, m, y in dates), default="")
            files = re.findall(r'href="([^"]+\.csv)"', p["content"]["rendered"])
            detail["lists"][label].update({"page_modified": p.get("modified"), "newest_decision": newest, "csv": files})
        except Exception as e:  # freshness metadata is nice to have, not required
            detail["lists"][label]["page_error"] = str(e)[:200]
    try:
        records += csv_only_records(client, records, detail)
    except Exception as e:
        detail["csv_error"] = repr(e)[:200]
    return records, detail


# -- coverage check against the downloadable CSV files ---------------------------------------
_NAME_HEADERS = ("AD-SOYAD/ÜNVANI", "ADI SOYADI-ÜNVANI", "GERÇEK/TÜZEL KİŞİ/KURULUŞ/ORGANİZASYON ADI SOYADI ÜNVANI")


def _col(header: list[str], *needles: str) -> int | None:
    for j, h in enumerate(header):
        hu = " ".join(h.upper().split())
        if any(n in hu for n in needles):
            return j
    return None


def parse_csv_rows(body: bytes) -> list[dict]:
    """Rows from one MASAK CSV (Windows-1254, ';' separated, title rows above the header)."""
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = body.decode("cp1254", errors="replace")
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    hi = None
    for i, row in enumerate(rows[:10]):
        if any(c.strip().upper() in _NAME_HEADERS or "ADI SOYADI" in c.upper() or "AD-SOYAD" in c.upper() for c in row):
            hi = i
            break
    if hi is None:
        return []
    head = rows[hi]
    col = {"name": _col(head, *_NAME_HEADERS, "ADI SOYADI", "AD-SOYAD"), "ids": _col(head, "TCKN"),
           "aliases": _col(head, "DİĞER İSİMLERİ"), "birth": _col(head, "DOĞUM TARİHİ"),
           "nationality": _col(head, "UYRUĞU"), "gazette": _col(head, "RESMİ GAZETE")}
    out = []
    for row in rows[hi + 1:]:
        if len(row) <= col["name"] or not row[0].strip().isdigit() or not row[col["name"]].strip():
            continue
        out.append({k: (row[j].strip() if j is not None and j < len(row) else "") for k, j in col.items()} | {"no": row[0].strip()})
    return out


def parse_csv(body: bytes) -> list[str]:
    return [r["name"] for r in parse_csv_rows(body)]


def csv_only_records(client, records: list[dict], detail: dict) -> list[dict]:
    """Rows that appear in a list's CSV file but match no row from the JSON endpoint.

    The two disagree on a handful of rows (see README). For screening a missed name is worse
    than a duplicate, so these rows are kept too, marked ``csv_only``.
    """
    from match import name_score
    from normalize import tokens

    extra = []
    for label, info in detail["lists"].items():
        if not info.get("csv"):
            continue
        url = info["csv"][0]
        api = [tokens(n) for r in records if r["list"] == label for n in r["names"]]
        for row in parse_csv_rows(client.get(url).body):
            t = tokens(row["name"])
            if any(name_score(t, a) >= 0.93 for a in api):
                continue
            extra.append({
                "rid": f"{label}:csv:{row['no']}:{hashlib.sha1(fold(row['name']).encode()).hexdigest()[:8]}",
                "source": SOURCE, "list": label, "kind": "unknown", "csv_only": True,
                "names": [row["name"], *split_aliases(row.get("aliases", ""))],
                "ids": [row.get("ids", "")], "birth": row.get("birth", ""), "nationality": row.get("nationality", ""),
                "organisation": "", "sanction": "", "decision": row.get("gazette", ""),
                "url": LISTS[label][1], "file_url": url, "gazette_url": "",
                "raw": row,
            })
        info["csv_only_rows"] = sum(1 for e in extra if e["list"] == label)
    return extra


def crosscheck(client, records: list[dict], detail: dict) -> dict:
    """Compare names from the JSON endpoint with names in each list's CSV file."""
    out = {}
    for label, info in detail["lists"].items():
        csvs = info.get("csv") or []
        if not csvs:
            out[label] = {"csv": None}
            continue
        names_csv = parse_csv(client.get(csvs[0]).body)
        api = {fold(r["names"][0]) for r in records if r["list"] == label and not r.get("csv_only")}
        csvn = {fold(n) for n in names_csv}
        out[label] = {
            "csv": csvs[0].rsplit("/", 1)[-1],
            "csv_rows": len(names_csv),
            "api_rows": info["received"],
            "csv_rows_kept_extra": info.get("csv_only_rows"),
            "in_both": len(api & csvn),
            "only_api": len(api - csvn),
            "only_csv": len(csvn - api),
            "only_csv_examples": sorted(csvn - api)[:5],
            "only_api_examples": sorted(api - csvn)[:5],
        }
    return out
