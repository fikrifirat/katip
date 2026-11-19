// TypeScript port of katip_redact/recognizers.py (vendored at sdk/python/src/katip_mask/_engine/recognizers.py).
// Line for line the same logic; every regex is the Python one compiled by sdk/tools/pyre2js.py.
// Keep this file in step with the Python source: the parity tests fail on any difference.
import {
  finditer, fold, fullmatch, isAllCaps, isAlnumChar, isCapitalised, isDigitChar, isUpperChar, islower, match, pyIn, search, sortBy,
  split, splitWs, startsWithAny, strip, rstrip, sub, wordlist, findall, lstrip, rfind, type PyMatch,
} from "./py.js";

export class RecognizerResult {
  recognition_metadata: { recognizer_name?: string; explanation?: string } = {};
  constructor(public entity_type: string, public start: number, public end: number, public score: number) {}
}

export const ENTITY_LABELS_TR: Record<string, string> = {
  TCKN: "T.C. Kimlik No", VKN: "Vergi Kimlik No", IBAN: "IBAN", CREDIT_CARD: "Kredi Kartı", PHONE: "Telefon", EMAIL: "E-posta",
  PLATE: "Araç Plakası", PERSON: "Ad Soyad", ADDRESS: "Adres", BIRTH_DATE: "Doğum Tarihi", IP_ADDRESS: "IP Adresi",
  YKN: "Yabancı Kimlik No", PASSPORT: "Pasaport No", FOREIGN_ID: "Yabancı Ülke Kimlik No", UETS: "UETS (e-Tebligat) Adresi",
  HEALTH: "Sağlık Verisi", RELIGION: "Din/İnanç", POLITICAL: "Siyasi Görüş", UNION: "Sendika Üyeliği", ETHNICITY: "Irk/Etnik Köken",
  SEXUAL_LIFE: "Cinsel Hayat", BIOMETRIC_GENETIC: "Biyometrik/Genetik", CRIMINAL_RECORD: "Ceza Mahkumiyeti",
};
export const SPECIAL_ENTITIES = ["HEALTH", "RELIGION", "POLITICAL", "UNION", "ETHNICITY", "SEXUAL_LIFE", "BIOMETRIC_GENETIC", "CRIMINAL_RECORD"];
export const ALL_ENTITIES = Object.keys(ENTITY_LABELS_TR);

const contextBefore = (text: string, start: number, window = 60) => fold(text.slice(Math.max(0, start - window), start));
export const hasContext = (text: string, start: number, words: readonly string[], window = 60) => {
  const ctx = contextBefore(text, start, window);
  return words.some(w => ctx.includes(w));
};

export interface Recognizer {
  supported_entities: string[];
  name: string;
  analyze(text: string, entities: string[]): RecognizerResult[];
}

function result(entity: string, name: string, start: number, end: number, score: number, why = ""): RecognizerResult {
  const r = new RecognizerResult(entity, start, end, score);
  r.recognition_metadata = { recognizer_name: name, explanation: why };
  return r;
}

// ---------------------------------------------------------------- checksums
const digitsOnly = (d: string) => d.length > 0 && [...d].every(isDigitChar);
/** Python int(c) for one Unicode decimal digit: its distance from the zero that starts its run of ten */
function digitValue(c: string): number {
  const n = c.codePointAt(0)!;
  if (n >= 48 && n <= 57) return n - 48;
  let z = n;
  while (z > n - 9 && /\p{Nd}/u.test(String.fromCodePoint(z - 1))) z--;
  return (n - z) % 10;
}
const ints = (d: string) => [...d].map(digitValue);

export function tcknValid(d: string): boolean {
  if ([...d].length !== 11 || !digitsOnly(d) || d[0] === "0") return false;
  const n = ints(d);
  const d10 = ((((n[0]! + n[2]! + n[4]! + n[6]! + n[8]!) * 7 - (n[1]! + n[3]! + n[5]! + n[7]!)) % 10) + 10) % 10;
  return d10 === n[9] && n.slice(0, 10).reduce((a, b) => a + b, 0) % 10 === n[10];
}

export function vknValid(d: string): boolean {
  if ([...d].length !== 10 || !digitsOnly(d)) return false;
  const n = ints(d);
  let total = 0;
  for (let i = 0; i < 9; i++) {
    const tmp = (n[i]! + (9 - i)) % 10;
    let v = (tmp * 2 ** (9 - i)) % 9;
    if (tmp !== 0 && v === 0) v = 9;
    total += v;
  }
  return (10 - (total % 10)) % 10 === n[9];
}

export function ibanValid(s: string): boolean {
  s = sub("inline.iban_ws", "", s).toUpperCase();
  if (!fullmatch("inline.iban_shape", s)) return false;
  if (s.startsWith("TR") && [...s].length !== 26) return false;
  let rem = 0;
  for (const c of s.slice(4) + s.slice(0, 4)) {
    const v = isDigitChar(c) ? String(ints(c)[0]) : String(parseInt(c, 36));
    for (const ch of v) rem = (rem * 10 + (ch.charCodeAt(0) - 48)) % 97;
  }
  return rem === 1;
}

export function luhnValid(d: string): boolean {
  d = sub("inline.non_digit", "", d);
  const n = ints(d);
  if (!(n.length >= 13 && n.length <= 19)) return false;
  let s = 0, alt = false;
  for (let i = n.length - 1; i >= 0; i--) {
    let x = n[i]!;
    if (alt) { x *= 2; if (x > 9) x -= 9; }
    s += x;
    alt = !alt;
  }
  return s % 10 === 0;
}

