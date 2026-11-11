"""Build the static Katip Yerel demo site (GitHub Pages / Hugging Face static Space).

  python build_site.py <katip-redact dir> <node_modules dir> <out dir> [--source URL]

Runs build_core.py (Python bundle + vendored runtimes), then adds the demo UI,
sample documents with their answer keys, the model registry, transformers.js /
ONNX Runtime for NER models, version info, and writes the CSP from config.js.
"""
import argparse, datetime, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("nm"); ap.add_argument("out"); ap.add_argument("--source", default="")
a = ap.parse_args()
src, nm, out, here = Path(a.src), Path(a.nm), Path(a.out), Path(__file__).parent
subprocess.run([sys.executable, str(here / "build_core.py"), str(src), str(nm), str(out)], check=True)

for f in ("index.html", "app.js", "worker.js", "engine.js", "ner.js", "style.css", "config.js", "serve.py", "brand.js", "mark.svg"):
    shutil.copy2(here / f, out / f)
shutil.copytree(here / "fonts", out / "fonts", dirs_exist_ok=True)  # Geist (SIL OFL), self-hosted
(out / "README.md").unlink(missing_ok=True)
(out / ".nojekyll").write_text("")

# OCR models: both Turkish variants
for name, d in (("best_int", "4.0.0_best_int"), ("fast", "4.0.0")):
    (out / "vendor/tessdata" / name).mkdir(parents=True, exist_ok=True)
    shutil.copy2(nm / "@tesseract.js-data/tur" / d / "tur.traineddata.gz", out / "vendor/tessdata" / name / "tur.traineddata.gz")
(out / "vendor/tessdata/tur.traineddata.gz").unlink(missing_ok=True)

# transformers.js + ONNX Runtime (only loaded when a NER model is picked)
(out / "vendor/transformers").mkdir(parents=True, exist_ok=True)
shutil.copy2(nm / "@huggingface/transformers/dist/transformers.min.js", out / "vendor/transformers/transformers.min.js")
(out / "vendor/ort").mkdir(parents=True, exist_ok=True)
for f in ("ort-wasm-simd-threaded.asyncify.mjs", "ort-wasm-simd-threaded.asyncify.wasm"):
    shutil.copy2(nm / "onnxruntime-web/dist" / f, out / "vendor/ort" / f)

# samples: one synthetic document per type, every format it has, plus its answer key
TITLES = {"aydinlatma": "Aydınlatma metni", "bilirkisi": "Bilirkişi raporu", "dilekce": "Dava dilekçesi", "epikriz": "Epikriz (hastane)",
          "eposta": "E-posta yazışması", "fatura": "Fatura", "icra": "İcra takip talebi", "ihtarname": "İhtarname",
          "is_sozlesmesi": "İş sözleşmesi", "karar": "Mahkeme kararı", "kira_sozlesmesi": "Kira sözleşmesi", "mektup": "Mektup",
          "mesaj": "Mesajlaşma dökümü", "tutanak": "Tutanak", "vekaletname": "Vekaletname", "zabit": "Duruşma zaptı"}
ORDER = ["pdf", "scan.pdf", "png", "docx", "udf", "txt"]
blind = src / "eval/blind"
man = json.loads((blind / "manifest.json").read_text())
(out / "samples").mkdir(exist_ok=True)
picked = []
for t, title in TITLES.items():
    cands = [m for m in man if m["doc_type"] == t]
    if not cands: continue
    m = max(cands, key=lambda m: (len(m["formats"]), -int(m["id"].split("_")[-1])))
    for f in m["formats"]:
        shutil.copy2(blind / f"{m['id']}.{f}", out / "samples" / f"{m['id']}.{f}")
    gold = json.loads((blind / f"{m['id']}.gold.json").read_text())
    picked.append({"id": m["id"], "type": t, "title": title, "formats": [f for f in ORDER if f in m["formats"]],
                   "gold": [{"entity_type": g["entity_type"], "text": g["text"]} for g in gold]})
(out / "samples/manifest.json").write_text(json.dumps(picked, ensure_ascii=False, indent=1))

# models
reg = json.loads((here / "models/registry.json").read_text())
(out / "models").mkdir(exist_ok=True)
for m in reg:
    if m.get("ner") and (here / "models" / m["ner"]).exists():
        shutil.copytree(here / "models" / m["ner"], out / "models" / m["ner"], dirs_exist_ok=True)
    elif m.get("ner") and m.get("hosted"):
        m["elsewhere"] = True  # too big for GitHub (100 MB file limit): the card links to where it runs
(out / "models/registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1))

# version
rules_hash = hashlib.sha256((src / "katip_redact/recognizers.py").read_bytes() + (src / "katip_redact/textutil.py").read_bytes()).hexdigest()[:8]
(out / "version.json").write_text(json.dumps({"app": "0.3", "rules": f"v0.2+{rules_hash}", "built": datetime.date.today().isoformat(), "source": a.source}))

# CSP from config.js: own origin only, plus the report endpoint if one is set
cfg = (here / "config.js").read_text()
ep = re.search(r'reportEndpoint:\s*"([^"]*)"', cfg).group(1)
extra = " " + re.match(r"https://[^/]+", ep).group(0) if ep else ""
csp = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; "
       f"connect-src 'self' blob: data:{extra}; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; font-src 'self'; "
       "form-action 'none'; base-uri 'none'; frame-src 'none'; object-src 'none'")
html = (out / "index.html").read_text()
html = re.sub(r"<!--CSP-->.*?\n", f'<meta http-equiv="Content-Security-Policy" content="{csp}">\n', html, count=1)
(out / "index.html").write_text(html)
print("site built:", out, "samples:", len(picked), "report endpoint:", ep or "(none, e-mail draft only)")
