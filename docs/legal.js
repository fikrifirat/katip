// What each data group is, why Katip masks it, the legal text it rests on, and what can happen if it leaks.
// Shown in the expandable "Ne maskelenir, neden?" panels of the send page (gonder.html).
// General information, not legal advice. Paraphrases, not official translations: the link is the source.
// Fine amounts in KVKK m.18 are re-valued every year, so we never print a number here.

export const SRC = {
  kvkk: "https://www.mevzuat.gov.tr/mevzuatmetin/1.5.6698.pdf",
  tck: "https://www.mevzuat.gov.tr/mevzuatmetin/1.5.5237.pdf",
  ak: "https://www.mevzuat.gov.tr/mevzuatmetin/1.5.1136.pdf",
  guide: "https://www.kvkk.gov.tr/Icerik/8990/avukatlarin-mesleki-faaliyetlerinde-kisisel-verilerin-korunmasina-iliskin-uygulama-rehberi-yayimlandi",
  srb: "https://curia.europa.eu/juris/liste.jsf?num=C-413/23",
};

// Law references used across groups. ref = short label, src = key in SRC.
const L = {
  m3: { ref: "KVKK m.3(1)(d)", src: "kvkk",
    tr: "Kişisel veri: kimliği belirli veya belirlenebilir gerçek kişiye ilişkin her türlü bilgi.",
    en: "Personal data: any information about an identified or identifiable natural person." },
  m4: { ref: "KVKK m.4(2)(ç)", src: "kvkk",
    tr: "Veri, işlendiği amaçla bağlantılı, sınırlı ve ölçülü olmalı.",
    en: "Data must be relevant, limited and proportionate to the purpose." },
  m6: { ref: "KVKK m.6", src: "kvkk",
    tr: "Sağlık, ceza mahkûmiyeti, din, siyasi görüş, sendika, etnik köken, cinsel hayat ve biyometrik/genetik veriler özel nitelikli kişisel veridir; daha sıkı koşullarla işlenir.",
    en: "Health, criminal convictions, religion, political opinion, union membership, ethnic origin, sex life and biometric/genetic data are special categories, with stricter conditions." },
  m9: { ref: "KVKK m.9", src: "kvkk",
    tr: "Yurt dışına aktarım (7499 sayılı Kanunla değişik): m.5/m.6 şartlarından biri ve yeterlilik kararı ya da uygun güvence (ör. Kurul'a 5 iş günü içinde bildirilen standart sözleşme) gerekir.",
    en: "Transfer abroad (as amended by Law 7499): needs an m.5/m.6 condition plus an adequacy decision or an appropriate safeguard (e.g. standard contracts notified to the Board within 5 business days)." },
  m12: { ref: "KVKK m.12", src: "kvkk",
    tr: "Veri sorumlusu, verilerin hukuka aykırı işlenmesini ve erişilmesini önlemek için gerekli teknik ve idari tedbirleri almak zorundadır. İhlal, Kurul'a ve ilgili kişiye bildirilir.",
    en: "The controller must take the technical and organisational measures needed to prevent unlawful processing and access. Breaches are notified to the Board and the person." },
  m18: { ref: "KVKK m.18", src: "kvkk",
    tr: "m.12 yükümlülüklerine uymamak idari para cezası gerektirir. Tutarlar her yıl yeniden değerlenir; güncel tutar için Kurum duyurusuna bakın.",
    en: "Breaching m.12 duties leads to an administrative fine. Amounts are re-valued every year; check the Authority's current figures." },
  tck136: { ref: "TCK m.136", src: "tck",
    tr: "Kişisel verileri hukuka aykırı olarak başkasına vermek, yaymak veya ele geçirmek: 2–4 yıl hapis.",
    en: "Unlawfully giving, spreading or obtaining personal data: 2–4 years' imprisonment." },
  tck135: { ref: "TCK m.135(2)", src: "tck",
    tr: "Siyasi, felsefi, dinî görüş, ırk, sağlık, cinsel hayat veya sendika bilgisini hukuka aykırı kaydetmek: ceza yarı oranında artar.",
    en: "Unlawfully recording political, philosophical or religious views, race, health, sex life or union data: the penalty is increased by half." },
  tck137: { ref: "TCK m.137", src: "tck",
    tr: "Bu suçlar meslek veya sanatın sağladığı kolaylıktan yararlanılarak işlenirse ceza yarı oranında artar.",
    en: "If these offences are committed by using the advantages of a profession, the penalty is increased by half." },
  ak36: { ref: "Avukatlık Kanunu m.36", src: "ak",
    tr: "Avukat, mesleği dolayısıyla öğrendiği hususları açığa vuramaz (sır saklama). İhlali disiplin sorumluluğu doğurur.",
    en: "A lawyer may not disclose what they learn through their work (professional secrecy). A breach leads to disciplinary liability." },
  guide: { ref: "KVKK Avukatlar Rehberi (22.09.2026), s. 120–121, 146", src: "guide",
    tr: "Üretken yapay zekâ araçlarına müvekkil belgesi yüklemek yurt dışına aktarım olabilir; paylaşmadan önce verilerin maskelenmesi veya anonimleştirilmesi önerilir.",
    en: "Uploading client documents to generative AI tools can be a transfer abroad; the guide recommends masking or anonymising data before sharing." },
  srb: { ref: "ABAD, EDPS v SRB (C-413/23 P, 2025)", src: "srb",
    tr: "AB Adalet Divanı: takma adlı veri, kişiyi makul olarak tanıyamayan alıcı için kişisel veri sayılmayabilir. KVKK'da böyle bir karar yok; riski azaltan bir gerekçe, kalkan değil.",
    en: "EU Court of Justice: pseudonymised data may not be personal data for a recipient who cannot reasonably re-identify the person. KVKK has no such ruling; it lowers the risk, it is not a shield." },
};

