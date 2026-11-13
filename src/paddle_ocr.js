// PaddleOCR (PP-OCRv5, Apache-2.0) on onnxruntime: text-line detection (DB) + Latin recogniser (CTC).
// Used for phone photos and handwriting, where Tesseract misses handwritten digits and names.
// Same output as the Tesseract path: lines of words {text, bbox:[x0,y0,x1,y1], conf} in image pixels.
//
//   const ocr = await createPaddleOcr(ort, { det: detBytesOrUrl, rec: recBytesOrUrl, dict: [...chars] });
//   const lines = await ocr.recognize({ width, height, rgb });   // rgb: Uint8Array, 3 bytes per pixel
//
// Runs fully offline: the caller hands in the model bytes (or this site's own URLs).

const MEAN = [0.485, 0.456, 0.406], STD = [0.229, 0.224, 0.225];

export async function createPaddleOcr(ort, { det, rec, dict, detLimit = 1600, detThresh = 0.3, boxThresh = 0.5,
  unclip = 1.6, recHeight = 48, minScore = 0.5, opts = {} } = {}) {
  const sess = m => ort.InferenceSession.create(m, { executionProviders: ["wasm"], graphOptimizationLevel: "all", logSeverityLevel: 3, ...opts });
  const [detS, recS] = await Promise.all([sess(det), sess(rec)]);
  const chars = ["", ...dict, " "];   // CTC blank first; PaddleOCR appends the space class last

  async function detect(img) {
    const { width: W, height: H, rgb } = img;
    const r = Math.min(1, detLimit / Math.max(W, H));
    const w = Math.max(32, Math.round(W * r / 32) * 32), h = Math.max(32, Math.round(H * r / 32) * 32);
    const sx = W / w, sy = H / h, x = new Float32Array(3 * w * h);
    for (let yy = 0; yy < h; yy++) {
      const y0 = Math.min(H - 1, Math.floor((yy + 0.5) * sy));
      for (let xx = 0; xx < w; xx++) {
        const s = (y0 * W + Math.min(W - 1, Math.floor((xx + 0.5) * sx))) * 3, o = yy * w + xx;
        // PaddleOCR feeds BGR: channel 0 = blue
        x[o] = (rgb[s + 2] / 255 - MEAN[0]) / STD[0];
        x[w * h + o] = (rgb[s + 1] / 255 - MEAN[1]) / STD[1];
        x[2 * w * h + o] = (rgb[s] / 255 - MEAN[2]) / STD[2];
      }
    }
    const out = await detS.run({ [detS.inputNames[0]]: new ort.Tensor("float32", x, [1, 3, h, w]) });
    const prob = out[detS.outputNames[0]].data;
    // connected components of the thresholded map; one axis-aligned box per component
    const lab = new Int32Array(w * h), boxes = [], stack = [];
    for (let i = 0; i < w * h; i++) {
      if (lab[i] || prob[i] < detThresh) continue;
      let x0 = w, y0 = h, x1 = 0, y1 = 0, n = 0, sum = 0;
      lab[i] = 1; stack.push(i);
      while (stack.length) {
        const j = stack.pop(), jx = j % w, jy = (j / w) | 0;
        n++; sum += prob[j];
        if (jx < x0) x0 = jx; if (jx > x1) x1 = jx; if (jy < y0) y0 = jy; if (jy > y1) y1 = jy;
        for (const k of [j - 1, j + 1, j - w, j + w]) {
          if (k < 0 || k >= w * h || lab[k] || prob[k] < detThresh) continue;
          if ((k === j - 1 && jx === 0) || (k === j + 1 && jx === w - 1)) continue;
          lab[k] = 1; stack.push(k);
        }
      }
      const bw = x1 - x0 + 1, bh = y1 - y0 + 1;
      if (n < 6 || Math.min(bw, bh) < 3 || sum / n < boxThresh) continue;
      // DB shrinks text regions when training; grow back by area * unclip / perimeter
      const d = n * unclip / (2 * (bw + bh));
      boxes.push([Math.max(0, (x0 - d) * sx), Math.max(0, (y0 - d) * sy), Math.min(W, (x1 + 1 + d) * sx), Math.min(H, (y1 + 1 + d) * sy)]);
    }
    return boxes;
  }

  // crop a box, resize to recHeight (bilinear), normalise to [-1, 1] in BGR
  function crop(img, [bx0, by0, bx1, by1]) {
    const { width: W, rgb } = img, cw = bx1 - bx0, ch = by1 - by0;
    const h = recHeight, w = Math.max(8, Math.min(3200, Math.round(cw * h / ch)));
    const x = new Float32Array(3 * w * h);
    for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) {
      const fx = bx0 + (xx + 0.5) * cw / w - 0.5, fy = by0 + (yy + 0.5) * ch / h - 0.5;
      const ix = Math.max(0, Math.floor(fx)), iy = Math.max(0, Math.floor(fy)), ax = Math.min(1, Math.max(0, fx - ix)), ay = Math.min(1, Math.max(0, fy - iy));
      const ix1 = Math.min(W - 1, ix + 1), iy1 = Math.min(img.height - 1, iy + 1);
      for (let c = 0; c < 3; c++) {
        const p = (yy0, xx0) => rgb[(yy0 * W + xx0) * 3 + c];
        const v = (p(iy, ix) * (1 - ax) + p(iy, ix1) * ax) * (1 - ay) + (p(iy1, ix) * (1 - ax) + p(iy1, ix1) * ax) * ay;
        x[(2 - c) * w * h + yy * w + xx] = (v / 255 - 0.5) / 0.5;
      }
    }
    return { x, w };
  }

  async function read(img, box) {
    const { x, w } = crop(img, box);
    const out = await recS.run({ [recS.inputNames[0]]: new ort.Tensor("float32", x, [1, 3, recHeight, w]) });
    const t = out[recS.outputNames[0]], [, T, C] = t.dims, p = t.data;
    // greedy CTC; keep the time step of every character so words get their own boxes
    const seq = [];
    let prev = 0;
    for (let i = 0; i < T; i++) {
      let best = 0, bp = -1;
      for (let c = 0; c < C; c++) if (p[i * C + c] > bp) { bp = p[i * C + c]; best = c; }
      if (best !== 0 && best !== prev) seq.push({ ch: chars[best] ?? "", t: i, p: bp });
      prev = best;
    }
    const step = (box[2] - box[0]) / T, words = [];
    let cur = null;
    for (const s of seq) {
      if (s.ch === " ") { cur = null; continue; }
      if (!cur) words.push(cur = { text: "", t0: s.t, t1: s.t, ps: [] });
      cur.text += s.ch; cur.t1 = s.t; cur.ps.push(s.p);
    }
    return words.map(wd => ({
      text: fixCase(wd.text),
      conf: wd.ps.reduce((a, b) => a + b, 0) / wd.ps.length,
      bbox: [Math.max(box[0], box[0] + (wd.t0 - 0.5) * step), box[1], Math.min(box[2], box[0] + (wd.t1 + 1.5) * step), box[3]],
    }));
  }

  async function recognize(img) {
    const boxes = await detect(img);
    // reading order: top to bottom, then left to right within a row
    boxes.sort((a, b) => (a[1] + a[3]) / 2 - (b[1] + b[3]) / 2);
    const lines = [];
    for (const b of boxes) {
      if ((b[3] - b[1]) > 1.6 * (b[2] - b[0])) continue;   // vertical text: not on these forms
      const words = (await read(img, b)).filter(wd => wd.conf >= minScore && wd.text.trim());
      if (words.length) lines.push(words);
    }
    // join boxes on the same row (Paddle splits a row at wide gaps: label | value)
    const rows = [];
    for (const l of lines) {
      const cy = (l[0].bbox[1] + l[0].bbox[3]) / 2, lh = l[0].bbox[3] - l[0].bbox[1];
      const row = rows.find(r => Math.abs(r.cy - cy) < 0.5 * Math.min(lh, r.lh));
      if (row) row.words.push(...l); else rows.push({ cy, lh, words: [...l] });
    }
    return rows.map(r => r.words.sort((a, b) => a.bbox[0] - b.bbox[0]));
  }

  return { recognize, detect, read };
}

