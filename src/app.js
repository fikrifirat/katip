import Tesseract from "./vendor/tesseract.js/dist/tesseract.esm.min.js";
import CONFIG from "./config.js";
const $ = id => document.getElementById(id);
const el = (tag, props = {}, ...kids) => { const e = Object.assign(document.createElement(tag), props); e.append(...kids); return e; };
const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
const DEV = new URLSearchParams(location.search).has("dev");

const LABEL = { TCKN: "T.C. Kimlik No", VKN: "Vergi Kimlik No", IBAN: "IBAN", CREDIT_CARD: "Kredi kartı", PHONE: "Telefon", EMAIL: "E-posta",
  PLATE: "Araç plakası", PERSON: "Ad soyad", ADDRESS: "Adres", BIRTH_DATE: "Doğum tarihi", IP_ADDRESS: "IP adresi", HEALTH: "Sağlık",
  RELIGION: "Din/inanç", POLITICAL: "Siyasi görüş", UNION: "Sendika", ETHNICITY: "Etnik köken", SEXUAL_LIFE: "Cinsel hayat",
  BIOMETRIC_GENETIC: "Biyometrik/genetik", CRIMINAL_RECORD: "Ceza mahkumiyeti" };
const ART6 = ["HEALTH", "RELIGION", "POLITICAL", "UNION", "ETHNICITY", "SEXUAL_LIFE", "BIOMETRIC_GENETIC", "CRIMINAL_RECORD"];
const FORMAT_LABEL = { txt: "Metin", docx: "Word", udf: "UYAP .udf", pdf: "PDF", "scan.pdf": "Taranmış PDF", png: "Fotoğraf" };

let ready = false, samples = [], models = [], version = {};
let src = { mode: "sample", sample: null, format: "pdf", file: null };
let res = null; window.__katip = () => res;  // for automated tests          // {name, kind, text, spans, previews, gold, timing, ...}
let off = new Set(), maskTerms = [], page = 0, outBlob = null, outName = "", reportWhat = "";

// ---------------------------------------------------------------- network watch
let docOpenedAt = Infinity, netCount = 0;
const runtimeFile = u => /\/(vendor|models|samples)\/|katip_py\.zip|\.(m?js|css|wasm)(\?|$)/.test(u);
new PerformanceObserver(list => {
  for (const e of list.getEntries()) if (e.startTime >= docOpenedAt && !runtimeFile(e.name)) netCount++;
  $("netCount").textContent = netCount; $("netPill").classList.toggle("bad", netCount > 0);
}).observe({ type: "resource", buffered: true });

// ---------------------------------------------------------------- OCR (tesseract.js runs its own worker)
const tess = {};
function getTess(lang) {
  return tess[lang] ??= Tesseract.createWorker("tur", 1, {
    workerPath: new URL("./vendor/tesseract.js/dist/worker.min.js", location.href).href,
    corePath: new URL("./vendor/tesseract.js-core/", location.href).href,
    langPath: new URL(`./vendor/tessdata/${lang}`, location.href).href,
    gzip: true, cacheMethod: "none", workerBlobURL: false,
  });
}
async function ocr(png, lang) {
  const { data } = await (await getTess(lang)).recognize(new Blob([png]), {}, { blocks: true });
  const lines = [];
  for (const b of data.blocks ?? []) for (const p of b.paragraphs) for (const l of p.lines)
    lines.push(l.words.filter(w => w.text.trim() && w.confidence >= 0).map(w => ({ text: w.text, bbox: [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1] })));
  return lines.filter(l => l.length);
}

// ---------------------------------------------------------------- settings
function settings() {
  const m = models.find(x => x.id === $("engine").value) ?? models[0];
  return {
    engine: m?.id, engineName: m?.name, ner: m?.ner ?? null, nerDtype: m?.dtype ?? "q8", ocrLang: $("ocrLang").value,
    threshold: Number($("threshold").value), style: $("style").value,
    entities: [...document.querySelectorAll("#entities input:checked")].map(i => i.value), mask: maskTerms,
  };
}
function buildSettingsUI() {
  for (const m of models.filter(m => !m.dev || DEV)) $("engine").append(el("option", { value: m.id, textContent: m.name, disabled: !!m.disabled }));
  const showInfo = () => { const m = models.find(x => x.id === $("engine").value); $("engineInfo").textContent = m ? m.info : ""; };
  $("engine").onchange = showInfo; showInfo();
  for (const [k, v] of Object.entries(LABEL)) {
    const cb = el("input", { type: "checkbox", value: k, checked: k !== "CRIMINAL_RECORD" });
    cb.onchange = entCount;
    $("entities").append(el("label", {}, cb, " " + v + (ART6.includes(k) ? " ·6" : "")));
  }
  entCount();
  $("threshold").oninput = () => ($("thresholdVal").textContent = Number($("threshold").value).toFixed(2));
}
function entCount() { const n = document.querySelectorAll("#entities input:checked").length; $("entCount").textContent = `(${n}/${Object.keys(LABEL).length})`; }

