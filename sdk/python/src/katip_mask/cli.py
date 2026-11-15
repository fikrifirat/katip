"""katip-mask command line: mask, detect, restore, download.

    katip-mask mask dilekce.txt --profile ai --model mini > maskeli.txt
    katip-mask mask dilekce.txt --json > result.json          # text, spans and the placeholder mapping
    katip-mask restore answer.txt --mapping result.json        # put the original values back
    katip-mask detect dilekce.txt
    katip-mask download mini                                   # fetch and verify a model for offline use
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .api import PROFILES, Masker, restore
from .models import MODELS, download_model
from .safety import LeakError


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.buffer.read().decode("utf-8")
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Turkish text on consoles that default to cp1252/cp857
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="katip-mask", description="Mask Turkish personal data (KVKK) on this machine.")
    ap.add_argument("--version", action="version", version=f"katip-mask {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("mask", "detect"):
        p = sub.add_parser(name, help=f"{name} a UTF-8 text file ('-' for stdin)")
        p.add_argument("file")
        p.add_argument("--profile", choices=list(PROFILES), default="court")
        p.add_argument("--model", help=f"{', '.join(MODELS)} or a model folder (default: rules only)")
        p.add_argument("--threshold", type=float, default=None)
        p.add_argument("--allow", action="append", default=[], help="term never masked (repeatable)")
        p.add_argument("--deny", action="append", default=[], help="term always masked (repeatable)")
        p.add_argument("--address", choices=["street", "full"], help="override the profile's address rule")
        if name == "mask":
            p.add_argument("--style", choices=["label", "block"], default="label")
            p.add_argument("--json", action="store_true", help="print text, spans and mapping as JSON")
    r = sub.add_parser("restore", help="put original values back using a mapping from `mask --json`")
    r.add_argument("file")
    r.add_argument("--mapping", required=True, help="JSON file from `mask --json` (or a plain mapping object)")
    d = sub.add_parser("download", help="download and verify a model for offline use")
    d.add_argument("model", choices=list(MODELS))
    a = ap.parse_args(argv)

    if a.cmd == "download":
        print(download_model(a.model, progress=lambda m: print(m, file=sys.stderr)))
        return 0
    if a.cmd == "restore":
        with open(a.mapping, encoding="utf-8") as f:
            m = json.load(f)
        sys.stdout.write(restore(_read(a.file), m.get("mapping", m)))
        return 0
    opts = dict(model=a.model, allow=a.allow, deny=a.deny, address_detail=a.address,
                progress=lambda m: print(m, file=sys.stderr))
    if a.threshold is not None:
        opts["threshold"] = a.threshold
    if a.cmd == "mask":
        opts["style"] = a.style
    masker = Masker(a.profile, **opts)
    text = _read(a.file)
    if a.cmd == "detect":
        for s in masker.detect(text):
            print(json.dumps(s.to_dict(), ensure_ascii=False, separators=(",", ":")))
        return 0
    try:
        res = masker.mask(text)
    except LeakError as e:
        print(f"katip-mask: {e}", file=sys.stderr)
        return 3
    if a.json:
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=1))
    else:
        sys.stdout.write(res.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
