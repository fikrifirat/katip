"""One command that keeps the two packages in step with the engine and with each other.

    python sdk/tools/check.py          # regenerate everything derived from the engine and the spec
    python sdk/tools/check.py --check  # CI: fail if anything derived is stale or a version differs

Derived files: the vendored engine in the Python package (sync_engine.py), the JavaScript regex/char
tables and spec (gen_js_tables.py), and the spec copy inside the Python package. Versions that must
match: sdk/python/pyproject.toml, katip_mask.__version__, sdk/js/package.json and VERSION in index.ts.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SDK = Path(__file__).resolve().parents[1]
SPEC_FILES = ("profiles.json", "models.json")


def versions() -> dict[str, str]:
    def grab(path: str, pattern: str) -> str:
        m = re.search(pattern, (SDK / path).read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else "?"
    return {
        "python/pyproject.toml": grab("python/pyproject.toml", r'^version\s*=\s*"([^"]+)"'),
        "katip_mask.__version__": grab("python/src/katip_mask/__init__.py", r'^__version__\s*=\s*"([^"]+)"'),
        "js/package.json": json.loads((SDK / "js/package.json").read_text())["version"],
        "js/src/index.ts VERSION": grab("js/src/index.ts", r'^export const VERSION = "([^"]+)"'),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    flag = ["--check"] if a.check else []
    bad = []
    for tool in ("sync_engine.py", "gen_js_tables.py"):
        if subprocess.call([sys.executable, str(SDK / "tools" / tool), *flag]) != 0:
            bad.append(tool)
    for name in SPEC_FILES:
        src, dst = SDK / "spec" / name, SDK / "python/src/katip_mask/spec" / name
        if dst.read_bytes() != src.read_bytes():
            if a.check:
                bad.append(f"python/src/katip_mask/spec/{name} differs from spec/{name}")
            else:
                dst.write_bytes(src.read_bytes())
    v = versions()
    if len(set(v.values())) != 1:
        bad.append("versions differ: " + ", ".join(f"{k}={x}" for k, x in v.items()))
    for b in bad:
        print(f"stale or inconsistent: {b}", file=sys.stderr)
    if not bad:
        print(f"ok: engine, tables, spec and version {next(iter(v.values()))} in step")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
