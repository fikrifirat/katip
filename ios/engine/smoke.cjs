// Smoke test of the built engine bundle in Chromium (Playwright): rules, Nano, Mini, restore, .udf/.docx text,
// and no requests outside the bundle. Run after build.mjs:  node ios/engine/smoke.cjs
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const repo = path.resolve(__dirname, '../..');
const root = path.join(repo, 'ios/Katip/Resources/Engine');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.onnx': 'application/octet-stream' };
const srv = http.createServer((q, r) => { const f = path.join(root, decodeURIComponent(q.url.split('?')[0])); if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r); });
srv.listen(8799, async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  const ext = []; p.on('request', q => { if (!q.url().startsWith('http://127.0.0.1:8799')) ext.push(q.url()); });
  p.on('console', m => console.log('console:', m.text()));
  await p.goto('http://127.0.0.1:8799/index.html'); await p.waitForFunction(() => window.katip);
  const text = fs.readFileSync(path.join(repo, 'docs/samples/') + 'dilekce_01.txt', 'utf8');
  for (const model of [null, 'nano', 'mini']) {
    const r = await p.evaluate(async ([t, m]) => { const x = await window.katip.mask({ text: t, profile: 'ai', model: m }); return { ok: x.ok, model: x.model, ms: x.ms, n: x.spans.length, head: x.text.slice(0, 300), mapping: x.mapping }; }, [text, model]);
    console.log(model, r.ok, r.model, r.ms + 'ms', r.n, 'spans');
    if (model === 'mini') { console.log(r.head); const back = await p.evaluate(([t, m]) => window.katip.restore({ text: 'Müvekkil ' + Object.keys(m)[0] + ' hakkında. [AD SOYAD-99]', mapping: m }), [r.head, r.mapping]); console.log(back); }
  }
  for (const k of ['udf', 'docx']) {
    const b64 = fs.readFileSync(path.join(repo, `docs/samples/dilekce_01.${k}`)).toString('base64');
    const r = await p.evaluate(async ([b, k]) => (await window.katip.extract({ base64: b, kind: k })).text, [b64, k]);
    console.log(k, r.length, JSON.stringify(r.slice(0, 120)));
  }
  // Letter explained: a synthetic IND letter (Dutch, Pyodide path) and a Turkish one (SDK path)
  const letters = path.join(repo, 'src/tests/letters/');
  const fail = m => { console.log('FAIL:', m); process.exitCode = 1; };
  const ind = await p.evaluate(async t => window.katip.letter({ text: t, model: 'mini' }), fs.readFileSync(letters + 'ind_besluit.txt', 'utf8'));
  console.log('letter nl', ind.ok, ind.lang, ind.type, ind.ms + 'ms', Object.keys(ind.mapping || {}).join(' '));
  if (!(ind.ok && ind.lang === 'nl' && ind.type === 'ind_besluit')) fail('IND letter type');
  for (const v of ['111222333', '3012345678', 'Yıldız']) if (ind.text.includes(v)) fail('still readable: ' + v);
  if (!ind.text.includes('Immigratie- en Naturalisatiedienst') || !/\[NAAM-1\]/.test(ind.text) || !/\[V-NUMMER-1\]/.test(ind.text)) fail('Dutch labels / sender');
  const tr = await p.evaluate(async t => window.katip.letter({ text: t, model: 'mini' }), fs.readFileSync(letters + 'turks.txt', 'utf8'));
  console.log('letter tr', tr.ok, tr.lang, tr.type, Object.keys(tr.mapping || {}).join(' '));
  if (!(tr.ok && tr.lang === 'tr' && !tr.text.includes('Ahmet Yılmaz'))) fail('Turkish letter');
  const info = await p.evaluate(() => window.katip.letterInfo());
  if (!info.types.ind_besluit || !info.law.vw69 || info.help.length !== 3 || info.labels.PERSON.tag !== 'NAAM') fail('letterInfo');
  const pr = await p.evaluate(m => window.katip.letterPrompt({ type: 'ind_besluit', docLang: 'nl', answerLang: 'en', masked: m }), ind.text);
  if (!/art\. 69/.test(pr) || pr.includes('111222333')) fail('letterPrompt');
  console.log('txt', text.length, 'external requests:', ext);
  if (ext.length) fail('external requests');
  await b.close(); srv.close();
});
