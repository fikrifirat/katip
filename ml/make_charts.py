"""Draw the README charts (light + dark SVG) from metrics/accuracy.json and metrics/formats.json."""
import json
from pathlib import Path
M = Path(__file__).resolve().parents[1] / "metrics"
acc = json.loads((M / "accuracy.json").read_text()); fmt = json.loads((M / "formats.json").read_text())
NAMES = {"PERSON": "Ad soyad / name", "ADDRESS": "Adres / address", "TCKN": "T.C. kimlik no", "VKN": "VKN (tax no)",
         "IBAN": "IBAN", "PHONE": "Telefon / phone", "EMAIL": "E-posta / email", "BIRTH_DATE": "Doğum tarihi / birth date",
         "PLATE": "Plaka / plate", "CREDIT_CARD": "Kart no / card", "HEALTH": "Sağlık (md. 6) / health", "UNION": "Sendika / union"}
THEMES = {"light": dict(bg="#ffffff", fg="#1f2328", mute="#59636e", grid="#d1d9e0", bar="#2f7d4f", bar2="#c08a2e"),
          "dark": dict(bg="#0d1117", fg="#e6edf3", mute="#9198a1", grid="#3d444d", bar="#4fb07a", bar2="#d9a74a")}
esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")

def accuracy_svg(t):
    b = acc["sets"]["blind"]["types"]
    rows = sorted(((k, v) for k, v in b.items() if v["gold"] >= 5), key=lambda kv: -kv[1]["gold"])
    W, L, R, top, h = 720, 210, 150, 58, 26; H = top + h * len(rows) + 40; bw = W - L - R
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
         f'<rect width="100%" height="100%" fill="{t["bg"]}" rx="8"/>',
         f'<text x="20" y="28" font-size="16" font-weight="600" fill="{t["fg"]}">Values found, by data type (blind set, 80 docs)</text>',
         f'<text x="20" y="46" font-size="12" fill="{t["mute"]}">Bulunan değerler, veri türüne göre. Default settings: rules + name tagger. Synthetic documents.</text>']
    for x in (0, 25, 50, 75, 100):
        X = L + bw * x / 100
        o.append(f'<line x1="{X}" y1="{top - 6}" x2="{X}" y2="{top + h * len(rows)}" stroke="{t["grid"]}"/>')
        o.append(f'<text x="{X}" y="{top + h * len(rows) + 16}" font-size="11" fill="{t["mute"]}" text-anchor="middle">{x}%</text>')
    for i, (k, v) in enumerate(rows):
        y = top + i * h; r = v["found"] / v["gold"]; fp = v["false"]
        o.append(f'<text x="{L - 10}" y="{y + 17}" font-size="12.5" fill="{t["fg"]}" text-anchor="end">{esc(NAMES.get(k, k))}</text>')
        o.append(f'<rect x="{L}" y="{y + 5}" width="{bw * r:.1f}" height="{h - 10}" rx="3" fill="{t["bar"]}"/>')
        note = f'{v["found"]}/{v["gold"]}' + (f' · {fp} extra' if fp else '')
        o.append(f'<text x="{L + bw + 8}" y="{y + 17}" font-size="12" fill="{t["fg"]}">{r * 100:.1f}% <tspan fill="{t["mute"]}">{note}</tspan></text>')
    o.append("</svg>"); return "\n".join(o)

def speed_svg(t):
    rows = fmt["formats"]; W, L, R, top, h = 720, 170, 200, 58, 30; H = top + h * len(rows) + 52; bw = W - L - R
    mx = 5000
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
         f'<rect width="100%" height="100%" fill="{t["bg"]}" rx="8"/>',
         f'<text x="20" y="28" font-size="16" font-weight="600" fill="{t["fg"]}">Time per document and values still readable after masking</text>',
         f'<text x="20" y="46" font-size="12" fill="{t["mute"]}">Belge başına süre ve maskeden sonra okunabilen değerler. Open, detect, mask and re-check, all in the browser engine.</text>']
    for x in (0, 1000, 2000, 3000, 4000, 5000):
        X = L + bw * x / mx
        o.append(f'<line x1="{X}" y1="{top - 6}" x2="{X}" y2="{top + h * len(rows)}" stroke="{t["grid"]}"/>')
        o.append(f'<text x="{X}" y="{top + h * len(rows) + 16}" font-size="11" fill="{t["mute"]}" text-anchor="middle">{x / 1000:g} s</text>')
    for i, r in enumerate(rows):
        y = top + i * h; ocr = "Photo" in r["format"] or "Scan" in r["format"]
        leak = r["readable_after"] / r["values"] * 100
        o.append(f'<text x="{L - 10}" y="{y + 19}" font-size="12.5" fill="{t["fg"]}" text-anchor="end">{esc(r["format"])}</text>')
        o.append(f'<rect x="{L}" y="{y + 6}" width="{max(2, bw * r["ms_per_doc"] / mx):.1f}" height="{h - 12}" rx="3" fill="{t["bar2"] if ocr else t["bar"]}"/>')
        o.append(f'<text x="{L + bw + 8}" y="{y + 19}" font-size="12" fill="{t["fg"]}">{r["ms_per_doc"] / 1000:.2f} s <tspan fill="{t["mute"]}">· {leak:.1f}% still readable</tspan></text>')
    o.append(f'<text x="20" y="{H - 12}" font-size="11" fill="{t["mute"]}">Amber = OCR (Tesseract, Turkish). Rules only, 4-core cloud VM, 2026-11-10. Laptop timings will differ.</text>')
    o.append("</svg>"); return "\n".join(o)

for name, t in THEMES.items():
    (M / f"accuracy-{name}.svg").write_text(accuracy_svg(t)); (M / f"speed-{name}.svg").write_text(speed_svg(t))
print("ok")
