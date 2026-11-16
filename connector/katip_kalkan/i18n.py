"""What the user can read (tool titles, the permission-prompt line, errors, notes) in one language.

MCP doesn't tell a server the user's language, so it is a setting: KATIP_LANG=tr (default, for
Turkish lawyers) or en. Claude answers in the user's language either way; this only changes the
text that Claude Desktop shows as is."""
from __future__ import annotations

import os

T = {
    "tr": {
        "leak": "Bu belge Claude'a gönderilmedi: maskelemeden sonra {kinds} türünde {n} değer hâlâ okunabiliyordu. "
                "Belgeyi Katip uygulamasında (https://fikrifirat.github.io/katip) açıp bu değerleri elle "
                "işaretleyebilirsiniz. Belgenin aslını sohbete eklemeyin.",
        "not_found": "Dosya bulunamadı. list_files ile belge adından bir sözcükle arayın; belge dava klasöründe ya da İndirilenler'de olmalı.",
        "no_id": "Bu kimlikte dosya yok; list_files'ı tekrar çalıştırın.",
        "need_file": "file_id (list_files'tan) ya da dosya yolu gerekli.",
        "too_big": "Dosya {mb} MB'tan büyük.",
        "outside": "Belge Katip'in açabildiği klasörlerin dışında. Katip yalnızca ayarlarda seçilen dava klasöründeki ve İndirilenler'deki belgeleri açar.",
        "exists": "Bu adda bir dosya zaten var; başka bir output_path seçin.",
        "outside_write": "Katip yalnızca açabildiği klasörlere yazar; output_path olarak yalnızca bir dosya adı verin (ör. cevap-dilekcesi.docx), belgenin yanına kaydedilir.",
        "restore_ext": "Gerçek adlı metin .docx, .txt ya da .md olarak kaydedilebilir.",
        "no_burn": "PDF ve fotoğraflarda kalıcı karartma Katip uygulamasında yapılır; metin için mask_file kullanın.",
        "folder_note": "Müvekkil dosyalarını buraya koyun; Katip yalnızca bu klasördeki dosyaları açar.",
        "folder_broad": "Dava klasörü çok geniş seçilmiş (ana klasör, Masaüstü ya da Belgeler'in tamamı): "
                        "Katip oradaki her dosyayı açabilir. Ayarlardan dava dosyalarınızın bulunduğu klasörü seçin "
                        "(ör. Belgeler/Davalar).",
        "folder_cloud": "Bu klasör iCloud, OneDrive, Google Drive ya da Dropbox ile eşitleniyor gibi görünüyor: "
                        "müvekkil belgeleri ve gerçek adlı son metinler o hizmete de kopyalanır. Eşitlenmeyen bir klasör "
                        "seçmenizi öneririz (ör. kullanıcı klasörünüzde Katip).",
        "list_note": "Adlar bilerek kısaltıldı: kişi adı olabilecek sözcükler … olarak görünür. mask_file'a "
                     "file_id verin. Birden çok belge uyuyorsa kısaltılmış adları ve where'i gösterip kullanıcıya "
                     "hangisi olduğunu sorun. Liste en yeni belgeyle başlar.",
        "no_match": "Bu sözcüklerle eşleşen belge yok. Kullanıcıdan belge adından başka bir sözcük isteyin ya da "
                    "belgenin dava klasöründe veya İndirilenler'de olup olmadığını sorun.",
        "in_downloads": "İndirilenler",
        "in_cases": "Dava klasörü",
        "ocr": "{n} sayfa bu bilgisayarda OCR ile okundu ({readers}); olağandışı yazımları kontrol edin.",
        "placeholders": "[AD SOYAD-1] gibi yer tutucular yalnızca kullanıcının bilgisayarında saklanan gerçek "
                        "değerlerin yerine geçer. Yanıtınızda onları aynen koruyun ki Katip yerelde geri koyabilsin. Kullanıcıya bir kez "
                        "söyleyin: son metni gerçek adlarla bilgisayarına kaydetmenizi isteyebilir (restore_to_file).",
    },
    "en": {
        "leak": "This document was not sent to Claude: after masking, {n} values of type {kinds} were still "
                "readable. You can open it in the Katip app (https://fikrifirat.github.io/katip) and mark them by "
                "hand. Don't attach the original to the chat.",
        "not_found": "File not found. Search with list_files using a word from the document's name; it must be in the case folder or Downloads.",
        "no_id": "No file with this id; run list_files again.",
        "need_file": "Give file_id (from list_files) or a path.",
        "too_big": "The file is larger than {mb} MB.",
        "outside": "The document is outside the folders Katip may open. Katip only opens documents in the case folder and Downloads picked in its settings.",
        "exists": "A file with this name already exists; pick another output_path.",
        "outside_write": "Katip only writes into the folders it may open; give output_path as a file name only (e.g. cevap-dilekcesi.docx), it is saved next to the document.",
        "restore_ext": "The text with real names can be saved as .docx, .txt or .md.",
        "no_burn": "Burn-in redaction of PDFs and photos runs in the Katip app; use mask_file for the text.",
        "folder_note": "Put client files here; Katip only opens files in this folder.",
        "folder_broad": "The case folder is very broad (your home folder, or all of Desktop or Documents): "
                        "Katip could open any file there. In the settings, pick the folder that holds your case files "
                        "(e.g. Documents/Davalar).",
        "folder_cloud": "This folder seems to sync to iCloud, OneDrive, Google Drive or Dropbox, so client documents "
                        "and final texts with real names are copied there too. We recommend a folder that doesn't sync "
                        "(e.g. a Katip folder in your user folder).",
        "list_note": "Names are shortened on purpose: words that could be a person's name show as …. Pass "
                     "file_id to mask_file. If several documents match, show the shortened names and where, and "
                     "ask the user which one. Newest first.",
        "no_match": "No document matches these words. Ask the user for another word from the document's name, or "
                    "whether it is in their case folder or Downloads.",
        "in_downloads": "Downloads",
        "in_cases": "Case folder",
        "ocr": "{n} page(s) read with OCR on this computer ({readers}); check unusual spellings.",
        "placeholders": "Placeholders like [AD SOYAD-1] stand for real values kept only on the user's computer. "
                        "Keep them exactly as written in your answer so Katip can restore them locally. Tell the user once that "
                        "you can save the final text with the real names on their computer (restore_to_file).",
    },
}


