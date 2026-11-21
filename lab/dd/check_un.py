"""Freshness check for MASAK's art. 5 list against the UN Security Council consolidated list.

MASAK's art. 5 list is Türkiye's implementation of UNSC 1267/1988/1989 (ISIL/Al-Qaida and
Taliban). The UN publishes its own list as XML. Comparing the two shows how far behind (or
ahead) the Turkish list is: UN entries missing from MASAK, sorted by UN listing date.

    python lab/dd/check_un.py [--xml consolidated.xml] [--out lab/dd/results/un_check.json]

Only counts and UN reference numbers go into the results file (UN numbers are public IDs).
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "connector"))

from katip_kalkan.dd.match import MATCH, REVIEW, ListIndex  # noqa: E402
from katip_kalkan.dd.net import PoliteClient  # noqa: E402
from katip_kalkan.dd.store import Store  # noqa: E402

UN_XML = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
REGIMES = {"Al-Qaida", "Taliban"}


def un_entries(xml: bytes) -> tuple[list[dict], str]:
    root = ET.fromstring(xml)
    out = []
    for tag in ("INDIVIDUAL", "ENTITY"):
        for e in root.iter(tag):
            lt = (e.findtext("UN_LIST_TYPE") or "").strip()
            if lt not in REGIMES:
                continue
            name = " ".join(x for x in [(e.findtext(f) or "").strip() for f in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")] if x)
            aliases = [(a.findtext("ALIAS_NAME") or "").strip() for a in e.iter(tag + "_ALIAS")]
            out.append({"ref": (e.findtext("REFERENCE_NUMBER") or "").strip(), "regime": lt, "kind": tag.lower(),
                        "listed_on": (e.findtext("LISTED_ON") or "")[:10], "names": [name, *[a for a in aliases if a]]})
    return out, root.get("dateGenerated", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml")
    ap.add_argument("--out", default=str(Path(__file__).with_name("results") / "un_check.json"))
    a = ap.parse_args()
    xml = Path(a.xml).read_bytes() if a.xml else PoliteClient().get(UN_XML).body
    un, generated = un_entries(xml)
    masak = [r for r in Store().records("masak") if r["list"] == "6415-m5-bmgk"]
    idx = ListIndex(masak)
    found, review, missing = 0, 0, []
    for e in un:
        best = 0.0
        for n in e["names"][:6]:
            h = idx.search(n, limit=1, floor=0.5)
            if h:
                best = max(best, h[0].score)
        if best >= MATCH:
            found += 1
        elif best >= REVIEW:
            review += 1
        else:
            missing.append({"ref": e["ref"], "listed_on": e["listed_on"], "regime": e["regime"], "best": round(best, 3)})
    # reverse direction: MASAK art. 5 rows with no UN counterpart (delisted at the UN, or other spelling)
    un_idx = ListIndex([{"rid": e["ref"], "names": e["names"], "ids": [], "birth": ""} for e in un])
    orphan = sum(1 for r in masak if not any(h.score >= REVIEW for n in r["names"][:6] for h in un_idx.search(n, limit=1, floor=0.5)))
    res = {
        "un_generated": generated, "un_entries_1267_1988": len(un),
        "masak_art5_rows": len(masak), "masak_fetched": (Store().last_ok("masak") or {}).get("finished"),
        "un_found_in_masak_match": found, "un_found_in_masak_review": review, "un_not_found": len(missing),
        "un_not_found_by_listing_year": dict(sorted(Counter(m["listed_on"][:4] for m in missing).items())),
        "un_not_found_newest": sorted(missing, key=lambda m: m["listed_on"], reverse=True)[:15],
        "masak_rows_without_un_counterpart": orphan,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "un_not_found_newest"}, ensure_ascii=False, indent=1))
    print("newest UN entries not found:", [(m["listed_on"], m["ref"], m["best"]) for m in res["un_not_found_newest"][:8]])


if __name__ == "__main__":
    main()
