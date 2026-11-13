import Tesseract from "./vendor/tesseract.js/dist/tesseract.esm.min.js";
import CONFIG from "./config.js";
const $ = id => document.getElementById(id);
const el = (tag, props = {}, ...kids) => { const e = Object.assign(document.createElement(tag), props); e.append(...kids.filter(k => k != null)); return e; };
const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
// A module worker drops messages that arrive while its imports are still loading, so queue until it says "alive".
let workerAlive = false; const outbox = [];
const send = (msg, transfer = []) => workerAlive ? worker.postMessage(msg, transfer) : outbox.push([msg, transfer]);
const DEV = new URLSearchParams(location.search).has("dev");

// ---------------------------------------------------------------- UI copy (documents stay Turkish; the interface is TR/EN)
const I18N = {
  tr: {
    tagline: "Türkçe KVKK maskeleme, tamamen tarayıcınızda. Belge hiçbir sunucuya yüklenmez.",
    netLbl: "Belge açıldıktan sonra ağ isteği", netTip: "Belgeniz bu sekmede açılır, taranır ve maskelenir; hiçbir sunucuya yüklenmez.||Sayfanın güvenlik politikası (CSP) başka bir adrese veri gönderilmesini engeller ve hiçbir şey kaydedilmez: sekmeyi kapatınca belge silinir. Belge açıldıktan sonraki ağ isteği sayacı Gelişmiş ayarlarda görünür ve 0 kalmalıdır.",
    cspLbl: "Dışarı gönderim", blocked: "engelli", cspTip: "Bu sayfa belgenizi başka bir yere gönderemez.||Sayfanın güvenlik politikası (CSP), tarayıcının başka bir adrese veri göndermesini engeller.",
    storeLbl: "Kayıt", none: "yok", storeTip: "Hiçbir şey kaydedilmez; sekmeyi kapatınca belge silinir.||Belge yalnızca bu sekmenin belleğinde tutulur.",
    docH: "Belge", sampleTab: "Örnek belge", fileTab: "Kendi belgem",
    sampleHint: "Sentetik belgeler, cevap anahtarıyla puanlanır.",
    sampleTip: "Örneklerdeki kişiler uydurmadır. Doğru cevaplar bilindiği için kaçanları da görürsünüz.||Bulunan, kaçan ve fazladan işaretlenen değerler cevap anahtarına göre canlı sayılır.",
    dropH: "Belgeyi buraya bırakın veya seçin", fileHint: "Dosya yalnızca bu sekmenin belleğinde kalır.",
    fileTip: "Dosyanız bilgisayarınızdan çıkmaz.||Açma, tarama, maskeleme ve kontrol bu sekmede yapılır; sekmeyi kapatınca silinir.",
    detectH: "Algılama", ocrH: "OCR (tarama ve fotoğraf)",
    ocrTip: "Taranmış belge ve fotoğrafları okuyan model. Önerilen yeterlidir.||Türkçe Tesseract modeli. 96 taranmış örnekte ikisi neredeyse aynı değerleri buldu; önerilen 4 kat küçüktür çünkü yalnızca yeni (LSTM) okuyucuyu içerir.",
    thrH: "Güven eşiği", thrTip: "Düşük: daha çok yakalar, daha çok yanlış alarm. Yüksek: tersi. 0,70 önerilir.||T.C. kimlik, VKN, IBAN gibi sağlama kontrollü numaralar her zaman yakalanır.",
    typesH: "Veri türleri", maskH: "Maske", colorH: "Maske rengi", styleH: "Word ve metinde",
    styleTip: "Değerin yerine ne konacağı: kutu, ████ veya [AD SOYAD-1] gibi etiket.||PDF ve görüntülerde seçilen renkte kutu çizilir. Word, UDF ve metinde değer ██████ veya etiketle değiştirilir.",
    styleBox: "██████ blok", styleLabel: "[AD SOYAD-1] etiket",
    unreadItem: "Sayfa {p} · alan {i}", addrH: "Adresler", addrStreet: "Sokak görünür, bina/daire gizli", addrFull: "Adresin tamamı gizli",
    addrTip: "Mahalle, cadde/sokak, ilçe ve il kişisel veri değildir; bina adı, blok, kapı ve daire numarası kişiyi gösterir.||Varsayılan: Alparslan Türkeş Cad. gibi sokak adları görünür kalır, yalnızca bina, blok, kat, kapı ve daire maskelenir. Sokak adları hiçbir zaman kişi adı sayılmaz. Tüm adresi gizlemek için \"Adresin tamamı gizli\"yi seçin.",
    tipMore: "Ayrıntılar",
    markH: "Ortaya Katip logosu", markTip: "Her sayfanın ortasına soluk bir Katip logosu basar.||PDF ve görüntülerde. Kapalıyken alttaki tek satırlık filigran yine eklenir.",
    wmH: "Filigran ekle", wmTip: "Çıktının altına küçük bir \"Katip Mask ile maskelendi\" satırı ekler.||Tam metin: \"{wm}\". PDF'te bağlantılıdır. UYAP .udf dosyalarına eklenmez.",
    viewReview: "Orijinal", viewResult: "Maskeli", apply: "Maskeleri uygula", reapply: "Yeniden uygula", download: "Maskeli belgeyi indir", report: "Hata bildir",
    copy: "Etiketli metni kopyala", forget: "Belgeyi unut",
    empty: "Soldan bir örnek seçin veya kendi belgenizi açın.",
    termPh: "Kaçan bir şey mi var? Buraya yazın", add: "Ekle",
    findTip: "İşaretini kaldırdığınız değer maskelenmez.||Belgedeki işarete tıklamak da aç/kapa yapar. ⚑ o değeri hata bildirimine ekler.",
    found: "{n} kişisel veri karartıldı", missedH: "Kaçanlar", addMissed: "Maskeye ekle", flag: "Hata bildirimine ekle", warnOnly: "uyarı",
    details: "Ayrıntılar",
    sRecall: "bulundu", sFp: "fazla", sLeak: "çıktıda okunabilir", sNotApplied: "Değişiklikler henüz uygulanmadı",
    sPreview: "Henüz maskelenmedi: işaretleri kontrol edin, sonra Maskeleri uygula'ya basın.",
    leakBad: "Dikkat: {n} değer çıktıda hâlâ okunabiliyor. Bu dosyayı göndermeyin.", leakUnchecked: "Taranmış sayfalar tekrar okunmadı; indirmeden önce gözle kontrol edin.",
    leakOk: "Kontrol edildi: karartılan değerlerin hiçbiri çıktıda okunamıyor.",
    loading: "Katip hazırlanıyor… (ilk açılışta birkaç saniye)", ready: "Katip hazır.", preparing: "Hazırlanıyor…", done: "{n} kişisel veri karartıldı.", copied: "Etiketli metin kopyalandı.", forgotten: "Belge bellekten silindi.",
    waiting: "Katip hazırlanıyor; hazır olunca belge kendiliğinden taranır.", toScan: "Önizleme hazır. Kişisel verileri bul'a basın.", listHint: "Kişisel verileri bul'a basınca bulunan değerler burada türlerine göre listelenir; her birini açıp kapatabilirsiniz.", scan: "Kişisel verileri bul", rescan: "Yeniden tara",
    error: "Hata: ", page: "Sayfa", ok: "doğru", fpL: "fazla", missL: "kaçan",
    tType: "Tür", tGold: "Doğru cevap", tFound: "Bulunan", tMissed: "Kaçan", tFp: "Fazla", partial: "kısmen: yalnız \"{p}\"",
    goldNote: "Doğru cevaplar belgeyi üreten betikten gelir. Taranmış belgelerde OCR hataları da puanı etkiler.",
    kModel: "Model", kOcr: "OCR modeli", kPages: "Sayfa", kParse: "Okuma ve OCR", kRules: "Kurallar", kRedact: "Maskeleme ve kontrol", kVersion: "Motor sürümü", unused: "kullanılmadı",
    rWhatWrong: "Konu", rMissed: "Bir şey açık kaldı", rFp: "Gereksiz karartıldı", rBroken: "Dosya açılmıyor", rOther: "Diğer",
    rWhere: "Hangi değer veya yer? (isteğe bağlı)", rDesc: "Mesajınız", rDescPh: "Ne işe yaradı, ne eksik, neyi farklı yapardınız?", rInclude: "Rapora eklenecekler",
    rIncSettings: "Ayarlar, sürüm, süreler, puanlar", rIncMasked: "Maskeli çıktı", rIncDet: "Bulunan değerler", rIncOrig: "Orijinal belge",
    rPersonal: "(kişisel veri içerir)", rPersonalOk: "(kişisel veri içerir; yalnızca izniniz varsa)", cancel: "Vazgeç", rSend: "Doğrudan gönder", rMail: "E-postayla gönder",
    rHowMail: "E-posta uygulamanız {to} adresine hazır bir mesajla açılır. Belgeyle ilgili bir sorunsa küçük bir rapor (.zip) da indirilir; onu ekleyin. Kişisel veri içeren hiçbir şey siz seçmeden eklenmez.",
    rHowSend: "\"Doğrudan gönder\" raporu {host} üzerinden iletir. Ya da raporu indirip e-postayla kendiniz gönderin.",
    rDownloaded: "{f} indirildi. E-posta açılmadıysa {to} adresine dosyayı ekleyerek yazın.", rSending: "Gönderiliyor…", rSent: "Gönderildi, teşekkürler.", rFailed: "Gönderilemedi",
    foot: "Açık kaynak · tamamen cihazınızda çalışır", source: "Kaynak kod", issues: "Soru ve öneriler",
    onSpace: "Bu sayfa için çok büyük (110 MB) · Hugging Face'te deneyin →",
    ocrBest: "Küçük", ocrBestMeta: "Aynı doğruluk, 4 kat küçük · 2 MB", ocrFast: "Standart", ocrFastMeta: "Eski motor verisiyle · 7,7 MB",
    origAlt: "Orijinal sayfa", maskAlt: "Maskeli sayfa", ocrText: "Okunan metin",
    trust: "Cihazınızda çalışır · belgeniz bilgisayarınızdan çıkmaz", feedback: "Görüş bildir", feedbackH: "Görüşünüz bizim için çok değerli", hero: "Belgedeki kişisel verileri saniyeler içinde maskeleyin.", lead: "Ad, T.C. kimlik, adres, telefon, IBAN, sağlık bilgisi… Katip bulur ve karartır; siz kontrol edip indirirsiniz.", dropFormats: "PDF · fotoğraf · Word · UYAP .udf · metin", tryH: "Elinizde belge yok mu? Örnekle deneyin:", allSamples: "Tüm örnekler", openSample: "Aç", step1: "Belgeyi bırakın", step2: "Karartılanları kontrol edin", step3: "Maskeli halini indirin", newDoc: "← Yeni belge", listHint2: "Tik kaldırdığınız değer açık kalır. Belgedeki işarete tıklamak da aynı işi görür.", advH: "Gelişmiş ayarlar", modelH: "Algılama modeli", scanning: "Kişisel veriler aranıyor…", applying: "Karartılıyor…", sampleNote: "Örnek belge (kişiler uydurma). Cevap anahtarı:", leakFix: "Bunları da karart", qKira: "Kira sözleşmesi · fotoğraf", qDilekce: "Dava dilekçesi · UYAP .udf", qBilirkisi: "Bilirkişi raporu · tarama", qIs: "İş sözleşmesi · Word", rGeneral: "Genel görüş", rHowGeneral: "E-posta uygulamanız {to} adresine hazır bir mesajla açılır. Siz göndermeden hiçbir şey çıkmaz.",
    profH: "Ne için maskeliyorsunuz?", pCourt: "Mahkemeye sunum", pAi: "Yapay zekâ ile paylaşım", pAnon: "Tam anonim", pCustom: "Özel seçim", pCourtHint: "Kişisel verilerin tamamı karartılır; sokak, dosya numarası ve tarihler okunur kalır. Delil ve dilekçe ekleri için.", pAiHint: "Buna ek olarak adresin tamamı, esas/karar ve UYAP numaraları, baro sicil numaraları ve sabıka bilgisi karartılır.", pAnonHint: "Buna ek olarak tarihler, il ve ilçeler, mahkeme, şirket ve kurum adları da karartılır. Metin okunur, kim olduğu çıkmaz.", pCustomHint: "Veri türlerini kendiniz seçtiniz.", pickTypes: "Türleri tek tek seç", baCap: "Örnek dava dilekçesi (kişiler uydurma). Çizgiyi kaydırın.", baOpen: "Bu örneği aç →", sampleN: "örnek", baMadeUp: "kişiler uydurma", pickType: "Örnek belge türü", pickVariant: "Örnek numarası", baOrigAlt: "Örnek dilekçe, orijinal", baMaskAlt: "Aynı dilekçe, Katip ile maskelenmiş", baAria: "Orijinal ile maskeli arasında kaydır",
  },
  en: {
    tagline: "Turkish KVKK redaction that runs entirely in your browser. Nothing is uploaded.",
    netLbl: "Network requests after opening the document", netTip: "Your document is opened, scanned and masked in this tab; it is never uploaded.||The page's Content-Security-Policy blocks sending data anywhere else, and nothing is stored: closing the tab deletes it. The counter of requests after opening a document is under Advanced settings and should stay 0.",
    cspLbl: "Sending out", blocked: "blocked", cspTip: "This page cannot send your document anywhere.||The page's Content-Security-Policy makes the browser block any request to another address.",
    storeLbl: "Stored", none: "nothing", storeTip: "Nothing is saved; closing the tab deletes the document.||The document lives only in this tab's memory.",
    docH: "Document", sampleTab: "Sample", fileTab: "My file",
    sampleHint: "Synthetic documents, scored against an answer key.",
    sampleTip: "The people in the samples are made up. The right answers are known, so you also see what was missed.||Found, missed and extra values are counted live against the answer key.",
    dropH: "Drop a document here or choose one", fileHint: "The file stays in this tab's memory only.",
    fileTip: "Your file never leaves your computer.||Opening, scanning, masking and checking all happen in this tab; closing the tab deletes it.",
    detectH: "Detection", ocrH: "OCR (scans and photos)",
    ocrTip: "The model that reads scans and photos. The recommended one is enough.||Turkish Tesseract model. On 96 scanned samples both found almost the same values; the recommended one is 4× smaller because it holds only the newer (LSTM) reader.",
    thrH: "Confidence threshold", thrTip: "Lower catches more but raises more false alarms. Higher does the opposite. 0.70 is recommended.||Numbers with a checksum (T.C. kimlik, VKN, IBAN) are always caught.",
    typesH: "Data types", maskH: "Mask", colorH: "Mask colour", styleH: "In Word and text",
    styleTip: "What replaces each value: a box, ████ or a label such as [AD SOYAD-1].||PDFs and images get a box in the chosen colour. In Word, UDF and text the value is replaced with ██████ or a label.",
    styleBox: "██████ block", styleLabel: "[AD SOYAD-1] label",
    unreadItem: "Page {p} · area {i}", addrH: "Addresses", addrStreet: "Street visible, building/flat hidden", addrFull: "Whole address hidden",
    addrTip: "Neighbourhood, street, district and province are not personal data; building name, block, door and flat number point to a person.||Default: street names such as Alparslan Türkeş Cad. stay readable and only the building, block, floor, door and flat are masked. Street names are never treated as people's names. Pick \"Whole address hidden\" to mask all of it.",
    tipMore: "Details",
    markH: "Katip logo in the centre", markTip: "Stamps a faint Katip logo across the middle of each page.||PDFs and images only. Off, the one-line watermark at the bottom is still added.",
    wmH: "Add watermark", wmTip: "Adds a small \"Redacted with Katip Mask\" line at the bottom.||Full text: \"{wm}\". Linked in PDFs. Not added to UYAP .udf files.",
    viewReview: "Original", viewResult: "Masked", apply: "Apply masks", reapply: "Apply again", download: "Download masked file", report: "Report a mistake",
    copy: "Copy labelled text", forget: "Forget document",
    empty: "Pick a sample on the left or open your own file.",
    termPh: "Something missed? Type it here", add: "Add",
    findTip: "Untick a value and it will not be masked.||Clicking a highlight in the document toggles it too. ⚑ adds the value to a mistake report.",
    found: "{n} personal data items masked", missedH: "Missed", addMissed: "Add to masks", flag: "Add to mistake report", warnOnly: "flag",
    details: "Details",
    sRecall: "found", sFp: "extra", sLeak: "readable in output", sNotApplied: "Changes not applied yet",
    sPreview: "Nothing is masked yet: check the highlights, then press Apply masks.",
    leakBad: "Warning: {n} values are still readable in the output. Do not send this file.", leakUnchecked: "Scanned pages were not re-read; check by eye before downloading.",
    leakOk: "Checked: none of the masked values can be read in the output.",
    loading: "Getting Katip ready… (a few seconds the first time)", ready: "Katip is ready.", preparing: "Preparing…", done: "{n} personal data items masked.", copied: "Labelled text copied.", forgotten: "Document removed from memory.",
    waiting: "Getting Katip ready; the document is scanned as soon as it is.", toScan: "Preview ready. Press Find personal data.", listHint: "After Find personal data, the values found are listed here by type; you can switch each one on or off.", scan: "Find personal data", rescan: "Scan again",
    error: "Error: ", page: "Page", ok: "correct", fpL: "extra", missL: "missed",
    tType: "Type", tGold: "Answer key", tFound: "Found", tMissed: "Missed", tFp: "Extra", partial: "partly: only \"{p}\"",
    goldNote: "The answer key comes from the script that generated the document. On scans, OCR errors also affect the score.",
    kModel: "Model", kOcr: "OCR model", kPages: "Pages", kParse: "Reading and OCR", kRules: "Rules", kRedact: "Masking and check", kVersion: "Engine version", unused: "not used",
    rWhatWrong: "Topic", rMissed: "Something was left visible", rFp: "Masked by mistake", rBroken: "File won't open", rOther: "Other",
    rWhere: "Which value or place? (optional)", rDesc: "Your message", rDescPh: "What helped, what is missing, what would you do differently?", rInclude: "Include in the report",
    rIncSettings: "Settings, version, timings, scores", rIncMasked: "Masked output", rIncDet: "Detected values", rIncOrig: "Original document",
    rPersonal: "(contains personal data)", rPersonalOk: "(contains personal data; only with permission)", cancel: "Cancel", rSend: "Send directly", rMail: "Send by e-mail",
    rHowMail: "Your e-mail app opens a ready message to {to}. For a problem with a document a small report (.zip) is also downloaded; attach it. Nothing with personal data is added unless you tick it.",
    rHowSend: "\"Send directly\" delivers the report through {host}. Or download it and e-mail it yourself.",
    rDownloaded: "{f} downloaded. If no e-mail opened, write to {to} and attach the file.", rSending: "Sending…", rSent: "Sent, thank you.", rFailed: "Could not send",
    foot: "Open source · runs entirely on your device", source: "Source code", issues: "Questions and ideas",
    onSpace: "Too big for this page (110 MB) · try it on Hugging Face →",
    ocrBest: "Compact", ocrBestMeta: "Same accuracy, 4× smaller · 2 MB", ocrFast: "Standard", ocrFastMeta: "Includes old engine data · 7.7 MB",
    origAlt: "Original page", maskAlt: "Masked page", ocrText: "Recognised text",
    trust: "Runs on your device · your file never leaves it", feedback: "Send feedback", feedbackH: "We'd love your feedback", hero: "Mask personal data in legal documents in seconds.", lead: "Names, ID numbers, addresses, phones, IBANs, health details… Katip finds and blacks them out; you check and download.", dropFormats: "PDF · photo · Word · UYAP .udf · text", tryH: "No document at hand? Try a sample:", allSamples: "All samples", openSample: "Open", step1: "Drop the document", step2: "Check what's masked", step3: "Download the masked copy", newDoc: "← New document", listHint2: "Untick a value to leave it visible. Clicking a highlight in the document does the same.", advH: "Advanced settings", modelH: "Detection model", scanning: "Looking for personal data…", applying: "Masking…", sampleNote: "Sample document (made-up people). Answer key:", leakFix: "Mask these too", qKira: "Lease · photo", qDilekce: "Petition · UYAP .udf", qBilirkisi: "Expert report · scan", qIs: "Employment contract · Word", rGeneral: "General feedback", rHowGeneral: "Your e-mail app opens a ready message to {to}. Nothing leaves until you send it.",
    profH: "What are you masking it for?", pCourt: "Court filing", pAi: "Sharing with AI", pAnon: "Fully anonymous", pCustom: "Custom", pCourtHint: "All personal data is masked; streets, case numbers and dates stay readable. For evidence and petition attachments.", pAiHint: "On top of that, the whole address, case and UYAP numbers, bar registry numbers and criminal records are masked.", pAnonHint: "On top of that, dates, provinces and districts, and court, company and institution names are masked too. The text reads, the people can't be traced.", pCustomHint: "You picked the data types yourself.", pickTypes: "Pick types one by one", baCap: "Sample petition (made-up people). Drag the line.", baOpen: "Open this sample →", sampleN: "sample", baMadeUp: "made-up people", pickType: "Sample document type", pickVariant: "Sample number", baOrigAlt: "Sample petition, original", baMaskAlt: "The same petition masked by Katip", baAria: "Slide between original and masked",
  },
};
const LABELS = {
  tr: { TCKN: "T.C. Kimlik No", VKN: "Vergi Kimlik No", IBAN: "IBAN", CREDIT_CARD: "Kredi kartı", PHONE: "Telefon", EMAIL: "E-posta", PLATE: "Araç plakası",
    PERSON: "Ad soyad", ADDRESS: "Adres", BIRTH_DATE: "Doğum tarihi", IP_ADDRESS: "IP adresi", YKN: "Yabancı kimlik no", PASSPORT: "Pasaport no", FOREIGN_ID: "Yabancı ülke kimlik no", HEALTH: "Sağlık", RELIGION: "Din/inanç", POLITICAL: "Siyasi görüş",
    UNION: "Sendika", ETHNICITY: "Etnik köken", SEXUAL_LIFE: "Cinsel hayat", BIOMETRIC_GENETIC: "Biyometrik/genetik", CRIMINAL_RECORD: "Ceza mahkumiyeti", UNREAD: "El yazısı alanı",
    CASE_NO: "Esas/karar/UYAP no", BAR_NO: "Baro/sicil no", DATE: "Tarih", PLACE: "İl/ilçe", INSTITUTION: "Mahkeme/kurum/şirket", CUSTOM: "Eklenen terim" },
  en: { TCKN: "Turkish ID no.", VKN: "Tax ID", IBAN: "IBAN", CREDIT_CARD: "Card number", PHONE: "Phone", EMAIL: "E-mail", PLATE: "Licence plate",
    PERSON: "Name", ADDRESS: "Address", BIRTH_DATE: "Birth date", IP_ADDRESS: "IP address", YKN: "Foreigner ID no.", PASSPORT: "Passport no.", FOREIGN_ID: "Foreign national ID", HEALTH: "Health", RELIGION: "Religion/belief", POLITICAL: "Political opinion",
    UNION: "Trade union", ETHNICITY: "Ethnic origin", SEXUAL_LIFE: "Sex life", BIOMETRIC_GENETIC: "Biometric/genetic", CRIMINAL_RECORD: "Criminal record", UNREAD: "Handwritten area",
    CASE_NO: "Case/UYAP no.", BAR_NO: "Bar/registry no.", DATE: "Date", PLACE: "Province/district", INSTITUTION: "Court/institution/company", CUSTOM: "Added term" },
};
const FORMATS = { tr: { txt: "Metin", docx: "Word", udf: "UYAP .udf", pdf: "PDF", "scan.pdf": "Taranmış PDF", png: "Fotoğraf" },
                  en: { txt: "Text", docx: "Word", udf: "UYAP .udf", pdf: "PDF", "scan.pdf": "Scanned PDF", png: "Photo" } };
