"""Build the distributables from this folder.

    python connector/build_bundle.py            # -> connector/dist/katip-kalkan.mcpb

1. Refreshes katip_kalkan/engine.zip from docs/katip_py.zip (the browser engine build).
2. Packs an MCPB bundle (zip: manifest.json + server/katip_kalkan/...) for one-click install
   in Claude Desktop. The Claude plugin needs no build: it is this folder (see
   .claude-plugin/plugin.json and the repo-level .claude-plugin/marketplace.json).

`cryptography` is optional and not bundled (native wheels per platform); without it the
vault is memory-only. Bundling per-platform wheels into server/lib is the next step.
"""
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = HERE.parent / "docs" / "katip_py.zip"
eng = HERE / "katip_kalkan" / "engine.zip"
if src.exists() and (not eng.exists() or src.read_bytes() != eng.read_bytes()):
    shutil.copyfile(src, eng)
    print("engine.zip refreshed from docs/katip_py.zip")

dist = HERE / "dist"
dist.mkdir(exist_ok=True)
out = dist / "katip-kalkan.mcpb"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(HERE / "manifest.json", "manifest.json")
    z.write(HERE / "PRIVACY.md", "PRIVACY.md")
    z.write(HERE / ".claude-plugin" / "icon.png", "icon.png")
    for f in sorted((HERE / "katip_kalkan").rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            z.write(f, "server/" + str(f.relative_to(HERE)))
print(out, out.stat().st_size // 1024, "KB")
