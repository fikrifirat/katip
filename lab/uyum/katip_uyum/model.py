"""Load and check the questionnaire (a JSON file that describes an AI agent system's data flows).

`null` (or a missing key) means "we don't know yet". The pack then prints an [OPEN: ...] marker in
the document and lists the question, instead of guessing.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_KINDS = {"ordinary", "contact", "id_number", "financial", "special", "criminal", "minor"}
SOURCES = {"data_subject", "client", "public", "third_party", "generated"}
VENDOR_ROLES = {"processor", "sub_processor", "controller", "joint_controller", "none"}
RECEIVES = {"raw", "masked", "metadata", "none"}
DPA_STATES = {"signed", "accepted_online", "available", "none"}
MECHANISMS = {"adequacy", "dpf", "scc", "bcr", "derogation", "none"}
OUTPUTS = {"internal", "client", "court", "published"}
REVIEW = {True, False, "always", "sometimes", "never"}
CRIMINAL_TYPES = {"conviction", "proceedings", "sanctions_listing", "mixed"}
ROLES = {"controller", "processor", "both"}
PARTNER_ROLES = {"joint_controller", "controller", "processor"}
TIERS = {"free", "paid", "enterprise"}

LISTS = ("subjects", "data", "activities", "agents", "vendors", "storage", "partners")


def sources(act: dict) -> list[str]:
    s = act.get("source")
    return [] if s is None else (s if isinstance(s, list) else [s])


def review_state(agent: dict) -> str:
    """always | sometimes | never | unknown"""
    r = agent.get("human_review")
    return {True: "always", False: "never", None: "unknown"}.get(r, r) if not isinstance(r, str) else r


class QuestionnaireError(ValueError):
    pass


def load(path: str | Path) -> dict:
    q = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(q)
    return q


def _ids(q, key):
    return {x["id"] for x in q.get(key, [])}


def validate(q: dict) -> None:
    """Raise QuestionnaireError on structural mistakes (unknown ids, bad enum values).

    Missing *answers* are not errors: they become open questions in the pack.
    """
    errs = []
    if not isinstance(q.get("system"), dict) or not q["system"].get("name"):
        errs.append("system.name is required")
    if not isinstance(q.get("controller"), dict) or not q["controller"].get("name"):
        errs.append("controller.name is required")
    for key in LISTS:
        items = q.get(key, [])
        if not isinstance(items, list):
            errs.append(f"{key} must be a list")
            continue
        seen = set()
        for i, x in enumerate(items):
            if not isinstance(x, dict) or not x.get("id"):
                errs.append(f"{key}[{i}] needs an id")
                continue
            if x["id"] in seen:
                errs.append(f"{key}: duplicate id {x['id']!r}")
            seen.add(x["id"])

    def enum(where, value, allowed):
        if value is not None and value not in allowed:
            errs.append(f"{where}: {value!r} is not one of {sorted(allowed)}")

    def refs(where, values, key):
        known = _ids(q, key)
        for v in values or []:
            if v not in known:
                errs.append(f"{where}: unknown {key} id {v!r}")

    for d in q.get("data", []):
        enum(f"data {d.get('id')}.kind", d.get("kind"), DATA_KINDS)
        enum(f"data {d.get('id')}.criminal_type", d.get("criminal_type"), CRIMINAL_TYPES)
    enum("controller.role", q.get("controller", {}).get("role"), ROLES)
    for p in q.get("partners", []):
        enum(f"partner {p.get('id')}.role", p.get("role"), PARTNER_ROLES)
    for v in q.get("vendors", []):
        w = f"vendor {v.get('id')}"
        enum(w + ".role", v.get("role"), VENDOR_ROLES)
        enum(w + ".receives", v.get("receives"), RECEIVES)
        enum(w + ".dpa", v.get("dpa"), DPA_STATES)
        enum(w + ".transfer_mechanism", v.get("transfer_mechanism"), MECHANISMS)
        enum(w + ".tier", v.get("tier"), TIERS)
    for a in q.get("agents", []):
        w = f"agent {a.get('id')}"
        refs(w + ".models", a.get("models"), "vendors")
        refs(w + ".vendors", a.get("vendors"), "vendors")
        enum(w + ".output", a.get("output"), OUTPUTS)
        if a.get("human_review") not in REVIEW and a.get("human_review") is not None:
            errs.append(f"{w}.human_review: {a.get('human_review')!r} is not one of true, false, always, sometimes, never")
        for vid, how in (a.get("sends") or {}).items():
            refs(w + ".sends", [vid], "vendors")
            enum(w + f".sends.{vid}", how, RECEIVES)
    for s in q.get("storage", []):
        where = s.get("vendor")
        if where is not None and where not in _ids(q, "vendors"):
            errs.append(f"storage {s.get('id')}.vendor: unknown vendors id {where!r}")
    for a in q.get("activities", []):
        w = f"activity {a.get('id')}"
        refs(w + ".subjects", a.get("subjects"), "subjects")
        refs(w + ".data", a.get("data"), "data")
        refs(w + ".agents", a.get("agents"), "agents")
        refs(w + ".storage", a.get("storage"), "storage")
        for src in sources(a):
            enum(w + ".source", src, SOURCES)
        enum(w + ".role", a.get("role"), {"controller", "processor"})
        refs(w + ".partners", a.get("partners"), "partners")
    if errs:
        raise QuestionnaireError("questionnaire has problems:\n  - " + "\n  - ".join(errs))


def by_id(q: dict, key: str) -> dict:
    return {x["id"]: x for x in q.get(key, [])}


def activity_vendors(q: dict, act: dict) -> list[dict]:
    """Vendors an activity's data reaches: through its agents (models + tools) and its storage."""
    agents, vendors, storage = by_id(q, "agents"), by_id(q, "vendors"), by_id(q, "storage")
    ids: list[str] = []
    for aid in act.get("agents", []):
        ag = agents[aid]
        ids += ag.get("models", []) + ag.get("vendors", [])
    for sid in act.get("storage", []):
        if storage[sid].get("vendor"):
            ids.append(storage[sid]["vendor"])
    out, seen = [], set()
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(vendors[i])
    return out


def activity_data(q: dict, act: dict) -> list[dict]:
    data = by_id(q, "data")
    return [data[d] for d in act.get("data", [])]


def activity_subjects(q: dict, act: dict) -> list[dict]:
    subs = by_id(q, "subjects")
    return [subs[s] for s in act.get("subjects", [])]


def receives(q: dict, vendor: dict) -> str | None:
    """What a vendor gets, worst case over the agents that send to it ('raw' beats 'masked')."""
    order = {"raw": 3, "masked": 2, "metadata": 1, "none": 0}
    seen = [vendor.get("receives")] + [a["sends"][vendor["id"]] for a in q.get("agents", [])
                                         if vendor["id"] in (a.get("sends") or {})]
    seen = [x for x in seen if x]
    return max(seen, key=lambda x: order[x]) if seen else None


def activity_role(q: dict, act: dict) -> str:
    r = act.get("role")
    if r:
        return r
    c = q.get("controller", {}).get("role")
    return c if c in ("controller", "processor") else ("controller" if c is None else "unknown")