// ---------------------------------------------------------------- recognizers
class TCKNRecognizer implements Recognizer {
  name = "tckn_checksum";
  supported_entities = ["TCKN", "YKN"];
  static YKN_CTX = ["yabanci kimlik", "ykn", "y.k.n", "gecici koruma", "yabanci", "ikamet", "uyruklu"];
  static NOT_TC = ["pasaport", "passport", "ulusal", "national", "melli", "tazkira", "tezkire", "personal no", "kisisel",
    "ssn", "social security", "sosyal guvenlik no", "amka", "ausweis", "cni", "dni", "bsn", "fin"];
  static CTX = ["kimlik", "tckn", "t.c", "tc no", "tc:", "vatandaslik"];
  analyze(text: string): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    const r = (s: number, e: number, sc: number, why: string, entity?: string) => result(entity ?? "TCKN", this.name, s, e, sc, why);
    for (const m of finditer("TCKNRecognizer.RE", text)) {
      const digits = sub("inline.non_digit", "", m.group(1)!);
      if (tcknValid(digits) && digits.startsWith("99")) {
        const score = hasContext(text, m.start(), [...TCKNRecognizer.YKN_CTX, ...TCKNRecognizer.CTX]) ? 0.95 : 0.85;
        out.push(r(m.start(1), m.end(1), score, "11 digits from 99, TCKN checksum ok: foreigner ID (YKN)", "YKN"));
      } else if (tcknValid(digits)) {
        const score = hasContext(text, m.start(), TCKNRecognizer.CTX) ? 0.95 : 0.85;
        out.push(r(m.start(1), m.end(1), score, "11 digits, TCKN checksum ok"));
      }
    }
    for (const m of finditer("TCKNRecognizer.LABELLED", text)) {
      if (hasContext(text, m.start(1), TCKNRecognizer.NOT_TC, 40) && !hasContext(text, m.start(1), ["yabanci kimlik"], 30)) continue;
      if (!out.some(x => x.start <= m.start(1) && m.start(1) < x.end)) {
        const ykn = hasContext(text, m.start(1), ["yabanci kimlik", "ykn", "y.k.n", "gecici koruma"], 30) || m.group(1)!.startsWith("99");
        out.push(r(m.start(1), m.end(1), 0.7, "number after an ID label (checksum failed, likely OCR)", ykn ? "YKN" : undefined));
      }
    }
    return out;
  }
}

export function iranMelliValid(d: string): boolean {
  if ([...d].length !== 10 || !digitsOnly(d) || new Set(d).size === 1) return false;
  const n = ints(d);
  let s = 0;
  for (let i = 0; i < 9; i++) s += n[i]! * (10 - i);
  s %= 11;
  return n[9] === (s < 2 ? s : 11 - s);
}

function trim(text: string, s: number, e: number): number {
  const v = text.slice(s, e);
  const m = search("inline.trim_word", v);
  if (m) e = s + m.start();
  while (e > s && pyIn(text[e - 1]!, " -")) e -= 1;
  return e;
}
const countDigits = (s: string) => [...s].filter(isDigitChar).length;

class PassportRecognizer implements Recognizer {
  name = "passport_cue";
  supported_entities = ["PASSPORT"];
  analyze(text: string): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    for (const rx of ["PassportRecognizer.AFTER", "PassportRecognizer.BEFORE"]) {
      for (const m of finditer(rx, text)) {
        const s = m.start(1), e = trim(text, m.start(1), m.end(1));
        const v = text.slice(s, e);
        const core = sub("inline.space_dash", "", v);
        if (core.length >= 6 && core.length <= 12 && countDigits(core) >= 5 && !fullmatch("inline.year_slash", v))
          out.push(result("PASSPORT", this.name, s, e, 0.9, "number after a passport cue"));
      }
    }
    for (const m of finditer("PassportRecognizer.MRZ2", text))
      out.push(result("PASSPORT", this.name, m.start(), m.end(), 0.95, "passport machine-readable zone, line 2 (number, birth date)"));
    for (const m of finditer("PassportRecognizer.MRZ1", text))
      out.push(result("PERSON", this.name, m.start(1), m.end(1), 0.95, "passport machine-readable zone, line 1 (name)"));
    return out;
  }
}

class ForeignIDRecognizer implements Recognizer {
  name = "foreign_id_cue";
  supported_entities = ["FOREIGN_ID"];
  analyze(text: string): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    for (const m of finditer("ForeignIDRecognizer.RX", text)) {
      const cue = text.slice(m.start(), m.start(1));
      if (match("ForeignIDRecognizer.SHORT", strip(cue)) && m.start() > 0 && isAlnumChar(text[m.start() - 1]!)) continue;
      const s = m.start(1), e = trim(text, m.start(1), m.end(1));
      const core = sub("inline.space_dash", "", text.slice(s, e));
      const fin = !!match("inline.fin_cue", strip(cue));
      const n = [...core].length;
      const ok = fin ? n === 7 && countDigits(core) >= 1 : n >= 6 && n <= 16 && countDigits(core) >= 5;
      if (ok && !fullmatch("inline.year_slash", text.slice(s, e)))
        out.push(result("FOREIGN_ID", this.name, s, e, 0.85, `number after a foreign ID cue (${strip(cue, " :.")})`));
    }
    for (const m of finditer("ForeignIDRecognizer.MELLI", text)) {
      const d = m.group(1)!.replaceAll("-", "");
      if (iranMelliValid(d) && hasContext(text, m.start(), ["iran", "melli", "kod", "ulusal", "national"], 50))
        out.push(result("FOREIGN_ID", this.name, m.start(1), m.end(1), 0.9, "Iranian national code, check digit ok"));
    }
    return out;
  }
}

class UETSRecognizer implements Recognizer {
  name = "uets";
  supported_entities = ["UETS"];
  static CTX = ["uets", "tebligat", "kep"];
  analyze(text: string): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    for (const m of finditer("UETSRecognizer.SHAPED", text)) {
      const cue = hasContext(text, m.start(1), UETSRecognizer.CTX, 40);
      out.push(result("UETS", this.name, m.start(1), m.end(1), cue ? 0.95 : 0.8,
        "UETS e-Tebligat address" + (cue ? " after a UETS cue" : " (5-5-5 digits)")));
    }
    for (const m of finditer("UETSRecognizer.CUED", text))
      out.push(result("UETS", this.name, m.start(1), m.end(1), 0.95, "15 digits after a UETS / e-Tebligat cue"));
    return out;
  }
}

class VKNRecognizer implements Recognizer {
  name = "vkn_checksum_context";
  supported_entities = ["VKN"];
  static CTX = ["vergi", "vkn", "v.k.n", "vd.", "v.d", "vergi no", "vergi kimlik"];
  analyze(text: string): RecognizerResult[] {
    return finditer("VKNRecognizer.RE", text)
      .filter(m => vknValid(m.group(1)!) && hasContext(text, m.start(), VKNRecognizer.CTX, 50))
      .map(m => result("VKN", this.name, m.start(1), m.end(1), 0.8, "10 digits, VKN checksum + tax context"));
  }
}

class IBANRecognizer implements Recognizer {
  name = "iban_mod97";
  supported_entities = ["IBAN"];
  analyze(text: string): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    for (const m of finditer("IBANRecognizer.RE", text)) {
      const cand = m.group(1)!;
      const parts = split("inline.iban_split", cand) as string[];
      for (let k = parts.length; k > 0; k -= 2) {
        const c = parts.slice(0, k).join("");
        if (ibanValid(c)) { out.push(result("IBAN", this.name, m.start(1), m.start(1) + c.length, 0.95, "IBAN mod-97 ok")); break; }
      }
    }
    for (const m of finditer("IBANRecognizer.OCR_RE", text)) {
      if (out.some(r => r.start <= m.start() && m.start() < r.end)) continue;
      const fixed = "TR" + m.group()!.slice(2).replace(/[OoIlB]/g, c => ({ O: "0", o: "0", I: "1", l: "1", B: "8" })[c]!);
      const digits = sub("inline.iban_ws", "", fixed);
      const ok = ibanValid(fixed);
      if (ok || [25, 26, 27].includes([...digits].length))
        out.push(result("IBAN", this.name, m.start(), m.end(), ok ? 0.9 : 0.65, ok ? "IBAN after OCR fix" : "TR IBAN shape (OCR, checksum failed)"));
    }
    return out;
  }
}

