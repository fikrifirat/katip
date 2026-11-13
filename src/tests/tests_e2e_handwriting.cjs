// Playwright: a synthetic photographed hand-filled lease (lab/photo_forms) through the real page with the
// default OCR ("auto"): the page must be read by PaddleOCR, the TC numbers and names masked, and nothing
// may be requested from anywhere but this site.
//   python docs/serve.py 8770 &  node src/tests/tests_e2e_handwriting.cjs /tmp/photo/kira_foto_01.pdf
const { chromium } = require("playwright");
const fs = require("fs");
const BASE = process.env.BASE || "http://127.0.0.1:8770/";
const FILE = process.argv[2];
(async () => {
  const gold = JSON.parse(fs.readFileSync(FILE.replace(/\.pdf$/, ".gold.json")));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 1, locale: "tr-TR" });
  const page = await ctx.newPage();
  const reqs = [], errs = [];
  ctx.on("request", r => reqs.push(r.url()));
  page.on("console", m => m.type() === "error" && errs.push(m.text()));
  page.on("pageerror", e => errs.push(String(e)));
  await page.goto(BASE);
  await page.waitForFunction(() => !document.getElementById("scan").disabled, null, { timeout: 120000 });
  console.log("OCR option picked:", await page.evaluate(() => document.querySelector("#ocrModels input:checked")?.value));
  await page.setInputFiles("#file", FILE);
  await page.waitForFunction(() => !document.getElementById("scan").disabled, null, { timeout: 60000 });
  const t0 = Date.now();
  await page.click("#scan").catch(() => {});
  await page.waitForFunction(() => window.__katip()?.spans && !document.getElementById("apply").disabled, null, { timeout: 300000 });
  const r = await page.evaluate(() => ({ text: window.__katip().text, spans: window.__katip().spans.map(s => ({ t: s.entity_type, x: s.text, rec: s.recognizer, flag: s.flag_only })) }));
  console.log(`analysed in ${Date.now() - t0} ms; spans ${r.spans.length}`);
  const sq = s => s.replace(/\s+/g, "").toLocaleLowerCase("tr");
  for (const g of gold.entities.filter(g => g.entity_type === "TCKN"))
    console.log("TC", g.text, r.spans.some(s => s.t === "TCKN" && sq(s.x) === sq(g.text)) ? "found as TCKN" : r.text.includes(g.text) ? "read but not tagged" : "not read as text (masked only if pen ink rule hits)");
  console.log("pen-ink masks:", r.spans.filter(s => s.rec === "pen_in_id_row").length);
  await page.screenshot({ path: (process.env.SHOTS || "/tmp") + "/handwriting_review.png" });
  const outside = reqs.filter(u => !u.startsWith(BASE) && !u.startsWith("blob:") && !u.startsWith("data:"));
  console.log("requests to other hosts:", outside.length, outside.slice(0, 5));
  console.log("paddle model fetched from this site:", reqs.some(u => u.startsWith(BASE) && u.includes("vendor/paddleocr/det/inference.onnx")));
  console.log("errors:", errs.length ? errs.slice(0, 5) : "none");
  await browser.close();
})();
