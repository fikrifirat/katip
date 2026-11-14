"""Katip Cite: find every Turkish statute citation in a text and check it against the official law texts, offline.

    python lab/cite/katip_cite.py answer.txt          # prints each citation with a verdict
    from katip_cite import Checker; Checker().check(text)

Standard library only. The index (data/statutes.json.gz, ~1.5 MB) is built by build_index.py from a dated snapshot of
the Açık Mevzuat mirror of mevzuat.adalet.gov.tr. It answers one question per citation: does this article of this law
exist and is it in force today? It does not judge whether the article supports the argument (the bench measures that
separately, with expected articles written per question).

Verdicts (statutes)
  OK                  law in force, article exists and is in force
  ARTICLE_REPEALED    the article is marked "Mülga" (repealed)
  NO_SUCH_ARTICLE     the law has no article with that number
  LAW_REPEALED        the whole law is repealed (818 BK, 743 MK, 765 TCK, 1086 HUMK, most of 1475 İş K.)
  NUMBER_NAME_CLASH   the law number and the law name point to different laws ("6098 sayılı Türk Medeni Kanunu")
  UNKNOWN_LAW         no law with that number exists in the index
  UNVERIFIED          we could not decide (our parse of that law has a gap at that number)
Decisions (Yargıtay, Danıştay, AYM) are extracted and format-checked only: DECISION_UNVERIFIED or DECISION_MALFORMED.
"""
from __future__ import annotations

import gzip, json, re, sys, unicodedata
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = HERE / "data" / "statutes.json.gz"

BAD = {"ARTICLE_REPEALED", "NO_SUCH_ARTICLE", "LAW_REPEALED", "NUMBER_NAME_CLASH", "UNKNOWN_LAW"}