class CreditCardRecognizer implements Recognizer {
  name = "card_luhn";
  supported_entities = ["CREDIT_CARD"];
  analyze(text: string): RecognizerResult[] {
    return finditer("CreditCardRecognizer.RE", text)
      .filter(m => { const d = sub("inline.non_digit", "", m.group(1)!); return luhnValid(d) && (pyIn(d[0]!, "3456") || d.startsWith("9792")) && !tcknValid(d); })
      .map(m => result("CREDIT_CARD", this.name, m.start(1), m.end(1), 0.8, "Luhn ok"));
  }
}

class EmailRecognizer implements Recognizer {
  name = "email_regex";
  supported_entities = ["EMAIL"];
  analyze(text: string): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    for (const m of finditer("EmailRecognizer.RE", text)) {
      const role = !!match("EmailRecognizer.ROLE", m.group()!);
      out.push(result("EMAIL", this.name, m.start(), m.end(), role ? 0.35 : 0.95, role ? "role mailbox" : "email shape"));
    }
    for (const rx of ["EmailRecognizer.OCR_RE", "EmailRecognizer.OCR_SYM"]) {
      for (const m of finditer(rx, text)) {
        if (m.group()!.includes("@") || out.some(r => r.start <= m.start() && m.start() < r.end)) continue;
        out.push(result("EMAIL", this.name, m.start(), m.end(), 0.8, "e-mail with OCR-garbled @"));
      }
    }
    return out;
  }
}

class PhoneRecognizer implements Recognizer {
  name = "tr_phone";
  supported_entities = ["PHONE"];
  static CTX = ["tel", "gsm", "cep", "telefon", "phone", "faks", "fax", "irtibat"];
  analyze(text: string): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    for (const m of finditer("PhoneRecognizer.RE", text)) out.push(result("PHONE", this.name, m.start(), m.end(), 0.85, "TR phone with prefix"));
    for (const m of finditer("PhoneRecognizer.BARE", text))
      if (hasContext(text, m.start(), PhoneRecognizer.CTX, 30))
        out.push(result("PHONE", this.name, m.start(1), m.end(1), 0.7, "bare mobile number + phone context"));
    return out;
  }
}

class PlateRecognizer implements Recognizer {
  name = "tr_plate";
  supported_entities = ["PLATE"];
  static BAD = new Set(["TL", "TRY", "USD", "EUR", "KDV", "AS", "NO", "MD", "HD", "CD", "E", "K", "T", "M", "S"]);
  static CTX = ["plaka", "arac", "araç", "plakali", "plakalı", "vasita", "otomobil"];
  analyze(text: string): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    for (const m of finditer("PlateRecognizer.RE", text)) {
      const letters = m.group(2)!, digits = m.group(3)!;
      const ok = (letters.length === 1 && [4, 5].includes(digits.length)) || (letters.length === 2 && [3, 4].includes(digits.length)) ||
        (letters.length === 3 && [2, 3].includes(digits.length));
      if (!ok) continue;
      const ctx = hasContext(text, m.start(), PlateRecognizer.CTX, 60) ||
        PlateRecognizer.CTX.some(c => fold(text.slice(m.end(), m.end() + 25)).includes(c));
      if (PlateRecognizer.BAD.has(letters) && !ctx) continue;
      out.push(result("PLATE", this.name, m.start(), m.end(), ctx ? 0.9 : 0.65, "TR plate shape"));
    }
    return out;
  }
}

class IPRecognizer implements Recognizer {
  name = "ipv4";
  supported_entities = ["IP_ADDRESS"];
  analyze(text: string) {
    return finditer("IPRecognizer.RE", text).map(m => result("IP_ADDRESS", this.name, m.start(1), m.end(1), 0.6, "IPv4"));
  }
}

class BirthDateRecognizer implements Recognizer {
  name = "birth_date_context";
  supported_entities = ["BIRTH_DATE"];
  static CTX = ["dogum tarihi", "d.tarihi", "dogum t", "d. tarihi", "dogumlu", "d.t.", "dogum yeri ve tarihi"];
  analyze(text: string) {
    const out: RecognizerResult[] = [];
    for (const m of finditer("BirthDateRecognizer.RE", text)) {
      const after = fold(text.slice(m.end(), m.end() + 25));
      const before = fold(text.slice(Math.max(0, m.start() - 12), m.start()));
      if (hasContext(text, m.start(), BirthDateRecognizer.CTX, 35) || match("BirthDateRecognizer.AFTER", after) || search("BirthDateRecognizer.BEFORE", before))
        out.push(result("BIRTH_DATE", this.name, m.start(1), m.end(1), 0.85, "date + birth context"));
    }
    return out;
  }
}

// ---------------------------------------------------------------- person names
export const PERSON_CUES = [
  "davaci", "davali", "davacilar", "davalilar", "vekili", "vekilleri", "av.", "avukat",
  "sayin", "sn.", "hakim", "katip", "uye", "baskan", "bay ", "bayan", "adi soyadi",
  "ad soyad", "adi-soyadi", "kiraci", "kiraya veren", "alici", "satici", "isci",
  "isveren vekili", "muvekkil", "vekil eden", "vekalet veren", "borclu", "alacakli",
  "musteki", "magdur", "sanik", "supheli", "tanik", "murisi", "muris", "mirasci",
  "basvurucu", "basvuran", "ihtar eden", "muhatap", "kefil", "veli", "vasi",
  "ilgili kisi", "hasta", "calisan", "personel", "imza", "duzenleyen", "teslim alan",
  "teslim eden", "katip", "zabit", "bilirkisi", "arabulucu", "noter", "sorumlu",
  "cocugu", "cocuklari", "esi", "annesi", "babasi", "kardesi", "mirascisi", "yetkili", "ihtar eden", "kefil",
  "kimden", "kime", "gonderen", "alici:", "bilgi:", "cc:", "from:", "to:", "katilimcilar", "katilanlar",
  "hazirlayan", "merhaba", "sevgili", "degerli", "dr.", "prof.", "doc.", "uzm.", "refakatci", "hekim",
  "karsi taraf", "dinlenen", "yakini", "ogretmen", "sofor", "surucu",
];
export const LEGAL_TITLE = ["kanun", "vatandaslig", "yonetmeli", "medeni", "borclar", "kazanilmas", "uygulanmas", "tuzug",
  "genelge", "anayasa", "mevzuat", "yasasi", "yasasin", "teskilat", "telekom", "lirasi", "hava yollari",
  "silahli", "milleti", "devleti", "ceza kanun", "ticaret kanun"];
