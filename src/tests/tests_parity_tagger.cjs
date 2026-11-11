// Browser (transformers.js + Pyodide) vs Python (onnxruntime + same bundle) on every sample .txt with the name tagger.
const { chromium } = require("playwright"); const fs = require("fs");
(async () => {
  const b = await chromium.launch(); const p = await b.newPage(); const out = {};
  await p.goto(process.env.BASE || "http://127.0.0.1:8770/");
  await p.waitForFunction(() => document.getElementById("run").textContent === "Maskele", null, { timeout: 120000 });
  await p.selectOption("#engine", "rules+tagger");
  const ids = await p.$$eval("#sampleType option", o => o.map(x => x.value));
  for (const id of ids) {
    await p.selectOption("#sampleType", id); await p.click('#formatBtns button:text-is("Metin")');
    await p.click("#run");
    await p.waitForFunction(() => /^Bitti|^Hata/.test(document.getElementById("status").textContent), null, { timeout: 120000 });
    out[id] = await p.evaluate(() => window.__katip().spans.map(s => [s.entity_type, s.start, s.end]));
  }
  fs.writeFileSync(process.argv[2], JSON.stringify(out)); console.log("docs", ids.length); await b.close();
})();
