// Node: models cached on disk in the same place as the Python SDK, so one download serves both.
import { createHash } from "node:crypto";
import { mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import type { OrtLike } from "../model/ner.js";
import type { Runtime } from "./types.js";

export function cacheDir(): string {
  if (process.env.KATIP_MASK_CACHE) return process.env.KATIP_MASK_CACHE.replace(/^~(?=$|\/)/, homedir());
  return join(process.env.XDG_CACHE_HOME || join(homedir(), ".cache"), "katip-mask");
}

const path = (model: string, revision: string, file: string) => join(cacheDir(), model, revision, ...file.split("/"));

export const runtime: Runtime = {
  kind: "node",
  async loadOrt() {
    try {
      const m = await import(/* webpackIgnore: true */ "onnxruntime-node" as string);
      return (m.default ?? m) as OrtLike;
    } catch {
      throw new Error("katip-mask: the name models need onnxruntime-node in Node: npm install onnxruntime-node");
    }
  },
  async sha256(data) { return createHash("sha256").update(data).digest("hex"); },
  async read(model, revision, file) {
    try { return new Uint8Array(await readFile(path(model, revision, file))); } catch { return null; }
  },
  async write(model, revision, file, _url, data) {
    const p = path(model, revision, file);
    await mkdir(dirname(p), { recursive: true });
    const tmp = `${p}.part-${process.pid}-${Date.now()}`;
    await writeFile(tmp, data);
    await rename(tmp, p);
  },
  async remove(model, revision, file) { await rm(path(model, revision, file), { force: true }); },
};
