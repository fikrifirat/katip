"""Bundle the Dutch recognizers (lab/nl/katip_nl) for the browser.

  python src/build_nl.py [out dir, default docs]

Writes katip_nl.zip (recognizers.py and labels.py as-is, plus a minimal __init__ so nothing that does network
I/O is imported) and katip_nl_labels.json (placeholder tags and nl/en/tr labels for the page). The worker
loads the zip only when a Dutch document arrives; katip_py.zip, and the Kalkan engine.zip that must match it,
are not touched.
"""
import io, json, sys, zipfile
from pathlib import Path

here = Path(__file__).parent
pkg = here.parent / "lab/nl/katip_nl"
out = Path(sys.argv[1]) if len(sys.argv) > 1 else here.parent / "docs"
out.mkdir(parents=True, exist_ok=True)

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for f in ("recognizers.py", "labels.py"):
        info = zipfile.ZipInfo(f"katip_nl/{f}", (2026, 1, 1, 0, 0, 0))  # fixed date: same input, same bytes
        z.writestr(info, (pkg / f).read_bytes(), zipfile.ZIP_DEFLATED)
    z.writestr(zipfile.ZipInfo("katip_nl/__init__.py", (2026, 1, 1, 0, 0, 0)),
               '"""Katip NL recognizers, browser bundle (built by src/build_nl.py)."""\n')
(out / "katip_nl.zip").write_bytes(buf.getvalue())

sys.path.insert(0, str(pkg.parent))
from katip_nl.labels import LABELS  # noqa: E402
(out / "katip_nl_labels.json").write_text(json.dumps(
    {k: {"tag": v[0], "nl": v[1], "en": v[2], "tr": v[3]} for k, v in LABELS.items()}, ensure_ascii=False, indent=1) + "\n")
print("built", out / "katip_nl.zip", out / "katip_nl_labels.json")
