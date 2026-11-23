# 03 · Privacy notices (GDPR Arts. 13 and 14)

**System:** Örnek Hukuk agent harness · **Controller:** Örnek Hukuk Bürosu · **Questionnaire dated:** 2026-11-23

> **DRAFT for lawyer review.** Katip drafted this from the questionnaire above. It is a starting point for the reviewing lawyer, not legal advice, and not a statement that the system meets the GDPR, KVKK or the AI Act. **[OPEN: ...]** marks facts that are still missing; document 00 lists what each one changes.

Two notices: **A** for clients and people who give their data directly (Art. 13), **B** for people whose data comes from clients or public sources, such as the subjects of a due-diligence report (Art. 14). Plain language is required (Art. 12(1)); translate into the languages of the people concerned. The Turkish notice under KVKK m.10 is [03-aydinlatma-metni.tr.md](03-aydinlatma-metni.tr.md).

# A · Clients and people who give us their data (Art. 13)

## Who we are

Örnek Hukuk Bürosu, Örnek Mah. 1. Sok. No:1, Beşiktaş, İstanbul. Privacy questions: kvkk@ornekhukuk.example.

## What we do with your data, on what basis, for how long

| Purpose | Legal basis | How long |
|---|---|---|
| Take on the client, identify the matter, check conflicts of interest | GDPR Art. 6(1)(f) (legitimate interests). Interest: Taking on the client and avoiding conflicts of interest; for individual clients the contract (6(1)(b)) also applies | 10 years after the matter closes |

## Who receives it

Service providers bound by contract to our instructions: Anthropic (Claude API) (Language model for drafting); Hetzner (Server for the vector store and agent logs). Other recipients: Mistral AI (Language model for intake sorting, **[OPEN: contract status]**); TOBB Türkiye Ticaret Sicili Gazetesi portal (Public gazette searched by company name, acts on its own account). Our clients receive the reports and opinions we prepare for them. Before text is sent to Anthropic (Claude API), Mistral AI, Hetzner, the names, ID numbers, contact details and addresses that our masking tool detects are replaced with placeholders on our own computer. These providers therefore receive pseudonymised text; it is still personal data for us.

## Transfers outside the EU/EEA

Anthropic (Claude API) (United States): onward (client SCCs). Ask us for a copy of the safeguards.

## Use of AI

We use AI systems to sort documents, research and draft. A lawyer reviews every result before it leaves our office; no decision about you is made by a machine alone (Art. 22).

## Your rights

You can ask for access (Art. 15), correction (16), deletion (17), restriction (18), portability where it applies (20), and object to processing based on legitimate interests (21). Legal professional secrecy can limit these rights where the law of a Member State provides for it (Art. 23) **[OPEN: which national law applies]**. You can complain to a supervisory authority, in particular in the EU country where you live or work (Art. 77).

## Do you have to give us the data?

The data is needed to take on and run your matter; without it we cannot act for you (Art. 13(2)(e)).

# B · People we receive data about from others (Art. 14)

## Who we are

Örnek Hukuk Bürosu, Örnek Mah. 1. Sok. No:1, Beşiktaş, İstanbul. Privacy questions: kvkk@ornekhukuk.example.

## What we do with your data, on what basis, for how long

| Purpose | Legal basis | How long |
|---|---|---|
| Take on the client, identify the matter, check conflicts of interest | GDPR Art. 6(1)(f) (legitimate interests). Interest: Taking on the client and avoiding conflicts of interest; for individual clients the contract (6(1)(b)) also applies | 10 years after the matter closes |
| Find public records (sanctions lists, insolvency and court notices, trade registry gazette) about the target company and the individuals behind it, for the client's DD report | GDPR Art. 6(1)(f) (legitimate interests). Interest: The client's interest in knowing who it is dealing with before a transaction; limited to people with a control or signing role | Until the DD report is delivered + 2 years, then only the report |
| Draft reports and opinions from the client's documents and the screening results | GDPR Art. 6(1)(f) (legitimate interests). Interest: Providing the legal service the client engaged us for, which requires reading the documents it sends; Art. 9(2)(f) (establishment, exercise or defence of legal claims) | 10 years after the matter closes |

## Who receives it