# Aliases -> law number. Abbreviations follow Turkish legal writing: BK = 818 (the old code, repealed 2012), TBK = 6098.
# A bare "Borçlar Kanunu" is read as the code in force (6098), and MK as TMK (4721): that is how people use them today.
# Keys are matched case-insensitively after normalisation (see norm()). English names cover expat-facing answers.
ALIASES = {
    "6098": ["TBK", "Türk Borçlar Kanunu", "Borçlar Kanunu", "Turkish Code of Obligations", "Code of Obligations", "TCO"],
    "818": ["BK", "eski Borçlar Kanunu", "mülga Borçlar Kanunu", "818 sayılı Borçlar Kanunu"],
    "4721": ["TMK", "MK", "Türk Medeni Kanunu", "Medeni Kanun", "Turkish Civil Code", "Civil Code"],
    "743": ["Türk Kanunu Medenisi", "eski Medeni Kanun", "mülga Medeni Kanun"],
    "6100": ["HMK", "Hukuk Muhakemeleri Kanunu", "Code of Civil Procedure", "Turkish Code of Civil Procedure", "Civil Procedure Code", "CCP"],
    "1086": ["HUMK", "Hukuk Usulü Muhakemeleri Kanunu"],
    "4857": ["İş K", "İşK", "İş Kanunu", "Labour Law", "Labor Law", "Labour Act", "Labor Act", "Turkish Labour Law", "Turkish Labor Law", "Turkish Labour Code", "Turkish Labor Code"],
    "1475": ["1475 sayılı İş Kanunu", "eski İş Kanunu", "mülga İş Kanunu"],
    "5237": ["TCK", "Türk Ceza Kanunu", "Turkish Penal Code", "Turkish Criminal Code", "Penal Code", "TPC"],
    "765": ["eski TCK", "mülga TCK", "765 sayılı TCK"],
    "5271": ["CMK", "Ceza Muhakemesi Kanunu", "Code of Criminal Procedure", "Criminal Procedure Code"],
    "1412": ["CMUK", "Ceza Muhakemeleri Usulü Kanunu"],
    "2004": ["İİK", "İcra ve İflas Kanunu", "Enforcement and Bankruptcy Law", "Execution and Bankruptcy Law", "Enforcement and Bankruptcy Code"],
    "6102": ["TTK", "Türk Ticaret Kanunu", "Turkish Commercial Code", "Commercial Code"],
    "6762": ["eski TTK", "mülga TTK", "6762 sayılı TTK"],
    "6698": ["KVKK", "KVKK'", "Kişisel Verilerin Korunması Kanunu", "Personal Data Protection Law", "Law on the Protection of Personal Data", "Personal Data Protection Law (KVKK)", "PDPL"],
    "6458": ["YUKK", "Yabancılar ve Uluslararası Koruma Kanunu", "Law on Foreigners and International Protection", "LFIP"],
    "6735": ["Uluslararası İşgücü Kanunu", "International Labour Force Law", "International Labor Force Law", "Law on International Labour Force", "Law on International Labor Force"],
    "5901": ["Türk Vatandaşlığı Kanunu", "Turkish Citizenship Law", "Turkish Citizenship Code"],
    "6502": ["TKHK", "Tüketicinin Korunması Hakkında Kanun", "Tüketici Kanunu", "Consumer Protection Law", "Law on Consumer Protection"],
    "634": ["KMK", "Kat Mülkiyeti Kanunu", "Condominium Law", "Property Ownership Law"],
    "7201": ["Tebligat Kanunu", "Notification Law", "Law on Notification"],
    "6325": ["HUAK", "Hukuk Uyuşmazlıklarında Arabuluculuk Kanunu", "Mediation in Civil Disputes Law", "Law on Mediation in Civil Disputes"],
    "7036": ["İş Mahkemeleri Kanunu", "Labour Courts Law", "Labor Courts Law", "Law on Labour Courts", "Law on Labor Courts"],
    "2709": ["AY", "Anayasa", "Türkiye Cumhuriyeti Anayasası", "Constitution", "Turkish Constitution"],
    "1136": ["Av. K", "Avukatlık Kanunu", "Attorneyship Law", "Advocacy Law"],
    "5718": ["MÖHUK", "Milletlerarası Özel Hukuk ve Usul Hukuku Hakkında Kanun", "Private International Law", "Law on Private International and Procedural Law", "PIL"],
    "2577": ["İYUK", "İdari Yargılama Usulü Kanunu", "Administrative Procedure Law"],
    "5510": ["SGK Kanunu", "Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu", "Social Insurance and General Health Insurance Law"],
    "492": ["Harçlar Kanunu", "Law on Fees", "Fees Law"],
    "2644": ["Tapu Kanunu", "Land Registry Law", "Title Deed Law"],
    "1512": ["Noterlik Kanunu", "Notary Law"],
    "5275": ["İnfaz Kanunu", "Ceza ve Güvenlik Tedbirlerinin İnfazı Hakkında Kanun"],
    "5395": ["ÇKK", "Çocuk Koruma Kanunu", "Child Protection Law"],
    "7338": ["Veraset ve İntikal Vergisi Kanunu", "Inheritance and Transfer Tax Law"],
    "193": ["GVK", "Gelir Vergisi Kanunu", "Income Tax Law"],
    "213": ["VUK", "Vergi Usul Kanunu", "Tax Procedure Law"],
    "3194": ["İmar Kanunu", "Zoning Law"],
    "6356": ["Sendikalar ve Toplu İş Sözleşmesi Kanunu", "Trade Unions and Collective Labour Agreements Law"],
    "6331": ["İş Sağlığı ve Güvenliği Kanunu", "İSG Kanunu", "Occupational Health and Safety Law"],
    "4734": ["Kamu İhale Kanunu", "KİK", "Public Procurement Law"],
    "5846": ["FSEK", "Fikir ve Sanat Eserleri Kanunu"],
    "6769": ["SMK", "Sınai Mülkiyet Kanunu", "Industrial Property Law"],
    "7155": [],
}

