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
    netLbl: "Belge sonrası ağ isteği", netTip: "Belgeyi açtıktan sonra bu sayfanın internete kaç kez bağlandığı. 0 kalmalı.||Motor ve model dosyaları sayılmaz; bunlar belgeyi açmadan önce indirilir.",
    cspLbl: "Dışarı gönderim", blocked: "engelli", cspTip: "Bu sayfa belgenizi başka bir yere gönderemez.||Sayfanın güvenlik politikası (CSP), tarayıcının başka bir adrese veri göndermesini engeller.",
    storeLbl: "Kayıt", none: "yok", storeTip: "Hiçbir şey kaydedilmez; sekmeyi kapatınca belge silinir.||Belge yalnızca bu sekmenin belleğinde tutulur.",
    docH: "Belge", sampleTab: "Örnek belge", fileTab: "Kendi belgem",
    sampleHint: "Sentetik belgeler, cevap anahtarıyla puanlanır.",
    sampleTip: "Örneklerdeki kişiler uydurmadır. Doğru cevaplar bilindiği için kaçanları da görürsünüz.||Bulunan, kaçan ve fazladan işaretlenen değerler cevap anahtarına göre canlı sayılır.",
    dropH: "Belgeyi bırakın veya tıklayın", fileHint: "Dosya yalnızca bu sekmenin belleğinde kalır.",
    fileTip: "Dosyanız bilgisayarınızdan çıkmaz.||Açma, tarama, maskeleme ve kontrol bu sekmede yapılır; sekmeyi kapatınca silinir.",
    detectH: "Algılama", ocrH: "OCR (tarama ve fotoğraf)",
    ocrTip: "Taranmış belge ve fotoğrafları okuyan model. Önerilen yeterlidir.||Türkçe Tesseract modeli. 96 taranmış örnekte ikisi neredeyse aynı değerleri buldu; önerilen 4 kat küçüktür çünkü yalnızca yeni (LSTM) okuyucuyu içerir.",
    thrH: "Güven eşiği", thrTip: "Düşük: daha çok yakalar, daha çok yanlış alarm. Yüksek: tersi.||T.C. kimlik, VKN, IBAN gibi sağlama kontrollü numaralar her zaman yakalanır.",
    typesH: "Veri türleri", maskH: "Maske", colorH: "Renk", styleH: "Word ve metinde",
    styleTip: "Değerin yerine ne konacağı: kutu, ████ veya [AD SOYAD-1] gibi etiket.||PDF ve görüntülerde seçilen renkte kutu çizilir. Word, UDF ve metinde değer ██████ veya etiketle değiştirilir.",
    styleBox: "██████ blok", styleLabel: "[AD SOYAD-1] etiket",
    tipMore: "Ayrıntılar",
    markH: "Ortaya Katip logosu", markTip: "Her sayfanın ortasına soluk bir Katip logosu basar.||PDF ve görüntülerde. Kapalıyken alttaki tek satırlık filigran yine eklenir.",
    wmH: "Filigran ekle", wmTip: "Çıktının altına küçük bir \"Katip Yerel ile maskelendi\" satırı ekler.||Tam metin: \"{wm}\". PDF'te bağlantılıdır. UYAP .udf dosyalarına eklenmez.",
    viewReview: "İnceleme", viewResult: "Sonuç", apply: "Maskeleri uygula", reapply: "Yeniden uygula", download: "İndir", report: "Hata bildir",
    copy: "Etiketli metni kopyala", forget: "Belgeyi unut",
    empty: "Soldan bir örnek seçin veya kendi belgenizi açın.",
    termPh: "Kaçan bir terim ekle", add: "Ekle",
    findTip: "İşaretini kaldırdığınız değer maskelenmez.||Belgedeki işarete tıklamak da aç/kapa yapar. ⚑ o değeri hata bildirimine ekler.",
    found: "{n} değer maskelenecek", missedH: "Kaçanlar", addMissed: "Maskeye ekle", flag: "Hata bildirimine ekle", warnOnly: "uyarı",
    details: "Ayrıntılar",
    sRecall: "bulundu", sFp: "fazla", sLeak: "çıktıda okunabilir", sNotApplied: "Değişiklikler henüz uygulanmadı",
    sPreview: "Henüz maskelenmedi: işaretleri kontrol edin, sonra Maskeleri uygula'ya basın.",
    leakBad: "Dikkat: {n} değer çıktıda hâlâ okunabiliyor. Göndermeyin.", leakUnchecked: "Taranmış sayfalar tekrar okunmadı; çıktıyı gözle kontrol edin.",
    leakOk: "Sızıntı kontrolü geçti: maskelenen değerlerin hiçbiri çıktıda okunamıyor.",
    loading: "Motor yükleniyor…", ready: "Motor hazır ({s} sn).", preparing: "Hazırlanıyor…", done: "{n} değer maskelendi.", copied: "Etiketli metin kopyalandı.", forgotten: "Belge bellekten silindi.",
    waiting: "Motor yükleniyor; sonra Kişisel verileri bul'a basın.", toScan: "Önizleme hazır. Kişisel verileri bul'a basın.", listHint: "Kişisel verileri bul'a basınca bulunan değerler burada türlerine göre listelenir; her birini açıp kapatabilirsiniz.", scan: "Kişisel verileri bul", rescan: "Yeniden tara",
    error: "Hata: ", page: "Sayfa", ok: "doğru", fpL: "fazla", missL: "kaçan",
    tType: "Tür", tGold: "Doğru cevap", tFound: "Bulunan", tMissed: "Kaçan", tFp: "Fazla", partial: "kısmen: yalnız \"{p}\"",
    goldNote: "Doğru cevaplar belgeyi üreten betikten gelir. Taranmış belgelerde OCR hataları da puanı etkiler.",
    kModel: "Model", kOcr: "OCR modeli", kPages: "Sayfa", kParse: "Okuma ve OCR", kRules: "Kurallar", kRedact: "Maskeleme ve kontrol", kVersion: "Motor sürümü", unused: "kullanılmadı",
    rWhatWrong: "Ne yanlış?", rMissed: "Bir şey maskelenmedi", rFp: "Gereksiz bir şey maskelendi", rBroken: "Çıktı bozuk veya açılmıyor", rOther: "Diğer",
    rWhere: "Hangi değer veya yer? (isteğe bağlı)", rDesc: "Açıklama", rDescPh: "Ne bekliyordunuz, ne oldu?", rInclude: "Rapora eklenecekler",
    rIncSettings: "Ayarlar, sürüm, süreler, puanlar", rIncMasked: "Maskeli çıktı", rIncDet: "Bulunan değerler", rIncOrig: "Orijinal belge",
    rPersonal: "(kişisel veri içerir)", rPersonalOk: "(kişisel veri içerir; yalnızca izniniz varsa)", cancel: "Vazgeç", rSend: "Doğrudan gönder", rMail: "Raporu indir ve e-posta aç",
    rHowMail: "Rapor bilgisayarınıza indirilir ve e-posta uygulamanız {to} adresine açılır. İndirilen .zip dosyasını ekleyip gönderin. Siz göndermeden hiçbir şey çıkmaz.",
    rHowSend: "\"Doğrudan gönder\" raporu {host} üzerinden iletir. Ya da raporu indirip e-postayla kendiniz gönderin.",
    rDownloaded: "{f} indirildi. E-posta açılmadıysa {to} adresine dosyayı ekleyerek yazın.", rSending: "Gönderiliyor…", rSent: "Gönderildi, teşekkürler.", rFailed: "Gönderilemedi",
    foot: "Kurallar Katip sunucusundakilerle aynı (Pyodide) · PDF: MuPDF · OCR: Tesseract", source: "Kaynak kod", issues: "Soru ve öneriler",
    onSpace: "Bu sayfa için çok büyük (110 MB) · Hugging Face'te deneyin →",
    ocrBest: "Küçük", ocrBestMeta: "Aynı doğruluk, 4 kat küçük · 2 MB", ocrFast: "Standart", ocrFastMeta: "Eski motor verisiyle · 7,7 MB",
    origAlt: "Orijinal sayfa", maskAlt: "Maskeli sayfa", ocrText: "Okunan metin",
  },
  en: {
    tagline: "Turkish KVKK redaction that runs entirely in your browser. Nothing is uploaded.",
    netLbl: "Requests after opening", netTip: "How many times this page went online after you opened the document. It should stay 0.||Engine and model files are not counted; they download before you open a document.",
    cspLbl: "Sending out", blocked: "blocked", cspTip: "This page cannot send your document anywhere.||The page's Content-Security-Policy makes the browser block any request to another address.",
    storeLbl: "Stored", none: "nothing", storeTip: "Nothing is saved; closing the tab deletes the document.||The document lives only in this tab's memory.",
    docH: "Document", sampleTab: "Sample", fileTab: "My file",
    sampleHint: "Synthetic documents, scored against an answer key.",
    sampleTip: "The people in the samples are made up. The right answers are known, so you also see what was missed.||Found, missed and extra values are counted live against the answer key.",
    dropH: "Drop a file or click", fileHint: "The file stays in this tab's memory only.",
    fileTip: "Your file never leaves your computer.||Opening, scanning, masking and checking all happen in this tab; closing the tab deletes it.",
    detectH: "Detection", ocrH: "OCR (scans and photos)",
    ocrTip: "The model that reads scans and photos. The recommended one is enough.||Turkish Tesseract model. On 96 scanned samples both found almost the same values; the recommended one is 4× smaller because it holds only the newer (LSTM) reader.",
    thrH: "Confidence threshold", thrTip: "Lower catches more but raises more false alarms. Higher does the opposite.||Numbers with a checksum (T.C. kimlik, VKN, IBAN) are always caught.",
    typesH: "Data types", maskH: "Mask", colorH: "Colour", styleH: "In Word and text",
    styleTip: "What replaces each value: a box, ████ or a label such as [AD SOYAD-1].||PDFs and images get a box in the chosen colour. In Word, UDF and text the value is replaced with ██████ or a label.",
    styleBox: "██████ block", styleLabel: "[AD SOYAD-1] label",
    tipMore: "Details",
    markH: "Katip logo in the centre", markTip: "Stamps a faint Katip logo across the middle of each page.||PDFs and images only. Off, the one-line watermark at the bottom is still added.",
    wmH: "Add watermark", wmTip: "Adds a small \"Redacted with Katip Yerel\" line at the bottom.||Full text: \"{wm}\". Linked in PDFs. Not added to UYAP .udf files.",
    viewReview: "Review", viewResult: "Result", apply: "Apply masks", reapply: "Apply again", download: "Download", report: "Report a mistake",
    copy: "Copy labelled text", forget: "Forget document",
    empty: "Pick a sample on the left or open your own file.",
    termPh: "Add a missed term", add: "Add",
    findTip: "Untick a value and it will not be masked.||Clicking a highlight in the document toggles it too. ⚑ adds the value to a mistake report.",
    found: "{n} values to mask", missedH: "Missed", addMissed: "Add to masks", flag: "Add to mistake report", warnOnly: "flag",
    details: "Details",
    sRecall: "found", sFp: "extra", sLeak: "readable in output", sNotApplied: "Changes not applied yet",
    sPreview: "Nothing is masked yet: check the highlights, then press Apply masks.",
    leakBad: "Warning: {n} values are still readable in the output. Do not send it.", leakUnchecked: "Scanned pages were not re-read; check the output by eye.",
    leakOk: "Leak check passed: none of the masked values can be read in the output.",
    loading: "Loading engine…", ready: "Engine ready ({s} s).", preparing: "Preparing…", done: "{n} values masked.", copied: "Labelled text copied.", forgotten: "Document removed from memory.",
    waiting: "Engine loading; then press Find personal data.", toScan: "Preview ready. Press Find personal data.", listHint: "After Find personal data, the values found are listed here by type; you can switch each one on or off.", scan: "Find personal data", rescan: "Scan again",
    error: "Error: ", page: "Page", ok: "correct", fpL: "extra", missL: "missed",
    tType: "Type", tGold: "Answer key", tFound: "Found", tMissed: "Missed", tFp: "Extra", partial: "partly: only \"{p}\"",
    goldNote: "The answer key comes from the script that generated the document. On scans, OCR errors also affect the score.",
    kModel: "Model", kOcr: "OCR model", kPages: "Pages", kParse: "Reading and OCR", kRules: "Rules", kRedact: "Masking and check", kVersion: "Engine version", unused: "not used",
    rWhatWrong: "What went wrong?", rMissed: "Something was not masked", rFp: "Something was masked by mistake", rBroken: "The output is broken or won't open", rOther: "Other",
    rWhere: "Which value or place? (optional)", rDesc: "Description", rDescPh: "What did you expect, what happened?", rInclude: "Include in the report",
    rIncSettings: "Settings, version, timings, scores", rIncMasked: "Masked output", rIncDet: "Detected values", rIncOrig: "Original document",
    rPersonal: "(contains personal data)", rPersonalOk: "(contains personal data; only with permission)", cancel: "Cancel", rSend: "Send directly", rMail: "Download report and open e-mail",
    rHowMail: "The report is downloaded to your computer and your e-mail app opens a message to {to}. Attach the downloaded .zip and send it. Nothing leaves until you send it.",
    rHowSend: "\"Send directly\" delivers the report through {host}. Or download it and e-mail it yourself.",
    rDownloaded: "{f} downloaded. If no e-mail opened, write to {to} and attach the file.", rSending: "Sending…", rSent: "Sent, thank you.", rFailed: "Could not send",
    foot: "Same rules as the Katip server (Pyodide) · PDF: MuPDF · OCR: Tesseract", source: "Source code", issues: "Questions and ideas",
    onSpace: "Too big for this page (110 MB) · try it on Hugging Face →",
    ocrBest: "Compact", ocrBestMeta: "Same accuracy, 4× smaller · 2 MB", ocrFast: "Standard", ocrFastMeta: "Includes old engine data · 7.7 MB",
    origAlt: "Original page", maskAlt: "Masked page", ocrText: "Recognised text",
  },
};
const LABELS = {
  tr: { TCKN: "T.C. Kimlik No", VKN: "Vergi Kimlik No", IBAN: "IBAN", CREDIT_CARD: "Kredi kartı", PHONE: "Telefon", EMAIL: "E-posta", PLATE: "Araç plakası",
    PERSON: "Ad soyad", ADDRESS: "Adres", BIRTH_DATE: "Doğum tarihi", IP_ADDRESS: "IP adresi", HEALTH: "Sağlık", RELIGION: "Din/inanç", POLITICAL: "Siyasi görüş",
    UNION: "Sendika", ETHNICITY: "Etnik köken", SEXUAL_LIFE: "Cinsel hayat", BIOMETRIC_GENETIC: "Biyometrik/genetik", CRIMINAL_RECORD: "Ceza mahkumiyeti", CUSTOM: "Eklenen terim" },
  en: { TCKN: "Turkish ID no.", VKN: "Tax ID", IBAN: "IBAN", CREDIT_CARD: "Card number", PHONE: "Phone", EMAIL: "E-mail", PLATE: "Licence plate",
    PERSON: "Name", ADDRESS: "Address", BIRTH_DATE: "Birth date", IP_ADDRESS: "IP address", HEALTH: "Health", RELIGION: "Religion/belief", POLITICAL: "Political opinion",
    UNION: "Trade union", ETHNICITY: "Ethnic origin", SEXUAL_LIFE: "Sex life", BIOMETRIC_GENETIC: "Biometric/genetic", CRIMINAL_RECORD: "Criminal record", CUSTOM: "Added term" },
};
const FORMATS = { tr: { txt: "Metin", docx: "Word", udf: "UYAP .udf", pdf: "PDF", "scan.pdf": "Taranmış PDF", png: "Fotoğraf" },
                  en: { txt: "Text", docx: "Word", udf: "UYAP .udf", pdf: "PDF", "scan.pdf": "Scanned PDF", png: "Photo" } };