const ORG_TAIL = ["a.s", "a.ş", "ltd", "sti", "şti", "limited", "anonim", "sirketi", "şirketi", "sanayi", "san.",
  "ticaret", "tic.", "insaat", "lojistik", "yazilim", "teknoloji", "turizm", "gida", "enerji",
  "holding", "bankasi", "bankası", "vakfi", "derneği", "dernegi", "kooperatifi",
  "universitesi", "belediyesi", "mahkemesi", "bakanligi", "baskanligi", "hastanesi", "noterligi",
  "mudurlugu", "dairesi", "barosu", "grubu", "group", "inc", "gmbh"];
const INFL = [...new Set(["larinin", "lerinin", "larin", "lerin", "larina", "lerine", "larindan", "lerinden", "larinda", "lerinde", "lari", "leri",
  "lar", "ler", "sinin", "sunun", "sina", "sine", "suna", "sinda", "sinde", "sindan", "sinden", "si", "su",
  "nin", "nun", "na", "ne", "nda", "nde", "ndan", "nden", "in", "un", "i", "u", "a", "e", "da", "de",
  "dan", "den", "ta", "te", "tan", "ten", "ya", "ye", "yi", "yu", "yla", "yle", "la", "le", "ca", "ce",
  "cilik", "lik", "luk", "li", "lu", "siz", "suz", "dir", "tir", "dur", "tur", "ki", "daki", "deki",
  "inda", "inde", "indan", "inden", "ina", "ine", "imiz", "iniz", "umuz", "unuz", "ligi", "lugu",
  "ligin", "lugun", "ligine", "lugune", "ligini", "lugunu", "ini", "unu", "dik", "tik", "duk", "tuk",
  "digi", "tigi", "dugu", "tugu", "digindan", "tigindan", "dugundan", "tugundan", "ilan", "ilen",
  "im", "um", "imiz", "umuz", "imizin", "umuzun", "imize", "umuza", "ime", "uma"])];
// Python sorts a set by length only, so equal-length suffixes come in hash order; the result
// (any matching suffix -> True) does not depend on that order.
INFL.sort((a, b) => b.length - a.length);
const MUTATE: Record<string, string> = { d: "t", g: "k", b: "p", c: "c" };

function inflectedCommon(f: string): boolean {
  const common = wordlist("common_words.txt");
  for (const suf of INFL) {
    if (f.endsWith(suf) && [...f].length - [...suf].length >= 3) {
      const stem = f.slice(0, f.length - suf.length);
      const last = stem.slice(-1);
      if (common.has(stem) || (last in MUTATE && common.has(stem.slice(0, -1) + MUTATE[last]))) return true;
    }
  }
  return false;
}

export function isLexical(tok: string): boolean {
  const f = fold(tok);
  if (wordlist("first_names.txt").has(f) || wordlist("last_names.txt").has(f)) return false;
  if (wordlist("common_words.txt").has(f) || wordlist("stopwords_caps.txt").has(f)) return true;
  return inflectedCommon(f);
}

function acronym(tok: string): boolean {
  const f = fold(tok);
  return isAllCaps(tok) && [...tok].length <= 4 && !wordlist("common_words.txt").has(f) && !wordlist("last_names.txt").has(f) &&
    !wordlist("first_names.txt").has(f);
}

type Tok = [number, number, string];
const len = (s: string) => [...s].length;
const capsStyleOf = (run: Tok[], minLen = 0) =>
  run.filter(([, , t]) => len(t) > minLen).every(([, , t]) => isAllCaps(t) || (isUpperChar(t[0]!) && islower(t.slice(1))));

export class PersonRecognizer implements Recognizer {
  name = "tr_person_gazetteer";
  supported_entities = ["PERSON"];
  first = wordlist("first_names.txt");
  last = wordlist("last_names.txt");
  stop: ReadonlySet<string>;
  ambiguous = wordlist("ambiguous_first.txt");
  private emails = new Set<string>();
  private speakers = new Set<number>();

  constructor() {
    const cueWords = new Set(PERSON_CUES.filter(c => !strip(c).includes(" ")).map(c => strip(c, " .:")));
    this.stop = new Set([...wordlist("stopwords_caps.txt"), ...wordlist("provinces.txt"), ...wordlist("districts.txt"), ...cueWords]);
  }

  private tokens(text: string): Tok[] {
    return finditer("recognizers.TOKEN_RE", text).map(m => [m.start(), m.end(), m.group()!]);
  }

  private nameish(tok: string): boolean {
    if (!isCapitalised(tok) || len(tok) < 2) return false;
    if (this.stop.has(fold(rstrip(tok, ".")))) return false;
    if (tok.includes(".")) return false;
    return true;
  }

  private placeSurname(prev: Tok, tok: Tok): boolean {
    const t = tok[2], f = fold(t);
    return len(t) >= 3 && isCapitalised(t) && this.last.has(f) && wordlist("districts.txt").has(f) &&
      !wordlist("provinces.txt").has(f) && this.first.has(fold(prev[2]));
  }

  private emailParts(text: string): Set<string> {
    const parts = new Set<string>();
    for (const m of finditer("recognizers.EMAIL_LOCAL", text))
      for (const p of split("inline.email_split", m.group(1)!) as string[]) if (len(p) > 2) parts.add(fold(p));
    return parts;
  }

