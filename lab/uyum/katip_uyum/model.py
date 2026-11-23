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

LISTS = ("subjects", "data", "activities", "agents", "vendors", "storage")


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
    for v in q.get("vendors", []):
        w = f"vendor {v.get('id')}"
        enum(w + ".role", v.get("role"), VENDOR_ROLES)
        enum(w + ".receives", v.get("receives"), RECEIVES)
        enum(w + ".dpa", v.get("dpa"), DPA_STATES)
        enum(w + ".transfer_mechanism", v.get("transfer_mechanism"), MECHANISMS)
    for a in q.get("agents", []):
        w = f"agent {a.get('id')}"
        refs(w + ".models", a.get("models"), "vendors")
        refs(w + ".vendors", a.get("vendors"), "vendors")
        enum(w + ".output", a.get("output"), OUTPUTS)
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
        enum(w + ".source", a.get("source"), SOURCES)
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