const SAMPLE_EN = { aydinlatma: "Privacy notice", bilirkisi: "Expert report", dilekce: "Petition", epikriz: "Hospital discharge summary", eposta: "E-mail thread",
  fatura: "Invoice", icra: "Enforcement request", ihtarname: "Formal notice", is_sozlesmesi: "Employment contract", karar: "Court judgment", kira_sozlesmesi: "Lease",
  mektup: "Letter", mesaj: "Chat log", tutanak: "Minutes", vekaletname: "Power of attorney", zabit: "Hearing record" };
const PROGRESS_EN = [[/^NER modeli yükleniyor/, "Loading name model"], [/^NER çalışıyor/, "Running name model"], [/^OCR sayfa (\d+)\/(\d+)/, "OCR page $1/$2"], [/^Sayfa (\d+)\/(\d+)/, "Page $1/$2"],
  [/^OCR$/, "OCR"], [/^Kişisel veriler aranıyor/, "Looking for personal data"], [/^Maskeleniyor/, "Masking"], [/tekrar okunuyor/, "Re-reading output (leak check)"]];
const ART6 = ["HEALTH", "RELIGION", "POLITICAL", "UNION", "ETHNICITY", "SEXUAL_LIFE", "BIOMETRIC_GENETIC", "CRIMINAL_RECORD"];
// Masking profiles: one click sets the data types and the address rule; the checkboxes stay for fine control.
// A ladder: each profile masks everything the one before it does, plus more.
const CASE = ["CASE_NO", "BAR_NO"], ANON = ["DATE", "PLACE", "INSTITUTION"];
const PERSONAL = () => Object.keys(LABELS.tr).filter(k => k !== "CUSTOM" && !CASE.includes(k) && !ANON.includes(k));
const PROFILES = {
  court: { name: "pCourt", hint: "pCourtHint", addr: "street", types: () => PERSONAL().filter(k => k !== "CRIMINAL_RECORD") },
  ai: { name: "pAi", hint: "pAiHint", addr: "full", types: () => [...PERSONAL(), ...CASE] },
  anon: { name: "pAnon", hint: "pAnonHint", addr: "full", types: () => [...PERSONAL(), ...CASE, ...ANON] },
};
let profile = "court";
const COLORS = [["#000000", "Siyah / Black"], ["#3a3a3a", "Grafit / Graphite"], ["#1f3a5f", "Lacivert / Navy"], ["#1f5f4a", "Yeşil / Green"], ["#7a1f1f", "Bordo / Maroon"], ["#ffffff", "Beyaz / White"]];