  analyze(text: string): RecognizerResult[] {
    const toks = this.tokens(text);
    this.emails = this.emailParts(text);
    this.speakers = new Set(finditer("recognizers.CHAT_SPEAKER", text).map(m => m.start(1)));
    const out: RecognizerResult[] = [], seenNames = new Set<string>(), runs: Tok[][] = [];
    let i = 0;
    while (i < toks.length) {
      if (!this.nameish(toks[i]![2])) { i += 1; continue; }
      let j = i;
      while (j + 1 < toks.length && j - i < 3 && (this.nameish(toks[j + 1]![2]) || this.placeSurname(toks[j]!, toks[j + 1]!)) &&
        fullmatch("inline.gap12", text.slice(toks[j]![1], toks[j + 1]![0]))) j += 1;
      let run = toks.slice(i, j + 1);
      let res: ScoreResult | null = null;
      if (run.length > 2 && isLexical(run[0]![2]) && !this.first.has(fold(run[0]![2]))) {
        res = this.scoreRun(text, run.slice(1));
        if (res) run = run.slice(1);
      }
      res = res ?? this.scoreRun(text, run);
      if (res === null && run.length > 2) {
        for (const sub of [run.slice(1), run.slice(0, -1), run.slice(1, -1), run.slice(2), run.slice(0, -2)]) {
          if (sub.length >= 2) {
            res = this.scoreRun(text, sub);
            if (res) { run = sub; break; }
          }
        }
      }
      if (res) {
        const [s, e, score, why] = res;
        out.push(result("PERSON", this.name, s, e, score, why));
        for (const [, , t] of run) seenNames.add(fold(t));
      } else runs.push(toks.slice(i, j + 1));
      i = j + 1;
    }
    out.push(...this.fillLists(text, runs, out, seenNames));
    out.push(...this.secondPass(text, toks, seenNames, out));
    return out;
  }

  static orgFollows(text: string, end: number): boolean {
    const seg = (split("inline.org_split", text.slice(end, end + 45)) as string[])[0]!;
    return splitWs(fold(seg)).slice(0, 4).some(w => ORG_TAIL.some(o => w.startsWith(o)));
  }

  private scoreRun(text: string, run: Tok[]): ScoreResult | null {
    const start = run[0]![0], end = run.at(-1)![1];
    const words = run.map(([, , t]) => fold(t));
    if (words.some(w => startsWithAny(w, LEGAL_TITLE)) ||
      (["turk", "turkiye"].includes(words[0]!) && startsWithAny(lstrip(fold(text.slice(end, end + 30))), LEGAL_TITLE))) return null;
    if (PersonRecognizer.orgFollows(text, end)) return null;
    const ctx = contextBefore(text, start, 30);
    const cue = !!search("recognizers.CUE_RE", ctx.slice(-30));
    const after = text.slice(end, end + 25);
    const cueAfter = !!match("recognizers.PERSON_AFTER", after);
    const apos = !!match("recognizers.APOS_SUFFIX", after);
    const kin = !!match("recognizers.KINSHIP", text.slice(end, end + 8));
    const firstHit = this.first.has(words[0]!) && (!this.ambiguous.has(words[0]!) || words.length >= 2);
    const lastHit = this.last.has(words.at(-1)!);
    const capsStyle = capsStyleOf(run, 1);
    const courtStyle = run.length >= 2 && capsStyle && !isAllCaps(run[0]![2]) && isAllCaps(run.at(-1)![2]) && len(run.at(-1)![2]) >= 3;
    const email = words.filter(w => this.emails.has(w)).length;
    const speaker = this.speakers.has(start);
    const surnameShape = len(words.at(-1)!) >= 4 && !!search("recognizers.SURNAME_SUFFIX", words.at(-1)!);
    const lineS = rfind(text, "\n", start) + 1;
    const lineE = text.indexOf("\n", end);
    const line = strip(text.slice(lineS, lineE < 0 ? text.length : lineE));
    const heading = isAllCaps(run[0]![2]) && line === text.slice(start, end);
    const lex = run.map(([, , t]) => isLexical(t));
    const acr = acronym(run.at(-1)![2]);
    const plausible = !lex.at(-1) && !acr && (!lex[0] || firstHit);
    const someName = !acr && (!lex.every(Boolean) || firstHit || lastHit);
    if (run.length >= 2 && firstHit && capsStyle && (!lex.at(-1) || lastHit || cue))
      return [start, end, 0.85 + 0.1 * Number(lastHit || cue), "first-name gazetteer"];
    if (run.length >= 2 && lastHit && words.slice(0, -1).some(w => this.first.has(w)))
      return [start, end, 0.85, "first+last gazetteer"];
    if (cue && courtStyle && !acr) return [start, end, 0.75, "person cue + court casing"];
    if (cue && capsStyle && (run.length >= 2 || this.first.has(words[0]!) || this.last.has(words[0]!)) && len(words.at(-1)!) >= 3 && someName)
      return [start, end, 0.75, "person cue before capitalised run"];
    if (speaker && run.length <= 3) return [start, end, 0.8, "chat speaker"];
    if (email && capsStyle && (run.length >= 2 || len(words[0]!) >= 3) && (email >= 2 || !lex.every(Boolean)))
      return [start, end, 0.8, "matches an e-mail address in the document"];
    if (run.length >= 2 && courtStyle && run.length <= 4 && !lex.at(-1) && !acr &&
      (!lex[0] || firstHit || !wordlist("common_words.txt").has(fold(run.at(-1)![2]))))
      return [start, end, 0.75, "court casing Ad SOYAD"];
    if (run.length >= 2 && capsStyle && !heading && ((someName && cueAfter) || (plausible && apos && surnameShape)))
      return [start, end, 0.7, "person word after capitalised run"];
    if ((run.length === 2 || run.length === 3) && capsStyle && !heading && plausible && surnameShape && (apos || cueAfter || firstHit))
      return [start, end, 0.65, "surname shape + context"];
    if (kin && this.first.has(words[0]!)) return [start, end, 0.7, "X oğlu/kızı"];
    if (run.length === 1 && firstHit && !this.ambiguous.has(words[0]!) && (cue || cueAfter))
      return [start, end, 0.7, "single first name + cue"];
    if (run.length === 1 && len(words[0]!) >= 3 && !lex[0] && search("inline.greeting", ctx) && match("inline.greeting_after", after))
      return [start, end, 0.7, "greeting + name"];
    if ((run.length === 2 || run.length === 3) && capsStyle && !heading && apos && plausible && !lex[0])
      return [start, end, 0.6, "capitalised run with a case suffix ('in, 'a)"];
    if (run.length === 1 && capsStyle && len(words[0]!) >= 3 && match("inline.hanim_bey", after))
      return [start, end, 0.7, "name + Hanım/Bey"];
    return null;
  }

  private fillLists(text: string, runs: Tok[][], found: RecognizerResult[], seen: Set<string>): RecognizerResult[] {
    let spans = sortBy(found.map(r => [r.start, r.end] as [number, number]), x => x);
    const extra: RecognizerResult[] = [];
    let changed = true;
    const pending = runs.filter(r => r.length >= 2 && r.length <= 3);
    while (changed && pending.length) {
      changed = false;
      for (const run of [...pending]) {
        const s = run[0]![0], e = run.at(-1)![1];
        const capsStyle = capsStyleOf(run);
        if (!capsStyle || PersonRecognizer.orgFollows(text, e)) continue;
        const lex = run.map(([, , t]) => isLexical(t));
        if (lex.every(Boolean) || acronym(run.at(-1)![2])) continue;
        if (spans.some(([ps, pe]) => match("recognizers.NAME_LIST_SEP", text.slice(pe, s)) || match("recognizers.NAME_LIST_SEP", text.slice(e, ps)))) {
          extra.push(result("PERSON", this.name, s, e, 0.7, "in a list of names"));
          spans = sortBy([...spans, [s, e] as [number, number]], x => x);
          for (const [, , t] of run) seen.add(fold(t));
          pending.splice(pending.indexOf(run), 1);
          changed = true;
        }
      }
    }
    return extra;
  }

