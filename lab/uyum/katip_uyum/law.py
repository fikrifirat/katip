"""Reference data the pack cites. Every list here is dated: law moves, so check before relying on it.

Nothing in this file is legal advice. It is the minimum the generator needs to put the right article
next to the right question.
"""
from __future__ import annotations

CHECKED = "23 Nov 2026 (compiled from the texts; re-check lists marked 'moving' before use)"

# EEA = EU 27 + Iceland, Liechtenstein, Norway (ISO 3166 alpha-2).
EU = set("AT BE BG HR CY CZ DK EE FI FR DE GR IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())
EEA = EU | {"IS", "LI", "NO"}

# Art. 45 adequacy decisions (moving: Commission list at the URL below). "US" only covers
# organisations certified under the EU-US Data Privacy Framework (Decision (EU) 2023/1795).
ADEQUATE = {
    "AD": "Andorra", "AR": "Argentina", "CA": "Canada (commercial organisations under PIPEDA)",
    "FO": "Faroe Islands", "GG": "Guernsey", "IL": "Israel", "IM": "Isle of Man", "JP": "Japan",
    "JE": "Jersey", "NZ": "New Zealand", "KR": "Republic of Korea", "CH": "Switzerland",
    "GB": "United Kingdom", "UY": "Uruguay",
}
ADEQUACY_URL = ("https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/"
                "adequacy-decisions_en")

COUNTRY = {
    "TR": "Türkiye", "US": "United States", "DE": "Germany", "FR": "France", "NL": "Netherlands",
    "IE": "Ireland", "BE": "Belgium", "SE": "Sweden", "FI": "Finland", "AT": "Austria", "IT": "Italy",
    "ES": "Spain", "PL": "Poland", "GB": "United Kingdom", "CH": "Switzerland", "LOCAL": "the user's own computer",
}


def country(code: str | None) -> str:
    if not code:
        return "unknown"
    return COUNTRY.get(code, ADEQUATE.get(code, code))


LAWFUL_BASIS = {
    "6(1)(a)": "consent",
    "6(1)(b)": "performance of a contract with the data subject",
    "6(1)(c)": "compliance with a legal obligation of the controller",
    "6(1)(d)": "vital interests",
    "6(1)(e)": "public interest or official authority",
    "6(1)(f)": "legitimate interests",
}

ART9 = {
    "9(2)(a)": "explicit consent",
    "9(2)(b)": "employment and social security law",
    "9(2)(e)": "made manifestly public by the data subject",
    "9(2)(c)": "vital interests where the person cannot consent",
    "9(2)(f)": "establishment, exercise or defence of legal claims",
    "9(2)(h)": "medical care under professional secrecy",
    "9(2)(g)": "substantial public interest (needs Union or Member State law)",
}

# KVKK equivalents (Law No. 6698, as amended by Law No. 7499 in force 1 June 2024).
KVKK_BASIS = {
    "6(1)(a)": "KVKK m.5/1 (açık rıza)",
    "6(1)(b)": "KVKK m.5/2-c (sözleşmenin kurulması veya ifası)",
    "6(1)(c)": "KVKK m.5/2-ç (hukuki yükümlülük)",
    "6(1)(d)": "KVKK m.5/2-b (hayati menfaat)",
    "6(1)(e)": "no direct KVKK match; closest m.5/2-a (kanunlarda açıkça öngörülme)",
    "6(1)(f)": "KVKK m.5/2-f (meşru menfaat)",
}
# KVKK m.6/3 as amended by Law No. 7499 (checked against the consolidated text; test_uyum checks it too).
KVKK_ART9 = {
    "9(2)(a)": "KVKK m.6/3-a (açık rıza)",
    "9(2)(b)": "KVKK m.6/3-f (istihdam, iş sağlığı ve güvenliği, sosyal güvenlik yükümlülükleri)",
    "9(2)(c)": "KVKK m.6/3-c (fiili imkânsızlık; hayat veya beden bütünlüğü)",
    "9(2)(e)": "KVKK m.6/3-ç (ilgili kişinin alenileştirmesi)",
    "9(2)(f)": "KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması)",
    "9(2)(g)": "KVKK m.6/3-b (kanunlarda açıkça öngörülme)",
    "9(2)(h)": "KVKK m.6/3-e (sağlık hizmetleri, sır saklama yükümlülüğü altındakilerce)",
}
# KVKK bases with no GDPR twin. m.5/2-e is the usual one for lawyers' work for clients.
KVKK_ONLY = {
    "m.5/2-e": "KVKK m.5/2-e (bir hakkın tesisi, kullanılması veya korunması)",
    "m.5/2-a": "KVKK m.5/2-a (kanunlarda açıkça öngörülme)",
    "m.5/2-d": "KVKK m.5/2-d (ilgili kişinin alenileştirmesi)",
}

# EDPB/WP29 DPIA guidelines (WP248 rev.01): two or more criteria usually means a DPIA is required.
DPIA_CRITERIA = [
    ("scoring", "Evaluation or scoring, including profiling and predicting"),
    ("automated_decision", "Automated decision-making with legal or similarly significant effect"),
    ("monitoring", "Systematic monitoring"),
    ("sensitive", "Sensitive data or data of a highly personal nature (Art. 9, Art. 10 data)"),
    ("large_scale", "Data processed on a large scale"),
    ("matching", "Matching or combining datasets"),
    ("vulnerable", "Data concerning vulnerable data subjects (employees, children, patients...)"),
    ("innovative", "Innovative use or new technological or organisational solutions (EDPB lists AI)"),
    ("blocks_rights", "Processing that prevents data subjects from exercising a right or using a service"),
]

# EU AI Act, Regulation (EU) 2024/1689, Art. 113 as amended by the Digital Omnibus on AI, Regulation
# (EU) 2026/1744 of 8 July 2026 (in force 27 July 2026). Read from the consolidated text on
# artificialintelligenceact.eu on 23 Nov 2026; confirm against EUR-Lex before relying on it.
AI_ACT_AMENDMENT = "Regulation (EU) 2026/1744 (Digital Omnibus on AI), in force 27 July 2026"
AI_ACT_DATES = [
    ("1 Aug 2024", "Regulation in force"),
    ("2 Feb 2025", "Chapters I and II apply: prohibited practices (Art. 5) and AI literacy (Art. 4)"),
    ("2 Aug 2025", "General-purpose AI model obligations (Chapter V), governance, penalties apply"),
    ("2 Aug 2026", "The rest of the Regulation applies, incl. Art. 50 transparency, unless a later date below"),
    ("2 Dec 2026", "New prohibitions added by Regulation (EU) 2026/1744 (Art. 5(1)(ba), (bb), 5(1a), (1b))"),
    ("2 Dec 2027", "High-risk systems under Art. 6(2) and Annex III (was 2 Aug 2026 before the 2026 amendment)"),
    ("2 Aug 2028", "High-risk systems under Art. 6(1) and Annex I (was 2 Aug 2027)"),
]

# Annex III areas a legal-services harness can stumble into.
ANNEX_III = {
    "employment": "Annex III point 4: recruitment, selection, decisions on work relationships",
    "credit": "Annex III point 5(b): creditworthiness or credit score of natural persons",
    "insurance": "Annex III point 5(c): risk and pricing for life and health insurance",
    "justice": "Annex III point 8(a): used by or on behalf of a judicial authority (or similarly in ADR) to "
               "research and interpret facts and law and apply the law to facts",
    "migration": "Annex III point 7: migration, asylum and border control",
    "biometric": "Annex III point 1: biometrics",
    "education": "Annex III point 3: education and vocational training",
    "essential_services": "Annex III point 5(a): eligibility for public assistance benefits and services",
    "law_enforcement": "Annex III point 6: law enforcement",
}

SOURCES = {
    "GDPR": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
    "AI Act": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
    "KVKK": "https://www.mevzuat.gov.tr/mevzuatmetin/1.5.6698.pdf",
    "SCCs (Decision 2021/914)": "https://eur-lex.europa.eu/eli/dec_impl/2021/914/oj",
    "EDPB Recommendations 01/2020 (transfer tools)": "https://www.edpb.europa.eu/our-work-tools/our-documents/recommendations/recommendations-012020-measures-supplement-transfer_en",
    "WP248 rev.01 (DPIA)": "https://ec.europa.eu/newsroom/article29/items/611236",
    "EDPB Guidelines 9/2022 (breach notification)": "https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-92022-personal-data-breach-notification-under_en",
    "EDPB Guidelines 3/2018 (territorial scope)": "https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32018-territorial-scope-gdpr-article-3-version_en",
    "EU-US Data Privacy Framework list": "https://www.dataprivacyframework.gov/list",
    "Adequacy decisions": ADEQUACY_URL,
}


# Standard contractual clauses, Decision (EU) 2021/914. Module choice follows the parties' roles.
SCC_MODULES = {
    ("controller", "controller"): "Module One (controller to controller)",
    ("controller", "processor"): "Module Two (controller to processor)",
    ("processor", "processor"): "Module Three (processor to processor)",
    ("processor", "controller"): "Module Four (processor to controller)",
}
SCC_CLAUSES = {
    "onward": "Clause 8.7 (Module One) / Clause 8.8 (Module Two): onward transfers",
    "breach": "Clause 8.5 (Module One) / Clause 8.6 (Module Two): security of processing, incl. breach notification",
    "local_laws": "Clause 14: local laws and practices (the TIA)",
    "gov_access": "Clause 15: requests from public authorities",
}

# Turkish laws a TIA for data held in Türkiye usually has to discuss. Candidates for the reviewing
# lawyer to confirm and analyse, not a finished list.
TR_ACCESS_LAWS = [
    "CMK m.130 (search of law offices: by a judge's decision, under the prosecutor's supervision, with the bar president or a representative present)",
    "Law No. 2937 on State Intelligence Services and MİT (powers to request information and documents)",
    "Law No. 5651 (internet content and traffic data)",
    "KVKK m.28 (processing by public authorities outside parts of the Law: e.g. national security, criminal investigations)",
    "Avukatlık Kanunu m.36 (lawyer's duty of secrecy) and m.58 (investigations concerning lawyers)",
]

# KVKK Board decision 2018/10 (31.01.2018): adequate measures for special-category data (m.6/4).
# Summary for a checklist; the decision text is authoritative.
KVKK_2018_10 = [
    "A separate written policy and procedure for special-category data",
    "Regular training of staff who handle it; confidentiality agreements",
    "Clear authorisations and periodic access reviews; access removed at once when a role changes",
    "Electronic: encryption, keys kept separately, logs of all actions, security updates, two-factor for remote access",
    "Physical: adequate physical security and entry controls where it is kept",
    "Transfers: encrypted corporate e-mail or KEP; encrypted portable media; VPN or sFTP between servers",
]

# Where a vendor or partner is used for client secrets, secrecy rules decide as much as the GDPR.
SECRECY = {
    "TR": "Avukatlık Kanunu m.36 (sır saklama) and TBB Meslek Kuralları",
    "DE": "§ 203 StGB and § 43e BRAO (German lawyers may use IT service providers only with written secrecy undertakings)",
}