// The Latin recogniser mixes cases inside Turkish capitals ("SözERi", "HACısALiHOĞLU"): a word that is
// mostly capitals is upper-cased the Turkish way (i -> İ, ı -> I), and its suffix after an apostrophe is kept.
export function fixCase(w) {
  const [stem, ...rest] = w.split(/(?=['’])/);
  const letters = [...stem].filter(c => /\p{L}/u.test(c)), up = letters.filter(c => c !== c.toLocaleLowerCase("tr")).length;
  if (letters.length < 3 || up === letters.length || up * 2 < letters.length) return w;
  return stem.toLocaleUpperCase("tr") + rest.join("");
}

// PNG/JPEG bytes -> {width, height, rgb} via MuPDF (already loaded for PDFs; works in the browser and in Node)
export function decodeImage(mupdf, bytes) {
  const pix = new mupdf.Image(bytes).toPixmap();
  const rgbPix = pix.getColorSpace()?.getName?.() === "DeviceRGB" && !pix.getAlpha() ? pix : pix.convertToColorSpace(mupdf.ColorSpace.DeviceRGB, false);
  const W = rgbPix.getWidth(), H = rgbPix.getHeight(), n = rgbPix.getNumberOfComponents() + (rgbPix.getAlpha() ? 1 : 0), stride = rgbPix.getStride(), px = rgbPix.getPixels();
  const rgb = new Uint8Array(W * H * 3);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) for (let c = 0; c < 3; c++) rgb[(y * W + x) * 3 + c] = px[y * stride + x * n + c];
  return { width: W, height: H, rgb };
}
