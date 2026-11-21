"""Dutch statute citations: find them in a text, check that the article exists in the act in force today,
and quote it. The Dutch counterpart of Katip Cite (lab/cite) and of Mevzuat.

Source: the Basiswettenbestand (BWB) of wetten.overheid.nl, through the official SRU search service
(zoekservice.overheid.nl) and the XML repository (repository.officiele-overheidspublicaties.nl).
Statute texts are not protected by copyright (Auteurswet art. 11) and the BWB is published as open data.

Only act identifiers (BWBR...) and a date ever leave the computer, never document text. Downloaded acts are
cached in ~/.cache/katip-nl/bwb so the second lookup is offline.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

CACHE = Path.home() / ".cache" / "katip-nl" / "bwb"
SRU = "https://zoekservice.overheid.nl/sru/Search"
UA = "katip-nl/0.1 (+https://github.com/fikrifirat/katip)"

# abbreviation -> (BWB id, Dutch title, English title, "book" style)
# BW books are cited as art. <book>:<article> BW; the book picks the act. Awb is cited as art. 8:69 Awb, where the
# colon is part of the article number itself. Ids checked against the SRU service on 20 Nov 2026.
BW_BOOKS = {"1": "BWBR0002656", "2": "BWBR0003045", "3": "BWBR0005291", "4": "BWBR0002761", "5": "BWBR0005288",
            "6": "BWBR0005289", "7": "BWBR0005290", "7A": "BWBR0006000", "8": "BWBR0005034", "10": "BWBR0030068"}
ACTS = {
    "Rv": ("BWBR0001827", "Wetboek van Burgerlijke Rechtsvordering", "Code of Civil Procedure"),
    "Sr": ("BWBR0001854", "Wetboek van Strafrecht", "Criminal Code"),
    "Sv": ("BWBR0001903", "Wetboek van Strafvordering", "Code of Criminal Procedure"),
    "Awb": ("BWBR0005537", "Algemene wet bestuursrecht", "General Administrative Law Act"),
    "Gw": ("BWBR0001840", "Grondwet", "Constitution"),
    "UAVG": ("BWBR0040940", "Uitvoeringswet Algemene verordening gegevensbescherming", "GDPR Implementation Act"),
    "Vw 2000": ("BWBR0011823", "Vreemdelingenwet 2000", "Aliens Act 2000"),
    "Vw": ("BWBR0011823", "Vreemdelingenwet 2000", "Aliens Act 2000"),
    "WOR": ("BWBR0002747", "Wet op de ondernemingsraden", "Works Councils Act"),
    "Wet IB 2001": ("BWBR0011353", "Wet inkomstenbelasting 2001", "Income Tax Act 2001"),
    "AWR": ("BWBR0002320", "Algemene wet inzake rijksbelastingen", "General State Taxes Act"),
    "Wet LB 1964": ("BWBR0002471", "Wet op de loonbelasting 1964", "Wage Tax Act 1964"),
    "Wet OB 1968": ("BWBR0002629", "Wet op de omzetbelasting 1968", "Turnover Tax Act 1968"),
}
BW_TITLES = ("Burgerlijk Wetboek Boek {b}", "Civil Code Book {b}")
EU = {"AVG": ("32016R0679", "Algemene verordening gegevensbescherming", "General Data Protection Regulation (GDPR)"),
      "GDPR": ("32016R0679", "Algemene verordening gegevensbescherming", "General Data Protection Regulation (GDPR)")}

_ACT_ALT = "|".join(re.escape(a) for a in sorted(list(ACTS) + list(EU), key=len, reverse=True))
CITE_RE = re.compile(
    rf"\b(?:art(?:ikel|\.|icle)?|artt\.)\s*(?P<nr>\d+[a-z]?(?::\d+[a-z]?)?)(?P<rest>(?:\s+(?:lid|leden)\s+\d+)?"
    rf"(?:\s*(?:,|sub|onder)\s*[a-z0-9]+\.?)?)\s+(?:van\s+(?:het|de)\s+)?(?P<act>BW|{_ACT_ALT})\b")


def find_citations(text):
    """[{'cite', 'start', 'end', 'act_key', 'bwb', 'article', 'title_nl', 'title_en'}]; unknown acts are skipped."""
    out = []
    for m in CITE_RE.finditer(text):
        nr, act = m.group("nr"), m.group("act")
        c = {"cite": m.group(), "start": m.start(), "end": m.end(), "act_key": act}
        if act == "BW":
            if ":" not in nr:
                c.update(bwb=None, article=nr, title_nl="Burgerlijk Wetboek (boek ontbreekt)",
                         title_en="Civil Code (book missing)")
            else:
                book, art = nr.split(":", 1)
                book = book.upper()
                c.update(bwb=BW_BOOKS.get(book), article=art, title_nl=BW_TITLES[0].format(b=book),
                         title_en=BW_TITLES[1].format(b=book))
        elif act in EU:
            celex, tnl, ten = EU[act]
            c.update(bwb=None, celex=celex, article=nr, title_nl=tnl, title_en=ten)
        else:
            bwb, tnl, ten = ACTS[act]
            c.update(bwb=bwb, article=nr, title_nl=tnl, title_en=ten)
        out.append(c)
    return out


def _get(url, accept="application/xml", timeout=60):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def act_xml(bwb, on=None):
    """Download (or read from cache) the consolidated act valid on `on` (default today)."""
    on = on or dt.date.today().isoformat()
    CACHE.mkdir(parents=True, exist_ok=True)
    idx = CACHE / f"{bwb}.json"
    meta = json.loads(idx.read_text()) if idx.exists() else {}
    if meta.get("checked") != on:
        q = f"dcterms.identifier={bwb} and overheidbwb.geldigheidsdatum={on}"
        sru = _get(f"{SRU}?operation=searchRetrieve&version=2.0&x-connection=BWB&maximumRecords=1&query="
                   + urllib.parse.quote(q)).decode("utf-8")
        loc = re.search(r"<overheidbwb:locatie_toestand>([^<]+)", sru)
        if not loc:
            raise LookupError(f"{bwb}: no version in force on {on}")
        meta = {"checked": on, "url": loc.group(1), "file": loc.group(1).rsplit("/", 1)[-1]}
        idx.write_text(json.dumps(meta))
    f = CACHE / meta["file"]
    if not f.exists():
        f.write_bytes(_get(meta["url"]))
    return f.read_text(encoding="utf-8"), meta


def _plain(xml_fragment):
    t = re.sub(r"<meta-data>.*?</meta-data>", " ", xml_fragment, flags=re.S)
    t = re.sub(r"</(?:al|li|lid)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(re.sub(r"[ \t]+", " ", t))
    t = "\n".join(x.strip() for x in t.splitlines() if x.strip())
    return re.sub(r"(?m)^(\d+[a-z]?\.?)\n", r"\1 ", t)  # "1\nHij die ..." -> "1 Hij die ..." (lid numbers)


def article(bwb, nr, on=None):
    """Returns {'exists', 'heading', 'text', 'url', 'version'} for article `nr` of act `bwb`."""
    xml, meta = act_xml(bwb, on)
    m = re.search(rf'<artikel\b[^>]*\blabel="Artikel {re.escape(nr)}"[^>]*>(.*?)</artikel>', xml, re.S)
    url = f"https://wetten.overheid.nl/jci1.3:c:{bwb}&artikel={urllib.parse.quote(nr)}"
    if not m:
        return {"exists": False, "heading": None, "text": None, "url": url, "version": meta["file"]}
    body = m.group(1)
    head = re.search(r"<titel>(.*?)</titel>", body, re.S)
    status = re.search(r'<artikel\b[^>]*\bstatus="([^"]+)"', m.group(0))
    text = _plain(re.sub(r"<kop>.*?</kop>", "", body, count=1, flags=re.S))
    vervallen = "vervallen" in (status.group(1) if status else "") or text.strip().lower() in ("[vervallen]", "vervallen")
    return {"exists": not vervallen, "repealed": vervallen, "heading": _plain(head.group(1)) if head else None,
            "text": text, "url": url, "version": meta["file"]}


def check_text(text, on=None):
    """Find every citation and look it up. Network: one SRU query + one XML download per act (then cached)."""
    out = []
    for c in find_citations(text):
        if c.get("bwb"):
            try:
                c.update(article(c["bwb"], c["article"], on))
            except Exception as e:  # noqa: BLE001 - report, don't crash a whole document
                c.update(exists=None, error=str(e))
        elif c.get("celex"):
            c.update(exists=None, url=f"https://eur-lex.europa.eu/legal-content/NL/TXT/?uri=CELEX:{c['celex']}",
                     note="EU regulation: link only, not checked")
        else:
            c.update(exists=None, note="book number missing (write art. 7:611 BW, not art. 611 BW)")
        out.append(c)
    return out