const SAMPLE_EN = { aydinlatma: "Privacy notice", bilirkisi: "Expert report", dilekce: "Petition", epikriz: "Hospital discharge summary", eposta: "E-mail thread",
  fatura: "Invoice", icra: "Enforcement request", ihtarname: "Formal notice", is_sozlesmesi: "Employment contract", karar: "Court judgment", kira_sozlesmesi: "Lease",
  mektup: "Letter", mesaj: "Chat log", tutanak: "Minutes", vekaletname: "Power of attorney", zabit: "Hearing record" };
const PROGRESS_EN = [[/^NER modeli yükleniyor/, "Loading name model"], [/^NER çalışıyor/, "Running name model"], [/^OCR sayfa (\d+)\/(\d+)/, "OCR page $1/$2"], [/^Sayfa (\d+)\/(\d+)/, "Page $1/$2"],
  [/^OCR$/, "OCR"], [/^Kişisel veriler aranıyor/, "Looking for personal data"], [/^Maskeleniyor/, "Masking"], [/tekrar okunuyor/, "Re-reading output (leak check)"]];
const ART6 = ["HEALTH", "RELIGION", "POLITICAL", "UNION", "ETHNICITY", "SEXUAL_LIFE", "BIOMETRIC_GENETIC", "CRIMINAL_RECORD"];
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
const runtimeFile = u => /\/(vendor|models|samples)\/|katip_py\.zip|\.(m?js|css|wasm|json)(\?|$)/.test(u);
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
  document.querySelectorAll("[data-i18n-tip]").forEach(e => { const s = t(e.dataset.i18nTip, { wm: wmText() }); e.dataset.tip = s; e.setAttribute("aria-label", s.split("||")[0]); e.setAttribute("role", "button"); });
  document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  document.title = lang === "tr" ? "Katip Yerel: tarayıcıda KVKK maskeleme" : "Katip Yerel: in-browser Turkish PII redaction";
  if (samples.length) { buildSampleOptions(); drawFormats(); buildModelUI(); buildEntityUI(); }
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
    threshold: Number($("threshold").value), style: $("style").value,
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
    const cb = el("input", { type: "checkbox", value: k, checked: prev.length ? on.has(k) : k !== "CRIMINAL_RECORD" });
    $("entities").append(el("label", {}, cb, " " + L(k) + (ART6.includes(k) ? " ·6" : "")));
  }
  entCount();
}
$("entities").onchange = () => { entCount(); res?.spans && redetect(); };
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
$("watermark").onchange = () => maskOptionsChanged();
$("centerMark").onchange = () => maskOptionsChanged();
function maskOptionsChanged() { if (res?.spans && applied && !busy) redactNow(); }

