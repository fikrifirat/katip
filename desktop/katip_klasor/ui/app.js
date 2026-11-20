// Katip Klasör window. Everything comes from the local API on 127.0.0.1; values are only ever put in the
// page with textContent, never as HTML.
const TOKEN = new URLSearchParams(location.search).get("t") || "";
const $ = s => document.querySelector(s);

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) el.append(c.nodeType ? c : String(c));
  return el;
}

async function api(path, body) {
  const r = await fetch("/api/" + path, body === undefined
    ? { headers: { "X-Katip-Token": TOKEN } }
    : { method: "POST", headers: { "X-Katip-Token": TOKEN, "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json();
  if (j.error) throw new Error(j.error);
  return j;
}

const STATUS = { working: "Maskeleniyor", review: "Kontrol bekliyor", ready: "Hazır", released: "Maskeli klasörde", error: "Hata" };
const KIND = { txt: "Metin", docx: "Word", udf: "UYAP", pdf: "PDF", image: "Fotoğraf" };
const GROUPS = {
  missed: ["Gözden kaçmış olabilir", "Katip bunları kişisel veri sandı ama emin olamadı, maskelemedi. Varsayılan: maskelenir."],
  lone: ["Tek başına ad", "Cümle içinde tek kelimelik ad. Sıradan bir kelimeyse Maskeleme'yi seçin."],
  unsure: ["Emin değil", "Maskelendi ama güven düşük. Yanlışsa Maskeleme'yi seçin."],
  ocr: ["Fotoğraftan okunan sayfa", "Taramadan okunan metinde harf hataları adları gizleyebilir. Sayfaya bir göz atın."],
};

let S = null, curCase = null, review = null, selFlag = null, view = "files";

// ---------------------------------------------------------------- shell
function show(v) {
  view = v;
  for (const b of document.querySelectorAll(".tabs button")) b.setAttribute("aria-selected", String(b.dataset.view === v || (v === "review" && b.dataset.view === "files")));
  for (const s of document.querySelectorAll(".view")) s.hidden = s.id !== "view-" + v;
  if (v === "audit") loadAudit();
  if (v === "settings") fillSettings();
  if (v === "restore") fillCaseSelect($("#restoreCase"), true);
}
for (const b of document.querySelectorAll(".tabs button")) b.addEventListener("click", () => { review = null; show(b.dataset.view); });

async function refresh() {
  try { S = await api("state"); } catch (e) { return; }
  const warn = [S.warning, S.error && S.error.split("\n").filter(Boolean).pop()].filter(Boolean).join(" · ");
  $("#warn").hidden = !warn; $("#warn").textContent = warn;
  $("#busy").hidden = !S.busy; $("#busyText").textContent = S.busy ? `Maskeleniyor: ${S.busy}` : "";
  if (!curCase || !S.cases.some(c => c.name === curCase)) curCase = S.cases[0]?.name || null;
  if (view === "files") renderFiles();
}

// ---------------------------------------------------------------- files
function caseObj() { return S.cases.find(c => c.name === curCase); }

function renderFiles() {
  const list = $("#caseList"); list.replaceChildren();
  for (const c of S.cases) {
    const waiting = c.jobs.filter(j => j.status === "review" || j.status === "error").length;
    list.append(h("li", {}, h("button", { "aria-current": String(c.name === curCase), onclick: () => { curCase = c.name; renderFiles(); } },
      h("span", {}, c.name === "Genel" ? "Genel (klasörsüz)" : c.name), waiting ? h("span", { class: "count" }, waiting) : null)));
  }
  $("#tools").replaceChildren(...S.modules.map(m => h("li", { title: m.about, class: m.status === "installed" ? "on" : "" },
    h("span", {}, m.name), h("span", { class: "pill " + (m.status === "installed" ? "released" : "working") }, m.status === "installed" ? "Açık" : "Yakında"))));
  const pane = $("#casePane"); pane.replaceChildren();
  const c = caseObj();
  if (!c) {
    pane.append(h("div", { class: "empty" }, h("p", {}, h("b", {}, "Henüz dava yok.")),
      h("p", {}, "Soldan bir dava klasörü ekleyin ya da belgeleri doğrudan ", h("b", {}, "1 Gelen"), " klasörüne bırakın."),
      h("button", { onclick: () => api("open", { which: "inbox" }) }, "1 Gelen klasörünü aç")));
    return;
  }
  const seg = h("div", { class: "seg", role: "group", "aria-label": "Profil" },
    Object.entries(S.profiles).map(([k, label]) => h("button", { "aria-pressed": String(c.profile === k),
      onclick: async () => { if (c.profile === k) return; await api("profile", { case: c.name, profile: k }); refresh(); } }, label)));
  pane.append(h("div", { class: "casehead" },
    h("div", {}, h("h1", {}, c.name === "Genel" ? "Genel" : c.name),
      h("div", { class: "row" }, h("span", { class: "hint" }, "Profil:"), seg)),
    h("div", { class: "row" },
      h("button", { onclick: () => api("open", { which: "inbox", case: c.name }) }, "Belge ekle (Gelen)"),
      h("button", { onclick: () => api("open", { which: "out", case: c.name }) }, "Maskeli klasörü aç"))));
  if (!c.jobs.length) {
    pane.append(h("div", { class: "empty" }, h("p", {}, h("b", {}, "Bu davada belge yok.")),
      h("p", {}, "PDF, Word, UYAP (.udf), metin ya da fotoğrafları ", h("b", {}, `1 Gelen/${c.name}`), " klasörüne bırakın. Katip birkaç saniye içinde maskeler."),
      h("button", { onclick: () => api("open", { which: "inbox", case: c.name }) }, "Klasörü aç")));
    return;
  }
  const rows = c.jobs.map(j => {
    const total = Object.values(j.counts || {}).reduce((a, b) => a + b, 0);
    let action;
    if (j.status === "review" || j.status === "ready") action = h("button", { class: j.status === "review" ? "primary" : "", onclick: () => openReview(c.name, j.key) }, j.status === "review" ? "Kontrol et" : "Gözden geçir");
    else if (j.status === "released") action = h("button", { onclick: () => openReview(c.name, j.key) }, "Görüntüle");
    else if (j.status === "error") action = h("button", { onclick: async () => { await api("reprocess", { case: c.name, key: j.key }); refresh(); } }, "Yeniden dene");
    return h("tr", {},
      h("td", { class: "name", title: j.name }, j.name),
      h("td", { class: "sm" }, KIND[j.kind] || j.kind || ""),
      h("td", {}, h("span", { class: "pill " + j.status }, STATUS[j.status] || j.status)),
      h("td", { class: "sm" }, j.status === "error" ? (j.error || "") : `${total} değer maskelendi` + (j.flags ? `, ${j.flags} yer kontrol bekliyor` : "") + (j.ocr ? ", fotoğraftan okundu" : "")),
      h("td", {}, action));
  });
  pane.append(h("div", { class: "tablewrap" }, h("table", { class: "grid" },
    h("thead", {}, h("tr", {}, h("th", {}, "Belge"), h("th", {}, "Tür"), h("th", {}, "Durum"), h("th", {}, "Özet"), h("th", {}, ""))),
    h("tbody", {}, rows))));
  pane.append(h("p", { class: "note" }, "Katip yalnızca tespit ettiğini maskeler. Maskeli kopya ancak kontrolü onayladığınızda ",
    h("b", {}, "2 Maskeli"), " klasörüne konur. Asıl belgeleriniz taşınmaz ve değiştirilmez."));
}

$("#newCase").addEventListener("submit", async e => {
  e.preventDefault();
  const name = $("#newCaseName").value.trim(); if (!name) return;
  try { const r = await api("case", { name }); curCase = r.case; $("#newCaseName").value = ""; refresh(); }
  catch (err) { alert(err.message); }
});

// ---------------------------------------------------------------- review
async function openReview(caseName, key) {
  review = { case: caseName, key, ...(await api(`job?case=${encodeURIComponent(caseName)}&key=${encodeURIComponent(key)}`)) };
  selFlag = null; show("review"); renderReview();
}

function renderReview() {
  const R = review, j = R.job, root = $("#view-review"); root.replaceChildren();
  const released = j.status === "released";
  const paper = h("div", { class: "paper", id: "paper" }, R.segments.map(s => {
    if (!s.m) return s.t;
    if (s.m === "mask") return h("span", { class: "m" + (s.flag ? " flag" : ""), "data-flag": s.flag, title: s.flag ? "Kontrol listesinde" : "Maskelenecek", onclick: s.flag ? () => pick(s.flag) : null }, s.type);
    return h("span", { class: "c", "data-flag": s.flag, title: `${s.type}: maskelenmeyecek`, onclick: s.flag ? () => pick(s.flag) : null }, s.t);
  }));
  const doc = h("div", { class: "doc" },
    h("div", { class: "dochead" }, h("button", { class: "link", onclick: () => { review = null; show("files"); refresh(); } }, "← Dosyalar"),
      h("h1", {}, j.name), h("span", { class: "pill " + j.status }, STATUS[j.status])),
    h("p", { class: "hint" }, released ? `Maskeli klasörde: ${j.outputs.join(", ")}` : "Siyah etiketler maskelenecek yerler; kırmızı çizgili kelimeler maskelenmeyecek. Paylaşılacak kopya bu görünümün aynısıdır."),
    paper);
  const groups = Object.keys(GROUPS).map(kind => {
    const fs = R.flags.filter(f => f.kind === kind); if (!fs.length) return null;
    return h("div", { class: "group" }, h("h2", {}, `${GROUPS[kind][0]} (${fs.length})`), h("p", { class: "why" }, GROUPS[kind][1]), fs.map(spot));
  }).filter(Boolean);
  const scroll = h("div", { class: "scroll" }, groups.length ? groups : h("p", { class: "hint" }, "Kontrol edilecek bir yer yok. Yine de belgeye göz atıp onaylayın."));
  const term = h("input", { type: "text", placeholder: "Kaçan bir ad ya da kelime", "aria-label": "Her zaman maskelenecek kelime" });
  const foot = h("div", { class: "foot" },
    released ? null : h("form", { class: "addterm", onsubmit: async e => { e.preventDefault(); if (!term.value.trim()) return;
      await api("term", { case: R.case, key: R.key, term: term.value, action: "mask" }); await openReview(R.case, R.key); } },
      term, h("button", { type: "submit" }, "Her zaman maskele")),
    released ? h("button", { onclick: () => api("open", { which: "out", case: R.case }) }, "Maskeli klasörü aç")
      : h("button", { class: "primary", id: "approve", onclick: approve }, "Onayla ve maskeli klasöre koy"),
    h("p", { class: "caveat" }, "Katip yalnızca tespit ettiğini maskeler; bu ekran, gözden kaçabilecek yerleri göstermek içindir."));
  root.append(h("div", { class: "review" }, doc, h("aside", { class: "side" }, scroll, foot)));
}

function spot(f) {
  const released = review.job.status === "released";
  const ctx = f.kind === "ocr" ? h("div", { class: "ctx" }, `Sayfa ${f.page} taramadan okundu.`)
    : h("div", { class: "ctx", onclick: () => pick(f.id) }, f.context[0], h("b", {}, f.context[1]), f.context[2]);
  const choices = f.kind === "ocr" ? [["ok", "Baktım"]] : [["mask", "Maskele"], ["keep", "Maskeleme"]];
  return h("div", { class: "spot" + (selFlag === f.id ? " sel" : ""), id: "spot-" + f.id },
    h("div", { class: "meta" }, h("span", {}, [f.type_label, f.kind !== "ocr" ? `s.${f.page}` : null, f.count > 1 ? `${f.count} kez` : null].filter(Boolean).join(" · ")),
      f.kind !== "ocr" ? h("span", {}, `güven %${Math.round(f.score * 100)}`) : null),
    ctx,
    h("div", { class: "seg" }, choices.map(([d, label]) => h("button", { class: d, "aria-pressed": String(f.decision === d), disabled: released,
      onclick: async () => { const r = await api("decide", { case: review.case, key: review.key, flag: f.id, decision: d }); Object.assign(review, r); renderReview(); } }, label))));
}

function pick(id) {
  selFlag = id; renderReview();
  document.getElementById("spot-" + id)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  const el = document.querySelector(`#paper [data-flag="${id}"]`);
  if (el) { el.scrollIntoView({ block: "center", behavior: "smooth" }); el.classList.add("hl"); }
}

async function approve() {
  const b = $("#approve"); b.disabled = true; b.textContent = "Kontrol ediliyor…";
  try {
    const r = await api("release", { case: review.case, key: review.key });
    if (r.error) { alert(r.error); }
    else if (r.job.status === "error") { alert(r.job.error); }
    review = null; show("files"); refresh();
  } catch (e) { alert(e.message); b.disabled = false; b.textContent = "Onayla ve maskeli klasöre koy"; }
}

// ---------------------------------------------------------------- restore
function fillCaseSelect(sel, withAuto) {
  const cur = sel.value; sel.replaceChildren();
  if (withAuto) sel.append(h("option", { value: "" }, "Otomatik bul"));
  for (const c of S?.cases || []) sel.append(h("option", { value: c.name }, c.name));
  if ([...sel.options].some(o => o.value === cur)) sel.value = cur;
}
$("#restoreBtn").addEventListener("click", async () => {
  const out = $("#restoreOut");
  try {
    const r = await api("restore", { text: $("#restoreText").value, case: $("#restoreCase").value });
    out.hidden = false;
    out.className = "result" + (r.restored ? "" : " bad");
    out.replaceChildren(r.restored ? `${r.restored} yer gerçek değeriyle dolduruldu: 4 Geri yüklenmiş/${r.case === "Genel" ? "" : r.case + "/"}${r.name}` : "Metinde bu davalara ait bir etiket bulunamadı.");
    if (r.restored) out.append(" ", h("button", { onclick: () => api("open", { which: "restored", case: r.case === "Genel" ? "" : r.case }) }, "Klasörü aç"));
  } catch (e) { out.hidden = false; out.className = "result bad"; out.textContent = e.message; }
});
$("#openAnswers").addEventListener("click", () => api("open", { which: "answers" }));

// ---------------------------------------------------------------- audit
const EVENT = { masked: "Maskelendi", released: "Maskeli klasöre kondu", restored: "Geri yüklendi", error: "Hata", forgotten: "Dava unutuldu" };
async function loadAudit() {
  fillCaseSelect($("#auditCase"), false);
  const c = $("#auditCase").value; if (!c) return;
  $("#auditCsv").href = `/api/audit.csv?case=${encodeURIComponent(c)}&t=${encodeURIComponent(TOKEN)}`;
  const { rows } = await api(`audit?case=${encodeURIComponent(c)}`);
  $("#auditRows").replaceChildren(...rows.reverse().map(r => h("tr", {},
    h("td", { class: "sm" }, (r.at || "").replace("T", " ").slice(0, 16)), h("td", {}, EVENT[r.event] || r.event),
    h("td", { class: "name" }, r.file || ""), h("td", { class: "sm" }, r.profile ? S.profiles[r.profile] || r.profile : ""),
    h("td", { class: "sm" }, Object.values(r.counts || {}).reduce((a, b) => a + b, 0) || ""),
    h("td", { class: "sm" }, r.detail || ""), h("td", { class: "sm" }, r.user || ""))));
}
$("#auditCase").addEventListener("change", loadAudit);

// ---------------------------------------------------------------- settings
async function fillSettings() {
  $("#setFolder").value = S.root;
  $("#setModel").value = S.settings.model;
  const p = $("#setProfile"); p.replaceChildren(...Object.entries(S.profiles).map(([k, l]) => h("option", { value: k }, l)));
  p.value = S.settings.default_profile; $("#setAuto").checked = !!S.settings.auto_release;
  fillCaseSelect($("#forgetCase"), false);
  $("#mods").replaceChildren(...S.modules.map(m => h("li", {}, h("div", {}, h("b", {}, m.name), " ",
    h("span", { class: "pill " + (m.status === "installed" ? "released" : "working") }, m.status === "installed" ? "Kurulu" : "Yakında")),
    h("div", { class: "hint" }, m.about))));
  try { const st = await api("status"); $("#engineInfo").textContent = `Katip Klasör ${st.version} · ${st.engine}`; } catch {}
}
$("#saveSettings").addEventListener("click", async () => {
  await api("settings", { folder: $("#setFolder").value, model: $("#setModel").value, default_profile: $("#setProfile").value, auto_release: $("#setAuto").checked });
  $("#savedNote").hidden = false; setTimeout(() => $("#savedNote").hidden = true, 2000); refresh();
});
$("#openRoot").addEventListener("click", () => api("open", { which: "inbox" }));
$("#forgetBtn").addEventListener("click", async () => {
  const c = $("#forgetCase").value; if (!c) return;
  if (!confirm(`"${c}" davasının anahtarı silinsin mi? Bu davanın cevaplarına artık gerçek adlar geri konamaz.`)) return;
  await api("forget", { case: c }); refresh();
});

refresh();
setInterval(() => { if (view === "files") refresh(); }, 2000);
