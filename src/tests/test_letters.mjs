// Letter types and language guess for the client test page (cep.html). Synthetic letters only.
//   node src/tests/test_letters.mjs
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { classifyLetter, guessLanguage, TYPES, LAW, HELP } from "../letters.js";

const L = f => readFileSync(new URL(`./letters/${f}`, import.meta.url), "utf8");
const cases = [
  ["ind_besluit.txt", "nl", "ind_besluit"],
  ["gemeente_besluit.txt", "nl", "overheid_besluit"],
  ["beeindiging.txt", "nl", "beeindiging"],
  ["turks.txt", "tr", null],
];
for (const [f, lang, type] of cases) {
  const text = L(f);
  assert.equal(guessLanguage(text), lang, f);
  if (type) assert.equal(classifyLetter(text).type, type, f);
}
const t = s => classifyLetter(s).type;
assert.equal(t("Immigratie- en Naturalisatiedienst. Wij zijn van plan uw verblijfsvergunning in te trekken (voornemen). U kunt uw zienswijze geven."), "ind_voornemen");
assert.equal(t("IND. Beslissing op uw aanvraag om een verblijfsvergunning asiel voor bepaalde tijd. Uw aanvraag is afgewezen."), "ind_asiel");
assert.equal(t("Immigratie- en Naturalisatiedienst. Besluit op uw verzoek om naturalisatie volgens de Rijkswet op het Nederlanderschap: afgewezen."), "naturalisatie");
assert.equal(t("Dagvaarding. De deurwaarder roept gedaagde op te verschijnen voor de kantonrechter van de rechtbank Amsterdam."), "dagvaarding");
assert.equal(t("Beste klant, bedankt voor uw bestelling."), "other");

// every type has text in all three languages, and every law reference is an official wetten.overheid.nl link
for (const [k, v] of Object.entries(TYPES)) {
  for (const f of ["name", "what"]) for (const l of ["nl", "en", "tr"]) assert.ok(v[f][l], `${k}.${f}.${l}`);
  if (v.deadline) for (const l of ["nl", "en", "tr"]) assert.ok(v.deadline[l], `${k}.deadline.${l}`);
  for (const x of v.law) assert.ok(LAW[x], `${k} law ${x}`);
}
for (const x of Object.values(LAW)) assert.match(x.url, /^https:\/\/wetten\.overheid\.nl\/jci1\.3:c:BWBR\d{7}&artikel=/);
// the deadlines we state match the law we cite
assert.match(TYPES.ind_besluit.deadline.en, /4 weeks/); assert.match(LAW.vw69.quote, /vier weken/);
assert.match(TYPES.overheid_besluit.deadline.en, /6 weeks/); assert.match(LAW.awb67.quote, /zes weken/);
assert.match(TYPES.beeindiging.deadline.en, /14 days/); assert.match(LAW.bw670b.quote, /veertien dagen/);
for (const h of HELP.nl) assert.match(h.url, /^https:\/\//);
console.log("letters: ok");