// ---------------------------------------------------------------- sources
function buildSampleOptions() {
  const cur = $("sampleType").value;
  $("sampleType").textContent = "";
  for (const s of samples) $("sampleType").append(el("option", { value: s.id, textContent: lang === "en" ? SAMPLE_EN[s.type] ?? s.title : s.title }));
  if (cur) $("sampleType").value = cur;
}
function buildSampleUI() {
  buildSampleOptions();
  $("sampleType").onchange = () => { src.sample = samples.find(s => s.id === $("sampleType").value); drawFormats(); loadSource(); };
  src.sample = samples[0]; drawFormats();
  $("srcSampleBtn").onclick = () => { if (src.mode === "sample") return; setMode("sample"); loadSource(); };
  $("srcFileBtn").onclick = () => { if (src.mode === "file") return; setMode("file"); if (src.file) loadSource(); };
}
function drawFormats() {
  const f = $("formatBtns"); f.textContent = "";
  if (!src.sample.formats.includes(src.format)) src.format = src.sample.formats[0];
  for (const fmt of src.sample.formats) {
    const b = el("button", { type: "button", textContent: FORMATS[lang][fmt] ?? fmt });
    b.dataset.fmt = fmt; b.setAttribute("aria-pressed", fmt === src.format);
    b.onclick = () => { if (src.format === fmt) return; src.format = fmt; drawFormats(); loadSource(); };
    f.append(b);
  }
}
function setMode(m) {
  src.mode = m;
  $("srcSampleBtn").setAttribute("aria-selected", m === "sample"); $("srcFileBtn").setAttribute("aria-selected", m === "file");
  $("srcSample").classList.toggle("hidden", m !== "sample"); $("srcFile").classList.toggle("hidden", m !== "file");
}
function pickFile(f) { if (!f) return; src.file = f; $("fileName").textContent = f.name; setMode("file"); loadSource(); }
$("drop").onclick = () => $("file").click();
$("drop").onkeydown = e => (e.key === "Enter" || e.key === " ") && $("file").click();
$("file").onchange = e => { pickFile(e.target.files[0]); e.target.value = ""; };
$("drop").ondragover = e => { e.preventDefault(); $("drop").classList.add("over"); };
$("drop").ondragleave = () => $("drop").classList.remove("over");
$("drop").ondrop = e => { e.preventDefault(); $("drop").classList.remove("over"); pickFile(e.dataTransfer.files[0]); };

