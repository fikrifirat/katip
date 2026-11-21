// Katip "letter explained" page: a private test of Cebindeki hukuk as a client would use it.
// A Dutch letter (IND, gemeente, Belastingdienst, employer, court) is read and masked on this device, Katip names
// the type and the deadline rule it knows (letters.js, every rule read in the official text), the masked letter goes
// to Claude or ChatGPT for a plain-language explanation, and the page points to people who can help.
// Not linked from the site and marked noindex: this is for testing with our own letters, not a public service.
import Tesseract from "./vendor/tesseract.js/dist/tesseract.esm.min.js";
import { GROUPS } from "./legal.js";
import { TYPES, LAW, HELP, classifyLetter, letterPrompt } from "./letters.js";

const $ = id => document.getElementById(id);
const el = (tag, props = {}, ...kids) => { const e = Object.assign(document.createElement(tag), props); e.append(...kids.filter(k => k != null)); return e; };

// ---------------------------------------------------------------- text (nl / en / tr)
const I18N = {
  nl: {
    tagline: "Brief uitgelegd", badge: "test", trust: "Uw brief wordt op dit apparaat gelezen en gemaskeerd. Naar Claude of ChatGPT gaat alleen de gemaskeerde tekst; namen en nummers blijven in dit tabblad.",
    h1: "Voeg de brief toe", pick: "Kies een bestand of maak een foto", pickSub: "PDF, Word, tekst of foto", orPaste: "of plak de tekst", pastePh: "Plak de tekst van de brief hier", go: "Lezen",
    h2: "Wat voor brief is dit?", h3: "Wat Katip heeft afgeschermd", h4: "Uitleg vragen", h5: "Een mens vragen",
    wrongType: "Klopt dit niet? Kies het juiste soort brief", deadlineH: "Termijn volgens Katip", noDeadline: "Katip noemt voor deze brief geen termijn. Kijk in de brief of er een datum of termijn staat.",
    urgent: "Let op: hier kunnen korte termijnen gelden. Vraag snel hulp.", checkLetter: "Controleer altijd de datum en de bezwaarparagraaf in uw eigen brief. Die gaan voor.", lawH: "Waar staat dit?", cues: "Herkend aan: {c}",
    loading: "Even geduld, Katip wordt geladen (eerste keer ~60 MB)…", ready: "Klaar. Voeg een brief toe.", working: "Bezig met lezen en maskeren…",
    ok: "{n} gegevens afgeschermd. Geen van de gevonden gegevens staat nog in de tekst.", leak: "Let op: {n} gegevens zijn nog zichtbaar. Niet versturen; voeg ze hieronder toe.",
    review: "Katip kan iets missen. Lees de tekst voordat u hem verstuurt.", itemsH: "Afgeschermd", itemsHint: "Tik op iets dat niet afgeschermd hoeft te worden.",
    addPh: "Nog een naam of nummer zichtbaar? Typ het hier", add: "Afschermen",
    askHint: "Katip stuurt de gemaskeerde brief met een vraag om uitleg in eenvoudige taal. Lange teksten worden gekopieerd: plak ze in het chatvenster.",
    toClaude: "Uitleg in Claude", toChatgpt: "Uitleg in ChatGPT", share: "Delen…", copy: "Kopiëren", copied: "Gekopieerd. Plak het in de chat.", opened: "Geopend.", copiedOpen: "Lange tekst: gekopieerd. Plak het in de chat die openging.",
    apiTitle: "Hier vragen met uw eigen API-sleutel", apiHint: "De gemaskeerde tekst gaat vanuit deze browser rechtstreeks naar Anthropic of OpenAI, niet via Katip. API-gebruik wordt apart betaald.",
    keyPh: "API-sleutel (sk-…)", remember: "Onthouden op dit apparaat", ask: "Vraag uitleg", asking: "Bezig…", noKey: "Vul eerst een API-sleutel en model in.", apiErr: "API-fout: {e}", refused: "Het model gaf geen antwoord op deze vraag.",
    answerH: "Antwoord", answerPh: "Plak hier het antwoord; labels zoals [NAAM-1] worden weer de echte namen.", restoredN: "{n} labels teruggezet.",
    helpHint: "Twijfelt u, of staat er een termijn? Vraag een mens. Deze organisaties helpen, sommige gratis.", helpTr: "Bel het adli yardım-bureau (rechtsbijstand) van uw balie, of een advocaat.",
    notesTitle: "Testnotities (alleen op dit apparaat)", notesHint: "Per brief: welk soort Katip herkende, of u het verbeterde, hoeveel gegevens werden afgeschermd en waar u het heen stuurde. Geen tekst of namen.",
    export: "Exporteren", clear: "Wissen", notAdvice: "Katip geeft geen juridisch advies. Dit is een test.", forLawyers: "Voor advocaten: naar AI sturen", privacy: "Privacy", err: "Fout: {e}",
    otherLang: "Deze brief lijkt Turks. Katip maskeert hem met de Turkse modellen; het soort brief wordt (nog) niet herkend.",
  },
  en: {
    tagline: "Letter explained", badge: "test", trust: "Your letter is read and masked on this device. Claude or ChatGPT only get the masked text; names and numbers stay in this tab.",
    h1: "Add the letter", pick: "Choose a file or take a photo", pickSub: "PDF, Word, text or photo", orPaste: "or paste the text", pastePh: "Paste the letter's text here", go: "Read",
    h2: "What kind of letter is this?", h3: "What Katip hid", h4: "Ask for an explanation", h5: "Ask a person",
    wrongType: "Not right? Pick the right kind of letter", deadlineH: "Deadline according to Katip", noDeadline: "Katip names no deadline for this letter. Look in the letter for a date or term.",
    urgent: "Careful: short deadlines can apply here. Get help soon.", checkLetter: "Always check the date and the objection paragraph in your own letter. They come first.", lawH: "Where does this come from?", cues: "Recognised by: {c}",
    loading: "Please wait, Katip is loading (first time ~60 MB)…", ready: "Ready. Add a letter.", working: "Reading and masking…",
    ok: "{n} details hidden. None of the details found is left in the text.", leak: "Careful: {n} details are still visible. Don't send; add them below.",
    review: "Katip can miss something. Read the text before you send it.", itemsH: "Hidden", itemsHint: "Tap anything that doesn't need hiding.",
    addPh: "A name or number still visible? Type it here", add: "Hide",
    askHint: "Katip sends the masked letter with a request for a plain-language explanation. Long texts are copied: paste them into the chat.",
    toClaude: "Explain in Claude", toChatgpt: "Explain in ChatGPT", share: "Share…", copy: "Copy", copied: "Copied. Paste it into the chat.", opened: "Opened.", copiedOpen: "Long text: copied. Paste it into the chat that opened.",
    apiTitle: "Ask here with your own API key", apiHint: "The masked text goes from this browser straight to Anthropic or OpenAI, never through Katip. API use is billed separately.",
    keyPh: "API key (sk-…)", remember: "Remember on this device", ask: "Explain", asking: "Asking…", noKey: "Enter an API key and model first.", apiErr: "API error: {e}", refused: "The model declined this request.",
    answerH: "Answer", answerPh: "Paste the answer here; labels like [NAAM-1] turn back into the real names.", restoredN: "{n} labels put back.",
    helpHint: "In doubt, or is there a deadline? Ask a person. These organisations help, some for free.", helpTr: "Call your bar association's legal aid office (adli yardım), or a lawyer.",
    notesTitle: "Test notes (on this device only)", notesHint: "Per letter: which type Katip named, whether you corrected it, how many details were hidden and where you sent it. No text or names.",
    export: "Export", clear: "Clear", notAdvice: "Katip does not give legal advice. This is a test.", forLawyers: "For lawyers: send to AI", privacy: "Privacy", err: "Error: {e}",
    otherLang: "This letter looks Turkish. Katip masks it with the Turkish models; the letter type isn't recognised (yet).",
  },
  tr: {
    tagline: "Mektup açıklaması", badge: "test", trust: "Mektubunuz bu cihazda okunur ve maskelenir. Claude'a veya ChatGPT'ye yalnızca maskeli metin gider; isimler ve numaralar bu sekmede kalır.",
    h1: "Mektubu ekleyin", pick: "Dosya seçin veya fotoğraf çekin", pickSub: "PDF, Word, metin veya fotoğraf", orPaste: "ya da metni yapıştırın", pastePh: "Mektubun metnini buraya yapıştırın", go: "Oku",
    h2: "Bu nasıl bir mektup?", h3: "Katip'in gizledikleri", h4: "Açıklama isteyin", h5: "Bir insana sorun",
    wrongType: "Doğru değil mi? Doğru türü seçin", deadlineH: "Katip'e göre süre", noDeadline: "Katip bu mektup için süre belirtmiyor. Mektupta bir tarih veya süre olup olmadığına bakın.",
    urgent: "Dikkat: burada kısa süreler geçerli olabilir. Hemen yardım alın.", checkLetter: "Her zaman kendi mektubunuzdaki tarihi ve itiraz (bezwaar) paragrafını kontrol edin. Onlar esastır.", lawH: "Dayanağı nedir?", cues: "Tanındığı ifadeler: {c}",
    loading: "Bekleyin, Katip yükleniyor (ilk seferde ~60 MB)…", ready: "Hazır. Bir mektup ekleyin.", working: "Okunuyor ve maskeleniyor…",
    ok: "{n} bilgi gizlendi. Bulunan bilgilerin hiçbiri metinde kalmadı.", leak: "Dikkat: {n} bilgi hâlâ görünüyor. Göndermeyin; aşağıdan ekleyin.",
    review: "Katip bir şey kaçırabilir. Göndermeden önce metni okuyun.", itemsH: "Gizlenenler", itemsHint: "Gizlenmesi gerekmeyen bir şeye dokunun.",
    addPh: "Hâlâ görünen bir isim veya numara mı var? Yazın", add: "Gizle",
    askHint: "Katip maskeli mektubu, sade dille açıklama isteğiyle gönderir. Uzun metinler kopyalanır: sohbet kutusuna yapıştırın.",
    toClaude: "Claude'da açıkla", toChatgpt: "ChatGPT'de açıkla", share: "Paylaş…", copy: "Kopyala", copied: "Kopyalandı. Sohbete yapıştırın.", opened: "Açıldı.", copiedOpen: "Metin uzun: kopyalandı. Açılan sohbete yapıştırın.",
    apiTitle: "Kendi API anahtarınızla burada sorun", apiHint: "Maskeli metin bu tarayıcıdan doğrudan Anthropic'e veya OpenAI'a gider; Katip'e uğramaz. API kullanımı ayrıca ücretlendirilir.",
    keyPh: "API anahtarı (sk-…)", remember: "Bu cihazda hatırla", ask: "Açıkla", asking: "Soruluyor…", noKey: "Önce API anahtarını ve modeli girin.", apiErr: "API hatası: {e}", refused: "Model bu isteği yanıtlamadı.",
    answerH: "Cevap", answerPh: "Cevabı buraya yapıştırın; [NAAM-1] gibi etiketler gerçek isimlere döner.", restoredN: "{n} etiket geri kondu.",
    helpHint: "Emin değilseniz veya bir süre varsa bir insana sorun. Bu kuruluşlar yardım eder, bazıları ücretsiz.", helpTr: "Baronuzun adli yardım bürosunu veya bir avukatı arayın.",
    notesTitle: "Test notları (yalnızca bu cihazda)", notesHint: "Her mektup için: Katip'in bulduğu tür, düzeltip düzeltmediğiniz, kaç bilginin gizlendiği ve nereye gönderildiği. Metin veya isim kaydedilmez.",
    export: "Dışa aktar", clear: "Temizle", notAdvice: "Katip hukuki danışmanlık vermez. Bu bir testtir.", forLawyers: "Avukatlar için: yapay zekâya gönder", privacy: "Gizlilik", err: "Hata: {e}",
    otherLang: "Bu mektup Türkçe görünüyor. Katip Türkçe modellerle maskeler; mektup türü (henüz) tanınmıyor.",
  },
};

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* storage blocked */ } },
};
const LANGS = ["nl", "en", "tr"];
let lang = (() => {
  const q = new URLSearchParams(location.search).get("lang"); if (LANGS.includes(q)) return q;
  const s = store.get("katip-cep-lang"); if (LANGS.includes(s)) return s;
  const n = (navigator.language || "nl").toLowerCase();
  return n.startsWith("tr") ? "tr" : n.startsWith("nl") ? "nl" : "en";
})();
const t = (k, v = {}) => (I18N[lang][k] ?? I18N.en[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => v[x] ?? "");
const loc = o => o?.[lang] ?? o?.en ?? "";

// ---------------------------------------------------------------- labels
let NL = {};  // entity -> { tag, nl, en, tr } from katip_nl/labels.py (built into katip_nl_labels.json)
fetch("katip_nl_labels.json").then(r => r.json()).then(j => { NL = j; }).catch(() => {});
const TR_NAMES = { PERSON: "Ad soyad / Name", TCKN: "T.C. Kimlik No", YKN: "Yabancı kimlik no", ADDRESS: "Adres / Address", PHONE: "Telefon / Phone", EMAIL: "E-posta", IBAN: "IBAN" };
const labelOf = typ => doc?.lang === "nl" && NL[typ] ? (lang === "en" ? NL[typ].en : `${NL[typ][lang]} / ${NL[typ].en}`) : TR_NAMES[typ] ?? typ;
const tagsFor = l => l === "nl" ? Object.fromEntries(Object.entries(NL).map(([k, v]) => [k, v.tag])) : null;
// Turkish letters: everything personal, but dates, places and institutions stay readable (the reader needs them)
const TR_TYPES = GROUPS.flatMap(g => g.types).filter(x => !["DATE", "PLACE", "INSTITUTION"].includes(x)).concat("CUSTOM");

// ---------------------------------------------------------------- state
let ready = false, seq = 0, doc = null;  // doc: { name, text0, lang, spans, off:Set, mask:[], type, auto, why, text, map, leaks, sent:[] }
const key = s => `${s.start}:${s.end}:${s.entity_type}`;

// ---------------------------------------------------------------- worker (same engine as the full app)
const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
let alive = false, pending = null; const outbox = [];
const post = (m, tr = []) => alive ? worker.postMessage(m, tr) : outbox.push([m, tr]);
const tess = {};
// Only Turkish Tesseract data ships with the site; it reads Dutch print well enough (same Latin script), but
// photos of Dutch letters are less reliable than PDFs or pasted text.
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
  docLang: "auto", entities: TR_TYPES, mask: doc?.mask ?? [] });

