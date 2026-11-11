// Playwright check of the demo site: every sample format, a NER model, a user file, the report flow.
const { chromium } = require("playwright");
const BASE = process.env.BASE || "http://127.0.0.1:8770/";
const SHOTS = process.env.SHOTS || "/tmp";
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 960 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const reqs = [], errs = [];
  ctx.on("request", r => reqs.push({ m: r.method(), u: r.url() }));
  page.on("console", m => m.type() === "error" && errs.push(m.text()));
  page.on("pageerror", e => errs.push(String(e)));
  await page.goto(BASE + (process.env.DEV ? "?dev" : ""));
  await page.waitForFunction(() => document.getElementById("run").textContent === "Maskele", null, { timeout: 120000 });
  const runAndWait = async () => {
    await page.click("#run");
    await page.waitForFunction(() => /^Bitti|^Hata/.test(document.getElementById("status").textContent), null, { timeout: 240000 });
    return page.textContent("#status");
  };
  const cases = (process.env.CASES || "dilekce:pdf,dilekce:scan.pdf,dilekce:png,dilekce:docx,dilekce:udf,dilekce:txt,epikriz:pdf,mesaj:txt").split(",");
  for (const c of cases) {
    const [type, fmt] = c.split(":");
    const id = await page.evaluate(t => [...document.querySelectorAll("#sampleType option")].find(o => o.value.startsWith(t + "_")).value, type);
    await page.selectOption("#sampleType", id);
    await page.click(`#formatBtns button:text-is("${({ txt: "Metin", docx: "Word", udf: "UYAP .udf", pdf: "PDF", "scan.pdf": "Taranmış PDF", png: "Fotoğraf" })[fmt]}")`);
    const t0 = Date.now(); const st = await runAndWait();
    await page.click('[data-tab="gold"]');
    const score = await page.$$eval(".score b", b => b.map(x => x.textContent));
    console.log(`${id}.${fmt}`.padEnd(24), `${Date.now() - t0} ms`, st, "| recall/precision/leaks:", score.join(" "));
    if (c === "dilekce:pdf") { await page.click('[data-tab="compare"]'); await page.screenshot({ path: SHOTS + "/demo_compare.png" }); }
    if (c === "dilekce:txt") { await page.click('[data-tab="compare"]'); await page.screenshot({ path: SHOTS + "/demo_text.png" }); await page.click('[data-tab="gold"]'); await page.screenshot({ path: SHOTS + "/demo_gold.png" }); }
  }
  if (process.env.DEV) {
    await page.selectOption("#engine", "rules+test-ner");
    console.log("NER:", await runAndWait(), await page.$$eval("#timing tr", r => r.map(x => x.textContent).join(" | ")));
    await page.selectOption("#engine", "rules");
  }
  // own file
  await page.click("#srcFileBtn");
  await page.setInputFiles("#file", "/mnt/project-files/katip-redact/eval/blind/kira_sozlesmesi_02.docx");
  console.log("own file:", await runAndWait());
  // report flow
  await page.click("#reportBtn");
  const def = await page.evaluate(() => ({ det: document.getElementById("incDetections").checked, orig: document.getElementById("incOriginal").checked }));
  await page.fill("#rText", "Test bildirimi");
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#rMail")]);
  const p = SHOTS + "/" + dl.suggestedFilename(); await dl.saveAs(p);
  const mail = await page.evaluate(() => window.__lastMailto);
  console.log("report: defaults for own file", def, "zip", dl.suggestedFilename(), "| subject:", mail.subject);
  await page.screenshot({ path: SHOTS + "/demo_report.png" });
  const ext = reqs.filter(r => !r.u.startsWith(BASE) && !r.u.startsWith("blob:") && !r.u.startsWith("data:") && !r.u.startsWith("mailto:"));
  console.log("requests to other origins:", ext.length, ext.slice(0, 3), "| non-GET:", reqs.filter(r => r.m !== "GET").length);
  console.log("console errors:", errs.slice(0, 5));
  await browser.close();
})();
