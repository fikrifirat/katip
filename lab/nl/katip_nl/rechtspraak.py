"""Dutch case law: find ECLI numbers in a text and check each against Rechtspraak Open Data
(data.rechtspraak.nl), with court, date, area of law, summary (inhoudsindicatie) and formal relations
(appeal, cassation, AG opinion). The Dutch counterpart of Katip Emsal's number check.

Only the ECLI itself is sent. Published Dutch decisions are already pseudonymised by the courts, and
Rechtspraak offers them as open data for reuse, so a local index (phase 2) is legally simpler than in Turkey.
"""
from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

CACHE = Path.home() / ".cache" / "katip-nl" / "ecli"
API = "https://data.rechtspraak.nl/uitspraken/content?id={ecli}"
UA = "katip-nl/0.1 (+https://github.com/fikrifirat/katip)"
ECLI_RE = re.compile(r"\bECLI:[A-Z]{2}:[A-Z0-9]{1,7}:\d{4}:[A-Z0-9.]{1,25}[A-Z0-9]")


def find_eclis(text):
    seen, out = set(), []
    for m in ECLI_RE.finditer(text):
        if m.group() not in seen:
            seen.add(m.group())
            out.append(m.group())
    return out


def _txt(x):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x))).strip()


def lookup(ecli):
    """{'ecli', 'exists', 'court', 'date', 'area', 'procedure', 'summary', 'relations', 'url'}; NL ECLIs only."""
    url = f"https://uitspraken.rechtspraak.nl/details?id={ecli}"
    if not ecli.startswith("ECLI:NL:"):
        return {"ecli": ecli, "exists": None, "url": None, "note": "not a Dutch ECLI: not checked"}
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (ecli.replace(":", "_") + ".json")
    if f.exists():
        return json.loads(f.read_text())
    req = urllib.request.Request(API.format(ecli=ecli), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            x = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"ecli": ecli, "exists": False, "url": url}
        raise
    if "<dcterms:identifier>" not in x:
        return {"ecli": ecli, "exists": False, "url": url}

    def one(pat):
        m = re.search(pat, x, re.S)
        return _txt(m.group(1)) if m else None

    rel = [{"ecli": a, "type": b.rsplit("/", 1)[-1], "result": c.split("#")[-1]} for a, b, c in re.findall(
        r'<dcterms:relation[^>]*ecli:resourceIdentifier="([^"]+)"[^>]*psi:type="([^"]+)"[^>]*psi:gevolg="([^"]+)"', x)]
    summ = one(r"<inhoudsindicatie[^>]*>(.*?)</inhoudsindicatie>")
    out = {"ecli": ecli, "exists": True, "court": one(r"<dcterms:creator[^>]*>([^<]*)"),
           "date": one(r'<dcterms:date[^>]*rdfs:label="Uitspraakdatum"[^>]*>([^<]*)'),
           "area": one(r'<dcterms:subject[^>]*>([^<]*)'), "procedure": one(r"<psi:procedure[^>]*>([^<]*)"),
           "summary": summ, "relations": rel, "url": url}
    f.write_text(json.dumps(out, ensure_ascii=False))
    return out


def check_text(text):
    return [lookup(e) for e in find_eclis(text)]
