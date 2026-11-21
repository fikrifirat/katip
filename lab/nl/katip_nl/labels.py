"""Placeholder tags and UI labels. Every label carries English next to Dutch (and Turkish), because fikri
wants to read English alongside the local language in both the Dutch and the Turkish UI."""
from __future__ import annotations

# entity: (placeholder tag, Dutch, English, Turkish)
LABELS = {
    "PERSON": ("NAAM", "Naam", "Name", "Ad soyad"),
    "BSN": ("BSN", "Burgerservicenummer (BSN)", "Citizen service number", "Vatandaşlık hizmet numarası (BSN)"),
    "IBAN": ("IBAN", "Rekeningnummer (IBAN)", "Bank account (IBAN)", "IBAN"),
    "POSTCODE": ("POSTCODE", "Postcode", "Postcode", "Posta kodu"),
    "HOUSE_NUMBER": ("HUISNR", "Huisnummer", "House number", "Kapı numarası"),
    "ADDRESS": ("ADRES", "Adres", "Address", "Adres"),
    "PHONE": ("TELEFOON", "Telefoonnummer", "Phone number", "Telefon"),
    "EMAIL": ("E-MAIL", "E-mailadres", "E-mail address", "E-posta"),
    "PLATE": ("KENTEKEN", "Kenteken", "Licence plate", "Plaka"),
    "ID_DOCUMENT": ("DOCUMENTNR", "Paspoort-, ID- of rijbewijsnummer", "Passport, ID card or driving licence no.",
                    "Pasaport / kimlik / ehliyet no"),
    "V_NUMBER": ("V-NUMMER", "Vreemdelingennummer (V-nummer)", "Immigration number (V-number)", "Yabancı numarası (V-nummer)"),
    "VAT_ID": ("BTW-ID", "Btw-identificatienummer", "VAT id", "KDV numarası"),
    "KVK": ("KVK", "KvK-nummer", "Chamber of Commerce no.", "Ticaret sicil no (KvK)"),
    "RSIN": ("RSIN", "RSIN / fiscaal nummer", "RSIN / tax number", "RSIN / vergi no"),
    "BIRTH_DATE": ("GEBOORTEDATUM", "Geboortedatum", "Date of birth", "Doğum tarihi"),
}

UI = {
    "masked": ("Gemaskeerd", "Masked", "Maskelendi"),
    "kept": ("Leesbaar gelaten", "Left readable", "Okunur bırakıldı"),
    "review": ("Ter controle (niet gemaskeerd)", "For review (not masked)", "Kontrol için (maskelenmedi)"),
    "article_found": ("Artikel gevonden", "Article found", "Madde bulundu"),
    "article_missing": ("Artikel bestaat niet in deze wet", "Article does not exist in this act", "Bu kanunda böyle bir madde yok"),
    "act_unknown": ("Onbekende wet", "Unknown act", "Bilinmeyen kanun"),
    "ecli_found": ("Uitspraak gevonden", "Decision found", "Karar bulundu"),
    "ecli_missing": ("ECLI niet gevonden", "ECLI not found", "ECLI bulunamadı"),
}


def tag(entity: str) -> str:
    return LABELS.get(entity, (entity,))[0]


def label(entity: str, lang: str = "nl") -> str:
    """'nl' -> 'Naam / Name', 'tr' -> 'Ad soyad / Name', 'en' -> 'Name'."""
    t = LABELS.get(entity)
    if not t:
        return entity
    nl, en, tr = t[1], t[2], t[3]
    return {"nl": f"{nl} / {en}", "tr": f"{tr} / {en}", "en": en}.get(lang, f"{nl} / {en}")


def ui(key: str, lang: str = "nl") -> str:
    nl, en, tr = UI[key]
    return {"nl": f"{nl} / {en}", "tr": f"{tr} / {en}", "en": en}.get(lang, f"{nl} / {en}")