// Groups shown in the panels. types = Katip entity types (LABELS keys).
export const GROUPS = [
  { id: "ids", types: ["TCKN", "YKN", "PASSPORT", "FOREIGN_ID", "VKN"],
    name: { tr: "Kimlik numaraları", en: "ID numbers" },
    why: { tr: "Kişiyi tek başına ve kesin olarak gösterir; kimlik hırsızlığına da kapı açar. Yapay zekânın işini görmesi için gerekmez.",
           en: "Identifies the person on its own and for certain, and enables identity fraud. The AI never needs it to do the work." },
    law: ["m3", "m4", "tck136", "tck137"] },
  { id: "names", types: ["PERSON", "BIRTH_DATE"],
    name: { tr: "Ad soyad, doğum tarihi", en: "Names, birth dates" },
    why: { tr: "Kimin hakkında olduğunu doğrudan söyler. Yapay zekâ için [AD SOYAD-1] gibi bir etiket yeterli; cevaptaki etiketleri gerçek isimlerle Katip geri koyar.",
           en: "Says directly who the document is about. A label like [AD SOYAD-1] is enough for the AI; Katip puts the real names back into its answer." },
    law: ["m3", "m4", "tck136"] },
  { id: "contact", types: ["PHONE", "EMAIL", "ADDRESS", "UETS", "IP_ADDRESS"],
    name: { tr: "İletişim ve adres", en: "Contact details and addresses" },
    why: { tr: "Kişiye ulaşmayı ve evini bulmayı sağlar. Tarafın kendi adresi her profilde tam maskelenir.",
           en: "Lets someone reach the person or find their home. A party's own address is masked in full in every profile." },
    law: ["m3", "m4", "m12", "tck136"] },
  { id: "money", types: ["IBAN", "CREDIT_CARD", "PLATE"],
    name: { tr: "Banka, kart, plaka", en: "Bank, card, licence plate" },
    why: { tr: "Hesap ve araç sahibine kayıtlardan ulaşılabilir; dolandırıcılık riski taşır.",
           en: "Registers lead from these to the account or vehicle owner, and they carry fraud risk." },
    law: ["m3", "m4", "m12"] },
  { id: "special", types: ["HEALTH", "RELIGION", "POLITICAL", "UNION", "ETHNICITY", "SEXUAL_LIFE", "BIOMETRIC_GENETIC", "CRIMINAL_RECORD"],
    name: { tr: "Özel nitelikli veriler", en: "Special-category data" },
    why: { tr: "Sızarsa en ağır zararı veren veriler; kanun bunları ayrıca korur ve ceza artırır.",
           en: "The data that does most harm if it leaks; the law protects it separately and raises penalties." },
    law: ["m6", "tck135", "tck137"] },
  { id: "handwriting", types: ["UNREAD"],
    name: { tr: "Okunamayan el yazısı", en: "Unread handwriting" },
    why: { tr: "Taramada okunamayan el yazısı alanı ne içerdiği bilinmediği için güvenli tarafta kalınır ve kapatılır.",
           en: "A handwritten area the scan could not read is covered, because we cannot tell what it says." },
    law: ["m12"] },
  { id: "case", types: ["CASE_NO", "BAR_NO"],
    name: { tr: "Dosya ve sicil numaraları", en: "Case and registry numbers" },
    why: { tr: "Esas/UYAP numarası veya baro sicil numarasıyla dosyaya ve kişilere ulaşılabilir. Emsal kararların künyeleri ise kamuya açıktır ve okunur kalır.",
           en: "A case/UYAP number or a bar registry number can lead to the file and the people in it. Citations of published precedents are public and stay readable." },
    law: ["m3", "ak36"] },
  { id: "context", types: ["DATE", "PLACE", "INSTITUTION"],
    name: { tr: "Tarih, yer, kurum", en: "Dates, places, institutions" },
    why: { tr: "Tek başına kimseyi göstermez, ama bir araya gelince gösterebilir: \"14 Mart'ta Kadıköy'de X Hastanesi'nde\" küçük bir grubu işaret eder. Maskeli metnin hâlâ kişisel veri sayılmasının ana sebebi budur.",
           en: "None of these identifies anyone alone, but together they can: \"on 14 March at X Hospital in Kadıköy\" points to a small group. This is the main reason masked text can still be personal data." },
    law: ["m3", "m4", "srb"] },
];