// ---------------------------------------------------------------- sources
function buildSampleUI() {
  for (const s of samples) $("sampleType").append(el("option", { value: s.id, textContent: s.title }));
  $("sampleType").onchange = () => { src.sample = samples.find(s => s.id === $("sampleType").value); drawFormats(); };
  src.sample = samples[0]; drawFormats();
  $("srcSampleBtn").onclick = () => setMode("sample");
  $("srcFileBtn").onclick = () => setMode("file");
}
function drawFormats() {
  const f = $("formatBtns"); f.textContent = "";
  if (!src.sample.formats.includes(src.format)) src.format = src.sample.formats[0];
  for (const fmt of src.sample.formats) {
    const b = el("button", { type: "button", textContent: FORMAT_LABEL[fmt] ?? fmt });
    b.setAttribute("aria-pressed", fmt === src.format);
    b.onclick = () => { src.format = fmt; drawFormats(); };
    f.append(b);
  }
}
function setMode(m) {
  src.mode = m;
  $("srcSampleBtn").setAttribute("aria-selected", m === "sample"); $("srcFileBtn").setAttribute("aria-selected", m === "file");
  $("srcSample").classList.toggle("hidden", m !== "sample"); $("srcFile").classList.toggle("hidden", m !== "file");
  updateRun();
}
function updateRun() {
  const can = ready && (src.mode === "sample" || src.file);
  $("run").disabled = !can; $("run").textContent = ready ? "Maskele" : "Motor yükleniyor…";
}
function pickFile(f) { if (!f) return; src.file = f; $("fileName").textContent = f.name; setMode("file"); }
$("drop").onclick = () => $("file").click();
$("drop").onkeydown = e => (e.key === "Enter" || e.key === " ") && $("file").click();
$("file").onchange = e => { pickFile(e.target.files[0]); e.target.value = ""; };
$("drop").ondragover = e => { e.preventDefault(); $("drop").classList.add("over"); };
$("drop").ondragleave = () => $("drop").classList.remove("over");
$("drop").ondrop = e => { e.preventDefault(); $("drop").classList.remove("over"); pickFile(e.dataTransfer.files[0]); };

// ---------------------------------------------------------------- run
const status = m => ($("status").textContent = m);
async function run() {
  const s = settings(); let name, bytes, gold = null, isSample = src.mode === "sample";
  $("run").disabled = true; status("Hazırlanıyor…");
  if (isSample) {
    name = `${src.sample.id}.${src.format}`;
    bytes = new Uint8Array(await (await fetch(`samples/${name}`)).arrayBuffer());
    gold = src.sample.gold;
  } else { name = src.file.name; bytes = new Uint8Array(await src.file.arrayBuffer()); }
  docOpenedAt = performance.now(); netCount = 0; $("netCount").textContent = "0"; $("netPill").classList.remove("bad");
  res = { name, isSample, gold, settings: s, imageUrl: null, maskUrl: null };
  if (/\.(png|jpe?g|tiff?|bmp|webp)$/i.test(name)) res.imageUrl = URL.createObjectURL(new Blob([bytes]));
  off = new Set(); page = 0;
  worker.postMessage({ type: "analyze", name, bytes, settings: s }, [bytes.buffer]);
}
function redactNow() { status("Maskeleniyor…"); worker.postMessage({ type: "redact", spans: chosen(), style: res.settings.style, verifyOcr: true, ocrLang: res.settings.ocrLang }); }
$("run").onclick = run;
$("rerun").onclick = () => res && redactNow();
$("addTerm").onclick = () => { const t = $("term").value.trim(); if (!t || !res) return; maskTerms.push(t); $("term").value = ""; res.settings = settings(); worker.postMessage({ type: "redetect", settings: res.settings }); };
$("term").onkeydown = e => e.key === "Enter" && $("addTerm").click();

