// Shrink sample PDFs for the demo: drop unused objects, compress streams and fonts (about 775 KB -> 45 KB each).
// The text layer is unchanged, so detection and answer keys stay valid; the script checks that.
//   node compress_pdf.mjs <vendored mupdf.js> <in.pdf> <out.pdf> [...more in/out pairs]
const [lib, ...files] = process.argv.slice(2);
const mupdf = await import(new URL(lib, "file://" + process.cwd() + "/").href);
const fs = await import("fs");
const text = d => { let s = ""; for (let i = 0; i < d.countPages(); i++) s += d.loadPage(i).toStructuredText().asText(); return s; };
for (let i = 0; i < files.length; i += 2) {
  const src = mupdf.Document.openDocument(new Uint8Array(fs.readFileSync(files[i])), "application/pdf");
  const before = text(src);
  src.subsetFonts?.();
  const out = src.saveToBuffer("garbage=4,compress,compress-fonts").asUint8Array().slice();
  const after = text(mupdf.Document.openDocument(out, "application/pdf"));
  if (after !== before) throw new Error(`text changed after compressing ${files[i]}`);
  fs.writeFileSync(files[i + 1], out);
}
