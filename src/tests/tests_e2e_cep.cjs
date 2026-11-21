// Playwright check of the client test page (cep.html) with synthetic letters: a Dutch IND decision and a municipal
// decision are typed and masked, the deadline card shows the right rule, the prompt holds no masked value, names
// come back in a pasted answer, a Turkish letter falls back to the Turkish models, and nothing leaves the origin.
//   (cd docs && python serve.py 8770) & node src/tests/tests_e2e_cep.cjs
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const BASE = process.env.BASE || "http://127.0.0.1:8770/";
const SHOTS = process.env.SHOTS || "/tmp";
const letter = f => fs.readFileSync(path.join(__dirname, "letters", f), "utf8");
const ok = (c, m) => { if (!c) { console.error("FAIL:", m); process.exitCode = 1; } else console.log("ok:", m); };

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, locale: "nl-NL" });
  const page = await ctx.newPage();
  const outside = [], errs = [];
  ctx.on("request", r => { if (!r.url().startsWith(BASE) && !r.url().startsWith("blob:") && !r.url().startsWith("data:")) outside.push(r.url()); });
  page.on("pageerror", e => errs.push(String(e)));
  await page.goto(BASE + "cep.html");
  await page.waitForFunction(() => /Klaar|Ready|Hazır/.test(document.getElementById("status").textContent), null, { timeout: 180000 });

  async function run(file) {
    await page.evaluate(() => { document.getElementById("pasteBox").open = true; });
    await page.fill("#paste", letter(file));
    await page.click("#pasteGo");
    await page.waitForFunction(() => window.__katipCep()?.map && !document.getElementById("s4").classList.contains("hidden"), null, { timeout: 240000 });
    return page.evaluate(() => { const d = window.__katipCep(); return { lang: d.lang, type: d.type, map: d.map, text: d.text, leaks: d.leaks.length,
      kind: document.getElementById("kind").innerText }; });
  }

  // 1. IND decision
  let d = await run("ind_besluit.txt");
  ok(d.lang === "nl", "IND letter read as Dutch");
  ok(d.type === "ind_besluit", "IND letter typed as ind_besluit: " + d.type);
  ok(/4 weken/.test(d.kind) && /4 weeks/.test(d.kind), "deadline card says 4 weken / 4 weeks");
  const vals = Object.values(d.map);
  for (const v of ["111222333", "3012345678"]) ok(vals.includes(v), "masked " + v);
  ok(vals.some(v => /Yıldız/.test(v)), "masked the client's name");
  ok(Object.keys(d.map).some(k => k.startsWith("[NAAM-")) && Object.keys(d.map).some(k => k.startsWith("[V-NUMMER-")), "Dutch placeholder tags");
  ok(d.leaks === 0, "no leaks");
  ok(/Immigratie- en Naturalisatiedienst/.test(d.text) && /3 november 2026/.test(d.text), "sender and date stay readable");
  await page.screenshot({ path: SHOTS + "/cep_ind.png", fullPage: true });
  // prompt: copy button puts the prompt on the clipboard; read it from the page function instead
  await ctx.grantPermissions(["clipboard-read", "clipboard-write"], { origin: BASE.replace(/\/$/, "") });
  await page.click("#copy");
  const prompt = await page.evaluate(() => navigator.clipboard.readText());
  ok(/IND decision \(residence or visa\)/.test(prompt) && /Vreemdelingenwet 2000, art. 69/.test(prompt), "prompt carries the type and the law");
  ok(!vals.some(v => prompt.includes(v)), "prompt holds no masked value");
  const lab = Object.keys(d.map).find(k => k.startsWith("[NAAM-"));
  await page.fill("#answer", `Deze brief is aan ${lab}. Maak binnen 4 weken bezwaar.`);
  const restored = await page.textContent("#restored");
  ok(restored.includes(d.map[lab]), "names come back in the answer");
  // the wrong-type picker updates the card
  await page.evaluate(() => { document.getElementById("typeFix").open = true; });
  await page.selectOption("#typeSel", "overheid_besluit");
  ok(/6 weken/.test(await page.textContent("#kind")), "picking another type changes the deadline");
  const notes = await page.evaluate(() => JSON.parse(localStorage.getItem("katip-cep-notes")));
  ok(notes[0].katip_type === "ind_besluit" && notes[0].your_type === "overheid_besluit" && !JSON.stringify(notes).includes("111222333"), "test notes keep the correction and no values");

  // 2. municipal decision, English UI
  await page.click('[data-lang="en"]');
  d = await run("gemeente_besluit.txt");
  ok(d.type === "overheid_besluit" && /6 weeks/.test(d.kind), "municipal decision: 6 weeks");
  ok(Object.values(d.map).includes("06-12345678") || Object.values(d.map).some(v => /12345678/.test(v)), "phone masked");
  await page.screenshot({ path: SHOTS + "/cep_gemeente_en.png", fullPage: true });

  // 3. Turkish letter
  await page.click('[data-lang="tr"]');
  d = await run("turks.txt");
  ok(d.lang === "tr" && d.type === "other", "Turkish letter falls back to Turkish masking");
  ok(Object.values(d.map).some(v => /Ahmet Yılmaz/.test(v)), "Turkish name masked");

  const wide = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  ok(!wide, "no sideways scroll at phone width");
  ok(outside.length === 0, "no requests outside the site: " + outside.slice(0, 3).join(" "));
  ok(errs.length === 0, "no page errors: " + errs.join(" | "));
  await browser.close();
})();
