// Katip Mask models: fetched once from Hugging Face at a pinned commit, every file verified by SHA-256.
import { runtime } from "#runtime";
import { MODEL_SPEC } from "../spec.generated.js";
import { NameModel, type ModelFiles, type OrtLike } from "./ner.js";

export type ModelName = keyof typeof MODEL_SPEC.models;
export const MODELS = MODEL_SPEC.models;
const FILES = ["config.json", "tokenizer.json", "onnx/model_quantized.onnx"] as const;

export interface ModelOptions {
  /** Serve the model files yourself (e.g. for a strict CSP): files are read from `${modelBaseUrl}/${model}/${file}`.
   *  They are still verified against the pinned SHA-256. Default: Hugging Face at the pinned revision. */
  modelBaseUrl?: string;
  /** Never download; fail unless the model is already cached. */
  offline?: boolean;
  /** Your own fetch (proxies, auth). */
  fetch?: typeof fetch;
  /** Your own onnxruntime module, e.g. `await import("onnxruntime-web/webgpu")`. */
  ort?: OrtLike;
  /** Extra InferenceSession options. */
  sessionOptions?: Record<string, unknown>;
  /** Progress messages while downloading. */
  onProgress?: (message: string) => void;
}

export class ModelError extends Error { override name = "ModelError"; }

const env = (k: string) => (typeof process !== "undefined" ? process.env?.[k] : undefined);

export function modelUrl(name: ModelName, file: string, base?: string): string {
  const info = MODELS[name];
  if (base) return `${base.replace(/\/+$/, "")}/${name}/${file}`;
  const endpoint = (env("KATIP_MASK_ENDPOINT") || env("HF_ENDPOINT") || MODEL_SPEC.endpoint).replace(/\/+$/, "");
  return `${endpoint}/${info.repo}/resolve/${info.revision}/${file}`;
}

/** Download (if needed) and verify the files of a model; returns their bytes. */
export async function modelFiles(name: ModelName, o: ModelOptions = {}): Promise<ModelFiles> {
  const info = MODELS[name];
  if (!info) throw new ModelError(`unknown model ${String(name)}: use ${Object.keys(MODELS).join(", ")}`);
  const offline = o.offline || /^(1|true|yes)$/i.test(env("KATIP_MASK_OFFLINE") ?? "");
  const out: Uint8Array[] = [];
  for (const file of FILES) {
    const want = info.files[file];
    const url = modelUrl(name, file, o.modelBaseUrl);
    let data = await runtime.read(name, info.revision, file, url);
    if (data && (data.length !== want.size || (await runtime.sha256(data)) !== want.sha256)) {
      await runtime.remove(name, info.revision, file, url);
      data = null;
    }
    if (!data) {
      if (offline) throw new ModelError(`${info.name} is not downloaded and downloads are off`);
      o.onProgress?.(`downloading ${info.name}: ${file} (${(want.size / 1e6).toFixed(1)} MB)`);
      const res = await (o.fetch ?? fetch)(url);
      if (!res.ok) throw new ModelError(`${info.name}: ${file}: HTTP ${res.status}`);
      data = new Uint8Array(await res.arrayBuffer());
      if ((await runtime.sha256(data)) !== want.sha256)
        throw new ModelError(`${info.name}: ${file} does not match its pinned SHA-256; refusing to use it`);
      await runtime.write(name, info.revision, file, url, data);
    }
    out.push(data);
  }
  return { config: out[0]!, tokenizer: out[1]!, onnx: out[2]! };
}

/** Download and verify a model now, so later runs work offline. */
export async function downloadModel(name: ModelName, o: ModelOptions = {}): Promise<void> {
  await modelFiles(name, o);
}

const loaded = new Map<string, Promise<NameModel>>();

export function loadModel(name: ModelName, o: ModelOptions = {}): Promise<NameModel> {
  const key = `${name}|${o.modelBaseUrl ?? ""}`;
  let p = loaded.get(key);
  if (!p) {
    p = (async () => {
      const files = await modelFiles(name, o);
      const ort = o.ort ?? (await runtime.loadOrt());
      return NameModel.load(`${name}@${MODELS[name].revision.slice(0, 7)}`, files, ort, MODELS[name].trust, o.sessionOptions);
    })();
    loaded.set(key, p);
    p.catch(() => loaded.delete(key));
  }
  return p;
}

/** A model from files you already have (your own fine-tune, or files bundled with your app). Not hash-checked. */
export async function loadModelFromFiles(name: string, files: ModelFiles, ort?: OrtLike, trust?: number): Promise<NameModel> {
  return NameModel.load(name, files, ort ?? (await runtime.loadOrt()), trust);
}
