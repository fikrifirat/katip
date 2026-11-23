"""Render the ten documents (plus an overview) as Markdown, from a questionnaire and its analysis.

Style rules: cite the article next to each requirement, print [OPEN: ...] instead of guessing, and
never say "compliant". Each document carries the same draft banner.
"""
from __future__ import annotations

from . import law
from .model import activity_data, activity_subjects, activity_vendors, by_id
from .rules import SEVERITY_LABEL, Analysis

DOCS = [
    ("00", "overview", "Pack overview, findings and open questions"),
    ("01", "ropa", "Record of processing activities (GDPR Art. 30)"),
    ("02", "dpia", "Data protection impact assessment (GDPR Art. 35)"),
    ("03", "privacy-notice", "Privacy notice (GDPR Arts. 13 and 14)"),
    ("04", "dpa-checklist", "Processor agreements: checklist per vendor (GDPR Art. 28)"),
    ("05", "transfers-tia", "International transfers and transfer impact assessment (GDPR Chapter V)"),
    ("06", "retention", "Retention and deletion policy (GDPR Art. 5(1)(e))"),
    ("07", "breach", "Personal data breach procedure (GDPR Arts. 33 and 34)"),
    ("08", "dsr", "Data subject request procedure (GDPR Arts. 12 and 15-22)"),
    ("09", "toms", "Technical and organisational measures (GDPR Art. 32)"),
    ("10", "ai-act", "EU AI Act note: role, risk class and duties (Regulation (EU) 2024/1689)"),
]
TITLE = {n: t for n, _, t in DOCS}


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


def banner(an: Analysis, num: str) -> str:
    s = an.q["system"]
    return (f"# {num} · {TITLE[num]}\n\n"
            f"**System:** {s['name']} · **Controller:** {an.q['controller']['name']} · "
            f"**Questionnaire dated:** {v(s.get('date'), 'date')}\n\n"
            "> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point "
            "for the reviewing lawyer, not legal advice, and not a statement that the system complies with the GDPR, "
            "KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; the findings list in document "
            "00 says what each one changes.\n")


def findings_block(an: Analysis, num: str) -> str:
    fs = an.by_doc(num)
    if not fs:
        return ""
    lines = ["## Points for the reviewer", ""]
    for f in fs:
        end = "" if f.title.endswith(("?", ".")) else "."
        lines.append(f"- **{SEVERITY_LABEL[f.severity]}: {f.title}{end}** {f.detail} *({f.cite})*")
    return "\n".join(lines) + "\n"


def kvkk_block(text: str) -> str:
    return "## KVKK (Türkiye)\n\n" + text.strip() + "\n"


def names(items, key="label"):
    return ", ".join(i.get(key) or i.get("name") or i["id"] for i in items) or "none"


# --------------------------------------------------------------------------------------------- 00
def overview(an: Analysis) -> str:
    q = an.q
    s, c = q["system"], q["controller"]
    out = [banner(an, "00")]
    out.append("## The system in one paragraph\n\n" + v(s.get("description"), "short description") + "\n")
    out.append("## Who is responsible\n\n" + table(["", ""], [
        ["Controller", f"{c['name']} ({law.country(c.get('country'))})"],
        ["Role", v(c.get("role"), "controller or processor for clients")],
        ["Privacy contact", v(c.get("contact"), "privacy contact")],
        ["DPO", c.get("dpo") or "none appointed (see findings)"],
        ["EU representative (Art. 27)", c.get("eu_representative") or "none"],
    ]) + "\n")
    out.append("## Which laws apply, and why\n\n" + ("\n".join(f"- {a}" for a in an.applicability)
                                                       or "- " + O("whether the GDPR applies (Art. 3)")) + "\n")
    out.append("## The pack\n\n" + table(["#", "Document", "What it is for"], [
        [n, f"[{t}]({n}-{slug}.md)", PURPOSE[slug]] for n, slug, t in DOCS[1:]]) + "\n")
    counts = {}
    for f in an.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    out.append("## Findings\n\n" + ", ".join(f"{counts.get(k, 0)} {SEVERITY_LABEL[k].lower()}"
                                             for k in ("action", "risk", "open", "info")) + ".\n")
    rows = [[SEVERITY_LABEL[f.severity], f.title, f.cite, ", ".join(f.docs)] for f in an.findings]
    out.append(table(["Type", "Finding", "Source", "Docs"], rows) + "\n")
    out.append("## KVKK map\n\nKVKK was modelled on the GDPR's predecessor and shares most concepts. Where Türkiye "
               "differs, each document has a KVKK section.\n\n" + table(["GDPR document", "KVKK counterpart"], [
                   ["01 RoPA (Art. 30)", "Kişisel veri işleme envanteri; VERBİS kaydı (m.16) unless an exemption "
                                         "decision of the Board covers the controller (check the current list)"],
                   ["02 DPIA (Art. 35)", "No statutory DPIA; the Board's guides recommend a risk analysis"],
                   ["03 Notice (Arts. 13-14)", "Aydınlatma metni (m.10; Aydınlatma Yükümlülüğü Tebliği)"],
                   ["04 DPA (Art. 28)", "Veri işleyen sözleşmesi; joint liability for security (m.12/2)"],
                   ["05 Transfers", "Yurt dışına aktarım (m.9, amended 2024): standard contract notified within 5 "
                                    "business days"],
                   ["06 Retention", "Saklama ve imha politikası (Silme, Yok Etme veya Anonim Hale Getirme Yönetmeliği)"],
                   ["07 Breach (Arts. 33-34)", "m.12/5: notify the Board 'en kısa sürede', read as 72 hours (Board "
                                               "decision 2019/10)"],
                   ["08 Rights (Arts. 15-22)", "m.11 rights; m.13 answer within 30 days, free of charge in principle"],
                   ["09 TOMs (Art. 32)", "m.12/1 technical and administrative measures; Board security guide"],
                   ["10 AI Act", "No Turkish equivalent in force (check the AI bill status)"],
               ]) + "\n")
    out.append("## Sources\n\nLists checked " + law.CHECKED + ".\n\n" +
               "\n".join(f"- [{k}]({u})" for k, u in law.SOURCES.items()) + "\n")
    return "\n".join(out)