TOOLS = {
    "tr": {
        "why": "Katip KVKK kapsamındaki kişisel verileri bu bilgisayarda çıkarır; Claude, Katip'in bulduğu değerlerin yerine yer tutucuları görür. ",
        "list_files": ("Belgeyi bul (adlar gizli)",
                       "Dava klasöründeki ve İndirilenler'deki belgeleri bulur. ara verilirse (ör. \"Yılmaz kira\", "
                       "\"bilirkişi raporu\") gerçek dosya ve klasör adlarında bu bilgisayarda arar; Claude'a yalnızca "
                       "kimlik, tarih ve kısaltılmış adlar döner, kişi adı olabilecek her sözcük … olarak görünür. "
                       "En yeni belge başta. Başka bir dosya listeleme aracı yerine bunu kullanın."),
        "mask_file": ("Belgeyi bu bilgisayarda maskeleyip aç",
                      ".docx, .udf (UYAP), .txt, .pdf (taranmış dahil) ya da fotoğrafı bu bilgisayarda açar, taramaları "
                      "yerel OCR ile okur, kişisel verileri (ad soyad, T.C. kimlik / YKN / pasaport no, adres, telefon, "
                      "IBAN, sağlık ve diğer KVKK m.6 verileri) yerelde çıkarır ve yalnızca maskeli metni döndürür. "
                      "Uzun belgeler sayfa sayfa gelir."),
        "write_masked_copy": ("Maskeli kopyasını kaydet",
                              ".docx, .udf ya da .txt dosyasının maskeli kopyasını aynı biçimde aslının yanına kaydeder "
                              "(ad.maskeli.uzantı). Hiçbir dosyanın üzerine yazmaz."),
        "restore_to_file": ("Gerçek adlarla dosyaya kaydet (bu bilgisayarda)",
                            "Metindeki [AD SOYAD-1] gibi yer tutucuları bu bilgisayarda saklanan gerçek değerlerle "
                            "değiştirir ve sonucu yeni bir yerel dosyaya kaydeder. Claude'a yalnızca dosya yolu ve "
                            "sayı döner, gerçek değerler asla dönmez."),
        "forget_matter": ("Bu dosyanın ad eşleşmelerini kalıcı sil",
                          "Bir dosyanın (matter) yerel yer tutucu eşleşmelerini kalıcı olarak siler. Sonrasında bu "
                          "yer tutucular geri konamaz."),
        "open_folder": ("Katip klasörümü aç",
                        "Katip'in varsayılan klasörünü Finder'da ya da Gezgin'de açar, yoksa oluşturur. Belgeleri buraya "
                        "taşımak gerekmez: Katip dava klasöründe ve İndirilenler'de de arar."),
        "katip_status": ("Katip durumunu göster",
                         "Yerel motoru, OCR'ı, eşiği, Katip'in aradığı klasörleri ve eşleşme haritasının nerede "
                         "saklandığını gösterir."),
        "prompt": ("Katip ile güvenli çalış",
                   "Belgeyi dava klasörünüzde ya da İndirilenler'de bulur, bu bilgisayarda maskeler ve isteğinizi yanıtlar.",
                   "İstek (ör. fesih şartlarını çıkar)",
                   "Katip ile çalış. Belgeyi bul: kullanıcı belgeyi tarif ettiyse ({doc}) list_files\'ı ara ile çağır (ör. ara=\"Yılmaz kira\"); \"son indirdiğim\" ya da \"son eklediğim\" diyorsa ya da tarif yoksa file_id \"latest\" kullan; birden çok belge uyuyorsa kısaltılmış adları gösterip sor. mask_file ile bu bilgisayarda maskele ve yalnızca maskeli metinle çalış. Dosyayı başka bir araçla açma; yer tutucuları aynen koru. Türkçe yanıt ver.\n\nİstek: {req}"),
        "prompt_review": ("Dilekçeyi incele ve özetle",
                          "Belgeyi maskeleyip özetler; talepleri, dayanakları, eksik ve hataları işaretler.",
                          "Neye odaklanayım? (ör. zamanaşımı, deliller)",
                          "Katip ile çalış. Belgeyi bul: kullanıcı belgeyi tarif ettiyse ({doc}) list_files\'ı ara ile çağır (ör. ara=\"Yılmaz kira\"); \"son indirdiğim\" ya da \"son eklediğim\" diyorsa ya da tarif yoksa file_id \"latest\" kullan; birden çok belge uyuyorsa kısaltılmış adları gösterip sor. mask_file ile bu bilgisayarda maskele ve yalnızca maskeli metinle çalış. Dosyayı başka bir araçla açma; yer tutucuları aynen koru. Belgeyi dikkatlice özetle; tarafları rolleriyle (davacı, davalı, vekil) ve "
                          "yer tutucularıyla yaz, talepleri, dayanılan delilleri ve hukuki gerekçeyi ayır, eksik ya da hatalı "
                          "gördüğün noktaları ve önerilerini madde madde yaz. Türkçe yanıt ver.\n\nÖzellikle: {req}"),
        "prompt_draft": ("Cevap taslağı hazırla",
                         "Belgeye taslak yazar; isterseniz gerçek adlarla, belgenin yanına Word dosyası olarak kaydeder.",
                         "Taslak türü ve notlar (ör. cevap dilekçesi, itiraz)",
                         "Katip ile çalış. Belgeyi bul: kullanıcı belgeyi tarif ettiyse ({doc}) list_files\'ı ara ile çağır (ör. ara=\"Yılmaz kira\"); \"son indirdiğim\" ya da \"son eklediğim\" diyorsa ya da tarif yoksa file_id \"latest\" kullan; birden çok belge uyuyorsa kısaltılmış adları gösterip sor. mask_file ile bu bilgisayarda maskele ve yalnızca maskeli metinle çalış. Dosyayı başka bir araçla açma; yer tutucuları aynen koru. Buna bir taslak yaz; bilinmeyenleri uydurma, […] ile işaretle. Sonra "
                         "kullanıcıya sor: taslağı gerçek adlarla belgenin yanına .docx olarak kaydetmemi ister misiniz "
                         "(restore_to_file)? Türkçe yanıt ver.\n\nTaslak: {req}"),
        "doc_arg": "Hangi belge? (ör. Yılmaz kira sözleşmesi, bugün indirdiğim bilirkişi raporu; boş = son belge)",
        "info_key": "bilgi",
        "doc_key": "belge",
        "doc_desc": "list_files'taki kısaltılmış ad (ör. \"… - Vatandaşlık Dava Dilekçesi.udf\"); onay kutusunda kullanıcıya gösterilir",
        "privacy_mask": "Belge bu bilgisayarda açılır ve maskelenir; Claude, Katip'in bulduğu kişisel verilerin yerine [AD SOYAD-1] gibi yer tutucuları görür. Katip bazı değerleri kaçırabilir.",
        "privacy_list": "Yalnızca dava klasöründe ve İndirilenler'de bu bilgisayarda aranır; dosya adlarındaki kişi adları gizlenir.",
        "privacy_restore": "Gerçek adlar yalnızca bu bilgisayarda, kaynak belgenin yanına yeni bir dosya olarak yazılır; Claude'a yalnızca dosya adı döner. Göndermeden önce son metni okuyun.",
    },
    "en": {
        "why": "Katip removes KVKK personal data on this computer, so Claude sees placeholders instead of the values it finds. ",
        "list_files": ("Find a document (names hidden)",
                       "Find documents in the user's case folder and Downloads. With ara (e.g. \"Yılmaz kira\", "
                       "\"bilirkişi raporu\") it searches the real file and folder names on this computer; Claude only "
                       "gets ids, dates and shortened names, with any word that could be a person's name shown as …. "
                       "Newest first. Use this instead of any other file listing."),
        "mask_file": ("Mask and open a document (on this computer)",
                      "Open a .docx, .udf (UYAP), .txt, .pdf (also scanned) or photo on this computer, read scans with "
                      "local OCR, remove personal data (names, T.C. kimlik / YKN / passport numbers, addresses, phones, "
                      "IBAN, health and other KVKK Article 6 data) locally, and return only the masked text. Long "
                      "documents come in pages."),
        "write_masked_copy": ("Save a masked copy",
                              "Save a masked copy of a .docx, .udf or .txt file in the same format next to the original "
                              "(name.maskeli.ext). Never overwrites a file."),
        "restore_to_file": ("Save with the real names (on this computer)",
                            "Replace placeholders like [AD SOYAD-1] in the text with the real values kept on this "
                            "computer and save the result as a new local file. Returns only the path and a count, "
                            "never the real values."),
        "forget_matter": ("Delete a matter's name map",
                          "Permanently delete a matter's local placeholder map. Its placeholders can't be restored after this."),
        "open_folder": ("Open my Katip folder",
                        "Open Katip's default folder in Finder or Explorer, creating it if needed. Documents don't have "
                        "to be moved there: Katip also searches the case folder and Downloads."),
        "katip_status": ("Katip status",
                         "Show the local engine, OCR, threshold, the folders Katip searches and where the placeholder "
                         "map is kept."),
        "prompt": ("Work safely with Katip",
                   "Finds the document in your case folder or Downloads, masks it on this computer, then answers your request.",
                   "Request (e.g. list the termination terms)",
                   "Work with Katip. Find the document: if the user described it ({doc}), call list_files with ara (e.g. ara=\"Yılmaz kira\"); for \"the one I just downloaded\" or no description use file_id \"latest\"; if several match, show the shortened names and ask. Mask it on this computer with mask_file and work only with the masked text. Don\'t open the file with any other tool; keep placeholders exactly as written. Answer in English.\n\nRequest: {req}"),
        "prompt_review": ("Review and summarise a petition",
                          "Masks the document, summarises it and flags claims, grounds, gaps and errors.",
                          "What to focus on (e.g. limitation, evidence)",
                          "Work with Katip. Find the document: if the user described it ({doc}), call list_files with ara (e.g. ara=\"Yılmaz kira\"); for \"the one I just downloaded\" or no description use file_id \"latest\"; if several match, show the shortened names and ask. Mask it on this computer with mask_file and work only with the masked text. Don\'t open the file with any other tool; keep placeholders exactly as written. Summarise it carefully: name the parties by role and placeholder, "
                          "separate the claims, evidence and legal grounds, and list gaps or errors with suggestions. "
                          "Answer in English.\n\nFocus: {req}"),
        "prompt_draft": ("Draft a reply",
                         "Drafts a reply to the document and can save it with the real names as a Word file next to it.",
                         "Kind of draft and notes (e.g. reply petition, objection)",
                         "Work with Katip. Find the document: if the user described it ({doc}), call list_files with ara (e.g. ara=\"Yılmaz kira\"); for \"the one I just downloaded\" or no description use file_id \"latest\"; if several match, show the shortened names and ask. Mask it on this computer with mask_file and work only with the masked text. Don\'t open the file with any other tool; keep placeholders exactly as written. Write the draft; don't invent facts, mark gaps as […]. Then ask whether "
                         "to save it with the real names as a .docx next to the document (restore_to_file). Answer in "
                         "English.\n\nDraft: {req}"),
        "doc_arg": "Which document? (e.g. the Yılmaz lease, the expert report I downloaded today; empty = newest)",
        "info_key": "privacy",
        "doc_key": "document",
        "doc_desc": "The shortened name from list_files; shown to the user in the permission prompt",
        "privacy_mask": "The document is opened and masked on this computer; Claude sees placeholders like [AD SOYAD-1] instead of the personal data Katip finds. Katip can miss a value.",
        "privacy_list": "Only the case folder and Downloads are searched, on this computer; names in file names are hidden.",
        "privacy_restore": "Real names are written only to a new file on this computer, next to the source document; Claude gets only the file name back. Read the final text before you send it.",
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
