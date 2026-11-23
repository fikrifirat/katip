"""Katip Uyum: draft a GDPR (+KVKK, + EU AI Act) document pack for an AI agent system.

  python -m katip_uyum build    harness.json --out pack/      # 11 Markdown files (00 overview + 10 documents)
  python -m katip_uyum check    harness.json                  # findings only: must-dos, risks, open questions
  python -m katip_uyum template > my_harness.json             # empty questionnaire to fill in

Offline, standard library only. The questionnaire describes data flows, not documents: nothing
about any client or person goes in it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .docs import render_all
from .model import QuestionnaireError, load
from .rules import SEVERITY_LABEL, analyse

TEMPLATE = Path(__file__).with_name("template.json")


def cmd_build(a):
    an = analyse(load(a.questionnaire))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = render_all(an)
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    counts = {}
    for f in an.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    print(f"{len(files)} files -> {out}/")
    print("  " + ", ".join(f"{counts.get(k, 0)} {SEVERITY_LABEL[k].lower()}" for k in ("action", "risk", "open", "info")))
    print("  Drafts for lawyer review. Start with 00-overview.md.")


def cmd_check(a):
    an = analyse(load(a.questionnaire))
    if a.json:
        print(json.dumps([f.__dict__ for f in an.findings], ensure_ascii=False, indent=2))
        return
    for f in an.findings:
        print(f"[{SEVERITY_LABEL[f.severity]}] {f.title}  ({f.cite}; docs {', '.join(f.docs)})")


def cmd_template(_a):
    sys.stdout.write(TEMPLATE.read_text(encoding="utf-8"))


def main(argv=None):
    p = argparse.ArgumentParser(prog="katip_uyum", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="write the document pack")
    b.add_argument("questionnaire")
    b.add_argument("--out", default="pack")
    b.set_defaults(func=cmd_build)
    c = sub.add_parser("check", help="print findings")
    c.add_argument("questionnaire")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_check)
    t = sub.add_parser("template", help="print an empty questionnaire")
    t.set_defaults(func=cmd_template)
    a = p.parse_args(argv)
    try:
        a.func(a)
    except QuestionnaireError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
