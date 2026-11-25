"""Katip engine: Katip's masking and sources as a background service on this computer, like Docker's engine.

One process serves a small HTTP API on 127.0.0.1. The menu bar app, Klasör, Kalkan and the command line
are its clients. It never listens on another address, every call needs the token in ~/.katip/engine.json
(readable only by this user), and it refuses calls from web pages. On macOS it runs as a launchd agent that
starts on demand and exits when idle, so it holds no memory while nobody uses it.

    katip-engine install     register the launchd agent (no admin rights needed)
    katip-engine start       start it now
    katip-engine status      is it running, which models are loaded, how much memory
    echo "Davacı Ahmet YILMAZ" | katip-engine mask
    katip-engine stop
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"
# Tests and the screenshot tour run their own agent (KATIP_AGENT_LABEL), so they never take over the lawyer's.
LABEL = os.environ.get("KATIP_AGENT_LABEL") or "com.fikrifirat.katip.engine"

# Inside Katip.app nothing may be written: macOS treats a write into an app bundle as "modifying apps" (a
# permission prompt) and it breaks the app's signature. The bundle ships compiled files; never write new ones.
if getattr(sys, "frozen", False):
    sys.dont_write_bytecode = True
DEFAULT_PORT = 47390

# Cases can run for years, as in Klasör: the case keys outlive Kalkan's 30-day default.
os.environ.setdefault("KATIP_VAULT_DAYS", "3650")


def _find_kalkan() -> None:
    """katip_kalkan comes from the connector folder of this repo, or from a frozen app's bundle."""
    try:
        import katip_kalkan  # noqa: F401
        return
    except ImportError:
        pass
    here = Path(__file__).resolve().parent
    for cand in (here.parent.parent / "connector", Path(getattr(sys, "_MEIPASS", here)) / "connector"):
        if (cand / "katip_kalkan").is_dir():
            sys.path.insert(0, str(cand))
            return
    raise ImportError("katip_kalkan not found: run from the katip repo or install connector/")


_find_kalkan()