let lang = (() => {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "tr" || q === "en") return q;
  try { const s = localStorage.getItem("katip-lang"); if (s === "tr" || s === "en") return s; } catch { /* storage blocked */ }
  return (navigator.language || "tr").toLowerCase().startsWith("tr") ? "tr" : "en";
})();
const t = (k, vars = {}) => (I18N[lang][k] ?? I18N.tr[k] ?? k).replace(/\{(\w+)\}/g, (_, v) => vars[v] ?? "");
const L = k => LABELS[lang][k] ?? k;
const loc = v => (v && typeof v === "object" ? v[lang] ?? v.tr : v) ?? "";
const wmText = () => CONFIG.watermark ? loc(CONFIG.watermark.text) : "";

let ready = false, samples = [], models = [], version = {};
let src = { mode: "sample", sample: null, format: "pdf", file: null };
let res = null; window.__katip = () => res;  // for automated tests
let off = new Set(), maskTerms = [], outBlob = null, outName = "", view = "review", applied = false, busy = false, maskColor = "#000000", seq = 0;
let preview = null;  // { seq, kind, text, pages: [url], imageUrl }
let loaded = null;   // { name, bytes, gold, isSample }

// ---------------------------------------------------------------- network watch
let docOpenedAt = Infinity, netCount = 0;
const runtimeFile = u => /\/(vendor|models|samples|hero)\/|katip_py\.zip|\.(m?js|css|wasm|json)(\?|$)/.test(u);
new PerformanceObserver(list => {
  for (const e of list.getEntries()) if (e.startTime >= docOpenedAt && !runtimeFile(e.name)) netCount++;
  $("netCount").textContent = netCount; $("netPill").classList.toggle("bad", netCount > 0);
}).observe({ type: "resource", buffered: true });

// ---------------------------------------------------------------- OCR (tesseract.js runs its own worker)
const tess = {};
function getTess(model) {
  return tess[model] ??= Tesseract.createWorker("tur", 1, {
    workerPath: new URL("./vendor/tesseract.js/dist/worker.min.js", location.href).href,
    corePath: new URL("./vendor/tesseract.js-core/", location.href).href,
    langPath: new URL(`./vendor/tessdata/${model}`, location.href).href,
    gzip: true, cacheMethod: "none", workerBlobURL: false,
  });
}
async function ocr(png, model) {
  const { data } = await (await getTess(model)).recognize(new Blob([png]), {}, { blocks: true });
  const lines = [];
  for (const b of data.blocks ?? []) for (const p of b.paragraphs) for (const l of p.lines)
    lines.push(l.words.filter(w => w.text.trim() && w.confidence >= 0).map(w => ({ text: w.text, bbox: [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1] })));
  return lines.filter(l => l.length);
}

