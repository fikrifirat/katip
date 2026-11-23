"""Render the documents (overview + 11 documents in English, 3 in Turkish) as Markdown.

Style rules: cite the article next to each requirement, print [OPEN: ...] instead of guessing, never say
"compliant", and never state as fact something the answers contradict or leave open.
"""
from __future__ import annotations

import re

from . import law
from .model import activity_data, activity_role, effective_role, activity_subjects, activity_vendors, by_id, receives, review_state, sources
from .rules import SEVERITY_LABEL, THEMES, Analysis

DOCS = [
    ("00", "overview", "Pack overview: what to do first, findings, open questions"),
    ("01", "ropa", "Record of processing activities (GDPR Art. 30)"),
    ("02", "dpia", "Data protection impact assessment (GDPR Art. 35)"),
    ("03", "privacy-notice", "Privacy notices (GDPR Arts. 13 and 14)"),
    ("04", "contracts", "Roles and contracts: processors, clients, partners, secrecy (GDPR Arts. 26 and 28)"),
    ("05", "transfers-tia", "International transfers and transfer impact assessment (GDPR Chapter V, KVKK m.9)"),
    ("06", "retention", "Retention and deletion policy (GDPR Art. 5(1)(e), KVKK m.7)"),
    ("07", "breach", "Personal data breach procedure (GDPR Arts. 33 and 34, KVKK m.12/5)"),
    ("08", "dsr", "Data subject request procedure (GDPR Arts. 12 and 15-22, KVKK m.11 and m.13)"),
    ("09", "toms", "Technical and organisational measures (GDPR Art. 32, KVKK m.12)"),
    ("10", "ai-act", "EU AI Act note: role, risk class and duties (Regulation (EU) 2024/1689 as amended)"),
    ("11", "lia", "Legitimate-interests assessments (GDPR Art. 6(1)(f))"),
]
TITLE = {n: t for n, _, t in DOCS}
PURPOSE = {
    "ropa": "What is processed, why, for whom, where, how long. The supervisory authority can ask for it.",
    "dpia": "Whether the risk is high, and what reduces it. Required before go-live when risk is likely high.",
    "privacy-notice": "What clients and other people are told, at collection or within a month.",
    "contracts": "Controller or processor per client; DPA checklist per vendor; joint controllers; secrecy.",
    "transfers-tia": "Which data leaves the EU or Türkiye, on what legal tool, and with what risk.",
    "retention": "How long each kind of data is kept and how it is deleted, including in the agents' memory.",
    "breach": "Who notifies whom, and what happens in the 72 hours after a leak.",
    "dsr": "How access, deletion and other requests are answered within a month.",
    "toms": "The security measures, with what is in place and what is not.",
    "ai-act": "What the EU AI Act asks of this system, and from when.",
    "lia": "The written balancing test for each activity based on legitimate interests.",
}


_ABBR = re.compile(r"\b(Arts?|m|No|e\.g|i\.e|cf|Rec|para|Reg|Dec|Sec|Nr|vs)\.$")


def first_sentence(text: str) -> str:
    """First sentence, without splitting on 'Art. 6' or 'e.g. this'."""
    start = 0
    while True:
        i = text.find(". ", start)
        if i < 0:
            return text if text.endswith(".") else text + "."
        if not _ABBR.search(text[:i + 1]):
            return text[:i + 1]
        start = i + 2


def O(what: str) -> str:
    return f"**[OPEN: {what}]**"


def v(x, what: str) -> str:
    if x is None or x == "" or x == []:
        return O(what)
    if x is True:
        return "yes"
    if x is False:
        return "no"
    return str(x)


def table(head: list[str], rows: list[list[str]]) -> str:
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", "<br>")  # noqa: E731
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def note(x: dict) -> str:
    return f" *Note from the questionnaire: {x['notes']}*" if x.get("notes") else ""


def banner(an: Analysis, num: str) -> str:
    s = an.q["system"]
    return (f"# {num} · {TITLE[num]}\n\n"
            f"**System:** {s['name']} · **Controller:** {an.q['controller']['name']} · "
            f"**Questionnaire dated:** {v(s.get('date'), 'date')}\n\n"
            "> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point "
            "for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or "
            "the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.\n")


def findings_block(an: Analysis, num: str) -> str:
    fs = an.by_doc(num)
    if not fs:
        return ""
    lines = ["## Points for the reviewer", ""]
    for f in fs:
        end = "" if f.title.endswith(("?", ".")) else "."
        lines.append(f"- **{SEVERITY_LABEL[f.severity]}: {f.title}{end}** {f.detail} *({f.cite})*")
    return "\n".join(lines) + "\n"


def kvkk_block(an: Analysis, text: str) -> str:
    return ("## KVKK (Türkiye)\n\n" + text.strip() + "\n") if an.kvkk else ""


def names(items, key="label"):
    return ", ".join(i.get(key) or i.get("name") or i["id"] for i in items) or "none"


def _basis(a, kvkk=False) -> str:
    b = a.get("lawful_basis")
    if not b:
        s = O("Art. 6(1) basis")
    else:
        s = f"GDPR Art. {b} ({law.LAWFUL_BASIS.get(b, '?')})"
        if b == "6(1)(f)":
            s += f". Interest: {v(a.get('legitimate_interest'), 'legitimate interest + balancing test')}"
    if a.get("art9_condition"):
        s += f"; Art. {a['art9_condition']} ({law.ART9.get(a['art9_condition'], '?')})"
    if a.get("art10_basis"):
        s += f"; Art. 10: {a['art10_basis']}"
    return s


def _kvkk_basis(a) -> str:
    if a.get("kvkk_basis"):
        k = a["kvkk_basis"]
        return law.KVKK_ONLY.get(k, k)
    b = a.get("lawful_basis")
    parts = [law.KVKK_BASIS[b] + " " + O("confirm; for client work m.5/2-e may fit better")] if b in law.KVKK_BASIS else [O("KVKK m.5 basis")]
    if a.get("art9_condition"):
        parts.append(law.KVKK_ART9.get(a["art9_condition"], O("KVKK m.6/3 condition")))
    return "; ".join(parts)


def _recipients(q, a) -> list[str]:
    agents = by_id(q, "agents")
    out = []
    outs = {agents[x].get("output") for x in a.get("agents", []) if x in agents}
    if "client" in outs:
        out.append("the client (reports, opinions, results)")
    if "court" in outs:
        out.append("courts and authorities")
    if "published" in outs:
        out.append("the public")
    parts = by_id(q, "partners")
    out += [f"{parts[p]['name']} ({parts[p].get('role', 'partner').replace('_', ' ')})" for p in a.get("partners", []) if p in parts]
    out += a.get("recipients", [])
    return out


def _gdpr_route(an: Analysis, a) -> str:
    if an.eea_controller:
        return "Art. 3(1) (EU establishment)"
    eu = any(s.get("in_eu") for s in activity_subjects(an.q, a))
    if an.art3_2 and eu and a.get("eu_offer_related") is not False:
        return "Art. 3(2), if this activity relates to the offer to people in the EU " + O("confirm per activity")
    if an.q.get("scope", {}).get("eu_clients"):
        return "Through EU clients' SCCs for their data; otherwise KVKK only"
    return O("GDPR route")


