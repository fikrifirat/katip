/**
 * Katip Mask: find and mask Turkish personal data (KVKK) in the browser or in Node, on the user's own device.
 *
 * The guarantee is narrow and stated plainly: every value the detector finds is masked everywhere it occurs,
 * or masking fails with LeakError. Values the detector does not find are not covered.
 */
import { detect as engineDetect } from "./engine/detect.js";
import { toWorkingText } from "./engine/py.js";
import { ENGINE_SHA256 } from "./engine/generated.js";
import { NameModel } from "./model/ner.js";
import { loadModel, type ModelName, type ModelOptions } from "./model/models.js";
import { idNumbers, propagate, render, restore as restoreText, safeSpans, type RawSpan } from "./safety.js";
import { PROFILE_SPEC } from "./spec.generated.js";

export { LeakError } from "./safety.js";
export { ModelError, MODELS, downloadModel, loadModel, loadModelFromFiles, modelUrl, type ModelName, type ModelOptions } from "./model/models.js";
export { NameModel, type ModelFiles, type OrtLike } from "./model/ner.js";
export { ENGINE_SHA256 };
export { cacheDir } from "#runtime";
export const VERSION = "0.1.1";

export type Profile = keyof typeof PROFILE_SPEC.profiles;
export type EntityType = keyof typeof PROFILE_SPEC.labels_tr;
export const PROFILES = PROFILE_SPEC.profiles;
export const LABELS_TR: Record<string, string> = PROFILE_SPEC.labels_tr;
export const ENTITY_TYPES = Object.keys(PROFILE_SPEC.labels_tr) as EntityType[];
export const DEFAULT_THRESHOLD = PROFILE_SPEC.default_threshold;

/** One detected value. start/end are UTF-16 offsets into the input string, so `input.slice(start, end) === text`. */
export interface Span {
  entityType: EntityType | string;
  start: number;
  end: number;
  text: string;
  score: number;
  recognizer: string;
  explanation: string;
}

export interface MaskResult {
  /** The masked text. */
  text: string;
  /** Everything that was masked, in document order. */
  spans: Span[];
  /** Placeholder -> original value (style "label"). Keep it on your side; never send it with the text. */
  mapping: Record<string, string>;
  profile: Profile;
  model: string | null;
  /** Put the original values back into text that contains the placeholders, e.g. an AI model's answer. */
  restore(text: string): string;
}

export interface MaskerOptions extends ModelOptions {
  /** "court" (court filing, default), "ai" (sharing with AI) or "anon" (fully anonymous). */
  profile?: Profile;
  /** null/undefined: rules only. "mini" (recommended), "nano" (fastest), "base" (most accurate), or a loaded NameModel. */
  model?: ModelName | NameModel | null;
  /** Minimum confidence for a rule or model hit (default 0.5). */
  threshold?: number;
  /** Replace the profile's entity types. */
  entities?: readonly string[];
  /** "street" keeps mahalle/street/district/province readable; "full" masks the whole address. Default: the profile's. */
  addressDetail?: "street" | "full";
  /** Terms never masked. */
  allow?: readonly string[];
  /** Terms always masked (whole words, case-insensitive). */
  deny?: readonly string[];
  /** "label" -> "[AD SOYAD-1]" (reversible), "block" -> "██████". */
  style?: "label" | "block";
}

export interface TextOptions {
  /** [start, end) UTF-16 ranges of the text that came from OCR (misread IDs and handwritten form values are caught there). */
  ocrRanges?: ReadonlyArray<readonly [number, number]>;
}

export class Masker {
  readonly profile: Profile;
  readonly entities: string[];
  readonly addressDetail: "street" | "full";
  readonly threshold: number;
  readonly style: "label" | "block";
  private allow: string[];
  private deny: string[];
  private nameModel: NameModel | null;

  /** Rules only, or with a NameModel you already loaded. Use Masker.create() to load a model by name. */
  constructor(o: Omit<MaskerOptions, "model"> & { model?: NameModel | null } = {}) {
    const profile = o.profile ?? (PROFILE_SPEC.default_profile as Profile);
    const p = PROFILES[profile];
    if (!p) throw new Error(`unknown profile ${String(profile)}: use ${Object.keys(PROFILES).join(", ")}`);
    if (o.style && o.style !== "label" && o.style !== "block") throw new Error('style must be "label" or "block"');
    const unknown = (o.entities ?? []).filter(e => !(e in LABELS_TR));
    if (unknown.length) throw new Error(`unknown entity types ${unknown.join(", ")}: see ENTITY_TYPES`);
    if (typeof o.model === "string") throw new Error("load a model by name with `await Masker.create({ model })`");
    this.profile = profile;
    this.entities = o.entities?.length ? [...o.entities] : [...p.entities];
    this.addressDetail = o.addressDetail ?? p.address_detail;
    this.threshold = o.threshold ?? DEFAULT_THRESHOLD;
    this.style = o.style ?? "label";
    this.allow = [...(o.allow ?? [])];
    this.deny = [...(o.deny ?? [])];
    this.nameModel = o.model ?? null;
  }