# Repealed code -> the code that replaced it: "818 sayılı Borçlar Kanunu" names the old code, not a clash with TBK.
PREDECESSOR = {"818": "6098", "743": "4721", "1475": "4857", "765": "5237", "1086": "6100", "6762": "6102", "1412": "5271"}

FOLD = str.maketrans({"I": "i", "İ": "i", "ı": "i", "’": "'", "‘": "'", "`": "'", "*": " ", "#": " "})  # markdown ** and ## -> space


def fold(s: str) -> str:
    """Length-preserving fold for matching: dotted/dotless i become i, then lower case. Positions stay aligned."""
    out = unicodedata.normalize("NFC", s).translate(FOLD)
    low = "".join(ch.lower() if len(ch.lower()) == 1 else ch for ch in out)
    return low


def tr_title(s: str) -> str:
    """'TÜRK MEDENİ KANUNU' -> 'Türk Medeni Kanunu' with Turkish i/ı rules."""
    low = s.replace("I", "ı").replace("İ", "i").lower()
    return " ".join((w[0].replace("i", "İ").replace("ı", "I").upper() + w[1:]) if w and w not in {"ve", "ile", "hakkında"} else w
                    for w in low.split())


def norm(s: str) -> str:
    """fold(), plus: drop dots that end abbreviations and collapse spaces (for alias lookup)."""
    s = re.sub(r"\.(?=\s|$)", " ", fold(s))
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class Citation:
    kind: str                      # "statute" | "decision"
    text: str                      # the matched span
    start: int
    end: int
    law_no: str | None = None
    law_title: str | None = None
    article: str | None = None     # "344", "7/A", "ek 3", "geçici 1"
    verdict: str = ""
    note: str = ""
    source: str | None = None      # official URL of the law
    article_text: str | None = None


# ----------------------------------------------------------------------------- patterns
ORD = r"(?:'?\s?(?:inci|uncu|üncü|nci|ncu|ncü|i|u|ü))"         # 18 inci, 344'üncü
ART_NUM = r"\d{1,4}(?:\s*/\s*[a-zçğöşü](?![a-zçğıöşü]))?"
PARA = r"(?:\s*/\s*(?:\d{1,2}|[ivx]{1,5})(?![a-zçğöşü])(?:\s*-\s*[a-zçğöşü]\))?|\s*\(\s*\d{1,2}\s*\)|\s*(?:f|fik|fikra)\s*\.?\s*\d{1,2})*"
KIND = r"(?:ek\s+madde|geçici\s+madde|ek\s+md|geçici\s+md|ek\s+m|geç\s*m)"
# article after the law: "m. 344", "md. 344/1", "madde 344", "344. madde(si)", "344 üncü maddesi", "Art. 18", "Article 18(1)"
ART_AFTER = (r"(?:(?:" + KIND + r"\s*\.?\s*|(?:m|md|mad|madde|maddesi|art|article|articles)\s*\.?\s*)" + ART_NUM + PARA +
             r"|" + ART_NUM + PARA + r"\s*(?:\.|" + ORD + r")?\s*(?:maddesi|madde|maddesinde|maddesine|maddesinin|maddeleri|maddesiyle|md|m)(?![a-zçğıöşü]))")
ART_BARE = ART_NUM + PARA                                          # "TBK 344", "HMK 345/1"
LAW_NO_TR = r"(?<![\d/.])(?P<no>\d{2,4})(?!\d)\s*(?:s\.|sayili|no'?lu|numarali)\s*"
LAW_NO_EN = r"(?:law|act|code)\s*(?:no\.?|number)\s*(?P<no2>\d{2,4})(?!\d)"
DECISION = re.compile(
    r"(?P<court>Yargıtay|Yarg\.|YHGK|YCGK|Y\.?\s?\d{1,2}\.?\s?(?:HD|CD)|Danıştay|Dnş\.|Anayasa Mahkemesi|AYM|Court of Cassation|Council of State|Constitutional Court)"
    r"[^\n]{0,120}?(?:E\.|Esas)\s*(?:No\s*[:.]?\s*)?(?P<ey>\d{4})\s*/\s*(?P<en>\d{1,6})"
    r"(?:[^\n]{0,40}?(?:K\.|Karar)\s*(?:No\s*[:.]?\s*)?(?P<ky>\d{4})\s*/\s*(?P<kn>\d{1,6}))?"
    r"|(?P<aym>(?:AYM|Anayasa Mahkemesi|Constitutional Court)[^\n]{0,60}?(?:B\.\s*No|Başvuru\s*No|Application\s*No)\s*[:.]?\s*(?P<by>\d{4})\s*/\s*(?P<bn>\d{1,6}))"
    r"|(?P<ek>(?P<ey2>\d{4})\s*/\s*(?P<en2>\d{1,6})\s*E\.?\s*,?\s*(?P<ky2>\d{4})\s*/\s*(?P<kn2>\d{1,6})\s*K\.)",
    re.I)


