// Katip "Cebindeki hukuk" client test: what kind of Dutch letter is this, and is there a deadline?
// Runs on the device, on the original text; nothing here touches the network. Rules, not a model: every type
// below has a deadline that was read in the official text (wetten.overheid.nl, 21 Nov 2026), and the page always
// tells the reader that the letter's own "bezwaar" paragraph and date win. Types we can't name come back as
// "other" with no deadline claim.

const W = "https://wetten.overheid.nl/jci1.3:c:";
export const LAW = {
  vw69: { ref: "Vreemdelingenwet 2000, art. 69 lid 1", url: W + "BWBR0011823&artikel=69",
    quote: "In afwijking van artikel 6:7 van de Algemene wet bestuursrecht bedraagt de termijn voor het indienen van een bezwaar- of beroepschrift vier weken." },
  awb67: { ref: "Algemene wet bestuursrecht, art. 6:7", url: W + "BWBR0005537&artikel=6%3A7",
    quote: "De termijn voor het indienen van een bezwaar- of beroepschrift bedraagt zes weken." },
  awb68: { ref: "Algemene wet bestuursrecht, art. 6:8 lid 1", url: W + "BWBR0005537&artikel=6%3A8",
    quote: "De termijn vangt aan met ingang van de dag na die waarop het besluit op de voorgeschreven wijze is bekendgemaakt." },
  awb48: { ref: "Algemene wet bestuursrecht, art. 4:8", url: W + "BWBR0005537&artikel=4%3A8",
    quote: "Voordat een bestuursorgaan een beschikking geeft waartegen een belanghebbende die de beschikking niet heeft aangevraagd naar verwachting bedenkingen zal hebben, stelt het die belanghebbende in de gelegenheid zijn zienswijze naar voren te brengen ..." },
  bw670b: { ref: "Burgerlijk Wetboek Boek 7, art. 670b lid 2–3", url: W + "BWBR0005290&artikel=670b",
    quote: "... heeft de werknemer het recht om deze overeenkomst zonder opgaaf van redenen, binnen veertien dagen na de datum waarop de overeenkomst tot stand is gekomen, ... te ontbinden. ... bij gebreke waarvan de termijn ... drie weken bedraagt." },
};