# --------------------------------------------------------------------------------------------- 00
def overview(an: Analysis) -> str:
    q = an.q
    s, c = q["system"], q["controller"]
    out = [banner(an, "00")]
    top = an.top(5)
    if top:
        out.append("## Do these first\n\nRanked by severity and by how sensitive the data involved is.\n\n" +
                   "\n".join(f"{i}. **{f.title}.** {first_sentence(f.detail)} *({f.cite})*"
                             for i, f in enumerate(top, 1)) + "\n")
    out.append("## The system in one paragraph\n\n" + v(s.get("description"), "short description") + "\n")
    out.append("## Who is responsible\n\n" + table(["", ""], [
        ["Controller", f"{c['name']} ({law.country(c.get('country'))})"],
        ["Role towards clients", v(c.get("role"), "controller or processor for clients")],
        ["Privacy contact", v(c.get("contact"), "privacy contact")],
        ["DPO", c.get("dpo") or "none appointed (see findings)"],
        ["EU representative (Art. 27)", c.get("eu_representative") or "none"],
        ["Partners", names(q.get("partners", []), "name")],
    ]) + "\n")
    out.append("## Which laws apply, and why\n\n" + ("\n".join(f"- {a}" for a in an.applicability)
                                                       or "- " + O("whether the GDPR applies (Art. 3)")) + "\n")
    rows = [[n, f"[{t}]({n}-{slug}.md)", PURPOSE[slug]] for n, slug, t in DOCS[1:]]
    if an.kvkk:
        rows += [["TR", "[Özet ve yapılacaklar](00-ozet.tr.md)", "Turkish summary of the findings, for the lawyer"],
                 ["TR", "[Kişisel veri işleme envanteri](01-envanter.tr.md)", "Turkish inventory (KVKK, VERBİS)"],
                 ["TR", "[Aydınlatma metni](03-aydinlatma-metni.tr.md)", "Turkish notice under KVKK m.10"]]
    out.append("## The pack\n\n" + table(["#", "Document", "What it is for"], rows) + "\n")
    counts = {}
    for f in an.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    out.append("## All findings, by theme\n\n" + ", ".join(f"{counts.get(k, 0)} {SEVERITY_LABEL[k].lower()}"
                                                          for k in ("action", "risk", "open", "info")) + ".\n")
    for th, label in THEMES.items():
        fs = [f for f in an.findings if f.theme == th]
        if fs:
            out.append(f"### {label}\n\n" + table(["Type", "Finding", "Source", "Docs"],
                                                   [[SEVERITY_LABEL[f.severity], f.title, f.cite, ", ".join(f.docs)]
                                                    for f in fs]) + "\n")
    if an.kvkk:
        out.append("## KVKK map\n\n" + table(["GDPR document", "KVKK counterpart"], [
            ["01 RoPA (Art. 30)", "Kişisel veri işleme envanteri; VERBİS registration (m.16) unless a Board exemption "
                                  "decision covers the firm. Exemption decisions since 2018 cover several professions; "
                                  "check whether lawyers are covered in the current list " + O("decision number, verified")
                                  + ". An exemption from registration does not remove the other duties."],
            ["02 DPIA (Art. 35)", "No statutory DPIA; the Board's security guide expects a risk analysis"],
            ["03 Notice (Arts. 13-14)", "Aydınlatma metni (m.10; Aydınlatma Yükümlülüğü Tebliği), in Turkish"],
            ["04 Contracts (Arts. 26, 28)", "Veri işleyen sözleşmesi; joint liability for security (m.12/2)"],
            ["05 Transfers", "Yurt dışına aktarım (m.9 as amended in 2024): standard contract notified within 5 business days"],
            ["06 Retention", "Saklama ve imha politikası (Silme, Yok Etme veya Anonim Hale Getirme Yönetmeliği), "
                             "required for controllers that must register in VERBİS"],
            ["07 Breach (Arts. 33-34)", "m.12/5: notify the Board 'en kısa sürede', read as 72 hours (Board decision 2019/10)"],
            ["08 Rights (Arts. 15-22)", "m.11 rights; m.13 answer within 30 days, free in principle"],
            ["09 TOMs (Art. 32)", "m.12/1; for special-category data the adequate measures of m.6/4 (Board decision 2018/10)"],
            ["10 AI Act", "No Turkish equivalent in force"],
            ["11 LIA (Art. 6(1)(f))", "KVKK m.5/2-f meşru menfaat: the Board also expects a balancing test"],
        ]) + "\n")
    out.append("## Sources\n\nLists checked " + law.CHECKED + ". AI Act text and dates as amended by " +
               law.AI_ACT_AMENDMENT + ".\n\n" + "\n".join(f"- [{k}]({u})" for k, u in law.SOURCES.items()) + "\n")
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 01
def ropa(an: Analysis) -> str:
    q, c = an.q, an.q["controller"]
    out = [banner(an, "01")]
    out.append("Controller's record under Art. 30(1). The Art. 30(5) exemption for organisations under 250 people does "
               "not apply where processing is not occasional or includes Art. 9 or Art. 10 data.\n")
    out.append("## Controller (Art. 30(1)(a))\n\n" + table(["", ""], [
        ["Name", c["name"]], ["Address", v(c.get("address"), "address")],
        ["Contact", v(c.get("contact"), "privacy contact")],
        ["Representative", c.get("eu_representative") or "none"], ["DPO", c.get("dpo") or "none"]]) + "\n")
    stor = by_id(q, "storage")
    for a in q.get("activities", []):
        vend = activity_vendors(q, a)
        rows = [
            ["Purpose (b)", v(a.get("purpose"), "purpose")],
            ["Role", activity_role(q, a)],
            ["How the GDPR applies", _gdpr_route(an, a)],
            ["Lawful basis", _basis(a)],
        ]
        if an.kvkk:
            rows.append(["KVKK basis", _kvkk_basis(a)])
        rows += [
            ["Data subjects (c)", names(activity_subjects(q, a))],
            ["Personal data (c)", names(activity_data(q, a))],
            ["Source", ", ".join(sources(a)) or O("where the data comes from")],
            ["Recipients (d)", ", ".join(_recipients(q, a)) or O("recipients (clients, co-counsel, courts?)")],
            ["Processors and vendors", ", ".join(f"{x['name']} ({law.country(x.get('country'))})" for x in vend) or "none"],
            ["Transfers outside the EEA (e)", _xfer_summary(an, vend)],
            ["Where it is stored", ", ".join(stor[s].get("what", s) for s in a.get("storage", [])) or O("storage")],
            ["Retention (f)", v(a.get("retention"), "retention period")],
            ["Security (g)", "See document 09 (TOMs)."],
        ]
        out.append(f"## Activity: {a.get('name', a['id'])}\n\n" + table(["Art. 30(1)", "Entry"], rows) + note(a) + "\n")
    if c.get("role") in ("processor", "both") or any(a.get("role") == "processor" for a in q.get("activities", [])):
        out.append("## Processor's record (Art. 30(2))\n\nFor work done on a client's instructions. One row per client.\n\n" +
                   table(["Client (controller)", "Categories of processing", "Transfers and safeguards", "Measures"],
                         [[O("client"), O("e.g. DD research on instructions"), "document 05", "document 09"]]) + "\n")
    out.append(findings_block(an, "01"))
    out.append(kvkk_block(an, "The Turkish inventory is [01-envanter.tr.md](01-envanter.tr.md). VERBİS (m.16): see the "
                              "KVKK map in document 00."))
    return "\n".join(out)


def _xfer_summary(an: Analysis, vend) -> str:
    ids = {x["id"] for x in vend}
    ts = [t for t in an.transfers if t.vendor["id"] in ids and t.route not in ("EEA", "same country")]
    if not ts:
        return "none"
    return "; ".join(f"{t.vendor['name']} → {law.country(t.country)} ({t.route})" for t in ts)


