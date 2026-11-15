"""Vendor Katip's detection engine into the Python SDK, unchanged except for import paths.

The engine is the pure-Python bundle that the browser demo runs in Pyodide and that Katip Kalkan
runs on the desktop (docs/katip_py.zip, built by src/build_core.py). The SDK must run the same code,
so this script copies it file by file and only rewrites imports, so the vendored copy never installs
a top-level ``katip_redact`` or ``presidio_analyzer`` package into the user's environment.

    python sdk/tools/sync_engine.py           # write sdk/python/src/katip_mask/_engine/
    python sdk/tools/sync_engine.py --check   # CI: fail if the vendored copy is stale

Every rewrite is listed below and asserted, so a change in the source that the rewrites no longer
fit fails loudly instead of producing a silently different engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_ZIP = ROOT / "docs" / "katip_py.zip"
DST = ROOT / "sdk" / "python" / "src" / "katip_mask" / "_engine"
PKG = "katip_mask._engine"

HEADER = ("# Vendored from docs/katip_py.zip ({name}) by sdk/tools/sync_engine.py. Do not edit here:\n"
          "# change the engine at its source and re-run the sync, so the SDK, the demo and Kalkan stay identical.\n")

# zip member -> vendored file name
FILES = {
    "katip_redact/textutil.py": "textutil.py",
    "katip_redact/recognizers.py": "recognizers.py",
    "katip_redact/_analyzer_core.py": "_analyzer_core.py",
    "presidio_analyzer/__init__.py": "_presidio_shim.py",
    "local_detect.py": "local_detect.py",
}
DATA = ("ambiguous_first.txt", "common_words.txt", "districts.txt", "first_names.txt", "last_names.txt",
        "provinces.txt", "stopwords_caps.txt")

# (file, old, new, expected count or None for "at least one")
REWRITES = [
    ("recognizers.py", "from presidio_analyzer import EntityRecognizer, RecognizerResult",
     f"from {PKG}._presidio_shim import EntityRecognizer, RecognizerResult", 1),
    ("local_detect.py", "from presidio_analyzer import RecognizerResult",
     f"from {PKG}._presidio_shim import RecognizerResult", 1),
    ("local_detect.py", 'resources.files("katip_redact.data")', f'resources.files("{PKG}.data")', 1),
    ("local_detect.py", "from katip_redact.", f"from {PKG}.", None),
]


def build() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(SRC_ZIP) as z:
        for member, name in FILES.items():
            text = z.read(member).decode("utf-8")
            for f, old, new, n in REWRITES:
                if f != name:
                    continue
                found = text.count(old)
                if (n is None and found == 0) or (n is not None and found != n):
                    sys.exit(f"sync_engine: expected {n or '>=1'} x {old!r} in {member}, found {found}")
                text = text.replace(old, new)
            for bad in ("from katip_redact", "import katip_redact", "from presidio_analyzer", "import presidio_analyzer",
                        '"katip_redact.'):
                if bad in text:
                    sys.exit(f"sync_engine: {bad!r} still in {name}: add a rewrite")
            out[name] = (HEADER.format(name=member) + text).encode("utf-8")
        for d in DATA:
            out[f"data/{d}"] = z.read(f"katip_redact/data/{d}")
    out["__init__.py"] = (b'"""Katip detection engine, vendored unchanged from docs/katip_py.zip (see sdk/tools/sync_engine.py)."""\n')
    out["data/__init__.py"] = b""
    out["SOURCE.json"] = (json.dumps({
        "source": "docs/katip_py.zip",
        "sha256": hashlib.sha256(SRC_ZIP.read_bytes()).hexdigest(),
        "files": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(out.items())},
    }, indent=1) + "\n").encode()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the vendored copy differs")
    a = ap.parse_args()
    want = build()
    if a.check:
        stale = [k for k, v in want.items() if not (DST / k).exists() or (DST / k).read_bytes() != v]
        extra = [p.relative_to(DST).as_posix() for p in DST.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                 and p.relative_to(DST).as_posix() not in want]
        if stale or extra:
            sys.exit(f"vendored engine is out of date (run sdk/tools/sync_engine.py): {stale + extra}")
        print("vendored engine matches docs/katip_py.zip")
        return
    for k, v in want.items():
        p = DST / k
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(v)
    print(f"wrote {len(want)} files to {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
