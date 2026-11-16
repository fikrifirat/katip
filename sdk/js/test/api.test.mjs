import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { Masker, LeakError, ModelError, PROFILES, ENTITY_TYPES, mask, restore, downloadModel, MODELS } from "../dist/index.js";

const DOC = "Davacı Ahmet YILMAZ (T.C. Kimlik No: 10000000146) Kızılay Mah. Atatürk Cad. No:12 D:3 Çankaya/ANKARA adresinde oturur.\n" +
  "Tel: 0532 123 45 67, e-posta ahmet.yilmaz@gmail.com. Ankara 3. Asliye Hukuk Mahkemesi 2023/145 E. sayılı dosya.\n" +
  "Ahmet YILMAZ 12.03.2024 tarihinde ödedi. Depresyon tedavisi görüyor.";

test("court profile masks the party's address, keeps case number and date readable", () => {
  const r = new Masker().maskSync(DOC);
  for (const gone of ["Ahmet", "10000000146", "0532", "Kızılay", "Çankaya"]) assert.ok(!r.text.includes(gone), gone);
  for (const kept of ["2023/145", "12.03.2024"]) assert.ok(r.text.includes(kept), kept);
  assert.equal(r.text.split("[AD SOYAD-1]").length - 1, 2);
});

test("court profile keeps the property in dispute readable and masks UETS", () => {
  const text = "Kiralananın Adresi: Kızılay Mah. Atatürk Cad. No:12 D:3 Çankaya/ANKARA\nDavalı vekili Av. Zeynep KARA, UETS: 16013-10288-73541";
  const r = new Masker().maskSync(text);
  assert.ok(r.text.includes("Kızılay Mah. Atatürk Cad. No:12 D:3 Çankaya/ANKARA"));
  assert.ok(!r.text.includes("16013-10288-73541") && !r.text.includes("Zeynep"));
  assert.ok(!new Masker({ profile: "ai" }).maskSync(text).text.includes("Kızılay"));
});

test("each profile masks everything the previous one does", () => {
  const [court, ai, anon] = ["court", "ai", "anon"].map(profile => new Masker({ profile }).maskSync(DOC));
  for (const [weak, strong] of [[court, ai], [ai, anon]]) for (const s of weak.spans) assert.ok(!strong.text.includes(s.text), s.text);
});

test("restore puts every value back", async () => {
  const r = await mask(DOC, { profile: "ai" });
  assert.equal(r.restore(r.text), DOC);
  assert.equal(restore("[AD SOYAD-1] haklıdır.", r.mapping), "Ahmet YILMAZ haklıdır.");
});

test("block style, allow and deny", () => {
  assert.ok(new Masker({ style: "block" }).maskSync(DOC).text.includes("██████"));
  const t = "Müvekkil Ayşe Kaya ile Katip Hukuk Bürosu çalışanı Zeynep görüştü.";
  assert.ok(!new Masker({ deny: ["Zeynep"] }).maskSync(t).text.includes("Zeynep"));
  assert.ok(new Masker({ allow: ["Ayşe Kaya"] }).maskSync(t).text.includes("Ayşe Kaya"));
});

test("Turkish case-insensitive cues behave like Python's re.I", () => {
  assert.ok(!new Masker().maskSync("KİMLİK NO 10000000146").text.includes("10000000146"));
});

test("offsets are UTF-16, also after emoji", () => {
  const text = "😀👩‍⚖️ Davacı Ahmet YILMAZ";
  const [s] = new Masker().detectSync(text);
  assert.equal(text.slice(s.start, s.end), "Ahmet YILMAZ");
  assert.equal(s.text, "Ahmet YILMAZ");
  assert.equal(new Masker().maskSync(text).text, "😀👩‍⚖️ Davacı [AD SOYAD-1]");
});

test("profiles and types come from the shared spec", () => {
  assert.deepEqual(Object.keys(PROFILES), ["court", "ai", "anon"]);
  assert.ok(ENTITY_TYPES.includes("TCKN") && ENTITY_TYPES.includes("INSTITUTION"));
});

test("bad options are rejected", () => {
  assert.throws(() => new Masker({ profile: "everything" }));
  assert.throws(() => new Masker({ entities: ["NAME"] }));
  assert.throws(() => new Masker({ model: "mini" }), /Masker.create/);
});

test("LeakError carries kinds and lines, never values", () => {
  const e = new LeakError(["PERSON"], [3]);
  assert.match(e.message, /PERSON/);
  assert.ok(e instanceof Error);
});

test("a model file with the wrong hash is refused and not cached", async () => {
  const dir = mkdtempSync(join(tmpdir(), "katip-"));
  const info = MODELS.nano;
  for (const f of Object.keys(info.files)) {
    const p = join(dir, "mirror", "nano", f);
    mkdirSync(join(p, ".."), { recursive: true });
    writeFileSync(p, Buffer.alloc(info.files[f].size, 120));
  }
  process.env.KATIP_MASK_CACHE = join(dir, "cache");
  const fakeFetch = async url => new Response(new Uint8Array(Buffer.alloc(10)));
  await assert.rejects(downloadModel("nano", { modelBaseUrl: pathToFileURL(join(dir, "mirror")).href, fetch: fakeFetch }), ModelError);
  await assert.rejects(downloadModel("nano", { offline: true }), /not downloaded/);
  delete process.env.KATIP_MASK_CACHE;
});

test("CLI masks and restores", () => {
  const dir = mkdtempSync(join(tmpdir(), "katip-"));
  writeFileSync(join(dir, "d.txt"), DOC);
  const out = execFileSync("node", ["dist/cli.js", "mask", join(dir, "d.txt"), "--profile", "ai", "--json"], { encoding: "utf8" });
  writeFileSync(join(dir, "m.json"), out);
  writeFileSync(join(dir, "a.txt"), "[AD SOYAD-1] haklı.");
  assert.equal(execFileSync("node", ["dist/cli.js", "restore", join(dir, "a.txt"), "--mapping", join(dir, "m.json")], { encoding: "utf8" }), "Ahmet YILMAZ haklı.");
});

test("models find names the rules miss", { skip: process.env.KATIP_MASK_TEST_MODELS !== "1" && "set KATIP_MASK_TEST_MODELS=1" }, async () => {
  const text = "Toplantıya Peter Aufschnaiter ve Madeleine Okonkwo da katıldı.";
  assert.ok(new Masker().maskSync(text).text.includes("Peter"));
  for (const model of ["nano", "mini"]) {
    const r = await (await Masker.create({ model })).mask(text);
    assert.ok(!r.text.includes("Peter"), model);
    assert.ok(r.model.startsWith(model));
  }
});
