"""Add e-mail and Excel samples to the demo (docs/samples), from the synthetic samples already there.

- The five "E-posta" samples get an .eml and an Outlook .msg version, built from their own text
  (Kimden/Kime/Konu header lines + body), so their answer keys apply unchanged.
- A new type, "Müvekkil listesi" (client list), has five .xlsx variants: a client table and a call log,
  filled from other samples' answer keys (made-up people), with its own answer key.

Stdlib only. build_site.py runs this after copying the samples; it can also run alone:
    python3 src/build_mail_samples.py docs/samples
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mail_samples as M  # noqa: E402

EML_STYLES = ["alternative", "html", "plain", "qp-html", "base64"]
LIST_FROM = ["aydinlatma", "vekaletname", "ihtarname", "kira_sozlesmesi", "is_sozlesmesi", "icra"]


def main(out: Path):
    man_path = out / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man = [m for m in man if m["type"] != "musteri_listesi"]
    by_id = {m["id"]: m for m in man}
    for m in man:
        if m["type"] != "eposta" or not (out / f"{m['id']}.txt").exists():
            continue
        head, body = M.split_text_mail((out / f"{m['id']}.txt").read_text(encoding="utf-8"))
        k = m["n"] - 1
        att = [(f"{m['title']} ek.pdf", b"%PDF-1.4 ornek")] if k % 2 == 0 else []
        (out / f"{m['id']}.eml").write_bytes(M.eml(head, body, EML_STYLES[k % len(EML_STYLES)], att))
        (out / f"{m['id']}.msg").write_bytes(M.msg(head, body, html_only=(k % 2 == 1), attachments=att))
        m["formats"] = [f for f in m["formats"] if f not in ("eml", "msg")] + ["eml", "msg"]
    for n in range(1, 6):
        picked = [by_id[f"{t}_{(n + i - 1) % 5 + 1:02d}"] for i, t in enumerate(LIST_FROM) if f"{t}_{(n + i - 1) % 5 + 1:02d}" in by_id]
        rows, gold = M.client_rows(picked)
        notes, gold2 = M.notes_rows(picked)
        (out / f"musteri_listesi_{n:02d}.xlsx").write_bytes(M.xlsx([("Müvekkiller", rows), ("Görüşmeler", notes)]))
        seen, g = set(), []
        for x in gold + gold2:
            if x["text"] not in seen:
                seen.add(x["text"]); g.append(x)
        man.append({"id": f"musteri_listesi_{n:02d}", "type": "musteri_listesi", "title": "Müvekkil listesi", "n": n,
                    "formats": ["xlsx"], "gold": g})
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print("mail and Excel samples:", sum(1 for m in man if "eml" in m["formats"]), "e-mails,",
          sum(1 for m in man if m["type"] == "musteri_listesi"), "workbooks")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parents[1] / "docs" / "samples"))