// name, what it is, what to do, deadline (null = none we can state), law keys; texts in nl / en / tr
export const TYPES = {
  ind_asiel: {
    name: { nl: "IND-beslissing over asiel", en: "IND decision on asylum", tr: "IND iltica kararı" },
    what: { nl: "Een besluit of voornemen in een asielprocedure. Hier gelden korte en verschillende termijnen (soms één of twee weken).",
      en: "A decision or intended decision in an asylum procedure. Deadlines here are short and differ by case (sometimes one or two weeks).",
      tr: "İltica sürecinde bir karar veya karar niyeti. Süreler kısa ve duruma göre farklıdır (bazen bir veya iki hafta)." },
    deadline: null, urgent: true, law: ["vw69"] },
  ind_voornemen: {
    name: { nl: "IND-voornemen (u mag reageren)", en: "IND intended decision (you may respond)", tr: "IND karar niyeti (görüş bildirebilirsiniz)" },
    what: { nl: "De IND laat weten wat zij van plan is te beslissen. U mag eerst uw zienswijze geven. De termijn staat in de brief.",
      en: "The IND tells you what it intends to decide. You may first give your view (zienswijze). The deadline is stated in the letter.",
      tr: "IND vermeyi düşündüğü kararı bildiriyor. Önce görüşünüzü (zienswijze) yazabilirsiniz. Süre mektupta yazar." },
    deadline: { nl: "De termijn staat in de brief.", en: "The deadline is in the letter.", tr: "Süre mektupta yazılıdır." }, law: ["awb48"] },
  ind_besluit: {
    name: { nl: "IND-beslissing (verblijf of visum)", en: "IND decision (residence or visa)", tr: "IND kararı (oturum veya vize)" },
    what: { nl: "Een besluit van de IND over een verblijfsvergunning, visum of verlenging. Bent u het er niet mee eens, dan kunt u bezwaar maken.",
      en: "An IND decision on a residence permit, visa or extension. If you disagree, you can object (bezwaar).",
      tr: "IND'nin oturum izni, vize veya uzatma hakkındaki kararı. Katılmıyorsanız itiraz (bezwaar) edebilirsiniz." },
    deadline: { nl: "Bezwaar binnen 4 weken, vanaf de dag na de datum van het besluit.", en: "Object within 4 weeks, counted from the day after the decision's date.",
      tr: "İtiraz 4 hafta içinde, karar tarihinden sonraki günden itibaren." }, law: ["vw69", "awb68"] },
  naturalisatie: {
    name: { nl: "Beslissing over naturalisatie / Nederlanderschap", en: "Decision on naturalisation / Dutch nationality", tr: "Vatandaşlık (naturalisatie) kararı" },
    what: { nl: "Een besluit over het Nederlanderschap. Dit valt niet onder de Vreemdelingenwet, dus de gewone bezwaartermijn geldt.",
      en: "A decision on Dutch nationality. It does not fall under the Aliens Act, so the usual objection period applies.",
      tr: "Hollanda vatandaşlığı hakkında bir karar. Yabancılar Kanunu'na girmez, normal itiraz süresi geçerlidir." },
    deadline: { nl: "Bezwaar binnen 6 weken, vanaf de dag na de datum van het besluit.", en: "Object within 6 weeks, counted from the day after the decision's date.",
      tr: "İtiraz 6 hafta içinde, karar tarihinden sonraki günden itibaren." }, law: ["awb67", "awb68"] },
  overheid_besluit: {
    name: { nl: "Besluit van een overheidsinstantie", en: "Decision by a government body", tr: "Bir kamu kurumunun kararı" },
    what: { nl: "Bijvoorbeeld van de gemeente, Belastingdienst, UWV, DUO of SVB. Bent u het er niet mee eens, dan kunt u bezwaar maken.",
      en: "For example from the municipality, Tax Administration, UWV, DUO or SVB. If you disagree, you can object (bezwaar).",
      tr: "Örneğin belediye, vergi dairesi, UWV, DUO veya SVB'den. Katılmıyorsanız itiraz (bezwaar) edebilirsiniz." },
    deadline: { nl: "Bezwaar binnen 6 weken, vanaf de dag na de datum van het besluit.", en: "Object within 6 weeks, counted from the day after the decision's date.",
      tr: "İtiraz 6 hafta içinde, karar tarihinden sonraki günden itibaren." }, law: ["awb67", "awb68"] },
  beeindiging: {
    name: { nl: "Beëindigingsovereenkomst (ontslag met wederzijds goedvinden)", en: "Settlement agreement ending your employment", tr: "İş sözleşmesini sona erdiren anlaşma" },
    what: { nl: "U en uw werkgever spreken af dat uw contract stopt. Na het tekenen mag u nog zonder reden terugkomen op uw handtekening.",
      en: "You and your employer agree that your contract ends. After signing, you may still undo it without giving a reason.",
      tr: "Siz ve işvereniniz sözleşmenin biteceğinde anlaşıyorsunuz. İmzaladıktan sonra da gerekçe göstermeden vazgeçebilirsiniz." },
    deadline: { nl: "Binnen 14 dagen na het sluiten schriftelijk ontbinden (3 weken als dit recht niet in de overeenkomst staat).",
      en: "Undo it in writing within 14 days of signing (3 weeks if the agreement doesn't mention this right).",
      tr: "İmzadan sonraki 14 gün içinde yazılı olarak vazgeçebilirsiniz (anlaşmada bu hak yazmıyorsa 3 hafta)." }, law: ["bw670b"] },
  dagvaarding: {
    name: { nl: "Dagvaarding (u wordt voor de rechter geroepen)", en: "Summons (you are called to court)", tr: "Mahkemeye çağrı (dagvaarding)" },
    what: { nl: "Iemand begint een rechtszaak tegen u. In de dagvaarding staat wanneer en waar u moet reageren.",
      en: "Someone is starting a court case against you. The summons says when and where you must respond.",
      tr: "Biri size karşı dava açıyor. Ne zaman ve nerede cevap vermeniz gerektiği çağrı kâğıdında yazar." },
    deadline: { nl: "De datum staat in de dagvaarding. Reageert u niet, dan kan de rechter beslissen zonder u.",
      en: "The date is in the summons. If you don't respond, the court can decide without you.",
      tr: "Tarih çağrı kâğıdında yazar. Cevap vermezseniz mahkeme sizsiz karar verebilir." }, urgent: true, law: [] },
  other: {
    name: { nl: "Onbekend soort brief", en: "Letter type not recognised", tr: "Mektup türü tanınmadı" },
    what: { nl: "Katip herkent dit soort brief (nog) niet. De uitleg hieronder komt van de AI, zonder termijn van Katip.",
      en: "Katip doesn't recognise this kind of letter (yet). The explanation below comes from the AI, without a deadline from Katip.",
      tr: "Katip bu tür mektubu (henüz) tanımıyor. Aşağıdaki açıklama yapay zekâdan gelir; Katip süre belirtmez." },
    deadline: null, law: [] },
};

