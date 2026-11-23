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
    "9(2)(f)": "establishment, exercise or defence of legal claims",
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
KVKK_ART9 = {
    "9(2)(a)": "KVKK m.6/3 (açık rıza)",
    "9(2)(b)": "KVKK m.6/3-d (istihdam, iş sağlığı, sosyal güvenlik yükümlülükleri)",
    "9(2)(e)": "KVKK m.6/3-c (ilgili kişinin alenileştirmesi)",
    "9(2)(f)": "KVKK m.6/3-ç (bir hakkın tesisi, kullanılması veya korunması)",
    "9(2)(g)": "KVKK m.6/3-a (kanunlarda açıkça öngörülme)",
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

# EU AI Act, Regulation (EU) 2024/1689, Art. 113. Moving: the Commission's "Digital Omnibus" proposal
# (19 Nov 2025) would postpone the high-risk dates; check whether it was adopted before relying on them.
AI_ACT_DATES = [
    ("1 Aug 2024", "Regulation in force"),
    ("2 Feb 2025", "Prohibited practices (Art. 5) and AI literacy (Art. 4) apply"),
    ("2 Aug 2025", "General-purpose AI model obligations (Chapter V), governance, penalties apply"),
    ("2 Aug 2026", "Most of the Regulation applies, incl. Annex III high-risk systems and Art. 50 transparency"),
    ("2 Aug 2027", "High-risk systems that are safety components of products under Annex I (Art. 6(1))"),
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
