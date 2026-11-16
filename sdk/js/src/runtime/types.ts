import type { OrtLike } from "../model/ner.js";

/** Where model files come from and where they are kept: file system in Node, Cache Storage in browsers. */
export interface Runtime {
  readonly kind: "node" | "browser";
  loadOrt(): Promise<OrtLike>;
  sha256(data: Uint8Array): Promise<string>;
  /** Cached bytes for this model file, or null. */
  read(model: string, revision: string, file: string, url: string): Promise<Uint8Array | null>;
  write(model: string, revision: string, file: string, url: string, data: Uint8Array): Promise<void>;
  remove(model: string, revision: string, file: string, url: string): Promise<void>;
}