worker.onmessage = async ({ data: m }) => {
  if (m.type === "alive") { alive = true; for (const [x, tr] of outbox.splice(0)) worker.postMessage(x, tr); return; }
  if (m.type === "ready") { ready = true; if (pending) { post(...pending); pending = null; status(t("working")); } else if (!doc) status(t("ready")); return; }
  if (m.type === "progress") return status(m.msg + "…");
  if (m.type === "ocr") {
    try { worker.postMessage({ type: "ocrResult", id: m.id, lines: await ocr(m.png, m.lang) }); }
    catch (e) { worker.postMessage({ type: "ocrResult", id: m.id, error: String(e) }); }
    return;
  }
  if (m.type === "analyzed") {
    if (m.seq !== seq) return;
    Object.assign(doc, { text0: m.text, lang: m.lang ?? "tr", spans: m.spans });
    const c = doc.lang === "nl" ? classifyLetter(m.text) : { type: "other", why: [] };
    Object.assign(doc, { type: c.type, auto: c.type, why: c.why });
    renderKind(); return remask();
  }
  if (m.type === "redetected") { doc.spans = m.spans; return remask(); }
  if (m.type === "maskMap") { Object.assign(doc, { text: m.text, map: m.map, leaks: m.leaks }); status(""); return render(); }
  if (m.type === "error") status(t("err", { e: m.msg }), true);
};