PURPOSE = {
    "ropa": "What is processed, why, for whom, where, how long. The supervisory authority can ask for it.",
    "dpia": "Whether the risk is high, and what reduces it. Required before go-live when risk is likely high.",
    "privacy-notice": "What clients and other people are told, at collection or within a month.",
    "dpa-checklist": "Per vendor: does its contract have every Art. 28(3) term?",
    "transfers-tia": "Which data leaves the EU or Türkiye, on what legal tool, and with what risk.",
    "retention": "How long each kind of data is kept and how it is deleted, including in the agents' memory.",
    "breach": "Who does what in the 72 hours after a leak.",
    "dsr": "How access, deletion and other requests are answered within a month.",
    "toms": "The security measures, written down so they can be checked.",
    "ai-act": "What the EU AI Act asks of this system, and from when.",
}


# --------------------------------------------------------------------------------------------- 01
def ropa(an: Analysis) -> str:
    q, c = an.q, an.q["controller"]
    out = [banner(an, "01")]
    out.append("Controller's record under Art. 30(1). If you also process data **on behalf of clients**, keep a "
               "processor's record under Art. 30(2) as well (categories of processing per client, transfers, "
               "measures). The Art. 30(5) exemption for organisations under 250 people does not apply where "
               "processing is not occasional or includes Art. 9 or Art. 10 data.\n")
    out.append("## Controller (Art. 30(1)(a))\n\n" + table(["", ""], [
        ["Name", c["name"]], ["Address", v(c.get("address"), "address")],
        ["Contact", v(c.get("contact"), "privacy contact")],
        ["Representative", c.get("eu_representative") or "none"], ["DPO", c.get("dpo") or "none"]]) + "\n")
    stor = by_id(q, "storage")
    for a in q.get("activities", []):
        vend = activity_vendors(q, a)
        rows = [
            ["Purpose (b)", v(a.get("purpose"), "purpose")],
            ["Lawful basis", _basis(a)],
            ["Data subjects (c)", names(activity_subjects(q, a))],
            ["Personal data (c)", names(activity_data(q, a))],
            ["Source", v(a.get("source"), "where the data comes from")],
            ["Recipients (d)", ", ".join(a.get("recipients", [])) or "none outside the controller"],
            ["Processors and vendors", ", ".join(f"{x['name']} ({law.country(x.get('country'))})" for x in vend) or "none"],
            ["Transfers outside the EEA (e)", _xfer_summary(an, vend)],
            ["Where it is stored", ", ".join(stor[s].get("what", s) for s in a.get("storage", [])) or O("storage")],
            ["Retention (f)", v(a.get("retention"), "retention period")],
            ["Security (g)", "See document 09 (TOMs)."],
        ]
        out.append(f"## Activity: {a.get('name', a['id'])}\n\n" + table(["Art. 30(1)", "Entry"], rows) + "\n")
    out.append(findings_block(an, "01"))
    out.append(kvkk_block(
        "Keep the same table as the kişisel veri işleme envanteri. VERBİS (KVKK m.16) registration is required "
        "unless a Board exemption decision covers the controller; the Board has exempted several groups by decision "
        "since 2018, so check the current list for law firms before registering or relying on an exemption."))
    return "\n".join(out)