# --------------------------------------------------------------------------------------------- 02
def dpia(an: Analysis) -> str:
    q = an.q
    out = [banner(an, "02")]
    mark = {True: "yes", False: "no", None: "unknown"}
    out.append("## 1. Is a DPIA required? (Art. 35(1), WP248 rev.01)\n\n" + table(
        ["EDPB criterion", "Met?", "Why"], [[label, mark[met], why] for _, label, met, why in an.dpia_criteria]) +
        f"\n\n**At least {an.dpia_min} of 9 criteria met" + (f"; {an.dpia_unknown} unanswered" if an.dpia_unknown else "") +
        ".** " + (("Two or more usually mean a DPIA is required. The system is already in use, so this DPIA is "
                   "overdue: Art. 35(1) asks for it before the processing starts. Complete it now, and pause the "
                   "highest-risk flows until it is done." if (q["system"].get("stage") or "").lower() in ("production", "live", "in use")
                   else "Two or more usually mean a DPIA is required: treat this document as mandatory and complete it "
                   "before go-live.") if an.dpia_required else
                  "Fewer than two so far: a DPIA may not be mandatory. Answer the open criteria before deciding.") + "\n")
    vend = by_id(q, "vendors")
    out.append("## 2. Systematic description (Art. 35(7)(a))\n\n" + v(q["system"].get("description"), "description") +
               "\n\n" + table(["Agent", "What it does", "Models and tools", "Lawyer reads output first", "Output goes to"], [
                   [a.get("name", a["id"]), v(a.get("does"), "task"),
                    ", ".join(vend[m]["name"] + (f" ({a['sends'][m]})" if m in (a.get("sends") or {}) else "")
                              for m in a.get("models", []) + a.get("vendors", []))
                    + (("; tools: " + ", ".join(a["tools"])) if a.get("tools") else ""),
                    {"always": "always", "sometimes": "sometimes", "never": "no", "unknown": O("review?")}[review_state(a)],
                    v(a.get("output"), "output")]
                   for a in q.get("agents", [])]) + "\n\nPurposes and data per activity: document 01.\n")
    out.append("## 3. Necessity and proportionality (Art. 35(7)(b))\n\n" + table(
        ["Question", "Answer for this system"], [
            ["Is each data item needed for the purpose? (Art. 5(1)(c))", _minimisation(q)],
            ["Lawful bases", "Document 01, per activity; balancing tests in document 11."],
            ["Retention limits", "Document 06."], ["Information to people", "Document 03."],
            ["Rights handling", "Document 08."], ["Processors and transfers", "Documents 04 and 05."],
        ]) + "\n")
    out.append("## 4. Risks to people (Art. 35(7)(c))\n\nLikelihood and severity before the measures in section 5. "
               "Generated from the answers; the reviewer should adjust them.\n\n" +
               table(["#", "Risk to the people concerned", "Likelihood", "Severity", "Triggered by"], _risks(an)) + "\n")
    out.append("## 5. Measures (Art. 35(7)(d))\n\nStatus comes from the answers: a measure is only marked in place "
               "when the questionnaire says so.\n\n" + table(["Measure", "Status", "Source"], _measures(q)) + "\n")
    out.append("## 6. Residual risk and sign-off\n\n" + table(["", ""], [
        ["Residual risk after measures", O("reviewer's conclusion: low / medium / high")],
        ["Prior consultation needed (Art. 36)?", "Only if high residual risk remains: " + O("yes / no")],
        ["DPO advice (Art. 35(2))", O("advice, or 'no DPO'")],
        ["Views of data subjects (Art. 35(9))", O("sought / not appropriate, with reason")],
        ["Approved by, date", O("name, date")],
        ["Review date", O("at least yearly, and on any new agent, model or vendor")],
    ]) + "\n")
    out.append(findings_block(an, "02"))
    out.append(kvkk_block(an, "KVKK has no statutory DPIA. Keeping this one also covers the risk analysis the Board's "
                              "security guide expects under m.12/1."))
    return "\n".join(out)


def _minimisation(q) -> str:
    sec = q.get("security", {})
    raw = [x["name"] for x in q.get("vendors", []) if receives(q, x) == "raw" and x.get("country") != "LOCAL"]
    if sec.get("masking_before_cloud") is True and not raw:
        s = ("Names, ID numbers, contact details and addresses are masked on the device before any text goes to a "
             "cloud model; detected values are masked and leak-checked before the text leaves the computer.")
    elif raw:
        s = "Raw text goes to: " + ", ".join(raw) + ". " + O("why raw text is necessary for each")
    else:
        s = O("is text masked before the cloud call?")
    return s + " " + O("data items that could be dropped")


def _risks(an: Analysis):
    q = an.q
    kinds = {d.get("kind") for d in q.get("data", [])}
    vend = q.get("vendors", [])
    raw = any(receives(q, x) == "raw" and x.get("country") != "LOCAL" for x in vend)
    acts, agents = q.get("activities", []), q.get("agents", [])
    rows = []

    def r(text, lik, sev, why):
        rows.append([str(len(rows) + 1), text, lik, sev, why])

    if "criminal" in kinds:
        r("A person is wrongly linked to sanctions, crime or insolvency (false name match), harming reputation or a deal",
          "medium", "high", "screening against lists by name")
    if any(a.get("labels_people") for a in acts):
        r("A per-person risk label is wrong, unexplained, or reused beyond the matter", "medium", "high", "per-person labels")
    r("The model invents facts or citations about a person and a lawyer relies on them", "medium",
      "high" if "criminal" in kinds else "medium", "LLM-written drafts")
    unrev = [a["name"] for a in agents if a.get("output") in ("client", "court", "published") and review_state(a) != "always"]
    if unrev:
        r("An unreviewed output goes to the wrong recipient or states something wrong about a person", "medium", "high",
          "agents without consistent review: " + ", ".join(unrev))
    r("Client or third-party data leaks through a vendor (breach, logs, staff access)",
      "medium" if raw else "low", "high" if kinds & {"special", "criminal"} else "medium",
      "raw text to cloud vendors" if raw else "masked text to cloud vendors")
    if any(t.route not in ("EEA", "adequacy", "DPF", "same country") for t in an.transfers):
        r("Authorities abroad access data held by a vendor in a country without an adequacy decision", "low", "high",
          "transfers on SCCs, onward transfers, or without a tool")
    if not an.eea_controller and q.get("scope", {}).get("eu_clients"):
        r(f"Authorities in {law.country(q['controller'].get('country'))} access EU clients' data held by the firm itself",
          O("reviewer, from the TIA in document 05"), "high", "the firm is the importer of EU data")
    r("Prompt injection in a fetched document makes an agent leak or alter data", "medium", "medium",
      "agents that read outside documents and call tools")
    r("People cannot exercise rights because they never learn about the processing", "high" if any(
        s in ("client", "public", "third_party") for a in acts for s in sources(a)) else "low", "medium",
      "data collected about third parties (Art. 14)")
    if "minor" in kinds or any(s.get("children") for s in q.get("subjects", [])):
        r("Children's data (e.g. dependants in compensation claims) is exposed or kept too long", "low", "high",
          "children in case files")
    r("Data kept longer than needed in agent memory, vector stores or vendor logs", "medium", "medium",
      "retention across several stores")
    return rows


def _status(x, planned=False):
    if x is True:
        return "in place"
    if x is False:
        return "not in place"
    if isinstance(x, str) and x:
        return f"answer: {x}; status: {O('reviewer')}"
    return O("in place?")


def _measures(q):
    sec, agents = q.get("security", {}), q.get("agents", [])
    raw = any(receives(q, x) == "raw" and x.get("country") != "LOCAL" for x in q.get("vendors", []))
    mask = sec.get("masking_before_cloud")
    rows = [["Mask personal data on the device before cloud model calls; keep the key locally (Katip Kalkan)",
             "in place for some vendors only" if mask and raw else _status(mask), "GDPR Arts. 25, 32(1)(a)"]]
    rev = {review_state(a) for a in agents if a.get("output") in ("client", "court", "published")}
    rows.append(["A named lawyer approves every output before it leaves the firm",
                 "in place" if rev == {"always"} else ("not in place for every agent" if rev & {"never", "sometimes"} else O("in place?")),
                 "GDPR Arts. 5(1)(d), 22"])
    labels = any(a.get("labels_people") for a in q.get("activities", []))
    rows.append(["Screening shows the source record and link for each hit; no score about a person",
                 "not in place (per-person labels)" if labels else O("in place?"), "GDPR Art. 5(1)(d); AI Act Art. 5(1)(d)"])
    tr = [x for x in q.get("vendors", []) if x.get("trains_on_data") is True]
    rows.append(["No training on inputs, shortest retention, in each vendor contract",
                 ("not in place: " + ", ".join(x["name"] for x in tr)) if tr else O("confirmed per vendor?"), "GDPR Art. 28"])
    rows.append(["Fetched documents treated as data, never instructions; tool allow-list per agent",
                 _status(sec.get("agent_guardrails")), "GDPR Art. 32(1)(b)"])
    rows.append(["Retention enforced in every store, incl. embeddings and logs (document 06)", O("in place?"), "GDPR Art. 5(1)(e)"])
    rows.append(["Art. 14 notice for third parties, or a documented exemption (document 03)", O("in place?"), "GDPR Art. 14"])
    for k, label, cite in (("mfa", "Multi-factor login", "GDPR Art. 32(1)(b)"),
                           ("encryption_at_rest", "Encryption at rest", "GDPR Art. 32(1)(a)"),
                           ("logging", "Logs of who and which agent accessed what", "GDPR Arts. 5(2), 32(1)(b)")):
        rows.append([label, _status(sec.get(k)), cite])
    return rows