// Selecting a document shows it at once; analysis starts as soon as the engine is ready.
async function loadSource() {
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
  res = null; applied = false; view = "review"; outBlob = null; busy = false;
  preview = { seq: my, kind: /\.(png|jpe?g|tiff?|bmp|webp)$/i.test(name) ? "image" : null, text: null, pages: [], imageUrl: null };
  if (preview.kind === "image") preview.imageUrl = URL.createObjectURL(new Blob([bytes]));
  renderPreview();
  if (preview.kind !== "image") send({ type: "preview", name, bytes: bytes.slice(), seq: my });
  updateButtons();
  status(ready ? t("toScan") : t("waiting"));
}

// ---------------------------------------------------------------- run
const status = m => ($("status").textContent = m);
const progressText = m => { if (lang === "tr") return m; for (const [re, en] of PROGRESS_EN) if (re.test(m)) return m.replace(re, en); return m; };
function analyze() {
  if (!loaded) return;
  const s = settings(), { name, gold, isSample } = loaded, bytes = loaded.bytes.slice();
  status(t("preparing"));
  docOpenedAt = performance.now(); netCount = 0; $("netCount").textContent = "0"; $("netPill").classList.remove("bad");
  res = { name, isSample, gold, settings: s, imageUrl: preview?.imageUrl ?? null, maskUrl: null, seq };
  off = new Set(); applied = false; view = "review"; busy = true; updateButtons();
  worker.postMessage({ type: "analyze", name, bytes, settings: s, seq }, [bytes.buffer]);
}
function redetect() { if (!res?.spans || busy) return; res.settings = settings(); busy = true; updateButtons(); worker.postMessage({ type: "redetect", settings: res.settings }); }
function redactNow() {
  busy = true; updateButtons(); status(progressText("Maskeleniyor") + "…");
  worker.postMessage({ type: "redact", spans: chosen(), style: $("style").value, verifyOcr: true, ocrLang: res.settings.ocrLang, color: rgb(maskColor),
                       watermark: $("watermark").checked && CONFIG.watermark ? { text: wmText(), url: CONFIG.watermark.url } : null,
                       mark: $("centerMark").checked });
}
$("apply").onclick = () => res?.spans && !busy && redactNow();
$("scan").onclick = () => ready && loaded && !busy && analyze();
$("addTerm").onclick = () => addTerm($("term").value);
$("term").onkeydown = e => e.key === "Enter" && $("addTerm").click();
function addTerm(v) { v = (v ?? "").trim(); if (!v || !res?.spans) return; maskTerms.push(v); $("term").value = ""; redetect(); }
document.querySelectorAll("#viewSeg [data-view]").forEach(b => (b.onclick = () => { if (b.disabled) return; view = b.dataset.view; render(); }));

