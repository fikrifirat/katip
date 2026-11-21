"""docs/katip_nl.zip and katip_nl_labels.json must match lab/nl/katip_nl (rebuild with src/build_nl.py)."""
import subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_nl_bundle_in_sync():
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, str(ROOT / "src/build_nl.py"), d], check=True, capture_output=True)
        for f in ("katip_nl.zip", "katip_nl_labels.json"):
            assert (Path(d) / f).read_bytes() == (ROOT / "docs" / f).read_bytes(), f"{f} is stale: run python src/build_nl.py"


def test_nl_bundle_detects_from_zip():
    import zipfile
    with tempfile.TemporaryDirectory() as d:
        zipfile.ZipFile(ROOT / "docs/katip_nl.zip").extractall(d)
        sys.path.insert(0, d)
        try:
            for m in [m for m in sys.modules if m.startswith("katip_nl")]:
                del sys.modules[m]
            from katip_nl import recognizers
            text = (ROOT / "src/tests/letters/ind_besluit.txt").read_text()
            found = {s["entity_type"]: s["text"] for s in recognizers.detect(text)}
            assert found.get("BSN") == "111222333"
            assert found.get("V_NUMBER") == "3012345678"
            assert "PERSON" in found
        finally:
            sys.path.remove(d)
            for m in [m for m in sys.modules if m.startswith("katip_nl")]:
                del sys.modules[m]