const has = (t, words) => words.some(w => t.includes(w));
const IND = ["immigratie- en naturalisatiedienst", "ind.nl", "v-nummer", "vreemdelingennummer", "vreemdelingenwet"];
const BESLUIT = ["besluit", "beschikking", "beslissing", "heb ik besloten", "hebben wij besloten", "wij hebben besloten", "afgewezen", "toegekend",
  "bezwaar maken", "kunt u bezwaar", "u kunt bezwaar", "niet eens met dit besluit", "niet eens met deze beslissing"];

/** Classify a Dutch letter. Returns { type, why: [matched cues] }. The text never leaves the device. */
export function classifyLetter(text) {
  const t = " " + text.toLowerCase().replace(/\s+/g, " ") + " ";
  const why = c => c.filter(w => t.includes(w));
  const ind = has(t, IND) || /\bIND\b/.test(text);
  if (ind && has(t, ["asiel", "asylum", "verblijfsvergunning asiel"])) return { type: "ind_asiel", why: why(["asiel"]) };
  if (has(t, ["voornemen", "zienswijze"]) && (ind || has(t, BESLUIT))) return { type: ind ? "ind_voornemen" : "other", why: why(["voornemen", "zienswijze"]) };
  if ((/naturalisatie(?!dienst)/.test(t) || t.includes("nederlanderschap")) && has(t, BESLUIT))  // (?!dienst): not the IND's own name
    return { type: "naturalisatie", why: why(["naturalisatie", "nederlanderschap"]) };
  if (ind && has(t, BESLUIT)) return { type: "ind_besluit", why: why(["besluit", "beschikking", "beslissing", "bezwaar"]) };
  if (has(t, ["beëindigingsovereenkomst", "beeindigingsovereenkomst", "vaststellingsovereenkomst"]) && has(t, ["arbeidsovereenkomst", "werkgever", "werknemer", "dienstverband"]))
    return { type: "beeindiging", why: why(["beëindigingsovereenkomst", "vaststellingsovereenkomst"]) };
  if (has(t, ["dagvaarding", "dagvaard", "gedaagde"]) && has(t, ["rechtbank", "kantonrechter", "deurwaarder"])) return { type: "dagvaarding", why: why(["dagvaarding", "gedaagde"]) };
  if (has(t, ["bezwaar maken", "kunt u bezwaar", "u kunt bezwaar", "bezwaarschrift"]) && has(t, BESLUIT)) return { type: "overheid_besluit", why: why(["bezwaar", "besluit", "beschikking"]) };
  return { type: "other", why: [] };
}

/** Is this text Dutch or Turkish (or unknown)? Counts common function words; enough for whole letters. */
export function guessLanguage(text) {
  const w = text.toLowerCase().match(/[a-zçğıöşüëéèïäâ]+/g) ?? [];
  const NL = new Set(["de", "het", "een", "van", "en", "dat", "u", "uw", "is", "niet", "op", "met", "voor", "wij", "zijn", "naar", "deze", "dit"]);
  const TR = new Set(["ve", "bir", "bu", "için", "ile", "olarak", "olan", "da", "de", "ne", "gibi", "daha", "kadar", "sayılı", "tarihli"]);
  let nl = 0, tr = 0;
  for (const x of w) { if (NL.has(x)) nl++; if (TR.has(x)) tr++; }
  tr += (text.match(/[ğışİĞŞ]/g) ?? []).length;
  if (nl + tr < 5) return "unknown";
  return nl > tr * 1.5 ? "nl" : tr > nl * 1.5 ? "tr" : "unknown";
}

// where to get a person, by language of the letter (links read 21 Nov 2026)
export const HELP = {
  nl: [
    { name: "Het Juridisch Loket", url: "https://www.juridischloket.nl", what: { nl: "Gratis juridisch advies, ook over brieven van de overheid.", en: "Free legal advice, also on letters from the government.", tr: "Ücretsiz hukuki danışma, kamu kurumlarından gelen mektuplar dahil." } },
    { name: "Raad voor Rechtsbijstand", url: "https://www.rvr.org", what: { nl: "Een advocaat met een eigen bijdrage, als uw inkomen laag is.", en: "A lawyer with a reduced fee, if your income is low.", tr: "Geliriniz düşükse indirimli ücretle avukat." } },
    { name: "Zoek een advocaat (NOvA)", url: "https://zoekeenadvocaat.advocatenorde.nl", what: { nl: "Vind een advocaat, bijvoorbeeld in het vreemdelingenrecht.", en: "Find a lawyer, for example in immigration law.", tr: "Avukat bulun, örneğin yabancılar hukukunda." } },
  ],
};