  private secondPass(text: string, toks: Tok[], seen: Set<string>, already: RecognizerResult[]): RecognizerResult[] {
    const covered = already.map(r => [r.start, r.end] as const);
    const extra: RecognizerResult[] = [];
    const strong = new Set([...seen].filter(w => !this.ambiguous.has(w) && !this.stop.has(w) && len(w) > 2 &&
      (this.first.has(w) || this.last.has(w) || !isLexical(w))));
    let k = 0;
    while (k < toks.length) {
      const [s, , t] = toks[k]!;
      let e = toks[k]![1];
      if (strong.has(fold(t)) && isCapitalised(t) && !covered.some(([a, b]) => a <= s && s < b)) {
        while (k + 1 < toks.length && this.nameish(toks[k + 1]![2]) && fullmatch("inline.gap12", text.slice(e, toks[k + 1]![0])) &&
          !covered.some(([a, b]) => a <= toks[k + 1]![0] && toks[k + 1]![0] < b)) {
          k += 1;
          e = toks[k]![1];
        }
        if (!splitWs(text.slice(s, e)).slice(1).some(x => startsWithAny(fold(x), LEGAL_TITLE)) &&
          !startsWithAny(lstrip(fold(text.slice(e, e + 30))), LEGAL_TITLE))
          extra.push(result("PERSON", this.name, s, e, 0.6, "repeat of a name found earlier"));
      }
      k += 1;
    }
    return extra;
  }
}
type ScoreResult = [number, number, number, string];

// ---------------------------------------------------------------- addresses
class AddressRecognizer implements Recognizer {
  name = "tr_address";
  supported_entities = ["ADDRESS"];
  places = new Set([...wordlist("provinces.txt"), ...wordlist("districts.txt")]);

  analyze(text: string): RecognizerResult[] {
    const spans: Array<[number, number, number, string]> = [];
    for (const m of finditer("recognizers.ADDR_LABEL", text)) {
      const s = m.end();
      let e = text.indexOf("\n", s);
      e = e < 0 ? text.length : e;
      const nxtEnd = text.indexOf("\n", e + 1);
      const nxt = text.slice(e + 1, nxtEnd > 0 ? nxtEnd : text.length);
      const r = rstrip(text.slice(s, e));
      if (r.endsWith(",") || r.endsWith("-") || (search("recognizers.ADDR_ANCHOR", nxt) && !nxt.slice(0, 15).includes(":")) ||
        search("inline.no_digit", nxt)) e = nxtEnd > 0 ? nxtEnd : text.length;
      const seg = rstrip(text.slice(s, e), " .;");
      if (len(strip(seg)) >= 8 && (search("recognizers.ADDR_ANCHOR", seg) || search("inline.no_digit", seg) || this.hasPlace(seg)))
        spans.push([s, s + seg.length, 0.9, "address label"]);
    }
    for (const m of finditer("recognizers.ADDR_FORM_ROW", text)) {
      const s = m.end();
      let e = text.indexOf("\n", m.end());
      e = e < 0 ? text.length : e;
      const seg = rstrip(text.slice(s, e), " .;|");
      if (findall("inline.letters_digits", seg).length >= 2 && match("inline.upper_or_digit", seg) && splitWs(seg).length <= 14)
        spans.push([s, s + seg.length, 0.8, "address row of a form"]);
    }
    for (const m of finditer("recognizers.ADDR_ANCHOR", text)) {
      const [s, e] = this.grow(text, m.start(), m.end());
      if (e - s >= 12) spans.push([s, e, 0.75, "street anchor"]);
    }
    return mergeSpans(spans).map(([s, e, sc, why]) => result("ADDRESS", this.name, s, e, sc, why));
  }

  private hasPlace(seg: string): boolean {
    return (findall("inline.letters", seg) as string[]).some(w => this.places.has(fold(w)));
  }

  private grow(text: string, s: number, e: number): [number, number] {
    const lineStart = rfind(text, "\n", s) + 1;
    let left = text.slice(lineStart, s);
    let toks = finditer("inline.grow_left", left);
    let k = 0;
    while (toks.length && k < 5) {
      const m = toks.at(-1)!;
      const word = m.group(1)!;
      if (["adres", "adresi", "ikametgah"].includes(fold(word)) || word.endsWith(":")) break;
      s = lineStart + m.start(1);
      left = text.slice(lineStart, s);
      toks = finditer("inline.grow_left", left);
      k += 1;
    }
    let pos = e, lines = 0, steps = 0, lastGood = e;
    while (pos < text.length && steps < 30) {
      const ws = match("inline.grow_ws", text, pos)!;
      const wsEnd = ws.end() - pos;
      if (ws.group(1) !== undefined) {
        lines += 1;
        if (lines > 1) break;
        const nxt = text.slice(pos + wsEnd, pos + wsEnd + 40);
        if (!(search("recognizers.ADDR_ANCHOR", nxt.slice(0, 30)) || match("inline.grow_next", nxt))) break;
      }
      const p2 = pos + wsEnd;
      const t = match("recognizers.ADDR_TOKEN", text, p2);
      if (!t) break;
      const word = t.group()!;
      if (["tel", "telefon", "gsm", "e-posta", "vergi", "tc", "t.c", "iban", "konu", "vekili"].includes(fold(strip(word, ".")))) break;
      pos = t.end();
      if (!pyIn(word, ",-")) lastGood = pos;
      steps += 1;
      if (this.places.has(fold(word)) && text.slice(pos, pos + 1) !== "/" && !match("inline.slash_after", text, pos)) {
        if (search("inline.slash_before", text.slice(Math.max(0, p2 - 3), p2)) || wordlist("provinces.txt").has(fold(word))) break;
      }
    }
    return [s, lastGood];
  }
}

function mergeSpans(spans: Array<[number, number, number, string]>): Array<[number, number, number, string]> {
  const sorted = sortBy(spans, x => [x[0], -x[1]]);
  const out: Array<[number, number, number, string]> = [];
  for (const [s, e, sc, why] of sorted) {
    const prev = out.at(-1);
    if (prev && s <= prev[1]) {
      const [ps, pe, psc, pwhy] = prev;
      out[out.length - 1] = [ps, Math.max(pe, e), Math.max(psc, sc), psc >= sc ? pwhy : why];
    } else out.push([s, e, sc, why]);
  }
  return out;
}