worker.onmessage = async ({ data: m }) => {
  if (m.type === "ready") {
    ready = true; status(`Motor hazır (${(m.ms / 1000).toFixed(1)} sn).`); updateRun();
    getTess("best_int");
  } else if (m.type === "progress") status(m.msg + "…");
  else if (m.type === "ocr") {
    try { worker.postMessage({ type: "ocrResult", id: m.id, lines: await ocr(m.png, m.lang) }); }
    catch (e) { worker.postMessage({ type: "ocrResult", id: m.id, error: String(e) }); }
  } else if (m.type === "analyzed") {
    Object.assign(res, { kind: m.kind, text: m.text, spans: m.spans, pages: m.pages, ocrPages: m.ocrPages, timing: m.timing, nerCount: m.nerCount,
      origPreviews: m.previews.map(p => URL.createObjectURL(new Blob([p], { type: "image/png" }))) });
    off = new Set(m.spans.filter(s => s.flag_only || !res.settings.entities.includes(s.entity_type)).map(key));
    redactNow();
  } else if (m.type === "redetected") {
    res.spans = m.spans; Object.assign(res.timing, m.timing); off = new Set(m.spans.filter(s => s.flag_only).map(key)); redactNow();
  } else if (m.type === "redacted") {
    outBlob = new Blob([m.out], { type: m.mime }); outName = m.outName;
    Object.assign(res, { outText: m.outText, leaks: m.leaks, unchecked: m.unchecked, redactMs: m.ms,
      maskPreviews: m.previews.map(p => URL.createObjectURL(new Blob([p], { type: "image/png" }))) });
    if (res.kind === "image") res.maskUrl = URL.createObjectURL(outBlob);
    res.eval = res.gold ? goldEval(res.text, chosen(), res.gold) : null;
    status(`Bitti: ${chosen().length} değer maskelendi.`); $("run").disabled = false; $("reportBtn").disabled = false;
    render();
  } else if (m.type === "maskedText") { await navigator.clipboard.writeText(m.text); status("Etiketli metin panoya kopyalandı."); }
  else if (m.type === "original") { pendingOriginal?.(m); }
  else if (m.type === "forgotten") { res = null; outBlob = null; $("empty").hidden = false; document.querySelectorAll(".panel").forEach(p => (p.hidden = true)); $("reportBtn").disabled = true; status("Belge bellekten silindi."); }
  else if (m.type === "error") { status("Hata: " + m.msg); $("run").disabled = false; console.error(m.msg, m.stack); }
};

// ---------------------------------------------------------------- scoring against gold (sample documents)
const sq = s => s.replace(/\s+/g, "").toLocaleLowerCase("tr");
const matches = (a, b) => { const x = sq(a), y = sq(b); return x.includes(y) || (y.includes(x) && x.length >= Math.max(3, y.length * 0.5)); };
function goldEval(text, spans, gold) {
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
document.querySelectorAll(".tabs [role=tab]").forEach(b => (b.onclick = () => showTab(b.dataset.tab)));
let tab = "compare";
function showTab(t) {
  tab = t;
  document.querySelectorAll(".tabs [role=tab]").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === t));
  document.querySelectorAll(".panel").forEach(p => (p.hidden = !res || p.id !== "p-" + t));
  $("empty").hidden = !!res;
}
function render() {
  showTab(tab);
  $("countBadge").textContent = `(${chosen().length})`;
  $("goldTabBtn").classList.toggle("hidden", !res.gold);
  if (!res.gold && tab === "gold") showTab("compare");
  renderCompare(); renderList(); renderGold(); renderOut();
}
function renderCompare() {
  const imgPages = res.kind === "pdf" ? res.origPreviews.length : 0;
  $("pager").classList.toggle("hidden", imgPages < 2);
  page = Math.min(page, Math.max(0, imgPages - 1));
  $("pageLbl").textContent = `Sayfa ${page + 1} / ${res.pages}`;
  const O = $("origView"), M = $("maskView"); O.textContent = ""; M.textContent = "";
  const imgView = res.kind === "pdf" || res.kind === "image";
  O.classList.toggle("img", imgView); M.classList.toggle("img", imgView);
  $("legend").textContent = "";
  if (res.gold) $("legend").append(el("i", { style: "background:var(--ok)", textContent: "doğru" }), el("i", { style: "background:var(--fp)", textContent: "fazla" }), el("i", { style: "text-decoration:underline wavy var(--miss)", textContent: "kaçan" }));
  if (res.kind === "pdf") {
    O.append(el("img", { src: res.origPreviews[page], alt: "Orijinal sayfa" }));
    if (res.maskPreviews[page]) M.append(el("img", { src: res.maskPreviews[page], alt: "Maskeli sayfa" }));
    O.append(el("details", {}, el("summary", { textContent: "Okunan metin ve işaretler" }), textWithMarks()));
  } else if (res.kind === "image") {
    O.append(el("img", { src: res.imageUrl, alt: "Orijinal görüntü" }), el("details", {}, el("summary", { textContent: "OCR metni ve işaretler" }), textWithMarks()));
    M.append(el("img", { src: res.maskUrl, alt: "Maskeli görüntü" }));
  } else { O.append(textWithMarks()); M.textContent = res.outText; }
}
$("pagePrev").onclick = () => { if (page > 0) { page--; renderCompare(); } };
$("pageNext").onclick = () => { if (page < res.origPreviews.length - 1) { page++; renderCompare(); } };

