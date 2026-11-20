"""katip-nl command line.

  python -m katip_nl mask    brief.txt [--out brief.masked.txt] [--vault brief.vault.json] [--full-address] [--lang nl|en|tr]
  python -m katip_nl restore antwoord.txt --vault brief.vault.json
  python -m katip_nl check   brief.txt [--lang nl|en|tr]    # statute citations + ECLI numbers (sends only ids)

Text files only in this first slice; .docx/.pdf go through Katip's existing readers next.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import rechtspraak, wetten
from .labels import label, ui
from .mask import load_table, mask, restore, save_table


def _read(p):
    return Path(p).read_text(encoding="utf-8")


def cmd_mask(a):
    text = _read(a.file)
    masked, table, spans = mask(text, address_detail="full" if a.full_address else "street")
    src = Path(a.file)
    out = Path(a.out or src.with_suffix(".masked" + src.suffix))
    vault = Path(a.vault or src.with_suffix(".vault.json"))
    for p in (out, vault):
        if p.exists() and not a.force:
            sys.exit(f"{p} exists; use --force to overwrite")
    out.write_text(masked, encoding="utf-8")
    save_table(table, vault)
    counts = {}
    for s in spans:
        k = (s["entity_type"], s["flag_only"])
        counts[k] = counts.get(k, 0) + 1
    print(f"{ui('masked', a.lang)}:")
    for (t, flag), n in sorted(counts.items()):
        if not flag:
            print(f"  {n:3d}  {label(t, a.lang)}")
    flagged = [(t, n) for (t, flag), n in counts.items() if flag]
    if flagged:
        print(f"{ui('review', a.lang)}:")
        for t, n in flagged:
            print(f"  {n:3d}  {label(t, a.lang)}")
    print(f"\n-> {out}\n-> {vault}  (stays on this computer / blijft op deze computer)")


def cmd_restore(a):
    print(restore(_read(a.file), load_table(a.vault)))


def cmd_check(a):
    text = _read(a.file)
    for c in wetten.check_text(text):
        if c.get("exists") is True:
            state = ui("article_found", a.lang)
        elif c.get("exists") is False:
            state = ui("article_missing", a.lang) + (" (vervallen / repealed)" if c.get("repealed") else "")
        else:
            state = c.get("note") or c.get("error") or ui("act_unknown", a.lang)
        print(f"- {c['cite']}  [{c['title_nl']} / {c['title_en']}]\n    {state}  {c.get('url') or ''}")
        if c.get("text") and c.get("exists"):
            print("    " + c["text"].replace("\n", "\n    ")[:600])
    for r in rechtspraak.check_text(text):
        if r.get("exists"):
            print(f"- {r['ecli']}  {ui('ecli_found', a.lang)}: {r['court']}, {r['date']}, {r['area']}\n    {r['url']}")
            if r.get("summary"):
                print(f"    {r['summary'][:400]}")
        elif r.get("exists") is False:
            print(f"- {r['ecli']}  {ui('ecli_missing', a.lang)}")
        else:
            print(f"- {r['ecli']}  {r.get('note')}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="katip-nl", description="Dutch masking + statute/ECLI checks (Katip NL)")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mask")
    m.add_argument("file")
    m.add_argument("--out")
    m.add_argument("--vault")
    m.add_argument("--full-address", action="store_true", help="mask the whole address, not only number + postcode")
    m.add_argument("--force", action="store_true")
    r = sub.add_parser("restore")
    r.add_argument("file")
    r.add_argument("--vault", required=True)
    c = sub.add_parser("check")
    c.add_argument("file")
    for s in (m, c):
        s.add_argument("--lang", default="nl", choices=("nl", "en", "tr"))
    a = p.parse_args(argv)
    {"mask": cmd_mask, "restore": cmd_restore, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
