// Katip "send to AI" page: mask on this device, send only masked text to Claude or ChatGPT, put the names back.
// Uses the same worker, engine and models as the full app (index.html). The placeholder map lives only in this
// tab's memory. The page talks to the network only for its own files, and for api.anthropic.com/api.openai.com
// when the user turns on API mode with their own key (masked text only).
import Tesseract from "./vendor/tesseract.js/dist/tesseract.esm.min.js";
import { GROUPS, PROFILES, ALWAYS, LAW, SRC } from "./legal.js";

const $ = id => document.getElementById(id);
const el = (tag, props = {}, ...kids) => { const e = Object.assign(document.createElement(tag), props); e.append(...kids.filter(k => k != null)); return e; };

// ---------------------------------------------------------------- text
const I18N = {
  tr: {
    tagline: "Yapay zekâya maskeli gönder", trust: "Belgeniz bu cihazda maskelenir. Claude'a veya ChatGPT'ye yalnızca maskeli metin gider; gerçek isimler bu sekmede kalır.",
    h1: "Belgeyi ekleyin", pick: "Dosya seçin veya fotoğraf çekin", pickSub: "PDF, Word, UYAP .udf, metin, fotoğraf", orPaste: "ya da metni yapıştırın", pastePh: "Metni buraya yapıştırın", maskThis: "Maskele",
    h2: "Ne için maskeleniyor?", whyTitle: "Ne maskelenir, neden? (kanun ve kaynaklar)", always: "Her profilde geçerli", masked: "maskelenir", readable: "okunur kalır", why: "Neden", law: "Dayanak",
    h3: "Kontrol edin", h4: "Gönderin", h5: "İsimleri geri koyun",
    loading: "Hazırlanıyor (ilk açılışta model iner, ~60 MB)…", ready: "Hazır. Bir belge ekleyin.", working: "Maskeleniyor…",
    ok: "{n} değer maskelendi. Bulunan değerlerin hiçbiri metinde kalmadı.", leak: "Dikkat: {n} değer hâlâ metinde görünüyor. Göndermeyin; aşağıdan ekleyin.",
    review: "Katip bazı değerleri kaçırabilir. Göndermeden önce metni okuyun.",
    residualH: "Hâlâ görünenler", residualHint: "Bunlar tek başına kimseyi göstermez, ama bir araya gelince gösterebilir. Gerekmiyorsa maskeleyin.", maskAll: "Hepsini maskele",
    itemsH: "Maskelenenler", itemsHint: "Yanlış maskelenen bir şey varsa dokunup açın.",
    addPh: "Kaçan bir isim veya bilgi mi var? Yazın", add: "Maskele",
    withNote: "Yapay zekâya etiketleri korumasını söyleyen kısa bir not ekle",
    toClaude: "Claude'da aç", toChatgpt: "ChatGPT'de aç", share: "Paylaş…", copy: "Kopyala",
    sendHint: "Uzun metinler bağlantıya sığmaz: metin kopyalanır, sohbet kutusuna yapıştırmanız yeterli. Telefonda \"Paylaş\" ile ChatGPT veya Claude uygulamasını seçebilirsiniz.",
    copied: "Kopyalandı. Sohbet kutusuna yapıştırın.", opened: "Açıldı.", copiedOpen: "Metin uzun: kopyalandı. Açılan sohbete yapıştırın.",
    apiTitle: "Kendi API anahtarınızla burada sorun", apiHint: "Maskeli metin bu tarayıcıdan doğrudan Anthropic'e veya OpenAI'a gider; Katip'e uğramaz. API hesapları, aylık Claude Pro/Max veya ChatGPT Plus aboneliğinden ayrı ücretlendirilir. API koşullarında veriler varsayılan olarak modeli eğitmek için kullanılmaz.",
    keyPh: "API anahtarı (sk-…)", remember: "Bu cihazda hatırla", askPh: "Sorunuz (ör. Bu dilekçeyi özetle, eksikleri yaz)", ask: "Sor", asking: "Soruluyor…", noKey: "Önce API anahtarını girin.",
    refused: "Model bu isteği yanıtlamadı.", apiErr: "API hatası: {e}",
    answerPh: "Yapay zekânın cevabını buraya yapıştırın; [AD SOYAD-1] gibi etiketler gerçek değerlerle değişir.",
    restoredN: "{n} etiket geri kondu.", unknown: "Bu belgede olmayan etiketler: {l}", copyBack: "Kopyala", download: "İndir (.txt)",
    logTitle: "Kayıt (yalnızca bu cihazda)", logHint: "Ne zaman, hangi profille, ne türde kaç değer maskelenip nereye gönderildi. Değerlerin kendisi kaydedilmez.", export: "Dışa aktar", clear: "Temizle",
    fullApp: "Tam uygulama (PDF karartma, ayarlar)", privacy: "Gizlilik",
    note: "Not: Bu metindeki [AD SOYAD-1] gibi köşeli parantezli etiketler, maskelenmiş kişisel verilerdir. Etiketleri cevabında aynen kullan; gerçek değerlerini tahmin etmeye çalışma.",
    err: "Hata: {e}",
  },
  en: {
    tagline: "Send to AI, masked", trust: "Your document is masked on this device. Claude or ChatGPT only get the masked text; the real names stay in this tab.",
    h1: "Add the document", pick: "Choose a file or take a photo", pickSub: "PDF, Word, UYAP .udf, text, photo", orPaste: "or paste text", pastePh: "Paste the text here", maskThis: "Mask",
    h2: "What is it for?", whyTitle: "What is masked, and why? (law and sources)", always: "Applies to every profile", masked: "masked", readable: "stays readable", why: "Why", law: "Basis",
    h3: "Check it", h4: "Send it", h5: "Put the names back",
    loading: "Getting ready (the model downloads on first use, ~60 MB)…", ready: "Ready. Add a document.", working: "Masking…",
    ok: "{n} values masked. None of the values found is left in the text.", leak: "Careful: {n} values are still visible. Don't send; add them below.",
    review: "Katip can miss values. Read the text before you send it.",
    residualH: "Still visible", residualHint: "None of these identifies anyone alone, but together they can. Mask them if the AI doesn't need them.", maskAll: "Mask all",
    itemsH: "Masked", itemsHint: "Tap anything masked by mistake to unmask it.",
    addPh: "Missed a name or detail? Type it", add: "Mask",
    withNote: "Add a short note telling the AI to keep the labels",
    toClaude: "Open in Claude", toChatgpt: "Open in ChatGPT", share: "Share…", copy: "Copy",
    sendHint: "Long texts don't fit in a link: the text is copied, just paste it into the chat. On a phone, \"Share\" lets you pick the ChatGPT or Claude app.",
    copied: "Copied. Paste it into the chat.", opened: "Opened.", copiedOpen: "Long text: copied. Paste it into the chat that opened.",
    apiTitle: "Ask here with your own API key", apiHint: "The masked text goes from this browser straight to Anthropic or OpenAI, never through Katip. API accounts are billed separately from a Claude Pro/Max or ChatGPT Plus subscription. Under API terms, data is not used for training by default.",
    keyPh: "API key (sk-…)", remember: "Remember on this device", askPh: "Your question (e.g. Summarise this petition, list what's missing)", ask: "Ask", asking: "Asking…", noKey: "Enter an API key first.",
    refused: "The model declined this request.", apiErr: "API error: {e}",
    answerPh: "Paste the AI's answer here; labels like [AD SOYAD-1] are replaced with the real values.",
    restoredN: "{n} labels put back.", unknown: "Labels not in this document: {l}", copyBack: "Copy", download: "Download (.txt)",
    logTitle: "Record (on this device only)", logHint: "When, with which profile, how many values of each type were masked and where they were sent. The values themselves are never stored.", export: "Export", clear: "Clear",
    fullApp: "Full app (PDF redaction, settings)", privacy: "Privacy",
    note: "Note: labels in square brackets like [AD SOYAD-1] are masked personal data. Use the labels as they are in your answer; don't try to guess the real values.",
    err: "Error: {e}",
  },
};
const LABELS = {
  tr: { TCKN: "T.C. Kimlik No", VKN: "Vergi Kimlik No", IBAN: "IBAN", CREDIT_CARD: "Kredi kartı", PHONE: "Telefon", EMAIL: "E-posta", PLATE: "Araç plakası",
    PERSON: "Ad soyad", ADDRESS: "Adres", BIRTH_DATE: "Doğum tarihi", IP_ADDRESS: "IP adresi", YKN: "Yabancı kimlik no", PASSPORT: "Pasaport no", FOREIGN_ID: "Yabancı ülke kimlik no", UETS: "UETS adresi", HEALTH: "Sağlık", RELIGION: "Din/inanç", POLITICAL: "Siyasi görüş",
    UNION: "Sendika", ETHNICITY: "Etnik köken", SEXUAL_LIFE: "Cinsel hayat", BIOMETRIC_GENETIC: "Biyometrik/genetik", CRIMINAL_RECORD: "Ceza mahkumiyeti", UNREAD: "El yazısı alanı",
    CASE_NO: "Esas/karar/UYAP no", BAR_NO: "Baro/sicil no", DATE: "Tarih", PLACE: "İl/ilçe", INSTITUTION: "Mahkeme/kurum/şirket", CUSTOM: "Eklenen terim" },
  en: { TCKN: "Turkish ID no.", VKN: "Tax ID", IBAN: "IBAN", CREDIT_CARD: "Card number", PHONE: "Phone", EMAIL: "E-mail", PLATE: "Licence plate",
    PERSON: "Name", ADDRESS: "Address", BIRTH_DATE: "Birth date", IP_ADDRESS: "IP address", YKN: "Foreigner ID no.", PASSPORT: "Passport no.", FOREIGN_ID: "Foreign national ID", UETS: "UETS address", HEALTH: "Health", RELIGION: "Religion/belief", POLITICAL: "Political opinion",
    UNION: "Trade union", ETHNICITY: "Ethnic origin", SEXUAL_LIFE: "Sex life", BIOMETRIC_GENETIC: "Biometric/genetic", CRIMINAL_RECORD: "Criminal record", UNREAD: "Handwritten area",
    CASE_NO: "Case/UYAP no.", BAR_NO: "Bar/registry no.", DATE: "Date", PLACE: "Province/district", INSTITUTION: "Court/institution/company", CUSTOM: "Added term" },
};
const API_MODELS = { anthropic: ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"], openai: [] };
const CONTEXT = ["DATE", "PLACE", "INSTITUTION"];
const ALL_TYPES = GROUPS.flatMap(g => g.types).concat("CUSTOM");
const typesOf = p => new Set(PROFILES[p].groups.flatMap(id => GROUPS.find(g => g.id === id).types).concat("CUSTOM"));

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* storage blocked */ } },
};
let lang = (() => {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "tr" || q === "en") return q;
  const s = store.get("katip-lang"); if (s === "tr" || s === "en") return s;
  return (navigator.language || "tr").toLowerCase().startsWith("tr") ? "tr" : "en";
})();
const t = (k, v = {}) => (I18N[lang][k] ?? I18N.tr[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => v[x] ?? "");
const loc = o => o?.[lang] ?? o?.tr ?? "";
const L = k => LABELS[lang][k] ?? k;

// ---------------------------------------------------------------- state
let profile = store.get("katip-send-profile") === "anon" ? "anon" : "ai";
let ready = false, seq = 0, doc = null;  // doc: { name, spans, off:Set, on:Set, mask:[], text, map, leaks }
const key = s => `${s.start}:${s.end}:${s.entity_type}`;

// ---------------------------------------------------------------- worker
const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
let alive = false, pending = null; const outbox = [];  // pending: a document opened before the engine finished loading
const post = (m, tr = []) => alive ? worker.postMessage(m, tr) : outbox.push([m, tr]);
const tess = {};
const getTess = model => tess[model] ??= Tesseract.createWorker("tur", 1, {
  workerPath: new URL("./vendor/tesseract.js/dist/worker.min.js", location.href).href,
  corePath: new URL("./vendor/tesseract.js-core/", location.href).href,
  langPath: new URL(`./vendor/tessdata/${model}`, location.href).href, gzip: true, cacheMethod: "none", workerBlobURL: false,
});
async function ocr(png, model) {
  const { data } = await (await getTess(model)).recognize(new Blob([png]), {}, { blocks: true });
  const lines = [];
  for (const b of data.blocks ?? []) for (const p of b.paragraphs) for (const l of p.lines)
    lines.push(l.words.filter(w => w.text.trim() && w.confidence >= 0).map(w => ({ text: w.text, bbox: [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1] })));
  return lines.filter(l => l.length);
}
const settings = () => ({ ner: "katip-mask-mini", nerDtype: "q8", trust: 0.5, threshold: 0.5, ocrLang: "auto", addressDetail: "full",
  entities: ALL_TYPES, mask: doc?.mask ?? [] });

worker.onmessage = async ({ data: m }) => {
  if (m.type === "alive") { alive = true; for (const [x, tr] of outbox.splice(0)) worker.postMessage(x, tr); return; }
  if (m.type === "ready") { ready = true; if (pending) { post(pending[0], pending[1]); pending = null; status(t("working")); } else if (!doc) status(t("ready")); return; }
  if (m.type === "progress") return status(progressText(m.msg) + "…");
  if (m.type === "ocr") {
    try { worker.postMessage({ type: "ocrResult", id: m.id, lines: await ocr(m.png, m.lang) }); }
    catch (e) { worker.postMessage({ type: "ocrResult", id: m.id, error: String(e) }); }
    return;
  }
  if (m.type === "analyzed") { if (m.seq !== seq) return; doc.spans = m.spans; return remask(); }
  if (m.type === "redetected") { doc.spans = m.spans; return remask(); }
  if (m.type === "maskMap") { Object.assign(doc, { text: m.text, map: m.map, leaks: m.leaks }); status(""); return render(); }
  if (m.type === "error") { status(t("err", { e: m.msg }), true); }
};
const PROGRESS_EN = [[/^NER modeli yükleniyor/, "Loading name model"], [/^NER çalışıyor/, "Running name model"], [/^OCR sayfa (\d+)\/(\d+)/, "OCR page $1/$2"],
  [/^Sayfa (\d+)\/(\d+)/, "Page $1/$2"], [/^Kişisel veriler aranıyor/, "Looking for personal data"], [/^El yazısı OCR modeli yükleniyor/, "Loading handwriting OCR model"]];
const progressText = s => lang === "tr" ? s : PROGRESS_EN.reduce((a, [re, r]) => a.replace(re, r), s);

// ---------------------------------------------------------------- open a document
async function open(name, bytes) {
  doc = { name, spans: null, off: new Set(), on: new Set(), mask: [] };
  ["s3", "s4", "s5"].forEach(id => $(id).classList.add("hidden"));
  $("answer").value = ""; renderRestore();
  status(ready ? t("working") : t("loading"));
  const msg = [{ type: "analyze", name, bytes, settings: settings(), seq: ++seq }, [bytes.buffer]];
  if (ready) post(...msg); else pending = msg;
}
$("file").onchange = async e => { const f = e.target.files[0]; if (f) open(f.name, new Uint8Array(await f.arrayBuffer())); e.target.value = ""; };
$("pasteGo").onclick = () => { const s = $("paste").value.trim(); if (s) open("metin.txt", new TextEncoder().encode(s)); };
const pick = document.querySelector(".pick");
pick.ondragover = e => { e.preventDefault(); pick.classList.add("over"); };
pick.ondragleave = () => pick.classList.remove("over");
pick.ondrop = async e => { e.preventDefault(); pick.classList.remove("over"); const f = e.dataTransfer.files[0]; if (f) open(f.name, new Uint8Array(await f.arrayBuffer())); };

// which detected spans are masked: the profile's types, minus what the user opened, plus context items they closed
const isOn = s => doc.on.has(key(s)) || (typesOf(profile).has(s.entity_type) && !doc.off.has(key(s)));
function remask() { post({ type: "maskMap", spans: doc.spans.filter(isOn) }); }

// ---------------------------------------------------------------- render
function status(msg, bad = false) { $("status").textContent = msg; $("status").classList.toggle("bad", bad); }
function render() {
  ["s3", "s4", "s5"].forEach(id => $(id).classList.remove("hidden"));
  const on = doc.spans.filter(isOn), shown = doc.spans.filter(s => !isOn(s));
  $("check").replaceChildren(
    el("p", { className: doc.leaks.length ? "verdict bad" : "verdict good", textContent: doc.leaks.length ? t("leak", { n: doc.leaks.length }) : t("ok", { n: Object.keys(doc.map).length }) }),
    el("p", { className: "hint", textContent: t("review") }));
  // still visible: context types not masked (and anything the user opened)
  const resid = shown.filter(s => CONTEXT.includes(s.entity_type));
  $("residual").replaceChildren(...(resid.length ? [
    el("h3", { textContent: `${t("residualH")} (${resid.length})` }), el("p", { className: "hint", textContent: t("residualHint") }),
    el("div", { className: "chips" }, ...uniq(resid).map(s => chip(s, false)),
      el("button", { className: "all", textContent: t("maskAll"), onclick: () => { resid.forEach(s => { doc.on.add(key(s)); doc.off.delete(key(s)); }); remask(); } })),
  ] : []));
  const masked = uniq(on);
  const openList = $("items").querySelector("details")?.open ?? false;  // keep the list open across re-masks
  $("items").replaceChildren(el("details", { open: openList }, el("summary", {}, el("b", { textContent: `${t("itemsH")} (${masked.length})` })),
    el("p", { className: "hint", textContent: t("itemsHint") }), el("div", { className: "chips" }, ...masked.map(s => chip(s, true)))),
    ...uniq(shown.filter(s => !CONTEXT.includes(s.entity_type))).length ? [el("div", { className: "chips" }, ...uniq(shown.filter(s => !CONTEXT.includes(s.entity_type))).map(s => chip(s, false)))] : []);
  // masked text with labels highlighted
  const pre = $("masked"); pre.textContent = "";
  let pos = 0; const re = /\[[^\[\]\n]{1,40}-\d+\]/g; let m;
  const txt = doc.text.replace(/\f\n?/g, "\n");
  while ((m = re.exec(txt))) { pre.append(txt.slice(pos, m.index), el("mark", { textContent: m[0] })); pos = m.index + m[0].length; }
  pre.append(txt.slice(pos));
}
// one chip per distinct value (a name repeated ten times is one decision)
function uniq(spans) { const seen = new Map(); for (const s of spans) { const k = s.entity_type + "|" + s.text.toLocaleLowerCase("tr"); if (!seen.has(k)) seen.set(k, s); } return [...seen.values()]; }
function chip(s, masked) {
  const same = doc.spans.filter(x => x.entity_type === s.entity_type && x.text.toLocaleLowerCase("tr") === s.text.toLocaleLowerCase("tr"));
  return el("button", { className: masked ? "on" : "off", title: L(s.entity_type), onclick: () => {
    for (const x of same) { if (masked) { doc.off.add(key(x)); doc.on.delete(key(x)); } else { doc.on.add(key(x)); doc.off.delete(key(x)); } }
    remask();
  } }, el("small", { textContent: L(s.entity_type) }), " ", s.text.length > 40 ? s.text.slice(0, 38) + "…" : s.text);
}
$("addGo").onclick = () => {
  const v = $("addTerm").value.trim(); if (!v || !doc?.spans) return;
  doc.mask.push(v); $("addTerm").value = ""; status(t("working"));
  post({ type: "redetect", settings: settings() });
};
$("addTerm").onkeydown = e => { if (e.key === "Enter") $("addGo").click(); };

// ---------------------------------------------------------------- profiles and the "why" panels
function renderProfiles() {
  $("profiles").replaceChildren(...Object.entries(PROFILES).map(([id, p]) => el("button", { role: "radio", ariaChecked: String(id === profile), textContent: loc(p.name),
    onclick: () => { profile = id; store.set("katip-send-profile", id); renderProfiles(); if (doc?.spans) { doc.on.clear(); doc.off.clear(); remask(); } } })));
  $("profHint").textContent = loc(PROFILES[profile].hint);
  const inP = new Set(PROFILES[profile].groups);
  const law = id => { const x = LAW[id]; return el("li", {}, el("a", { href: SRC[x.src], target: "_blank", rel: "noopener", textContent: x.ref }), " ", loc(x)); };
  $("whyBody").replaceChildren(...GROUPS.map(g => el("details", { className: "grp" + (inP.has(g.id) ? " in" : "") },
      el("summary", {}, el("b", { textContent: loc(g.name) }), el("span", { className: "tag", textContent: inP.has(g.id) ? t("masked") : t("readable") })),
      el("p", { className: "types", textContent: g.types.map(L).join(" · ") }),
      el("p", {}, el("b", { textContent: t("why") + ": " }), loc(g.why)),
      el("ul", { className: "law" }, ...g.law.map(law)))),
    el("details", { className: "grp" }, el("summary", {}, el("b", { textContent: t("always") })), el("ul", { className: "law" }, ...ALWAYS.map(law))));
}

// ---------------------------------------------------------------- send
const outgoing = () => ($("withNote").checked ? t("note") + "\n\n" : "") + doc.text.replace(/\f\n?/g, "\n").trim();
function toast(msg) { const e = $("toast"); e.textContent = msg; e.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(() => { e.hidden = true; }, 3500); }
async function copy(text) { try { await navigator.clipboard.writeText(text); return true; } catch { return false; } }
function logSend(dest) {
  const counts = {}; for (const lab of Object.keys(doc.map)) { const typ = lab.replace(/^\[|-\d+\]$/g, ""); counts[typ] = (counts[typ] ?? 0) + 1; }
  const log = readLog(); log.unshift({ t: new Date().toISOString(), profile, dest, values: Object.keys(doc.map).length, types: counts, chars: doc.text.length, leaks: doc.leaks.length });
  store.set("katip-send-log", JSON.stringify(log.slice(0, 200))); renderLog();
}
const MAX_URL = 6000;  // keep links short: very long ?q= links fail on some phones and servers
async function openIn(base, dest) {
  if (doc.leaks.length) return toast(t("leak", { n: doc.leaks.length }));
  const text = outgoing(), q = encodeURIComponent(text);
  logSend(dest);
  if (q.length <= MAX_URL) { window.open(base + q, "_blank", "noopener"); toast(t("opened")); }
  else { await copy(text); window.open(base.replace(/[?&]q=$/, ""), "_blank", "noopener"); toast(t("copiedOpen")); }
}
$("toClaude").onclick = () => openIn("https://claude.ai/new?q=", "claude.ai");
$("toChatgpt").onclick = () => openIn("https://chatgpt.com/?q=", "chatgpt.com");
$("copy").onclick = async () => { if (doc.leaks.length) return toast(t("leak", { n: doc.leaks.length })); await copy(outgoing()); logSend("clipboard"); toast(t("copied")); };
if (navigator.share) {
  $("share").hidden = false;
  $("share").onclick = async () => {
    if (doc.leaks.length) return toast(t("leak", { n: doc.leaks.length }));
    try { await navigator.share({ text: outgoing() }); logSend("share-sheet"); } catch { /* cancelled */ }
  };
}

// ---------------------------------------------------------------- API mode (the user's own key, masked text only)
function apiSetup() {
  const prov = store.get("katip-api-prov") ?? "anthropic";
  $("apiProv").value = prov;
  const k = store.get("katip-api-key-" + prov); $("apiKey").value = k ?? ""; $("apiRemember").checked = !!k;
  $("apiModel").value = store.get("katip-api-model-" + prov) ?? (prov === "anthropic" ? "claude-opus-5-5" : "");
  $("apiModels").replaceChildren(...API_MODELS[prov].map(v => el("option", { value: v })));
  $("apiModel").placeholder = prov === "openai" ? "model id" : "";
}
$("apiProv").onchange = () => { store.set("katip-api-prov", $("apiProv").value); apiSetup(); };
$("apiRemember").onchange = () => store.set("katip-api-key-" + $("apiProv").value, $("apiRemember").checked ? $("apiKey").value : null);
$("apiKey").onchange = () => { if ($("apiRemember").checked) store.set("katip-api-key-" + $("apiProv").value, $("apiKey").value); };
$("apiModel").onchange = () => store.set("katip-api-model-" + $("apiProv").value, $("apiModel").value.trim());
const SYSTEM = "You are assisting a Turkish lawyer. Personal data in the document has been replaced with labels in square brackets such as [AD SOYAD-1] or [T.C. KİMLİK NO-1]. Keep every label exactly as written when you refer to it, never invent or guess the real values, and answer in the language of the question.";
async function askApi() {
  if (doc.leaks.length) return toast(t("leak", { n: doc.leaks.length }));
  const prov = $("apiProv").value, keyv = $("apiKey").value.trim(), model = $("apiModel").value.trim();
  if (!keyv || !model) return toast(t("noKey"));
  const q = $("apiAsk").value.trim() || (lang === "tr" ? "Bu belgeyi özetle." : "Summarise this document.");
  const content = `${q}\n\n<document>\n${doc.text.replace(/\f\n?/g, "\n").trim()}\n</document>`;
  $("apiGo").disabled = true; $("apiGo").textContent = t("asking");
  try {
    let answer;
    if (prov === "anthropic") {
      const r = await fetch("https://api.anthropic.com/v1/messages", { method: "POST",
        headers: { "content-type": "application/json", "x-api-key": keyv, "anthropic-version": "2023-06-01", "anthropic-dangerous-direct-browser-access": "true" },
        body: JSON.stringify({ model, max_tokens: 16000, system: SYSTEM, messages: [{ role: "user", content }] }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error?.message ?? r.status);
      if (j.stop_reason === "refusal") throw new Error(t("refused"));
      answer = j.content.filter(b => b.type === "text").map(b => b.text).join("\n");
    } else {
      const r = await fetch("https://api.openai.com/v1/chat/completions", { method: "POST",
        headers: { "content-type": "application/json", authorization: "Bearer " + keyv },
        body: JSON.stringify({ model, messages: [{ role: "system", content: SYSTEM }, { role: "user", content }] }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error?.message ?? r.status);
      answer = j.choices?.[0]?.message?.content ?? "";
    }
    logSend("api:" + prov + ":" + model);
    $("answer").value = answer; renderRestore(); $("s5").scrollIntoView({ behavior: "smooth" });
  } catch (e) { toast(t("apiErr", { e: e.message ?? e })); }
  finally { $("apiGo").disabled = false; $("apiGo").textContent = t("ask"); }
}
$("apiGo").onclick = askApi;

// ---------------------------------------------------------------- put names back (on this device only)
let restoredText = "";
function renderRestore() {
  const a = $("answer").value, box = $("restored");
  const has = !!(a.trim() && doc?.map);
  box.classList.toggle("hidden", !has); $("copyBack").classList.toggle("hidden", !has); $("dlBack").classList.toggle("hidden", !has);
  if (!has) { restoredText = ""; return; }
  let n = 0;
  const labels = Object.keys(doc.map).sort((x, y) => y.length - x.length);
  restoredText = a;
  for (const lab of labels) { const parts = restoredText.split(lab); n += parts.length - 1; restoredText = parts.join(doc.map[lab]); }
  const unknown = [...new Set(restoredText.match(/\[[^\[\]\n]{1,40}-\d+\]/g) ?? [])];
  box.replaceChildren(el("p", { className: "hint", textContent: t("restoredN", { n }) + (unknown.length ? " " + t("unknown", { l: unknown.join(", ") }) : "") }),
    el("pre", { className: "masked", textContent: restoredText }));
}
$("answer").oninput = renderRestore;
$("copyBack").onclick = async () => { await copy(restoredText); toast(t("copied").split(".")[0] + "."); };
$("dlBack").onclick = () => {
  const a = el("a", { href: URL.createObjectURL(new Blob([restoredText], { type: "text/plain;charset=utf-8" })), download: (doc.name.replace(/\.[^.]+$/, "") || "katip") + ".cevap.txt" });
  a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};

// ---------------------------------------------------------------- on-device record
function readLog() { try { return JSON.parse(store.get("katip-send-log") ?? "[]"); } catch { return []; } }
function renderLog() {
  $("log").replaceChildren(...readLog().map(e => el("li", {}, el("b", { textContent: new Date(e.t).toLocaleString(lang === "tr" ? "tr-TR" : "en-GB") }),
    ` · ${loc(PROFILES[e.profile]?.name)} · ${e.dest} · ${e.values} · ${Object.entries(e.types).map(([k, v]) => `${k} ${v}`).join(", ")}`)));
}
$("logExport").onclick = () => {
  const a = el("a", { href: URL.createObjectURL(new Blob([JSON.stringify(readLog(), null, 1)], { type: "application/json" })), download: "katip-kayit.json" });
  a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};
$("logClear").onclick = () => { store.set("katip-send-log", null); renderLog(); };

// ---------------------------------------------------------------- language
function applyLang() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(e => { e.textContent = t(e.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach(e => { e.placeholder = t(e.dataset.i18nPh); });
  document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  document.title = lang === "tr" ? "Katip · Yapay zekâya gönder" : "Katip · Send to AI";
  renderProfiles(); renderLog(); apiSetup();
  if (!doc) status(ready ? t("ready") : t("loading"));
  else if (doc.map) { render(); renderRestore(); }
}
document.querySelectorAll("[data-lang]").forEach(b => b.onclick = () => { lang = b.dataset.lang; store.set("katip-lang", lang); applyLang(); });
applyLang();
window.__katipSend = () => doc;  // for automated tests
