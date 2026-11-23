"""Turn a questionnaire into findings: what the law asks for, given these data flows.

Deterministic and explainable: every finding names the facts that triggered it and the article it
comes from. A finding is a prompt for the reviewing lawyer, not a conclusion.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import law
from .model import activity_data, activity_subjects, activity_vendors, by_id

SEVERITY_ORDER = {"action": 0, "risk": 1, "open": 2, "info": 3}
SEVERITY_LABEL = {"action": "Must do", "risk": "Risk to address", "open": "Open question", "info": "Note"}


@dataclass
class Finding:
    id: str
    severity: str  # action | risk | open | info
    title: str
    detail: str
    cite: str
    docs: list[str] = field(default_factory=list)


@dataclass
class Transfer:
    vendor: dict
    country: str
    mechanism: str        # what the questionnaire says
    route: str            # what we conclude: "EEA" | "adequacy" | "DPF" | "SCC" | "missing" | "unknown"
    needs_tia: bool
    kvkk_transfer: bool   # data leaves Türkiye (KVKK m.9) when KVKK applies


@dataclass
class Analysis:
    q: dict
    findings: list[Finding]
    transfers: list[Transfer]
    dpia_criteria: list[tuple[str, str, bool, str]]
    dpia_required: bool
    applicability: list[str]
    ai_role: str
    ai_risk: str

    def by_doc(self, doc: str) -> list[Finding]:
        return [f for f in self.findings if doc in f.docs]


def _yes(x):
    return x is True


def _unknown(x):
    return x is None


def analyse(q: dict) -> Analysis:
    F: list[Finding] = []

    def add(*a, **k):
        F.append(Finding(*a, **k))

    ctl, scope, sec = q["controller"], q.get("scope", {}), q.get("security", {})
    ai, scale = q.get("ai", {}), q.get("scale", {})
    acts, vendors, data = q.get("activities", []), q.get("vendors", []), q.get("data", [])
    ctl_cc = ctl.get("country")
    in_eea = ctl_cc in law.EEA
    kvkk = scope.get("kvkk_applies")
    if kvkk is None:
        kvkk = ctl_cc == "TR"

    # ---- 1. Does the GDPR apply, and how (Art. 3)?
    applicability = []
    if in_eea or _yes(ctl.get("eu_establishment")):
        applicability.append("Art. 3(1): the controller has an establishment in the EU/EEA.")
    else:
        if _yes(scope.get("offers_to_eu_data_subjects")):
            applicability.append("Art. 3(2)(a): offers services to people in the EU.")
        if _yes(scope.get("monitors_eu_behaviour")):
            applicability.append("Art. 3(2)(b): monitors behaviour of people in the EU.")
        if _yes(scope.get("eu_clients")):
            applicability.append("EU clients send personal data out of the EU/EEA: for them it is a transfer under "
                                 "Chapter V, so they will ask for SCCs and security terms even where Art. 3(2) does not "
                                 "reach this controller directly.")
        if not applicability:
            add("scope", "open", "Does the GDPR apply at all?",
                "The controller is outside the EU/EEA and the questionnaire does not say whether it offers services to "
                "people in the EU, monitors them, or receives data from EU clients. Each answer changes the pack.",
                "GDPR Art. 3; EDPB Guidelines 3/2018", ["00", "01"])
    if not (in_eea or _yes(ctl.get("eu_establishment"))) and applicability and \
            _unknown(scope.get("offers_to_eu_data_subjects")):
        add("art3_2", "open", "Does the GDPR reach you directly (Art. 3(2))?",
            "If you offer your services to people in the EU (not only to EU companies), the GDPR applies to you "
            "directly and you need an EU representative (Art. 27). If not, it reaches you through your EU clients' "
            "contracts. The answer decides documents 00, 01, 03 and 07.",
            "GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018", ["00", "01", "03", "07"])
    if kvkk:
        applicability.append("KVKK (Law No. 6698) applies in parallel: the controller processes data in Türkiye.")
    art3_2 = not (in_eea or _yes(ctl.get("eu_establishment"))) and (
        _yes(scope.get("offers_to_eu_data_subjects")) or _yes(scope.get("monitors_eu_behaviour")))
    if art3_2 and not ctl.get("eu_representative"):
        add("art27", "action", "Appoint an EU representative",
            "The GDPR reaches this controller through Art. 3(2) and it has no EU establishment, so it must designate "
            "a representative in a Member State where the data subjects are, unless the processing is occasional, does "
            "not include large-scale Art. 9 or Art. 10 data, and is unlikely to be a risk (Art. 27(2)). Screening "
            "people against sanctions and criminal-record sources is hard to call occasional.",
            "GDPR Art. 27", ["00", "01", "03"])
    if _yes(scope.get("eu_clients")) and not in_eea:
        add("eu_scc", "action", f"Prepare SCCs for EU clients who send files to {law.country(ctl_cc)}",
            f"{law.country(ctl_cc)} has no EU adequacy decision, so each EU client needs the 2021 SCCs with you "
            "(Module 1 controller-to-controller or Module 2 controller-to-processor) and its own TIA. Have one "
            "ready-made set and a standard answer on local government-access laws.",
            "GDPR Art. 46(2)(c); Decision (EU) 2021/914", ["05", "04"])
    if _unknown(scope.get("eu_clients")) and not in_eea:
        add("eu_clients", "open", "Do EU clients send their own files into the system?",
            "If yes, each EU client is exporting data to a non-EU recipient and needs SCCs (Module 1 or 2) with you.",
            "GDPR Arts. 44, 46(2)(c)", ["04", "05"])

    # ---- 2. Lawful basis, special and criminal data, Art. 14 (per activity).
    for a in acts:
        name = a.get("name", a["id"])
        kinds = {d.get("kind") for d in activity_data(q, a)}
        basis = a.get("lawful_basis")
        if not basis:
            add(f"basis:{a['id']}", "open", f"Lawful basis for '{name}'",
                "Each purpose needs one Art. 6(1) basis, chosen before processing starts.", "GDPR Arts. 5(1)(a), 6(1)",
                ["01", "03"])
        elif basis == "6(1)(f)" and not a.get("legitimate_interest"):
            add(f"lia:{a['id']}", "action", f"Write the legitimate-interests test for '{name}'",
                "Legitimate interests need a documented three-part test: the interest, necessity, and the balance "
                "against the data subjects' rights and reasonable expectations.", "GDPR Art. 6(1)(f), Recital 47",
                ["01", "02"])
        if "special" in kinds and not a.get("art9_condition"):
            add(f"art9:{a['id']}", "action", f"Art. 9 condition for '{name}'",
                "This activity touches special-category data (health, religion, ethnicity, ...). Besides an Art. 6 "
                "basis it needs an Art. 9(2) condition; for lawyers this is usually 9(2)(f) (legal claims).",
                "GDPR Art. 9; KVKK m.6", ["01", "02"])
        if "criminal" in kinds:
            if not a.get("art10_basis"):
                add(f"art10:{a['id']}", "action", f"Art. 10 authority for criminal-offence data in '{name}'",
                    "Data on criminal convictions and offences (including sanctions and court records about "
                    "individuals) may be processed only under the control of official authority or when Union or "
                    "Member State law authorises it with safeguards. A private screening tool needs to name that law "
                    "(for AML-obliged clients, the national law implementing Directive (EU) 2015/849). Without it, "
                    "screen companies, not individuals.", "GDPR Art. 10; KVKK m.6", ["01", "02", "10"])
        if a.get("source") in ("client", "public", "third_party"):
            add(f"art14:{a['id']}", "info", f"'{name}' collects data not from the person: Art. 14 notice",
                "People whose data comes from clients or public sources must be told within one month, unless an "
                "Art. 14(5) exemption applies and is documented (e.g. 14(5)(b) disproportionate effort, or 14(5)(d) "
                "professional secrecy under Union or Member State law). Record which exemption you rely on.",
                "GDPR Art. 14(3), 14(5)", ["03"])
        if not a.get("retention"):
            add(f"ret:{a['id']}", "open", f"How long is data from '{name}' kept?",
                "Each purpose needs a retention period or the criteria that set it.", "GDPR Arts. 5(1)(e), 30(1)(f)",
                ["01", "06"])
        if _yes(a.get("automated_decision")):
            add(f"art22:{a['id']}", "action", f"'{name}' makes decisions without a person",
                "A decision based solely on automated processing with legal or similarly significant effect is allowed "
                "only under Art. 22(2), with a right to human intervention. Keep a named reviewer in the loop.",
                "GDPR Art. 22", ["02", "03", "08"])

    # ---- 3. Vendors: DPA (Art. 28) and transfers (Chapter V, KVKK m.9).
    transfers: list[Transfer] = []
    for v in vendors:
        vname = v.get("name", v["id"])
        cc = v.get("country")
        local = cc == "LOCAL"
        if v.get("role") in ("processor", "sub_processor"):
            if v.get("dpa") in (None,):
                add(f"dpa:{v['id']}", "open", f"Is there a DPA with {vname}?",
                    "A processor may act only under a contract with the Art. 28(3) terms.", "GDPR Art. 28(3)", ["04"])
            elif v.get("dpa") in ("available", "none"):
                add(f"dpa:{v['id']}", "action", f"Sign or accept {vname}'s DPA",
                    "No processing on behalf of the controller without an Art. 28(3) contract. Check it against the "
                    "checklist in document 04 before accepting.", "GDPR Art. 28(3)", ["04"])
        if v.get("role") is None and not local:
            add(f"role:{v['id']}", "open", f"Is {vname} a processor or a controller?",
                "It decides whether you need an Art. 28 DPA or a controller-to-controller arrangement.",
                "GDPR Arts. 4(7)-(8), 28", ["04"])
        if _yes(v.get("trains_on_data")):
            add(f"train:{v['id']}", "risk", f"{vname} may use your data to train its models",
                "Training on client data is a new purpose of the vendor's own: it makes the vendor a controller for "
                "that part and is hard to square with confidentiality. Switch it off or choose a tier without it.",
                "GDPR Arts. 5(1)(b), 28(10)", ["02", "04"])
        sends = v.get("receives") in ("raw", "masked") and not local
        if sends and v.get("role") in ("processor", "sub_processor"):
            if _unknown(v.get("trains_on_data")):
                add(f"train?:{v['id']}", "open", f"Does {vname} train on what you send?",
                    "Check the plan's terms; API and business tiers usually differ from consumer apps.",
                    "GDPR Arts. 5(1)(b), 28(3)(a)", ["04"])
            if not v.get("retention"):
                add(f"vret:{v['id']}", "open", f"How long does {vname} keep prompts and outputs?",
                    "Include abuse-monitoring logs and backups; ask for zero retention if offered.",
                    "GDPR Arts. 5(1)(e), 28(3)(g)", ["04", "06"])
        if v.get("receives") == "masked" and not local:
            special = [d["label"] for d in data if d["id"] in v.get("data", []) and d.get("kind") in ("special", "criminal")]
            if special:
                add(f"maskspecial:{v['id']}", "risk", f"{vname} still sees the facts in {', '.join(special).lower()}",
                    "Masking hides who the person is, not what happened to them. A rare accident or diagnosis plus a "
                    "date and place can point back to the person. Keep such passages local or generalise them.",
                    "GDPR Arts. 9, 25, 32; Recital 26", ["02", "09"])
        if v.get("receives") == "raw" and not local:
            sensitive = {d.get("kind") for d in data if d["id"] in v.get("data", [])} & {"special", "criminal", "id_number"}
            if sensitive:
                add(f"raw:{v['id']}", "risk", f"{vname} receives unmasked {', '.join(sorted(sensitive))} data",
                    "Mask before sending (Katip does this on the device) or justify why the raw text is needed.",
                    "GDPR Arts. 5(1)(c), 25, 32(1)(a)", ["02", "09"])
        if local or not cc:
            if not cc:
                add(f"cc:{v['id']}", "open", f"Where does {vname} process the data?",
                    "Country and region of the servers decide whether there is a transfer.", "GDPR Art. 44", ["05"])
            continue
        if v.get("receives") == "none":
            continue
        mech = v.get("transfer_mechanism")
        if cc == ctl_cc and not in_eea:
            # Same country as a non-EU controller (e.g. a Turkish host for a Turkish firm): no onward
            # transfer, but the EU client's export to this country still needs a tool (finding eu_clients).
            route, tia = "same country", False
        elif cc in law.EEA:
            route, tia = "EEA", False
        elif cc in law.ADEQUATE:
            route, tia = "adequacy", False
        elif cc == "US" and _yes(v.get("dpf_certified")):
            route, tia = "DPF", False
        elif mech in ("scc", "bcr"):
            route, tia = mech.upper(), True
        elif mech is None:
            route, tia = "unknown", True
        else:
            route, tia = "missing", True
        kv = bool(kvkk) and cc != "TR"
        transfers.append(Transfer(v, cc, mech or "unknown", route, tia, kv))
        if route == "missing":
            add(f"xfer:{v['id']}", "action", f"No transfer tool for {vname} ({law.country(cc)})",
                "Personal data may go to a country without an adequacy decision only with an Art. 46 safeguard "
                "(usually the 2021 SCCs) plus a transfer impact assessment, or an Art. 49 derogation for occasional "
                "transfers.", "GDPR Arts. 44-49", ["05"])
        elif route == "unknown":
            hint = " Check whether it is on the Data Privacy Framework list." if cc == "US" else ""
            add(f"xfer:{v['id']}", "open", f"Which transfer tool covers {vname} ({law.country(cc)})?",
                "The questionnaire does not say." + hint, "GDPR Arts. 45-46", ["05"])
    kv_out = [t for t in transfers if t.kvkk_transfer and t.vendor.get("receives") in ("raw", "masked")]
    if kv_out:
        add("kvkk9", "action",
            "KVKK transfer abroad: " + ", ".join(t.vendor.get("name", t.vendor["id"]) for t in kv_out),
            "Since 1 June 2024, KVKK m.9 allows transfers abroad on an adequacy decision of the Board, appropriate "
            "safeguards (the Board's standard contract, notified to the Authority within 5 business days of "
            "signing; binding corporate rules; written undertakings) or the occasional-transfer exceptions. "
            "Explicit consent is no longer the general route. Masked text is still personal data for you, so "
            "the rule applies to it too.",
            "KVKK m.9; Regulation on transfers abroad (10 Jul 2024)", ["05"])

    # ---- 4. DPIA screening (Art. 35, WP248 criteria).
    kinds_all = {d.get("kind") for d in data}
    subjects = q.get("subjects", [])
    has_llm = any(a.get("models") for a in q.get("agents", []))
    met = {
        "scoring": any(_yes(a.get("profiling")) for a in acts),
        "automated_decision": any(_yes(a.get("automated_decision")) for a in acts),
        "monitoring": any(_yes(a.get("monitoring")) for a in acts),
        "sensitive": bool(kinds_all & {"special", "criminal"}),
        "large_scale": _yes(scale.get("large_scale")),
        "matching": any(_yes(a.get("combines_sources")) for a in acts),
        "vulnerable": any(_yes(s.get("vulnerable")) for s in subjects) or "minor" in kinds_all,
        "innovative": has_llm,
        "blocks_rights": any(_yes(a.get("can_block_service")) for a in acts),
    }
    why = {
        "scoring": "activities marked profiling: " + ", ".join(a["name"] for a in acts if _yes(a.get("profiling"))),
        "sensitive": "data categories: " + ", ".join(d["label"] for d in data if d.get("kind") in ("special", "criminal")),
        "matching": "activities combining sources: " + ", ".join(a["name"] for a in acts if _yes(a.get("combines_sources"))),
        "innovative": "agents built on language models",
        "large_scale": f"about {scale.get('data_subjects_per_year', '?')} people a year, marked large scale",
        "vulnerable": "vulnerable data subjects: " + ", ".join(s["label"] for s in subjects if _yes(s.get("vulnerable"))),
        "automated_decision": "activities marked automated decision",
        "monitoring": "activities marked monitoring",
        "blocks_rights": "activities that can block a service",
    }
    criteria = [(k, label, met[k], why.get(k, "") if met[k] else "") for k, label in law.DPIA_CRITERIA]
    n = sum(1 for c in criteria if c[2])
    dpia_required = n >= 2
    if dpia_required:
        add("dpia", "action", f"Do the DPIA before going live ({n} of 9 EDPB criteria met)",
            "Two or more criteria usually mean the processing is likely to result in a high risk. Document 02 is a "
            "starting draft; if high residual risk remains after measures, consult the supervisory authority first.",
            "GDPR Arts. 35(1), 35(7), 36; WP248 rev.01", ["02"])
    if _unknown(scale.get("large_scale")):
        add("scale", "open", "How many people's data a year?",
            "Scale feeds the DPIA, the DPO question and Art. 27(2).", "GDPR Arts. 35(3), 37(1); Recital 91", ["02"])

    # ---- 5. DPO (Art. 37).
    core_sensitive = bool(kinds_all & {"special", "criminal"}) and _yes(scale.get("large_scale"))
    if core_sensitive and not ctl.get("dpo"):
        add("dpo", "action", "Appoint a data protection officer",
            "Core activities include large-scale processing of Art. 9 or Art. 10 data.", "GDPR Art. 37(1)(c)", ["00"])
    elif kinds_all & {"special", "criminal"} and not ctl.get("dpo"):
        add("dpo", "info", "A DPO is probably not mandatory, but write down why",
            "Recital 91 says processing by an individual lawyer is not large scale. Record the reasoning and name a "
            "privacy contact instead.", "GDPR Art. 37(1)(c), Recital 91", ["00"])

    # ---- 6. Security (Art. 32).
    for key, title, cite in [
        ("encryption_in_transit", "Encryption in transit", "Art. 32(1)(a)"),
        ("encryption_at_rest", "Encryption at rest", "Art. 32(1)(a)"),
        ("mfa", "Multi-factor login for staff and admin accounts", "Art. 32(1)(b)"),
        ("logging", "Access and agent-action logs", "Art. 32(1)(b), 33(5)"),
        ("backups", "Backups and restore test", "Art. 32(1)(c)"),
        ("incident_owner", "A named person who runs a breach", "Arts. 33-34"),
    ]:
        val = sec.get(key)
        if val is None:
            add(f"sec:{key}", "open", f"Security: {title}?", "Not answered.", "GDPR " + cite, ["09"])
        elif val is False:
            add(f"sec:{key}", "action", f"Security: add {title.lower()}", "Answered 'no'.", "GDPR " + cite, ["09"])
    if not _yes(sec.get("masking_before_cloud")) and any(v.get("receives") == "raw" for v in vendors):
        add("mask", "risk", "Cloud models see the raw text",
            "Pseudonymising before the model call (Art. 4(5)) is the cheapest strong measure available here.",
            "GDPR Arts. 25, 32(1)(a)", ["02", "09"])
    if _yes(sec.get("masking_before_cloud")):
        add("mask_note", "info", "Masked text is pseudonymised, not anonymous",
            "Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a "
            "recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v "
            "SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Do not describe the system as "
            "'anonymous'.", "GDPR Art. 4(5), Recital 26; CJEU C-413/23 P", ["02", "03", "09"])

    # ---- 7. EU AI Act.
    role = ai.get("role") or "deployer"
    if _yes(ai.get("offered_under_own_name")):
        role = "provider" if role == "deployer" else role
    areas = ai.get("annex_iii") or []
    if _yes(ai.get("predicts_crime_risk")):
        ai_risk = "prohibited?"
        add("ai5", "action", "Check the Art. 5(1)(d) prohibition",
            "AI that predicts whether a person will commit a crime based solely on profiling or personality traits is "
            "prohibited since 2 Feb 2025. Support for a human assessment based on objective, verifiable facts linked "
            "to a criminal activity is allowed. Keep screening to exact matches against official lists with the "
            "source shown, and no risk score about a person.", "AI Act Art. 5(1)(d)", ["10", "02"])
    elif areas:
        ai_risk = "high-risk"
        add("ai_high", "action", "The system may be high-risk under the AI Act",
            "Listed areas: " + "; ".join(law.ANNEX_III.get(x, x) for x in areas) + ". Check the Art. 6(3) "
            "exceptions; if none applies, deployers have Art. 26 duties (and Art. 27 FRIA for some).",
            "AI Act Arts. 6, 26, 27; Annex III", ["10"])
    elif _unknown(ai.get("annex_iii")):
        ai_risk = "open"
        add("ai_area", "open", "Is the system used for hiring, credit, courts, or other Annex III areas?",
            "Those uses make the system high-risk.", "AI Act Art. 6(2), Annex III", ["10"])
    else:
        ai_risk = "limited / minimal"
    add("ai4", "info", "AI literacy",
        "Everyone who operates the agents needs enough AI literacy for their role, in force since 2 Feb 2025. Keep a "
        "short training record.", "AI Act Art. 4", ["10", "09"])
    if _yes(ai.get("chats_with_people")):
        add("ai50_1", "action", "Tell people they are talking to an AI",
            "Systems that interact directly with natural persons must say so, unless obvious.", "AI Act Art. 50(1)",
            ["10", "03"])
    if _yes(ai.get("publishes_text")):
        add("ai50_4", "info", "Published AI text on public-interest matters",
            "Deployers must disclose AI-generated text published to inform the public, unless a person reviewed it and "
            "holds editorial responsibility.", "AI Act Art. 50(4)", ["10"])

    # ---- 8. Breach and rights basics.
    if not q.get("controller", {}).get("contact"):
        add("contact", "open", "Privacy contact address", "Needed in the notice and the RoPA.",
            "GDPR Arts. 13(1)(a), 30(1)(a)", ["01", "03"])

    F.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.id))
    return Analysis(q, F, transfers, criteria, dpia_required, applicability, role, ai_risk)
