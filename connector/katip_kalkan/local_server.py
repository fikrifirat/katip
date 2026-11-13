"""Katip Kalkan local MCP server (stdio) for Claude Desktop, Claude Code and Cowork.

The model only ever sends us a *file path*. We open the file on this device, mask it
here, and return masked text. The original bytes never enter the chat, so they never
reach Anthropic's servers.

    python -m katip_kalkan.local_server
"""
from __future__ import annotations

import json
import logging
import os
import sys

from . import __version__, core
from .mcp_proto import Server, Tool

PROFILE = {"type": "string", "enum": ["ai", "court", "anon"], "default": "ai",
           "description": "ai = Yapay zekâ ile paylaşım (default: all personal data, the whole address, case and "
                          "bar numbers); court = Mahkemeye sunum (streets, case numbers and dates stay readable); "
                          "anon = Tam anonim (also dates, provinces, courts, companies and institutions)."}
MATTER = {"type": "string", "description": "Matter (dosya) label; files of the same case share placeholders. "
                                           "Use a neutral label such as a file number, not a client name.",
          "default": "default"}

INSTRUCTIONS = """Katip Kalkan masks Turkish personal data (KVKK) on the user's own computer.
When the user asks about a document on their computer, call mask_file with its path and work only
with the masked text it returns. Use the default profile "ai" unless the user asks for a court copy
("court") or full anonymisation ("anon"). Do not open the original file with any other tool, and do not ask the
user to paste or upload the original. Keep placeholders such as [AD SOYAD-1] exactly as written.
When the user wants a final document with the real names, call restore_to_file with your text: Katip
writes it on their computer and you will only get the file path back, never the real values.
If the user asks where their files go or wants to see the folder, call open_folder. When a file is not
found, tell the user to put it in their Katip folder (open_folder shows it) and ask for its name."""

TOOLS = [
    Tool("mask_file", "Mask a document on this computer",
         "Open a .docx, .udf (UYAP), .txt, .pdf (also scanned) or photo (.jpg/.png) by its path on the "
         "user's computer, read scans with local OCR, remove personal data (names, T.C. kimlik / YKN / "
         "passport numbers, addresses, phones, IBAN, health and other KVKK Article 6 data) locally, and "
         "return only the masked text. Long documents come in pages.",
         {"type": "object", "properties": {"path": {"type": "string", "description": "Absolute path to the file"},
                                           "matter": MATTER, "profile": PROFILE,
                                           "page": {"type": "integer", "minimum": 1, "default": 1}},
          "required": ["path"], "additionalProperties": False},
         lambda path, matter="default", page=1, profile=None: core.mask_file(path, matter, page, profile),
         # reads the user's file; writes only the local encrypted vault; never reaches the internet
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("write_masked_copy", "Save a masked copy next to the original",
         "Write a masked copy of a .docx, .udf or .txt file in the same format next to the original "
         "(name.maskeli.ext) so the user can share it. Never overwrites a file. Returns the new path.",
         {"type": "object", "properties": {"path": {"type": "string"}, "matter": MATTER, "profile": PROFILE,
                                           "output_path": {"type": "string"}},
          "required": ["path"], "additionalProperties": False},
         lambda path, matter="default", output_path=None, profile=None: core.write_redacted(
             path, matter, output_path, profile),
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}),
    Tool("restore_to_file", "Put the real names back, on this computer",
         "Replace placeholders like [AD SOYAD-1] in the given text with the real values kept on the user's "
         "computer, and save the result as a new local file. Returns only the file path and a count, never "
         "the real values. Never overwrites a file.",
         {"type": "object", "properties": {"text": {"type": "string"},
                                           "output_path": {"type": "string", "description": "e.g. ~/Desktop/dilekce.txt"},
                                           "matter": MATTER},
          "required": ["text", "output_path"], "additionalProperties": False},
         lambda text, output_path, matter="default": core.restore_to_file(text, output_path, matter),
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}),
    Tool("forget_matter", "Delete the name map of a matter",
         "Permanently delete the local placeholder map of a matter. After this, its placeholders can no "
         "longer be restored.",
         {"type": "object", "properties": {"matter": MATTER}, "required": ["matter"], "additionalProperties": False},
         lambda matter: core.forget_matter(matter),
         {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}),
    Tool("open_folder", "Open my Katip folder",
         "Open the user's Katip folder (where client files go) in Finder or Explorer on their computer, "
         "creating it if needed. Returns the folder path and a file:// link.",
         {"type": "object", "properties": {}, "additionalProperties": False},
         lambda: core.open_folder(),
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("katip_status", "Katip status",
         "Show the local engine, OCR, threshold, the user's Katip folder (with a link) and where the "
         "placeholder map is kept.",
         {"type": "object", "properties": {}, "additionalProperties": False},
         lambda: core.status(),
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
]


def build() -> Server:
    return Server("katip-kalkan", __version__, INSTRUCTIONS, TOOLS)


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=os.environ.get("KATIP_LOG", "WARNING"),
                        format="katip %(levelname)s %(message)s")
    # --allow DIR (repeatable) limits which folders Katip may open; set by the plugin/MCPB settings
    args, allow = sys.argv[1:], []
    while "--allow" in args:
        i = args.index("--allow")
        allow.append(args[i + 1])
        del args[i:i + 2]
    if allow:
        os.environ["KATIP_ALLOWED_DIRS"] = os.pathsep.join(a for a in allow if a)
    server = build()
    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            batch = msg if isinstance(msg, list) else [msg]
            resps = [r for r in (server.handle(m) for m in batch) if r is not None]
            resp = resps if isinstance(msg, list) else (resps[0] if resps else None)
        if resp is not None:
            out.write(json.dumps(resp, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
