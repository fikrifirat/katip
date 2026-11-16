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
                          "bar numbers); court = Mahkemeye sunum (parties' own addresses, UETS and bar numbers masked; the disputed "
                          "property's address, case numbers and dates stay readable); "
                          "anon = Tam anonim (also dates, provinces, courts, companies and institutions)."}
MATTER = {"type": "string", "description": "Matter (dosya) label; files of the same case share placeholders. "
                                           "Use a neutral label such as a file number, not a client name.",
          "default": "default"}

INSTRUCTIONS = """Katip Kalkan masks Turkish personal data (KVKK) on the user's own computer, so that the client
names, ID numbers and health data it finds are replaced by placeholders before the text reaches Claude.
Most users are Turkish lawyers: answer in the user's language (usually Turkish) and use Turkish legal terms.
Documents stay where the lawyer keeps them: the case folder picked in the settings (with subfolders) and Downloads,
where UYAP downloads and e-mail attachments land. Nothing has to be copied anywhere.
To find a document, call list_files. When the user describes it ("Yılmaz kira sözleşmesi", "bugün indirdiğim
bilirkişi raporu"), pass those words as ara: Katip searches the real file and folder names on this computer and
returns ids, shortened names and where. File names are personal data too, so you only ever see shortened names;
do not repeat a file's full name. If several documents match, show the shortened names and where, and ask which
one. For "the file I just downloaded / added" or no description, use file_id "latest". When the user gives a path,
mask_file also accepts it. Then call mask_file with file_id and put the shortened name in the display field
(belge / document) so the user sees which document they are approving. Do not list, search or open documents with
any other tool (no file listing, Read, Bash or computer use). Work only with the masked text that mask_file returns.
Use the default profile "ai" unless the user asks for a court copy ("court": mahkemeye sunulacak, dilekçe eki) or
full anonymisation ("anon": tam anonim, anonimleştir, yayın, makale).
Pass matter only when the user works on several documents of one case (a neutral label such as 2026/123, never a
client name); for a single document leave the default. Do not ask the user to paste or upload the original. Keep
placeholders such as [AD SOYAD-1] exactly as written.
When the user wants a final document with the real names, call restore_to_file with your text and a file name such
as cevap-dilekcesi.docx (.docx, .txt or .md). It is saved next to the document you masked last for that matter.
Never open that file: you will only get the file path back, never the real values.
If a result has folder_warning, pass it on to the user once, in their language.
If no document matches, ask for another word from its name, or where it is; if it is somewhere else, the user can
add that folder in Katip's settings (Claude Desktop) or to ~/.katip/folders.txt (Claude Code).
If the user types a client's real name or ID number in the chat (also to find a document), it reaches you as typed:
don't repeat it. Once, mention that describing the document by type, date or file number (bilirkişi raporu, dünkü
UYAP evrakı, 2026/123) finds it without sending a name.
Remind the user once per conversation to review your work: Katip can miss a value, and your legal analysis can be wrong.
If the user attaches a client document to the chat instead, it has already been uploaded with the message: say so
plainly, don't analyse it further unless they confirm, and suggest typing the document's name next time instead,
so Katip can open it on their computer.
When a Katip tool fails, explain the error in one or two plain sentences in the user's language. Never suggest
pasting the text, attaching the file, or removing names by hand and sending it: point to the Katip app
(https://fikrifirat.github.io/katip) instead."""

def _privacy(text: str) -> dict:
    """A fixed argument whose only job is to show up in Claude Desktop's permission prompt, which shows
    the tool title and its arguments but not the description."""
    return {"type": "string", "enum": [text], "default": text,
            "description": "Always send exactly this text; it tells the user what Katip does."}


MASK_NOTE = _privacy(text("privacy_mask"))
LIST_NOTE = _privacy(text("privacy_list"))
RESTORE_NOTE = _privacy(text("privacy_restore"))
INFO = text("info_key")  # the field's name is what Claude Desktop shows as its label ("Bilgi" / "Privacy")
DOC = text("doc_key")    # display-only: the shortened file name, so the prompt says which document
DOC_FIELD = {"type": "string", "description": text("doc_desc")}
FILE_ID = {"type": "string", "description": "Id from list_files (preferred: keeps the file name private)"}

TOOLS = [
    Tool("list_files", *tool("list_files"),
         {"type": "object", "properties": {INFO: LIST_NOTE,
                                           "ara": {"type": "string", "description": "Words from the document's name or "
                                                   "folder as the user said them (e.g. \"Yılmaz kira\", \"bilirkişi\"); "
                                                   "empty = newest documents"},
                                           "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20}},
          "required": [INFO], "additionalProperties": False},
         lambda ara=None, limit=20: core.list_files(ara, limit),
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("mask_file", *tool("mask_file"),
         {"type": "object", "properties": {INFO: MASK_NOTE, DOC: DOC_FIELD, "file_id": FILE_ID,
                                           "path": {"type": "string", "description": "Absolute path, if no file_id"},
                                           "matter": MATTER, "profile": PROFILE,
                                           "page": {"type": "integer", "minimum": 1, "default": 1}},
          "required": [INFO], "additionalProperties": False},
         lambda path=None, matter="default", page=1, profile=None, file_id=None: core.mask_file(
             path, matter, page, profile, file_id),
         # reads the user's file; writes only the local encrypted vault; never reaches the internet
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("write_masked_copy", *tool("write_masked_copy"),
         {"type": "object", "properties": {INFO: MASK_NOTE, DOC: DOC_FIELD, "file_id": FILE_ID, "path": {"type": "string"},
                                           "matter": MATTER, "profile": PROFILE, "output_path": {"type": "string"}},
          "required": [INFO], "additionalProperties": False},
         lambda path=None, matter="default", output_path=None, profile=None, file_id=None: core.write_redacted(
             path, matter, output_path, profile, file_id),
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}),
    Tool("restore_to_file", *tool("restore_to_file"),
         {"type": "object", "properties": {INFO: RESTORE_NOTE, "text": {"type": "string"},
                                           "output_path": {"type": "string", "description": "File name, saved next to the source document: .docx, .txt or .md (e.g. cevap-dilekcesi.docx)"},
                                           "matter": MATTER},
          "required": [INFO, "text", "output_path"], "additionalProperties": False},
         lambda text, output_path, matter="default": core.restore_to_file(text, output_path, matter),
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}),
    Tool("forget_matter", *tool("forget_matter"),
         {"type": "object", "properties": {"matter": MATTER}, "required": ["matter"], "additionalProperties": False},
         lambda matter: core.forget_matter(matter),
         {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}),
    Tool("open_folder", *tool("open_folder"),
         {"type": "object", "properties": {}, "additionalProperties": False},
         lambda: core.open_folder(),  # creates the folder on first use
         {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
    Tool("katip_status", *tool("katip_status"),
         {"type": "object", "properties": {}, "additionalProperties": False},
         lambda: core.status(),
         {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}),
]


def _prompt(name: str, key: str) -> dict:
    title, desc, arg, body = text(key)
    return {"name": name, "title": title, "description": desc,
            "arguments": [{"name": "belge", "description": text("doc_arg"), "required": False},
                          {"name": "istek", "description": arg, "required": False}],
            "render": lambda a: body.format(doc=(a.get("belge") or "").strip() or "son belge / newest",
                                            req=(a.get("istek") or "").strip() or "…")}


def _prompts() -> list[dict]:
    return [_prompt("katip", "prompt"), _prompt("katip_incele", "prompt_review"), _prompt("katip_taslak", "prompt_draft")]


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