# --------------------------------------------------------------------------------------------- 03
def notice(an: Analysis) -> str:
    q, c = an.q, an.q["controller"]
    acts = q.get("activities", [])
    out = [banner(an, "03")]
    out.append("Two notices: **A** for clients and people who give their data directly (Art. 13), **B** for people "
               "whose data comes from clients or public sources, such as the subjects of a due-diligence report "
               "(Art. 14). Plain language is required (Art. 12(1)); translate into the languages of the people "
               "concerned. The Turkish notice under KVKK m.10 is [03-aydinlatma-metni.tr.md](03-aydinlatma-metni.tr.md).\n")

    def purpose_rows(group):
        if not group:
            return O("which activities collect data from these people") + "\n"
        return table(["Purpose", "Legal basis", "How long"], [
            [v(a.get("purpose"), "purpose"), _basis(a), v(a.get("retention"), "retention")] for a in group])

    vend = [x for x in q.get("vendors", []) if receives(q, x) not in ("none", None) and x.get("country") != "LOCAL"]
    signed = [x for x in vend if effective_role(x) in ("processor", "sub_processor") and x.get("dpa") in ("signed", "accepted_online")]
    other = [x for x in vend if x not in signed]
    recips = ("Service providers bound by contract to our instructions: " +
              ("; ".join(f"{x['name']} ({x.get('service', '')})" for x in signed) or "none") + ".")
    if other:
        recips += (" Other recipients: " + "; ".join(f"{x['name']} ({x.get('service', '')}, "
                                                    f"{'acts on its own account' if x.get('role') in ('controller', 'joint_controller') else O('contract status')})"
                                                    for x in other) + ".")
    parts = q.get("partners", [])
    if parts:
        recips += " Law firms we work with on some matters: " + "; ".join(f"{p['name']} ({law.country(p.get('country'))})" for p in parts) + "."
    if any(a2.get("output") == "client" for a2 in q.get("agents", [])):
        recips += " Our clients receive the reports and opinions we prepare for them."
    masked = [x["name"] for x in vend if receives(q, x) == "masked"]
    if masked:
        recips += (" Before text is sent to " + ", ".join(masked) + ", the names, ID numbers, contact details and addresses "
                   "that our masking tool detects are replaced with placeholders on our own computer" +
                   (" " + O("list the ID types the masking profile in use does not detect, e.g. foreign tax or "
                            "citizen numbers") if any(f.id == "maskprofile" and f.severity == "risk" for f in an.findings) else "") + ". These providers therefore receive pseudonymised "
                   "text; it is still personal data for us.")
    xfers = [t for t in an.transfers if t.route not in ("EEA", "same country")]
    agents = q.get("agents", [])
    out_agents = [a for a in agents if a.get("output") in ("client", "court", "published")]
    if out_agents and all(review_state(a) == "always" for a in out_agents):
        ai_txt = ("We use AI systems to sort documents, research and draft. A lawyer reviews every result before it "
                  "leaves our office; no decision about you is made by a machine alone (Art. 22).")
    else:
        ai_txt = ("We use AI systems to sort documents, research and draft. " +
                  O("describe truthfully which outputs a lawyer reviews before they are sent; the answers say some are "
                    "sent without review") + " No decision with legal effect about you is made by a machine alone (Art. 22).")
    rights = ("You can ask for access (Art. 15), correction (16), deletion (17), restriction (18), portability where it "
              "applies (20), and object to processing based on legitimate interests (21).")
    if any(a.get("lawful_basis") == "6(1)(a)" or a.get("art9_condition") == "9(2)(a)" for a in acts):
        rights += " Where we rely on consent you can withdraw it at any time (Art. 7(3))."
    rights += (" Legal professional secrecy can limit these rights where the law of a Member State provides for it "
               "(Art. 23) " + O("which national law applies") + ". You can complain to a supervisory authority, in "
               "particular in the EU country where you live or work (Art. 77).")
    who = f"{c['name']}, {v(c.get('address'), 'address')}. Privacy questions: {v(c.get('contact'), 'contact')}."
    if c.get("dpo"):
        who += f" Data protection officer: {c['dpo']}."
    if c.get("eu_representative"):
        who += f" EU representative (Art. 27): {c['eu_representative']}."
    elif any(f.id == "art27" for f in an.findings):
        who += " EU representative (Art. 27): " + O("name and contact of the representative") + "."
    common = [
        "## Who we are\n\n" + who,
        None,
        "## Who receives it\n\n" + recips,
        "## Transfers outside the EU/EEA\n\n" + ("; ".join(
            f"{t.vendor['name']} ({law.country(t.country)}): {t.route if t.route != 'unknown' else O('transfer tool')}"
            for t in xfers) + ". Ask us for a copy of the safeguards." if xfers else "None."),
        "## Use of AI\n\n" + ai_txt,
        "## Your rights\n\n" + rights,
    ]
    direct = [a for a in acts if "data_subject" in sources(a)]
    third = [a for a in acts if any(s in ("client", "public", "third_party") for s in sources(a))]
    what = "## What we do with your data, on what basis, for how long\n\n"
    a_parts = common[:1] + [what + purpose_rows(direct)] + common[2:]
    b_parts = common[:1] + [what + purpose_rows(third)] + common[2:]
    out.append("# A · Clients and people who give us their data (Art. 13)\n\n" + "\n\n".join(a_parts) +
               "\n\n## Do you have to give us the data?\n\nThe data is needed to take on and run your matter; "
               "without it we cannot act for you (Art. 13(2)(e)).\n")
    if third:
        seen, cat_list = set(), []
        for a in third:
            for d in activity_data(q, a):
                if d["id"] not in seen:
                    seen.add(d["id"])
                    cat_list.append(d)
        out.append("# B · People we receive data about from others (Art. 14)\n\n" + "\n\n".join(b_parts) +
                   f"\n\n## Which data, and from where (Art. 14(1)(d), 14(2)(f))\n\nCategories: {names(cat_list)}. "
                   "Sources: " + ", ".join(sorted({a.get('source_detail') or ", ".join(sources(a)) for a in third})) + ".\n\n"
                   "## When you are told (Art. 14(3))\n\nWithin one month of receiving the data, or at first contact. "
                   "**Exemption check (Art. 14(5)); the reviewer must pick one and document it:**\n\n"
                   "- 14(5)(b) informing would be impossible or need disproportionate effort, or would seriously "
                   "impair the purpose (e.g. tipping off the target of a DD). Then publish this notice and take other "
                   "measures.\n"
                   "- 14(5)(d) the data must stay confidential under professional secrecy regulated by **Union or "
                   "Member State** law. A Turkish attorney's secrecy duty (Avukatlık Kanunu m.36) is not Member State "
                   "law; check whether the EU client's own lawyers' secrecy covers the matter.\n"
                   "- Otherwise: send this notice. " + O("chosen route") + "\n")
    out.append(findings_block(an, "03"))
    out.append(kvkk_block(an, "The Turkish aydınlatma metni is a separate file "
                              "([03-aydinlatma-metni.tr.md](03-aydinlatma-metni.tr.md)): KVKK m.10 and the Tebliğ "
                              "require it at collection, separate from any request for açık rıza."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 04
CHECKS_28 = [
    ("28(3)", "Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated"),
    ("28(3)(a)", "Processes only on documented instructions, including on transfers"),
    ("28(3)(b)", "Staff are bound by confidentiality"),
    ("28(3)(c)", "Takes all Art. 32 security measures"),
    ("28(2), 28(3)(d), 28(4)", "Sub-processors only with prior authorisation; same terms flow down; you can object to new ones"),
    ("28(3)(e)", "Helps you answer data subject requests"),
    ("28(3)(f)", "Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36)"),
    ("28(3)(g)", "Deletes or returns all data at the end; says how long logs and backups persist"),
    ("28(3)(h)", "Makes information available and allows audits; tells you if an instruction breaks the law"),
    ("33(2)", "Notifies you of a breach without undue delay (agree a number of hours)"),
    ("Ch. V", "Transfer tool named (SCC module) with its sub-processor countries"),
    ("AI-specific", "No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered)"),
    ("AI-specific", "Abuse-monitoring access by vendor staff described and limited"),
    ("Secrecy", "Confidentiality undertaking covering client secrets, incl. staff and sub-processors"),
]


def contracts(an: Analysis) -> str:
    q, c = an.q, an.q["controller"]
    out = [banner(an, "04")]
    out.append("## Controller or processor towards each client\n\nA law firm giving legal advice normally decides why "
               "and how client data is used, so it is a controller (EDPB Guidelines 07/2020, which give lawyers as an "
               "example). It is a processor only for work it does strictly on a client's instructions for the client's "
               "purposes. The answer decides the contract each client needs:\n\n" + table(
                   ["If you are…", "Contract with the EU client", "Your duties", "Breach notice goes to"], [
                       ["Controller (usual)", "SCC Module One if you are outside the EEA; no Art. 28 contract",
                        "All controller duties for your own processing", "Supervisory authority (Art. 33(1)); under the "
                        "SCCs also the exporting client"],
                       ["Processor (on instructions)", "Art. 28(3) contract (a German client calls it AVV); SCC Module Two "
                        "if outside the EEA", "Processor duties: instructions, Art. 30(2) record, help with requests",
                        "The client, without undue delay (Art. 33(2))"],
                   ]) + f"\n\nThis questionnaire says: **{v(c.get('role'), 'role')}**." + (
                   " " + O("list which clients and matters are processor work") if c.get("role") == "both" else "") + "\n")
    parts = q.get("partners", [])
    if parts:
        rows = []
        for p in parts:
            rows.append([p["name"], law.country(p.get("country")), (p.get("role") or "?").replace("_", " "),
                         v(p.get("arrangement"), "arrangement in place?")])
        out.append("## Partners and co-counsel\n\n" + table(["Firm", "Country", "Role", "Arrangement"], rows) +
                   "\n\nFor joint controllers, the Art. 26 arrangement must say: who gives the notices (Arts. 13-14), who "
                   "answers requests (Arts. 15-22), who notifies breaches, and a contact point; its essence must be "
                   "available to the people concerned (Art. 26(2)). People can exercise their rights against either "
                   "firm (Art. 26(3)).\n")
    sec = q.get("secrecy") or {}
    out.append("## Professional secrecy\n\n" + table(["Regime", "Applies?"], [
        [law.SECRECY["TR"], v(sec.get("turkish_lawyer"), "Turkish lawyer's secrecy applies?") if q.get("secrecy") is not None else O("secrecy regimes")],
        [law.SECRECY["DE"], ", ".join(sec.get("client_regimes", [])) or O("does a foreign law firm instruct you?")],
    ]) + "\n\nEach vendor that sees client text must accept confidentiality terms that cover client secrets; the "
         "checklist below has a row for it.\n")
    out.append("## Vendors\n\nMost AI vendors offer a standard DPA; you usually cannot negotiate it, but you must read it "
               "against this list and record gaps. A missing term is a reason to choose another tier or vendor, or to "
               "mask more before sending.\n")
    for x in q.get("vendors", []):
        rcv = receives(q, x)
        if x.get("country") == "LOCAL" or rcv in ("none", None):
            continue
        role = effective_role(x)
        if role != x.get("role"):
            role = f"{role} (answered: {x.get('role')}; a free tier without a DPA gives no Art. 28 terms)"
        head = (f"### {x['name']}: {x.get('service', '')}\n\n" + table(["", ""], [
            ["Role", v(role, "processor or controller")],
            ["Country / region", f"{law.country(x.get('country'))} / {v(x.get('region'), 'region')}"
             + (f" (parent: {law.country(x['parent_country'])})" if x.get("parent_country") else "")],
            ["Tier", v(x.get("tier"), "free / paid / enterprise")],
            ["Receives", v(rcv, "raw, masked or metadata")],
            ["DPA status", v(x.get("dpa"), "DPA status")],
            ["Vendor retention", v(x.get("retention"), "how long the vendor keeps inputs and outputs")],
            ["Trains on data", v(x.get("trains_on_data"), "training on inputs?")],
            ["Sub-processor list published", v(x.get("subprocessors_published"), "sub-processor list")],
        ]) + note(x))
        if role in ("controller", "joint_controller"):
            out.append(head + "\n\nThis vendor acts as a **controller** for the data it receives, so Art. 28 does not "
                       "apply. Check its own privacy terms, the purpose it uses the data for, and whether sharing with "
                       "it is covered by your lawful basis and notice (document 03)." +
                       (" Joint controllers need an Art. 26 arrangement." if role == "joint_controller" else "") + "\n")
            continue
        out.append(head + "\n\n" + table(["GDPR", "Term", "In the DPA?", "Clause / note"],
                                         [[a, t, "☐ yes ☐ no", ""] for a, t in CHECKS_28]) + "\n")
    out.append(findings_block(an, "04"))
    out.append(kvkk_block(an, "KVKK has no equivalent of GDPR Art. 28's list of terms, but the controller is jointly "
                              "liable with the veri işleyen for security (m.12/2), so the Board expects a written "
                              "contract with security terms. The same checklist works. If the vendor is abroad, the "
                              "contract alone is not a transfer tool: see document 05."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 05
def tia(an: Analysis) -> str:
    q, c = an.q, an.q["controller"]
    out = [banner(an, "05")]
    rows = [[t.vendor["name"], law.country(t.country), v(t.receives, "what"), t.route,
             "yes" if t.needs_tia else "no", "yes" if t.kvkk_transfer else "no"] for t in an.transfers]
    out.append("## Map of data leaving the EU/EEA or Türkiye\n\n" + (table(
        ["Vendor", "Country", "Receives", "GDPR route", "TIA needed", "KVKK m.9 transfer"], rows) if rows else
        "No vendor outside the controller's own computer receives personal data.") + "\n\n"
        "GDPR routes: **EEA** no transfer; **adequacy** Art. 45 decision; **DPF** a US organisation certified under the "
        "EU-US Data Privacy Framework, usable by exporters in the EU/EEA; **SCC** Art. 46(2)(c) standard clauses "
        "(Decision 2021/914), which need this assessment; **onward (client SCCs)** a firm outside the EU passes EU "
        f"clients' data on, governed by {law.SCC_CLAUSES['onward']} of the SCCs it signed with them; **same country** "
        "the vendor sits where the controller does.\n")
    if q.get("scope", {}).get("eu_clients") and not an.eea_controller:
        role = "processor" if c.get("role") == "processor" else "controller"
        mod = law.SCC_MODULES[("controller", role)]
        cc = law.country(c.get("country"))
        cats = names(q.get("data", []))
        subs = names(q.get("subjects", []))
        out.append(f"## EU clients sending data to {cc}\n\nEach EU client exporting files to you needs the SCCs and its "
                   f"own TIA about {cc}. Proposed module: **{mod}**" + (" (and Module Two for matters where you act on "
                   "instructions)" if c.get("role") == "both" else "") + ". Pre-filled annexes, for the reviewer to "
                   "complete:\n\n" + table(["SCC Annex", "Content"], [
                       ["I.A Data importer", f"{c['name']}, {v(c.get('address'), 'address')}; contact "
                                             f"{v(c.get('contact'), 'contact')}; role: {role}"],
                       ["I.B Categories of data subjects", subs],
                       ["I.B Categories of data", cats],
                       ["I.B Sensitive data and safeguards", "See documents 02 and 09; masking before any cloud call where "
                                                             "configured"],
                       ["I.B Purpose", "; ".join(a.get("purpose") or a["name"] for a in q.get("activities", []))],
                       ["I.B Retention", "Document 06"],
                       ["I.B Onward recipients", ", ".join(t.vendor["name"] for t in an.transfers) or "none"],
                       ["II Technical and organisational measures", "Document 09"],
                   ]) + f"\n\n**Local laws a TIA about {cc} has to discuss** ({law.SCC_CLAUSES['local_laws']}; "
                   f"{law.SCC_CLAUSES['gov_access']}). Candidates for the reviewing lawyer to confirm and analyse, "
                   "not a finished assessment:\n\n" + "\n".join(f"- {x}" for x in law.TR_ACCESS_LAWS) + "\n\n" +
                   O("conclusion: are there laws or practices that prevent the importer from meeting the SCCs, and "
                     "which supplementary measures address them?") + "\n")
    for t in [t for t in an.transfers if t.needs_tia]:
        x = t.vendor
        tool = {"onward (client SCCs)": "Onward transfer under the clients' SCCs: the recipient accepts the SCCs (or "
                                         "another Chapter V safeguard). " + O("which tool the vendor offers"),
                "SCC": "SCCs " + O("module and annexes"), "BCR": "BCRs"}.get(t.route, O("transfer tool"))
        out.append(f"## TIA: {x['name']} ({law.country(t.country)})\n\nSteps from EDPB Recommendations 01/2020.\n\n" +
                   table(["Step", "Assessment"], [
                       ["1. Know the transfer", f"{x.get('service', '')}; data: {v(t.receives, 'what')}; "
                                                f"region: {v(x.get('region'), 'region')}; sub-processor list: "
                                                f"{v(x.get('subprocessors_published'), 'sub-processors')}"],
                       ["2. Transfer tool", tool],
                       ["3. Laws and practice of the destination", O("government access laws that apply to this "
                                                                     "vendor, e.g. FISA 702 for US providers")],
                       ["4. Supplementary measures", "Masking on the device before sending (the vendor never gets "
                        "the key); encryption in transit" if t.receives == "masked" else O("supplementary measures; the "
                        "text is sent unmasked")],
                       ["5. Procedural steps", "If SCCs are changed or another tool is used, check whether Art. 46(3) "
                                               "authorisation is needed"],
                       ["6. Re-evaluate", O("date; at least yearly and on vendor changes")],
                   ]) + "\n")
    out.append(findings_block(an, "05"))
    out.append(kvkk_block(an,
        "Since the amendment by Law No. 7499 (in force 1 June 2024) and the Regulation on the Procedures and "
        "Principles for the Transfer of Personal Data Abroad (10 July 2024), KVKK m.9 works like GDPR Chapter V: an "
        "adequacy decision of the Board, or appropriate safeguards (standard contract in the Board's form, notified to "
        "the Authority within 5 business days of signing; binding corporate rules; written undertaking with Board "
        "permission), or the occasional-transfer exceptions in m.9/6. Each vendor marked 'KVKK m.9 transfer' needs one "
        "of these, separately from its GDPR tool. The EU-US Data Privacy Framework has no effect under KVKK."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 06
def retention(an: Analysis) -> str:
    q = an.q
    out = [banner(an, "06")]
    out.append("Personal data is kept no longer than needed for the purpose (Art. 5(1)(e)). In an agent system data "
               "is copied into places people forget: prompts, tool outputs, embeddings, caches, logs, the vendor's "
               "own logs, backups, sent e-mail. Each row below needs an owner and a deletion method.\n")
    rows = []
    for s in q.get("storage", []):
        vend = by_id(q, "vendors").get(s.get("vendor")) if s.get("vendor") else None
        where = "own computer" if not vend or vend.get("country") == "LOCAL" else vend["name"]
        rows.append([s.get("what", s["id"]), where, v(s.get("retention"), "period"),
                     v(s.get("deletion"), "how deleted"), "yes" if s.get("encrypted") else v(s.get("encrypted"), "encrypted?")])
    model_ids = {m for a in q.get("agents", []) for m in a.get("models", [])}
    for x in q.get("vendors", []):
        if x["id"] in model_ids and receives(q, x) in ("raw", "masked") and x.get("country") != "LOCAL":
            rows.append([f"Prompts and outputs kept by {x['name']}", x["name"], v(x.get("retention"), "vendor retention"),
                         "by vendor; confirm in DPA", "vendor"])
    out.append("## Schedule\n\n" + table(["Data / store", "Where", "Kept for", "Deleted how", "Encrypted"], rows) + "\n")
    out.append("## Per purpose\n\n" + table(["Activity", "Retention", "Reason / legal basis for the period"], [
        [a.get("name", a["id"]), v(a.get("retention"), "period"), v(a.get("retention_reason"), "reason")]
        for a in q.get("activities", [])]) + "\n")
    out.append("## Rules\n\n- When a matter closes, the matter's prompts, agent memory and embeddings are deleted "
               "with it, not only the documents.\n- Deletion runs on a schedule " + O("how often") + " and is logged.\n"
               "- Backups age out within " + O("backup retention") + "; restored backups are re-cleaned.\n"
               "- Legal holds pause deletion for the affected matter only, with a written reason.\n")
    out.append(findings_block(an, "06"))
    out.append(kvkk_block(an, "Controllers that must register in VERBİS must also keep a written saklama ve imha "
                              "politikası and run periodic destruction at most every 6 months (Silme, Yok Etme veya "
                              "Anonim Hale Getirme Yönetmeliği m.5, m.11). Turkish limitation periods often set the outer "
                              "limit for client files: TBK m.146 sets 10 years in general, but claims from a mandate "
                              "(vekâlet) against a lawyer fall under the 5 years of TBK m.147/5; the reviewer should "
                              "choose with reasons " + O("period and reason") + ". VUK m.253: 5 years for books."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 07
def breach(an: Analysis) -> str:
    q, sec, c = an.q, an.q.get("security", {}), an.q["controller"]
    out = [banner(an, "07")]
    out.append("## Who\n\n" + table(["Role", "Person"], [
        ["Breach lead (decides and notifies)", v(sec.get("incident_owner"), "named person")],
        ["Deputy", O("deputy")], ["Technical contact", O("who can switch agents off and pull logs")],
    ]) + "\n")
    rows = [
        ["0 h: aware", "Someone has reasonable certainty that personal data was lost, disclosed, altered or "
                       "accessed without authority. Log the time. Contain: revoke keys, pause agents, stop syncs.",
         "Art. 4(12); EDPB 9/2022"],
        ["< 24 h", "Assess: what data, how many people, masked or raw, who could see it, likely consequences.", ""],
        ["≤ 72 h", "Notify the competent supervisory authority unless the breach is unlikely to result in a risk. Late? "
                   "Give reasons. Information can come in phases.", "Art. 33(1), 33(4)"],
        ["Without undue delay", "Tell the people affected if the risk to them is high, in plain language, with what "
                                "they can do. Not needed if the data was unintelligible to anyone without access, as with "
                                "proper encryption. Masked text is not unintelligible: it still carries the facts, so "
                                "masking lowers the risk but does not by itself meet Art. 34(3)(a).",
         "Art. 34(1), 34(3)"],
        ["Always", "Record every breach, even unnotified ones: facts, effects, actions, reasons.", "Art. 33(5)"],
    ]
    if an.kvkk:
        rows.insert(3, ["≤ 72 h (KVKK)", "Notify the KVKK Board 'en kısa sürede', interpreted as 72 hours, on its breach "
                                         "form.", "KVKK m.12/5; Board decision 2019/10"])
    out.append("## Clock\n\n" + table(["When", "What", "Source"], rows) + "\n")
    who = [["Controller under the GDPR (Art. 3(1) or 3(2))", "The supervisory authority (Art. 33); people if high risk (Art. 34)"]]
    if q.get("scope", {}).get("eu_clients") and not an.eea_controller:
        who.append(["Importer of an EU client's data under SCC Module One",
                    f"The exporting client and the authority named in the SCCs ({law.SCC_CLAUSES['breach']})"])
    if c.get("role") in ("processor", "both"):
        who.append(["Processor for a client (Art. 28 contract / AVV)", "The client, without undue delay; the client "
                    "notifies the authority (Art. 33(2))"])
    if an.kvkk:
        who.append(["Controller under KVKK", "The KVKK Board and the people affected (m.12/5)"])
    out.append("## Who notifies whom\n\nOne breach can trigger several of these at once.\n\n" +
               table(["Your role for the data", "Notify"], who) + "\n\nWithout an EU establishment the one-stop-shop "
               "(Art. 56) does not apply: " + O("which authorities, by where the affected people live") + ".\n")
    vend = [x for x in q.get("vendors", []) if receives(q, x) in ("raw", "masked") and x.get("country") != "LOCAL"]
    out.append("## Processors\n\nEach vendor must tell us without undue delay (Art. 33(2)); see the agreed hours in "
               "document 04. Vendor contacts: " + ("; ".join(f"{x['name']}: {O('breach contact')}" for x in vend) or "none")
               + ".\n")
    out.append("## Agent-specific incidents to treat as possible breaches\n\n- An agent e-mailed a document to the "
               "wrong client, or with the wrong attachment.\n- An agent sent unmasked text to a cloud model that "
               "should only get masked text.\n- A prompt injection made an agent send data to a tool, URL or e-mail it "
               "should not use.\n- An agent wrote one client's data into another client's matter or shared memory.\n"
               "- An API key or the masking key (vault) was exposed.\n- A vendor reports a breach of its logs.\n")
    out.append(findings_block(an, "07"))
    out.append(kvkk_block(an, "The KVKK Board publishes breach notifications in summary on its website. Data subjects "
                              "are informed within a reasonable time after they are identified, directly if contact "
                              "details exist, otherwise by publication."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 08
def dsr(an: Analysis) -> str:
    out = [banner(an, "08")]
    out.append("## Steps\n\n1. **Receive and log.** Any channel counts. Log date, person, right, matter. "
               "Inbox: " + v(an.q["controller"].get("contact"), "contact") + ".\n"
               "2. **Verify identity** proportionately (Art. 12(6)); ask only for what you need.\n"
               "3. **Search every store**, including agent memory, embeddings, prompt logs, sent e-mail and vendor "
               "logs (documents 06 and 09 list them). The masking vault maps placeholders back to people: search it too.\n"
               "4. **Check limits.** A copy must not adversely affect the rights and freedoms of others (Art. 15(4)), "
               "e.g. other parties in the file. Legal professional secrecy limits rights only where Union or Member "
               "State law provides for it under Art. 23 " + O("which national law, e.g. the client's Member State") +
               "; a Turkish lawyer's secrecy (Avukatlık Kanunu m.36) is not such a law. Deletion can be refused while "
               "the data is needed for legal claims (Art. 17(3)(e)).\n"
               "5. **Answer within one month** (Art. 12(3)); extend by two more months for complex cases, telling the "
               "person within the first month why. Free of charge unless manifestly unfounded or excessive (Art. 12(5)).\n"
               "6. **Tell processors** to act where needed (Art. 28(3)(e)) and recipients of corrected or deleted "
               "data (Art. 19).\n7. **Keep the record** of the request and the answer.\n")
    out.append("## Per right\n\n" + table(["Right", "GDPR", "Agent-system notes"], [
        ["Access, copy", "Art. 15", "Include the AI processing, sources (Art. 15(1)(g)), any per-person label and its logic"],
        ["Correction", "Art. 16", "Also correct a screening record that confused the person with someone else"],
        ["Deletion", "Art. 17", "Delete embeddings and memory too; vendor logs per their retention"],
        ["Restriction", "Art. 18", "Flag the matter so agents skip it"],
        ["Portability", "Art. 20", "Only for data the person gave, on consent or contract, processed by automated means"],
        ["Objection", "Art. 21", "Stop unless compelling legitimate grounds or legal claims"],
        ["No solely automated decisions", "Art. 22", "Confirm a person reviewed the outcome"],
    ]) + "\n")
    out.append(findings_block(an, "08"))
    out.append(kvkk_block(an, "KVKK m.11 lists similar rights (including learning whether data is processed, the "
                              "purpose, recipients at home and abroad, and objecting to an outcome against the person "
                              "arising from analysis exclusively by automated systems, m.11/1-g). Applications are made "
                              "in writing or by the methods in the Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ; the answer is due "
                              "within 30 days and is free, except that the Tebliğ allows a set fee for answers over 10 "
                              "pages or on a medium (m.13/2)."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 09
def toms(an: Analysis) -> str:
    q, sec = an.q, an.q.get("security", {})
    out = [banner(an, "09")]
    agents = q.get("agents", [])
    rev = {review_state(a) for a in agents if a.get("output") in ("client", "court", "published")}
    raw = any(receives(q, x) == "raw" and x.get("country") != "LOCAL" for x in q.get("vendors", []))
    mask = sec.get("masking_before_cloud")
    out.append("Status comes from the answers. A free-text answer is shown as given, with the status left for the "
               "reviewer; only an explicit yes is shown as 'in place'.\n\n" + table(["Area", "Measure", "Status", "Source"], [
        ["Pseudonymisation", "Personal data masked on the device before cloud model calls; key stays local" +
         (f" (profile: {sec['masking_profile']})" if sec.get("masking_profile") else ""),
         "in place for some vendors only; others get raw text" if mask and raw else _status(mask), "GDPR Art. 32(1)(a)"],
        ["Encryption", "TLS in transit", _status(sec.get("encryption_in_transit")), "GDPR Art. 32(1)(a)"],
        ["Encryption", "Disks, databases and backups at rest", _status(sec.get("encryption_at_rest")), "GDPR Art. 32(1)(a)"],
        ["Keys", "API keys and the masking vault key in a secrets store, rotated", _status(sec.get("key_management")), "GDPR Art. 32(1)(b)"],
        ["Access", "Named accounts, least privilege, per-matter access",
         "not in place (shared logins)" if sec.get("shared_logins") else _status(sec.get("access_control")), "GDPR Art. 32(1)(b), 32(4)"],
        ["Access", "Multi-factor login", _status(sec.get("mfa")), "GDPR Art. 32(1)(b)"],
        ["Logging", "Who and which agent read or sent what, kept " + v(sec.get("log_retention"), "log retention"),
         ("partial: with shared logins the logs cannot show which person acted" if sec.get("shared_logins") and sec.get("logging")
          else _status(sec.get("logging"))), "GDPR Arts. 5(2), 32(1)(b)"],
        ["Agents", "Tool allow-list per agent; outside documents treated as data; no autonomous outbound e-mail/upload",
         _status(sec.get("agent_guardrails")), "GDPR Art. 32(1)(b)"],
        ["Agents", "A lawyer approves every output before it leaves the firm",
         "in place" if rev == {"always"} else ("not in place for every agent" if rev & {"never", "sometimes"} else O("in place?")),
         "GDPR Arts. 5(1)(d), 25(1)"],
        ["Resilience", "Backups", _status(sec.get("backups")), "GDPR Art. 32(1)(c)"],
        ["Resilience", "Restore from backup tested", _status(sec.get("restore_tested")), "GDPR Art. 32(1)(c)-(d)"],
        ["Testing", "Regular test of the measures (incl. a prompt-injection test)", _status(sec.get("pentest")), "GDPR Art. 32(1)(d)"],
        ["People", "Staff act only on instructions; confidentiality undertakings", O("in place?"), "GDPR Art. 32(4)"],
        ["People", "AI-literacy training", _status(sec.get("staff_training")), "AI Act Art. 4"],
        ["Vendors", "DPAs and transfer tools (documents 04, 05)", "see 04 and 05", "GDPR Arts. 28, 32"],
    ]) + "\n")
    if an.kvkk and any(d.get("kind") in ("special", "criminal") for d in q.get("data", [])):
        out.append("## Special-category data: KVKK Board decision 2018/10 (m.6/4)\n\nSummary for a checklist; the "
                   "decision text is authoritative.\n\n" + table(["Measure", "Status"],
                                                                 [[m, O("in place?")] for m in law.KVKK_2018_10]) + "\n")
    out.append(findings_block(an, "09"))
    out.append(kvkk_block(an, "KVKK m.12/1 requires 'technical and administrative measures'. The Board's Personal Data "
                              "Security Guide lists them in the same groups; this table maps one-to-one."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 10
def ai_act(an: Analysis) -> str:
    q, ai = an.q, an.q.get("ai", {})
    out = [banner(an, "10")]
    out.append("Text and dates as amended by " + law.AI_ACT_AMENDMENT + ". Article numbers below are AI Act articles "
               "unless marked GDPR.\n")
    out.append("## Role\n\n" + table(["Question", "Answer"], [
        ["Role under the AI Act", an.ai_role + " (AI Act Art. 3(3) provider: develops a system and places it on the "
                                              "market or puts it into service under its own name; AI Act Art. 3(4) "
                                              "deployer: uses a system under its authority)"],
        ["Offered to others under own name?", v(ai.get("offered_under_own_name"), "sold or offered to others?") +
         (f". Plan: {ai['offering_planned']}" if ai.get("offering_planned") else "")],
        ["Models used", ", ".join(sorted({by_id(q, 'vendors')[m]['name'] for a in q.get('agents', [])
                                          for m in a.get('models', [])})) or "none"],
        ["Territorial reach", "Applies to providers and deployers outside the EU where the output is used in the EU "
                              "(AI Act Art. 2(1)(c))"],
    ]) + "\n\nUsing a vendor's general-purpose model through its API does not make you a GPAI model provider. "
               "Fine-tuning one may, if the modification is substantial (Commission GPAI guidelines, July 2025): "
               + v(ai.get("fine_tunes_models"), "do you fine-tune models?") + ".\n")
    crime = ai.get("predicts_crime_risk")
    out.append("## Risk class: " + an.ai_risk + "\n\n" + table(["Check", "Result", "Source"], [
        ["Prohibited practice?", "No prediction of a person's risk of offending from profiling. " + (
            "**Flagged: see findings.**" if crime else ("Answered: no." if crime is False else O("answer: does any label "
                                                                                                    "or score predict offending?"))),
         "AI Act Art. 5(1)(d)"],
        ["Annex III high-risk use?", ("; ".join(law.ANNEX_III.get(x, x) for x in ai.get("annex_iii") or [])
                                     or ("none indicated" if ai.get("annex_iii") == [] else O("Annex III areas"))) +
         ". Legal research for a law firm's own clients is not listed; point 8(a) covers systems used by or for a "
         "judicial authority or in ADR.", "AI Act Art. 6(2), Annex III"],
        ["Transparency", "The provider of a system that interacts directly with people must design it so they are told "
                         "(Art. 50(1)); deployers of emotion recognition or biometric categorisation must inform "
                         "(Art. 50(3)); deployers publishing AI text on public-interest matters must disclose it unless "
                         "a person reviewed it and holds editorial responsibility (Art. 50(4)).", "AI Act Art. 50"],
        ["AI literacy", "Take measures to support the AI literacy of staff who operate the system.", "AI Act Art. 4"],
    ]) + "\n")
    out.append("## Dates\n\n" + table(["Date", "What applies"], [list(x) for x in law.AI_ACT_DATES]) + "\n")
    out.append("## Professional duties beside the AI Act\n\nBar rules on confidentiality and competence apply to AI "
               "use regardless of the AI Act: check the Türkiye Barolar Birliği and, for EU work, the CCBE guidance "
               "on AI use by lawyers. " + O("which bar rules the reviewing lawyer applies") + "\n")
    out.append(findings_block(an, "10"))
    out.append(kvkk_block(an, "Türkiye has no AI act in force " + O("check the status of the AI bill") + ". KVKK "
                              "m.11/1-g already lets a person object to an outcome against them that results exclusively "
                              "from automated analysis."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 11
def lia(an: Analysis) -> str:
    q = an.q
    out = [banner(an, "11")]
    acts = [a for a in q.get("activities", []) if a.get("lawful_basis") == "6(1)(f)"]
    out.append("One assessment per activity based on legitimate interests. The three steps follow Art. 6(1)(f) as the "
               "CJEU reads it (C-252/21, Meta v Bundeskartellamt): a legitimate interest, processing strictly "
               "necessary for it, and the interest not overridden by the person's rights, taking into account their "
               "reasonable expectations (Recital 47).\n")
    if not acts:
        out.append("No activity relies on Art. 6(1)(f).\n")
    for a in acts:
        subs = activity_subjects(q, a)
        data = activity_data(q, a)
        sens = [d["label"] for d in data if d.get("kind") in ("special", "criminal", "minor", "id_number")]
        vuln = [s["label"] for s in subs if s.get("vulnerable") or s.get("children")]
        safeguards = []
        if q.get("security", {}).get("masking_before_cloud"):
            safeguards.append("masking before cloud calls")
        if all(review_state(by_id(q, "agents")[x]) == "always" for x in a.get("agents", []) if x in by_id(q, "agents")) and a.get("agents"):
            safeguards.append("a lawyer reads this activity's outputs before they are used (per the questionnaire)")
        if a.get("retention") and not re.search(r"never|not deleted", a["retention"], re.I):
            safeguards.append(f"retention limited to: {a['retention']}")
        out.append(f"## {a.get('name', a['id'])}\n\n" + table(["Step", "Assessment"], [
            ["1. Interest", v(a.get("legitimate_interest"), "the interest, stated concretely") +
             ". Is it lawful, clear and present? " + O("reviewer")],
            ["2. Necessity", f"Purpose: {v(a.get('purpose'), 'purpose')}. Could it be reached with less data or a less "
                             "intrusive method (e.g. screening companies before people, exact matches instead of "
                             "fuzzy ones)? " + O("reviewer")],
            ["3a. Who is affected", names(subs) + (f". Vulnerable: {', '.join(vuln)}" if vuln else "")],
            ["3b. What data", names(data) + (f". Sensitive: {', '.join(sens)}" if sens else "")],
            ["3c. Reasonable expectations", "Given each group's relationship with the firm (own client, staff, "
                                            "counterparty, officer of a company under review), would they reasonably "
                                            "expect this processing at the time and in this context (Recital 47)? " + O("reviewer")],
            ["3d. Safeguards", ", ".join(safeguards) or O("safeguards")],
            ["Result", O("interest prevails / does not prevail, with reasons; date; reviewer")],
        ]) + "\n")
    out.append(findings_block(an, "11"))
    out.append(kvkk_block(an, "KVKK m.5/2-f (meşru menfaat) also requires that the processing does not harm the "
                              "person's fundamental rights and freedoms; the Board's guidance expects a balancing test of "
                              "the same kind. For client work, m.5/2-e (establishing, exercising or protecting a right) "
                              "is often the better KVKK basis."))
    return "\n".join(out)


RENDER = {"overview": overview, "ropa": ropa, "dpia": dpia, "privacy-notice": notice, "contracts": contracts,
          "transfers-tia": tia, "retention": retention, "breach": breach, "dsr": dsr, "toms": toms, "ai-act": ai_act,
          "lia": lia}


def render_all(an: Analysis) -> dict[str, str]:
    from . import tr
    files = {f"{n}-{slug}.md": RENDER[slug](an).rstrip() + "\n" for n, slug, _ in DOCS}
    if an.kvkk:
        files.update(tr.render_tr(an))
    return files