function textWithMarks() {
  const box = el("div", { style: "white-space:pre-wrap;font:12.5px/1.6 var(--code)" });
  const t = res.text, spans = res.spans, ev = res.eval;
  // missed gold values: underline their first occurrence in the text
  const miss = [];
  if (ev) ev.gold.forEach((g, i) => { if (!ev.found[i]) { const j = t.toLocaleLowerCase("tr").indexOf(g.text.toLocaleLowerCase("tr")); if (j >= 0) miss.push({ start: j, end: j + g.text.length, miss: true, g }); } });
  const items = [...spans.map(s => ({ ...s })), ...miss].sort((a, b) => a.start - b.start);
  let pos = 0;
  for (const s of items) {
    if (s.start < pos) continue;
    box.append(t.slice(pos, s.start).replace(/\f/g, "\n— sayfa sonu —\n"));
    if (s.miss) { box.append(el("span", { className: "miss", title: `Kaçan: ${LABEL[s.g.entity_type] ?? s.g.entity_type}`, textContent: t.slice(s.start, s.end) })); }
    else {
      const k = key(s), fp = ev && ev.fps.some(f => key(f) === k);
      const mk = el("mark", { textContent: t.slice(s.start, s.end), title: `${LABEL[s.entity_type] ?? s.entity_type} · ${s.recognizer} · ${s.score}` });
      if (off.has(k)) mk.classList.add("off"); else if (ev) mk.classList.add(fp ? "fp" : "ok");
      mk.onclick = () => toggle(s); box.append(mk);
    }
    pos = s.end;
  }
  box.append(t.slice(pos).replace(/\f/g, "\n— sayfa sonu —\n"));
  return box;
}
function toggle(s) { off.has(key(s)) ? off.delete(key(s)) : off.add(key(s)); render(); }

