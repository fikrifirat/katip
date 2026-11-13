"""Start the local MCP server, with the model runtime when it can be had.

The connector itself is standard library only. The name model needs onnxruntime and
numpy, and the encrypted vault needs cryptography. If they are missing and `uv` is
installed, we re-run ourselves under `uv run --with ...`, which fetches them once from
PyPI into uv's cache. Otherwise the server still starts: rules only, memory-only vault,
and katip_status says so.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys

DEPS = {"onnxruntime": "onnxruntime>=1.18", "numpy": "numpy", "cryptography": "cryptography>=42"}


def main() -> None:
    missing = [spec for mod, spec in DEPS.items() if importlib.util.find_spec(mod) is None]
    uv = shutil.which("uv")
    if missing and uv and not os.environ.get("KATIP_LAUNCHED") and os.environ.get("KATIP_AUTO_DEPS", "1") != "0":
        os.environ["KATIP_LAUNCHED"] = "1"
        args = [uv, "run", "--quiet", "--no-project", "--python", ">=3.10"]
        for spec in missing:
            args += ["--with", spec]
        args += ["python", "-m", "katip_kalkan.local_server", *sys.argv[1:]]
        os.execv(uv, args)
    from .local_server import main as serve
    serve()


if __name__ == "__main__":
    main()