  /** A Masker, loading (downloading once, verifying) the named model first. */
  static async create(o: MaskerOptions = {}): Promise<Masker> {
    const model = typeof o.model === "string" ? await loadModel(o.model, o) : o.model ?? null;
    return new Masker({ ...o, model });
  }

  get model(): string | null { return this.nameModel?.name ?? null; }

  private run(text: string, extra: Array<[number, number, number, string]>, o: TextOptions, wt = toWorkingText(text)) {
    const ocrRanges = (o.ocrRanges ?? []).map(([a, b]) => [wt.fromUtf16(a), wt.fromUtf16(b)] as [number, number]);
    let spans: RawSpan[] = engineDetect(wt.text, {
      threshold: this.threshold, entities: this.entities, maskTerms: this.deny.map(t => toWorkingText(t).text),
      allowTerms: this.allow.map(t => toWorkingText(t).text), extra,
      trust: this.trustOverride !== undefined ? this.trustOverride : this.nameModel ? this.nameModel.trust : null, ocrRanges, addressDetail: this.addressDetail,
    });
    if (this.entities.includes("TCKN") || this.entities.includes("YKN")) spans = idNumbers(wt.text, spans);
    return { wt, spans: propagate(wt.text, spans) };
  }

  private toPublic(text: string, wt: ReturnType<typeof toWorkingText>, spans: RawSpan[]): Span[] {
    return spans.map(s => {
      const start = wt.toUtf16(s.start), end = wt.toUtf16(s.end);
      return { entityType: s.entity_type, start, end, text: text.slice(start, end), score: s.score, recognizer: s.recognizer, explanation: s.explanation };
    });
  }

  private finish(text: string, wt: ReturnType<typeof toWorkingText>, spans: RawSpan[]): MaskResult {
    const pub = this.toPublic(text, wt, safeSpans(wt.text, spans));
    const r = render(text, pub.map(s => ({ entity_type: s.entityType, start: s.start, end: s.end, text: s.text })), this.style, LABELS_TR);
    const mapping = r.mapping;
    return { text: r.text, spans: pub, mapping, profile: this.profile, model: this.model, restore: (t: string) => restoreText(t, mapping) };
  }

  private async extra(wtText: string) {
    return this.nameModel ? await this.nameModel.spans(wtText, this.threshold) : [];
  }

  /** Find personal data without masking. */
  async detect(text: string, o: TextOptions = {}): Promise<Span[]> {
    const wt = toWorkingText(text);
    const r = this.run(text, await this.extra(wt.text), o, wt);
    return this.toPublic(text, r.wt, r.spans);
  }

  /** Mask the text. Rejects with LeakError rather than return text in which a detected value is still readable. */
  async mask(text: string, o: TextOptions = {}): Promise<MaskResult> {
    const wt = toWorkingText(text);
    const r = this.run(text, await this.extra(wt.text), o, wt);
    return this.finish(text, r.wt, r.spans);
  }

  /** @internal Parity tests: mask with given model spans ([start, end, score, type] in code point offsets). */
  _maskWithModelSpans(text: string, extra: Array<[number, number, number, string]>, trust: number | null, o: TextOptions = {}): MaskResult {
    const saved = this.trustOverride;
    this.trustOverride = trust;
    try {
      const r = this.run(text, extra, o);
      return this.finish(text, r.wt, r.spans);
    } finally { this.trustOverride = saved; }
  }
  private trustOverride: number | null | undefined = undefined;

  /** Synchronous detect, rules only (throws if this Masker has a model). */
  detectSync(text: string, o: TextOptions = {}): Span[] {
    this.rulesOnly();
    const r = this.run(text, [], o);
    return this.toPublic(text, r.wt, r.spans);
  }

  /** Synchronous mask, rules only (throws if this Masker has a model). */
  maskSync(text: string, o: TextOptions = {}): MaskResult {
    this.rulesOnly();
    const r = this.run(text, [], o);
    return this.finish(text, r.wt, r.spans);
  }

  private rulesOnly() {
    if (this.nameModel) throw new Error("this Masker has a model: use the async mask()/detect()");
  }
}

/** Mask with a one-off Masker (reuse a Masker for many documents). */
export async function mask(text: string, o: MaskerOptions & TextOptions = {}): Promise<MaskResult> {
  return (await Masker.create(o)).mask(text, o);
}

/** Detect with a one-off Masker. */
export async function detect(text: string, o: MaskerOptions & TextOptions = {}): Promise<Span[]> {
  return (await Masker.create(o)).detect(text, o);
}

/** Put original values back in place of placeholders, using a MaskResult.mapping you stored. */
export function restore(text: string, mapping: Record<string, string>): string {
  return restoreText(text, mapping);
}