// ---------------------------------------------------------------- language
// ---------------------------------------------------------------- explanations: tap "?" (or a pill) for one plain
// sentence; "Details" expands the technical part. Text format: "short||details".
const pop = document.createElement("div"); pop.id = "tipPop"; pop.setAttribute("role", "dialog"); pop.hidden = true; document.body.append(pop);
let popFor = null;
function closeTip() { pop.hidden = true; popFor?.setAttribute("aria-expanded", "false"); popFor = null; }
function openTip(host) {
  if (popFor === host) return closeTip();
  closeTip();
  const [short, more] = (host.dataset.tip || "").split("||");
  pop.textContent = "";
  pop.append(el("p", { textContent: short }));
  if (more) {
    const d = el("details", {}, el("summary", { textContent: t("tipMore") }), el("p", { textContent: more }));
    d.ontoggle = () => place(host);
    pop.append(d);
  }
  pop.hidden = false; popFor = host; host.setAttribute("aria-expanded", "true"); place(host);
}
function place(host) {
  const r = host.getBoundingClientRect(), w = Math.min(300, innerWidth - 24);
  pop.style.width = w + "px";
  pop.style.left = Math.max(12, Math.min(r.left + r.width / 2 - w / 2, innerWidth - w - 12)) + "px";
  const h = pop.offsetHeight, below = r.bottom + 8;
  pop.style.top = (below + h < innerHeight - 8 || r.top - h - 8 < 8 ? below : r.top - h - 8) + "px";
}
document.addEventListener("click", e => {
  const host = e.target.closest("[data-tip]");
  if (host) { e.preventDefault(); e.stopPropagation(); return openTip(host); }
  if (!e.target.closest("#tipPop")) closeTip();
}, true);
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeTip();
  if ((e.key === "Enter" || e.key === " ") && e.target.matches?.("[data-tip]")) { e.preventDefault(); openTip(e.target); }
});
addEventListener("scroll", () => popFor && place(popFor), true); addEventListener("resize", closeTip);

function applyLang() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(e => (e.textContent = t(e.dataset.i18n)));
  document.querySelectorAll("[data-i18n-ph]").forEach(e => (e.placeholder = t(e.dataset.i18nPh)));
  document.querySelectorAll("[data-i18n-alt]").forEach(e => (e.alt = t(e.dataset.i18nAlt)));
  document.querySelectorAll("[data-i18n-aria]").forEach(e => e.setAttribute("aria-label", t(e.dataset.i18nAria)));
  document.querySelectorAll("[data-i18n-tip]").forEach(e => { const s = t(e.dataset.i18nTip, { wm: wmText() }); e.dataset.tip = s; e.setAttribute("aria-label", s.split("||")[0]); e.setAttribute("role", "button"); });
  document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  document.title = lang === "tr" ? "Katip Mask: belgedeki kişisel verileri maskeleyin" : "Katip Mask: mask personal data in documents";
  if (samples.length) { drawPicker(); buildModelUI(); buildEntityUI(); buildProfileUI(); }
  updateButtons(); if (res?.spans) render(); else if (preview) renderPreview();
}
document.querySelectorAll("[data-lang]").forEach(b => (b.onclick = () => {
  lang = b.dataset.lang; try { localStorage.setItem("katip-lang", lang); } catch { /* ignore */ }
  const u = new URL(location.href); u.searchParams.set("lang", lang); history.replaceState(null, "", u);
  applyLang();
}));

// ---------------------------------------------------------------- settings
const selModel = () => document.querySelector("#models input:checked")?.value ?? models.find(m => !m.dev && !m.disabled && !m.elsewhere)?.id;
const selOcr = () => document.querySelector("#ocrModels input:checked")?.value ?? "best_int";
function settings() {
  const m = models.find(x => x.id === selModel()) ?? models[0];
  return {
    engine: m?.id, engineName: loc(m?.name), ner: m?.ner ?? null, baseline: m?.baseline ?? null, nerDtype: m?.dtype ?? "q8", trust: m?.trust ?? null, ocrLang: selOcr(),
    threshold: Number($("threshold").value), style: $("style").value, addressDetail: $("addrDetail").value,
    entities: [...document.querySelectorAll("#entities input:checked")].map(i => i.value), mask: maskTerms,
  };
}
function optCard(group, value, title, meta, tip, checked, badge, disabled = false) {
  const tipEl = el("span", { className: "tip", tabIndex: 0, textContent: "?" }); tipEl.dataset.tip = tip; tipEl.setAttribute("aria-label", tip.split("||")[0]); tipEl.setAttribute("role", "button");
  return el("label", { className: "opt" + (disabled ? " dis" : "") }, el("input", { type: "radio", name: group, value, checked: checked && !disabled, disabled }),
    el("span", { className: "opt-t" }, el("b", { textContent: title }), badge ? el("em", { textContent: badge }) : null, tipEl),
    el("span", { className: "opt-m", textContent: meta }));
}
function buildModelUI() {
  const cur = selModel(), curOcr = selOcr();
  $("models").textContent = "";
  for (const m of models.filter(m => !m.dev || DEV)) {
    const card = optCard("model", m.id, loc(m.name), loc(m.meta), loc(m.info), m.id === cur, m.badge ? loc(m.badge) : null, !!(m.disabled || m.elsewhere));
    if (m.elsewhere) card.append(el("a", { className: "opt-l", href: m.hosted + (lang === "en" ? "?lang=en" : ""), target: "_blank", rel: "noopener", textContent: t("onSpace") }));
    $("models").append(card);
  }
  $("ocrModels").textContent = "";
  $("ocrModels").append(optCard("ocr", "best_int", t("ocrBest"), t("ocrBestMeta"), t("ocrTip"), curOcr === "best_int", lang === "tr" ? "önerilen" : "recommended"),
                        optCard("ocr", "fast", t("ocrFast"), t("ocrFastMeta"), t("ocrTip"), curOcr === "fast"));
}
$("models").onchange = () => res?.spans && redetect();
$("ocrModels").onchange = () => res?.spans && (res.kind === "image" || res.ocrPages) && analyze();
function buildEntityUI() {
  const prev = document.querySelectorAll("#entities input"), on = new Set([...prev].filter(i => i.checked).map(i => i.value));
  $("entities").textContent = "";
  for (const k of Object.keys(LABELS.tr)) {
    if (k === "CUSTOM") continue;
    const cb = el("input", { type: "checkbox", value: k, checked: prev.length ? on.has(k) : PROFILES.court.types().includes(k) });
    $("entities").append(el("label", {}, cb, " " + L(k) + (ART6.includes(k) ? " ·6" : "")));
  }
  entCount();
}
$("entities").onchange = () => { entCount(); syncProfile(); res?.spans && redetect(); };
function buildProfileUI() {
  $("profiles").textContent = "";
  for (const [id, p] of Object.entries(PROFILES)) {
    const b = el("button", { type: "button", textContent: t(p.name) }); b.dataset.p = id; b.setAttribute("role", "radio");
    b.onclick = () => setProfile(id); $("profiles").append(b);
  }
  syncProfile();
}
function setProfile(id) {
  const p = PROFILES[id], types = new Set(p.types());
  document.querySelectorAll("#entities input").forEach(i => (i.checked = types.has(i.value)));
  $("addrDetail").value = p.addr; entCount(); syncProfile();
  if (res?.spans) redetect();
}
function syncProfile() {
  const on = new Set([...document.querySelectorAll("#entities input:checked")].map(i => i.value));
  profile = Object.keys(PROFILES).find(id => { const ty = PROFILES[id].types(); return PROFILES[id].addr === $("addrDetail").value && ty.length === on.size && ty.every(k => on.has(k)); }) ?? "custom";
  document.querySelectorAll("#profiles button").forEach(b => b.setAttribute("aria-checked", b.dataset.p === profile));
  const h = $("profHint"); h.textContent = (profile === "custom" ? t("pCustomHint") : t(PROFILES[profile].hint)) + " ";
  const pick = el("button", { type: "button", className: "linkbtn", textContent: t("pickTypes") });
  pick.onclick = () => { $("adv").open = true; document.querySelector("#adv details.ents").open = true; document.querySelector("#adv details.ents").scrollIntoView({ block: "center", behavior: "smooth" }); };
  h.append(pick);
}
function entCount() { $("entCount").textContent = `(${document.querySelectorAll("#entities input:checked").length}/${Object.keys(LABELS.tr).length - 1})`; }
function buildColorUI() {
  for (const [hex, name] of COLORS) {
    const b = el("button", { type: "button", className: "sw", title: name, ariaLabel: name });
    b.style.setProperty("--c", hex); b.setAttribute("role", "radio"); b.dataset.c = hex; b.onclick = () => setColor(hex); $("colors").append(b);
  }
  const custom = el("input", { type: "color", value: "#5b3f8c", title: "Özel / Custom", ariaLabel: "Özel renk / Custom colour", className: "swc" });
  custom.oninput = () => setColor(custom.value);
  $("colors").append(custom); setColor(maskColor);
}
function setColor(hex) {
  maskColor = hex;
  document.documentElement.style.setProperty("--mask", hex);
  document.querySelectorAll("#colors .sw").forEach(b => b.setAttribute("aria-checked", b.dataset.c === hex));
  maskOptionsChanged();
}
const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
$("threshold").oninput = () => ($("thresholdVal").textContent = Number($("threshold").value).toFixed(2));
$("threshold").onchange = () => res?.spans && redetect();
$("style").onchange = () => maskOptionsChanged();
$("addrDetail").onchange = () => { syncProfile(); res?.spans && redetect(); };
$("watermark").onchange = () => maskOptionsChanged();
$("centerMark").onchange = () => maskOptionsChanged();
function maskOptionsChanged() { if (res?.spans && applied && !busy) redactNow(); }

