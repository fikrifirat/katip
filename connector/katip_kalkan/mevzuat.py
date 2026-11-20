"""mevzuat_bak: read a Turkish statute article, or check every statute citation in a text, offline.

Source: Katip Cite's index (cite.py, data/statutes.json.gz), built from github.com/onurcan-b/acik-mevzuat, a
daily mirror of mevzuat.adalet.gov.tr. It knows which laws and articles exist and whether they are in force,
for 1,085 laws; it keeps the article text for the core codes (TCK, CMK, TBK, TMK, HMK, İİK, TTK, İş Kanunu,
...). Nothing leaves the computer. The index has a date: amendments after it are not in it, and the tool says so.
"""
from __future__ import annotations

import re

from . import cite, emsal

VERDICTS = {
    "OK": "var ve yürürlükte",
    "ARTICLE_REPEALED": "madde mülga",
    "LAW_REPEALED": "kanun yürürlükten kalkmış",
    "NO_SUCH_ARTICLE": "böyle bir madde yok",
    "NUMBER_NAME_CLASH": "kanun numarası ile adı uyuşmuyor",
    "UNKNOWN_LAW": "bu numarada kanun yok",
    "UNVERIFIED": "doğrulanamadı",
    "DECISION_UNVERIFIED": "karar atfı (çevrimdışı denetlenmez; emsal_ara ile arayın)",
    "DECISION_MALFORMED": "karar atfı biçim hatalı",
}


def _clean(art_text: str | None, law_no: str | None, article: str | None) -> str | None:
    """The index keeps the next article's heading at the end of each article; cut it off."""
    if not art_text:
        return None
    t = re.sub(r"\s*\[\d+\]", "", art_text).strip()
    m = re.search(r"^(.*[.:;)])\s+[^.:;)]{3,160}$", t, re.S)
    return (m.group(1) if m else t)[:4000]


def lookup(citation_text: str = "", text: str = "", with_text: bool = True) -> dict:
    """citation_text: one citation such as 'TBK 344', '6098 sayılı Kanun m. 344', 'İş Kanunu 25/II'.
    text: a longer text (a draft, an AI answer) whose statute citations should all be checked."""
    src = (citation_text or text or "").strip()
    if not src:
        raise ValueError("give a citation (atif) or a text (metin)")
    if len(src) > 200_000:
        raise ValueError("text too long (200,000 characters at most)")
    ck = cite.default_checker()
    r = ck.check(src)
    out = []
    for c in r["citations"]:
        item = {"cited_as": c["text"].strip(), "kind": c["kind"], "verdict": c["verdict"],
                "meaning": VERDICTS.get(c["verdict"], c["verdict"]), "note": c["note"] or None}
        if c["kind"] == "statute":
            item.update({"law_no": c["law_no"], "law": c["law_title"], "article": c["article"], "source": c["source"]})
            if with_text and (citation_text or len(r["citations"]) <= 5):
                item["article_text"] = _clean(c.get("article_text"), c["law_no"], c["article"])
                if c["verdict"] == "OK" and not item["article_text"]:
                    item["article_text_note"] = "Katip'in kopyasında bu kanunun madde metni yok; resmi metin için source bağlantısını açın."
        out.append(item)
    if not out:
        return {"citations": [], "note": "Metinde tanınan bir kanun maddesi atfı yok. Örnek: 'TBK 344', "
                                          "'6098 sayılı Kanun'un 344. maddesi', 'İş Kanunu m. 25/II'."}
    return {"citations": out, "summary": {"statutes": r["statutes"], "ok": r["ok"], "wrong": r["bad"],
                                          "unverified": r["unverified"], "decisions": r["decisions"]},
            "index": {"source": "mevzuat.adalet.gov.tr (acik-mevzuat mirror)", "as_of": r["index"].get("commit_date")},
            "note": "Çevrimdışı kontrol: index tarihinden sonraki değişiklikler görünmez. Karar atıfları burada "
                    "denetlenmez; Yargıtay kararı için emsal_ara kullanın."}


def heading_of(key: str) -> str:
    return emsal.heading(key)