// The two profiles this page offers (the demo also has a court-filing profile).
export const PROFILES = {
  ai: { name: { tr: "Yapay zekâ ile paylaşım", en: "Sharing with AI" },
    hint: { tr: "Kişileri, numaraları, adresleri ve dosya numaralarını maskeler. Tarih, yer ve kurum okunur kalır, böylece yapay zekâ olayı anlayabilir; bunları aşağıda tek dokunuşla maskeleyebilirsiniz.",
            en: "Masks people, numbers, addresses and case numbers. Dates, places and institutions stay readable so the AI can follow the facts; you can mask them below with one tap." },
    groups: ["ids", "names", "contact", "money", "special", "handwriting", "case"] },
  anon: { name: { tr: "En sıkı", en: "Strictest" },
    hint: { tr: "Bunlara ek olarak tarih, il/ilçe ve mahkeme/kurum/şirket adlarını da maskeler. Metin okunur, kişilerin izi çok zorlaşır. Yine de olayın kendisi kişiyi gösterebilir; kontrol edin.",
            en: "Also masks dates, provinces/districts and court, institution and company names. The text still reads, and the people are much harder to trace. The facts themselves can still point to someone, so check." },
    groups: ["ids", "names", "contact", "money", "special", "handwriting", "case", "context"] },
};

// Lines that apply to every profile.
export const ALWAYS = ["m9", "m12", "m18", "ak36", "guide"];
export const LAW = L;