// ---------------------------------------------------------------- sources
// ---- home: sample picker next to the before/after preview. Picking a type, variant or format runs the real pipeline
// in the background (same worker, nothing leaves the tab) and swaps the slider; "Bu örneği aç" then opens it instantly.
const sampleTitle = sm => lang === "en" ? SAMPLE_EN[sm.type] ?? sm.title : sm.title;
const types = () => [...new Map(samples.map(x => [x.type, x])).values()];
function buildSampleOptions() {
  $("sampleType").textContent = "";
  for (const sm of types()) $("sampleType").append(el("option", { value: sm.type, textContent: sampleTitle(sm) }));
  if (src.sample) $("sampleType").value = src.sample.type;
}
function drawVariants() {
  const v = $("variantBtns"); v.textContent = "";
  for (const sm of samples.filter(x => x.type === src.sample.type)) {
    const b = el("button", { type: "button", textContent: String(sm.n ?? sm.id.split("_").pop()), title: `${t("sampleN")} ${sm.n}` });
    b.dataset.id = sm.id; b.setAttribute("aria-pressed", sm.id === src.sample.id);
    b.onclick = () => { if (sm.id === src.sample.id) return; src.sample = sm; drawPicker(); previewSample(); };
    v.append(b);
  }
}
function drawFormats() {
  const f = $("formatBtns"); f.textContent = "";
  if (!src.sample.formats.includes(src.format)) src.format = src.sample.formats.includes("pdf") ? "pdf" : src.sample.formats[0];
  for (const fmt of src.sample.formats) {
    const b = el("button", { type: "button", textContent: FORMATS[lang][fmt] ?? fmt });
    b.dataset.fmt = fmt; b.setAttribute("aria-pressed", fmt === src.format);
    b.onclick = () => { if (src.format === fmt) return; src.format = fmt; drawFormats(); previewSample(); };
    f.append(b);
  }
}
function drawPicker() { buildSampleOptions(); drawVariants(); drawFormats(); baCaption(); }
function baCaption() { $("baCap").textContent = `${sampleTitle(src.sample)} · ${t("sampleN")} ${src.sample.n} · ${FORMATS[lang][src.format] ?? src.format} — ${t("baMadeUp")}`; }
const sameAsLoaded = () => loaded?.isSample && loaded.name === `${src.sample.id}.${src.format}`;
function previewSample() { baCaption(); src.mode = "sample"; loadSource({ stay: true }); }
function openSample(sm, fmt) {
  src.mode = "sample"; src.sample = sm; src.format = fmt; drawPicker();
  if (sameAsLoaded() && res) { showWork(true); render(); updateButtons(); status(busy ? $("status").textContent : ""); } else loadSource();
}
function buildSampleUI() {
  src.sample = samples.find(x => x.id === "dilekce_01") ?? samples[0]; src.format = "png";  // matches the static hero images
  $("sampleType").onchange = () => {
    const keep = src.sample.n;
    src.sample = samples.find(x => x.type === $("sampleType").value && x.n === keep) ?? samples.find(x => x.type === $("sampleType").value);
    drawPicker(); previewSample();
  };
  $("openSample").onclick = () => openSample(src.sample, src.format);
  drawPicker();
}
// the masked/original pair for the home slider, from whatever the pipeline produced
function drawBA() {
  if (!res?.spans || !applied) return;
  const O = $("baFrame").querySelector(".ba-o"), M = $("baFrame").querySelector(".ba-m");
  O.textContent = ""; M.textContent = "";
  if (res.kind === "pdf" && res.origPreviews?.[0] && res.maskPreviews?.[0]) {
    O.append(el("img", { src: res.origPreviews[0], alt: t("baOrigAlt") })); M.append(el("img", { src: res.maskPreviews[0], alt: t("baMaskAlt") }));
  } else if (res.kind === "image") {
    O.append(el("img", { src: res.imageUrl, alt: t("baOrigAlt") })); M.append(el("img", { src: res.maskUrl, alt: t("baMaskAlt") }));
  } else {  // Word, UDF, text: the same text twice, the masked layer with the chosen values blacked out
    const tx = res.text.slice(0, 2200), on = chosen().filter(x => x.end <= tx.length).sort((a, b) => a.start - b.start);
    const plain = el("div", { className: "ba-txt", textContent: tx }), masked = el("div", { className: "ba-txt" });
    let pos = 0;
    for (const x of on) { if (x.start < pos) continue; masked.append(tx.slice(pos, x.start), el("span", { className: "bm", textContent: tx.slice(x.start, x.end) })); pos = x.end; }
    masked.append(tx.slice(pos)); O.append(plain); M.append(masked);
  }
  $("baFrame").classList.remove("loading");
}
function pickFile(f) { if (!f) return; src.file = f; src.mode = "file"; loadSource(); }
$("drop").onclick = () => $("file").click();
$("drop").onkeydown = e => (e.key === "Enter" || e.key === " ") && $("file").click();
$("file").onchange = e => { pickFile(e.target.files[0]); e.target.value = ""; };
// the whole page accepts a dropped file, not only the box
addEventListener("dragover", e => { e.preventDefault(); $("drop").classList.add("over"); });
addEventListener("dragleave", e => { if (!e.relatedTarget) $("drop").classList.remove("over"); });
addEventListener("drop", e => { e.preventDefault(); $("drop").classList.remove("over"); if (!$("reportDlg").open) pickFile(e.dataTransfer.files[0]); });

// before/after slider on the home screen
$("baRange").oninput = () => $("ba").style.setProperty("--pos", $("baRange").value + "%");
function showWork(on) { $("home").classList.toggle("hidden", on); $("work").classList.toggle("hidden", !on); if (!on) window.scrollTo(0, 0); }

// Selecting a document shows it at once; analysis starts as soon as the engine is ready.
let stayHome = false;
async function loadSource({ stay = false } = {}) {
  stayHome = stay; if (stay) $("baFrame").classList.add("loading");
  const my = ++seq, isSample = src.mode === "sample";
  let name, bytes, gold = null;
  status(t("preparing"));
  try {
    if (isSample) {
      name = `${src.sample.id}.${src.format}`;
      const r = await fetch(`samples/${name}`);
      if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
      bytes = new Uint8Array(await r.arrayBuffer()); gold = src.sample.gold;
    } else { name = src.file.name; bytes = new Uint8Array(await src.file.arrayBuffer()); }
  } catch (e) { if (my === seq) status(t("error") + (e?.message ?? e)); console.error(e); return; }
  if (my !== seq) return;
  loaded = { name, bytes, gold, isSample };
  if (!stay) showWork(true);
  $("docName").textContent = isSample ? `${sampleTitle(src.sample)} ${src.sample.n} · ${FORMATS[lang][src.format] ?? src.format}` : name;
  res = null; applied = false; view = "review"; outBlob = null; busy = false;
  preview = { seq: my, kind: /\.(png|jpe?g|tiff?|bmp|webp)$/i.test(name) ? "image" : null, text: null, pages: [], imageUrl: null };
  if (preview.kind === "image") preview.imageUrl = URL.createObjectURL(new Blob([bytes]));
  renderPreview();
  if (preview.kind !== "image") send({ type: "preview", name, bytes: bytes.slice(), seq: my });
  updateButtons();
  if (ready) analyze(); else status(t("waiting"));
}

// ---------------------------------------------------------------- run
const status = m => { $("status").textContent = m; $("engineState").textContent = loaded && !stayHome ? "" : m; };
const progressText = m => { if (lang === "tr") return m; for (const [re, en] of PROGRESS_EN) if (re.test(m)) return m.replace(re, en); return m; };
function analyze() {
  if (!loaded) return;
  const s = settings(), { name, gold, isSample } = loaded, bytes = loaded.bytes.slice();
  status(t("scanning"));
  docOpenedAt = performance.now(); netCount = 0; $("netCount").textContent = "0"; $("netPill").classList.remove("bad");
  res = { name, isSample, gold, settings: s, imageUrl: preview?.imageUrl ?? null, maskUrl: null, seq };
  off = new Set(); applied = false; view = "review"; busy = true; updateButtons();
  worker.postMessage({ type: "analyze", name, bytes, settings: s, seq }, [bytes.buffer]);
}
function redetect() { if (!res?.spans || busy) return; res.settings = settings(); busy = true; updateButtons(); worker.postMessage({ type: "redetect", settings: res.settings }); }
function redactNow() {
  clearTimeout(reapplyTimer); busy = true; updateButtons(); status(t("applying"));
  worker.postMessage({ type: "redact", spans: chosen(), style: $("style").value, verifyOcr: true, ocrLang: res.settings.ocrLang, color: rgb(maskColor),
                       watermark: $("watermark").checked && CONFIG.watermark ? { text: wmText(), url: CONFIG.watermark.url } : null,
                       mark: $("centerMark").checked });
}
let reapplyTimer = 0, dlAfter = false;
const scheduleReapply = () => { clearTimeout(reapplyTimer); reapplyTimer = setTimeout(() => res?.spans && (busy ? scheduleReapply() : redactNow()), 500); };
$("scan").onclick = () => ready && loaded && !busy && analyze();
$("addTerm").onclick = () => addTerm($("term").value);
$("term").onkeydown = e => e.key === "Enter" && $("addTerm").click();
function addTerm(v) { v = (v ?? "").trim(); if (!v || !res?.spans) return; maskTerms.push(v); $("term").value = ""; redetect(); }
document.querySelectorAll("#viewSeg [data-view]").forEach(b => (b.onclick = () => {
  if (b.disabled) return; view = b.dataset.view;
  if (view === "result" && dirty() && !busy) redactNow(); render();
}));

