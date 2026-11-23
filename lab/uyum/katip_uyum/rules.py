"""Turn a questionnaire into findings: what the law asks for, given these data flows.

Deterministic and explainable: every finding names the facts that triggered it and the article it
comes from. A finding is a prompt for the reviewing lawyer, not a conclusion. An unanswered question
stays an open question: it never silently counts as "no".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import law
from .model import activity_data, activity_role, activity_subjects, activity_vendors, by_id, receives, review_state, sources

SEVERITY_ORDER = {"action": 0, "risk": 1, "open": 2, "info": 3}
SEVERITY_LABEL = {"action": "Must do", "risk": "Risk to address", "open": "Open question", "info": "Note"}
SEVERITY_TR = {"action": "Yapılmalı", "risk": "Risk", "open": "Açık soru", "info": "Not"}
THEMES = {
    "scope": "Which law applies, and to what",
    "basis": "Legal bases",
    "sensitive": "Special-category and criminal data",
    "vendors": "Vendors and contracts",
    "transfers": "Transfers abroad",
    "agents": "Agents and human review",
    "security": "Security",
    "retention": "Retention",
    "rights": "Information and rights",
    "ai_act": "EU AI Act",
}
THEMES_TR = {
    "scope": "Hangi hukuk, neye uygulanıyor", "basis": "Hukuki sebepler", "sensitive": "Özel nitelikli ve ceza verileri",
    "vendors": "Hizmet sağlayıcılar ve sözleşmeler", "transfers": "Yurt dışına aktarım", "agents": "Ajanlar ve insan kontrolü",
    "security": "Güvenlik", "retention": "Saklama süreleri", "rights": "Aydınlatma ve başvurular", "ai_act": "AB Yapay Zekâ Tüzüğü",
}


@dataclass
class Finding:
    id: str
    severity: str  # action | risk | open | info
    title: str
    detail: str
    cite: str
    docs: list[str] = field(default_factory=list)
    title_tr: str = ""
    theme: str = "scope"
    weight: int = 1  # harm to people if left as is: sensitivity of the data, minus paperwork-only items

    @property
    def rank(self):
        return (SEVERITY_ORDER[self.severity], -self.weight, self.id)

    @property
    def top_rank(self):
        # For "do these first": what can hurt people comes before missing paperwork, so weight leads.
        return (-self.weight, SEVERITY_ORDER[self.severity], self.id)


@dataclass
class Transfer:
    vendor: dict
    country: str
    mechanism: str        # what the questionnaire says
    route: str            # EEA | adequacy | DPF | SCC | BCR | onward (client SCCs) | same country | missing | unknown
    needs_tia: bool
    kvkk_transfer: bool   # data leaves Türkiye (KVKK m.9) when KVKK applies
    receives: str | None = None


@dataclass
class Analysis:
    q: dict
    findings: list[Finding]
    transfers: list[Transfer]
    dpia_criteria: list[tuple[str, str, bool | None, str]]
    dpia_required: bool
    dpia_min: int
    dpia_unknown: int
    applicability: list[str]
    ai_role: str
    ai_risk: str
    kvkk: bool
    eea_controller: bool
    art3_2: bool

    def by_doc(self, doc: str) -> list[Finding]:
        return [f for f in self.findings if doc in f.docs]

    def top(self, n=5) -> list[Finding]:
        out, kinds = [], set()
        for f in sorted([f for f in self.findings if f.severity in ("action", "risk")], key=lambda f: f.top_rank):
            kind = f.id.split(":")[0]
            if kind in kinds:  # one 'raw:' line stands for all vendors that get raw text
                continue
            kinds.add(kind)
            out.append(f)
        return out[:n]


def _yes(x):
    return x is True


def _unknown(x):
    return x is None


SENSITIVE_WEIGHT = {"special": 3, "criminal": 3, "minor": 3, "id_number": 2, "financial": 1}
NEVER = re.compile(r"\b(never|not deleted|indefinite|unlimited|forever|kept until further notice|süresiz|silinmez)\b", re.I)


def analyse(q: dict) -> Analysis:
    F: list[Finding] = []

    def add(fid, sev, title, detail, cite, docs, tr="", theme="scope", weight=1):
        F.append(Finding(fid, sev, title, detail, cite, docs, tr, theme, weight))

    ctl, scope, sec = q["controller"], q.get("scope", {}), q.get("security", {})
    ai, scale = q.get("ai", {}), q.get("scale", {})
    acts, vendors, data = q.get("activities", []), q.get("vendors", []), q.get("data", [])
    agents, partners, subjects = q.get("agents", []), q.get("partners", []), q.get("subjects", [])
    data_ix, subj_ix, agent_ix = by_id(q, "data"), by_id(q, "subjects"), by_id(q, "agents")
    ctl_cc = ctl.get("country")
    in_eea = ctl_cc in law.EEA or _yes(ctl.get("eu_establishment"))
    kvkk = scope.get("kvkk_applies")
    if kvkk is None:
        kvkk = ctl_cc == "TR"

    def weight_of(data_ids):
        return max([SENSITIVE_WEIGHT.get(data_ix[d].get("kind"), 0) for d in data_ids if d in data_ix] or [0]) + 1

    # ------------------------------------------------------------------ 1. Scope (GDPR Art. 3)
    applicability = []
    art3_2 = False
    if in_eea:
        applicability.append("Art. 3(1): the controller has an establishment in the EU/EEA, so the GDPR applies to all "
                             "processing in the context of that establishment.")
    else:
        if _yes(scope.get("offers_to_eu_data_subjects")) or _yes(scope.get("monitors_eu_behaviour")):
            art3_2 = True
            applicability.append("Art. 3(2): the GDPR applies directly, but only to the processing related to offering "
                                 "services to people in the EU (3(2)(a)) or monitoring their behaviour there (3(2)(b)). "
                                 "Other activities (e.g. screening Turkish company officers) are not pulled in by this "
                                 "alone; the activity table in document 01 says which route applies to each.")
        if _yes(scope.get("eu_clients")):
            applicability.append("EU clients send personal data out of the EU/EEA: for them that is a transfer under "
                                 "Chapter V, so the GDPR's standards reach this firm through the SCCs it signs with them "
                                 "(Decision (EU) 2021/914), even where Art. 3(2) does not apply.")
        if not applicability:
            add("scope", "open", "Does the GDPR apply at all?",
                "The controller is outside the EU/EEA and the questionnaire does not say whether it offers services to "
                "people in the EU, monitors them, or receives data from EU clients. Each answer changes the pack.",
                "GDPR Art. 3; EDPB Guidelines 3/2018", ["00", "01"], "GDPR hiç uygulanıyor mu?")
    if kvkk:
        applicability.append("KVKK (Law No. 6698) applies in parallel: the controller processes data in Türkiye.")
    if art3_2 and not ctl.get("eu_representative"):
        add("art27", "action", "Appoint an EU representative (Art. 27)",
            "The GDPR reaches this controller directly through Art. 3(2) and it has no EU establishment, so it must "
            "designate in writing a representative in a Member State where the people concerned are. The exemption in "
            "Art. 27(2)(a) needs processing that is occasional, does not include large-scale Art. 9 or Art. 10 data and "
            "is unlikely to result in a risk: document why, if you rely on it.",
            "GDPR Art. 27", ["00", "01", "03"], "AB temsilcisi atanmalı (GDPR m.27)", "scope", 2)
    if not in_eea and applicability and _unknown(scope.get("offers_to_eu_data_subjects")):
        add("art3_2", "open", "Does the GDPR reach you directly (Art. 3(2))?",
            "If you offer services to people in the EU (individuals, not only EU companies) the GDPR applies directly to "
            "that processing and you need an EU representative (Art. 27). If not, it reaches you through your EU "
            "clients' SCCs. The answer decides documents 00, 01, 03 and 07.",
            "GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018", ["00", "01", "03", "07"],
            "GDPR size doğrudan uygulanıyor mu (m.3/2)?")
    if _yes(scope.get("eu_clients")) and not in_eea:
        mod = law.SCC_MODULES.get(("controller", "processor" if ctl.get("role") == "processor" else "controller"))
        add("eu_scc", "action", f"Prepare SCCs for EU clients who send files to {law.country(ctl_cc)}",
            f"{law.country(ctl_cc)} has no EU adequacy decision, so each EU client needs the 2021 SCCs with you and its "
            f"own transfer impact assessment. As an independent controller you would sign {mod}; where a client "
            "instructs you as its processor, Module Two. Document 05 has a pre-filled annex and the list of local laws "
            "the TIA has to discuss.", "GDPR Art. 46(2)(c); Decision (EU) 2021/914", ["05", "04"],
            f"AB müvekkilleri için SCC hazırlanmalı ({law.country(ctl_cc)} için yeterlilik kararı yok)", "transfers", 3)
    if _unknown(scope.get("eu_clients")) and not in_eea:
        add("eu_clients", "open", "Do EU clients send their own files into the system?",
            "If yes, each EU client is exporting data to a non-EU recipient and needs SCCs with you.",
            "GDPR Arts. 44, 46(2)(c)", ["04", "05"], "AB müvekkilleri dosya gönderiyor mu?", "transfers")

    # ------------------------------------------------------------------ 2. Controller or processor
    role = ctl.get("role")
    if role in ("processor", "both") or any(a.get("role") == "processor" for a in acts):
        add("art30_2", "action", "Settle, per client and matter, whether you are controller or processor",
            "A lawyer giving legal advice usually decides why and how client data is used, which makes the firm a "
            "controller (EDPB Guidelines 07/2020 give lawyers as an example). Where a client nevertheless wants an "
            "Art. 28 contract (e.g. a German client asking for an AVV) for work done strictly on its instructions, "
            "you are its processor for that work: you then need the Art. 28(3) terms with the client, a processor's "
            "record (Art. 30(2)) and breach notices to the client, not to the authority (Art. 33(2)). Document 04 has a "
            "section on this.", "GDPR Arts. 4(7)-(8), 28(3), 30(2); EDPB Guidelines 07/2020",
            ["04", "01", "07"], "Her müvekkil için veri sorumlusu mu veri işleyen mi olduğunuz netleşmeli", "vendors", 2)
    elif role is None:
        add("role", "open", "Are you controller or processor towards your clients?",
            "Usually controller for legal advice; it decides which contract each client needs.",
            "GDPR Arts. 4(7)-(8), 28; EDPB Guidelines 07/2020", ["04"], "Müvekkillere karşı rolünüz ne?", "vendors")
    for p in partners:
        if p.get("role") == "joint_controller" and not _yes(p.get("arrangement")):
            add(f"art26:{p['id']}", "action", f"Joint-controller arrangement with {p['name']}",
                "Where you and another firm decide purposes and means together, Art. 26 requires a transparent "
                "arrangement on who does what (notices, requests), and its essence must be made available to the people "
                "concerned. Document 04 has a checklist.", "GDPR Art. 26(1)-(2)", ["04", "03"],
                f"{p['name']} ile ortak veri sorumluluğu düzenlemesi yapılmalı", "vendors", 2)
    for v in vendors:
        if v.get("role") == "joint_controller":
            add(f"art26:{v['id']}", "action", f"Joint-controller arrangement with {v['name']}",
                "Art. 26 requires an arrangement allocating the duties.", "GDPR Art. 26(1)-(2)", ["04"],
                f"{v['name']} ile ortak veri sorumluluğu düzenlemesi", "vendors", 2)

    # ------------------------------------------------------------------ 3. Bases, special and criminal data
    art10_acts = []
    for a in acts:
        name = a.get("name", a["id"])
        kinds = {d.get("kind") for d in activity_data(q, a)}
        w = weight_of(a.get("data", []))
        basis = a.get("lawful_basis")
        subs = activity_subjects(q, a)
        if not basis:
            add(f"basis:{a['id']}", "open", f"Lawful basis for '{name}'",
                "Each purpose needs one Art. 6(1) basis, chosen before processing starts.", "GDPR Arts. 5(1)(a), 6(1)",
                ["01", "03"], f"'{name}' için hukuki sebep", "basis")
        elif basis == "6(1)(b)":
            outsiders = [s["label"] for s in subs if not _yes(s.get("contract_party"))]
            if outsiders:
                add(f"basis6b:{a['id']}", "action", f"Split the legal basis for '{name}'",
                    "Art. 6(1)(b) covers only processing necessary for a contract with the data subject. These people "
                    f"have no contract with the firm: {', '.join(outsiders)}. Use 6(1)(b) for the contracting client "
                    "(an individual), and 6(1)(f) with a legitimate-interests test (document 11) for everyone else, "
                    "including the contact persons of corporate clients.",
                    "GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019", ["01", "03", "11"],
                    f"'{name}' için hukuki sebep ayrılmalı (sözleşmenin tarafı olmayan kişiler)", "basis", min(w, 2))
        if basis == "6(1)(f)" and not a.get("legitimate_interest"):
            add(f"lia:{a['id']}", "action", f"Write the legitimate-interests test for '{name}'",
                "Legitimate interests need a documented three-step test: a legitimate interest, necessity, and a balance "
                "against the data subjects' rights and reasonable expectations. Document 11 is the template, pre-filled.",
                "GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21", ["01", "02", "11"],
                f"'{name}' için meşru menfaat testi yazılmalı", "basis", min(w, 2))
        if "special" in kinds and not a.get("art9_condition"):
            add(f"art9:{a['id']}", "action", f"Art. 9 condition for '{name}'",
                "This activity touches special-category data (health, religion, ethnicity, ...). Besides an Art. 6 "
                "basis it needs an Art. 9(2) condition; for lawyers this is usually 9(2)(f) (legal claims). Under KVKK, "
                "the m.6/3 condition (usually m.6/3-d) and the Board's adequate measures (decision 2018/10) apply.",
                "GDPR Art. 9; KVKK m.6/3, m.6/4", ["01", "02", "09"], f"'{name}': özel nitelikli veri için şart (GDPR m.9, KVKK m.6/3)",
                "sensitive", 3)
        if "criminal" in kinds:
            art10_acts.append(a)
        if NEVER.search(a.get("retention") or ""):
            add(f"never:{a['id']}", "action", f"'{name}' keeps data with no end date",
                f"Retention '{a['retention']}' is not a limit. Set a period or the criteria that end it.",
                "GDPR Arts. 5(1)(e), 13(2)(a); KVKK m.7", ["06", "01"], f"'{name}': saklama süresi sınırsız", "retention", w)
        elif not a.get("retention"):
            add(f"ret:{a['id']}", "open", f"How long is data from '{name}' kept?",
                "Each purpose needs a retention period or the criteria that set it.", "GDPR Arts. 5(1)(e), 30(1)(f)",
                ["01", "06"], f"'{name}' verileri ne kadar saklanıyor?", "retention")
        if _yes(a.get("automated_decision")):
            add(f"art22:{a['id']}", "action", f"'{name}' makes decisions without a person",
                "A decision based solely on automated processing with legal or similarly significant effect is allowed "
                "only under Art. 22(2), with a right to human intervention. Keep a named reviewer in the loop.",
                "GDPR Art. 22; KVKK m.11/1-g", ["02", "03", "08"], f"'{name}' insan olmadan karar veriyor", "agents", w)
        if _yes(a.get("labels_people")):
            add(f"label:{a['id']}", "risk", f"'{name}' puts a risk label on people",
                "A per-person label (e.g. red/amber/green) is profiling (Art. 4(4)): it is personal data in its own right, "
                "must be accurate (Art. 5(1)(d)), and is exactly what a person will ask about under Art. 15. Write down "
                "the logic, show the source records next to it, and keep it internal. If the label predicts whether "
                "someone will commit an offence, see the AI Act Art. 5(1)(d) finding.",
                "GDPR Arts. 4(4), 5(1)(d), 15, 22", ["02", "10"], f"'{name}' kişilere risk etiketi veriyor", "agents", w)
        if sources(a) and a.get("source") is not None and any(s in ("client", "public", "third_party") for s in sources(a)):
            add(f"art14:{a['id']}", "info", f"'{name}' collects data not from the person: Art. 14 notice",
                "People whose data comes from clients or public sources must be told within one month, unless an "
                "Art. 14(5) exemption applies and is documented. Document 03, notice B.",
                "GDPR Art. 14(3), 14(5)", ["03"], f"'{name}': veriler kişinin kendisinden alınmıyor (GDPR m.14)", "rights")

    if art10_acts:
        screen = [a for a in art10_acts if not _yes(a.get("legal_service"))]
        legal = [a for a in art10_acts if _yes(a.get("legal_service"))]
        missing = [a for a in art10_acts if not a.get("art10_basis")]
        if missing:
            parts = []
            if screen:
                parts.append("For screening (" + ", ".join(a["name"] for a in screen) + "): GDPR Art. 10 allows "
                             "criminal-offence data only under official authority or where Union or Member State law "
                             "authorises it with safeguards. For AML-obliged clients that is the national AML law "
                             "(Regulation (EU) 2024/1624 and the transposition of Directive (EU) 2015/849); otherwise "
                             "consider screening companies only and keeping individuals to exact list matches.")
            if legal:
                parts.append("For legal advice and defence (" + ", ".join(a["name"] for a in legal) + "): the "
                             "criminal facts are the subject of the service, so 'screen less' is no answer. Art. 10 has no "
                             "legal-claims exception of its own; identify the Member State law that authorises lawyers "
                             "to process such data (many have one), or record why the GDPR does not reach this activity "
                             "directly (see Art. 3 in document 00).")
            add("art10", "action", "Name the legal authority for criminal-offence data (GDPR Art. 10)", " ".join(parts),
                "GDPR Art. 10", ["01", "02", "10"], "Ceza verileri için yasal dayanak gösterilmeli (GDPR m.10)", "sensitive", 3)
    if kvkk:
        conv, pend = [], []
        for a in art10_acts:
            types = {data_ix[d].get("criminal_type") for d in a.get("data", []) if data_ix[d].get("kind") == "criminal"}
            if types & {"conviction", "mixed", None}:
                conv.append(a.get("name", a["id"]))
            if types & {"proceedings", "sanctions_listing", "mixed"}:
                pend.append(a.get("name", a["id"]))
        if conv:
            add("kvkk6", "action", "KVKK m.6/3 condition for criminal data",
                "Under KVKK, data on criminal convictions and security measures is special-category data (m.6/1). It "
                "needs one of the m.6/3 conditions (for lawyers usually m.6/3-d, establishing or defending a right) "
                "and the Board's adequate measures (m.6/4, decision 2018/10). Activities: " + ", ".join(conv) + ".",
                "KVKK m.6/1, m.6/3-d, m.6/4", ["01", "09"], "Ceza verisi için KVKK m.6/3 şartı", "sensitive", 3)
        if pend:
            add("kvkk6q", "info", "Is a sanctions listing or pending case special-category data under KVKK?",
                "KVKK m.6/1 names 'ceza mahkûmiyeti ve güvenlik tedbirleri'. A sanctions or asset-freeze listing, or a "
                "pending prosecution, is not a conviction; whether it falls under m.6 is not settled. Treat it with "
                "m.6 safeguards until Board practice says otherwise, and record the choice. Activities: "
                + ", ".join(pend) + ".",
                "KVKK m.5, m.6/1", ["01"], "Yaptırım listesi veya devam eden dava KVKK m.6 kapsamında mı?",
                "sensitive")

    # ------------------------------------------------------------------ 4. Agents and human review
    for ag in agents:
        st = review_state(ag)
        if ag.get("output") in ("client", "court", "published") and st != "always":
            sev = "action" if st in ("never", "sometimes") else "open"
            wtxt = {"never": "never", "sometimes": "only sometimes", "unknown": "not said to be"}[st]
            add(f"noreview:{ag['id']}", "risk" if sev == "action" else "open",
                f"'{ag.get('name', ag['id'])}' sends output to the {ag['output']} that a lawyer {wtxt} reads first",
                "Outputs about people that leave the firm unchecked risk wrong facts about a person (Art. 5(1)(d)), "
                "the wrong recipient (the most common law-firm breach, Art. 33) and an Art. 22 decision without a "
                "person. Either require approval before sending, or limit what can be sent unreviewed and log it. "
                "The privacy notice no longer says 'a lawyer reviews every result' while this is open.",
                "GDPR Arts. 5(1)(d), 22, 25(1), 32(1)(b), 33", ["02", "03", "07", "09"],
                f"'{ag.get('name', ag['id'])}' avukat okumadan dışarı çıktı gönderiyor", "agents", 4)

    # ------------------------------------------------------------------ 5. Vendors: DPA, tiers, training, raw data
    transfers: list[Transfer] = []
    # Only vendors that touch client-supplied files carry EU-origin data onward.
    client_vendors = {x["id"] for a in q.get("activities", []) if "client" in sources(a) for x in activity_vendors(q, a)}
    for v in vendors:
        vname = v.get("name", v["id"])
        cc = v.get("country")
        local = cc == "LOCAL"
        rcv = receives(q, v)
        vw = weight_of(v.get("data", []))
        sends = rcv in ("raw", "masked") and not local
        sensitive = {data_ix[d].get("kind") for d in v.get("data", []) if d in data_ix} & {"special", "criminal", "id_number"}
        if v.get("role") in ("processor", "sub_processor") and sends:
            if v.get("dpa") is None:
                add(f"dpa:{v['id']}", "open", f"Is there a DPA with {vname}?",
                    "A processor may act only under a contract with the Art. 28(3) terms.", "GDPR Art. 28(3)", ["04"],
                    f"{vname} ile veri işleme sözleşmesi var mı?", "vendors")
            elif v.get("dpa") in ("available", "none"):
                if v.get("dpa") == "none" and (v.get("tier") == "free" or _yes(v.get("trains_on_data"))):
                    add(f"dpa:{v['id']}", "action", f"Stop sending client data to {vname}" + ("" if "tier" in vname else f" ({v.get('tier') or 'this'} tier)"),
                        "This tier offers no Art. 28 terms" + (" and may use your inputs for its own purposes" if
                                                               _yes(v.get("trains_on_data")) else "") +
                        ". The vendor is then not your processor but a separate recipient, which needs its own legal "
                        "basis (and an Art. 9 condition for health data) and is hard to square with lawyers' secrecy. "
                        "Move to a paid tier with a DPA, or keep this step on your own computer.",
                        "GDPR Arts. 28(1), 28(3), 28(10), 9(1); Avukatlık Kanunu m.36", ["04", "02"],
                        f"{vname}'e müvekkil verisi gönderilmesi durdurulmalı", "vendors", vw + 1)
                else:
                    add(f"dpa:{v['id']}", "action", f"Sign or accept {vname}'s DPA",
                        "No processing on behalf of the controller without an Art. 28(3) contract. Check it against the "
                        "checklist in document 04 before accepting.", "GDPR Art. 28(3)", ["04"],
                        f"{vname} ile veri işleme sözleşmesi yapılmalı", "vendors", vw)
            if _unknown(v.get("trains_on_data")):
                add(f"train?:{v['id']}", "open", f"Does {vname} train on what you send?",
                    "Check the plan's terms; API and business tiers usually differ from consumer apps.",
                    "GDPR Arts. 5(1)(b), 28(3)(a)", ["04"], f"{vname} gönderilen verilerle model eğitiyor mu?", "vendors")
            if not v.get("retention"):
                add(f"vret:{v['id']}", "open", f"How long does {vname} keep prompts and outputs?",
                    "Include abuse-monitoring logs and backups; ask for zero retention if offered.",
                    "GDPR Arts. 5(1)(e), 28(3)(g)", ["04", "06"], f"{vname} istem ve çıktıları ne kadar saklıyor?", "vendors")
        if v.get("role") is None and not local and sends:
            add(f"role:{v['id']}", "open", f"Is {vname} a processor or a controller?",
                "It decides whether you need an Art. 28 DPA or a controller-to-controller arrangement. Search APIs "
                "and tracing tools often receive the full text of queries and prompts.",
                "GDPR Arts. 4(7)-(8), 28", ["04"], f"{vname} veri işleyen mi veri sorumlusu mu?", "vendors")
        if _yes(v.get("trains_on_data")) and sends and f"dpa:{v['id']}" not in {f.id for f in F if f.severity == "action" and "Stop" in f.title}:
            add(f"train:{v['id']}", "risk", f"{vname} may use your data to train its models",
                "Training on client data is the vendor's own purpose: it makes the vendor a controller for that part and "
                "is hard to square with confidentiality. Switch it off or choose a tier without it.",
                "GDPR Arts. 5(1)(b), 28(10)", ["02", "04"], f"{vname} verilerinizle model eğitebilir", "vendors", vw)
        if rcv == "raw" and not local and sensitive:
            add(f"raw:{v['id']}", "risk", f"{vname} receives unmasked {', '.join(sorted(sensitive))} data",
                "Mask before sending (Katip does this on the device) or justify why the raw text is needed.",
                "GDPR Arts. 5(1)(c), 25, 32(1)(a)", ["02", "09"], f"{vname} maskelenmemiş hassas veri alıyor", "vendors", vw)
        if rcv == "masked" and not local:
            special = [data_ix[d]["label"] for d in v.get("data", []) if d in data_ix and data_ix[d].get("kind") in ("special", "criminal")]
            if special:
                add(f"maskspecial:{v['id']}", "risk", f"{vname} still sees the facts in {', '.join(special).lower()}",
                    "Masking hides who the person is, not what happened to them. A rare accident or diagnosis plus a "
                    "date and place can point back to the person. Keep such passages local or generalise them.",
                    "GDPR Arts. 9, 25, 32; Recital 26", ["02", "09"], f"{vname} maskeli metinde de olay ayrıntılarını görüyor",
                    "vendors", 2)
        if v.get("parent_country") and v.get("parent_country") != cc and cc in law.EEA and v["parent_country"] not in law.EEA:
            add(f"parent:{v['id']}", "info", f"{vname}: EU region, {law.country(v['parent_country'])} parent",
                "Hosting in the EU avoids a Chapter V transfer for storage, but a non-EU parent can be subject to its "
                "home country's access laws, and support or sub-processors may sit outside the EU. Check the "
                "sub-processor list and the contract's clause on government requests.",
                "GDPR Arts. 28(2), 44, 48; EDPB Guidelines 05/2021", ["05"],
                f"{vname}: AB'de sunucu, AB dışı ana şirket", "transfers")
        if local or not cc:
            if not cc and sends:
                add(f"cc:{v['id']}", "open", f"Where does {vname} process the data?",
                    "Country and region of the servers decide whether there is a transfer.", "GDPR Art. 44", ["05"],
                    f"{vname} verileri hangi ülkede işliyor?", "transfers")
            continue
        if rcv in ("none", None) and not sends:
            continue
        mech = v.get("transfer_mechanism")
        if cc == ctl_cc and not in_eea:
            route, tia = "same country", False
        elif cc in law.EEA:
            route, tia = "EEA", False
        elif cc in law.ADEQUATE:
            route, tia = "adequacy", False
        elif not in_eea and _yes(scope.get("eu_clients")) and mech != "none" and v["id"] in client_vendors:
            # A non-EU firm passing EU-origin data on: governed by the onward-transfer clause of the SCCs it signed
            # with each EU client. The DPF and adequacy decisions are tools for exporters in the EU, not for it.
            route, tia = "onward (client SCCs)", True
        elif cc == "US" and _yes(v.get("dpf_certified")) and in_eea:
            route, tia = "DPF", False
        elif mech in ("scc", "bcr"):
            route, tia = mech.upper(), True
        elif mech is None:
            route, tia = "unknown", True
        else:
            route, tia = "missing", True
        kv = bool(kvkk) and cc != "TR"
        transfers.append(Transfer(v, cc, mech or "unknown", route, tia, kv, rcv))
        if route == "missing":
            add(f"xfer:{v['id']}", "action", f"No transfer tool for {vname} ({law.country(cc)})",
                "Personal data may go to a country without an adequacy decision only with an Art. 46 safeguard "
                "(usually the 2021 SCCs) plus a transfer impact assessment, or an Art. 49 derogation for occasional "
                "transfers.", "GDPR Arts. 44-49", ["05"], f"{vname} için aktarım aracı yok", "transfers", vw)
        elif route == "unknown":
            hint = (" Check whether the exact contracting entity is on the Data Privacy Framework list."
                    if cc == "US" and in_eea else "")
            add(f"xfer:{v['id']}", "open", f"Which transfer tool covers {vname} ({law.country(cc)})?",
                "The questionnaire does not say." + hint, "GDPR Arts. 45-46", ["05"],
                f"{vname} için hangi aktarım aracı kullanılıyor?", "transfers")
        elif route == "onward (client SCCs)":
            add(f"onward:{v['id']}", "info", f"{vname}: onward transfer of EU clients' data",
                "Your EU clients' SCCs let you pass their data on to a third country only on the onward-transfer "
                f"conditions ({law.SCC_CLAUSES['onward']}): typically the recipient accepts the SCCs or another "
                "safeguard. The US Data Privacy Framework does not cover a transfer made by a Turkish firm.",
                "GDPR Art. 44; Decision (EU) 2021/914", ["05"], f"{vname}: AB müvekkil verisinin ileri aktarımı", "transfers")
    kv_out = [t for t in transfers if t.kvkk_transfer and t.receives in ("raw", "masked")]
    if kv_out:
        add("kvkk9", "action",
            "KVKK transfer abroad: " + ", ".join(t.vendor.get("name", t.vendor["id"]) for t in kv_out),
            "Since 1 June 2024, KVKK m.9 allows transfers abroad on an adequacy decision of the Board, appropriate "
            "safeguards (the Board's standard contract, notified to the Authority within 5 business days of "
            "signing; binding corporate rules; a written undertaking with the Board's permission) or the "
            "occasional-transfer exceptions of m.9/6. Explicit consent is no longer the general route. Masked text is "
            "still personal data for you, so the rule applies to it too.",
            "KVKK m.9; Regulation on transfers abroad (10 Jul 2024)", ["05"],
            "Yurt dışına aktarım (KVKK m.9): " + ", ".join(t.vendor.get("name", t.vendor["id"]) for t in kv_out), "transfers", 2)

    # ------------------------------------------------------------------ 6. DPIA screening (Art. 35, WP248)
    kinds_all = {d.get("kind") for d in data}
    has_llm = any(a.get("models") for a in agents)

    def any_of(key):
        vals = [a.get(key) for a in acts]
        return True if any(_yes(x) for x in vals) else (None if any(x is None for x in vals) and vals else False)

    vuln = [s["label"] for s in subjects if _yes(s.get("vulnerable")) or _yes(s.get("children"))]
    met = {
        "scoring": True if any(_yes(a.get("profiling")) or _yes(a.get("labels_people")) for a in acts) else any_of("profiling"),
        "automated_decision": any_of("automated_decision"),
        "monitoring": any_of("monitoring"),
        "sensitive": bool(kinds_all & {"special", "criminal"}),
        "large_scale": scale.get("large_scale"),
        "matching": any_of("combines_sources"),
        "vulnerable": True if vuln or "minor" in kinds_all else (None if any(s.get("vulnerable") is None for s in subjects) else False),
        "innovative": has_llm,
        "blocks_rights": any_of("can_block_service"),
    }
    why = {
        "scoring": "profiling or per-person labels: " + ", ".join(a["name"] for a in acts if _yes(a.get("profiling")) or _yes(a.get("labels_people"))),
        "sensitive": "data categories: " + ", ".join(d["label"] for d in data if d.get("kind") in ("special", "criminal")),
        "matching": "activities combining sources: " + ", ".join(a["name"] for a in acts if _yes(a.get("combines_sources"))),
        "innovative": "agents built on language models",
        "large_scale": f"about {scale.get('data_subjects_per_year', '?')} people a year, marked large scale",
        "vulnerable": "vulnerable data subjects: " + ", ".join(vuln or ["children's data"]),
        "automated_decision": "activities marked automated decision",
        "monitoring": "activities marked monitoring",
        "blocks_rights": "activities that can block a service",
    }
    criteria = [(k, label, met[k], (why.get(k, "") if met[k] else ("not answered" if met[k] is None else "")))
                for k, label in law.DPIA_CRITERIA]
    n_min = sum(1 for c in criteria if c[2] is True)
    n_unknown = sum(1 for c in criteria if c[2] is None)
    dpia_required = n_min >= 2
    if dpia_required:
        add("dpia", "action", f"Do the DPIA before going live (at least {n_min} of 9 EDPB criteria met)",
            "Two or more criteria usually mean the processing is likely to result in a high risk. Document 02 is a "
            "starting draft; if high residual risk remains after measures, consult the supervisory authority first.",
            "GDPR Arts. 35(1), 35(7), 36; WP248 rev.01", ["02"], "Canlıya almadan önce DPIA yapılmalı", "security", 2)
    if _unknown(scale.get("large_scale")):
        add("scale", "open", "How many people's data a year, and is that large scale?",
            "Scale feeds the DPIA, the DPO question and Art. 27(2).", "GDPR Arts. 35(3), 37(1); Recital 91", ["02"],
            "Yılda kaç kişinin verisi işleniyor?", "scope")
    if any(_yes(s.get("deceased")) for s in subjects):
        add("deceased", "info", "Deceased people",
            "The GDPR does not protect the data of deceased persons (Recital 27), but their relatives' data in the same "
            "file is protected, and some Member States and KVKK practice go further. Keep the same safeguards.",
            "GDPR Recital 27", ["02"], "Vefat etmiş kişilerin verileri", "sensitive")

    # ------------------------------------------------------------------ 7. DPO (Art. 37)
    if kinds_all & {"special", "criminal"} and not ctl.get("dpo"):
        if _yes(scale.get("large_scale")):
            add("dpo", "action", "Appoint a data protection officer",
                "Core activities include large-scale processing of Art. 9 or Art. 10 data.", "GDPR Art. 37(1)(c)", ["00"],
                "Veri koruma görevlisi (DPO) atanmalı", "scope", 2)
        else:
            add("dpo", "info", "A DPO is probably not mandatory, but write down why",
                "Recital 91 says processing by an individual lawyer is not large scale. Record the reasoning and name a "
                "privacy contact instead.", "GDPR Art. 37(1)(c), Recital 91", ["00"], "DPO zorunlu görünmüyor; gerekçe yazılmalı")

    # ------------------------------------------------------------------ 8. Security (Art. 32)
    for key, title, title_tr, cite in [
        ("encryption_in_transit", "Encryption in transit", "Aktarımda şifreleme", "Art. 32(1)(a)"),
        ("encryption_at_rest", "Encryption at rest", "Depolamada şifreleme", "Art. 32(1)(a)"),
        ("mfa", "Multi-factor login for staff and admin accounts", "Çok faktörlü giriş", "Art. 32(1)(b)"),
        ("logging", "Access and agent-action logs", "Erişim ve ajan kayıtları", "Art. 32(1)(b), 5(2)"),
        ("backups", "Backups", "Yedekleme", "Art. 32(1)(c)"),
        ("restore_tested", "A tested restore from backup", "Yedekten geri yükleme testi", "Art. 32(1)(c)-(d)"),
        ("incident_owner", "A named person who runs a breach", "İhlal sorumlusu kişi", "Arts. 33-34"),
    ]:
        val = sec.get(key)
        if val is None:
            add(f"sec:{key}", "open", f"Security: {title}?", "Not answered.", "GDPR " + cite, ["09"],
                f"Güvenlik: {title_tr}?", "security")
        elif val is False:
            add(f"sec:{key}", "action", f"Security: add {title.lower()}", "Answered 'no'.", "GDPR " + cite, ["09"],
                f"Güvenlik: {title_tr.lower()} eklenmeli", "security", 2)
    if _yes(sec.get("shared_logins")):
        add("sec:shared", "action", "Security: end shared logins and readable API keys",
            "Shared accounts and keys in a file anyone can read make access untraceable and impossible to revoke for one "
            "person. Use named accounts and a secrets store.", "GDPR Art. 32(1)(b), 32(4)", ["09"],
            "Ortak hesaplar ve açıkta API anahtarları kaldırılmalı", "security", 2)
    if not _yes(sec.get("masking_before_cloud")) and any(receives(q, v) == "raw" and v.get("country") != "LOCAL" for v in vendors):
        add("mask", "risk", "Cloud models see the raw text",
            "Pseudonymising before the model call (Art. 4(5)) is the cheapest strong measure available here.",
            "GDPR Arts. 25, 32(1)(a)", ["02", "09"], "Bulut modelleri ham metni görüyor", "security", 2)
    if _yes(sec.get("masking_before_cloud")) or any(receives(q, v) == "masked" for v in vendors):
        add("mask_note", "info", "Masked text is pseudonymised, not anonymous",
            "Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a "
            "recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v "
            "SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Describe masking as: detected "
            "values are masked and leak-checked before the text leaves the computer.",
            "GDPR Art. 4(5), Recital 26; CJEU C-413/23 P", ["02", "03", "09"], "Maskeli metin anonim değil, takma adlıdır",
            "security")
        eu_people = any(_yes(s.get("in_eu")) for s in subjects)
        prof = sec.get("masking_profile")
        if eu_people and prof in ("kvkk", "ai", "court", "share"):
            add("maskprofile", "risk", "EU documents are masked with a Turkish profile",
                f"Kalkan's '{prof}' profile is built for Turkish documents and misses EU ID formats (BSN, Steuer-ID, NIR, "
                "codice fiscale...) and many non-Turkish names. Use the 'eu' profile (beta) for EU clients' files.",
                "GDPR Arts. 25, 32(1)(a)", ["09", "02"], "AB belgeleri Türkçe profille maskeleniyor", "security", 2)
        elif eu_people and prof == "eu":
            add("maskprofile", "info", "The 'eu' masking profile is beta: lone names are its weak spot",
                "On synthetic tests it masked every checksummed EU ID, IBAN, VAT, phone and address, but only about half "
                "of bare names with no title or cue around them. Review names in EU documents before sending.",
                "GDPR Arts. 25, 32(1)(a)", ["09"], "'eu' maskeleme profili beta: tek başına geçen adlar zayıf nokta", "security")
        elif eu_people and prof is None:
            add("maskprofile", "open", "Which masking profile is used for EU documents?",
                "Kalkan has an 'eu' profile (beta) for EU ID formats and non-Turkish names.", "GDPR Art. 32(1)(a)", ["09"],
                "AB belgeleri hangi maskeleme profiliyle işleniyor?", "security")

    # ------------------------------------------------------------------ 9. Secrecy
    if q.get("secrecy") is None:
        add("secrecy", "open", "Which secrecy rules apply to client files?",
            "For a law firm these decide whether a cloud model may be used at all: Avukatlık Kanunu m.36 for a Turkish "
            "lawyer, and the client's own regime where a foreign law firm instructs (e.g. § 203 StGB, § 43e BRAO). "
            "Document 04 has a per-vendor secrecy check.", "Avukatlık Kanunu m.36; GDPR Art. 90", ["04"],
            "Hangi sır saklama kuralları uygulanıyor?", "vendors")

    # ------------------------------------------------------------------ 10. EU AI Act (as amended in 2026)
    ai_role = ai.get("role") or "deployer"
    if _yes(ai.get("offered_under_own_name")):
        ai_role = "provider" if ai_role == "deployer" else ai_role
    elif ai.get("offered_under_own_name") is None:
        add("ai_offer", "open", "Will you offer the system to others under your name?",
            "Then you become its provider (Art. 3(3)), with provider duties such as Art. 50(1)-(2).",
            "AI Act Arts. 3(3), 50", ["10"], "Sistemi kendi adınızla başkalarına sunacak mısınız?", "ai_act")
    areas = ai.get("annex_iii") or []
    labels = any(_yes(a.get("labels_people")) for a in acts)
    crim = bool(art10_acts)
    if _yes(ai.get("predicts_crime_risk")):
        ai_risk = "prohibited?"
        add("ai5", "action", "Check the AI Act Art. 5(1)(d) prohibition",
            "AI that predicts whether a person will commit a crime based solely on profiling or personality traits is "
            "prohibited since 2 Feb 2025. Support for a human assessment based on objective, verifiable facts linked "
            "to a criminal activity is allowed. Keep screening to matches against official lists with the source shown, "
            "and no prediction about a person.", "AI Act Art. 5(1)(d)", ["10", "02"],
            "AI Act m.5/1-d yasağı kontrol edilmeli", "ai_act", 3)
    elif ai.get("predicts_crime_risk") is None and (labels or crim):
        ai_risk = "open"
        add("ai5", "open", "Does any label or score predict whether a person will offend? (AI Act Art. 5(1)(d))",
            "The questionnaire leaves this open while the system " + ("labels people" if labels else "handles criminal "
            "data") + ". A list match shown with its source is outside the prohibition; a score of how likely someone is "
            "to offend, based on profiling, is not. Describe what the label means and how it is computed.",
            "AI Act Art. 5(1)(d); GDPR Art. 4(4)", ["10", "02"],
            "Herhangi bir etiket kişinin suç işleme olasılığını mı tahmin ediyor? (AI Act m.5/1-d)", "ai_act", 2)
    elif areas:
        ai_risk = "high-risk"
    elif _unknown(ai.get("annex_iii")):
        ai_risk = "open"
    else:
        ai_risk = "limited / minimal"
    if areas:
        add("ai_high", "action", "The system may be high-risk under the AI Act",
            "Listed areas: " + "; ".join(law.ANNEX_III.get(x, x) for x in areas) + ". Check the Art. 6(3) exceptions; if "
            "none applies, deployers have Art. 26 duties (and an Art. 27 assessment for some). Since the 2026 amendment "
            "(" + law.AI_ACT_AMENDMENT + "), Annex III obligations apply from 2 Dec 2027.",
            "AI Act Arts. 6, 26, 27, 113; Annex III", ["10"], "Sistem AI Act kapsamında yüksek riskli olabilir", "ai_act", 2)
    elif _unknown(ai.get("annex_iii")):
        add("ai_area", "open", "Is the system used for hiring, credit, courts, or other Annex III areas?",
            "Those uses make the system high-risk.", "AI Act Art. 6(2), Annex III", ["10"],
            "Sistem işe alım, kredi, yargı gibi Ek III alanlarında kullanılıyor mu?", "ai_act")
    add("ai4", "info", "AI literacy",
        "Providers and deployers must take measures to support the AI literacy of staff who operate AI systems (Art. 4 "
        "as amended in 2026). Keep a short training record.", "AI Act Art. 4", ["10", "09"], "Yapay zekâ okuryazarlığı",
        "ai_act")
    if _yes(ai.get("chats_with_people")):
        add("ai50_1", "action", "Tell people they are talking to an AI",
            "The provider must design a system that interacts directly with people so they are told (Art. 50(1)); as the "
            "deployer, make sure the notice is actually shown.", "AI Act Art. 50(1)", ["10", "03"],
            "Kişilere yapay zekâyla konuştukları söylenmeli", "ai_act")
    if _yes(ai.get("publishes_text")):
        add("ai50_4", "info", "Published AI text on public-interest matters",
            "Deployers must disclose AI-generated text published to inform the public, unless a person reviewed it and "
            "holds editorial responsibility.", "AI Act Art. 50(4)", ["10"], "Kamuya yayımlanan yapay zekâ metni", "ai_act")

    # ------------------------------------------------------------------ 11. Contacts and languages
    if not ctl.get("contact"):
        add("contact", "open", "Privacy contact address", "Needed in the notice and the record.",
            "GDPR Arts. 13(1)(a), 30(1)(a); KVKK m.10/1-a", ["01", "03"], "Kişisel veri iletişim adresi", "rights")
    if not any(s in ("data_subject",) for a in acts for s in sources(a)):
        add("art13_src", "open", "Which activities collect data directly from the person?",
            "No activity has the person as a source, so the Art. 13 notice would be empty. Clients who write in, "
            "website contacts and staff usually do give data directly: add 'data_subject' to those activities' sources.",
            "GDPR Art. 13(1)(c)", ["03"], "Hangi faaliyetler veriyi doğrudan kişiden alıyor?", "rights")

    F.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.theme, f.id))
    return Analysis(q, F, transfers, criteria, dpia_required, n_min, n_unknown, applicability, ai_role, ai_risk,
                    bool(kvkk), in_eea, art3_2)