async function open(name, bytes) {
  doc = { id: "cep-" + Date.now().toString(36), name, spans: null, off: new Set(), mask: [], sent: [] };
  ["s2", "s3", "s4", "s5"].forEach(id => $(id).classList.add("hidden"));
  $("answer").value = ""; renderRestore();
  status(ready ? t("working") : t("loading"));
  const msg = [{ type: "analyze", name, bytes, settings: settings(), seq: ++seq }, [bytes.buffer]];
  if (ready) post(...msg); else pending = msg;
}
$("file").onchange = async e => { const f = e.target.files[0]; if (f) open(f.name, new Uint8Array(await f.arrayBuffer())); e.target.value = ""; };
$("pasteGo").onclick = () => { const s = $("paste").value.trim(); if (s) open("brief.txt", new TextEncoder().encode(s)); };

const isOn = s => !doc.off.has(key(s));
const remask = () => post({ type: "maskMap", spans: doc.spans.filter(isOn), tags: tagsFor(doc.lang) });

// ---------------------------------------------------------------- render
function status(msg, bad = false) { $("status").textContent = msg; $("status").classList.toggle("bad", bad); }

function renderKind() {
  if (!doc?.type) return;
  $("s2").classList.remove("hidden");
  const T = TYPES[doc.type];
  const both = o => lang === "en" ? [loc(o)] : [loc(o), o.en];
  const [name, nameEn] = both(T.name);
  const box = [el("p", { className: "kind" }, name, nameEn ? el("small", { textContent: nameEn }) : null), el("p", { textContent: loc(T.what) })];
  if (doc.lang === "tr") box.push(el("p", { className: "hint", textContent: t("otherLang") }));
  if (doc.lang === "nl") {
    const dl = T.deadline ? both(T.deadline) : null;
    box.push(el("div", { className: "deadline" + (T.urgent ? " urgent" : "") }, el("b", { textContent: t("deadlineH") }),
      el("span", { textContent: dl ? dl[0] : t("noDeadline") }), dl?.[1] ? el("div", { className: "en", textContent: dl[1] }) : null,
      T.urgent ? el("div", { textContent: t("urgent") }) : null,
      el("div", { className: "hint", textContent: t("checkLetter") })));
    if (T.law.length) box.push(el("details", {}, el("summary", { textContent: t("lawH") }), el("ul", { className: "law" },
      ...T.law.map(k => el("li", {}, el("a", { href: LAW[k].url, target: "_blank", rel: "noopener", textContent: LAW[k].ref }), el("blockquote", { textContent: LAW[k].quote }))))));
    if (doc.why.length && doc.type === doc.auto) box.push(el("p", { className: "cues", textContent: t("cues", { c: doc.why.join(", ") }) }));
  }
  $("kind").replaceChildren(...box);
  $("typeFix").classList.toggle("hidden", doc.lang !== "nl");
  $("typeSel").replaceChildren(...Object.entries(TYPES).map(([k, v]) => el("option", { value: k, textContent: loc(v.name), selected: k === doc.type })));
  renderHelp();
}
$("typeSel").onchange = () => { doc.type = $("typeSel").value; renderKind(); note(); };

