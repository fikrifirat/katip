"""Evaluate Katip Uyum packs. Offline after build_law_index.py has run once.

  python eval/eval_uyum.py                 # score the example + every scenario, print a table
  python eval/eval_uyum.py --json out.json # also write the numbers
  python eval/eval_uyum.py --list-cites    # every citation found, with how it resolved

Four automatic dimensions (the persona review in eval/persona/ adds a fifth, human-style one):

1. Citation accuracy. Every "Art. 33(1)", "Arts. 44-49", "AI Act Art. 5(1)(d)", "KVKK m.6/3-d" in the pack
   is parsed and looked up in law_index.json (official texts). `exists`: the article, paragraph and point
   exist. `verified`: for citations listed in claims.json, the law text contains the expected phrase AND
   the sentence in the pack that cites it is about that topic.
2. Gaps flagged. scenarios.json applies small changes to the example questionnaire; each scenario lists
   findings that must appear (recall) and findings that must not (false alarms).
3. No overclaiming. Phrases that claim compliance, safety or anonymity, in English and Turkish.
4. Turkish wording (Turkish documents only): official KVKK terms, calques, missing Turkish letters.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from katip_uyum.docs import render_all  # noqa: E402
from katip_uyum.rules import analyse  # noqa: E402

LAW = json.loads((HERE / "law_index.json").read_text(encoding="utf-8"))
CLAIMS = json.loads((HERE / "claims.json").read_text(encoding="utf-8"))
SCENARIOS = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "examples" / "dd_harness.json").read_text(encoding="utf-8"))

LETTERS = "abcdefghijklmnopqrstuvwxyz"

# ------------------------------------------------------------------------------------------ citations
_NUM = r"\d+[a-z]?(?:\(\d+[a-z]?\))?(?:\([a-z]{1,4}\))?(?:\([ivx]+\))?"
_ART = re.compile(rf"\b(?:Arts?|Articles?)\.?\s+((?:{_NUM})(?:\s*(?:-|–|,|and|to|or)\s*(?:{_NUM}))*)")
_KVKK = re.compile(r"\bm\.\s?(\d+)(?:/(\d+))?(?:-([a-zçğıöşü]))?")


def _split_list(s: str) -> list[tuple[str, bool]]:
    """-> [(cite, is_range_end)]. Range ends ('Arts. 15-22') are checked for existence only."""
    parts = re.split(r"\s*(?:,|and|or)\s*", s)
    out = []
    for p in parts:
        m = re.match(rf"^({_NUM})\s*(?:-|–|to)\s*({_NUM})$", p)
        out += [(m.group(1), True), (m.group(2), True)] if m else [(p, False)]
    return [p for p in out if p[0]]


def _key(cite: str) -> tuple[str, str]:
    """'6(1)(f)' -> ('6', '1.f');  '33' -> ('33', '')."""
    m = re.match(r"(\d+[a-z]?)((?:\([^)]+\))*)", cite)
    art, rest = m.group(1), re.findall(r"\(([^)]+)\)", m.group(2))
    return art, ".".join(rest)


def _law_for(text: str, start: int, doc: str) -> str:
    # The clause the citation sits in: back to the last ';', '(' or sentence start, max 80 chars.
    head = text[max(0, start - 80):start]
    cut = max(head.rfind(";"), head.rfind(". "), head.rfind("\n"), head.rfind("|"))
    clause = head[cut + 1:]
    if "AI Act" in clause:
        return "aiact"
    if "GDPR" in clause or "Regulation (EU) 2016/679" in clause:
        return "gdpr"
    if "KVKK" in clause:
        return "kvkk"
    return "aiact" if doc.startswith("10-") else "gdpr"


def find_citations(text: str, doc: str):
    out = []
    for m in _ART.finditer(text):
        if re.match(r"\s*(?:of|in)\s+(?:the\s+)?(?:Regulation|Directive|Decision|Law)", text[m.end():m.end() + 30]):
            if not re.match(r"\s*(?:of|in)\s+(?:the\s+)?(?:Regulation \(EU\) 2016/679|Regulation \(EU\) 2024/1689)",
                            text[m.end():m.end() + 40]):
                continue  # article of some other act (e.g. 'Article 42 of Regulation 2018/1725')
        law = _law_for(text, m.start(), doc)
        for c, rng in _split_list(m.group(1)):
            out.append((law, c, m.start(), rng))
    for m in _KVKK.finditer(text):
        law = _nearest_law(text, m.start())
        if law is None:
            continue  # another Turkish law (TBK m.146, CMK m.130, Avukatlık Kanunu m.36 ...)
        art, para, pt = m.group(1), m.group(2), m.group(3)
        out.append((law, art + (f"({para})" if para else "") + (f"({pt})" if pt else ""), m.start(), False))
    return out


_LAWTOK = re.compile(r"KVKK|GDPR|AI Act|TBK|VUK|CMK|HMK|TCK|Kanunu|Kanun|Yönetmeliği|Tebliğ|Law No\. \d+")


def _nearest_law(text: str, pos: int) -> str | None:
    """'m.9' style citations: the law named closest before it (within 120 chars), KVKK by default."""
    toks = list(_LAWTOK.finditer(text[max(0, pos - 120):pos]))
    if not toks:
        return "kvkk"
    t = toks[-1].group(0)
    return {"KVKK": "kvkk", "GDPR": "gdpr", "AI Act": "aiact"}.get(t)


def resolve(law: str, cite: str) -> tuple[bool, str, str]:
    art, sub = _key(cite)
    arts = LAW.get(law, {})
    if art not in arts:
        return False, f"{law} Art. {art} does not exist", ""
    if not sub:
        return True, "", " ".join(arts[art].values())
    node = arts[art]
    parts = sub.split(".")
    if law == "aiact" and parts[0] not in node and "0" in node:
        parts = ["0"] + parts  # unnumbered first paragraph, e.g. Art. 113 points
    k = ".".join(parts)
    if k in node:
        txt = " ".join(v for kk, v in node.items() if kk == k or kk.startswith(k + "."))
        return True, "", txt
    return False, f"{law} Art. {art}: no {sub}", ""


_ABBR = re.compile(r"\b(Arts?|m|No|e\.g|i\.e|cf|Rec|para)\. ")


def sentence_at(text: str, pos: int) -> str:
    text = _ABBR.sub(lambda m: m.group(0).replace(". ", "·_"), text)  # same length: positions stay valid
    a = max(text.rfind("\n", 0, pos), text.rfind(". ", 0, pos), text.rfind("| ", 0, pos))
    b_candidates = [i for i in (text.find("\n", pos), text.find(". ", pos)) if i != -1]
    b = min(b_candidates) if b_candidates else len(text)
    # Tables: include the whole row.
    line_start, line_end = text.rfind("\n", 0, pos) + 1, text.find("\n", pos)
    line = text[line_start:line_end if line_end != -1 else len(text)]
    out = line if line.startswith("|") or line.startswith("- ") else text[a + 1:b]
    return out.replace("·_", ". ")


def score_citations(files: dict[str, str]):
    rows, n, ok, ver, ver_bad, unknown = [], 0, 0, 0, 0, 0
    claim_ix = {c["cite"]: c for c in CLAIMS}
    for doc, text in files.items():
        for law, cite, pos, rng in find_citations(text, doc):
            n += 1
            exists, why, lawtext = resolve(law, cite)
            art, sub = _key(cite)
            key = f"{law}:{art}" + (f".{sub}" if sub else "")
            status = "missing" if not exists else "exists"
            if exists:
                ok += 1
                c = None if (rng or doc.startswith("00-")) else claim_ix.get(key)
                if rng or doc.startswith("00-"):
                    status = "exists (range end or overview repeat)"
                elif c:
                    in_law = all(p.lower() in lawtext.lower() for p in c["law_phrase"])
                    ctx = sentence_at(text, pos).lower()
                    in_ctx = any(w.lower() in ctx for w in c["context_any"])
                    if in_law and in_ctx:
                        ver += 1
                        status = "verified"
                    else:
                        ver_bad += 1
                        status = "WRONG: " + ("law text lacks phrase" if not in_law else "cited for another topic")
                else:
                    unknown += 1 if not (rng or doc.startswith("00-")) else 0
                    status = "exists, no claim entry"
            rows.append({"doc": doc, "law": law, "cite": cite, "status": status, "why": why,
                         "context": sentence_at(text, pos)[:160]})
    return {"citations": n, "exist": ok, "verified": ver, "wrong": ver_bad, "unverified": unknown,
            "exist_rate": ok / n if n else 1.0, "verified_rate": ver / (ver + ver_bad) if ver + ver_bad else 1.0,
            "coverage": (ver + ver_bad) / (ver + ver_bad + unknown) if ver + ver_bad + unknown else 1.0}, rows


# ------------------------------------------------------------------------------------------ scenarios
def apply_patch(q: dict, patch: dict) -> dict:
    q = copy.deepcopy(q)
    for path, value in patch.items():
        obj = q
        parts = path.split(".")
        for p in parts[:-1]:
            obj = obj[int(p)] if p.isdigit() else obj[p]
        last = parts[-1]
        if last == "+":
            obj.append(value)
        else:
            obj[int(last) if last.isdigit() else last] = value
    return q


def score_scenarios():
    hit = exp = fa = forb = 0
    rows = []
    packs = {}
    for sc in SCENARIOS:
        q = apply_patch(EXAMPLE, sc.get("patch", {}))
        an = analyse(q)
        got = {f.id: f.severity for f in an.findings}
        miss = [e for e in sc.get("expect", []) if not _match(e, got)]
        alarms = [e for e in sc.get("forbid", []) if _match(e, got)]
        exp += len(sc.get("expect", []))
        hit += len(sc.get("expect", [])) - len(miss)
        forb += len(sc.get("forbid", []))
        fa += len(alarms)
        rows.append({"scenario": sc["name"], "missed": miss, "false_alarms": alarms})
        packs[sc["name"]] = render_all(an)
    return {"expected": exp, "found": hit, "recall": hit / exp if exp else 1.0,
            "forbidden_checks": forb, "false_alarms": fa}, rows, packs


def _match(expect: str, got: dict) -> bool:
    """'art27' or 'art27=action' (finding id, optional severity). Ids ending in ':' match a prefix."""
    fid, _, sev = expect.partition("=")
    keys = [k for k in got if (k.startswith(fid) if fid.endswith(":") else k == fid)]
    return bool(keys) and (not sev or any(got[k] == sev for k in keys))


# ------------------------------------------------------------------------------------------ overclaim
OVERCLAIM = [
    (r"\b(?:is|are|be|being|fully|now|remain)\s+(?:gdpr[- ]|kvkk[- ])?compliant\b", "claims compliance"),
    (r"\bensur(?:es|ing) (?:full )?compliance\b", "claims compliance"),
    (r"\bcompliance (?:is )?guaranteed\b|\bguarantee[sd]? (?:that|compliance|no)\b", "guarantee"),
    (r"\b(?:gdpr|kvkk)[- ]safe\b", "'GDPR-safe' wording"),
    (r"\bno (?:data )?leak(?:age|s)?\b", "'no leakage'"),
    (r"(?<!not )(?<!never )\b(?:fully |truly )?anonymi[sz]ed\b|\banonymous\b", "calls data anonymous"),
    (r"\buyumlu(?:dur|dır)\b|\btam uyum\b|\buyumu sağla(?:r|nır|nmıştır)\b", "uyum iddiası"),
    (r"\bgaranti(?:dir| eder| edilir)\b", "garanti"),
    (r"\banonimdir\b|\banonim veri(?:dir)?\b", "anonim iddiası"),
]
_NEGATION = re.compile(r"(not|never|no|isn't|aren't|değil|olmadığı|söylemeyin|demeyin|iddia etmez)\W+(?:\w+\W+){0,6}$", re.I)


def score_overclaim(all_files: dict[str, dict[str, str]]):
    hits = []
    for pack, files in all_files.items():
        for doc, text in files.items():
            for pat, label in OVERCLAIM:
                for m in re.finditer(pat, text, re.I):
                    before = text[max(0, m.start() - 60):m.start()]
                    quoted = text[max(0, m.start() - 1):m.start()] in ("'", '"', "“", "‘")
                    if _NEGATION.search(before) or quoted:
                        continue
                    hits.append({"pack": pack, "doc": doc, "label": label, "text": text[max(0, m.start() - 60):m.end() + 30]})
    return {"overclaims": len(hits)}, hits


# ------------------------------------------------------------------------------------------ Turkish
TR_CALQUES = [
    (r"\bveri sahibi\b", "ilgili kişi"), (r"\bveri kontrolörü\b", "veri sorumlusu"),
    (r"\bveri işlemcisi?\b", "veri işleyen"), (r"\bdata subject\b", "ilgili kişi"),
    (r"\bcontroller\b", "veri sorumlusu"), (r"\bprocessor\b", "veri işleyen"),
    (r"\bkişisel veri ihlali bildirimi\b(?! \()", None),
    (r"\bgizlilik politikası\b", "aydınlatma metni (KVKK) / bilgilendirme (GDPR)"),
    (r"\bpersonal data\b", "kişisel veri"), (r"\bretention\b", "saklama süresi"),
    (r"\bbreach\b", "ihlal"), (r"\bconsent\b", "açık rıza / rıza"),
]
ASCII_TR = r"\b([Kk]isisel|[Ii]slen\w*|[Ii]liskin|[Ss]aglik\w*|[Gg]orus\w*|[Gg]uvenlik\w*|[Bb]aglant\w*|[Yy]urtdisi|[Oo]zel nitelikli|[Aa]ydinlatma|[Ii]lgili kisi|[Ss]ozlesme\w*|[Bb]asvuru\w*)\b"


def score_turkish(all_files: dict[str, dict[str, str]]):
    words = issues = 0
    rows = []
    for pack, files in all_files.items():
        for doc, text in files.items():
            if not doc.endswith(".tr.md"):
                continue
            words += len(text.split())
            body = re.sub(r"`[^`]*`|\([^)]*(?:GDPR|Art\.|Regulation)[^)]*\)", "", text)
            for pat, want in TR_CALQUES:
                if want is None:
                    continue
                for m in re.finditer(pat, body, re.I):
                    issues += 1
                    rows.append({"pack": pack, "doc": doc, "issue": f"'{m.group(0)}' -> '{want}'"})
            body2 = re.sub(r"\]\([^)]*\)", "]", body)  # link targets are file names
            for m in re.finditer(ASCII_TR, body2):
                issues += 1
                rows.append({"pack": pack, "doc": doc, "issue": f"Turkish letters missing: '{m.group(0)}'"})
    return {"turkish_words": words, "turkish_issues": issues,
            "issues_per_1000_words": round(1000 * issues / words, 2) if words else None}, rows


# ------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--list-cites", action="store_true")
    a = ap.parse_args()
    example_pack = render_all(analyse(EXAMPLE))
    cit, cit_rows = score_citations(example_pack)
    scen, scen_rows, packs = score_scenarios()
    all_packs = {"example": example_pack, **packs}
    over, over_rows = score_overclaim(all_packs)
    tr, tr_rows = score_turkish(all_packs)
    if a.list_cites:
        for r in cit_rows:
            print(f"{r['status'][:28]:28} {r['law']:5} {r['cite']:12} {r['doc']:22} {r['why']}  | {r['context'][:90]}")
    print("Citation accuracy (example pack)")
    print(f"  citations {cit['citations']}, exist {cit['exist']} ({cit['exist_rate']:.1%}), checked against claims "
          f"{cit['verified'] + cit['wrong']} ({cit['coverage']:.0%} coverage): verified {cit['verified']}, wrong "
          f"{cit['wrong']} -> {cit['verified_rate']:.1%}")
    for r in cit_rows:
        if r["status"].startswith(("missing", "WRONG")):
            print(f"    {r['status']}: {r['law']} {r['cite']} in {r['doc']} {r['why']} | {r['context'][:110]}")
    print(f"Gaps flagged ({len(SCENARIOS)} scenarios)")
    print(f"  recall {scen['found']}/{scen['expected']} = {scen['recall']:.1%}; false alarms "
          f"{scen['false_alarms']} of {scen['forbidden_checks']} checks")
    for r in scen_rows:
        if r["missed"] or r["false_alarms"]:
            print(f"    {r['scenario']}: missed {r['missed']} false alarms {r['false_alarms']}")
    print(f"No overclaiming ({sum(len(p) for p in all_packs.values())} documents)")
    print(f"  overclaims {over['overclaims']}")
    for h in over_rows[:15]:
        print(f"    {h['pack']}/{h['doc']}: {h['label']}: ...{h['text']}...")
    print("Turkish wording")
    if tr["turkish_words"]:
        print(f"  {tr['turkish_words']} words, {tr['turkish_issues']} issues ({tr['issues_per_1000_words']} per 1,000 words)")
        for r in tr_rows[:15]:
            print(f"    {r['pack']}/{r['doc']}: {r['issue']}")
    else:
        print("  no Turkish documents in the pack")
    if a.json:
        Path(a.json).write_text(json.dumps({"citations": cit, "scenarios": scen, "overclaim": over, "turkish": tr,
                                            "citation_rows": cit_rows, "scenario_rows": scen_rows,
                                            "overclaim_rows": over_rows, "turkish_rows": tr_rows},
                                           ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