Service providers bound by contract to our instructions: Anthropic (Claude API) (Language model for drafting); Hetzner (Server for the vector store and agent logs). Other recipients: Mistral AI (Language model for intake sorting, **[OPEN: contract status]**); TOBB Türkiye Ticaret Sicili Gazetesi portal (Public gazette searched by company name, acts on its own account). Our clients receive the reports and opinions we prepare for them. Before text is sent to Anthropic (Claude API), Mistral AI, Hetzner, the names, ID numbers, contact details and addresses that our masking tool detects are replaced with placeholders on our own computer. These providers therefore receive pseudonymised text; it is still personal data for us.

## Transfers outside the EU/EEA

Anthropic (Claude API) (United States): onward (client SCCs). Ask us for a copy of the safeguards.

## Use of AI

We use AI systems to sort documents, research and draft. A lawyer reviews every result before it leaves our office; no decision about you is made by a machine alone (Art. 22).

## Your rights

You can ask for access (Art. 15), correction (16), deletion (17), restriction (18), portability where it applies (20), and object to processing based on legitimate interests (21). Legal professional secrecy can limit these rights where the law of a Member State provides for it (Art. 23) **[OPEN: which national law applies]**. You can complain to a supervisory authority, in particular in the EU country where you live or work (Art. 77).

## Which data, and from where (Art. 14(1)(d), 14(2)(f))

Categories: Names and contact details, National ID and passport numbers, Roles, shareholdings and signing powers, Financial and insolvency information (konkordato, bankruptcy notices), Sanctions, asset-freeze and court records about individuals, Health data in case files (e.g. workplace accident opinions). Sources: MASAK lists, ilan.gov.tr, Türkiye Ticaret Sicili Gazetesi, data_subject, client, documents the client sends.

## When you are told (Art. 14(3))

Within one month of receiving the data, or at first contact. **Exemption check (Art. 14(5)); the reviewer must pick one and document it:**

- 14(5)(b) informing would be impossible or need disproportionate effort, or would seriously impair the purpose (e.g. tipping off the target of a DD). Then publish this notice and take other measures.
- 14(5)(d) the data must stay confidential under professional secrecy regulated by **Union or Member State** law. A Turkish attorney's secrecy duty (Avukatlık Kanunu m.36) is not Member State law; check whether the EU client's own lawyers' secrecy covers the matter.
- Otherwise: send this notice. **[OPEN: chosen route]**

## Points for the reviewer

- **Open question: Does the GDPR reach you directly (Art. 3(2))?** If you offer services to people in the EU (individuals, not only EU companies) the GDPR applies directly to that processing and you need an EU representative (Art. 27). If not, it reaches you through your EU clients' SCCs. The answer decides documents 00, 01, 03 and 07. *(GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018)*
- **Note: 'Drafting DD reports and legal opinions' collects data not from the person: Art. 14 notice.** People whose data comes from clients or public sources must be told within one month, unless an Art. 14(5) exemption applies and is documented. Document 03, notice B. *(GDPR Art. 14(3), 14(5))*
- **Note: 'Client intake and conflict check' collects data not from the person: Art. 14 notice.** People whose data comes from clients or public sources must be told within one month, unless an Art. 14(5) exemption applies and is documented. Document 03, notice B. *(GDPR Art. 14(3), 14(5))*
- **Note: 'DD screening of target companies and their people' collects data not from the person: Art. 14 notice.** People whose data comes from clients or public sources must be told within one month, unless an Art. 14(5) exemption applies and is documented. Document 03, notice B. *(GDPR Art. 14(3), 14(5))*
- **Note: Masked text is pseudonymised, not anonymous.** Masked text is still personal data for you, because you hold the key (Art. 4(5), Recital 26). For a recipient that cannot re-identify it, the CJEU accepts it may not be personal data (C-413/23 P, EDPS v SRB, 4 Sep 2025), but your duties to inform and to secure stay the same. Describe masking as: detected values are masked and leak-checked before the text leaves the computer. *(GDPR Art. 4(5), Recital 26; CJEU C-413/23 P)*

## KVKK (Türkiye)

The Turkish aydınlatma metni is a separate file ([03-aydinlatma-metni.tr.md](03-aydinlatma-metni.tr.md)): KVKK m.10 and the Tebliğ require it at collection, separate from any request for açık rıza.
