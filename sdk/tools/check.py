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


def derived_profiles() -> dict:
    """profiles.json with entity lists and labels taken from the engine and Kalkan's PROFILES, so the
    packages cannot drift from the connector."""
    import ast
    sys.path.insert(0, str(SDK / "python" / "src"))
    from katip_mask._engine import recognizers
    tree = ast.parse((SDK.parent / "connector" / "katip_kalkan" / "engine.py").read_text(encoding="utf-8"))
    ns: dict = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") in ("CASE", "ANON", "PROFILES") for t in node.targets):
            exec(compile(ast.Module([node], []), "engine.py", "exec"), ns)
    spec = json.loads((SDK / "spec" / "profiles.json").read_text(encoding="utf-8"))
    extra_labels = {k: v for k, v in spec["labels_tr"].items() if k in ns["CASE"] + ns["ANON"]}
    spec["labels_tr"] = {**recognizers.ENTITY_LABELS_TR, **extra_labels}
    for name, prof in spec["profiles"].items():
        k = ns["PROFILES"][name]
        prof["entities"] = [e for e in recognizers.ALL_ENTITIES if e not in k["drop"]] + k["extra"]
        prof["address_detail"] = k["addr"]
    return spec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    flag = ["--check"] if a.check else []
    bad = []
    if subprocess.call([sys.executable, str(SDK / "tools" / "sync_engine.py"), *flag]) != 0:
        bad.append("sync_engine.py")
    prof = json.dumps(derived_profiles(), ensure_ascii=False, indent=1) + "\n"
    if (SDK / "spec" / "profiles.json").read_text(encoding="utf-8") != prof:
        if a.check:
            bad.append("spec/profiles.json differs from the engine and Kalkan's PROFILES")
        else:
            (SDK / "spec" / "profiles.json").write_text(prof, encoding="utf-8")
    for tool in ("gen_js_tables.py",):
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