function updateButtons() {
  const has = !!res?.spans;
  $("scan").disabled = !ready || !loaded || busy;
  $("download").disabled = !has || busy;
  document.querySelector('#viewSeg [data-view="result"]').disabled = !applied;
  document.querySelectorAll("#viewSeg [data-view]").forEach(b => b.setAttribute("aria-selected", b.dataset.view === view));
  $("work").classList.toggle("busy", busy);
}

worker.onmessage = async ({ data: m }) => {
  if (m.type === "alive") { workerAlive = true; for (const [msg, tr] of outbox.splice(0)) worker.postMessage(msg, tr); return; }
  if (m.type === "ready") {
    ready = true; getTess("best_int"); updateButtons();
    if (loaded && !res) analyze(); else status(t("ready"));
  } else if (m.type === "progress") status(progressText(m.msg) + "…");
  else if (m.type === "preview") {
    if (!preview || m.seq !== preview.seq) return;
    preview.kind = m.kind; preview.text = m.text; preview.pages = m.previews.map(p => URL.createObjectURL(new Blob([p], { type: "image/png" })));
    if (!res?.spans) renderPreview();
  } else if (m.type === "ocr") {
    try { worker.postMessage({ type: "ocrResult", id: m.id, lines: await ocr(m.png, m.lang) }); }
    catch (e) { worker.postMessage({ type: "ocrResult", id: m.id, error: String(e) }); }
  } else if (m.type === "analyzed") {
    if (!res || m.seq !== res.seq || m.seq !== seq) return;
    Object.assign(res, { kind: m.kind, text: m.text, spans: m.spans, pages: m.pages, pageSizes: m.pageSizes, ocrPages: m.ocrPages, timing: m.timing, nerCount: m.nerCount,
      origPreviews: m.previews.map(p => URL.createObjectURL(new Blob([p], { type: "image/png" }))) });
    off = new Set(m.spans.filter(s => !res.settings.entities.includes(s.entity_type)).map(key));
    busy = false; render(); redactNow();  // show the masked result straight away; the list lets them undo any item
  } else if (m.type === "redetected") {
    if (!res?.spans) return;
    const wasOff = new Set([...off].filter(k => res.spans.some(s => key(s) === k && !s.flag_only)));
    res.spans = m.spans; Object.assign(res.timing, m.timing); res.nerCount = m.nerCount;
    off = new Set(m.spans.filter(s => wasOff.has(key(s))).map(key));
    busy = false; if (applied) redactNow(); else { status(t("found", { n: chosen().length }) + "."); render(); }
  } else if (m.type === "redacted") {
    if (!res?.spans) return;
    outBlob = new Blob([m.out], { type: m.mime }); outName = m.outName;
    Object.assign(res, { outText: m.outText, leaks: m.leaks, unchecked: m.unchecked, redactMs: m.ms,
      maskPreviews: m.previews.map(p => URL.createObjectURL(new Blob([p], { type: "image/png" }))), appliedKeys: new Set(chosen().map(key)) });
    if (res.kind === "image") res.maskUrl = URL.createObjectURL(outBlob);
    busy = false; applied = true; if (!dirty()) view = "result";
    status(""); render(); if (!$("home").classList.contains("hidden")) drawBA();
    if (dlAfter && !dirty()) { dlAfter = false; saveOut(); } else if (dirty()) scheduleReapply();
  } else if (m.type === "maskedText") { await navigator.clipboard.writeText(m.text); status(t("copied")); }
  else if (m.type === "original") { pendingOriginal?.(m); }
  else if (m.type === "forgotten") {
    res = null; outBlob = null; loaded = null; preview = null; applied = false; busy = false; seq++;
    $("scorebar").classList.add("hidden"); showWork(false);
    updateButtons(); status(ready ? t("ready") : t("loading"));
  } else if (m.type === "error") { busy = false; updateButtons(); status(t("error") + m.msg); console.error(m.msg, m.stack); }
};
worker.onerror = e => { status(t("error") + (e.message || "worker")); console.error(e); };

// ---------------------------------------------------------------- scoring against gold (sample documents)
const sq = s => s.replace(/\s+/g, "").toLocaleLowerCase("tr");
const exactMatches = (a, b) => { const x = sq(a), y = sq(b); return x.includes(y) || (y.includes(x) && x.length >= Math.max(3, y.length * 0.5)); };
// For scans and photos the answer key is compared with what OCR read, so allow a few misread characters
// (© for @, 4 for +): a value counts as found when it is within 15% edits of the key.
function editDist(a, b) {
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) { const cur = [i]; for (let j = 1; j <= b.length; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)); prev = cur; }
  return prev[b.length];
}
const ocrMatches = (a, b) => { if (exactMatches(a, b)) return true; const x = sq(a), y = sq(b); return y.length >= 5 && editDist(x, y) <= Math.max(1, Math.floor(y.length * 0.15)); };
function goldEval(spans, gold, ocr = false, streetVisible = false) {
  // image areas and the case-detail types of the stricter profiles are outside the answer key
  spans = spans.filter(s => s.entity_type !== "UNREAD" && !CASE.includes(s.entity_type) && !ANON.includes(s.entity_type));
  const matches = ocr ? ocrMatches : exactMatches;
  const g = gold.filter(x => x.entity_type !== "CRIMINAL_RECORD");
  // With "street visible" (the default) only the building/door part of an address is masked by design,
  // so an address counts as found when a masked address span sits inside it.
  const found = g.map(x => spans.some(s => matches(s.text, x.text) || (streetVisible && x.entity_type === "ADDRESS" && s.entity_type === "ADDRESS" && sq(s.text).length >= 2 && sq(x.text).includes(sq(s.text)))));
  const partial = g.map((x, i) => found[i] ? null : spans.find(s => sq(s.text).length >= 2 && sq(x.text).includes(sq(s.text)))?.text ?? null);
  const fps = spans.filter(s => !g.some(x => matches(s.text, x.text) || matches(x.text, s.text) || (streetVisible && s.entity_type === "ADDRESS" && x.entity_type === "ADDRESS" && sq(x.text).includes(sq(s.text)))));
  const per = {};
  g.forEach((x, i) => { const p = per[x.entity_type] ??= { gold: 0, found: 0, fp: 0 }; p.gold++; if (found[i]) p.found++; });
  for (const s of fps) (per[s.entity_type] ??= { gold: 0, found: 0, fp: 0 }).fp++;
  return { gold: g, found, partial, fps, per, recall: found.filter(Boolean).length / Math.max(1, g.length),
           precision: (spans.length - fps.length) / Math.max(1, spans.length) };
}

// ---------------------------------------------------------------- rendering
const key = s => s.uid ?? `${s.entity_type}:${s.start}:${s.end}`;
const chosen = () => (res?.spans ?? []).filter(s => !off.has(key(s)));
const dirty = () => !!(applied && res?.appliedKeys && (res.appliedKeys.size !== chosen().length || chosen().some(s => !res.appliedKeys.has(key(s)))));
function toggle(s) { off.has(key(s)) ? off.delete(key(s)) : off.add(key(s)); render(); if (view === "result") scheduleReapply(); }

function renderPreview() {
  // before analysis: the document as it is, no highlights yet
  $("scorebar").classList.add("hidden");
  const D = $("docView"); D.textContent = ""; D.className = "docview";
  if (preview.kind === "image" && preview.imageUrl) D.append(el("div", { className: "pg" }, el("img", { src: preview.imageUrl, alt: t("origAlt") })));
  else if (preview.pages.length) for (const u of preview.pages) D.append(el("div", { className: "pg" }, el("img", { src: u, alt: t("origAlt") })));
  else if (preview.text != null) D.append(el("div", { className: "txt", textContent: preview.text.replace(/\f/g, "\n") }));
  else D.append(el("div", { className: "skel" }));
  $("list").textContent = ""; $("fCount").textContent = "";
  document.querySelector(".fhead").classList.add("hidden");
  $("list").append(el("div", { className: "skel sm" }));
}

function render() {
  if (!res?.spans) { if (preview) renderPreview(); updateButtons(); return; }
  if (!applied && view === "result") view = "review";

  res.eval = res.gold ? goldEval(chosen(), res.gold, res.kind === "image" || res.ocrPages > 0, res.settings.addressDetail === "street") : null;
  updateButtons(); renderScore(); renderDoc(); renderList(); renderGold(); renderTiming();
}

function renderScore() {
  const S = $("scorebar"); S.textContent = "";
  const ev = res.eval, items = [];
  if (applied && !busy) {
    const n = res.leaks.length, cls = n ? "bad-t" : res.unchecked ? "warn-t" : "ok-t";
    items.push(el("span", { className: "msg " + cls }, el("b", { textContent: n ? "⚠ " : res.unchecked ? "! " : "✓ " }), n ? t("leakBad", { n }) : res.unchecked ? t("leakUnchecked") : t("leakOk")));
    if (n) {  // the same value appears again somewhere it was not caught: one click masks every occurrence
      const fix = el("button", { type: "button", className: "primary sm", textContent: t("leakFix") });
      fix.onclick = () => { for (const id of res.leaks) { const sp = res.spans.find(x => x.id === id || x.uid === id); if (sp?.text && !maskTerms.includes(sp.text)) maskTerms.push(sp.text); } redetect(); };
      items.push(fix);
    }
  }
  if (dirty()) items.push(el("span", { className: "msg warn-t", textContent: t("sNotApplied") }));
  if (ev) items.push(el("span", { className: "msg sample" }, t("sampleNote") + " ",
    el("b", { textContent: `${ev.found.filter(Boolean).length}/${ev.gold.length}` }), " " + t("sRecall") + " · ",
    el("b", { className: ev.fps.length ? "warn-t" : "", textContent: String(ev.fps.length) }), " " + t("sFp")));
  S.append(...items); S.classList.toggle("hidden", !items.length);
}

