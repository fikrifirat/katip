"""What the user can read (tool titles, the permission-prompt line, errors, notes) in one language.

MCP doesn't tell a server the user's language, so it is a setting: KATIP_LANG=tr (default, for
Turkish lawyers) or en. Claude answers in the user's language either way; this only changes the
text that Claude Desktop shows as is."""
from __future__ import annotations

import os

T = {
    "tr": {
        "leak": "Güvenlik kontrolü: {n} değer ({kinds}) maskelendikten sonra hâlâ okunabiliyordu, bu yüzden Claude'a "
                "hiçbir şey gönderilmedi. Dosyayı Katip uygulamasında açıp bu değerleri elle işaretleyin, "
                "ya da bu dosyayı bize (değerleri paylaşmadan) bildirin.",
        "not_found": "Dosya bulunamadı. Katip klasörünüze koyun (open_folder klasörü açar) ve list_files ile tekrar arayın.",
        "no_id": "Bu kimlikte dosya yok; list_files'ı tekrar çalıştırın.",
        "need_file": "file_id (list_files'tan) ya da dosya yolu gerekli.",
        "too_big": "Dosya {mb} MB'tan büyük.",
        "outside": "Dosya Katip klasörünün dışında. Katip yalnızca ayarlarda seçilen klasördeki dosyaları açar.",
        "exists": "Bu adda bir dosya zaten var; başka bir output_path seçin.",
        "no_burn": "PDF ve fotoğraflarda kalıcı karartma Katip uygulamasında yapılır; metin için mask_file kullanın.",
        "folder_note": "Müvekkil dosyalarını buraya koyun; Katip yalnızca bu klasördeki dosyaları açar.",
        "list_note": "Adlar bilerek kısaltıldı: kişi adı olabilecek sözcükler … olarak görünür. mask_file'a "
                     "file_id verin. Hangi dosyanın kastedildiği belirsizse kullanıcıya sorun. "
                     "Liste en yeni dosyayla başlar.",
        "ocr": "{n} sayfa bu bilgisayarda OCR ile okundu ({readers}); olağandışı yazımları kontrol edin.",
        "placeholders": "[AD SOYAD-1] gibi yer tutucular yalnızca kullanıcının bilgisayarında saklanan gerçek "
                        "değerlerin yerine geçer. Yanıtınızda onları aynen koruyun ki Katip yerelde geri koyabilsin.",
    },
    "en": {
        "leak": "Safety check: {n} values ({kinds}) were still readable after masking, so nothing was sent to "
                "Claude. Open the file in the Katip app and mark them by hand, or report this file to us "
                "(without the values).",
        "not_found": "File not found. Put it in your Katip folder (open_folder shows it) and look again with list_files.",
        "no_id": "No file with this id; run list_files again.",
        "need_file": "Give file_id (from list_files) or a path.",
        "too_big": "The file is larger than {mb} MB.",
        "outside": "The file is outside the Katip folder. Katip only opens files in the folder picked in its settings.",
        "exists": "A file with this name already exists; pick another output_path.",
        "no_burn": "Burn-in redaction of PDFs and photos runs in the Katip app; use mask_file for the text.",
        "folder_note": "Put client files here; Katip only opens files in this folder.",
        "list_note": "Names are shortened on purpose: words that could be a person's name show as …. Pass "
                     "file_id to mask_file. Ask the user which file they mean if it is unclear. Newest first.",
        "ocr": "{n} page(s) read with OCR on this computer ({readers}); check unusual spellings.",
        "placeholders": "Placeholders like [AD SOYAD-1] stand for real values kept only on the user's computer. "
                        "Keep them exactly as written in your answer so Katip can restore them locally.",
    },
}


