"""Start the local MCP server, with the model runtime when it can be had.

The connector itself is standard library only. The name model needs onnxruntime and
numpy, and the encrypted vault needs cryptography. If they are missing and `uv` is
installed, we re-run ourselves under `uv run --with ...`, which fetches them once from
PyPI into uv's cache (and Python 3.12 itself, if missing). Otherwise the server still starts: rules only, memory-only vault,
and katip_status says so.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

# Exact versions, tested together (tests/test_kalkan.py), so a new upstream release can't change what runs.
# pymupdf: PDFs; rapidocr: PaddleOCR for scans. Bump them together and rerun the tests.
DEPS = {"onnxruntime": "onnxruntime==1.32.0", "numpy": "numpy==2.5.4", "cryptography": "cryptography==50.0.2",
        "pymupdf": "pymupdf==2.1", "rapidocr": "rapidocr==3.10.0"}
PYTHON = "3.12"  # uv fetches this Python once if the computer doesn't have it


def main() -> None:
    missing = [spec for mod, spec in DEPS.items() if importlib.util.find_spec(mod) is None]
    # Claude Desktop starts servers with a short PATH that often lacks Homebrew and ~/.local/bin
    uv = shutil.which("uv") or next((str(c) for c in (Path.home() / ".local/bin/uv", Path.home() / ".cargo/bin/uv",
                                                     Path("/opt/homebrew/bin/uv"), Path("/usr/local/bin/uv"),
                                                     Path.home() / ".local/bin/uv.exe", Path.home() / ".cargo/bin/uv.exe")
                                     if c.exists()), None)
    if missing and uv and not os.environ.get("KATIP_LAUNCHED") and os.environ.get("KATIP_AUTO_DEPS", "1") != "0":
        os.environ["KATIP_LAUNCHED"] = "1"
        root = str(Path(__file__).resolve().parent.parent)  # so the uv-run Python finds katip_kalkan
        os.environ["PYTHONPATH"] = os.pathsep.join(filter(None, [root, os.environ.get("PYTHONPATH")]))
        args = [uv, "run", "--quiet", "--no-project", "--python", PYTHON]
        for spec in missing:
            args += ["--with", spec]
        args += ["python", "-m", "katip_kalkan.local_server", *sys.argv[1:]]
        os.execv(uv, args)
    from .local_server import main as serve
    serve()


if __name__ == "__main__":
    main()
