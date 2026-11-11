// Playwright check of the demo site: preview before analysis, every sample format, apply + download,
// mask colour and watermark, a user file, the report flow, both languages, phone width, no outside requests.
const { chromium } = require("playwright");
const BASE = process.env.BASE || "http://127.0.0.1:8770/";
const SHOTS = process.env.SHOTS || "/tmp";
const OWN = process.env.OWN || "/mnt/project-files/katip-redact/eval/blind/kira_sozlesmesi_02.docx";
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 960 }, deviceScaleFactor: 1, locale: "tr-TR" });
  const page = await ctx.newPage();
  const reqs = [], errs = [];
  ctx.on("request", r => reqs.push({ m: r.method(), u: r.url() }));
  page.on("console", m => m.type() === "error" && errs.push(m.text()));
  page.on("pageerror", e => errs.push(String(e)));
  await page.goto(BASE + (process.env.DEV ? "?dev" : ""));
  const analysed = () => page.waitForFunction(() => window.__katip()?.spans && !document.getElementById("apply").disabled, null, { timeout: 240000 });
  const applied = () => page.waitForFunction(() => window.__katip()?.outText != null && !document.getElementById("download").disabled, null, { timeout: 240000 });
  // the original is previewed on selection; nothing is analysed until "find personal data"
  await page.waitForSelector("#docView .pg img, #docView .txt", { timeout: 60000 });
  await page.waitForFunction(() => !document.getElementById("scan").disabled, null, { timeout: 120000 });
  await page.waitForTimeout(1500);
  console.log("original preview shown, no auto-run:", !(await page.evaluate(() => !!window.__katip()?.spans)), "| boxes:", await page.$$eval("#docView .bx", b => b.length));
  await page.click("#scan"); await analysed();
  const cases = (process.env.CASES || "dilekce:pdf,dilekce:scan.pdf,dilekce:png,dilekce:docx,dilekce:udf,dilekce:txt,epikriz:pdf,mesaj:txt").split(",");
  for (const c of cases) {
    const [type, fmt] = c.split(":");
    const id = await page.evaluate(t => [...document.querySelectorAll("#sampleType option")].find(o => o.value.startsWith(t + "_")).value, type);
    const t0 = Date.now();
    await page.selectOption("#sampleType", id);
    await page.click(`#formatBtns button[data-fmt="${fmt}"]`).catch(() => {});
    await page.waitForFunction(() => !document.getElementById("scan").disabled && !window.__katip()?.spans, null, { timeout: 60000 });
    await page.click("#scan");
    await page.waitForFunction(n => window.__katip()?.name === n && window.__katip()?.spans, `${id}.${fmt}`, { timeout: 240000 });
    await analysed();
    const tReview = Date.now() - t0;
    if (c === "dilekce:pdf") await page.screenshot({ path: SHOTS + "/demo_review.png" });
    await page.click("#apply"); await applied();
    const score = await page.textContent("#scorebar");
    console.log(`${id}.${fmt}`.padEnd(24), `review ${tReview} ms, total ${Date.now() - t0} ms |`, score.replace(/\s+/g, " ").trim());
    if (c === "dilekce:pdf") {
      await page.screenshot({ path: SHOTS + "/demo_result.png" });
      await page.click('#colors .sw[data-c="#1f3a5f"]'); await page.waitForFunction(() => !document.getElementById("download").disabled && window.__katip()?.outText != null);
      await page.waitForTimeout(400);
      const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#download")]);
      await dl.saveAs(SHOTS + "/" + dl.suggestedFilename()); console.log("download:", dl.suggestedFilename());
      await page.screenshot({ path: SHOTS + "/demo_navy.png" });
      await page.click('#colors .sw[data-c="#000000"]'); await page.waitForTimeout(1500);
    }
    if (c === "dilekce:txt") {
      const out = await page.evaluate(() => window.__katip().outText);
      console.log("text watermark present:", /Katip Yerel/.test(out));
      await page.click('[data-view="review"]'); await page.screenshot({ path: SHOTS + "/demo_text.png" });
    }
  }
  // toggle one finding off from the list, check "not applied" notice
  await page.click("#list .it input[type=checkbox]");
  console.log("dirty notice:", /henüz uygulanmadı/.test(await page.textContent("#scorebar")));
  // vanilla baseline on the same document
  await page.click('#models input[value="vanilla"]');
  await page.waitForFunction(() => window.__katip()?.settings?.baseline === "kvkk-pii" && !document.getElementById("apply").disabled, null, { timeout: 60000 });
  console.log("vanilla:", (await page.textContent("#scorebar")).replace(/\s+/g, " ").trim());
  await page.click('#models input[value="rules+tagger"]');
  await page.waitForFunction(() => window.__katip()?.settings?.engine === "rules+tagger" && !document.getElementById("apply").disabled, null, { timeout: 60000 });
  if (process.env.DEV) {
    await page.click('#models input[value="rules+test-ner"]'); await analysed();
    console.log("NER:", await page.$$eval("#timing tr", r => r.map(x => x.textContent).join(" | ")));
  }
  // own file
  await page.click("#srcFileBtn");
  await page.setInputFiles("#file", OWN);
  await page.waitForFunction(() => !document.getElementById("scan").disabled && !window.__katip()?.spans, null, { timeout: 60000 });
  await page.click("#scan");
  await page.waitForFunction(() => window.__katip()?.isSample === false && window.__katip()?.spans, null, { timeout: 240000 });
  await page.click("#apply"); await applied();
  console.log("own file:", await page.textContent("#status"));
  // report flow
  await page.click("#reportBtn");
  const def = await page.evaluate(() => ({ det: document.getElementById("incDetections").checked, orig: document.getElementById("incOriginal").checked }));
  await page.fill("#rText", "Test bildirimi");
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#rMail")]);
  await dl.saveAs(SHOTS + "/" + dl.suggestedFilename());
  const mail = await page.evaluate(() => window.__lastMailto);
  console.log("report: defaults for own file", def, "zip", dl.suggestedFilename(), "| subject:", mail.subject);
  await page.screenshot({ path: SHOTS + "/demo_report.png" });
  await page.keyboard.press("Escape");
  // English
  await page.click('[data-lang="en"]');
  console.log("EN:", await page.textContent("#apply"), "|", await page.textContent(".sub"));
  await page.screenshot({ path: SHOTS + "/demo_en.png" });
  // phone width
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  console.log("phone horizontal scroll:", await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth));
  await page.screenshot({ path: SHOTS + "/demo_phone.png", fullPage: false });
  const ext = reqs.filter(r => !r.u.startsWith(BASE) && !r.u.startsWith("blob:") && !r.u.startsWith("data:") && !r.u.startsWith("mailto:"));
  console.log("requests to other origins:", ext.length, ext.slice(0, 3), "| non-GET:", reqs.filter(r => r.m !== "GET").length);
  console.log("console errors:", errs.slice(0, 5));
  await browser.close();
})();