def _basis(a) -> str:
    b = a.get("lawful_basis")
    if not b:
        return O("Art. 6(1) basis")
    s = f"GDPR Art. {b} ({law.LAWFUL_BASIS.get(b, '?')})"
    if b == "6(1)(f)":
        s += f". Interest: {v(a.get('legitimate_interest'), 'legitimate interest + balancing test')}"
    if a.get("art9_condition"):
        s += f"; Art. {a['art9_condition']} ({law.ART9.get(a['art9_condition'], '?')})"
    if a.get("art10_basis"):
        s += f"; Art. 10: {a['art10_basis']}"
    return s


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
    n = sum(1 for c in an.dpia_criteria if c[2])
    out.append("## 1. Is a DPIA required? (Art. 35(1), WP248 rev.01)\n\n" + table(
        ["EDPB criterion", "Met?", "Why"],
        [[label, "yes" if met else "no", why] for _, label, met, why in an.dpia_criteria]) +
        f"\n\n**{n} of 9 criteria met.** " + (
            "Two or more usually mean a DPIA is required: treat this document as mandatory and complete it before "
            "go-live." if an.dpia_required else
            "Fewer than two: a DPIA may not be mandatory. Keep this screening as the record of that decision.") + "\n")
    out.append("## 2. Systematic description (Art. 35(7)(a))\n\n" + v(q["system"].get("description"), "description") +
               "\n\n" + table(["Agent", "What it does", "Models and tools", "Human review", "Output goes to"], [
                   [a.get("name", a["id"]), v(a.get("does"), "task"),
                    ", ".join(by_id(q, "vendors")[m]["name"] for m in a.get("models", []) + a.get("vendors", []))
                    + (("; tools: " + ", ".join(a["tools"])) if a.get("tools") else ""),
                    v(a.get("human_review"), "human review?"), v(a.get("output"), "output")]
                   for a in q.get("agents", [])]) + "\n\nPurposes and data per activity: document 01.\n")
    out.append("## 3. Necessity and proportionality (Art. 35(7)(b))\n\n" + table(
        ["Question", "Answer for this system"], [
            ["Is each data item needed for the purpose? (Art. 5(1)(c))", _minimisation(q)],
            ["Lawful bases", "; ".join(f"{a.get('name')}: {_basis(a)}" for a in q.get("activities", []))],
            ["Retention limits", "Document 06."],
            ["Information to people", "Document 03."],
            ["Rights handling", "Document 08."],
            ["Processors and transfers", "Documents 04 and 05."],
        ]) + "\n")
    out.append("## 4. Risks to people (Art. 35(7)(c))\n\nLikelihood and severity: low / medium / high, before the "
               "measures in section 5. The reviewer should adjust these; they are generated from the answers.\n\n" +
               table(["#", "Risk to the people concerned", "Likelihood", "Severity", "Triggered by"], _risks(an)) + "\n")
    out.append("## 5. Measures (Art. 35(7)(d))\n\n" + "\n".join(f"- {m}" for m in _measures(q)) + "\n")
    out.append("## 6. Residual risk and sign-off\n\n" + table(["", ""], [
        ["Residual risk after measures", O("reviewer's conclusion: low / medium / high")],
        ["Prior consultation needed (Art. 36)?", "Only if high residual risk remains: " + O("yes / no")],
        ["DPO advice (Art. 35(2))", O("advice, or 'no DPO'")],
        ["Views of data subjects (Art. 35(9))", O("sought / not appropriate, with reason")],
        ["Approved by, date", O("name, date")],
        ["Review date", O("at least yearly, and on any new agent, model or vendor")],
    ]) + "\n")
    out.append(findings_block(an, "02"))
    out.append(kvkk_block("KVKK has no statutory DPIA. Keeping this one also covers the risk analysis the Board's "
                          "security guide expects under m.12/1."))
    return "\n".join(out)


def _minimisation(q) -> str:
    sec = q.get("security", {})
    parts = []
    if sec.get("masking_before_cloud") is True:
        parts.append("Names, ID numbers, contact details and addresses are masked on the device before any text "
                     "goes to a cloud model; placeholders come back and are restored locally.")
    elif sec.get("masking_before_cloud") is False:
        parts.append("Raw text goes to the cloud models. " + O("why raw text is necessary"))
    else:
        parts.append(O("is text masked before the cloud call?"))
    parts.append(O("data items that could be dropped"))
    return " ".join(parts)


def _risks(an: Analysis):
    q = an.q
    kinds = {d.get("kind") for d in q.get("data", [])}
    vend = q.get("vendors", [])
    raw = any(x.get("receives") == "raw" and x.get("country") != "LOCAL" for x in vend)
    rows = []

    def r(text, lik, sev, why):
        rows.append([str(len(rows) + 1), text, lik, sev, why])

    if "criminal" in kinds:
        r("A person is wrongly linked to sanctions, crime or insolvency (false match), harming reputation or a deal",
          "medium", "high", "screening against public lists by name")
    r("The model invents facts or citations about a person and a lawyer relies on them", "medium",
      "high" if "criminal" in kinds else "medium", "LLM-written drafts")
    r("Client or third-party data leaks through a vendor (breach, logs, staff access)",
      "medium" if raw else "low", "high" if kinds & {"special", "criminal"} else "medium",
      "raw text to cloud vendors" if raw else "masked text to cloud vendors")
    if any(t.route not in ("EEA", "adequacy", "DPF", "same country") for t in an.transfers):
        r("Foreign authorities access data at a vendor in a country without adequate protection", "low", "high",
          "transfers on SCCs or without a tool")
    r("Prompt injection in a fetched document makes an agent leak or alter data", "medium", "medium",
      "agents that read outside documents and call tools")
    r("People cannot exercise rights because they never learn about the processing", "high" if any(
        a.get("source") in ("client", "public", "third_party") for a in q.get("activities", [])) else "low", "medium",
      "data collected about third parties (Art. 14)")
    r("Data kept longer than needed in agent memory, vector stores or vendor logs", "medium", "medium",
      "retention across several stores")
    return rows


