// Browsers: models cached in Cache Storage under their pinned URL; nothing is cached when it is unavailable.
import type { OrtLike } from "../model/ner.js";
import type { Runtime } from "./types.js";

const CACHE = "katip-mask-models";
const open = async () => (typeof caches === "undefined" ? null : caches.open(CACHE).catch(() => null));

export const cacheDir = () => `CacheStorage:${CACHE}`;

export const runtime: Runtime = {
  kind: "browser",
  async loadOrt() {
    try {
      const m = await import("onnxruntime-web" as string);
      return (m.default ?? m) as unknown as OrtLike;
    } catch {
      throw new Error("katip-mask: the name models need onnxruntime-web in the browser: npm install onnxruntime-web");
    }
  },
  async sha256(data) {
    const h = new Uint8Array(await crypto.subtle.digest("SHA-256", data));
    return [...h].map(b => b.toString(16).padStart(2, "0")).join("");
  },
  async read(_m, _r, _f, url) {
    const c = await open();
    const hit = c && (await c.match(url));
    return hit ? new Uint8Array(await hit.arrayBuffer()) : null;
  },
  async write(_m, _r, _f, url, data) {
    const c = await open();
    if (c) await c.put(url, new Response(data)).catch(() => undefined);
  },
  async remove(_m, _r, _f, url) {
    const c = await open();
    if (c) await c.delete(url);
  },
};