function renderList() {
  const tb = $("list"); tb.textContent = "";
  for (const s of res.spans) {
    const cb = el("input", { type: "checkbox", checked: !off.has(key(s)), ariaLabel: "Maskele" }); cb.onchange = () => toggle(s);
    const flag = el("button", { className: "flag", textContent: "⚑", title: "Hata bildirimine ekle" });
    flag.onclick = () => openReport(off.has(key(s)) ? "missed" : "false_positive", s.text);
    tb.append(el("tr", {}, el("td", {}, cb), el("td", { className: "v", textContent: s.text.replace(/\s+/g, " ") }),
      el("td", { textContent: (LABEL[s.entity_type] ?? s.entity_type) + (s.flag_only ? " (uyarı)" : "") }),
      el("td", { textContent: s.recognizer }), el("td", { className: "num", textContent: s.score.toFixed(2) }), el("td", {}, flag)));
  }
}
function renderGold() {
  const g = $("gold"); g.textContent = ""; const ev = res.eval; if (!ev) return;
  const pct = x => (100 * x).toFixed(1) + "%";
  g.append(el("div", { className: "score" },
    el("div", {}, el("b", { textContent: pct(ev.recall) }), el("span", { textContent: `Yakalama (recall): ${ev.found.filter(Boolean).length} / ${ev.gold.length}` })),
    el("div", {}, el("b", { textContent: pct(ev.precision) }), el("span", { textContent: `Kesinlik (precision): ${ev.fps.length} fazla` })),
    el("div", {}, el("b", { textContent: res.leaks.length ? `${res.leaks.length}` : "0", className: res.leaks.length ? "bad-t" : "ok-t" }), el("span", { textContent: "Çıktıda okunabilen değer" }))));
  const tb = el("tbody");
  for (const [k, p] of Object.entries(ev.per).sort()) tb.append(el("tr", {}, el("td", { textContent: LABEL[k] ?? k }), el("td", { className: "num", textContent: p.gold }),
    el("td", { className: "num", textContent: p.found }), el("td", { className: "num " + (p.gold - p.found ? "bad-t" : ""), textContent: p.gold - p.found }), el("td", { className: "num " + (p.fp ? "warn-t" : ""), textContent: p.fp })));
  g.append(el("table", { className: "tbl" }, el("thead", {}, el("tr", {}, ...["Tür", "Doğru cevap", "Bulunan", "Kaçan", "Fazla"].map((h, i) => el("th", { className: i ? "num" : "", textContent: h })))), tb));
  const missed = ev.gold.map((x, i) => ({ ...x, part: ev.partial[i] })).filter((_, i) => !ev.found[i]);
  g.append(el("div", { className: "lists" },
    el("div", {}, el("h3", { textContent: `Kaçan veya kısmen maskelenen (${missed.length})` }), el("ul", {}, ...missed.map(x => el("li", { textContent: `${x.text} · ${LABEL[x.entity_type] ?? x.entity_type}${x.part ? ` (kısmen: yalnız "${x.part}" maskelendi)` : ""}` })))),
    el("div", {}, el("h3", { textContent: `Fazla maskelenenler (${ev.fps.length})` }), el("ul", {}, ...ev.fps.map(x => el("li", { textContent: `${x.text} · ${LABEL[x.entity_type] ?? x.entity_type}` }))))));
  g.append(el("p", { className: "hint", textContent: "Doğru cevaplar belgeyi üreten betikten gelir. Taranmış belgelerde OCR hataları da puanı etkiler." }));
}
function renderOut() {
  const o = $("outSummary"); o.textContent = "";
  let msg, cls;
  if (res.leaks.length) { msg = `Dikkat: ${res.leaks.length} maskelenen değer çıktıda hâlâ okunabiliyor. Göndermeyin.`; cls = "bad-t"; }
  else if (res.unchecked) { msg = "Taranmış sayfalar tekrar okunmadı; çıktıyı gözle kontrol edin."; cls = "warn-t"; }
  else { msg = "Sızıntı kontrolü geçti: maskelenen değerlerin hiçbiri çıktıda okunamıyor."; cls = "ok-t"; }
  o.append(el("p", { className: cls, textContent: msg }), el("p", { className: "hint", textContent: `${outName} · ${(outBlob.size / 1024).toFixed(0)} KB` }));
  const t = res.timing, rows = [["Model", res.settings.engineName], ["OCR modeli", res.ocrPages ? $("ocrLang").selectedOptions[0].textContent : "kullanılmadı"],
    ["Sayfa", `${res.pages}${res.ocrPages ? ` (${res.ocrPages} OCR)` : ""}`], ["Okuma ve OCR", `${t.parse} ms`], ...(res.settings.ner ? [["NER", `${t.ner} ms · ${res.nerCount} aday`]] : []),
    ["Kurallar", `${t.rules} ms`], ["Maskeleme ve kontrol", `${res.redactMs} ms`], ["Motor sürümü", version.rules ?? ""]];
  $("timing").textContent = ""; for (const [a, b] of rows) $("timing").append(el("tr", {}, el("td", { textContent: a }), el("td", { textContent: b })));
}
$("download").onclick = () => { const a = el("a", { href: URL.createObjectURL(outBlob), download: outName }); a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 30000); };
$("copy").onclick = () => worker.postMessage({ type: "maskedText", spans: chosen() });
$("clear").onclick = () => worker.postMessage({ type: "forget" });

