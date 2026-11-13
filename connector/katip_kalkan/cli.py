"""Command line for the same features, plus `share` for the ChatGPT path.

    katip-kalkan serve                         # local MCP server (stdio) for Claude
    katip-kalkan mask dilekce.docx --matter 2026/123
    katip-kalkan share dilekce.docx --relay https://relay.katip.example
    katip-kalkan restore answer.txt out.txt --matter 2026/123
    katip-kalkan relay --port 8787             # run the relay (server side)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from . import core, vault


def share(path: str, relay_url: str, matter: str = "default", token: str | None = None) -> str:
    """Mask locally, encrypt locally, upload ciphertext. Returns the share code."""
    doc = core.mask_file(path, matter)
    if doc["pages"] > 1:  # the relay gets the whole masked text in one drop
        parts = [doc["masked_text"]] + [core.mask_file(path, matter, p)["masked_text"] for p in range(2, doc["pages"] + 1)]
        doc["masked_text"] = "".join(parts)
    payload = {k: doc[k] for k in ("file_name", "kind", "masked_text", "entity_counts", "placeholders")}
    key, nonce, ct = vault.seal_for_relay(json.dumps(payload, ensure_ascii=False))
    req = urllib.request.Request(relay_url.rstrip("/") + "/v1/drops", method="POST",
                                 data=json.dumps({"nonce": vault.b64u(nonce), "ciphertext": vault.b64u(ct)}).encode(),
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        drop = json.loads(r.read())
    return f"katip-{drop['id']}.{vault.b64u(key)}"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="katip-kalkan")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve", help="local MCP server over stdio")
    r = sub.add_parser("relay", help="run the relay")
    r.add_argument("--host", default="127.0.0.1")
    r.add_argument("--port", type=int, default=8787)
    for name in ("mask", "share", "copy"):
        p = sub.add_parser(name)
        p.add_argument("file")
        p.add_argument("--matter", default="default")
        if name == "share":
            p.add_argument("--relay", default=os.environ.get("KATIP_RELAY_URL", "http://127.0.0.1:8787"))
    p = sub.add_parser("restore")
    p.add_argument("text_file", help="file with the AI's answer (placeholders)")
    p.add_argument("output")
    p.add_argument("--matter", default="default")
    p = sub.add_parser("forget")
    p.add_argument("--matter", default="default")
    a = ap.parse_args(argv)

    if a.cmd == "serve":
        from .local_server import main as serve
        return serve()
    if a.cmd == "relay":
        sys.argv = [sys.argv[0], "--host", a.host, "--port", str(a.port)]
        from .relay import main as relay
        return relay()
    if a.cmd == "mask":
        doc = core.mask_file(a.file, a.matter)
        print(doc["masked_text"])
        print(json.dumps(doc["entity_counts"], ensure_ascii=False), file=sys.stderr)
    elif a.cmd == "copy":
        print(core.write_redacted(a.file, a.matter)["output_path"])
    elif a.cmd == "share":
        code = share(a.file, a.relay, a.matter, os.environ.get("KATIP_RELAY_UPLOAD_TOKEN"))
        print(code)
        print("Paste this code into ChatGPT. It works once and expires in 15 minutes.", file=sys.stderr)
    elif a.cmd == "restore":
        text = Path(a.text_file).read_text(encoding="utf-8")
        print(json.dumps(core.restore_to_file(text, a.output, a.matter)))
    elif a.cmd == "forget":
        print(json.dumps(core.forget_matter(a.matter)))
