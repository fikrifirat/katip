// Playwright: the demo masks the synthetic Excel and e-mail fixtures (src/tests/fixtures/mail_excel) with the browser
// default model, downloads each masked copy and checks every answer-key value is unreadable in it.
//   python3 docs/serve.py 8771 &  node src/tests/tests_e2e_mail_excel.cjs
// .xlsx downloads are checked with local_formats.leak_text (cells, shared strings, formulas, notes, properties).
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path"), os = require("os"), { execFileSync } = require("child_process");
const BASE = process.env.BASE || "http://127.0.0.1:8771/";
const FIX = process.env.FIX || path.join(__dirname, "fixtures", "mail_excel");
const KEY = JSON.parse(fs.readFileSync(path.join(FIX, "answer_key.json"), "utf8"));
const squash = s => s.replace(/\s+/g, "").toLocaleLowerCase("tr");
const ZIP = path.join(__dirname, "..", "..", "docs", "katip_py.zip");
const leakText = file => execFileSync("python3", ["-c", `import sys,zipfile,tempfile
t=tempfile.mkdtemp(); zipfile.ZipFile(sys.argv[1]).extractall(t); sys.path.insert(0,t)
import local_formats as F; sys.stdout.write(F.leak_text("xlsx", open(sys.argv[2],"rb").read()))`, ZIP, file]).toString();
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ acceptDownloads: true, locale: "tr-TR" });
  const page = await ctx.newPage();
  const errs = [], outside = [];
  page.on("pageerror", e => errs.push(String(e)));
  page.on("console", m => m.type() === "error" && console.log("console:", m.text().slice(0, 400)));
  ctx.on("request", r => { if (!r.url().startsWith(BASE) && !r.url().startsWith("blob:") && !r.url().startsWith("data:")) outside.push(r.url()); });
  await page.goto(BASE);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "katip-mx-"));
  let fails = 0;
  const rows = {};
  for (const [name, { mask: gold, keep }] of Object.entries(KEY)) {
    if (await page.isVisible("#clear")) { await page.click("#clear"); await page.waitForTimeout(500); }
    const t0 = Date.now();
    await page.setInputFiles("#file", path.join(FIX, name));
    await page.waitForFunction(n => window.__katip()?.name === n && window.__katip()?.outText != null && !document.getElementById("download").disabled
                               && !document.getElementById("work").classList.contains("busy"), name, { timeout: 60000 }).catch(async e => { console.log(name, "TIMEOUT", errs, await page.evaluate(() => [window.__katip()?.name, window.__katip()?.outText == null, document.getElementById("download").disabled, document.getElementById("work").className, document.getElementById("scorebar")?.textContent].join(" | "))); throw e; });
    const r = await page.evaluate(() => ({ texts: window.__katip().spans.map(s => s.text), spans: window.__katip().spans.length, leaks: window.__katip().leaks?.length ?? 0, out: window.__katip().outText }));
    const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#download")]);
    const file = path.join(tmp, dl.suggestedFilename());
    await dl.saveAs(file);
    const readable = name.endsWith(".xlsx") ? leakText(file) : fs.readFileSync(file, "utf8") + "\n" + r.out;
    const left = gold.filter(g => squash(readable).includes(squash(g)));
    const lost = keep.filter(k => !squash(r.out).includes(squash(k)));
    if (left.length || lost.length) fails++;
    // findings that are not (part of) an answer-key value: over-masking, shown so a person can judge them
    const extra = [...new Set(r.texts.filter(t => !gold.some(g => squash(g).includes(squash(t)) || squash(t).includes(squash(g)))))];
    rows[name] = { left, lost, n: gold.length };
    if (!process.env.QUIET || left.length || lost.length) console.log(name.padEnd(28), `${gold.length - left.length}/${gold.length} answer-key values masked | ${r.spans} findings | leak check ${r.leaks} |`,
                dl.suggestedFilename(), `| ${Date.now() - t0} ms`, left.length ? "| STILL READABLE: " + left.length : "", lost.length ? "| CONTENT LOST: " + lost.join(", ") : "",
                extra.length ? `| also masked: ${extra.map(x => JSON.stringify(x)).join(" ")}` : "");
  }
  // summary by format; with a corpus (make_mail_excel_corpus.py) also against the samples' own .txt
  const fmtOf = n => KEY[n].baseline ? "txt (baseline)" : n.split(".").pop();
  const base = {}; for (const n in KEY) if (KEY[n].baseline) base[KEY[n].source[0]] = new Set(rows[n].left);
  const sum = {};
  for (const n in rows) {
    const s = sum[fmtOf(n)] ??= { files: 0, values: 0, readable: 0, onlyContainer: 0, lost: 0 };
    s.files++; s.values += rows[n].n; s.readable += rows[n].left.length; s.lost += rows[n].lost.length;
    if (!KEY[n].baseline && KEY[n].source) for (const v of rows[n].left) if (!KEY[n].source.some(id => base[id]?.has(v))) { s.onlyContainer++; console.log("  readable only in the container:", n, "|", v); }
  }
  for (const [f, s] of Object.entries(sum)) console.log(f.padEnd(16), `files ${s.files} | values ${s.values} | masked ${s.values - s.readable} | readable ${s.readable} | only in container ${s.onlyContainer} | content lost ${s.lost}`);
  console.log("page errors:", errs.length, "| requests to other origins:", outside.length);
  await browser.close();
  process.exit(fails || errs.length || outside.length ? 1 : 0);
})();