// ---------------------------------------------------------------- KVKK Article 6
class SpecialCategoryRecognizer implements Recognizer {
  name = "kvkk_art6_lexicon";
  supported_entities = SPECIAL_ENTITIES;
  analyze(text: string, entities: string[]): RecognizerResult[] {
    const out: RecognizerResult[] = [];
    for (const ent of SPECIAL_ENTITIES) {
      if (entities.length && !entities.includes(ent)) continue;
      for (const m of finditer("special." + ent, text))
        out.push(result(ent, this.name, m.start(), m.end(), 0.7, `Art. 6 term '${m.group()}'`));
    }
    return out;
  }
}

// ---------------------------------------------------------------- post-processing shared by server and browser
export function dropPlaceNames(text: string, results: RecognizerResult[]): RecognizerResult[] {
  const addrs = results.filter(r => r.entity_type === "ADDRESS").map(r => [r.start, r.end] as const);
  return results.filter(r => !(r.entity_type === "PERSON" && (match("recognizers.PLACE_AFTER", text.slice(r.end, r.end + 16)) ||
    match("recognizers.MONEY_AFTER", text.slice(r.end, r.end + 14)) || addrs.some(([a, b]) => a < r.end && r.start < b))));
}

const STREET_KEYS = new Set(["Mahallesi", "Mahalle", "Mah", "Mh", "Caddesi", "Cadde", "Cad", "Cd", "Sokağı", "Sokak", "Sok", "Sk", "Bulvarı",
  "Bulvar", "Blv", "Bulv", "Meydanı", "Yolu", "Köyü", "Mevkii", "Parkı"].map(fold));
const OCR_STREET = new Set(["meh", "moh", "mah", "nah", "mab", "cod", "ced", "cadi", "cadı", "5k", "sk", "s.k", "5ok", "sek", "blu", "biv"]);

export function edit1(a: string, b: string): boolean {
  let A = [...a], B = [...b];
  if (Math.abs(A.length - B.length) > 1) return false;
  if (A.length === B.length) return A.filter((x, i) => x !== B[i]).length <= 1;
  if (A.length > B.length) [A, B] = [B, A];
  const as = A.join("");
  return B.some((_, i) => [...B.slice(0, i), ...B.slice(i + 1)].join("") === as);
}

function streetKey(tok: string): boolean {
  const f = fold(rstrip(tok, ".,:"));
  if (STREET_KEYS.has(f) || OCR_STREET.has(f)) return true;
  return len(f) >= 5 && [...STREET_KEYS].some(k => len(k) >= 5 && edit1(f, k));
}

export function addressParts(text: string, start: number, end: number): Array<[number, number]> {
  const seg = text.slice(start, end);
  const toks: Tok[] = finditer("recognizers._ADDR_TOK", seg).map(m => [m.start() + start, m.end() + start, m.group()!]);
  const provinces = wordlist("provinces.txt");
  const places = new Set([...provinces, ...wordlist("districts.txt")]);
  const visible = toks.map(() => false);
  toks.forEach(([, , t], i) => {
    const bare = rstrip(t, ".,:");
    if (streetKey(bare)) {
      visible[i] = true;
      let k = i - 1;
      while (k >= 0 && i - k <= 4 && !visible[k] && !match("recognizers._HOUSE", toks[k]![2]) && !search("inline.colon", toks[k]![2]) &&
        !text.slice(toks[k]![1], toks[k + 1]![0]).includes("\n") && !text.slice(toks[k]![1], toks[k + 1]![0]).includes(",")) {
        visible[k] = true;
        k -= 1;
      }
    }
    const f = fold(bare);
    if (places.has(f) || fullmatch("inline.postcode", bare) || ["turkiye", "tr"].includes(fold(bare))) {
      visible[i] = true;
      if (provinces.has(f) && i > 0 && !visible[i - 1] && !match("recognizers._HOUSE", toks[i - 1]![2]) &&
        fullmatch("inline.cap_word", toks[i - 1]![2]) && fullmatch("inline.slash_gap", text.slice(toks[i - 1]![1], toks[i]![0])))
        visible[i - 1] = true;
    }
  });
  const parts: Array<[number, number]> = [];
  let cur: [number, number] | null = null;
  toks.forEach(([s, e], i) => {
    if (visible[i]) { if (cur) parts.push(cur); cur = null; } else cur = cur ? [cur[0], e] : [s, e];
  });
  if (cur) parts.push(cur);
  return parts;
}

export type Make = (entity: string, start: number, end: number, score: number, why: string, name?: string) => RecognizerResult;

/** 'property' (evidence: keep readable in a court copy), 'party' (someone's own address: mask whole) or null. */
export function addressRole(text: string, start: number, end: number): "property" | "party" | null {
  const line = rfind(text, "\n", start) + 1;
  const before = text.slice(Math.max(line, start - 90), start);
  const after = text.slice(end, end + 80);
  if (search("recognizers.PROPERTY_BEFORE", before) || match("recognizers.PROPERTY_AFTER", after)) return "property";
  if (search("recognizers.RESIDENCE_BEFORE", before) || match("recognizers.RESIDENCE_AFTER", after)) return "party";
  const head = text.slice(line, start);
  if (match("recognizers.PARTY_LINE", head) || match("recognizers.PARTY_LABEL_ONLY", head)) return "party";
  if (!strip(head)) {
    const prevEnd = line - 1;
    const prev = rfind(text, "\n", Math.max(prevEnd, 0)) + 1;
    if (prevEnd > 0 && match("recognizers.PARTY_LINE", text.slice(prev, prevEnd))) return "party";
  }
  return null;
}

/** The address opens its line and the line before it is just a person's name. */
function underAName(text: string, start: number, results: RecognizerResult[]): boolean {
  const line = rfind(text, "\n", start) + 1;
  if (strip(text.slice(line, start), " \t|") || line === 0) return false;
  const prev = rfind(text, "\n", line - 1) + 1;
  let a = prev, b = line - 1;
  while (a < b && " \t|".includes(text[a]!)) a++;
  while (b > a && " \t|,".includes(text[b - 1]!)) b--;
  return b > a && results.some(r => r.entity_type === "PERSON" && r.start <= a && r.end >= b);
}

