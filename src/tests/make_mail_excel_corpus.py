"""A larger e-mail and Excel test set, made from all 80 synthetic demo samples (docs/samples).

Every sample's text becomes the body of an .eml (five MIME styles in turn: plain + HTML, HTML only, plain,
quoted-printable HTML in multipart/mixed, base64) and of an Outlook .msg (plain body, or HTML body only);
the e-posta samples keep their own sender and recipient, the others get the sample's first person as
sender. Each document type also becomes a workbook (client table + call log in prose) from its five
answer keys. The samples' own .txt files are copied too, as the baseline: the same values, no container.

answer_key.json: {file: {"mask": [values], "keep": [phrases], "source": [sample ids]}}

  python3 src/tests/make_mail_excel_corpus.py /tmp/mx-corpus [docs/samples]
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import mail_samples as M  # noqa: E402

STYLES = ["alternative", "html", "plain", "qp-html", "base64"]
FIRM = "Örnek Hukuk Bürosu <buro@ornekhukuk.invalid>"


def ascii_mail(name):
    s = unicodedata.normalize("NFKD", name.replace("ı", "i").replace("İ", "I")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", ".", s).strip(".") + "@ornekposta.invalid"


def keep_line(body, gold):
    """A line of the body with no answer-key value in it, to check the content survives masking."""
    vals = [g.casefold() for g in gold]
    for line in sorted(body.split("\n"), key=len, reverse=True):
        l = line.strip()
        if len(l) >= 25 and not any(v in l.casefold() for v in vals) and not re.search(r"\d{3}", l):
            words = l.split()
            return " ".join(words[:5])
    return None


def main(out: Path, samples: Path):
    out.mkdir(parents=True, exist_ok=True)
    man = json.loads((samples / "manifest.json").read_text(encoding="utf-8"))
    man = [m for m in man if m["type"] != "musteri_listesi" and (samples / f"{m['id']}.txt").exists()]
    key = {}
    for i, m in enumerate(man):
        text = (samples / f"{m['id']}.txt").read_text(encoding="utf-8")
        gold = [g["text"] for g in m["gold"]]
        if m["type"] == "eposta":
            head, body = M.split_text_mail(text)
        else:
            person = next((g["text"] for g in m["gold"] if g["entity_type"] == "PERSON"), "Belge Sahibi")
            email = next((g["text"] for g in m["gold"] if g["entity_type"] == "EMAIL"), None) or ascii_mail(person)
            gold = gold + ([email] if email not in gold else [])
            head = {"Kimden": f"{person} <{email}>", "Kime": FIRM, "Konu": f"{m['title']} - {person}", "Tarih": "12.11.2026"}
            body = text
        gold = [g for g in dict.fromkeys(gold) if g.casefold() in (" ".join(head.values()) + "\n" + body).casefold()]
        att = [(f"{m['title']} ek.pdf", b"%PDF-1.4 ornek")] if i % 3 == 0 else []
        k = keep_line(body, gold)
        style = STYLES[i % len(STYLES)]
        (out / f"{m['id']}.{style}.eml").write_bytes(M.eml(head, body, style, att))
        (out / f"{m['id']}.msg").write_bytes(M.msg(head, body, html_only=(i % 2 == 1), attachments=att))
        shutil.copyfile(samples / f"{m['id']}.txt", out / f"{m['id']}.txt")
        for name in (f"{m['id']}.{style}.eml", f"{m['id']}.msg"):
            key[name] = {"mask": gold, "keep": [k] if k else [], "source": [m["id"]]}
        key[f"{m['id']}.txt"] = {"mask": [g["text"] for g in m["gold"]], "keep": [k] if k else [], "source": [m["id"]], "baseline": True}
    for t in sorted({m["type"] for m in man}):
        group = sorted((m for m in man if m["type"] == t), key=lambda m: m["n"])
        rows, g1 = M.client_rows(group)
        notes, g2 = M.notes_rows(group)
        name = f"liste_{t}.xlsx"
        (out / name).write_bytes(M.xlsx([("Müvekkiller", rows), (group[0]["title"][:31], notes)]))
        key[name] = {"mask": list(dict.fromkeys(x["text"] for x in g1 + g2)), "keep": ["Görüşme bekleniyor", "evraklar hazırlanacak"],
                     "source": [m["id"] for m in group]}
    (out / "answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    n = lambda ext: sum(1 for f in key if f.endswith(ext))
    print(f"{out}: {n('.eml')} .eml, {n('.msg')} .msg, {n('.xlsx')} .xlsx, {n('.txt')} .txt baselines")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parents[2] / "docs" / "samples"))