function render() {
  ["s3", "s4", "s5"].forEach(id => $(id).classList.remove("hidden"));
  const n = Object.keys(doc.map).length;
  $("check").replaceChildren(
    el("p", { className: doc.leaks.length ? "verdict bad" : "verdict good", textContent: doc.leaks.length ? t("leak", { n: doc.leaks.length }) : t("ok", { n }) }),
    el("p", { className: "hint", textContent: t("review") }));
  const seen = new Map();
  for (const s of doc.spans) { const k = s.entity_type + "|" + s.text.toLowerCase(); if (!seen.has(k)) seen.set(k, s); }
  const openList = $("items").querySelector("details")?.open ?? false;
  $("items").replaceChildren(el("details", { open: openList }, el("summary", {}, el("b", { textContent: `${t("itemsH")} (${n})` })),
    el("p", { className: "hint", textContent: t("itemsHint") }),
    el("div", { className: "chips" }, ...[...seen.values()].map(s => {
      const on = isOn(s), same = doc.spans.filter(x => x.entity_type === s.entity_type && x.text.toLowerCase() === s.text.toLowerCase());
      return el("button", { className: on ? "on" : "off", onclick: () => { for (const x of same) on ? doc.off.add(key(x)) : doc.off.delete(key(x)); remask(); } },
        el("small", { textContent: labelOf(s.entity_type) }), " ", s.text.length > 40 ? s.text.slice(0, 38) + "…" : s.text);
    }))));
  const pre = $("masked"); pre.textContent = "";
  const txt = doc.text.replace(/\f\n?/g, "\n"), re = /\[[^\[\]\n]{1,40}-\d+\]/g;
  let pos = 0, m;
  while ((m = re.exec(txt))) { pre.append(txt.slice(pos, m.index), el("mark", { textContent: m[0] })); pos = m.index + m[0].length; }
  pre.append(txt.slice(pos));
  note();
}
$("addGo").onclick = () => {
  const v = $("addTerm").value.trim(); if (!v || !doc?.spans) return;
  doc.mask.push(v); $("addTerm").value = ""; status(t("working"));
  post({ type: "redetect", settings: settings() });
};
$("addTerm").onkeydown = e => { if (e.key === "Enter") $("addGo").click(); };