export function splitAddresses(text: string, results: RecognizerResult[], make: Make): RecognizerResult[] {
  const out: RecognizerResult[] = [];
  for (const r of results) {
    if (r.entity_type !== "ADDRESS") { out.push(r); continue; }
    let role = addressRole(text, r.start, r.end);
    if (role === null && underAName(text, r.start, results)) role = "party";
    const name = r.recognition_metadata?.recognizer_name ?? "tr_address";
    if (role === "party") { out.push(make("ADDRESS", r.start, r.end, r.score, "a party's own address (masked whole)", name)); continue; }
    if (role === "property") continue;
    for (const [s, e] of addressParts(text, r.start, r.end))
      out.push(make("ADDRESS", s, e, r.score, "building, door or flat of an address (street left visible)", name));
  }
  return out;
}

export function ocrNameRepeats(text: string, ranges: Array<[number, number]>, results: RecognizerResult[]): ScoreResult[] {
  const names = new Set<string>();
  for (const r of results) {
    if (r.entity_type !== "PERSON") continue;
    for (const m of finditer("recognizers.TOKEN_RE", text.slice(r.start, r.end))) if (len(m.group()!) >= 4) names.add(fold(m.group()!));
  }
  for (const w of wordlist("stopwords_caps.txt")) names.delete(w);
  if (!names.size) return [];
  const covered = results.map(r => [r.start, r.end] as const);
  const out: ScoreResult[] = [];
  for (const [a, b] of ranges) {
    for (const m of finditer("recognizers.TOKEN_RE", text, a, b)) {
      const t = m.group()!;
      if (len(t) < 4 || !isUpperChar(t[0]!) || covered.some(([x, y]) => x <= m.start() && m.start() < y)) continue;
      const f = fold(t);
      if (names.has(f) || (len(f) >= 5 && [...names].some(n => len(n) >= 5 && edit1(f, n))))
        out.push([m.start(), m.end(), 0.75, "repeat of a name found on an OCR'd page (handwriting read differently)"]);
    }
  }
  return out;
}

export function ocrFormValues(text: string, ranges: Array<[number, number]>): Array<[string, number, number, number, string]> {
  const found: Array<[string, number, number, number, string]> = [];
  const find = (sub: string, from: number, to: number) => { const i = text.slice(0, to).indexOf(sub, from); return i; };
  for (const [a, b] of ranges) {
    let pos = a;
    while (pos < b) {
      let e = find("\n", pos, b);
      e = e < 0 ? b : e;
      const line = text.slice(pos, e), f = fold(line);
      const same = len(f) === len(line);
      let m = same ? search("recognizers.FORM_ADDR_LABEL", f) : null;
      if (m) {
        const segS = pos + m.end();
        let segE = e;
        let nEnd = find("\n", e + 1, b);
        nEnd = nEnd < 0 ? b : nEnd;
        const nxt = text.slice(e + 1, nEnd);
        if (e < b && findall("inline.letters_digits", nxt).length >= 2 && !search("recognizers.FORM_ANY_LABEL", fold(nxt))) segE = nEnd;
        const seg = text.slice(segS, segE);
        const toks = finditer("inline.form_tok", seg);
        if (toks.length >= 2)
          found.push(["ADDRESS", segS + toks[0]!.start(), segS + toks.at(-1)!.end(), 0.8,
            "address written in a form row labelled İkametgahı/Adresi on an OCR'd page"]);
      }
      for (const [lab, typ] of [["recognizers.FORM_TCKN_LABEL", "TCKN"], ["recognizers.FORM_NAME_LABEL", "PERSON"]] as const) {
        m = same ? search(lab, f) : null;
        if (!m) continue;
        const restS = m.end();
        let stop = search("recognizers.FORM_STOP", line, restS);
        const restE = stop ? stop.start() : line.length;
        let seg = line.slice(restS, restE);
        let base = pos + restS;
        let toks = finditer("inline.form_tok", seg);
        if (!toks.length && e < b) {
          let nEnd = find("\n", e + 1, b);
          nEnd = nEnd < 0 ? b : nEnd;
          const nxt = text.slice(e + 1, nEnd);
          if (!search("recognizers.FORM_ANY_LABEL", fold(nxt).slice(0, 12))) {
            stop = search("recognizers.FORM_STOP", nxt);
            seg = nxt.slice(0, stop ? stop.start() : nxt.length);
            base = e + 1;
            toks = finditer("inline.form_tok", seg);
          }
        }
        if (!toks.length || (typ === "PERSON" && toks.length > 4)) continue;
        if (typ === "TCKN" && toks.reduce((n, t: PyMatch) => n + len(t.group()!), 0) < 5) continue;
        const s0 = base + toks[0]!.start(), e0 = base + toks.at(-1)!.end();
        found.push([typ, s0, e0, 0.8, "value of a form row labelled " + (typ === "TCKN" ? "T.C. Kimlik No" : "Adı soyadı") + " on an OCR'd page"]);
      }
      pos = e + 1;
    }
  }
  return found;
}

const OCR_DIGIT: Record<string, string> = { O: "0", o: "0", D: "0", I: "1", l: "1", "|": "1", S: "5", s: "5", B: "8", Z: "2", z: "2" };
const NOT_ID = ["uyap", "esas", "karar no", "dosya", "sicil", "mersis", "fatura", "seri", "sira no", "barkod"];

export function ocrTckn(text: string, ranges: Array<[number, number]>): ScoreResult[] {
  const found: ScoreResult[] = [];
  for (const [a, b] of ranges) {
    for (const m of finditer("recognizers.OCR_TCKN", text, a, b)) {
      const raw = m.group(1)!;
      const digits = [...raw].map(c => OCR_DIGIT[c] ?? c).join("").replaceAll(" ", "");
      if (countDigits(raw) < 9 || tcknValid(digits)) continue;
      if (len(digits) !== 11 && !hasContext(text, m.start(), ["kimlik", "kimlk", "kımlık", "tckn", "t.c", "tc no"], 40)) continue;
      if (search("inline.digit_before", text.slice(Math.max(0, m.start() - 2), m.start())) || match("inline.digit_after", text.slice(m.end(), m.end() + 2))) continue;
      if (hasContext(text, m.start(), NOT_ID, 25)) continue;
      found.push([m.start(1), m.end(1), 0.75, "11 digits on an OCR'd page, checksum failed (likely misread), masked to be safe"]);
    }
  }
  return found;
}

export function defaultRecognizers(): Recognizer[] {
  return [new TCKNRecognizer(), new PassportRecognizer(), new ForeignIDRecognizer(), new UETSRecognizer(), new VKNRecognizer(), new IBANRecognizer(),
    new CreditCardRecognizer(), new EmailRecognizer(), new PhoneRecognizer(), new PlateRecognizer(), new IPRecognizer(),
    new BirthDateRecognizer(), new PersonRecognizer(), new AddressRecognizer(), new SpecialCategoryRecognizer()];
}
