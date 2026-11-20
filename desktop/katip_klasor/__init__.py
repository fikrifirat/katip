"""Katip Klasör: a desktop app that masks the documents a lawyer drops into a folder, on this computer.

The masking itself is Katip Kalkan's (connector/katip_kalkan): same detection, same case vault, same
leak check. This package adds the folder workflow, the review queue, the audit log and the window.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

# Cases can run for years, so the case keys outlive Kalkan's 30-day default (Ayarlar > Dosyayı unut deletes one).
os.environ.setdefault("KATIP_VAULT_DAYS", "3650")


def _find_kalkan() -> None:
    """katip_kalkan comes from the connector folder of this repo, or from the frozen app's bundle."""
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