function spanClass(sp) {
  const k = key(sp);
  if (off.has(k)) return "off";
  return res.eval && res.eval.fps.some(f => key(f) === k) ? "on fp" : "on";
}
function boxEl(sp, b, [w, h]) {
  const [x0, y0, x1, y1] = b, pad = 1;
  const d = el("button", { type: "button", className: "bx " + spanClass(sp), title: `${L(sp.entity_type)} · ${sp.text}`, ariaLabel: `${L(sp.entity_type)}: ${sp.text}` });
  d.style.cssText = `left:${((x0 - pad) / w) * 100}%;top:${((y0 - pad) / h) * 100}%;width:${((x1 - x0 + 2 * pad) / w) * 100}%;height:${((y1 - y0 + 2 * pad) / h) * 100}%`;
  d.onclick = () => toggle(sp); d.dataset.k = key(sp);
  return d;
}
function renderDoc() {
  const D = $("docView"), top = D.scrollTop; D.textContent = ""; D.className = "docview" + (view === "result" ? " result" : "");
  if (view === "result") {
    if (res.kind === "pdf") res.maskPreviews.forEach(u => D.append(el("div", { className: "pg" }, el("img", { src: u, alt: t("maskAlt") }))));
    else if (res.kind === "image") D.append(el("div", { className: "pg" }, el("img", { src: res.maskUrl, alt: t("maskAlt") })));
    else D.append(el("div", { className: "txt", textContent: res.outText }));
  } else if (res.kind === "pdf" || res.kind === "image") {
    const pages = res.kind === "pdf" ? res.origPreviews : [res.imageUrl];
    pages.forEach((u, i) => {
      const pg = el("div", { className: "pg" }), img = el("img", { src: u, alt: t("origAlt") });
      pg.append(img); D.append(pg);
      const place = size => { for (const sp of res.spans) if (sp.page === i) for (const b of sp.boxes ?? []) pg.append(boxEl(sp, b, size)); };
      if (res.kind === "pdf") place(res.pageSizes[i]);
      else if (img.complete && img.naturalWidth) place([img.naturalWidth, img.naturalHeight]);
      else img.addEventListener("load", () => place([img.naturalWidth, img.naturalHeight]), { once: true });
    });
    D.append(el("details", { className: "ocrtxt" }, el("summary", { textContent: t("ocrText") }), textWithMarks()));
  } else D.append(textWithMarks());
  D.scrollTop = top;
}

function textWithMarks() {
  const box = el("div", { className: "txt" });
  const tx = res.text, ev = res.eval, miss = [];
  if (ev) ev.gold.forEach((g, i) => { if (!ev.found[i]) { const j = tx.toLocaleLowerCase("tr").indexOf(g.text.toLocaleLowerCase("tr")); if (j >= 0) miss.push({ start: j, end: j + g.text.length, miss: true, g }); } });
  const items = [...res.spans.filter(s => s.end > s.start), ...miss].sort((a, b) => a.start - b.start);
  let pos = 0;
  for (const s of items) {
    if (s.start < pos) continue;
    box.append(tx.slice(pos, s.start).replace(/\f/g, "\n— — —\n"));
    if (s.miss) box.append(el("span", { className: "miss", title: `${t("missL")}: ${L(s.g.entity_type)}`, textContent: tx.slice(s.start, s.end) }));
    else {
      const mk = el("mark", { textContent: tx.slice(s.start, s.end), title: `${L(s.entity_type)} · ${s.recognizer} · ${s.score}`, className: spanClass(s) });
      mk.dataset.k = key(s); mk.onclick = () => toggle(s); box.append(mk);
    }
    pos = s.end;
  }
  box.append(tx.slice(pos).replace(/\f/g, "\n— — —\n"));
  return box;
}