function renderHelp() {
  const list = doc?.lang === "nl" ? HELP.nl : [];
  $("help").replaceChildren(...list.map(h => el("div", {}, el("a", { href: h.url, target: "_blank", rel: "noopener", textContent: h.name }), el("span", { textContent: loc(h.what) }))),
    ...(doc?.lang === "nl" ? [] : [el("p", { textContent: t("helpTr") })]));
}

// ---------------------------------------------------------------- the question sent with the masked letter
const prompt = () => letterPrompt({ type: doc.type, docLang: doc.lang, answerLang: lang, masked: doc.text });

// ---------------------------------------------------------------- send
function toast(msg) { const e = $("toast"); e.textContent = msg; e.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(() => { e.hidden = true; }, 3500); }
async function copy(text) { try { await navigator.clipboard.writeText(text); return true; } catch { return false; } }
const MAX_URL = 6000;
function sent(dest) { if (!doc.sent.includes(dest)) doc.sent.push(dest); note(); }
async function openIn(base, dest) {
  if (doc.leaks.length) return toast(t("leak", { n: doc.leaks.length }));
  const text = prompt(), q = encodeURIComponent(text);
  sent(dest);
  if (q.length <= MAX_URL) { window.open(base + q, "_blank", "noopener"); toast(t("opened")); }
  else { await copy(text); window.open(base.replace(/[?&]q=$/, ""), "_blank", "noopener"); toast(t("copiedOpen")); }
}
$("toClaude").onclick = () => openIn("https://claude.ai/new?q=", "claude.ai");
$("toChatgpt").onclick = () => openIn("https://chatgpt.com/?q=", "chatgpt.com");
$("copy").onclick = async () => { if (doc.leaks.length) return toast(t("leak", { n: doc.leaks.length })); await copy(prompt()); sent("clipboard"); toast(t("copied")); };
if (navigator.share) {
  $("share").hidden = false;
  $("share").onclick = async () => {
    if (doc.leaks.length) return toast(t("leak", { n: doc.leaks.length }));
    try { await navigator.share({ text: prompt() }); sent("share-sheet"); } catch { /* cancelled */ }
  };
}

