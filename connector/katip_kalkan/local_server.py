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
from .i18n import text, tool
from .mcp_proto import Server, Tool

PROFILE = {"type": "string", "enum": ["ai", "court", "anon"], "default": "ai",
           "description": "ai = Yapay zekâ ile paylaşım (default: all personal data, the whole address, case and "
                          "bar numbers); court = Mahkemeye sunum (streets, case numbers and dates stay readable); "
                          "anon = Tam anonim (also dates, provinces, courts, companies and institutions)."}
MATTER = {"type": "string", "description": "Matter (dosya) label; files of the same case share placeholders. "
                                           "Use a neutral label such as a file number, not a client name.",
          "default": "default"}

INSTRUCTIONS = """Katip Kalkan masks Turkish personal data (KVKK) on the user's own computer, so that client
names, ID numbers and health data never reach Claude or Anthropic's servers.
File names are personal data too ("Ayşe Kaya - epikriz.pdf"). To find a document, call list_files: it
returns ids and shortened names. Then call mask_file with file_id. Do not list, search or open the folder
with any other tool (no file listing, Read, Bash or computer use), and do not repeat a file's full name.
When the user gives a path, mask_file also accepts it. Work only with the masked text that mask_file returns. Use the default profile "ai" unless the user asks for a court copy
("court") or full anonymisation ("anon"). Do not open the original file with any other tool, and do not ask the
user to paste or upload the original. Keep placeholders such as [AD SOYAD-1] exactly as written.
When the user wants a final document with the real names, call restore_to_file with your text: Katip
writes it on their computer and you will only get the file path back, never the real values.
If the user asks where their files go or wants to see the folder, call open_folder. When a file is not
in list_files, ask the user to put it in their Katip folder (open_folder shows it).
If the user says "the file I just added" or similar, call mask_file with file_id "latest".
If the user attaches a client document to the chat instead, it has already been uploaded with the message:
say so plainly, don't analyse it further unless they confirm, and suggest dropping it into the Katip folder
and asking again, so the next document stays on their computer."""

def _privacy(text: str) -> dict:
    """A fixed argument whose only job is to show up in Claude Desktop's permission prompt, which shows
    the tool title and its arguments but not the description."""
    return {"type": "string", "enum": [text], "default": text,
            "description": "Always send exactly this text; it tells the user what Katip does."}


MASK_NOTE = _privacy(text("privacy_mask"))
LIST_NOTE = _privacy(text("privacy_list"))
RESTORE_NOTE = _privacy(text("privacy_restore"))
FILE_ID = {"type": "string", "description": "Id from list_files (preferred: keeps the file name private)"}

TOOLS = [
    Tool("list_files", *tool("list_files"),
         {"type": "object", "properties": {"privacy": LIST_NOTE}, "required": ["privacy"],
          "additionalProperties": False},
         lambda: core.list_files(),
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("mask_file", *tool("mask_file"),
         {"type": "object", "properties": {"privacy": MASK_NOTE, "file_id": FILE_ID,
                                           "path": {"type": "string", "description": "Absolute path, if no file_id"},
                                           "matter": MATTER, "profile": PROFILE,
                                           "page": {"type": "integer", "minimum": 1, "default": 1}},
          "required": ["privacy"], "additionalProperties": False},
         lambda path=None, matter="default", page=1, profile=None, file_id=None: core.mask_file(
             path, matter, page, profile, file_id),
         # reads the user's file; writes only the local encrypted vault; never reaches the internet
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("write_masked_copy", *tool("write_masked_copy"),
         {"type": "object", "properties": {"privacy": MASK_NOTE, "file_id": FILE_ID, "path": {"type": "string"},
                                           "matter": MATTER, "profile": PROFILE, "output_path": {"type": "string"}},
          "required": ["privacy"], "additionalProperties": False},
         lambda path=None, matter="default", output_path=None, profile=None, file_id=None: core.write_redacted(
             path, matter, output_path, profile, file_id),
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}),
    Tool("restore_to_file", *tool("restore_to_file"),
         {"type": "object", "properties": {"privacy": RESTORE_NOTE, "text": {"type": "string"},
                                           "output_path": {"type": "string", "description": "e.g. ~/Desktop/dilekce.txt"},
                                           "matter": MATTER},
          "required": ["privacy", "text", "output_path"], "additionalProperties": False},
         lambda text, output_path, matter="default": core.restore_to_file(text, output_path, matter),
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}),
    Tool("forget_matter", *tool("forget_matter"),
         {"type": "object", "properties": {"matter": MATTER}, "required": ["matter"], "additionalProperties": False},
         lambda matter: core.forget_matter(matter),
         {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}),
    Tool("open_folder", *tool("open_folder"),
         {"type": "object", "properties": {}, "additionalProperties": False},
         lambda: core.open_folder(),
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("katip_status", *tool("katip_status"),
         {"type": "object", "properties": {}, "additionalProperties": False},
         lambda: core.status(),
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
]


def _prompts() -> list[dict]:
    title, desc, arg, body = text("prompt")
    return [{"name": "katip", "title": title, "description": desc,
             "arguments": [{"name": "istek", "description": arg, "required": False}],
             "render": lambda a: body.format(req=(a.get("istek") or "").strip() or "…")}]


def build() -> Server:
    return Server("katip-kalkan", __version__, INSTRUCTIONS, TOOLS, _prompts())


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