function renderList() {
  const box = $("list"), top = box.scrollTop; box.textContent = "";
  $("fCount").textContent = t("found", { n: chosen().length });
  document.querySelector(".fhead").classList.remove("hidden");
  const groups = new Map();
  for (const s of res.spans) groups.set(s.entity_type, [...(groups.get(s.entity_type) ?? []), s]);
  for (const [type, spans] of groups) {
    const on = spans.filter(s => !off.has(key(s))).length;
    const all = el("input", { type: "checkbox", checked: on === spans.length, indeterminate: on > 0 && on < spans.length, ariaLabel: L(type) });
    all.onchange = () => { for (const s of spans) all.checked ? off.delete(key(s)) : off.add(key(s)); render(); };
    // the same value found several times is one row (×n); its tick covers every occurrence
    const same = new Map();
    spans.forEach((s, k) => { const id = s.text ? sq(s.text) : `#${k}`; same.set(id, [...(same.get(id) ?? []), [s, k]]); });
    const rows = [...same.values()].map(occ => {
      const [s, k] = occ[0], all = occ.map(([x]) => x), isOn = all.some(x => !off.has(key(x)));
      const cb = el("input", { type: "checkbox", checked: isOn, ariaLabel: s.text });
      cb.onchange = () => { for (const x of all) cb.checked ? off.delete(key(x)) : off.add(key(x)); render(); if (view === "result") scheduleReapply(); };
      const fp = res.eval && all.some(x => res.eval.fps.some(f => key(f) === key(x)));
      const flag = el("button", { type: "button", className: "flag", textContent: "⚑", title: t("flag"), ariaLabel: t("flag") });
      flag.onclick = e => { e.preventDefault(); openReport(isOn ? "false_positive" : "missed", s.text); };
      const v = el("span", { className: "v" + (fp ? " fp-t" : ""), textContent: s.text ? s.text.replace(/\s+/g, " ") : t("unreadItem", { p: s.page + 1, i: k + 1 }), title: `${s.recognizer} · ${s.score.toFixed(2)}${s.flag_only ? " · " + t("warnOnly") : ""}` });
      v.onclick = e => { e.preventDefault(); document.querySelector(`#docView [data-k="${CSS.escape(key(s))}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" }); };
      return el("div", { className: "it" }, cb, v, occ.length > 1 ? el("span", { className: "times", textContent: `×${occ.length}` }) : null, flag);
    });
    box.append(el("div", { className: "grp" }, el("label", { className: "gh" }, all, el("b", { textContent: L(type) }), el("span", { textContent: `${on}/${spans.length}` })), ...rows));
  }
  const ev = res.eval;
  if (ev) {
    const missed = ev.gold.map((x, i) => ({ ...x, part: ev.partial[i] })).filter((_, i) => !ev.found[i]);
    if (missed.length) box.append(el("div", { className: "grp miss-g" }, el("div", { className: "gh" }, el("b", { textContent: `${t("missedH")} (${missed.length})` })),
      ...missed.map(x => { const b = el("button", { type: "button", className: "add", textContent: "+", title: t("addMissed"), ariaLabel: t("addMissed") }); b.onclick = () => addTerm(x.text);
        return el("div", { className: "it" }, el("span", { className: "v miss", textContent: x.text, title: L(x.entity_type) + (x.part ? " · " + t("partial", { p: x.part }) : "") }), b); })));
  }
  box.scrollTop = top;
}

function renderGold() {
  const g = $("gold"); g.textContent = ""; const ev = res.eval; if (!ev) return;
  const tb = el("tbody");
  for (const [k, p] of Object.entries(ev.per).sort()) tb.append(el("tr", {}, el("td", { textContent: L(k) }), el("td", { className: "num", textContent: p.gold }),
    el("td", { className: "num", textContent: p.found }), el("td", { className: "num " + (p.gold - p.found ? "bad-t" : ""), textContent: p.gold - p.found }), el("td", { className: "num " + (p.fp ? "warn-t" : ""), textContent: p.fp })));
  g.append(el("table", { className: "tbl" }, el("thead", {}, el("tr", {}, ...["tType", "tGold", "tFound", "tMissed", "tFp"].map((h, i) => el("th", { className: i ? "num" : "", textContent: t(h) })))), tb),
    el("p", { className: "hint", textContent: t("goldNote") }));
}
function renderTiming() {
  const tm = res.timing ?? {}, rows = [[t("kModel"), res.settings.engineName], [t("kOcr"), res.ocrPages ? (res.settings.ocrLang === "fast" ? t("ocrFast") : t("ocrBest")) : t("unused")],
    [t("kPages"), `${res.pages}${res.ocrPages ? ` (${res.ocrPages} OCR)` : ""}`], [t("kParse"), `${tm.parse} ms`], ...(res.settings.ner ? [["NER", `${tm.ner} ms · ${res.nerCount}`]] : []),
    [t("kRules"), `${tm.rules} ms`], ...(applied ? [[t("kRedact"), `${res.redactMs} ms`]] : []), [t("kVersion"), version.rules ?? ""]];
  $("timing").textContent = ""; for (const [a, b] of rows) $("timing").append(el("tr", {}, el("td", { textContent: a }), el("td", { textContent: b })));
}
function saveOut() { if (!outBlob) return; const a = el("a", { href: URL.createObjectURL(outBlob), download: outName }); a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 30000); }
// one button: if the ticks changed since the last masking, mask again first, then save
$("download").onclick = () => { if (!res?.spans || busy) return; if (!applied || dirty()) { dlAfter = true; redactNow(); } else saveOut(); };
$("copy").onclick = () => { res?.spans && worker.postMessage({ type: "maskedText", spans: chosen() }); };
$("clear").onclick = () => {
  res = null; outBlob = null; loaded = null; preview = null; applied = false; busy = false; seq++; maskTerms = []; dlAfter = false;
  stayHome = false; $("baFrame").classList.remove("loading");
  send({ type: "forget" }); $("scorebar").classList.add("hidden"); $("adv").open = false; showWork(false); updateButtons(); status(ready ? t("ready") : t("loading"));
};

// ---------------------------------------------------------------- report a mistake
let pendingOriginal = null;
function openReport(kind = "general", what = "") {
  const has = !!res?.spans;
  document.querySelectorAll("#reportForm .docOnly").forEach(e => e.classList.toggle("hidden", !has));
  if (!has) { kind = "general"; $("rStatus").textContent = ""; $("rHow").textContent = t("rHowGeneral", { to: CONFIG.reportEmail }); $("rSend").classList.add("hidden"); return $("reportDlg").showModal(); }
  document.querySelector(`#reportForm input[name=kind][value=${kind}]`).checked = true;
  $("rWhat").value = what; $("rStatus").textContent = "";
  $("incMasked").checked = applied; $("incMasked").disabled = !applied;
  $("incDetections").checked = res.isSample; $("incOriginal").checked = res.isSample;
  $("detWarn").classList.toggle("hidden", res.isSample); $("origWarn").classList.toggle("hidden", res.isSample);
  $("rSend").classList.toggle("hidden", !CONFIG.reportEndpoint);
  $("rHow").textContent = CONFIG.reportEndpoint ? t("rHowSend", { host: new URL(CONFIG.reportEndpoint).host }) : t("rHowMail", { to: CONFIG.reportEmail });
  $("reportDlg").showModal();
  document.querySelector(`#reportForm input[name=kind][value=${kind}]`).dispatchEvent(new Event("change", { bubbles: true }));
}
$("reportBtn").onclick = () => openReport();
$("reportForm").onchange = e => {
  if (e.target.name !== "kind" || !res?.spans) return;
  const general = e.target.value === "general";
  for (const id of ["rWhat"]) { $(id).classList.toggle("hidden", general); document.querySelector(`label[for=${id}]`).classList.toggle("hidden", general); }
  document.querySelector("#reportForm details.checks").classList.toggle("hidden", general);
  $("rHow").textContent = general ? t("rHowGeneral", { to: CONFIG.reportEmail }) : CONFIG.reportEndpoint ? t("rHowSend", { host: new URL(CONFIG.reportEndpoint).host }) : t("rHowMail", { to: CONFIG.reportEmail });
};

async function buildReport() {
  const kind = document.querySelector("#reportForm input[name=kind]:checked").value;
  const id = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
  const ev = res.eval;
  const report = {
    id, created: new Date().toISOString(), app: "katip-yerel", version, page: location.origin + location.pathname, ui_lang: lang,
    feedback: { kind, what: $("rWhat").value, text: $("rText").value },
    document: { name: res.isSample ? res.name : "(kullanıcı belgesi)", sample: res.isSample, kind: res.kind, pages: res.pages, ocrPages: res.ocrPages, chars: res.text.length },
    settings: { ...res.settings, mask: $("incDetections").checked ? res.settings.mask : `${res.settings.mask.length} terim`, color: maskColor, watermark: $("watermark").checked, centerMark: $("centerMark").checked },
    result: { detected: res.spans.length, masked: chosen().length, applied, leaks: res.leaks?.length ?? null, unchecked: res.unchecked ?? null, timing: { ...res.timing, redact: res.redactMs },
      score: ev ? { recall: ev.recall, precision: ev.precision, missed: ev.gold.filter((_, i) => !ev.found[i]).map(x => ({ type: x.entity_type, text: x.text })), false_alarms: ev.fps.map(x => ({ type: x.entity_type, text: x.text })) } : null },
    detections: $("incDetections").checked ? res.spans.map(s => ({ type: s.entity_type, text: s.text, start: s.start, end: s.end, score: s.score, recognizer: s.recognizer, masked: !off.has(key(s)) }))
                                           : res.spans.map(s => ({ type: s.entity_type, start: s.start, end: s.end, score: s.score, recognizer: s.recognizer, masked: !off.has(key(s)) })),
    browser: navigator.userAgent,
  };
  const zip = new JSZip();
  zip.file("report.json", JSON.stringify(report, null, 1));
  if ($("incMasked").checked && outBlob) zip.file("maskeli/" + outName, outBlob);
  if ($("incOriginal").checked) {
    const o = await new Promise(r => { pendingOriginal = r; worker.postMessage({ type: "original" }); });
    zip.file("orijinal/" + o.name, o.bytes);
  }
  return { id, report, blob: await zip.generateAsync({ type: "blob", compression: "DEFLATE" }) };
}
const KIND_TR = { general: "Genel görüş", missed: "Kaçan veri", false_positive: "Gereksiz maskeleme", broken: "Bozuk çıktı", other: "Diğer" };
const KIND_EN = { general: "General feedback", missed: "Left visible", false_positive: "Masked by mistake", broken: "File won't open", other: "Other" };
function mailGeneral() {
  const kind = document.querySelector("#reportForm input[name=kind]:checked").value;
  const subject = lang === "en" ? `Katip Mask feedback: ${KIND_EN[kind]}` : `Katip Mask görüş: ${KIND_TR[kind]}`;
  const body = [$("rText").value, "", `${location.origin + location.pathname} · ${version.app} · ${version.rules}`,
    res?.spans ? `${res.kind} · ${res.settings.engineName} · ${res.spans.length}/${chosen().length}` : null].filter(x => x != null).join("\n");
  location.href = `mailto:${CONFIG.reportEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body.slice(0, 1800))}`;
  $("rStatus").textContent = t("rHowGeneral", { to: CONFIG.reportEmail });
  window.__lastMailto = { subject, body, fname: null };
}
$("rMail").onclick = async () => {
  if (!res?.spans || document.querySelector("#reportForm input[name=kind]:checked").value === "general") return mailGeneral();
  const { id, report, blob } = await buildReport();
  const fname = `katip-rapor-${id}.zip`;
  const a = el("a", { href: URL.createObjectURL(blob), download: fname }); a.click();
  const sc = report.result.score;
  const body = [`Tür: ${KIND_TR[report.feedback.kind]}`, report.feedback.what && `Değer/yer: ${report.feedback.what}`, "", report.feedback.text, "",
    `Belge: ${report.document.name} (${report.document.kind}, ${report.document.pages} sayfa)`, `Model: ${report.settings.engineName} · eşik ${report.settings.threshold} · OCR ${report.settings.ocrLang}`,
    sc && `Puan: yakalama ${(sc.recall * 100).toFixed(1)}%, kesinlik ${(sc.precision * 100).toFixed(1)}%`, `Sürüm: ${version.rules} (${version.built})`, "",
    `Lütfen indirilen ${fname} dosyasını bu e-postaya ekleyin. / Please attach ${fname}.`].filter(x => x !== null && x !== undefined && x !== false).join("\n");
  const subject = `Katip Mask hata bildirimi: ${KIND_TR[report.feedback.kind]} (${report.document.kind})`;
  location.href = `mailto:${CONFIG.reportEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body.slice(0, 1800))}`;
  $("rStatus").textContent = t("rDownloaded", { f: fname, to: CONFIG.reportEmail });
  window.__lastMailto = { subject, body, fname };
};
$("rSend").onclick = async () => {
  $("rStatus").textContent = t("rSending");
  try {
    const { id, report, blob } = await buildReport();
    const fd = new FormData();
    fd.append("_subject", `Katip Mask hata bildirimi ${id}`); fd.append("email", CONFIG.reportEmail);
    fd.append("message", `${KIND_TR[report.feedback.kind]}: ${report.feedback.what}\n\n${report.feedback.text}`);
    fd.append("report", JSON.stringify(report)); fd.append("attachment", blob, `katip-rapor-${id}.zip`);
    const r = await fetch(CONFIG.reportEndpoint, { method: "POST", body: fd, headers: { Accept: "application/json" } });
    $("rStatus").textContent = r.ok ? t("rSent") : `${t("rFailed")} (${r.status}).`;
  } catch (e) { $("rStatus").textContent = `${t("rFailed")}: ${e.message}`; }
};

// ---------------------------------------------------------------- boot
(async () => {
  status(t("loading"));
  try {
    [samples, models, version] = await Promise.all(["samples/manifest.json", "models/registry.json", "version.json"].map(async u => {
      const r = await fetch(u); if (!r.ok) throw new Error(`${u}: HTTP ${r.status}`); return r.json(); }));
  } catch (e) { status(t("error") + e.message); return; }
  $("version").textContent = `Katip Mask ${version.app} · ${version.rules} · ${version.built}`;
  if (version.source) $("srcLink").href = version.source;
  buildColorUI(); buildSampleUI(); buildModelUI(); buildEntityUI(); buildProfileUI(); applyLang();
  const q = new URLSearchParams(location.search).get("sample");  // ?sample=dilekce:udf opens a sample directly (handy for sharing)
  if (q) { const [ty, fm] = q.split(":"), sm = samples.find(x => x.type === ty || x.id === ty); if (sm) openSample(sm, sm.formats.includes(fm) ? fm : sm.formats[0]); }
})();
