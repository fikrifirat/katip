"""Katip Kalkan guard for Claude Code and Cowork (a PreToolUse hook).

Claude's own tools (Read, Grep, Glob, Edit, Write, Bash) must not open the client files in the Katip
folder, the restored documents with real names, or Katip's encrypted name map. Katip's own tools
(mask_file, restore_to_file, ...) are MCP tools and are not affected. The hook reads the tool call on
stdin; it blocks with exit code 2 and a short reason, and otherwise prints nothing. It reads no file
contents and makes no network calls. Standard library only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MSG = {
    "tr": "Katip: Bu klasörde müvekkil belgeleri var. Claude bu dosyaları doğrudan açamaz, listeleyemez ya da "
          "değiştiremez. Belgeyi Katip ile bulun ve açın (list_files, sonra mask_file); gerçek adlı son metin için "
          "restore_to_file kullanın.",
    "en": "Katip: this folder holds client documents. Claude may not open, list or change these files directly. "
          "Find and open the document with Katip (list_files, then mask_file); use restore_to_file for the final "
          "text with real names.",
}
PATH_KEYS = ("file_path", "notebook_path", "path")
_COMMON = {"downloads", "indirilenler", "i̇ndirilenler", "documents", "belgeler", "desktop", "masaüstü", ""}


def _norm(p: str, cwd: str) -> str:
    p = os.path.expandvars(os.path.expanduser(p.strip().strip("'\"")))
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    try:
        p = str(Path(p).resolve())
    except OSError:
        p = os.path.abspath(p)
    return os.path.normcase(p)


def protected() -> list[str]:
    home = os.environ.get("KATIP_HOME") or "~/.katip"
    roots = [os.environ.get("KATIP_FOLDER") or "~/Documents/katip-documents", home]
    for var in ("KATIP_ALLOWED_DIRS", "KATIP_EXTRA_DIRS"):
        roots += [r for r in os.environ.get(var, "").split(os.pathsep) if r.strip() and "${" not in r]
    cfg = Path(os.path.expanduser(home)) / "folders.txt"  # the case folders Katip searches (one per line)
    try:
        roots += [l.strip() for l in cfg.read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.lstrip().startswith("#")]
    except OSError:
        pass
    if os.environ.get("KATIP_DOWNLOADS", "1") != "0":  # UYAP downloads and e-mail attachments land here
        roots += [d for d in ("~/Downloads", "~/İndirilenler") if os.path.isdir(os.path.expanduser(d))]
    return sorted({_norm(r, os.getcwd()) for r in roots})


def _inside(p: str, root: str) -> bool:
    return p == root or p.startswith(root.rstrip(os.sep) + os.sep)


def blocked(call: dict) -> bool:
    tool, args = call.get("tool_name", ""), call.get("tool_input") or {}
    cwd = call.get("cwd") or os.getcwd()
    roots = protected()
    if tool == "Bash":
        cmd = os.path.normcase(os.path.expandvars(str(args.get("command", ""))))
        home = os.path.normcase(os.path.expanduser("~"))
        forms = set()
        for r in roots:
            forms.add(r)
            if r.startswith(home + os.sep):
                rel = r[len(home) + 1:]
                forms |= {"~/" + rel, "$home/" + rel, "${home}/" + rel}
            base = os.path.basename(r)
            if base not in _COMMON:
                forms.add(base)  # e.g. "katip-documents", ".katip"
        if any(f and f in cmd for f in forms):
            return True
        return any(_inside(_norm(cwd, cwd), r) for r in roots)  # a shell started inside the folder
    paths = [str(args[k]) for k in PATH_KEYS if args.get(k)]
    if tool in ("Grep", "Glob"):
        if not args.get("path"):
            paths.append(cwd)
        pat = str(args.get("pattern", ""))
        if tool == "Glob" and (pat.startswith(("/", "~")) or ":" in pat[:3]):
            paths.append(pat.split("*")[0] or "/")
    return any(_inside(_norm(p, cwd), r) for p in paths for r in roots)


def main() -> int:
    try:
        call = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0  # not a tool call we understand: leave the decision to Claude Code
    if not isinstance(call, dict) or not blocked(call):
        return 0
    lang = (os.environ.get("KATIP_LANG") or "tr").lower()[:2]
    print(MSG.get(lang, MSG["tr"]), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