// own API key (same rules as gonder.html: masked text only, straight to the provider)
function apiSetup() {
  const prov = store.get("katip-api-prov") ?? "anthropic";
  $("apiProv").value = prov;
  const k = store.get("katip-api-key-" + prov); $("apiKey").value = k ?? ""; $("apiRemember").checked = !!k;
  $("apiModel").value = store.get("katip-api-model-" + prov) ?? (prov === "anthropic" ? "claude-sonnet-5-5" : "");
  $("apiModel").placeholder = "model id";
}
$("apiProv").onchange = () => { store.set("katip-api-prov", $("apiProv").value); apiSetup(); };
$("apiRemember").onchange = () => store.set("katip-api-key-" + $("apiProv").value, $("apiRemember").checked ? $("apiKey").value : null);
$("apiKey").onchange = () => { if ($("apiRemember").checked) store.set("katip-api-key-" + $("apiProv").value, $("apiKey").value); };
$("apiModel").onchange = () => store.set("katip-api-model-" + $("apiProv").value, $("apiModel").value.trim());
$("apiGo").onclick = async () => {
  if (doc.leaks.length) return toast(t("leak", { n: doc.leaks.length }));
  const prov = $("apiProv").value, keyv = $("apiKey").value.trim(), model = $("apiModel").value.trim();
  if (!keyv || !model) return toast(t("noKey"));
  $("apiGo").disabled = true; $("apiGo").textContent = t("asking");
  try {
    let answer;
    if (prov === "anthropic") {
      const r = await fetch("https://api.anthropic.com/v1/messages", { method: "POST",
        headers: { "content-type": "application/json", "x-api-key": keyv, "anthropic-version": "2023-06-01", "anthropic-dangerous-direct-browser-access": "true" },
        body: JSON.stringify({ model, max_tokens: 4000, messages: [{ role: "user", content: prompt() }] }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error?.message ?? r.status);
      if (j.stop_reason === "refusal") throw new Error(t("refused"));
      answer = j.content.filter(b => b.type === "text").map(b => b.text).join("\n");
    } else {
      const r = await fetch("https://api.openai.com/v1/chat/completions", { method: "POST",
        headers: { "content-type": "application/json", authorization: "Bearer " + keyv },
        body: JSON.stringify({ model, messages: [{ role: "user", content: prompt() }] }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error?.message ?? r.status);
      answer = j.choices?.[0]?.message?.content ?? "";
    }
    sent("api:" + prov);
    $("answer").value = answer; renderRestore();
  } catch (e) { toast(t("apiErr", { e: e.message ?? e })); }
  finally { $("apiGo").disabled = false; $("apiGo").textContent = t("ask"); }
};

// put the names back in the answer, on this device only
function renderRestore() {
  const a = $("answer").value, box = $("restored"), has = !!(a.trim() && doc?.map);
  box.classList.toggle("hidden", !has);
  if (!has) return;
  let n = 0, out = a;
  for (const lab of Object.keys(doc.map).sort((x, y) => y.length - x.length)) { const parts = out.split(lab); n += parts.length - 1; out = parts.join(doc.map[lab]); }
  box.replaceChildren(el("p", { className: "hint", textContent: t("restoredN", { n }) }), el("pre", { className: "masked", textContent: out }));
}
$("answer").oninput = renderRestore;

// ---------------------------------------------------------------- test notes: counts and choices only, never text
function readLog() { try { return JSON.parse(store.get("katip-cep-notes") ?? "[]"); } catch { return []; } }
function note() {
  if (!doc?.type) return;
  const types = {}; for (const s of doc.spans ?? []) if (isOn(s)) types[s.entity_type] = (types[s.entity_type] ?? 0) + 1;
  const rec = { id: doc.id, t: new Date().toISOString(), lang: doc.lang, katip_type: doc.auto, your_type: doc.type, cues: doc.why,
    hidden: types, unmasked: doc.off.size, added: doc.mask.length, leaks: doc.leaks?.length ?? 0, sent: doc.sent };
  const log = readLog().filter(r => r.id !== doc.id); log.unshift(rec);
  store.set("katip-cep-notes", JSON.stringify(log.slice(0, 200))); renderLog();
}
function renderLog() {
  $("log").replaceChildren(...readLog().slice(0, 30).map(r => el("li", { textContent:
    `${r.t.slice(0, 16).replace("T", " ")} · ${r.lang} · ${r.katip_type}${r.your_type !== r.katip_type ? " → " + r.your_type : ""} · ${Object.values(r.hidden).reduce((a, b) => a + b, 0)} · ${r.sent.join(", ") || "-"}` })));
}
$("logExport").onclick = () => {
  const a = el("a", { href: URL.createObjectURL(new Blob([JSON.stringify({ format: "katip-cep-notes/1", notes: readLog() }, null, 1)], { type: "application/json" })), download: "katip-cep-notes.json" });
  a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};
$("logClear").onclick = () => { store.set("katip-cep-notes", null); renderLog(); };

// ---------------------------------------------------------------- language
function applyLang() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(e => { e.textContent = t(e.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach(e => { e.placeholder = t(e.dataset.i18nPh); });
  document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  document.title = "Katip · " + t("tagline");
  apiSetup(); renderLog();
  if (!doc) status(ready ? t("ready") : t("loading"));
  else { renderKind(); if (doc.map) { render(); renderRestore(); } }
}
document.querySelectorAll("[data-lang]").forEach(b => b.onclick = () => { lang = b.dataset.lang; store.set("katip-cep-lang", lang); applyLang(); });
applyLang();
window.__katipCep = () => doc;  // for automated tests
