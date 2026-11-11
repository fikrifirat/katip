// Browser (transformers.js + Pyodide) vs Python (onnxruntime + same bundle) on every sample .txt.
//   BASE=http://127.0.0.1:8771/ MODEL=rules+tagger node src/tests/tests_parity_tagger.cjs /tmp/browser.json
//   KATIP_MODEL=hf/model python3 ml/parity_py.py /tmp/browser.json docs/samples
const { chromium } = require("playwright"); const fs = require("fs");
(async () => {
  const b = await chromium.launch(); const p = await b.newPage(); const out = {};
  await p.goto(process.env.BASE || "http://127.0.0.1:8771/");
  await p.waitForFunction(() => !document.getElementById("scan").disabled, null, { timeout: 120000 });
  await p.click(`#models input[value="${process.env.MODEL || "rules+tagger"}"]`);
  const ids = await p.$$eval("#sampleType option", o => o.map(x => x.value));
  for (const id of ids) {
    await p.selectOption("#sampleType", id); await p.click('#formatBtns button[data-fmt="txt"]');
    await p.waitForFunction(n => !document.getElementById("scan").disabled && !window.__katip()?.spans && document.querySelector("#docView .txt"), null, { timeout: 60000 });
    await p.click("#scan");
    await p.waitForFunction(n => window.__katip()?.name === n && window.__katip()?.spans, `${id}.txt`, { timeout: 300000 });
    out[id] = await p.evaluate(() => window.__katip().spans.map(s => [s.entity_type, s.start, s.end]));
  }
  fs.writeFileSync(process.argv[2], JSON.stringify(out)); console.log("docs", ids.length); await b.close();
})();