// ---------------------------------------------------------------- report a mistake
let pendingOriginal = null;
function openReport(kind = "missed", what = "") {
  if (!res) return;
  document.querySelector(`#reportForm input[name=kind][value=${kind}]`).checked = true;
  $("rWhat").value = what; $("rStatus").textContent = "";
  $("incDetections").checked = res.isSample; $("incOriginal").checked = res.isSample;
  $("detWarn").classList.toggle("hidden", res.isSample); $("origWarn").classList.toggle("hidden", res.isSample);
  $("rSend").classList.toggle("hidden", !CONFIG.reportEndpoint);
  $("rHow").textContent = CONFIG.reportEndpoint
    ? `"Doğrudan gönder" raporu ${new URL(CONFIG.reportEndpoint).host} üzerinden iletir. Ya da raporu indirip e-postayla kendiniz gönderin.`
    : `Rapor bilgisayarınıza indirilir ve e-posta uygulamanız ${CONFIG.reportEmail} adresine açılır. İndirilen .zip dosyasını ekleyip gönderin. Siz göndermeden hiçbir şey çıkmaz.`;
  $("reportDlg").showModal();
}
$("reportBtn").onclick = () => openReport();

async function buildReport() {
  const kind = document.querySelector("#reportForm input[name=kind]:checked").value;
  const id = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
  const ev = res.eval;
  const report = {
    id, created: new Date().toISOString(), app: "katip-yerel", version, page: location.origin + location.pathname,
    feedback: { kind, what: $("rWhat").value, text: $("rText").value },
    document: { name: res.isSample ? res.name : "(kullanıcı belgesi)", sample: res.isSample, kind: res.kind, pages: res.pages, ocrPages: res.ocrPages, chars: res.text.length },
    settings: { ...res.settings, mask: $("incDetections").checked ? res.settings.mask : `${res.settings.mask.length} terim` },
    result: { detected: res.spans.length, masked: chosen().length, leaks: res.leaks.length, unchecked: res.unchecked, timing: { ...res.timing, redact: res.redactMs },
      score: ev ? { recall: ev.recall, precision: ev.precision, missed: ev.gold.filter((_, i) => !ev.found[i]).map(x => ({ type: x.entity_type, text: x.text })), false_alarms: ev.fps.map(x => ({ type: x.entity_type, text: x.text })) } : null },
    detections: $("incDetections").checked ? res.spans.map(s => ({ type: s.entity_type, text: s.text, start: s.start, end: s.end, score: s.score, recognizer: s.recognizer, masked: !off.has(key(s)) }))
                                           : res.spans.map(s => ({ type: s.entity_type, start: s.start, end: s.end, score: s.score, recognizer: s.recognizer, masked: !off.has(key(s)) })),
    browser: navigator.userAgent,
  };
  const zip = new JSZip();
  zip.file("report.json", JSON.stringify(report, null, 1));
  if ($("incMasked").checked) zip.file("maskeli/" + outName, outBlob);
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
    `Lütfen indirilen ${fname} dosyasını bu e-postaya ekleyin.`].filter(x => x !== null && x !== undefined && x !== false).join("\n");
  const subject = `Katip Yerel hata bildirimi: ${KIND_TR[report.feedback.kind]} (${report.document.kind})`;
  location.href = `mailto:${CONFIG.reportEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body.slice(0, 1800))}`;
  $("rStatus").textContent = `${fname} indirildi. E-posta açılmadıysa ${CONFIG.reportEmail} adresine dosyayı ekleyerek yazın.`;
  window.__lastMailto = { subject, body, fname };
};
$("rSend").onclick = async () => {
  $("rStatus").textContent = "Gönderiliyor…";
  try {
    const { id, report, blob } = await buildReport();
    const fd = new FormData();
    fd.append("_subject", `Katip Yerel hata bildirimi ${id}`); fd.append("email", CONFIG.reportEmail);
    fd.append("message", `${KIND_TR[report.feedback.kind]}: ${report.feedback.what}\n\n${report.feedback.text}`);
    fd.append("report", JSON.stringify(report)); fd.append("attachment", blob, `katip-rapor-${id}.zip`);
    const r = await fetch(CONFIG.reportEndpoint, { method: "POST", body: fd, headers: { Accept: "application/json" } });
    $("rStatus").textContent = r.ok ? "Gönderildi, teşekkürler." : `Gönderilemedi (${r.status}). Raporu indirip e-postayla gönderin.`;
  } catch (e) { $("rStatus").textContent = "Gönderilemedi: " + e.message; }
};

// ---------------------------------------------------------------- boot
(async () => {
  [samples, models, version] = await Promise.all(["samples/manifest.json", "models/registry.json", "version.json"].map(u => fetch(u).then(r => r.json())));
  $("version").textContent = `Katip Yerel ${version.app} · kurallar ${version.rules} · ${version.built}`;
  if (version.source) $("srcLink").href = version.source; else $("srcLink").remove();
  buildSampleUI(); buildSettingsUI(); updateRun();
})();
