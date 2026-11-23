"""Build law_index.json (article -> paragraph -> point text) for GDPR and the EU AI Act.

  python eval/build_law_index.py --fetch     # download the article pages once (polite, ~4 min)
  python eval/build_law_index.py             # parse the cached pages into eval/law_index.json

Sources: gdpr-info.eu (GDPR, Regulation (EU) 2016/679) and artificialintelligenceact.eu (Regulation
(EU) 2024/1689), one page per article, which mirror the Official Journal text. EU legislation may be
reused freely (Commission Decision 2011/833/EU). The AI Act pages show the text as amended by the
Digital Omnibus on AI, Regulation (EU) 2026/1744 (in force 27 July 2026); we keep the amended text.
KVKK: consolidated text of Law No. 6698 from mevzuat.gov.tr (PDF, read with pdftotext).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache" / "katip-uyum-law"
KVKK_PDF = "https://www.mevzuat.gov.tr/mevzuatmetin/1.5.6698.pdf"
SOURCES = {"gdpr": ("https://gdpr-info.eu/art-{i}-gdpr/", 99),
           "aiact": ("https://artificialintelligenceact.eu/article/{i}/", 113)}


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    for law, (url, n) in SOURCES.items():
        for i in range(1, n + 1):
            f = CACHE / f"{law}-{i}.html"
            if f.exists() and f.stat().st_size > 2000:
                continue
            req = urllib.request.Request(url.format(i=i), headers={"User-Agent": "katip-uyum-eval"})
            f.write_bytes(urllib.request.urlopen(req, timeout=30).read())
            time.sleep(0.5)
    f = CACHE / "kvkk-6698.pdf"
    if not f.exists():
        req = urllib.request.Request(KVKK_PDF, headers={"User-Agent": "katip-uyum-eval"})
        f.write_bytes(urllib.request.urlopen(req, timeout=60).read())


TR_LETTERS = "a b c ç d e f g ğ h ı i j k l m n o ö p r s ş t u ü v y z".split()


def parse_kvkk() -> dict[str, dict[str, str]]:
    """KVKK (Law No. 6698, consolidated text from mevzuat.gov.tr) -> {"9": {"1": ..., "3.d": ...}}."""
    import subprocess
    txt = subprocess.run(["pdftotext", "-layout", str(CACHE / "kvkk-6698.pdf"), "-"], capture_output=True,
                         text=True, check=True).stdout
    arts: dict[str, dict[str, str]] = {}
    art = para = point = None
    for line in txt.splitlines():
        t = line.strip()
        m = re.match(r"(?:GEÇİCİ )?MADDE (\d+)\s*[-–]\s*(.*)", t)
        if m and not t.startswith("GEÇİCİ"):
            art, para, point = m.group(1), None, None
            arts[art] = {}
            t = m.group(2)
            t = re.sub(r"^\((Değişik|Ek|Mülga)[^)]*\)\s*", "", t)
        elif t.startswith("GEÇİCİ MADDE"):
            art = None
        if art is None or not t:
            continue
        m = re.match(r"^\((\d+)\)\s*(.*)", t)
        if m:
            para, point = m.group(1), None
            arts[art][para] = re.sub(r"^\((Değişik|Ek|Mülga)[^)]*\)\s*", "", m.group(2))
            continue
        m = re.match(r"^([a-zçğıöşü])\)\s*(.*)", t)
        if m and para and m.group(1) in TR_LETTERS:
            point = m.group(1)
            arts[art][f"{para}.{point}"] = m.group(2)
            continue
        key = f"{para}.{point}" if point else (para or "0")
        arts[art][key] = (arts[art].get(key, "") + " " + t).strip()
    return arts


class _Article(HTMLParser):
    """Collect top-level list items (paragraphs) and nested list items (points) of the article body."""

    def __init__(self, start_marker):
        super().__init__(convert_charrefs=True)
        self.start_marker, self.on, self.depth, self.done = start_marker, False, 0, False
        self.paras: list[dict] = []
        self.free: list[str] = []
        self.cur = None  # ("p", idx) or ("pt", para_idx, point_idx)
        self.div_depth = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.done:
            return
        if not self.on:
            if tag == "div" and self.start_marker in (a.get("class") or ""):
                self.on, self.div_depth = True, 1
            return
        if tag in ("sup", "script", "style"):
            self.skip += 1
        if tag == "div":
            self.div_depth += 1
        if tag == "ol":
            self.depth += 1
        if tag == "li":
            if self.depth == 1:
                self.paras.append({"text": "", "points": []})
                self.cur = ("p", len(self.paras) - 1)
            elif self.depth >= 2 and self.paras:
                self.paras[-1]["points"].append("")
                self.cur = ("pt", len(self.paras) - 1, len(self.paras[-1]["points"]) - 1)

    def handle_endtag(self, tag):
        if not self.on or self.done:
            return
        if tag in ("sup", "script", "style"):
            self.skip = max(0, self.skip - 1)
        if tag == "ol":
            self.depth -= 1
            if self.depth == 1 and self.paras:
                self.cur = ("p", len(self.paras) - 1)
        if tag == "div":
            self.div_depth -= 1
            if self.div_depth == 0:
                self.done = True

    def handle_data(self, data):
        if not self.on or self.done or self.skip:
            return
        if self.cur is None or self.depth == 0:
            self.free.append(data)
        elif self.cur[0] == "p":
            self.paras[self.cur[1]]["text"] += data
        else:
            self.paras[self.cur[1]]["points"][self.cur[2]] += data


def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


LETTERS = "abcdefghijklmnopqrstuvwxyz"
_TIP = re.compile(r'<span class="term-tip">.*?term-tip-src">[^<]*</span></span>', re.S)
_PARA = re.compile(r'<div class="para depth-\d[^"]*"[^>]*? id="p-article-\d+-([^"]+)">(.*?)(?=<div class="para depth-|<div class="item-|</article>|<footer)', re.S)


class _NoTips(HTMLParser):
    """Text of a fragment, skipping glossary pop-ups (span.term-tip) and hidden/label spans."""

    SKIP = ("term-tip", "para-label", "om-badge")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.out = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "img", "input", "hr", "meta", "link"):
            return
        cls = dict(attrs).get("class") or ""
        skip = any(c in cls.split() for c in self.SKIP) or tag in ("button", "script", "style")
        self.stack.append(skip or (bool(self.stack) and self.stack[-1]))

    def handle_endtag(self, tag):
        if tag in ("br", "img", "input", "hr", "meta", "link"):
            return
        if self.stack:
            self.stack.pop()

    def handle_data(self, d):
        if not (self.stack and self.stack[-1]):
            self.out.append(d)


def _text_without_tips(fragment: str) -> str:
    p = _NoTips()
    p.feed(fragment)
    return " ".join(p.out)


def parse(law, i) -> dict[str, str]:
    """Flat map: "1" -> paragraph 1, "1.a" -> point (a), "1.c.i" -> sub-point; "0" -> unnumbered text."""
    raw = (CACHE / f"{law}-{i}.html").read_text(encoding="utf-8", errors="replace")
    out: dict[str, str] = {}
    if law == "aiact":
        for key, body in _PARA.findall(raw):
            # The site shows the text as amended by the Digital Omnibus on AI (Regulation (EU) 2026/1744)
            # first, then the pre-amendment text in a hidden span: keep only the text in force.
            body = re.sub(r"<[^>]*$", "", body.split("om-ver om-old")[0])
            text = _clean(_text_without_tips(body))
            text = re.sub(r"^\(?[0-9a-z]+[.)]\s*", "", text)
            if text:  # continuation sub-paragraphs reuse the paragraph's id
                out[key] = (out.get(key, "") + " " + text).strip()
        return out
    p = _Article("entry-content")
    p.feed(raw)
    paras = [x for x in p.paras if _clean(x["text"]) or x["points"]]
    if not paras:
        out["0"] = _clean(" ".join(p.free))
    for n, x in enumerate(paras, 1):
        out[str(n)] = _clean(x["text"])
        for k, t in enumerate(x["points"]):
            out[f"{n}.{LETTERS[k]}"] = _clean(t)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        fetch()
    out = {law: {str(i): parse(law, i) for i in range(1, n + 1)} for law, (_, n) in SOURCES.items()}
    out["kvkk"] = parse_kvkk()
    (HERE / "law_index.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print("articles:", {k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    main()