class Checker:
    def __init__(self, index_path: Path = INDEX):
        idx = json.load(gzip.open(index_path, "rt", encoding="utf-8"))
        self.meta = {k: idx[k] for k in ("source", "commit", "commit_date")}
        self.laws = idx["laws"]
        self.by_no: dict[str, list[str]] = {}
        for slug, l in self.laws.items():
            self.by_no.setdefault(l["no"], []).append(slug)
        self.alias = {}                                            # normalised alias -> law number
        for no, names in ALIASES.items():
            for n in names:
                self.alias[norm(n)] = no
        for slug, l in self.laws.items():                          # every official title is an alias too
            if not l["removed_provisions_file"] and "KARARNAME" not in l["title"]:
                self.alias.setdefault(norm(l["title"]), l["no"])
        self._build_regex()

    # -------------------------------------------------------------- law lookup
    def _build_regex(self):
        names = sorted(self.alias, key=len, reverse=True)
        def alt(xs):
            return "|".join(re.escape(x).replace(r"\ ", r"\s+") for x in xs)
        short = [n for n in names if len(n) <= 6]                  # abbreviations: TBK, İİK, AY ...
        longn = [n for n in names if len(n) > 6]
        law_name = r"(?P<name>" + alt(longn) + r")"
        law_name2 = r"(?P<name2>" + alt(longn) + r")"
        abbr = r"(?P<abbr>(?<![\wçğöşü])(?:" + alt(short) + r"))(?![a-zçğöşü])\.?"
        kanun = r"(?P<kanun>kanun|law|yasa)"
        # "6098 sayılı (Türk Borçlar) Kanun('un)", "Law No. 6458", "TBK", "İş Kanunu"
        law = (r"(?:" + LAW_NO_TR + r"(?:" + law_name + r"|" + kanun + r")?|" + LAW_NO_EN + r"|" + law_name2 + r"(?:\s*\(\s*(?:law\s+)?(?:no\.?\s*|sayili\s*)?(?P<no3>\d{2,4})(?!\d)\s*(?:sayili)?\s*\))?|" + abbr + r")")
        suffix = r"(?:'?\s?(?:nin|nun|nün|in|un|ün|na|ne|ya|ye|da|de|ta|te|ndaki|ndeki|nda|nde|ca|ce|ça|çe)?)"
        # between law and article allow: a parenthetical "(TCC)" / "(Law No. 4857)", an English "on the ..." title, commas
        between = r"(?:\s*\((?:[^()\d]{1,15}|(?:law\s+)?no\.?\s*\d{2,4})\))?(?:\s+on\s+(?:the\s+)?[a-zçğöşü()\- ]{3,70}?(?=\s*,|\s+art))?\s*,?\s*(?:the\s+)?"
        self.re_law_art = re.compile(law + suffix + between + r"(?P<art>" + ART_AFTER + r"|(?<=\s)" + ART_BARE + r")")
        # English order: "Article 18 of the Labour Law", "Art. 344 of Law No. 6098", "Article 54 of the LFIP"
        self.re_art_law = re.compile(r"(?:art|article)\s*\.?\s*(?P<art>" + ART_NUM + PARA + r")\s+(?:of\s+(?:the\s+)?)(?:turkish\s+)?" + law)
        # a law cited by number with no article: "Law No. 5837", "6493 sayılı Kanun" (fabricated law numbers are real errors)
        self.re_law_only = re.compile(r"(?:" + LAW_NO_TR + r"(?:" + law_name + r"|" + kanun + r")|" + LAW_NO_EN + r")")
        self.re_anaphora = re.compile(r"(?:ayni|söz konusu|anilan)\s+(?:kanun|yasa)(?:'?\s?(?:un|nun))?\s+(?P<art>" + ART_AFTER + r")|(?:the\s+same\s+(?:law|code)),?\s*(?:art|article)\s*\.?\s*(?P<art2>" + ART_NUM + r")")
        self.re_more = re.compile(r"^\s*(?:,|ve|and|ile|-|–|ila|to)\s*(?:m\.?\s*|md\.?\s*|madde\s*|art\.?\s*|article\s*)?(?P<num>\d{1,4})(?:\s*/\s*(?P<let>[a-zçğöşü])(?![a-zçğöşü]))?(?!\d|\s*/\s*\d{4}|\s*(?:sayili|s\.|numarali|no'?lu|tarih|yil|gün|ay\b|hafta|saat|%|tl|lira|year|day|month|week))" + PARA)

    def resolve(self, m) -> tuple[str | None, str, str]:
        """Law number, how we found it, and a clash note if number and name disagree."""
        g = m.groupdict()
        no = g.get("no") or g.get("no2") or g.get("no3")
        name = g.get("name") or g.get("name2") or g.get("abbr")
        name_no = self.alias.get(norm(name)) if name else None
        if no and name_no and no != name_no and PREDECESSOR.get(no) != name_no:
            return no, "number+name", f"number {no} but name '{name}' is law {name_no}"
        if no:
            return no, "number", ""
        if name_no:
            return name_no, "name", ""
        return None, "", ""

    def pick_slugs(self, no: str, name: str | None):
        slugs = [s for s in self.by_no.get(no, []) if "KARARNAME" not in self.laws[s]["title"]] or self.by_no.get(no, [])
        main = [s for s in slugs if not self.laws[s]["removed_provisions_file"]]
        removed = [s for s in slugs if self.laws[s]["removed_provisions_file"]]
        if len(main) > 1 and name:                                  # same number, different laws: use the name
            nm = norm(name)
            main = sorted(main, key=lambda s: -len(set(norm(self.laws[s]["title"]).split()) & set(nm.split())))
        return main[:1], removed

    # -------------------------------------------------------------- verification
    @staticmethod
    def article_key(m_art: str) -> tuple[str, str]:
        a = norm(m_art)
        kind = "ek" if re.match(r"ek\s", a) else "gecici" if re.match(r"geç", a) else "madde"  # a is already folded
        mm = re.search(r"(\d{1,4})(?:\s*/\s*([a-zçğöşü])(?![a-zçğöşü0-9]))?", a)
        num = mm.group(1) + ("/" + mm.group(2).upper() if mm.group(2) else "")
        return kind, num

    def verify(self, no: str | None, kind: str, num: str, clash: str, name: str | None) -> tuple[str, str, dict | None, str | None]:
        if no is None:
            return "UNVERIFIED", "law not recognised", None, None
        if clash:
            return "NUMBER_NAME_CLASH", clash, None, None
        if no not in self.by_no:
            return "UNKNOWN_LAW", f"no law numbered {no} in the index", None, None
        main, removed = self.pick_slugs(no, name)
        base = num.split("/")[0]
        for slug in main:
            l = self.laws[slug]
            a = l["arts"][kind].get(num) or (l["arts"][kind].get(base) if "/" in num else None)
            if a:
                if l["status"] != "in_force":
                    return "LAW_REPEALED", f"{tr_title(l['title'])} ({no}) is repealed", a, slug
                if a["s"] == "repealed":
                    return "ARTICLE_REPEALED", "the article is marked Mülga", a, slug
                return "OK", "", a, slug
        for slug in removed:
            l = self.laws[slug]
            a = l["arts"][kind].get(num) or l["arts"][kind].get(base)
            if a:
                whole = not main or self.laws[main[0]]["status"] != "in_force"
                return ("LAW_REPEALED" if whole else "ARTICLE_REPEALED"), f"listed in '{tr_title(l['title'])}'", a, slug
        if main and self.laws[main[0]]["status"] != "in_force":
            return "LAW_REPEALED", f"{tr_title(self.laws[main[0]]['title'])} ({no}) is repealed", None, main[0]
        if not main:
            return "LAW_REPEALED", f"only repealed provisions of law {no} remain", None, (removed or [None])[0]
        l = self.laws[main[0]]
        nums = {int(k.split("/")[0]) for k in l["arts"][kind]} or {0}
        gapless = len(nums) >= max(nums)               # our parse found every number 1..max, so a miss is a real miss
        if int(base) > max(nums) or gapless:
            what = {"madde": "articles", "ek": "additional articles", "gecici": "provisional articles"}[kind]
            return "NO_SUCH_ARTICLE", f"law {no} has {max(nums)} {what}", None, main[0]
        return "UNVERIFIED", "gap in our copy of this law", None, main[0]

    # -------------------------------------------------------------- extraction
    def extract(self, text: str) -> list[Citation]:
        cits: list[Citation] = []
        taken: list[tuple[int, int]] = []

        def free(a, b):
            return all(b <= x or a >= y for x, y in taken)

        def add(m, art_text, no, how, clash, name, a_start):
            kind, num = self.article_key(art_text)
            cits.append(self._make(text, m.start(), m.end(), no, kind, num, clash, name))
            taken.append((m.start(), m.end()))
            # "TBK m. 344 ve 347", "m. 315, 350 and 352"
            pos = m.end()
            while True:
                mm = self.re_more.match(ft[pos:])
                if not mm:
                    break
                n2 = mm.group("num") + ("/" + mm.group("let").upper() if mm.group("let") else "")
                s2, e2 = pos + mm.start("num"), pos + mm.end()
                if kind == "madde" and re.match(r"^\s*(?:-|–|ila|to)", mm.group(0)) and int(mm.group("num")) - int(num.split("/")[0]) in range(1, 30):
                    for k in range(int(num.split("/")[0]) + 1, int(mm.group("num")) + 1):
                        cits.append(self._make(text, s2, e2, no, kind, str(k), clash, name))
                else:
                    cits.append(self._make(text, s2, e2, no, kind, n2, clash, name))
                taken.append((s2, e2))
                pos = e2

        ft = fold(text)
        for rx in (self.re_art_law, self.re_law_art):
            for m in rx.finditer(ft):
                if not free(m.start(), m.end()):
                    continue
                g = m.groupdict()
                if rx is self.re_law_art and g.get("abbr") and not re.search(r"\d", m.group("art")):
                    continue
                no, how, clash = self.resolve(m)
                if no is None and g.get("kanun"):
                    continue
                add(m, m.group("art"), no, how, clash, g.get("name") or g.get("name2") or g.get("abbr"), m.start("art"))
        # anaphora: "aynı Kanunun 25. maddesi" -> the closest law cited before it
        for m in self.re_anaphora.finditer(ft):
            if not free(m.start(), m.end()):
                continue
            prev = [c for c in cits if c.kind == "statute" and c.end <= m.start() and c.law_no]
            if prev:
                p = max(prev, key=lambda c: c.end)
                kind, num = self.article_key(m.group("art") or m.group("art2"))
                c = self._make(text, m.start(), m.end(), p.law_no, kind, num, "", p.law_title)
                if c.verdict in BAD:                       # an inferred law is never grounds for an accusation
                    c.note, c.verdict = f"{c.verdict} if the law is {p.law_no}; law inferred from the previous citation", "UNVERIFIED"
                else:
                    c.note = (c.note + "; " if c.note else "") + "law taken from the previous citation"
                cits.append(c); taken.append((m.start(), m.end()))
        for m in self.re_law_only.finditer(ft):
            if not free(m.start(), m.end()):
                continue
            no, how, clash = self.resolve(m)
            name = m.groupdict().get("name")
            if clash:
                verdict, note = "NUMBER_NAME_CLASH", clash
            elif no not in self.by_no:
                verdict, note = "UNKNOWN_LAW", f"no law numbered {no} in the index"
            else:
                main, _ = self.pick_slugs(no, name)
                verdict, note = ("OK", "") if main and self.laws[main[0]]["status"] == "in_force" else ("LAW_REPEALED", f"law {no} is repealed")
            slug = (self.pick_slugs(no, name)[0] or [None])[0] if no in self.by_no else None
            law = self.laws.get(slug) if slug else None
            cits.append(Citation("statute", text[m.start():m.end()], m.start(), m.end(), no, tr_title(law["title"]) if law else None,
                                 None, verdict, note or "law cited without an article", law["source"] if law else None))
            taken.append((m.start(), m.end()))
        for m in DECISION.finditer(text):
            if free(m.start(), m.end()):
                cits.append(self._decision(m))
        cits.sort(key=lambda c: (c.start, c.article or ""))
        return cits

    def _make(self, text, s, e, no, kind, num, clash, name) -> Citation:
        verdict, note, art, slug = self.verify(no, kind, num, clash, name)
        label = num if kind == "madde" else ("ek " if kind == "ek" else "geçici ") + num
        law = self.laws.get(slug) if slug else None
        return Citation("statute", text[s:e], s, e, no, tr_title(law["title"]) if law else None, label, verdict, note,
                        law["source"] if law else None, (art or {}).get("t"))

    @staticmethod
    def _decision(m) -> Citation:
        g = m.groupdict()
        ey, en, ky = g.get("ey") or g.get("ey2") or g.get("by"), g.get("en") or g.get("en2") or g.get("bn"), g.get("ky") or g.get("ky2")
        bad = []
        if ey and not (1950 <= int(ey) <= 2026):
            bad.append(f"year {ey} out of range")
        if ky and not (1950 <= int(ky) <= 2026):
            bad.append(f"decision year {ky} out of range")
        if ey and ky and int(ky) < int(ey):
            bad.append("decision year before file year")
        return Citation("decision", m.group(0), m.start(), m.end(), verdict="DECISION_MALFORMED" if bad else "DECISION_UNVERIFIED",
                        note="; ".join(bad) or "case-law existence is not checked offline yet")

    def check(self, text: str) -> dict:
        cits = self.extract(text)
        st = [c for c in cits if c.kind == "statute"]
        return {"citations": [asdict(c) for c in cits],
                "statutes": len(st), "ok": sum(c.verdict == "OK" for c in st),
                "bad": sum(c.verdict in BAD for c in st), "unverified": sum(c.verdict == "UNVERIFIED" for c in st),
                "decisions": sum(c.kind == "decision" for c in cits),
                "index": self.meta}


@lru_cache(maxsize=1)
def default_checker() -> Checker:
    return Checker()


if __name__ == "__main__":
    t = Path(sys.argv[1]).read_text() if len(sys.argv) > 1 and Path(sys.argv[1]).exists() else (" ".join(sys.argv[1:]) or sys.stdin.read())
    r = default_checker().check(t)
    for c in r["citations"]:
        lab = f"{c['law_title'] or c['law_no']} m. {c['article']}" if c["kind"] == "statute" else "decision"
        print(f"{c['verdict']:<20} {lab:<45} «{c['text'][:60]}»  {c['note']}")
    print(f"\n{r['statutes']} statute citations: {r['ok']} OK, {r['bad']} wrong, {r['unverified']} unverified; {r['decisions']} case-law citations (not checked)")
