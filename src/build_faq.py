"""Turn FAQ.tr.md / FAQ.md into plain HTML pages for GitHub Pages (src/site/sss.html, src/site/faq.html).

  python src/build_faq.py           # rewrite the pages
  python src/build_faq.py --check   # fail if they are out of date with the Markdown

Search engines and AI search tools read these pages; the app page itself is mostly an interactive tool.
Each page carries schema.org FAQPage data built from the same questions. Needs `pip install markdown`.
build_site.py copies src/site/ into the site as is, so run this after editing either FAQ file.
"""
import html, json, re, sys
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://fikrifirat.github.io/katip/"
BLOB = "https://github.com/fikrifirat/katip/blob/main/"
PAGES = {  # source, output, language, other language's page, labels
    "tr": ("FAQ.tr.md", "sss.html", "en", "faq.html", "Uygulamayı açın", "English", "Kaynak kod", "Bu sayfa FAQ.tr.md dosyasından üretilir."),
    "en": ("FAQ.md", "faq.html", "tr", "sss.html", "Open the app", "Türkçe", "Source code", "This page is generated from FAQ.md."),
}


def links(md: str) -> str:
    md = md.replace("(FAQ.md)", "(faq.html)").replace("(FAQ.tr.md)", "(sss.html)")
    md = re.sub(r"\]\(https://fikrifirat\.github\.io/katip/?\)", "](./)", md)
    # every other relative link points into the repository on GitHub
    return re.sub(r"\]\((?!https?:|#|\./|mailto:|faq\.html|sss\.html)([^)]+)\)", lambda m: f"]({BLOB}{m.group(1)})", md)


def plain(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def build(lang: str) -> str:
    src, out, other, other_page, open_app, other_name, source, note = PAGES[lang]
    md = links((ROOT / src).read_text(encoding="utf-8"))
    md = re.sub(r"^\*\*English\*\*.*\n|^\[English\].*\n", "", md, flags=re.M)  # language switch lives in the header
    body = markdown.markdown(md, extensions=["extra", "sane_lists", "toc"], output_format="html")
    title = plain(re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S).group(1))
    intro = plain(re.search(r"</h1>\s*<p>(.*?)</p>", body, re.S).group(1))
    qa = []
    for m in re.finditer(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|\Z)", body, re.S):
        qa.append({"@type": "Question", "name": plain(m.group(1)),
                   "acceptedAnswer": {"@type": "Answer", "text": plain(m.group(2))}})
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang, "url": SITE + out,
          "name": title, "about": {"@id": SITE + "#app"}, "mainEntity": qa}
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(intro)}">
<link rel="canonical" href="{SITE}{out}">
<link rel="alternate" hreflang="{lang}" href="{SITE}{out}">
<link rel="alternate" hreflang="{other}" href="{SITE}{other_page}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(intro)}">
<meta property="og:url" content="{SITE}{out}">
<meta property="og:image" content="{SITE}og.png">
<meta property="og:type" content="article">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="mark.svg" type="image/svg+xml">
<link rel="stylesheet" href="style.css">
<style>.doc{{max-width:760px;margin:0 auto;padding:24px 16px 48px}}.doc h1{{font:700 30px/1.15 var(--display);letter-spacing:-.02em}}
.doc h2{{font:600 20px/1.3 var(--display);margin:32px 0 8px;text-transform:none;letter-spacing:-.01em;color:var(--ink)}}.doc a{{color:var(--accent)}}.doc code{{font:13px var(--code)}}
.doc .cta{{display:inline-block;margin:6px 0 4px;padding:8px 14px;border-radius:8px;background:var(--accent);color:var(--accent-ink);text-decoration:none;font-weight:600}}</style>
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
</script>
</head>
<body>
<header class="top"><a href="./" class="logo" style="text-decoration:none;color:inherit"><img src="mark.svg" width="30" height="30" alt=""><span class="word">Katip <span class="word2">Mask</span></span></a>
<span class="spacer"></span><a href="{other_page}" hreflang="{other}">{other_name}</a> <a href="https://github.com/fikrifirat/katip">GitHub</a></header>
<main class="doc">
{body}
<p><a class="cta" href="./{'?lang=en' if lang == 'en' else ''}">{open_app}</a></p>
</main>
<footer class="foot">{note} · <a href="https://github.com/fikrifirat/katip">{source}</a> · <a href="https://huggingface.co/spaces/f1k/kvkk-bench">KVKK-Bench</a></footer>
</body>
</html>
"""


if __name__ == "__main__":
    stale = []
    for lang in PAGES:
        path = Path(__file__).parent / "site" / PAGES[lang][1]
        page = build(lang)
        if "--check" in sys.argv:
            if not path.exists() or path.read_text(encoding="utf-8") != page:
                stale.append(path.name)
        else:
            path.write_text(page, encoding="utf-8")
            print("wrote", path)
    if stale:
        sys.exit(f"out of date: {', '.join(stale)} (run python src/build_faq.py)")