def _measures(q):
    sec, ms = q.get("security", {}), []
    if sec.get("masking_before_cloud"):
        ms.append("Mask personal data on the device before any cloud model call; keep the re-identification key "
                  "locally (Katip Kalkan). Art. 25, 32(1)(a).")
    ms += [
        "A named lawyer reviews every output before it leaves the firm; agents draft, people decide. Art. 22, AI Act Art. 14 spirit.",
        "Show the source record and link for every screening hit; no score or summary about a person. Art. 5(1)(d).",
        "Zero-retention or shortest-retention API settings and no training on inputs, confirmed in each vendor contract. Art. 28.",
        "Treat fetched documents as data, never instructions; agents' tools limited to what the task needs. Art. 32.",
        "Retention schedule enforced in every store, including embeddings and logs (document 06). Art. 5(1)(e).",
        "Art. 14 notice for third parties, or a documented exemption (document 03).",
    ]
    for k, label in (("mfa", "Multi-factor login"), ("encryption_at_rest", "Encryption at rest"),
                     ("logging", "Logs of who and which agent accessed what")):
        if sec.get(k):
            ms.append(f"{label} (in place).")
    return ms


# --------------------------------------------------------------------------------------------- 03
def notice(an: Analysis) -> str:
    q, c = an.q, an.q["controller"]
    acts = q.get("activities", [])
    out = [banner(an, "03")]
    out.append("Two notices: **A** for clients and people who give their data directly (Art. 13), **B** for people "
               "whose data comes from clients or public sources, such as the subjects of a due-diligence report "
               "(Art. 14). Plain language is required (Art. 12(1)); translate into the languages of the people concerned.\n")
    def purpose_rows(group):
        return table(["Purpose", "Legal basis", "How long"], [
            [v(a.get("purpose"), "purpose"), _basis(a), v(a.get("retention"), "retention")] for a in group])

    vend = [x for x in q.get("vendors", []) if x.get("receives") not in ("none", None) and x.get("country") != "LOCAL"]
    procs = "; ".join(f"{x['name']} ({x.get('service', '')})" for x in vend
                      if x.get("role") in ("processor", "sub_processor")) or "none"
    ctrls = [x for x in vend if x.get("role") in ("controller", "joint_controller")]
    recips = procs + "." + ((" We also send search terms to these organisations, which act on their own account: " +
                            "; ".join(f"{x['name']} ({x.get('service', '')})" for x in ctrls) + ".") if ctrls else "")
    xfers = [t for t in an.transfers if t.route not in ("EEA", "same country")]
    common = [
        "## Who we are\n\n" + f"{c['name']}, {v(c.get('address'), 'address')}. Privacy questions: "
        f"{v(c.get('contact'), 'contact')}." + (f" Data protection officer: {c['dpo']}." if c.get("dpo") else "") +
        (f" EU representative: {c['eu_representative']}." if c.get("eu_representative") else ""),
        "## Who receives it\n\nWe use these service providers, under contracts that bind them to our instructions: "
        + recips + " " + ("Before text is sent to an AI model provider, names, ID numbers, contact details and "
                           "addresses are replaced with placeholders on our own computer. The providers therefore see "
                           "pseudonymised text; it is still personal data for us." if q.get("security", {}).get(
                               "masking_before_cloud") else ""),
        "## Transfers outside the EU/EEA\n\n" + ("; ".join(
            f"{t.vendor['name']} ({law.country(t.country)}), on the basis of {t.route if t.route != 'unknown' else O('transfer tool')}"
            for t in xfers) + ". Ask us for a copy of the safeguards." if xfers else "None."),
        "## Use of AI\n\nWe use AI systems to draft and research. A lawyer reviews every result before it is used; "
        "no decision about you is made by a machine alone (Art. 22).",
        "## Your rights\n\nYou can ask for access (Art. 15), correction (16), deletion (17), restriction (18), "
        "portability where it applies (20), and object to processing based on legitimate interests (21). Where we "
        "rely on consent you can withdraw it at any time (Art. 7(3)). Some rights are limited by legal professional "
        "secrecy " + O("which national law applies; Art. 23") + ". You can complain to a supervisory authority, in "
        "particular in the EU country where you live or work (Art. 77).",
    ]
    direct = [a for a in acts if a.get("source") in ("data_subject", None)]
    third = [a for a in acts if a.get("source") in ("client", "public", "third_party")]
    what = "## What we do with your data, on what basis, for how long\n\n"
    common_a = common[:1] + [what + purpose_rows(direct)] + common[1:]
    common_b = common[:1] + [what + purpose_rows(third)] + common[1:]
    out.append("# A · Clients and people who give us their data (Art. 13)\n\n" + "\n\n".join(common_a) +
               "\n\n## Do you have to give us the data?\n\nThe data is needed to take on and run your matter; "
               "without it we cannot act for you (Art. 13(2)(e)).\n")
    if third:
        seen, cat_list = set(), []
        for a in third:
            for d in activity_data(q, a):
                if d["id"] not in seen:
                    seen.add(d["id"])
                    cat_list.append(d)
        cats = names(cat_list)
        out.append("# B · People we receive data about from others (Art. 14)\n\n" + "\n\n".join(common_b) +
                   f"\n\n## Which data, and from where (Art. 14(1)(d), 14(2)(f))\n\nCategories: {cats}. Sources: "
                   + ", ".join(sorted({a.get('source_detail') or a.get('source') for a in third})) + ".\n\n"
                   "## When you are told (Art. 14(3))\n\nWithin one month of receiving the data, or at first contact. "
                   "**Exemption check (Art. 14(5)), the reviewer must pick one and document it:**\n\n"
                   "- 14(5)(b) informing would be impossible or need disproportionate effort, or would seriously "
                   "impair the purpose (e.g. tipping off the target of a DD). Then publish this notice and take other "
                   "measures.\n"
                   "- 14(5)(d) the data must stay confidential under professional secrecy regulated by **Union or "
                   "Member State** law. A Turkish attorney's secrecy duty (Avukatlık Kanunu m.36) is not Member State "
                   "law; check whether the EU client's own lawyers' secrecy covers the matter.\n"
                   "- Otherwise: send this notice. " + O("chosen route") + "\n")
    out.append(findings_block(an, "03"))
    out.append(kvkk_block(
        "Under KVKK m.10 and the Aydınlatma Yükümlülüğü Tebliği, the aydınlatma metni must be given at collection "
        "and must be separate from any request for açık rıza. The content above covers the m.10 list (identity, "
        "purpose, recipients and purpose of transfer, method and legal reason of collection, m.11 rights). Since "
        "2024, transfers abroad also need to be explained with their m.9 basis."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 04
CHECKS_28 = [
    ("28(3)", "Subject matter, duration, nature and purpose, type of data and categories of data subjects are stated"),
    ("28(3)(a)", "Processes only on documented instructions, including on transfers"),
    ("28(3)(b)", "Staff are bound by confidentiality"),
    ("28(3)(c)", "Takes all Art. 32 security measures"),
    ("28(2), 28(3)(d), 28(4)", "Sub-processors only with prior authorisation; flows down the same terms; you can object to new ones"),
    ("28(3)(e)", "Helps you answer data subject requests"),
    ("28(3)(f)", "Helps with security, breach notification, DPIA and prior consultation (Arts. 32-36)"),
    ("28(3)(g)", "Deletes or returns all data at the end; says how long logs and backups persist"),
    ("28(3)(h)", "Makes information available and allows audits; tells you if an instruction breaks the law"),
    ("33(2)", "Notifies you of a breach without undue delay (agree a number of hours)"),
    ("Ch. V", "Transfer tool named (SCC module, DPF certification) with its sub-processor countries"),
    ("AI-specific", "No training on your inputs or outputs; retention of prompts/outputs stated (zero-retention if offered)"),
    ("AI-specific", "Abuse-monitoring access by vendor staff described and limited"),
]


def dpa(an: Analysis) -> str:
    out = [banner(an, "04")]
    out.append("Use one copy of this checklist per vendor. Most AI vendors offer a standard DPA; you usually cannot "
               "negotiate it, but you must read it against this list and record gaps. A missing term is a reason "
               "to choose another tier or vendor, or to mask more before sending.\n")
    for x in an.q.get("vendors", []):
        if x.get("country") == "LOCAL" or x.get("receives") == "none":
            continue
        role = x.get("role")
        head = (f"## {x['name']}: {x.get('service', '')}\n\n" + table(["", ""], [
            ["Role", v(role, "processor or controller")],
            ["Country / region", f"{law.country(x.get('country'))} / {v(x.get('region'), 'region')}"],
            ["Receives", v(x.get("receives"), "raw, masked or metadata")],
            ["DPA status", v(x.get("dpa"), "DPA status")],
            ["Vendor retention", v(x.get("retention"), "how long the vendor keeps inputs and outputs")],
            ["Trains on data", v(x.get("trains_on_data"), "training on inputs?")],
            ["Sub-processor list published", v(x.get("subprocessors_published"), "sub-processor list")],
            ["Notes", x.get("notes") or ""],
        ]))
        if role in ("controller", "joint_controller"):
            out.append(head + "\n\nThis vendor acts as a **controller** for the data it receives, so Art. 28 does not "
                       "apply. Check its own privacy terms, the purpose it uses the data for, and whether sharing with "
                       "it is covered by your lawful basis and notice (document 03)." +
                       (" Joint controllers need an Art. 26 arrangement." if role == "joint_controller" else "") + "\n")
            continue
        out.append(head + "\n\n" + table(["GDPR", "Term", "In the DPA?", "Clause / note"],
                                         [[a, t, "☐ yes ☐ no", ""] for a, t in CHECKS_28]) + "\n")
    out.append(findings_block(an, "04"))
    out.append(kvkk_block("KVKK has no Art. 28 list, but the controller is jointly liable with the veri işleyen for "
                          "security (m.12/2), so the Board expects a written contract with security terms. The same "
                          "checklist works. If the vendor is abroad, the contract alone is not a transfer tool: see 05."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 05
def tia(an: Analysis) -> str:
    q = an.q
    out = [banner(an, "05")]
    rows = [[t.vendor["name"], law.country(t.country), v(t.vendor.get("receives"), "what"), t.route,
             "yes" if t.needs_tia else "no", "yes" if t.kvkk_transfer else "no"] for t in an.transfers]
    out.append("## Map of data leaving the EU/EEA or Türkiye\n\n" + (table(
        ["Vendor", "Country", "Receives", "GDPR route", "TIA needed", "KVKK m.9 transfer"], rows) if rows else
        "No vendor outside the controller's own computer receives personal data.") + "\n\n"
        "GDPR routes: **EEA** no transfer; **adequacy** Art. 45 decision; **DPF** US organisation certified under the "
        "EU-US Data Privacy Framework (check the [list](https://www.dataprivacyframework.gov/list) for the exact legal "
        "entity); **SCC** Art. 46(2)(c) standard clauses (Decision 2021/914), which need this assessment; "
        "**same country** the vendor sits where the controller does.\n")
    if q.get("scope", {}).get("eu_clients") and q["controller"].get("country") not in law.EEA:
        out.append(f"## EU clients sending data to {law.country(q['controller'].get('country'))}\n\n"
                   f"For each EU client, sending its files to you is a transfer to a country without an adequacy "
                   f"decision. The client will need the SCCs with you (Module 1 if you act as an independent "
                   f"controller, Module 2 if you process on its behalf), and a TIA covering "
                   f"{law.country(q['controller'].get('country'))}'s laws on government access. Prepare one standard "
                   f"answer so each client does not start from zero: " + O("local counsel's summary of access laws") + "\n")
    tias = [t for t in an.transfers if t.needs_tia]
    for t in tias:
        x = t.vendor
        out.append(f"## TIA: {x['name']} ({law.country(t.country)})\n\nSteps from EDPB Recommendations 01/2020.\n\n" +
                   table(["Step", "Assessment"], [
                       ["1. Know the transfer", f"{x.get('service', '')}; data: {v(x.get('receives'), 'what')}; "
                                                f"region: {v(x.get('region'), 'region')}; onward transfers: "
                                                f"{v(x.get('subprocessors_published'), 'sub-processors')}"],
                       ["2. Transfer tool", "SCCs " + O("module and annexes") if t.route in ("SCC", "unknown", "missing")
                        else t.route],
                       ["3. Laws and practice of the destination", O("government access laws that apply to this "
                                                                     "vendor, e.g. FISA 702 for US providers")],
                       ["4. Supplementary measures", "Masking on the device before sending (the vendor never gets "
                        "the key); encryption in transit; zero-retention if offered" if x.get("receives") == "masked"
                        else O("supplementary measures")],
                       ["5. Procedural steps", "If SCCs are amended or another tool is used, check whether Art. 46(3) "
                                               "authorisation is needed"],
                       ["6. Re-evaluate", O("date; at least yearly and on vendor changes")],
                   ]) + "\n")
    out.append(findings_block(an, "05"))
    out.append(kvkk_block(
        "Since the amendment by Law No. 7499 (in force 1 June 2024) and the Regulation on the Procedures and "
        "Principles for the Transfer of Personal Data Abroad (10 July 2024), KVKK m.9 works like GDPR Chapter V: an "
        "adequacy decision of the Board, or appropriate safeguards (standard contract in the Board's form, notified to "
        "the Authority within 5 business days of signing; binding corporate rules; written undertaking with Board "
        "permission), or the listed occasional-transfer exceptions. Each vendor marked 'KVKK m.9 transfer' needs one "
        "of these, separately from its GDPR tool."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 06
def retention(an: Analysis) -> str:
    q = an.q
    out = [banner(an, "06")]
    out.append("Personal data is kept no longer than needed for the purpose (Art. 5(1)(e)). In an agent system data "
               "is copied into places people forget: prompts, tool outputs, embeddings, caches, logs, the vendor's "
               "own logs, backups. Each row below needs an owner and a deletion method.\n")
    rows = []
    for s in q.get("storage", []):
        vend = by_id(q, "vendors").get(s.get("vendor")) if s.get("vendor") else None
        where = "own computer" if not vend or vend.get("country") == "LOCAL" else vend["name"]
        rows.append([s.get("what", s["id"]), where, v(s.get("retention"), "period"),
                     v(s.get("deletion"), "how deleted"), "yes" if s.get("encrypted") else v(s.get("encrypted"), "encrypted?")])
    model_ids = {m for a in q.get("agents", []) for m in a.get("models", [])}
    for x in q.get("vendors", []):
        if x["id"] in model_ids and x.get("receives") in ("raw", "masked") and x.get("country") != "LOCAL":
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
    out.append(kvkk_block("Controllers that must register in VERBİS must also keep a written saklama ve imha "
                          "politikası and run periodic destruction at most every 6 months (Silme, Yok Etme veya "
                          "Anonim Hale Getirme Yönetmeliği m.5, m.11). Turkish limitation periods (e.g. TBK m.146: 10 "
                          "years; VUK m.253: 5 years for books) often set the outer limit for client files."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 07
def breach(an: Analysis) -> str:
    q, sec = an.q, an.q.get("security", {})
    out = [banner(an, "07")]
    out.append("## Who\n\n" + table(["Role", "Person"], [
        ["Breach lead (decides and notifies)", v(sec.get("incident_owner"), "named person")],
        ["Deputy", O("deputy")], ["Technical contact", O("who can switch agents off and pull logs")],
    ]) + "\n")
    out.append("## Clock\n\n" + table(["When", "What", "Source"], [
        ["0 h: aware", "Someone has reasonable certainty that personal data was lost, disclosed, altered or "
                       "accessed without authority. Log the time. Contain: revoke keys, pause agents, stop syncs.",
         "Art. 4(12); EDPB 9/2022"],
        ["< 24 h", "Assess: what data, how many people, masked or raw, who could see it, likely consequences.", ""],
        ["≤ 72 h", "Notify the lead supervisory authority unless the breach is unlikely to result in a risk. Late? "
                   "Give reasons. Information can come in phases.", "Art. 33(1), 33(4)"],
        ["≤ 72 h (KVKK)", "Notify the KVKK Board 'en kısa sürede', interpreted as 72 hours, on its breach form.",
         "KVKK m.12/5; Board decision 2019/10"],
        ["Without undue delay", "Tell the people affected if the risk to them is high, in plain language, with what "
                                "they can do. Not needed if the data was unintelligible to the recipient (e.g. "
                                "encrypted, or masked with the key safe) or the risk was neutralised.",
         "Art. 34(1), 34(3)"],
        ["Always", "Record every breach, even unnotified ones: facts, effects, actions, reasons.", "Art. 33(5)"],
    ]) + "\n")
    out.append("## Processors\n\nEach vendor must tell us without undue delay (Art. 33(2)); see the agreed hours in "
               "document 04. Vendor contacts: " + "; ".join(
                   f"{x['name']}: {O('breach contact')}" for x in q.get("vendors", [])
                   if x.get("receives") in ("raw", "masked") and x.get("country") != "LOCAL") + ".\n")
    out.append("## Agent-specific incidents to treat as possible breaches\n\n- An agent sent unmasked text to a "
               "cloud model that should only get masked text.\n- A prompt injection made an agent send data to a "
               "tool, URL or email it should not use.\n- An agent wrote one client's data into another client's matter "
               "or shared memory.\n- An API key or the masking key (vault) was exposed.\n- A vendor reports a "
               "breach of its logs.\n")
    out.append("## Where to notify\n\n" + table(["Authority", "How"], [
        ["Lead EU supervisory authority", O("which one; with no EU establishment, every authority where affected people live (Art. 56 one-stop-shop does not apply)")],
        ["KVKK Board", "Online breach notification form on kvkk.gov.tr"],
    ]) + "\n")
    out.append(findings_block(an, "07"))
    out.append(kvkk_block("The KVKK Board publishes breach notifications in summary on its website. Data subjects "
                          "are informed within a reasonable time after they are identified, directly if contact "
                          "details exist, otherwise by publication."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 08
def dsr(an: Analysis) -> str:
    out = [banner(an, "08")]
    out.append("## Steps\n\n1. **Receive and log.** Any channel counts. Log date, person, right, matter. "
               "Inbox: " + v(an.q["controller"].get("contact"), "contact") + ".\n"
               "2. **Verify identity** proportionately (Art. 12(6)); ask only for what you need.\n"
               "3. **Search every store**, including agent memory, embeddings, prompt logs and vendor logs "
               "(documents 06 and 09 list them). The masking vault maps placeholders back to people: search it too.\n"
               "4. **Check limits:** legal professional secrecy and the rights of others (Art. 15(4)); legal claims "
               "(Art. 17(3)(e)); national restrictions under Art. 23 " + O("which national law") + ".\n"
               "5. **Answer within one month** (Art. 12(3)); extend by two more months for complex cases, telling the "
               "person within the first month why. Free of charge unless manifestly unfounded or excessive (Art. 12(5)).\n"
               "6. **Tell processors** to act where needed (Art. 28(3)(e)) and recipients of corrected or deleted "
               "data (Art. 19).\n7. **Keep the record** of the request and the answer.\n")
    out.append("## Per right\n\n" + table(["Right", "GDPR", "Agent-system notes"], [
        ["Access, copy", "Art. 15", "Include the AI processing, sources (Art. 15(1)(g)) and that a lawyer reviews outputs"],
        ["Correction", "Art. 16", "Also correct a screening record that confused the person with someone else"],
        ["Deletion", "Art. 17", "Delete embeddings and memory too; vendor logs per their retention"],
        ["Restriction", "Art. 18", "Flag the matter so agents skip it"],
        ["Portability", "Art. 20", "Only for data the person gave, on consent or contract, processed by automated means"],
        ["Objection", "Art. 21", "Stop unless compelling legitimate grounds or legal claims"],
        ["No solely automated decisions", "Art. 22", "Confirm a person reviewed the outcome"],
    ]) + "\n")
    out.append(findings_block(an, "08"))
    out.append(kvkk_block("KVKK m.11 lists similar rights (including learning whether data is processed, the "
                          "purpose, recipients at home and abroad, and objecting to an outcome against the person "
                          "arising from analysis exclusively by automated systems). Applications are made in writing "
                          "or by the methods in the Başvuru Usul ve Esasları Tebliği; the answer is due within 30 days "
                          "and is free, except that the Tebliğ allows a set fee for answers over 10 pages or on a "
                          "medium (m.13/2)."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 09
def toms(an: Analysis) -> str:
    q, sec = an.q, an.q.get("security", {})
    out = [banner(an, "09")]

    def s(k, what):
        x = sec.get(k)
        return ("in place: " + x if isinstance(x, str) else "in place") if x else ("not in place" if x is False else O(what))

    out.append(table(["Area", "Measure", "Status", "Art. 32"], [
        ["Pseudonymisation", "Personal data masked on the device before cloud model calls; key stays local",
         s("masking_before_cloud", "masking"), "32(1)(a)"],
        ["Encryption", "TLS in transit", s("encryption_in_transit", "TLS"), "32(1)(a)"],
        ["Encryption", "Disks, databases and backups at rest", s("encryption_at_rest", "at rest"), "32(1)(a)"],
        ["Keys", "API keys and the masking vault key in a secrets store, rotated", s("key_management", "key management"), "32(1)(b)"],
        ["Access", "Least privilege; per-matter access; named accounts", s("access_control", "access control"), "32(1)(b)"],
        ["Access", "Multi-factor login", s("mfa", "MFA"), "32(1)(b)"],
        ["Logging", "Who and which agent read or sent what, kept " + v(sec.get("log_retention"), "log retention"),
         s("logging", "logging"), "32(1)(b), 33(5)"],
        ["Agents", "Tool allow-list per agent; outside documents treated as data; no autonomous outbound email/upload",
         s("agent_guardrails", "agent guardrails"), "32(1)(b)"],
        ["Agents", "Human review before any output leaves the firm",
         "in place" if all(a.get("human_review") for a in q.get("agents", [])) else O("human review for every agent"), "32(1)(b)"],
        ["Resilience", "Backups and tested restore", s("backups", "backups"), "32(1)(c)"],
        ["Testing", "Regular test of the measures (incl. a prompt-injection test)", s("pentest", "testing"), "32(1)(d)"],
        ["People", "Confidentiality and AI-literacy training (AI Act Art. 4)", s("staff_training", "training"), "32(4)"],
        ["Vendors", "DPAs and transfer tools (documents 04, 05)", "see 04/05", "28, 32"],
    ]) + "\n")
    out.append(findings_block(an, "09"))
    out.append(kvkk_block("KVKK m.12/1 requires 'technical and administrative measures'. The Board's Personal Data "
                          "Security Guide lists them in the same groups; this table maps one-to-one."))
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- 10
def ai_act(an: Analysis) -> str:
    q, ai = an.q, an.q.get("ai", {})
    out = [banner(an, "10")]
    out.append("## Role\n\n" + table(["Question", "Answer"], [
        ["Role under the AI Act", an.ai_role + " (Art. 3(3) provider: develops a system and places it on the market "
                                              "or puts it into service under its own name; Art. 3(4) deployer: uses "
                                              "a system under its authority)"],
        ["Offered to others under own name?", v(ai.get("offered_under_own_name"), "sold or offered to others?")],
        ["Models used", ", ".join(sorted({by_id(q, 'vendors')[m]['name'] for a in q.get('agents', [])
                                          for m in a.get('models', [])})) or "none"],
        ["Territorial reach", "Applies to providers and deployers outside the EU where the output is used in the EU "
                              "(Art. 2(1)(c))"],
    ]) + "\n\nUsing a vendor's general-purpose model through its API does not make you a GPAI model provider. "
               "Fine-tuning one may, if the modification is substantial (Commission GPAI guidelines, July 2025): "
               + v(ai.get("fine_tunes_models"), "do you fine-tune models?") + ".\n")
    out.append("## Risk class: " + an.ai_risk + "\n\n" + table(["Check", "Result", "Source"], [
        ["Prohibited practice?", "Check Art. 5(1)(d): no prediction of a person's criminal risk from profiling. "
         + ("**Flagged: see findings.**" if ai.get("predicts_crime_risk") else "Not indicated by the answers."), "Art. 5"],
        ["Annex III high-risk use?", ("; ".join(law.ANNEX_III.get(x, x) for x in ai.get("annex_iii") or [])
                                     or ("none indicated" if ai.get("annex_iii") == [] else O("Annex III areas"))) +
         ". Legal research for a law firm's own clients is not listed; point 8(a) covers systems used by or for a "
         "judicial authority or in ADR.", "Art. 6(2), Annex III"],
        ["Transparency", "People who chat with an agent must be told (Art. 50(1)); published AI text on public-"
                         "interest matters must be disclosed unless human-reviewed (Art. 50(4)).", "Art. 50"],
        ["AI literacy", "Training for everyone who operates the system.", "Art. 4"],
    ]) + "\n")
    out.append("## Dates\n\n" + table(["Date", "What applies"], [list(x) for x in law.AI_ACT_DATES]) +
               "\n\nThe Commission's Digital Omnibus proposal (19 Nov 2025) would postpone the Annex III high-risk "
               "dates. " + O("check whether it was adopted, and the dates now in force") + "\n")
    out.append("## Professional duties beside the AI Act\n\nBar rules on confidentiality and competence apply to AI "
               "use regardless of the AI Act: check the Türkiye Barolar Birliği and, for EU work, the CCBE guidance "
               "on AI use by lawyers. " + O("which bar rules the reviewing lawyer applies") + "\n")
    out.append(findings_block(an, "10"))
    out.append(kvkk_block("Türkiye has no AI act in force; a bill was submitted to the Grand National Assembly in "
                          "2024. " + O("current status") + " KVKK m.11/1-g already lets a person object to an outcome "
                          "against them that results exclusively from automated analysis."))
    return "\n".join(out)


RENDER = {"overview": overview, "ropa": ropa, "dpia": dpia, "privacy-notice": notice, "dpa-checklist": dpa,
          "transfers-tia": tia, "retention": retention, "breach": breach, "dsr": dsr, "toms": toms, "ai-act": ai_act}


def render_all(an: Analysis) -> dict[str, str]:
    return {f"{n}-{slug}.md": RENDER[slug](an).rstrip() + "\n" for n, slug, _ in DOCS}