function updateButtons() {
  const has = !!res?.spans;
  $("scan").disabled = !ready || !loaded || busy; $("scan").textContent = has ? t("rescan") : t("scan"); $("scan").classList.toggle("primary", !has);
  $("apply").classList.toggle("hidden", !has); $("download").classList.toggle("hidden", !has);
  $("apply").disabled = !has || busy; $("apply").textContent = applied ? t("reapply") : t("apply");
  $("apply").classList.toggle("primary", !applied || dirty());
  $("download").disabled = !applied || busy; $("download").classList.toggle("primary", applied && !dirty());
  $("reportBtn").disabled = !has;
  document.querySelector('#viewSeg [data-view="result"]').disabled = !applied;
  document.querySelectorAll("#viewSeg [data-view]").forEach(b => b.setAttribute("aria-selected", b.dataset.view === view));
}

worker.onmessage = async ({ data: m }) => {
  if (m.type === "alive") { workerAlive = true; for (const [msg, tr] of outbox.splice(0)) worker.postMessage(msg, tr); return; }
  if (m.type === "ready") {
    ready = true; status(loaded && !res ? t("toScan") : t("ready", { s: (m.ms / 1000).toFixed(1) })); getTess("best_int"); updateButtons();
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
    off = new Set(m.spans.filter(s => s.flag_only || !res.settings.entities.includes(s.entity_type)).map(key));
    busy = false; status(t("found", { n: chosen().length }) + "."); render();
  } else if (m.type === "redetected") {
    if (!res?.spans) return;
    const wasOff = new Set([...off].filter(k => res.spans.some(s => key(s) === k && !s.flag_only)));
    res.spans = m.spans; Object.assign(res.timing, m.timing); res.nerCount = m.nerCount;
    off = new Set(m.spans.filter(s => s.flag_only || wasOff.has(key(s))).map(key));
    busy = false; if (applied) redactNow(); else { status(t("found", { n: chosen().length }) + "."); render(); }
  } else if (m.type === "redacted") {
    if (!res?.spans) return;
    outBlob = new Blob([m.out], { type: m.mime }); outName = m.outName;
    Object.assign(res, { outText: m.outText, leaks: m.leaks, unchecked: m.unchecked, redactMs: m.ms,
      maskPreviews: m.previews.map(p => URL.createObjectURL(new Blob([p], { type: "image/png" }))), appliedKeys: new Set(chosen().map(key)) });
    if (res.kind === "image") res.maskUrl = URL.createObjectURL(outBlob);
    busy = false; applied = true; view = "result";
    status(t("done", { n: chosen().length })); render();
  } else if (m.type === "maskedText") { await navigator.clipboard.writeText(m.text); status(t("copied")); }
  else if (m.type === "original") { pendingOriginal?.(m); }
  else if (m.type === "forgotten") {
    res = null; outBlob = null; loaded = null; preview = null; applied = false; busy = false; seq++;
    $("rv").classList.add("hidden"); $("more").classList.add("hidden"); $("scorebar").classList.add("hidden"); $("empty").hidden = false;
    updateButtons(); status(t("forgotten"));
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
function goldEval(spans, gold, ocr = false) {
  const matches = ocr ? ocrMatches : exactMatches;
  const g = gold.filter(x => x.entity_type !== "CRIMINAL_RECORD");
  const found = g.map(x => spans.some(s => matches(s.text, x.text)));
  const partial = g.map((x, i) => found[i] ? null : spans.find(s => sq(s.text).length >= 2 && sq(x.text).includes(sq(s.text)))?.text ?? null);
  const fps = spans.filter(s => !g.some(x => matches(s.text, x.text) || matches(x.text, s.text)));
  const per = {};
  g.forEach((x, i) => { const p = per[x.entity_type] ??= { gold: 0, found: 0, fp: 0 }; p.gold++; if (found[i]) p.found++; });
  for (const s of fps) (per[s.entity_type] ??= { gold: 0, found: 0, fp: 0 }).fp++;
  return { gold: g, found, partial, fps, per, recall: found.filter(Boolean).length / Math.max(1, g.length),
           precision: (spans.length - fps.length) / Math.max(1, spans.length) };
}

// ---------------------------------------------------------------- rendering
const key = s => `${s.entity_type}:${s.start}:${s.end}`;
const chosen = () => (res?.spans ?? []).filter(s => !off.has(key(s)));
const dirty = () => !!(applied && res?.appliedKeys && (res.appliedKeys.size !== chosen().length || chosen().some(s => !res.appliedKeys.has(key(s)))));
function toggle(s) { off.has(key(s)) ? off.delete(key(s)) : off.add(key(s)); if (view === "result") view = "review"; render(); }

function renderPreview() {
  // before analysis: the document as it is, no highlights yet
  $("empty").hidden = true; $("rv").classList.remove("hidden"); $("scorebar").classList.add("hidden"); $("more").classList.add("hidden");
  const D = $("docView"); D.textContent = ""; D.className = "docview";
  if (preview.kind === "image" && preview.imageUrl) D.append(el("div", { className: "pg" }, el("img", { src: preview.imageUrl, alt: t("origAlt") })));
  else if (preview.pages.length) for (const u of preview.pages) D.append(el("div", { className: "pg" }, el("img", { src: u, alt: t("origAlt") })));
  else if (preview.text != null) D.append(el("div", { className: "txt", textContent: preview.text.replace(/\f/g, "\n") }));
  else D.append(el("div", { className: "skel" }));
  $("list").textContent = ""; $("fCount").textContent = "";
  document.querySelector(".fhead").classList.add("hidden");
  $("list").append(el("p", { className: "hint", textContent: t("listHint") }));
}

function render() {
  if (!res?.spans) { if (preview) renderPreview(); updateButtons(); return; }
  if (!applied && view === "result") view = "review";
  $("empty").hidden = true; $("rv").classList.remove("hidden"); $("more").classList.remove("hidden");
  res.eval = res.gold ? goldEval(chosen(), res.gold, res.kind === "image" || res.ocrPages > 0) : null;
  updateButtons(); renderScore(); renderDoc(); renderList(); renderGold(); renderTiming();
}

function renderScore() {
  const S = $("scorebar"); S.textContent = "";
  const ev = res.eval, items = [];
  if (ev) {
    items.push(el("span", { className: "sc" }, el("b", { textContent: `${ev.found.filter(Boolean).length}/${ev.gold.length}` }), " " + t("sRecall")));
    items.push(el("span", { className: "sc" + (ev.fps.length ? " warn-t" : "") }, el("b", { textContent: String(ev.fps.length) }), " " + t("sFp")));
  }
  if (applied) {
    const n = res.leaks.length, cls = n ? "bad-t" : res.unchecked ? "warn-t" : "ok-t";
    items.push(el("span", { className: "sc " + cls }, el("b", { textContent: String(n) }), " " + t("sLeak")));
    items.push(el("span", { className: "msg " + cls, textContent: n ? t("leakBad", { n }) : res.unchecked ? t("leakUnchecked") : t("leakOk") }));
  }
  if (dirty()) items.push(el("span", { className: "msg warn-t", textContent: t("sNotApplied") }));
  else if (!applied) items.push(el("span", { className: "msg", textContent: t("sPreview") }));
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
  const items = [...res.spans, ...miss].sort((a, b) => a.start - b.start);
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
    const rows = spans.map(s => {
      const cb = el("input", { type: "checkbox", checked: !off.has(key(s)), ariaLabel: s.text }); cb.onchange = () => toggle(s);
      const fp = res.eval && res.eval.fps.some(f => key(f) === key(s));
      const flag = el("button", { type: "button", className: "flag", textContent: "⚑", title: t("flag"), ariaLabel: t("flag") });
      flag.onclick = e => { e.preventDefault(); openReport(off.has(key(s)) ? "missed" : "false_positive", s.text); };
      const v = el("span", { className: "v" + (fp ? " fp-t" : ""), textContent: s.text.replace(/\s+/g, " "), title: `${s.recognizer} · ${s.score.toFixed(2)}${s.flag_only ? " · " + t("warnOnly") : ""}` });
      v.onclick = e => { e.preventDefault(); document.querySelector(`#docView [data-k="${CSS.escape(key(s))}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" }); };
      return el("div", { className: "it" }, cb, v, flag);
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
$("download").onclick = () => { if (!outBlob) return; const a = el("a", { href: URL.createObjectURL(outBlob), download: outName }); a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 30000); };
$("copy").onclick = () => { res?.spans && worker.postMessage({ type: "maskedText", spans: chosen() }); $("copy").closest("details").open = false; };
$("clear").onclick = () => { worker.postMessage({ type: "forget" }); $("clear").closest("details").open = false; };

// ---------------------------------------------------------------- report a mistake
let pendingOriginal = null;
function openReport(kind = "missed", what = "") {
  if (!res?.spans) return;
  document.querySelector(`#reportForm input[name=kind][value=${kind}]`).checked = true;
  $("rWhat").value = what; $("rStatus").textContent = "";
  $("incMasked").checked = applied; $("incMasked").disabled = !applied;
  $("incDetections").checked = res.isSample; $("incOriginal").checked = res.isSample;
  $("detWarn").classList.toggle("hidden", res.isSample); $("origWarn").classList.toggle("hidden", res.isSample);
  $("rSend").classList.toggle("hidden", !CONFIG.reportEndpoint);
  $("rHow").textContent = CONFIG.reportEndpoint ? t("rHowSend", { host: new URL(CONFIG.reportEndpoint).host }) : t("rHowMail", { to: CONFIG.reportEmail });
  $("reportDlg").showModal();
}
$("reportBtn").onclick = () => openReport();

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
const KIND_TR = { missed: "Kaçan veri", false_positive: "Gereksiz maskeleme", broken: "Bozuk çıktı", other: "Diğer" };
$("rMail").onclick = async () => {
  const { id, report, blob } = await buildReport();
  const fname = `katip-rapor-${id}.zip`;
  const a = el("a", { href: URL.createObjectURL(blob), download: fname }); a.click();
  const sc = report.result.score;
  const body = [`Tür: ${KIND_TR[report.feedback.kind]}`, report.feedback.what && `Değer/yer: ${report.feedback.what}`, "", report.feedback.text, "",
    `Belge: ${report.document.name} (${report.document.kind}, ${report.document.pages} sayfa)`, `Model: ${report.settings.engineName} · eşik ${report.settings.threshold} · OCR ${report.settings.ocrLang}`,
    sc && `Puan: yakalama ${(sc.recall * 100).toFixed(1)}%, kesinlik ${(sc.precision * 100).toFixed(1)}%`, `Sürüm: ${version.rules} (${version.built})`, "",
    `Lütfen indirilen ${fname} dosyasını bu e-postaya ekleyin. / Please attach ${fname}.`].filter(x => x !== null && x !== undefined && x !== false).join("\n");
  const subject = `Katip Yerel hata bildirimi: ${KIND_TR[report.feedback.kind]} (${report.document.kind})`;
  location.href = `mailto:${CONFIG.reportEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body.slice(0, 1800))}`;
  $("rStatus").textContent = t("rDownloaded", { f: fname, to: CONFIG.reportEmail });
  window.__lastMailto = { subject, body, fname };
};
$("rSend").onclick = async () => {
  $("rStatus").textContent = t("rSending");
  try {
    const { id, report, blob } = await buildReport();
    const fd = new FormData();
    fd.append("_subject", `Katip Yerel hata bildirimi ${id}`); fd.append("email", CONFIG.reportEmail);
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
  $("version").textContent = `Katip Yerel ${version.app} · ${version.rules} · ${version.built}`;
  if (version.source) $("srcLink").href = version.source;
  buildColorUI(); buildSampleUI(); buildModelUI(); buildEntityUI(); applyLang();
  loadSource();
})();