TOOLS = {
    "tr": {
        "why": "Katip KVKK kapsamındaki kişisel verileri bu bilgisayarda çıkarır; Claude yalnızca yer tutucuları görür. ",
        "list_files": ("Dosyaları listele (adlar gizli)",
                       "Katip klasöründeki belgeleri kimlik, tarih ve kısaltılmış adlarla listeler: kişi adı olabilecek "
                       "her sözcük … olarak görünür. En yeni dosya başta. Başka bir dosya listeleme aracı yerine bunu kullanın."),
        "mask_file": ("Kişisel verileri maskele (bu bilgisayarda)",
                      ".docx, .udf (UYAP), .txt, .pdf (taranmış dahil) ya da fotoğrafı bu bilgisayarda açar, taramaları "
                      "yerel OCR ile okur, kişisel verileri (ad soyad, T.C. kimlik / YKN / pasaport no, adres, telefon, "
                      "IBAN, sağlık ve diğer KVKK m.6 verileri) yerelde çıkarır ve yalnızca maskeli metni döndürür. "
                      "Uzun belgeler sayfa sayfa gelir."),
        "write_masked_copy": ("Maskeli kopya kaydet",
                              ".docx, .udf ya da .txt dosyasının maskeli kopyasını aynı biçimde aslının yanına kaydeder "
                              "(ad.maskeli.uzantı). Hiçbir dosyanın üzerine yazmaz."),
        "restore_to_file": ("Gerçek adları geri koy (bu bilgisayarda)",
                            "Metindeki [AD SOYAD-1] gibi yer tutucuları bu bilgisayarda saklanan gerçek değerlerle "
                            "değiştirir ve sonucu yeni bir yerel dosyaya kaydeder. Claude'a yalnızca dosya yolu ve "
                            "sayı döner, gerçek değerler asla dönmez."),
        "forget_matter": ("Dosyanın ad eşleşmelerini sil",
                          "Bir dosyanın (matter) yerel yer tutucu eşleşmelerini kalıcı olarak siler. Sonrasında bu "
                          "yer tutucular geri konamaz."),
        "open_folder": ("Katip klasörümü aç",
                        "Müvekkil dosyalarının konduğu Katip klasörünü Finder'da ya da Gezgin'de açar, yoksa oluşturur."),
        "katip_status": ("Katip durumu",
                         "Yerel motoru, OCR'ı, eşiği, Katip klasörünü (bağlantısıyla) ve eşleşme haritasının nerede "
                         "saklandığını gösterir."),
        "prompt": ("Katip ile güvenli çalış",
                   "Katip klasöründeki belgeyi bu bilgisayarda maskeleyip isteğinizi yanıtlar.",
                   "İstek (ör. son eklediğim dilekçeyi özetle)",
                   "Katip ile çalış: önce list_files ile Katip klasöründeki dosyayı bul (istek 'son eklediğim' "
                   "diyorsa file_id \"latest\"), mask_file ile bu bilgisayarda maskele ve yalnızca maskeli metinle "
                   "çalış. Dosyayı başka bir araçla açma. Yer tutucuları aynen koru. Türkçe yanıt ver.\n\nİstek: {req}"),
        "privacy_mask": "Dosya bu bilgisayarda maskelenir; Claude yalnızca [AD SOYAD-1] gibi yer tutucuları görür (KVKK).",
        "privacy_list": "Dosya adlarındaki kişi adları gizlenir; Claude yalnızca kısaltılmış adları görür (KVKK).",
        "privacy_restore": "Gerçek adlar yalnızca bu bilgisayardaki dosyaya yazılır; Claude onları görmez (KVKK).",
    },
    "en": {
        "why": "Katip removes KVKK personal data on this computer, so Claude only sees placeholders. ",
        "list_files": ("List files (names hidden)",
                       "List the documents in the user's Katip folder with ids, dates and shortened names: any word that "
                       "could be a person's name shows as …. Newest first. Use this instead of any other file listing."),
        "mask_file": ("Mask personal data (on this computer)",
                      "Open a .docx, .udf (UYAP), .txt, .pdf (also scanned) or photo on this computer, read scans with "
                      "local OCR, remove personal data (names, T.C. kimlik / YKN / passport numbers, addresses, phones, "
                      "IBAN, health and other KVKK Article 6 data) locally, and return only the masked text. Long "
                      "documents come in pages."),
        "write_masked_copy": ("Save a masked copy",
                              "Save a masked copy of a .docx, .udf or .txt file in the same format next to the original "
                              "(name.maskeli.ext). Never overwrites a file."),
        "restore_to_file": ("Put the real names back (on this computer)",
                            "Replace placeholders like [AD SOYAD-1] in the text with the real values kept on this "
                            "computer and save the result as a new local file. Returns only the path and a count, "
                            "never the real values."),
        "forget_matter": ("Delete a matter's name map",
                          "Permanently delete a matter's local placeholder map. Its placeholders can't be restored after this."),
        "open_folder": ("Open my Katip folder",
                        "Open the Katip folder (where client files go) in Finder or Explorer, creating it if needed."),
        "katip_status": ("Katip status",
                         "Show the local engine, OCR, threshold, the Katip folder (with a link) and where the "
                         "placeholder map is kept."),
        "prompt": ("Work safely with Katip",
                   "Masks a document from your Katip folder on this computer, then answers your request.",
                   "Request (e.g. summarise the lease I just added)",
                   "Work with Katip: find the file in the Katip folder with list_files (file_id \"latest\" if the "
                   "request says 'just added'), mask it on this computer with mask_file and work only with the masked "
                   "text. Don't open the file with any other tool. Keep placeholders exactly as written. Answer in "
                   "English.\n\nRequest: {req}"),
        "privacy_mask": "The file is masked on this computer; Claude only sees placeholders like [AD SOYAD-1] (KVKK).",
        "privacy_list": "Names in file names are hidden; Claude only sees shortened names (KVKK).",
        "privacy_restore": "Real names are written only to a file on this computer; Claude never sees them (KVKK).",
    },
}


def tool(key: str) -> tuple[str, str]:
    title, desc = TOOLS[lang()][key]
    why = TOOLS[lang()]["why"] if key in ("list_files", "mask_file", "write_masked_copy") else ""
    return title, why + desc


def text(key: str) -> str:
    return TOOLS[lang()][key]


def lang() -> str:
    v = (os.environ.get("KATIP_LANG") or "tr").lower()[:2]
    return v if v in T else "tr"


def msg(key: str, **kw) -> str:
    return T[lang()][key].format(**kw)
