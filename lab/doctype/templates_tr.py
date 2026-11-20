"""Turkish document templates for the document-type classifier, three families per type.

A "family" is one way of writing that document: a different layout, different headings, different
phrasing (think: three different law firms, notaries or software vendors). gen.py trains on families
0 and 1 and tests on family 2, so the held-out score measures documents written in a way the model
has never seen, not new fills of a template it memorised.

All text was written for this file. Structure follows public statute (HMK md. 119, 129, 342; İİK md. 58,
60; Tebligat K.; TTK md. 21, 390; KVKK md. 10-13; VUK md. 230) and common practice; no sentence is
copied from a real document or from KVKK-Bench / docs/samples, which are kept as independent test sets.
"""
from __future__ import annotations

from fill import Fill, upper_tr

T: dict[str, list] = {}


def fam(label):
    def deco(fn):
        T.setdefault(label, []).append(fn)
        return fn
    return deco


def opt(f: Fill, p: float, s: str) -> str:
    return s if f.r.random() < p else ""


def para(f: Fill, pool: list[str], k: tuple[int, int]) -> str:
    n = f.r.randint(*k)
    return "\n".join(f.r.sample(pool, min(n, len(pool))))


# ---------------------------------------------------------------- dilekce (dava / talep dilekçesi)
@fam("dilekce")
def dilekce_0(f):
    a, b = f.name(), f.company()
    return f"""{f.court()} {f.pick("HAKİMLİĞİ'NE|BAŞKANLIĞI'NA|HÂKİMLİĞİNE")}

DAVACI      : {a} (TCKN: {f.tckn()})
              {f.address()}
VEKİLİ      : {f.lawyer()} - {f.address()}
DAVALI      : {b}
              {f.address()}
DAVA DEĞERİ : {f.money()}
KONU        : {f.pick(["Fazlaya ilişkin haklarımız saklı kalmak kaydıyla", "Şimdilik"])} {f.money()} {f.pick("alacağın|tazminatın|bedelin")} {f.pick("yasal faiziyle birlikte|ticari faiziyle birlikte|avans faiziyle birlikte")} davalıdan tahsili talebidir.

AÇIKLAMALAR :
1- Müvekkil ile davalı arasında {f.date()} tarihli {f.pick("hizmet|satış|eser|kira")} sözleşmesi imzalanmıştır.
2- {f.pick(["Davalı, sözleşmeden doğan edimini süresinde yerine getirmemiş, ihtarnameye rağmen ödeme yapmamıştır.", "Davalı taraf teslim edilen mallara ilişkin faturaları ödememiş, borcunu kabul etmesine rağmen ifadan kaçınmıştır."])}
3- {f.pick(["Bu nedenle işbu davayı açma zorunluluğu doğmuştur.", "Uyuşmazlığın çözümü için zorunlu arabuluculuk sürecine gidilmiş, anlaşma sağlanamamıştır."])}

HUKUKİ SEBEPLER : HMK, TBK, TTK ve ilgili mevzuat.
DELİLLER    : Sözleşme, faturalar, ihtarname, banka kayıtları, tanık, bilirkişi incelemesi ve her türlü yasal delil.
SONUÇ VE İSTEM : Yukarıda açıklanan nedenlerle davamızın kabulü ile {f.money()} alacağın {f.pick("dava tarihinden|temerrüt tarihinden")} itibaren işleyecek faiziyle birlikte davalıdan tahsiline, yargılama giderleri ile vekâlet ücretinin davalıya yükletilmesine karar verilmesini saygılarımızla arz ve talep ederiz. {f.date()}

Davacı Vekili
{f.lawyer()}"""


@fam("dilekce")
def dilekce_1(f):
    a = f.name()
    talep = f.pick(["ihtiyati tedbir", "ihtiyati haciz", "delil tespiti", "adli yardım", "tanık listesi sunulması",
                    "süre verilmesi", "keşif yapılması", "davadan feragat"])
    return f"""{f.pick("NÖBETÇİ ", "")}{f.court()}'NE
{opt(f, .6, "Dosya No: " + f.esas() + " Esas")}

TALEP EDEN  : {a}
ADRESİ      : {f.address()}
{opt(f, .7, "VEKİLİ      : " + f.lawyer())}
KARŞI TARAF : {f.pick([f.name(), f.company()])}

KONU : {upper_tr(talep[0]) + talep[1:]} talebimizden ibarettir.

AÇIKLAMALAR :
{para(f, [
        f"Mahkemenizin yukarıda numarası yazılı dosyasında {f.pick('davacı|davalı')} sıfatıyla taraf bulunmaktayız.",
        f"Karşı tarafın dava konusu {f.pick('taşınmazı|aracı|hisseleri')} üçüncü kişilere devretme ihtimali bulunduğundan hakkımızın korunması gerekmektedir.",
        "Gecikmesinde sakınca bulunan hâl mevcut olup telafisi güç zararların doğması muhtemeldir.",
        f"Talebimiz {f.pick('HMK md. 389|HMK md. 400|HMK md. 334|İİK md. 257|HMK md. 240')} uyarınca yerindedir.",
        "Durumu gösterir belgeler dilekçemiz ekinde sunulmuştur.",
        "Tanıklarımızın isim ve adresleri aşağıda gösterilmiştir.",
    ], (2, 5))}

SONUÇ VE TALEP : Açıklanan nedenlerle {talep} talebimizin kabulüne karar verilmesini saygılarımla arz ve talep ederim.

{f.date()}
{f.pick("Talep Eden|Davacı Vekili|Davalı Vekili")}
{f.pick([a, f.lawyer()])}
EKLER : {f.pick(["Vekaletname", "Tapu kaydı, vekaletname", "Fakirlik belgesi", "Fotoğraflar, tutanak"])}"""


@fam("dilekce")
def dilekce_2(f):
    a, b = f.name(), f.name()
    return f"""T.C.
{f.court()}
{f.pick("SAYIN HÂKİMİ", "BAŞKANLIĞINA", "HAKİMLİĞİNE")}

Dava eden {a} (T.C. Kimlik No {f.tckn()}), {f.address()} adresinde oturmaktadır. Vekili {f.lawyer()}.
Dava edilen {b}, {f.address()}.
Davanın konusu: {f.dava()} talebi.
Değeri: {f.money()}

Olaylar
{para(f, [
        f"{f.date()} tarihinde taraflar arasında {f.pick('trafik kazası|iş kazası|kira uyuşmazlığı|satım ilişkisi')} meydana gelmiştir.",
        f"Davalı tarafın kusurlu davranışı nedeniyle müvekkil {f.money()} tutarında zarara uğramıştır.",
        "Zararın tespiti için bilirkişi incelemesi yapılması gerekmektedir.",
        "Arabuluculuk son tutanağı dilekçe ekinde sunulmuştur, dava şartı yerine getirilmiştir.",
        "Davalıya keşide edilen ihtarname sonuçsuz kalmıştır.",
        "Uyuşmazlık konusu alacak muaccel olup davalı temerrüde düşmüştür.",
    ], (3, 5))}

Hukuki nedenler: {f.pick(["TBK md. 49 vd.", "TBK md. 112 vd.", "4857 sayılı İş Kanunu", "TMK md. 683 vd.", "6502 sayılı TKHK"])}, HMK md. 119.
Kanıtlar: {f.pick(["kaza tespit tutanağı, sigorta kayıtları", "SGK kayıtları, bordrolar, tanık", "tapu kayıtları, keşif", "yazışmalar, e-posta çıktıları"])}, bilirkişi raporu ve sair deliller.

İstek: Davanın kabulüne, {f.money()} tutarın davalıdan alınarak müvekkile verilmesine, masrafların ve avukatlık ücretinin karşı tarafa bırakılmasına karar verilmesini dilerim.

{f.date()}
Davacı vekili {f.lawyer()} (e-imzalıdır)"""


# ---------------------------------------------------------------- cevap_dilekcesi
@fam("cevap_dilekcesi")
def cevap_0(f):
    return f"""{f.court()} {f.pick("HAKİMLİĞİ'NE|BAŞKANLIĞI'NA")}

DOSYA NO    : {f.esas()} Esas
CEVAP VEREN
DAVALI      : {f.company()}
VEKİLİ      : {f.lawyer()}
DAVACI      : {f.name()}
KONU        : Davaya karşı cevaplarımızın sunulmasından ibarettir.
TEBLİĞ TARİHİ: {f.date()}

AÇIKLAMALAR :
1- Dava dilekçesi müvekkile {f.date()} tarihinde tebliğ edilmiş olup {f.pick("iki haftalık yasal süre içinde|HMK md. 127'de öngörülen süre içinde")} cevaplarımızı sunuyoruz.
2- ÖN İTİRAZLARIMIZ: {f.pick(["Mahkemenizin yetkisine itiraz ediyoruz; yetkili mahkeme " + f.city() + " mahkemeleridir.", "Davacının iddia ettiği alacak zamanaşımına uğramıştır.", "Dava şartı olan arabuluculuk yoluna başvurulmadığından dava usulden reddedilmelidir."])}
3- ESASA İLİŞKİN CEVAPLARIMIZ: Davacının iddiaları gerçeği yansıtmamaktadır. Müvekkil sözleşmeden doğan tüm edimlerini eksiksiz ifa etmiştir.
4- Davacı tarafından sunulan belgeler kabul edilmemektedir; imzaya ve içeriğe itiraz ediyoruz.

DELİLLER    : Ticari defterler, sözleşme, teslim belgeleri, tanık, bilirkişi incelemesi.
SONUÇ VE İSTEM : Haksız ve mesnetsiz davanın {f.pick("öncelikle usulden, aksi halde esastan reddine", "reddine")}, yargılama giderleri ve vekâlet ücretinin davacıya yükletilmesine karar verilmesini arz ve talep ederiz.

Davalı Vekili
{f.lawyer()}"""


@fam("cevap_dilekcesi")
def cevap_1(f):
    kind = f.pick(["CEVAP DİLEKÇESİ", "CEVAP DİLEKÇEMİZDİR", "CEVABA CEVAP DİLEKÇESİ", "İKİNCİ CEVAP DİLEKÇESİ"])
    return f"""{kind}

{f.court()}'NE
Esas No: {f.esas()}

Davalı: {f.name()} - {f.address()}
Vekili: {f.lawyer()}
Davacı: {f.company()}

Davacı yanın {f.pick("dava dilekçesine|replik dilekçesine")} karşı beyan ve itirazlarımızı aşağıda arz ediyoruz:

{para(f, [
        "Davacının ileri sürdüğü olaylar tamamen gerçek dışıdır, kabul etmiyoruz.",
        "Davacı yan iddialarını ispat edecek hiçbir belge sunamamıştır; ispat yükü davacıdadır.",
        f"Talep edilen {f.money()} tutar fahiştir, hesaplama yöntemine itiraz ediyoruz.",
        "Müvekkilin olayda herhangi bir kusuru bulunmamaktadır; zarar davacının kendi kusurundan doğmuştur.",
        "Husumet yönünden davanın reddi gerekmektedir; müvekkil pasif dava ehliyetine sahip değildir.",
        "Takas ve mahsup def'imizi ileri sürüyoruz.",
        "Davacının yeni vakıa ileri sürmesine ve iddiasını genişletmesine muvafakatimiz yoktur.",
    ], (3, 6))}

Sonuç: Davanın reddine, yargılama gideri ve ücreti vekâletin karşı tarafa yükletilmesine karar verilmesini talep ederiz. {f.date()}

{f.lawyer()}"""


@fam("cevap_dilekcesi")
def cevap_2(f):
    return f"""T.C.
{f.court()}
Dosya: {f.esas()} E.

Sayın Mahkeme,

Müvekkil {f.name()} aleyhine açılan {f.dava().lower()} davasında, dava dilekçesinin tebliği üzerine süresi içinde cevaplarımızı sunarız.

I. Usule ilişkin itirazlar
{f.pick(["Görev itirazımız vardır; uyuşmazlık tüketici mahkemesinin görev alanındadır.", "Derdestlik itirazımız vardır; aynı konuda " + f.esas() + " esas sayılı dosya görülmektedir.", "Kesin yetki kuralına aykırılık bulunmaktadır."])}

II. Esasa ilişkin savunmalarımız
Davacının talepleri hukuki dayanaktan yoksundur. {f.pick(["Kira bedelleri eksiksiz ödenmiştir; dekontlar ektedir.", "İşçinin fesih bildirimi haklı nedene dayanmaktadır.", "Ayıp ihbarı süresinde yapılmamıştır (TTK md. 23)."])}
Davacının ıslah yoluyla talebini artırmasına muvafakat etmediğimizi bildiririz.

III. Delillerimiz
Banka dekontları, yazışmalar, tanık {f.name()}, bilirkişi.

IV. Talep
Davanın reddine karar verilmesini saygıyla talep ederiz.

Davalı vekili {f.lawyer()}
{f.date()}"""


# ---------------------------------------------------------------- kanun_yolu (istinaf / temyiz)
@fam("kanun_yolu")
def kanun_0(f):
    return f"""{upper_tr(f.city())} BÖLGE ADLİYE MAHKEMESİ İLGİLİ HUKUK DAİRESİ BAŞKANLIĞI'NA
Gönderilmek üzere
{f.court()}'NE

DOSYA NO        : {f.esas()} Esas - {f.esas()} Karar
İSTİNAF EDEN    : {f.pick("Davacı|Davalı")} {f.name()}
VEKİLİ          : {f.lawyer()}
KARŞI TARAF     : {f.company()}
KARAR TARİHİ    : {f.date()}
TEBLİĞ TARİHİ   : {f.date()}
KONU            : Yerel mahkeme kararına karşı istinaf başvurusu ve gerekçelerimizdir.

İSTİNAF SEBEPLERİ :
1- İlk derece mahkemesi eksik inceleme ile hüküm kurmuştur; tanıklarımız dinlenmemiştir.
2- Bilirkişi raporu denetime elverişli değildir, itirazlarımız karşılanmamıştır.
3- Karar gerekçesi HMK md. 297'ye aykırıdır.
4- {f.pick(["Faiz başlangıç tarihi hatalı belirlenmiştir.", "Vekâlet ücreti hatalı hesaplanmıştır.", "Zamanaşımı def'imiz değerlendirilmemiştir."])}

SONUÇ VE İSTEM : İstinaf başvurumuzun kabulü ile {f.pick("kararın kaldırılmasına|yeniden esas hakkında karar verilmesine|dosyanın yeniden görülmek üzere ilk derece mahkemesine gönderilmesine")} karar verilmesini talep ederiz.

İstinaf Eden Vekili
{f.lawyer()}"""


@fam("kanun_yolu")
def kanun_1(f):
    return f"""YARGITAY {f.r.randint(1, 23)}. {f.pick("HUKUK|CEZA")} DAİRESİ BAŞKANLIĞI'NA
Gönderilmek üzere {upper_tr(f.city())} BÖLGE ADLİYE MAHKEMESİ {f.r.randint(1, 30)}. HUKUK DAİRESİ'NE

Dosya: {f.esas()} E. / {f.esas()} K.

TEMYİZ EDEN : {f.name()}
VEKİLİ      : {f.lawyer()}
KARŞI TARAF : {f.name()}

KONU: Bölge adliye mahkemesi kararının temyizen incelenerek bozulması talebidir.

TEMYİZ NEDENLERİ:
{para(f, [
        "Bölge adliye mahkemesi, istinaf başvurumuzu esastan reddederken gerekçe göstermemiştir.",
        "Hükme esas alınan bilirkişi raporu ile karar arasında çelişki bulunmaktadır.",
        "Yerleşik Yargıtay içtihatlarına aykırı karar verilmiştir.",
        "Hukuki dinlenilme hakkımız ihlal edilmiştir.",
        "Kesinlik sınırı aşıldığından karar temyize tabidir.",
        f"Uyuşmazlık değeri {f.money()} olup temyiz sınırının üzerindedir.",
    ], (3, 5))}

Açıklanan nedenlerle kararın BOZULMASINA karar verilmesini saygılarımızla arz ederiz.
{f.date()}
Temyiz eden vekili {f.lawyer()}"""


@fam("kanun_yolu")
def kanun_2(f):
    return f"""{f.court()}'NE
(Bölge Adliye Mahkemesine sunulmak üzere)

Esas: {f.esas()}  Karar: {f.esas()}

İstinaf yoluna başvuran davalı {f.company()} vekili olarak, mahkemenizin {f.date()} tarihli kararını aşağıdaki nedenlerle istinaf ediyoruz.

Başvuru süresi: Gerekçeli karar {f.date()} tarihinde tebliğ edilmiştir; iki haftalık süre içindeyiz.

Kararın hukuka aykırılığı:
a) Mahkeme davacının delillerini yeterli kabul etmiş, bizim delillerimizi değerlendirmemiştir.
b) {f.pick(["Hükmedilen manevi tazminat fahiştir.", "Hesaplamada brüt ücret esas alınmıştır, bu hatalıdır.", "Kira bedelinin tespitinde emsal kira bedelleri dikkate alınmamıştır."])}
c) Kamu düzenine aykırılık resen gözetilmelidir.

İstem: Kararın kaldırılmasına, davanın reddine; olmazsa dosyanın ilk derece mahkemesine iadesine karar verilmesi.
İstinaf karar ve ilam harcı yatırılmıştır.

{f.lawyer()}  {f.date()}"""


# ---------------------------------------------------------------- suc_duyurusu
@fam("suc_duyurusu")
def suc_0(f):
    return f"""{upper_tr(f.city())} CUMHURİYET BAŞSAVCILIĞI'NA

MÜŞTEKİ     : {f.name()} (TCKN: {f.tckn()})
ADRES       : {f.address()}
VEKİLİ      : {f.lawyer()}
ŞÜPHELİ     : {f.pick([f.name(), "Faili meçhul"])}
SUÇ         : {f.pick(["Dolandırıcılık (TCK md. 157)", "Güveni kötüye kullanma (TCK md. 155)", "Tehdit (TCK md. 106)", "Hakaret (TCK md. 125)", "Kişisel verilerin hukuka aykırı olarak kaydedilmesi (TCK md. 135)", "Mala zarar verme (TCK md. 151)"])}
SUÇ TARİHİ  : {f.date()}
KONU        : Şüpheli hakkında suç duyurusu ve şikâyetimizdir.

AÇIKLAMALAR :
1- {f.pick(["Şüpheli, kendisini banka görevlisi olarak tanıtarak müvekkilden " + f.money() + " tutarında para transferi yapılmasını sağlamıştır.", "Şüpheli, sosyal medya hesabı üzerinden müvekkile yönelik ağır hakaret içeren mesajlar göndermiştir.", "Şüpheli, müvekkilin işyerine gelerek tehditte bulunmuş ve camlarını kırmıştır."])}
2- Olaya ilişkin ekran görüntüleri, banka dekontları ve tanık beyanları mevcuttur.
3- Şüphelinin eylemi suç teşkil etmektedir.

SONUÇ VE İSTEM : Şüphelinin cezalandırılması için kamu davası açılmasını, delillerin toplanmasını ve şüphelinin ifadesinin alınmasını talep ederiz. Şikâyetçiyiz.

{f.date()}
Müşteki Vekili {f.lawyer()}"""


@fam("suc_duyurusu")
def suc_1(f):
    return f"""T.C. {upper_tr(f.city())} CUMHURİYET BAŞSAVCILIĞINA

ŞİKÂYETÇİ : {f.name()}, {f.address()}, Tel: {f.phone()}
ŞÜPHELİLER: {f.name()} ve {f.name()}

ŞİKÂYET KONUSU: {f.pick(["Konut dokunulmazlığının ihlali", "Kasten yaralama", "Hırsızlık", "Resmi belgede sahtecilik", "Şantaj", "Israrlı takip"])}

OLAYIN ÖZETİ:
{para(f, [
        f"{f.date()} günü saat {f.r.randint(0, 23):02d}.{f.r.randint(0, 59):02d} sıralarında şüpheliler evime zorla girmişlerdir.",
        "Olay anında kolluk kuvvetlerine haber verilmiş, olay yeri tutanağı tutulmuştur.",
        "Hastaneden alınan adli rapor dilekçeme eklenmiştir.",
        "Şüpheliler daha önce de benzer eylemlerde bulunmuşlardır.",
        "Olayın görgü tanığı komşum adı geçen kişidir.",
        "Güvenlik kamerası kayıtlarının ivedilikle temin edilmesini talep ediyorum.",
    ], (3, 5))}

Şüphelilerden şikâyetçiyim; haklarında gerekli soruşturmanın yapılarak cezalandırılmalarını arz ederim.
Şikâyetçi {f.name()}  {f.date()}"""


@fam("suc_duyurusu")
def suc_2(f):
    return f"""SUÇ DUYURUSU

Makam: {f.city()} Cumhuriyet Başsavcılığı (Soruşturma Bürosu)

Suç duyurusunda bulunan: {f.company()} adına yetkili {f.name()}
Vekili: {f.lawyer()}
Hakkında suç duyurusunda bulunulan: Şirketin eski çalışanı {f.name()}

Olaylar: Şüpheli, şirkette muhasebe sorumlusu olarak görev yaptığı dönemde {f.pick("şirket hesaplarından kendi hesabına havale yapmış", "müşteri verilerini kopyalayarak rakip firmaya aktarmış", "sahte faturalar düzenlemiş")} ve şirketi {f.money()} zarara uğratmıştır. İç denetim raporu ektedir.

Sevk maddeleri: {f.pick(["TCK md. 155", "TCK md. 136", "TCK md. 204", "TCK md. 158"])} ve ilgili hükümler.

Talep: CMK md. 160 uyarınca soruşturma başlatılarak delillerin karartılmasının önlenmesi için arama ve el koyma kararı alınmasını, şüphelinin yargılanmasını isteriz.

{f.date()}
{f.lawyer()}"""


# ---------------------------------------------------------------- karar
@fam("karar")
def karar_0(f):
    return f"""T.C.
{f.court()}
GEREKÇELİ KARAR

ESAS NO     : {f.esas()} Esas
KARAR NO    : {f.esas()} Karar
HAKİM       : {f.name()} {f.r.randint(10000, 99999)}
KATİP       : {f.name()} {f.r.randint(10000, 99999)}
DAVACI      : {f.name()}
VEKİLİ      : {f.lawyer()}
DAVALI      : {f.company()}
DAVA        : {f.dava()}
DAVA TARİHİ : {f.date()}
KARAR TARİHİ: {f.date()}

Mahkememizde görülmekte olan dava dosyasının yapılan açık yargılaması sonunda;
İDDİA: Davacı vekili dava dilekçesinde özetle; {f.pick(["müvekkilin davalı nezdinde çalıştığını, işçilik alacaklarının ödenmediğini", "taraflar arasındaki sözleşme gereği bedelin ödenmediğini", "kiralananın süresinde tahliye edilmediğini"])} beyanla davanın kabulünü talep etmiştir.
SAVUNMA: Davalı vekili cevap dilekçesinde özetle; davanın reddini savunmuştur.
DELİLLER VE GEREKÇE: Toplanan deliller, bilirkişi raporu ve tüm dosya kapsamından; {f.pick(["davacının iddialarını ispat ettiği", "davacının iddiasını ispat edemediği"])} anlaşılmıştır.
HÜKÜM: Gerekçesi yukarıda açıklandığı üzere;
1- Davanın {f.pick("KABULÜ|REDDİ|KISMEN KABULÜ")} ile,
2- Alınması gereken {f.money()} harçtan peşin alınan harcın mahsubuna,
3- Davacı kendisini vekil ile temsil ettirdiğinden AAÜT gereğince {f.money()} vekâlet ücretinin davalıdan alınarak davacıya verilmesine,
Dair, taraf vekillerinin yüzüne karşı, gerekçeli kararın tebliğinden itibaren 2 hafta içinde {f.pick("istinaf|temyiz")} yolu açık olmak üzere verilen karar açıkça okunup usulen anlatıldı. {f.date()}

Katip {f.r.randint(10000, 99999)}  Hakim {f.r.randint(10000, 99999)}
e-imzalıdır  e-imzalıdır"""


@fam("karar")
def karar_1(f):
    d = f.r.randint(1, 23)
    return f"""{f.pick(["YARGITAY", "T.C. YARGITAY"])} {d}. {f.pick("HUKUK|CEZA")} DAİRESİ
Esas No: {f.esas()}
Karar No: {f.esas()}

MAHKEMESİ : {f.court()}
TARİHİ    : {f.date()}
DAVA TÜRÜ : {f.dava()}

Taraflar arasındaki davadan dolayı Bölge Adliye Mahkemesince verilen kararın temyizen incelenmesi {f.pick("davacı|davalı")} vekili tarafından istenilmekle, temyiz dilekçesinin süresinde olduğu anlaşıldıktan sonra dosya incelendi, gereği görüşülüp düşünüldü:
{para(f, [
        "Dosyadaki yazılara, kararın dayandığı delillerle kanuni gerektirici sebeplere göre temyiz itirazları yerinde değildir.",
        "Somut olayda, mahkemece eksik inceleme ile karar verildiği anlaşılmaktadır.",
        "Hükme esas alınan bilirkişi raporu denetime elverişli olmadığından yeniden rapor alınması gerekir.",
        "Dairemizin yerleşik uygulamasına göre bu tür davalarda zamanaşımı süresi on yıldır.",
        "Hal böyle olunca, mahkemece yapılacak iş, tarafların tüm delillerini toplayarak sonucuna göre bir karar vermekten ibarettir.",
        "Davacının işyerinde fazla mesai yaptığı tanık beyanlarıyla sabittir.",
    ], (3, 5))}
SONUÇ: Yukarıda açıklanan nedenlerle kararın {f.pick(["BOZULMASINA", "ONANMASINA", "DÜZELTİLEREK ONANMASINA"])}, peşin harcın istek halinde iadesine, {f.date()} tarihinde oy birliğiyle karar verildi."""


@fam("karar")
def karar_2(f):
    return f"""T.C.
{upper_tr(f.city())} BÖLGE ADLİYE MAHKEMESİ
{f.r.randint(1, 30)}. HUKUK DAİRESİ
İSTİNAF İNCELEMESİ SONUNDA VERİLEN KARAR

DOSYA NO: {f.esas()}  KARAR NO: {f.esas()}
İNCELENEN KARARIN MAHKEMESİ: {f.court()}
BAŞKAN: {f.name()}   ÜYE: {f.name()}   ÜYE: {f.name()}
İSTİNAF EDEN: {f.pick("Davacı|Davalı")} vekili
DAVANIN KONUSU: {f.dava()}

Yukarıda açık kimliği yazılı taraflar arasındaki davada ilk derece mahkemesince verilen hükme karşı istinaf başvurusu üzerine dosya Dairemize gönderilmiş olmakla incelendi:
Uyuşmazlık, {f.pick(["kira bedelinin tespiti", "kıdem tazminatının hesaplanması", "ayıplı maldan doğan bedel iadesi"])} noktasında toplanmaktadır. Dairemizce yapılan incelemede ilk derece mahkemesinin kabulünde usul ve esas bakımından hukuka aykırılık görülmemiştir.
HÜKÜM: Gerekçesi yukarıda açıklandığı üzere; HMK md. {f.pick("353/1-b-1|353/1-a-6|353/1-b-2")} gereğince istinaf başvurusunun ESASTAN REDDİNE, harcın mahsubuna, dosya üzerinden yapılan inceleme sonucunda, kararın tebliğinden itibaren iki hafta içinde Yargıtay'da temyiz yolu açık olmak üzere oy birliği ile karar verildi. {f.date()}"""


# ---------------------------------------------------------------- durusma_zapti
@fam("durusma_zapti")
def zabit_0(f):
    return f"""T.C.
{f.court()}
DURUŞMA TUTANAĞI

ESAS NO       : {f.esas()}
CELSE NO      : {f.r.randint(1, 9)}
CELSE TARİHİ  : {f.date()}
HAKİM         : {f.name()} {f.r.randint(10000, 99999)}
KATİP         : {f.name()} {f.r.randint(10000, 99999)}

Belli gün ve saatte {f.pick("açık|SEGBİS ile")} duruşmaya başlandı. Davacı vekili {f.lawyer()} geldi, davalı vekili {f.lawyer()} geldi. Açık yargılamaya devam olundu.
{para(f, [
        "Tanık huzura alındı, kimliği soruldu, yemini yaptırıldı, beyanı okunup imzası alındı.",
        "Davacı vekili: Bilirkişi raporuna karşı beyanlarımız dilekçemizde mevcuttur, tekrar ederiz dedi.",
        "Davalı vekili: Tanık beyanlarına itiraz ediyoruz, tanık taraflı beyanda bulunmuştur dedi.",
        "Dosya ek rapor alınmak üzere bilirkişiye tevdi edildi.",
        "Mahkemece taraflara sulh olup olmayacakları soruldu, sulh olmayacaklarını beyan ettiler.",
        "Keşif masrafının yatırıldığı anlaşıldı.",
    ], (3, 5))}
G.D: 1- Eksik hususların ikmali için,
2- Davacı vekiline tanık ücretini yatırması için 2 haftalık kesin süre verilmesine,
3- Duruşmanın {f.date()} günü saat {f.r.randint(9, 16)}:{f.pick("00|15|30|45")}'e bırakılmasına karar verildi. {f.date()}

Katip  Hakim
e-imza  e-imza"""


@fam("durusma_zapti")
def zabit_1(f):
    return f"""{f.court()}
Dosya: {f.esas()}
DURUŞMA ZAPTI ({f.r.randint(1, 8)}. Oturum)

Başkan: {f.name()}  Üye: {f.name()}  Üye: {f.name()}
C. Savcısı: {f.name()}
Zabıt Katibi: {f.name()}

Sanık {f.name()} tutuksuz olarak geldi. Müdafii {f.lawyer()} hazır. Katılan vekili hazır.
Sanığa iddianame okundu, savunması soruldu:
Sanık savunmasında: "{f.pick(["Suçlamayı kabul etmiyorum, olay günü orada değildim.", "Olay kendimi korumak için oldu, kasıtlı değildi.", "Müştekiyi tanımam, hesabımı başkası kullandı."])}" dedi.
Tanık {f.name()} dinlendi, yemin ettirildi.
Cumhuriyet Savcısı esas hakkındaki mütalaasını hazırlamak için süre istedi.
ARA KARAR: Sanığın tutuksuz yargılanmasına devam edilmesine, eksik adli sicil kaydının celbine, duruşmanın {f.date()} tarihine ertelenmesine oy birliğiyle karar verildi.
Açıkça okunup anlatıldı."""


@fam("durusma_zapti")
def zabit_2(f):
    return f"""TUTANAK - CELSE {f.r.randint(1, 9)}
{f.court()} / {f.esas()} E.
Tarih: {f.date()}  Saat: {f.r.randint(9, 16)}:{f.pick("00|10|20|40")}

Hazır olanlar: Davacı asil {f.name()}, davacı vekili {f.lawyer()}. Davalı ve vekili gelmedi, tebligat usulüne uygun.
Önceki ara karara uyulduğu görüldü. Celse açıldı.
Davacı asil beyanında: {f.pick(["Ben dava dilekçemi tekrar ediyorum, kira bedelini ödemiyor.", "Eşimle bir araya gelmemiz mümkün değil, boşanmak istiyorum.", "İşten haklı bir neden olmadan çıkarıldım."])}
Davacı vekili: Tanıklarımızın dinlenmesini talep ederiz.
Mahkemece: Tanık listesinin verildiği, tanıkların bir sonraki celsede dinlenmesine, taraflara gelecek celse için davetiye çıkarılmasına,
Duruşmanın {f.date()} tarihine talikine karar verildi.
Hâkim  Zabıt kâtibi"""


# ---------------------------------------------------------------- tutanak (tespit / teslim / toplantı dışı genel)
@fam("tutanak")
def tutanak_0(f):
    kind = f.pick(["TESPİT TUTANAĞI", "TESLİM TESELLÜM TUTANAĞI", "HASAR TESPİT TUTANAĞI", "OLAY YERİ TUTANAĞI"])
    return f"""{kind}

Tarih : {f.date()}   Saat: {f.r.randint(8, 20)}:{f.pick("00|15|30|45")}
Yer   : {f.address()}

{f.date()} günü yukarıda adresi yazılı yerde aşağıda imzası bulunanlar tarafından yapılan incelemede;
{para(f, [
        f"Kiralanan dairenin anahtarları kiracı {f.name()} tarafından mal sahibine teslim edilmiştir.",
        "Dairenin mutfak tezgâhında kırık, salon duvarında rutubet izi tespit edilmiştir.",
        f"Teslim edilen demirbaşlar: {f.pick(['1 adet kombi, 2 adet klima', 'buzdolabı, çamaşır makinesi', 'ofis masası, 4 adet sandalye'])}.",
        f"Elektrik sayaç endeksi {f.r.randint(1000, 99999)}, su sayacı {f.r.randint(100, 9999)} olarak okunmuştur.",
        "Olay yerinde fotoğraf çekilmiş ve tutanağa eklenmiştir.",
        "Taraflar tespit edilen hususları kabul etmişlerdir.",
    ], (3, 5))}

İşbu tutanak {f.pick("iki|üç")} nüsha olarak düzenlenmiş, okunarak birlikte imza altına alınmıştır.

Teslim Eden          Teslim Alan          Tanık
{f.name()}       {f.name()}       {f.name()}"""


@fam("tutanak")
def tutanak_1(f):
    return f"""T.C.
{upper_tr(f.city())} {f.pick("İL EMNİYET MÜDÜRLÜĞÜ|JANDARMA KOMUTANLIĞI|BELEDİYE BAŞKANLIĞI ZABITA MÜDÜRLÜĞÜ")}
{f.pick(["İFADE TUTANAĞI", "YAKALAMA VE GÖZALTI TUTANAĞI", "ZABITA TESPİT TUTANAĞI", "ARAMA VE ELKOYMA TUTANAĞI"])}

Düzenleme tarihi ve saati: {f.date()} {f.r.randint(0, 23):02d}:{f.r.randint(0, 59):02d}
Düzenleyen: {f.pick("Polis Memuru|Komiser Yardımcısı|Zabıta Memuru|J.Astsb.Çvş.")} {f.name()}

Görevimiz esnasında {f.address()} adresinde yapılan kontrolde;
{f.pick(["işyerinin ruhsatsız faaliyet gösterdiği,", "şüphelinin üzerinde yapılan aramada suç unsuru bulunduğu,", "şahsın kendisine yöneltilen soruları müdafii huzurunda cevaplandırdığı,"])}
{f.pick(["işletme sahibine 5326 sayılı Kabahatler Kanunu gereğince işlem yapıldığı,", "elde edilen eşyaların muhafaza altına alındığı,", "şahsa CMK md. 147 gereğince hakları hatırlatıldığı,"])}
tespit edilmiş olup işbu tutanak mahallinde tanzim edilerek birlikte imza altına alınmıştır.

Tutanak Mümzii    Tutanak Mümzii    Hazır Bulunan
{f.name()}   {f.name()}   {f.name()}"""


@fam("tutanak")
def tutanak_2(f):
    return f"""Tutanaktır.

{f.date()} tarihinde {f.company()} {f.pick("şantiyesinde|deposunda|merkez ofisinde")} {f.pick("iş kazası|yangın|su baskını|hırsızlık olayı")} meydana gelmiştir. Olay yerinde bulunan aşağıda isimleri yazılı kişiler olayı şu şekilde tespit etmiştir:

- Olay saat {f.r.randint(0, 23):02d}.{f.r.randint(0, 59):02d} civarında gerçekleşmiştir.
- {f.pick(["Çalışan " + f.name() + " iskeleden düşerek yaralanmış ve hastaneye kaldırılmıştır.", "Deponun arka kapısının kilidinin kırık olduğu görülmüştür.", "Elektrik panosunda kısa devre olduğu anlaşılmıştır."])}
- Olay ile ilgili SGK'ya bildirim yapılacak, kamera kayıtları muhafaza edilecektir.
- Tahmini zarar {f.money()} olarak değerlendirilmiştir.

Bu tutanak olay yerinde tarafımızca düzenlenip okunarak imzalanmıştır.
İş Güvenliği Uzmanı: {f.name()}
Şantiye Şefi: {f.name()}
Tanık: {f.name()}"""


# ---------------------------------------------------------------- bilirkisi_raporu
@fam("bilirkisi_raporu")
def bilirkisi_0(f):
    return f"""{f.court()}'NE

BİLİRKİŞİ RAPORU

DOSYA NO    : {f.esas()} Esas
DAVACI      : {f.name()}
DAVALI      : {f.company()}
BİLİRKİŞİ   : {f.name()} ({f.pick("Mali Müşavir|İnşaat Mühendisi|Makine Mühendisi|Hesap Uzmanı|Bankacı|Hekim")})
GÖREV TARİHİ: {f.date()}

I. GÖREV
Mahkemenizin {f.date()} tarihli ara kararı ile {f.pick(["tarafların ticari defterleri üzerinde inceleme yapılarak davacının alacağının hesaplanması", "dava konusu yapıdaki ayıpların ve giderim bedelinin tespiti", "davacının işçilik alacaklarının hesaplanması"])} hususunda rapor tanzimi istenmiştir.

II. İNCELEME
{para(f, [
        "Dosya kapsamındaki tüm belgeler incelenmiştir.",
        f"Taraflara ait {f.year()} yılı ticari defterleri usulüne uygun tutulmuş ve kapanış tasdikleri yapılmıştır.",
        f"Mahallinde {f.date()} tarihinde keşif yapılmış, fotoğraflar çekilmiştir.",
        "Davacı ücretinin brüt asgari ücretin üzerinde olduğu bordrolardan anlaşılmıştır.",
        "Hesaplamada Yargıtay uygulaması gereği 1/3 oranında hakkaniyet indirimi yapılmıştır.",
        "Yapılan hesaplama ekteki tabloda gösterilmiştir.",
    ], (3, 5))}

III. SONUÇ
Takdiri Sayın Mahkemeye ait olmak üzere, davacının talep edebileceği alacak tutarının {f.money()} olduğu kanaatine varılmıştır.

Saygılarımla arz ederim. {f.date()}
Bilirkişi {f.name()}"""


@fam("bilirkisi_raporu")
def bilirkisi_1(f):
    return f"""EK RAPOR / BİLİRKİŞİ HEYETİ RAPORU
Mahkeme: {f.court()}
Dosya: {f.esas()}

Heyet: {f.name()} (Hukukçu), {f.name()} ({f.pick("Kusur Uzmanı|Aktüer|Tapu Kadastro Uzmanı|Bilişim Uzmanı")}), {f.name()}

1. Dosya özeti ve itirazlar
{f.pick("Davacı|Davalı")} vekilinin kök rapora yönelik itiraz dilekçesi incelenmiştir. İtirazlarda {f.pick(["kusur oranının hatalı belirlendiği", "hesaplamada yanlış ücret alındığı", "taşınmazın değerinin düşük tespit edildiği"])} ileri sürülmüştür.
2. Değerlendirme
{para(f, [
        "Kaza tespit tutanağı ve olay yeri krokisi birlikte değerlendirildiğinde sürücünün asli kusurlu olduğu görülmüştür.",
        "TRH 2010 yaşam tablosu ve %1,8 teknik faiz esas alınarak destekten yoksun kalma tazminatı hesaplanmıştır.",
        "Emsal satışlar dikkate alınarak taşınmazın m² değeri belirlenmiştir.",
        "Kök raporda yapılan hesaplama hatası düzeltilmiştir.",
        "Dijital deliller hash değerleri alınarak incelenmiştir.",
    ], (2, 4))}
3. Sonuç ve kanaat
Heyetimizce {f.pick("kusur oranları %75 - %25", "tazminat tutarı " + f.money(), "taşınmazın değeri " + f.money())} olarak belirlenmiş olup takdir Mahkemenize aittir.
{f.date()}"""


@fam("bilirkisi_raporu")
def bilirkisi_2(f):
    return f"""Sayın {f.court()} Hâkimliğine
Esas: {f.esas()}

Konu: Mahkemenizce tarafıma tevdi edilen dosyada istenen inceleme hakkında rapordur.

Bilirkişi: {f.name()}, Bilirkişilik Bölge Kurulu sicil no {f.r.randint(1000, 9999)}, uzmanlık alanı {f.pick("muhasebe|inşaat|trafik|tıp|bilişim")}.

Taraf iddiaları kısaca: Davacı, {f.pick("davalıya teslim ettiği malların bedelini alamadığını", "kiraladığı dairede ayıplar bulunduğunu", "iş kazası sonucu malul kaldığını")} ileri sürmektedir. Davalı bu iddiaları reddetmektedir.

Teknik inceleme ve değerlendirme: Dosyadaki faturalar, sevk irsaliyeleri ve cari hesap ekstreleri karşılaştırılmıştır. {f.pick(["Davalı defterlerinde " + f.money() + " borç kaydı mevcuttur.", "Maluliyet oranı %" + str(f.r.randint(5, 60)) + " olarak bildirilmiştir.", "Ayıpların giderim maliyeti " + f.money() + " olarak hesaplanmıştır."])}

Kanaat: Yukarıdaki açıklamalar çerçevesinde davacı iddiasının {f.pick("doğrulandığı|kısmen doğrulandığı|doğrulanamadığı")} yönünde görüş bildiririm. Nihai takdir Mahkemenize aittir.

Bilirkişi ücret ve masraf listesi ektedir. {f.date()}"""


# ---------------------------------------------------------------- icra_takip_talebi
@fam("icra_takip_talebi")
def icra_0(f):
    return f"""{f.icra_office()}'NE

TAKİP TALEBİ ({f.pick("İlamsız Takip - Örnek 1|Kambiyo Senetlerine Dayalı Takip - Örnek 10|İlamlı Takip - Örnek 4-5")})

ALACAKLI           : {f.company()}, VKN {f.vkn()}
ALACAKLI VEKİLİ    : {f.lawyer()}
BORÇLU             : {f.name()}, TCKN {f.tckn()}
BORÇLUNUN ADRESİ   : {f.address()}
ALACAK TUTARI      : {f.money()} asıl alacak, {f.money()} işlemiş faiz
FAİZ               : Takip tarihinden itibaren {f.pick("yasal|ticari avans|%" + str(f.r.randint(9, 60)))} faiz
ALACAĞIN SEBEBİ    : {f.pick(["Cari hesap alacağı ve faturalar", f.date() + " vadeli bono", f.esas() + " Esas sayılı ilam", "Kira sözleşmesinden doğan kira alacağı"])}
TAKİP YOLU         : {f.pick("Genel haciz yolu|Kambiyo senetlerine mahsus haciz yolu|Kiralanan taşınmazların ilamsız tahliyesi")}

Yukarıda belirtilen alacağın borçludan tahsili için ödeme emri gönderilmesini talep ederim.
{f.date()}
Alacaklı Vekili {f.lawyer()}"""


@fam("icra_takip_talebi")
def icra_1(f):
    return f"""İCRA MÜDÜRLÜĞÜNE
{f.icra_office()}

Takip talebinde bulunan alacaklı: {f.name()}
Vekili: {f.lawyer()} ({f.city()} Barosu)
Borçlu(lar): 1) {f.name()} 2) {f.company()}

Talep: İİK md. 58 uyarınca aşağıda gösterilen alacağımızın tahsili için borçlular hakkında icra takibi başlatılmasını,
- Asıl alacak: {f.money()}
- Takip öncesi faiz: {f.money()}
- Masraflar ve vekâlet ücreti
- Alacağa takip tarihinden itibaren işleyecek faiz
Alacağın dayanağı: {f.pick(["ödenmeyen çek", "ihtarname ve sözleşme", "kredi kartı borcu", "nafaka ilamı"])}
Banka hesabı (tahsilat için): {f.iban()}
Saygılarımla. {f.date()}"""


@fam("icra_takip_talebi")
def icra_2(f):
    return f"""T.C. İCRA DAİRESİ - TAKİP TALEPNAMESİ (UYAP)

Takip türü: {f.pick("İlamsız takiplerde ödeme emri", "Kambiyo senetlerine dayalı haciz yoluyla takip", "Rehnin paraya çevrilmesi yoluyla takip")}
Alacaklı: {f.company()}  Vekil: {f.lawyer()}
Borçlu: {f.name()}  Adres: {f.address()}
Alacak kalemleri:
  Asıl Alacak ........ {f.money()}
  İşlemiş Faiz ....... {f.money()}
  Protesto Gideri .... {f.money()}
  Toplam ............. {f.money()}
Senet/Belge: {f.pick(["Bono", "Çek", "Fatura", "Sözleşme"])} no {f.r.randint(1000, 999999)}, tanzim {f.date()}, vade {f.date()}
Talep: Borçluya ödeme emri tebliğ edilerek cebri icra yoluyla tahsil edilmesi talep olunur.
Talep tarihi: {f.date()}"""


# ---------------------------------------------------------------- odeme_emri
@fam("odeme_emri")
def odeme_0(f):
    return f"""T.C.
{f.icra_office()}
DOSYA NO: {f.esas()} Esas

ÖDEME EMRİ
({f.pick("Genel haciz yoluyla takipte - Örnek No: 7|Kambiyo senetlerine dayalı takipte - Örnek No: 10|Kiralanan taşınmazların tahliyesi - Örnek No: 13")})

ALACAKLI : {f.company()}
VEKİLİ   : {f.lawyer()}
BORÇLU   : {f.name()} - {f.address()}

TAKİP KONUSU ALACAK: {f.money()} asıl alacak ile işlemiş {f.money()} faiz.
ALACAĞIN NEDENİ: {f.pick(["Fatura alacağı", "Bono", "Çek", "Kira alacağı"])}

Borçlu yukarıda yazılı borç ile takip giderlerini bu ödeme emrinin tebliği tarihinden itibaren {f.pick("7 (yedi)|10 (on)|5 (beş)")} gün içinde ödemesi; borçlu olmadığınız veya alacaklının takibat icrasına hakkı bulunmadığı hakkında bir itirazınız varsa bunu aynı süre içinde icra dairesine bildirmeniz gerekir. İtiraz etmezseniz bu süre içinde 74. maddeye göre mal beyanında bulunmanız, bulunmazsanız hapisle tazyik olunacağınız, gerçeğe aykırı beyanda bulunursanız hapis cezası ile cezalandırılacağınız, borcu ödemez veya itiraz etmezseniz cebri icraya devam olunacağı ihtar olunur.

{f.date()}
İcra Müdürü {f.name()}  (Mühür)"""


@fam("odeme_emri")
def odeme_1(f):
    return f"""ÖDEME EMRİ - {f.icra_office()}
Esas: {f.esas()}

Sayın Borçlu {f.name()},
{f.address()}

Alacaklı {f.company()} tarafından aleyhinize başlatılan ilamsız icra takibine ilişkin olarak aşağıdaki hususlar tebliğ olunur:
Asıl Alacak: {f.money()}   Faiz: {f.money()}   İcra masrafları: {f.money()}
Dayanak belge: {f.pick(["cari hesap ekstresi", "kira sözleşmesi", "kredi sözleşmesi"])}

1. Borcu ve masrafları tebliğden itibaren 7 gün içinde ödemeniz gerekir.
2. Borca veya imzaya itirazınız varsa 7 gün içinde sebepleriyle birlikte icra dairesine bildirmelisiniz.
3. Süresinde itiraz edilmeyen takip kesinleşir; alacaklı haciz isteyebilir.
4. Mal beyanında bulunmak zorundasınız (İİK md. 74).
Tahsilat için icra dairesinin {f.bank()} Bankası hesabı: {f.iban()}

{f.date()}  İcra Müdür Yardımcısı"""


@fam("odeme_emri")
def odeme_2(f):
    return f"""T.C. ADALET BAKANLIĞI UYAP BİLİŞİM SİSTEMİ
{f.icra_office()} / {f.esas()}
Evrak: Ödeme Emri (Örnek {f.pick("7|10|49|51")})
Borçlu: {f.name()}, TC {f.tckn()}
Alacaklı: {f.name()} vekili {f.lawyer()}

İşbu ödeme emri ile, alacaklının {f.money()} tutarındaki alacağı ve ferileri için hakkınızda takip yapıldığı bildirilir. Tebliğ tarihinden itibaren yasal süre içinde borcu ödemeniz veya itiraz etmeniz; borca itirazınızı ve imzaya itirazınızı ayrı ayrı açıkça belirtmeniz gerekir. Kambiyo senetlerine dayalı takiplerde itirazlar icra mahkemesine yapılır.
Aksi halde cebri icraya devam edilecektir.
Bu belge 5070 sayılı Elektronik İmza Kanunu gereğince güvenli elektronik imza ile imzalanmıştır. Doğrulama kodu: {f.r.randint(10**9, 10**10)}"""


# ---------------------------------------------------------------- ihtarname
@fam("ihtarname")
def ihtar_0(f):
    return f"""{upper_tr(f.city())} {f.r.randint(1, 60)}. NOTERLİĞİ'NE

İHTARNAME

KEŞİDECİ        : {f.company()}
VEKİLİ          : {f.lawyer()}
MUHATAP         : {f.name()}
ADRESİ          : {f.address()}
KONU            : {f.pick(["Ödenmeyen kira bedellerinin ödenmesi ihtarıdır.", "Sözleşmeye aykırılığın giderilmesi ihtarıdır.", "Fatura bedelinin ödenmesi ihtarıdır.", "Haksız fiilin durdurulması ihtarıdır."])}

AÇIKLAMALAR :
{para(f, [
        f"Muhatap ile müvekkil arasında {f.date()} tarihli sözleşme akdedilmiştir.",
        f"Muhatabın {f.money()} tutarındaki borcu vadesi geldiği halde ödenmemiştir.",
        "Muhatap sözleşmede üstlendiği yükümlülükleri yerine getirmemektedir.",
        f"Borcunuzun işbu ihtarnamenin tebliğinden itibaren {f.pick('7|15|30')} gün içinde {f.iban()} numaralı hesaba ödenmesini,",
        "Aksi halde aleyhinize yasal yollara başvurulacağını, doğacak tüm masraf, faiz ve vekâlet ücretinin tarafınıza yükleneceğini,",
        "TBK md. 315 uyarınca süre içinde ödeme yapılmaması halinde sözleşmenin feshedileceğini,",
    ], (3, 5))}
ihtar ederiz.

Sayın Noter, iki nüsha olarak düzenlenen işbu ihtarnamenin bir nüshasının muhataba tebliğini, tebliğ şerhli bir nüshasının tarafımıza verilmesini rica ederiz. {f.date()}

Keşideci Vekili {f.lawyer()}"""


@fam("ihtarname")
def ihtar_1(f):
    return f"""İHTARNAME
(Noter Kanalıyla{f.pick(["", " / KEP ile"])})

İhtar Eden: {f.name()}, {f.address()}
Vekili: {f.lawyer()}
Muhatap: {f.company()}, {f.address()}

Konu: {f.pick(["İş sözleşmesinin haklı nedenle feshi", "Ayıplı malın iadesi ve bedelin ödenmesi", "Kira sözleşmesinin yenilenmeyeceğinin bildirimi", "Temerrüt ihtarı"])}

Sayın Muhatap,
{f.pick(["Müvekkilin ücretleri son " + str(f.r.randint(2, 6)) + " aydır ödenmemektedir.", "Tarafınızdan satın alınan ürün kısa sürede arızalanmıştır.", "Kiralananı kira süresi sonunda boşaltmanız gerekmektedir."])}
İşbu ihtarnamenin tebliğinden itibaren {f.pick("3|7|10|30")} gün içinde gereğini yapmanızı, aksi takdirde {f.pick(["yasal yollara başvurulacağını", "sözleşmenin feshedilmiş sayılacağını", "icra takibi başlatılacağını"])} ihtar ederiz.

İhtar eden vekili
{f.lawyer()}
{f.date()}"""


@fam("ihtarname")
def ihtar_2(f):
    return f"""{f.city()}, {f.date()}

Sayın {f.name()},

KONU: İHTAR

Müvekkil {f.company()} adına tarafınıza aşağıdaki hususları ihtaren bildiririz:
1. Tarafınız ile müvekkil arasında imzalanan {f.pick("bayilik|distribütörlük|gizlilik|tedarik")} sözleşmesinin {f.r.randint(3, 20)}. maddesine aykırı hareket ettiğiniz tespit edilmiştir.
2. Söz konusu aykırılığın derhal giderilmesini, aksi halde sözleşmede öngörülen {f.money()} cezai şartın tarafınızdan talep edileceğini,
3. Müvekkilin her türlü dava ve takip hakkının saklı olduğunu
bildirir, işbu ihtarnamenin TTK md. 18/3 uyarınca {f.pick("noter|KEP|iadeli taahhütlü posta")} vasıtasıyla tebliğini rica ederiz.

Saygılarımızla,
{f.lawyer()}
{f.pick("Hukuk Bürosu|Avukatlık Ortaklığı")}"""


# ---------------------------------------------------------------- tebligat
@fam("tebligat")
def tebligat_0(f):
    return f"""TEBLİĞ MAZBATASI
PTT - {f.pick("APS", "İadeli Taahhütlü")} Barkod No: RR{f.r.randint(10**8, 10**9)}TR

Gönderen Merci : {f.court()}
Dosya No       : {f.esas()}
Muhatap        : {f.name()}
Adres          : {f.address()}
Tebliğ Edilen Evrak: {f.pick(["Dava dilekçesi ve duruşma günü", "Gerekçeli karar", "Bilirkişi raporu", "Ödeme emri", "Davetiye"])}

TEBLİĞ ŞERHİ:
{f.pick([
        "Muhatap adreste bulunmadığından, beyanına müracaat edilen komşusu " + f.name() + " tarafından muhatabın geçici olarak adreste olmadığı, 3 gün içinde döneceği bildirilmekle, Tebligat Kanunu md. 21/1 gereğince tebliğ evrakı muhtara teslim edilmiş, 2 numaralı ihbarname kapıya yapıştırılmıştır.",
        "Evrak muhatabın kendisine imzası alınmak suretiyle tebliğ edilmiştir.",
        "Muhatabın adresi kapalı olup adreste kimse bulunamamıştır; Tebligat Kanunu md. 35 gereğince tebliğ evrakı muhtara bırakılmıştır.",
        "Evrak muhatapla aynı konutta oturan reşit eşi " + f.name() + "'e imzası alınarak teslim edilmiştir.",
    ])}
Tebliğ Tarihi  : {f.date()}
Dağıtıcı       : {f.name()} (Sicil {f.r.randint(10000, 99999)})"""


@fam("tebligat")
def tebligat_1(f):
    return f"""ELEKTRONİK TEBLİGAT BİLDİRİMİ
Ulusal Elektronik Tebligat Sistemi (UETS)

Muhatap: {f.pick([f.lawyer(), f.company(), f.name()])}
UETS Adresi: {f.r.randint(10000, 99999)}-{f.r.randint(10000, 99999)}-{f.r.randint(10000, 99999)}
Gönderici Kurum: {f.pick([f.court(), f.icra_office(), upper_tr(f.city()) + " VERGİ DAİRESİ BAŞKANLIĞI", "SOSYAL GÜVENLİK KURUMU"])}
Evrak Türü: {f.pick(["Duruşma Davetiyesi", "Ara Karar", "Muhtıra", "Ödeme Emri", "Vergi İnceleme Raporu"])}
Dosya: {f.esas()}
Gönderim Tarihi: {f.date()}
Elektronik tebligat, muhatabın elektronik adresine ulaştığı tarihi izleyen beşinci günün sonunda yapılmış sayılır (7201 sayılı Tebligat Kanunu md. 7/a).
Tebliğ Edilmiş Sayılma Tarihi: {f.date()}
Bu belge elektronik ortamda oluşturulmuştur."""


@fam("tebligat")
def tebligat_2(f):
    return f"""DAVETİYE
{f.court()}

Dosya: {f.esas()} Esas
Davetiye çıkarılan: {f.pick("Tanık|Davalı|Davacı|Bilirkişi")} {f.name()}
Adresi: {f.address()}

Yukarıda numarası yazılı dosyanın {f.date()} günü saat {f.r.randint(9, 16)}:{f.pick("00|30")}'daki duruşmasında {f.pick("tanık olarak dinlenmek üzere", "isticvap edilmek üzere", "hazır bulunmanız")} mahkememize gelmeniz, gelmediğiniz takdirde zorla getirileceğiniz ve gecikmeden doğan masrafların tarafınıza yükleneceği ihtarlı davetiye yerine geçmek üzere tebliğ olunur.
Bu davetiye Tebligat Kanunu hükümlerine göre tebliğ edilmiştir.
Tebliğ alan imza: ........  Tebliğ tarihi: {f.date()}
Yazı İşleri Müdürü {f.name()}"""


# ---------------------------------------------------------------- vekaletname
@fam("vekaletname")
def vekalet_0(f):
    return f"""VEKALETNAME

Vekil Eden : {f.name()} (T.C. Kimlik No: {f.tckn()})
Adresi     : {f.address()}
Vekiller   : {f.lawyer()} ve {f.lawyer()} ({f.city()} Barosu)

Yukarıda adı geçen avukatları; lehimde ve aleyhimde açılmış ve açılacak her türlü dava ve takiplerden dolayı, mahkemeler, icra daireleri, Cumhuriyet savcılıkları, vergi daireleri ve sair resmi ve özel kurumlar nezdinde beni temsile, davaya, takibe, feragate, kabule, sulhe, ibraya, hakem ve bilirkişi tayinine, reddine, haczedilen malları paraya çevirmeye, tahsile, ahzu kabza, temyize ve tashihi karara, yetkili olmak üzere vekil tayin ettim.
Vekiller birlikte veya ayrı ayrı hareket etmeye ve başkasını tevkile yetkilidir.

{f.date()}
Vekil Eden {f.name()}

{f.city()} {f.r.randint(1, 60)}. Noterliği - Yevmiye No: {f.r.randint(1000, 99999)}
Bu vekaletname huzurumda okunup imzalanmıştır. Noter {f.name()}"""


@fam("vekaletname")
def vekalet_1(f):
    return f"""ÖZEL VEKALETNAME

Ben {f.name()}, {f.address()} adresinde mukim, {f.tckn()} T.C. kimlik numaralı;
{f.pick(["adıma kayıtlı " + f.city() + " ili " + f.pick(['Merkez', 'Kuzey', 'Sahil']) + " mahallesi " + str(f.r.randint(10, 999)) + " ada " + str(f.r.randint(1, 50)) + " parsel sayılı taşınmazı dilediği bedel ve şartlarla satmaya, tapuda ferağ vermeye,", f.plate() + " plakalı aracımı satmaya, devir işlemlerini yapmaya, noterde satış sözleşmesi imzalamaya,", "adıma banka hesabı açmaya, kapatmaya, para yatırıp çekmeye,", "nüfus müdürlüğünde işlem yapmaya, belge almaya,"])}
bu işlemler için gerekli her türlü belgeyi imzalamaya ve resmi kurumlarda beni temsile yetkili olmak üzere {f.name()}'i vekil tayin ettim.

İşbu vekaletname {f.pick("bir yıl süreyle geçerlidir.", "azledilinceye kadar geçerlidir.")}
Tarih: {f.date()}  İmza: ........

T.C. {upper_tr(f.city())} {f.r.randint(1, 50)}. NOTERLİĞİ
Yevmiye: {f.r.randint(1000, 99999)}  Tarih: {f.date()}"""


@fam("vekaletname")
def vekalet_2(f):
    return f"""{f.city()} Barosu avukatlarından {f.lawyer()}'i, şirketimiz {f.company()}'nin her türlü hukuki işlemlerinde temsil etmek üzere genel dava vekili olarak tayin ettik.
Vekilimiz; Türkiye Cumhuriyeti mahkemeleri, icra ve iflas daireleri, arabuluculuk büroları, idari makamlar ve hakem heyetleri önünde dava açmaya, cevap vermeye, davayı ıslah etmeye, sulh olmaya, feragat ve kabule, ihtiyati tedbir ve haciz istemeye, haciz yaptırmaya, ahzu kabza ve ibraya yetkilidir.
Şirket ana sözleşmesi ve imza sirküleri uyarınca şirketi temsile yetkili {f.name()} ve {f.name()} müştereken imza atmıştır.
Bu vekaletname noterlikçe re'sen düzenlenmiştir.
Vekâlet veren: {f.company()}, Ticaret Sicil No {f.r.randint(10000, 999999)}
Tarih: {f.date()}
{f.city()} {f.r.randint(1, 50)}. Noteri {f.name()} - mühür / imza"""


# ---------------------------------------------------------------- kira_sozlesmesi
@fam("kira_sozlesmesi")
def kira_0(f):
    return f"""KİRA SÖZLEŞMESİ

Mahallesi      : {f.pick(["Merkez", "Cumhuriyet", "Bahçelievler", "Yenimahalle"])}
Sokağı         : {f.pick(["Lale", "Çınar", "Gül"])} Sokak
Kiralananın Cinsi : {f.pick("Mesken|İşyeri|Daire|Dükkan|Depo")}
Kiraya Veren   : {f.name()}
T.C. No        : {f.tckn()}
Kiracı         : {f.name()}
Kiracının Adresi: {f.address()}
Bir Aylık Kira Bedeli: {f.money()}
Bir Senelik Kira Bedeli: {f.money()}
Kira Bedelinin Ne Şekilde Ödeneceği: Her ayın ilk {f.r.randint(1, 10)} günü {f.iban()} numaralı hesaba
Kiranın Başlangıç Tarihi: {f.date()}
Kira Müddeti   : {f.pick("1 (bir) yıl|2 (iki) yıl|3 (üç) yıl")}
Kiralananın Şimdiki Durumu: Boyalı, temiz ve kullanılabilir
Kiralananla Birlikte Teslim Edilen Demirbaşlar: {f.pick(["Kombi, mutfak dolapları", "Klima", "Yok"])}

GENEL ŞARTLAR
1- Kiracı kiralananı özenle kullanmak ve komşulara saygı göstermek zorundadır.
2- Kiracı, kiraya verenin yazılı izni olmadan kiralananı başkasına kiralayamaz, alt kiraya veremez.
3- Kira bedeli her yıl bir önceki kira yılının TÜFE on iki aylık ortalaması oranında artırılır.
4- Depozito olarak {f.money()} alınmıştır; tahliyede iade edilecektir.
5- Kiracı kiralananı aldığı şekilde teslim edecektir.

Kiraya Veren {f.name()}    Kiracı {f.name()}    Kefil {f.name()}"""


@fam("kira_sozlesmesi")
def kira_1(f):
    return f"""İŞYERİ KİRA SÖZLEŞMESİ

Madde 1 - Taraflar
Bu sözleşme bir tarafta {f.company()} (bundan böyle "Kiraya Veren") ile diğer tarafta {f.company()} (bundan böyle "Kiracı") arasında {f.date()} tarihinde imzalanmıştır.
Madde 2 - Kiralanan
{f.address()} adresindeki {f.r.randint(80, 2000)} m² {f.pick("ofis|mağaza|depo|fabrika binası")}.
Madde 3 - Kira Süresi
Kira süresi {f.date()} tarihinden başlamak üzere {f.r.randint(1, 10)} yıldır.
Madde 4 - Kira Bedeli ve Ödeme
Aylık kira bedeli {f.money()} + KDV olup her ay peşin ödenir. Stopaj kiracıya aittir.
Madde 5 - Kira Artışı
Her kira yılı başında kira bedeli {f.pick("TÜFE oranında", "%" + str(f.r.randint(10, 60)) + " oranında", "taraflarca belirlenecek oranda")} artırılır.
Madde 6 - Tadilat
Kiracı, kiraya verenin yazılı onayı olmadan kiralananda esaslı değişiklik yapamaz.
Madde 7 - Tahliye ve Fesih
Kiracı süre sonunda kiralananı boşaltmazsa her gün için {f.money()} ceza öder. TBK md. 347 hükümleri saklıdır.
Madde 8 - Uyuşmazlık
Bu sözleşmeden doğacak uyuşmazlıklarda {f.city()} mahkemeleri ve icra daireleri yetkilidir.

KİRAYA VEREN                         KİRACI"""


@fam("kira_sozlesmesi")
def kira_2(f):
    return f"""Konut Kiralama Mukavelesi

{f.address()} adresindeki konutun sahibi {f.name()} ("ev sahibi") ile {f.name()} ("kiracı") aşağıdaki şartlarda anlaşmıştır:

- Ev, {f.date()} tarihinde kiracıya anahtarıyla birlikte teslim edilmiştir.
- Kiracı aylık {f.money()} kirayı her ayın {f.r.randint(1, 10)}'una kadar ev sahibinin {f.bank()} Bankası hesabına yatıracaktır.
- Aidat, elektrik, su, doğalgaz ve internet giderleri kiracıya aittir.
- Kiracı evde evcil hayvan beslemeyecektir. {opt(f, .5, "Sigara içilmeyecektir.")}
- Kiracı evden çıkmak isterse en az {f.pick("15|30|60")} gün önce yazılı olarak haber verecektir.
- İki ay üst üste kira ödenmezse ev sahibi sözleşmeyi feshedebilir.
- Güvence bedeli olarak {f.r.randint(1, 3)} aylık kira tutarı alınmıştır.

Bu kira kontratı iki nüsha olarak düzenlenmiş ve imzalanmıştır.
Ev sahibi: {f.name()}   Kiracı: {f.name()}   Tarih: {f.date()}"""


# ---------------------------------------------------------------- is_sozlesmesi
@fam("is_sozlesmesi")
def is_0(f):
    return f"""{f.pick("BELİRSİZ SÜRELİ|BELİRLİ SÜRELİ|KISMİ SÜRELİ")} İŞ SÖZLEŞMESİ

MADDE 1 - TARAFLAR
İşveren: {f.company()}, {f.address()}, SGK İşyeri Sicil No: {f.r.randint(10**12, 10**13)}
İşçi: {f.name()}, T.C. Kimlik No: {f.tckn()}, Adres: {f.address()}

MADDE 2 - İŞİN TANIMI VE YERİ
İşçi, işverenin {f.city()} işyerinde {f.pick("muhasebe uzmanı|satış temsilcisi|yazılım geliştirici|depo sorumlusu|şoför|hemşire")} olarak çalışacaktır.

MADDE 3 - ÇALIŞMA SÜRESİ
Haftalık çalışma süresi 45 saattir. Fazla çalışma 4857 sayılı İş Kanunu md. 41 hükümlerine göre ücretlendirilir.

MADDE 4 - ÜCRET
İşçiye aylık brüt {f.money()} ücret ödenir. Ücret her ayın son iş günü işçinin banka hesabına yatırılır.

MADDE 5 - DENEME SÜRESİ
Deneme süresi {f.pick("iki|bir")} aydır. Bu süre içinde taraflar bildirim süresine gerek olmaksızın ve tazminatsız sözleşmeyi feshedebilir.

MADDE 6 - YILLIK İZİN
İşçinin yıllık ücretli izin hakkı İş Kanunu md. 53 vd. hükümlerine tabidir.

MADDE 7 - GİZLİLİK VE REKABET YASAĞI
İşçi, iş ilişkisi süresince ve sona ermesinden itibaren {f.r.randint(1, 2)} yıl boyunca işverenin ticari sırlarını ifşa etmeyecektir.

MADDE 8 - FESİH
Sözleşmenin feshinde İş Kanunu md. 17 vd. hükümleri uygulanır.

İŞVEREN                             İŞÇİ
{f.date()}"""


@fam("is_sozlesmesi")
def is_1(f):
    return f"""HİZMET AKDİ (İŞ SÖZLEŞMESİ)

{f.company()} ("Şirket") ile {f.name()} ("Çalışan") arasında, Çalışanın {f.date()} tarihinden itibaren Şirket bünyesinde {f.pick("proje yöneticisi|grafik tasarımcı|insan kaynakları uzmanı|kasiyer")} unvanıyla istihdamına ilişkin olarak aşağıdaki şartlarda anlaşılmıştır.

1. Ücret ve yan haklar: Net aylık {f.money()}; yemek kartı, özel sağlık sigortası, yılda {f.r.randint(2, 4)} ikramiye.
2. Çalışma saatleri: Hafta içi 09.00-18.00, öğle arası bir saat. {opt(f, .5, "Haftada iki gün uzaktan çalışma imkânı tanınır.")}
3. Görev yeri değişikliği: Şirket, Çalışanı başka bir şehirdeki işyerine Çalışanın yazılı onayı ile nakledebilir.
4. Kişisel veriler: Çalışana ait kişisel veriler 6698 sayılı Kanun kapsamında işlenir; aydınlatma metni ayrıca tebliğ edilmiştir.
5. Fazla mesai: Çalışan yıllık 270 saate kadar fazla çalışmaya onay verir.
6. Sona erme: İhbar süreleri kıdeme göre 2 ila 8 haftadır.

Çalışan bu sözleşmenin bir nüshasını teslim aldığını kabul eder.
Şirket adına: {f.name()}    Çalışan: {f.name()}    {f.date()}"""


@fam("is_sozlesmesi")
def is_2(f):
    return f"""BELİRLİ SÜRELİ ÇALIŞMA SÖZLEŞMESİ
(Proje bazlı)

İşveren unvanı ................. {f.company()}
İşçinin adı soyadı ............. {f.name()}
Doğum tarihi ................... {f.date(1960, 2004)}
Görevi ......................... {f.pick("Saha mühendisi|Kalıp ustası|Formen|Teknisyen")}
Sözleşme başlangıcı ............ {f.date()}
Sözleşme bitişi ................ {f.date()}
Brüt ücret ..................... {f.money()} / ay
Çalışma yeri ................... {f.city()} {f.pick("şantiyesi|fabrikası|bölge müdürlüğü")}

Bu sözleşme belirli bir işin tamamlanması amacıyla İş Kanunu md. 11 uyarınca yapılmıştır. Süre bitiminde kendiliğinden sona erer; zincirleme yapılması esaslı neden olmadıkça mümkün değildir.
İşçi, iş sağlığı ve güvenliği eğitimlerine katılmak ve kişisel koruyucu donanım kullanmak zorundadır (6331 sayılı Kanun).
SGK girişi işe başlamadan önce yapılmıştır.

İşveren vekili              İşçi
{f.name()}                 {f.name()}"""


# ---------------------------------------------------------------- sozlesme (diğer)
@fam("sozlesme")
def soz_0(f):
    kind = f.pick(["HİZMET SÖZLEŞMESİ", "SATIŞ SÖZLEŞMESİ", "DANIŞMANLIK SÖZLEŞMESİ", "YAZILIM LİSANS SÖZLEŞMESİ", "TEDARİK SÖZLEŞMESİ"])
    return f"""{kind}

1. TARAFLAR
1.1. {f.company()} ("{f.pick("Hizmet Alan|Alıcı|Müşteri")}"), {f.address()}
1.2. {f.company()} ("{f.pick("Hizmet Veren|Satıcı|Yüklenici")}"), {f.address()}

2. KONU
İşbu sözleşmenin konusu, {f.pick(["Yüklenicinin Müşteriye bulut tabanlı muhasebe yazılımı sağlaması", "Satıcının Alıcıya ekte listelenen ürünleri teslim etmesi", "danışmanlık hizmetlerinin sunulması"])} ve tarafların hak ve yükümlülüklerinin belirlenmesidir.

3. BEDEL VE ÖDEME
Sözleşme bedeli KDV hariç {f.money()} olup fatura tarihinden itibaren {f.pick("30|45|60")} gün içinde ödenecektir. Geç ödemelerde aylık %{f.r.randint(1, 5)} gecikme faizi uygulanır.

4. SÜRE
Sözleşme imza tarihinden itibaren {f.r.randint(1, 5)} yıl süreyle yürürlükte kalır ve taraflardan biri fesih bildiriminde bulunmadıkça birer yıl uzar.

5. GİZLİLİK
Taraflar birbirlerine ait ticari sırları ve kişisel verileri gizli tutmayı taahhüt eder.

6. MÜCBİR SEBEP
Tarafların kontrolü dışındaki olaylar mücbir sebep sayılır.

7. UYUŞMAZLIKLARIN ÇÖZÜMÜ
Bu sözleşmeden doğan uyuşmazlıklarda {f.city()} {f.pick("mahkemeleri ve icra daireleri yetkilidir.|Ticaret Odası Tahkim kuralları uygulanır.")}

{f.date()}
{f.pick("Hizmet Alan|Alıcı|Müşteri")}                     {f.pick("Hizmet Veren|Satıcı|Yüklenici")}"""


@fam("sozlesme")
def soz_1(f):
    return f"""GİZLİLİK SÖZLEŞMESİ (NDA)

Taraflar: {f.company()} ve {f.company()} (birlikte "Taraflar")
Amaç: Taraflar, {f.pick("olası bir şirket birleşmesi|ortak bir yatırım projesi|hisse devri görüşmeleri")} kapsamında birbirlerine gizli bilgi açıklayacaklardır.

Madde 1. Gizli Bilgi; finansal tablolar, müşteri listeleri, ticari sırlar, know-how ve her türlü kişisel veriyi kapsar.
Madde 2. Alan Taraf, gizli bilgiyi yalnızca Amaç için kullanacak, üçüncü kişilere açıklamayacaktır.
Madde 3. Gizlilik yükümlülüğü sözleşmenin sona ermesinden sonra {f.r.randint(2, 5)} yıl devam eder.
Madde 4. Aykırılık halinde ihlal eden taraf {f.money()} cezai şart ödemeyi kabul eder; aşan zarar talebi saklıdır.
Madde 5. Bu sözleşme Türk hukukuna tabidir; {f.city()} mahkemeleri yetkilidir.

İmza: {f.name()} / {f.name()}   Tarih: {f.date()}"""


@fam("sozlesme")
def soz_2(f):
    return f"""PAY DEVİR SÖZLEŞMESİ

Devreden: {f.name()} (T.C. {f.tckn()})
Devralan: {f.company()}
Şirket: {f.company()} (Ticaret Sicil No {f.r.randint(10000, 999999)}, MERSİS {f.r.randint(10**15, 10**16)})

Devreden, Şirketin sermayesinin %{f.r.randint(5, 100)}'ini temsil eden {f.r.randint(100, 100000)} adet payını, tüm hak ve borçlarıyla birlikte {f.money()} bedel karşılığında Devralana devretmiştir.
Bedel, imza tarihinde {f.iban()} numaralı hesaba ödenmiştir.
Devreden; paylar üzerinde rehin, haciz veya başkaca bir takyidat bulunmadığını, şirketin vergi ve SGK borcu olmadığını beyan ve taahhüt eder.
Devir, TTK md. {f.pick("595|490")} uyarınca genel kurul onayına tabidir. Pay defterine kayıt Devralan adına yapılacaktır.
Beyan ve taahhütlerin gerçeğe aykırı çıkması halinde Devreden doğan tüm zararı tazmin eder.

{f.city()}, {f.date()}
Devreden            Devralan"""


# ---------------------------------------------------------------- sirket_karari
@fam("sirket_karari")
def sirket_0(f):
    return f"""{upper_tr(f.company())}
YÖNETİM KURULU KARARI

Karar Tarihi : {f.date()}
Karar No     : {f.year()}/{f.r.randint(1, 60)}
Toplantıya Katılanlar: {f.name()} (Başkan), {f.name()} (Başkan Yardımcısı), {f.name()} (Üye)

Şirket Yönetim Kurulu, şirket merkezinde toplanarak aşağıdaki hususları görüşmüş ve karara bağlamıştır:
GÜNDEM:
{para(f, [
        f"1. Şirketin {f.bank()} Bankası nezdinde {f.money()} tutarında kredi kullanmasına,",
        f"2. Şirket adına {f.city()} şubesi açılmasına,",
        f"3. Şirketi temsil ve ilzama {f.name()}'in münferiden yetkili kılınmasına,",
        "4. Olağan genel kurul toplantısının yapılmasına ve gündemin belirlenmesine,",
        f"5. {f.address()} adresindeki taşınmazın satın alınmasına,",
        "6. Şirketin sermayesinin artırılmasına ilişkin esas sözleşme tadil tasarısının onaylanmasına,",
    ], (2, 4))}
TTK md. 390 uyarınca toplantı ve karar nisabı mevcut olup kararlar oy birliği ile alınmıştır.

Başkan          Başkan Yrd.          Üye"""


@fam("sirket_karari")
def sirket_1(f):
    return f"""{f.company()}
{f.year()} YILINA AİT OLAĞAN{f.pick(['', 'ÜSTÜ'])} GENEL KURUL TOPLANTI TUTANAĞI

Şirketin genel kurul toplantısı {f.date()} tarihinde saat {f.r.randint(9, 16)}:00'da şirket merkezinde, {f.city()} Ticaret İl Müdürlüğü'nün görevlendirdiği Bakanlık temsilcisi {f.name()} gözetiminde yapılmıştır.
Hazır bulunanlar listesinin tetkikinden, şirketin {f.money()} toplam sermayesine tekabül eden payların tamamının asaleten temsil edildiği anlaşılmıştır.
1. Toplantı başkanlığına {f.name()} seçildi; tutanak yazmanlığına {f.name()} getirildi.
2. Yönetim kurulu faaliyet raporu ve bağımsız denetim raporu okunarak müzakere edildi.
3. Bilanço ve kâr-zarar hesapları ayrı ayrı okundu, oy birliği ile tasdik edildi.
4. Yönetim kurulu üyeleri ayrı ayrı ibra edildi.
5. Dağıtılabilir dönem kârının {f.pick("dağıtılmamasına|ortaklara dağıtılmasına")} karar verildi.
6. Yönetim kurulu üyelerine {f.money()} huzur hakkı ödenmesine karar verildi.
Gündemde görüşülecek başka konu olmadığından toplantıya son verildi.
Bakanlık Temsilcisi    Toplantı Başkanı    Oy Toplama Memuru"""


@fam("sirket_karari")
def sirket_2(f):
    return f"""MÜDÜRLER KURULU KARARI / ORTAKLAR KURULU KARARI
Şirket: {f.company()}
Toplantı yeri ve tarihi: Şirket merkezi, {f.date()}

Şirket ortakları {f.name()} (pay oranı %{f.r.randint(10, 90)}) ve {f.name()} toplanarak;
- Şirket müdürü {f.name()}'in istifasının kabulüne ve müdürlüğe {f.name()}'in {f.r.randint(1, 5)} yıl süre ile seçilmesine,
- Şirket merkezinin {f.address()} adresine nakline ve TTK hükümlerine uygun olarak tescil ve ilanına,
- {f.pick(["Ortak " + f.name() + "'in paylarını üçüncü kişiye devretmesine onay verilmesine,", "şirket sermayesinin " + f.money() + "'ye artırılmasına,", "şirketin tasfiyeye girmesine,"])}
oy birliği ile karar vermişlerdir.
Kararın Ticaret Sicil Müdürlüğüne tescili için müdür yetkilidir.
Ortak                      Ortak"""


# ---------------------------------------------------------------- fatura
@fam("fatura")
def fatura_0(f):
    q, p = f.r.randint(1, 50), f.r.randint(50, 50000)
    return f"""{f.pick("e-FATURA|e-Arşiv Fatura|FATURA")}

{f.company()}
{f.address()}
{f.pick(["Büyük Mükellefler", f.city() + " Kurumlar"])} V.D. - VKN: {f.vkn()}
Tel: {f.phone()}

SAYIN
{f.pick([f.company(), f.name()])}
{f.address()}
VKN/TCKN: {f.pick([f.vkn(), f.tckn()])}

Senaryo: {f.pick("TEMELFATURA|TİCARİFATURA|EARSIVFATURA")}   Fatura Tipi: SATIŞ
Fatura No: {f.pick(["ABC", "GIB", "EFT", "ARS"])}{f.year()}{f.r.randint(10**8, 10**9)}
Fatura Tarihi: {f.date()}
ETTN: {f.r.randint(10**7, 10**8):x}-{f.r.randint(1000, 9999)}-4{f.r.randint(100, 999)}-a{f.r.randint(100, 999)}-{f.r.randint(10**11, 10**12):x}

Sıra  Mal Hizmet               Miktar   Birim Fiyat   KDV Oranı   KDV Tutarı   Mal Hizmet Tutarı
1     {f.goods():24s} {q} Adet   {p},00 TL     %{f.pick("1|10|20")}       {f.money()}   {f.money()}

Mal Hizmet Toplam Tutarı: {f.money()}
Hesaplanan KDV: {f.money()}
Vergiler Dahil Toplam Tutar: {f.money()}
Ödenecek Tutar: {f.money()}
Yalnız: {f.pick(["Onbinikiyüz", "Yüzbin", "Üçbinbeşyüz"])} TL'dir.
Banka: {f.bank()} - IBAN {f.iban()}"""


@fam("fatura")
def fatura_1(f):
    return f"""SERBEST MESLEK MAKBUZU / {f.pick("e-SMM|SMM")}
Seri: {f.pick("A|B|SM")}  Sıra No: {f.r.randint(1, 99999)}
Düzenleyen: {f.lawyer()} - {f.city()} Barosu, {f.pick(["Kadıköy", "Çankaya", "Konak"])} V.D. {f.tckn()}
Müşteri: {f.pick([f.company(), f.name()])} - VKN {f.vkn()}
Tarih: {f.date()}
Açıklama: {f.pick(["Avukatlık hizmet bedeli", "Danışmanlık ücreti", "Dava takip ücreti", "Hukuki mütalaa bedeli"])} ({f.esas()} sayılı dosya)
Brüt Ücret ........ {f.money()}
Gelir Vergisi Stopajı (%20) ... {f.money()}
Net Ücret ......... {f.money()}
KDV (%20) ......... {f.money()}
Tahsil Edilen Toplam: {f.money()}
Bu makbuz 213 sayılı VUK uyarınca elektronik ortamda düzenlenmiştir."""


@fam("fatura")
def fatura_2(f):
    rows = "\n".join(f"{f.goods()} | {f.r.randint(1, 500)} {f.pick('kg|adet|m|saat')} | {f.money()} | {f.money()}" for _ in range(f.r.randint(2, 6)))
    return f"""{f.company()} - SATIŞ FATURASI
Fatura Seri-No: {f.pick("A|FTR|SAT")}-{f.r.randint(1000, 99999)}
Düzenleme Tarihi: {f.date()}   Sevk Tarihi: {f.date()}   İrsaliye No: {f.r.randint(1000, 99999)}
Alıcı: {f.company()}, Vergi No {f.vkn()}, {f.address()}

Ürün | Miktar | Birim Fiyat | Tutar
{rows}

Ara Toplam: {f.money()}
İskonto: {f.money()}
KDV %{f.pick("10|20")}: {f.money()}
GENEL TOPLAM: {f.money()}
Vade: {f.date()}  Ödeme şekli: {f.pick("Havale/EFT|Çek|Kredi kartı")}
Faturaya 8 gün içinde itiraz edilmediği takdirde içeriği kabul edilmiş sayılır (TTK md. 21/2)."""


# ---------------------------------------------------------------- aydinlatma_metni
@fam("aydinlatma_metni")
def aydin_0(f):
    return f"""{f.company()}
KİŞİSEL VERİLERİN İŞLENMESİNE İLİŞKİN AYDINLATMA METNİ

6698 sayılı Kişisel Verilerin Korunması Kanunu ("KVKK") md. 10 uyarınca, veri sorumlusu sıfatıyla {f.company()} olarak sizi aydınlatmak isteriz.

1. Veri Sorumlusu: {f.company()}, {f.address()}, MERSİS No: {f.r.randint(10**15, 10**16)}
2. İşlenen Kişisel Veriler: Kimlik (ad, soyad, T.C. kimlik no), iletişim (telefon, e-posta, adres), {f.pick(["müşteri işlem", "özlük", "finans", "sağlık", "görsel kayıt"])} verileri.
3. İşleme Amaçları: Sözleşmenin kurulması ve ifası, yasal yükümlülüklerin yerine getirilmesi, {f.pick(["müşteri ilişkileri yönetimi", "insan kaynakları süreçleri", "bina güvenliğinin sağlanması"])}.
4. Hukuki Sebepler: KVKK md. 5/2 (c) sözleşmenin ifası, (ç) hukuki yükümlülük, (f) meşru menfaat.
5. Aktarım: Kişisel verileriniz yetkili kamu kurum ve kuruluşlarına, iş ortaklarımıza ve hizmet sağlayıcılarımıza aktarılabilir.{opt(f, .5, " Yurt dışına aktarım KVKK md. 9 kapsamında yapılmaktadır.")}
6. Toplama Yöntemi: Fiziki ve elektronik ortamda, otomatik ve otomatik olmayan yollarla.
7. Haklarınız: KVKK md. 11 uyarınca kişisel verilerinizin işlenip işlenmediğini öğrenme, düzeltilmesini veya silinmesini isteme ve diğer haklarınızı {f.email()} adresine başvurarak kullanabilirsiniz."""


@fam("aydinlatma_metni")
def aydin_1(f):
    return f"""KVKK BİLGİLENDİRME METNİ
({f.pick("Çalışan Adayları|Ziyaretçiler|Müşteriler|Hasta ve Hasta Yakınları|Kamera ile İzleme")} İçin)

Değerli {f.pick("ziyaretçimiz|adayımız|müşterimiz|hastamız")},
{f.company()} olarak kişisel verilerinizin güvenliğine önem veriyoruz. Bu metin, Aydınlatma Yükümlülüğünün Yerine Getirilmesinde Uyulacak Usul ve Esaslar Hakkında Tebliğ'e uygun olarak hazırlanmıştır.

Hangi verilerinizi işliyoruz?
{f.pick(["Özgeçmişinizde yer alan eğitim ve iş deneyimi bilgileriniz, referanslarınız.", "Bina girişinde kamera kayıtlarınız ve ziyaretçi defterindeki bilgileriniz.", "Tetkik ve tedavi bilgileriniz, sağlık raporlarınız."])}
Neden işliyoruz?
{f.pick(["İşe alım süreçlerinin yürütülmesi için.", "Fiziksel mekân güvenliğinin sağlanması için.", "Tıbbi teşhis ve tedavi hizmetlerinin sunulması için."])}
Kimlerle paylaşıyoruz?
Yalnızca kanunen yetkili kurumlarla ve hizmet aldığımız tedarikçilerle.
Ne kadar süre saklıyoruz?
{f.pick(["2 yıl", "30 gün", "ilgili mevzuatta öngörülen süre"])} boyunca; sonra siliyor, yok ediyor veya anonim hale getiriyoruz.
Haklarınız nelerdir?
KVKK md. 11'deki haklarınız için Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ'e uygun başvurunuzu {f.address()} adresine iletebilirsiniz."""


@fam("aydinlatma_metni")
def aydin_2(f):
    return f"""Gizlilik ve Kişisel Verilerin Korunması Politikası

Bu Politika, {f.company()}'nin ("Şirket") internet sitesi ve mobil uygulaması aracılığıyla elde ettiği kişisel verilerin işlenmesine ilişkin esasları açıklar.

Çerezler: Sitemizde zorunlu, analitik ve pazarlama çerezleri kullanılmaktadır. Zorunlu olmayan çerezler için açık rızanız alınır.
Açık rıza: {f.pick(["Ticari elektronik ileti gönderimi", "Yurt dışındaki sunuculara aktarım", "Sağlık verilerinizin işlenmesi"])} için açık rızanıza başvurulmaktadır; rızanızı her zaman geri alabilirsiniz.
Saklama ve imha: Kişisel veriler Kişisel Veri Saklama ve İmha Politikamıza uygun olarak saklanır.
Veri güvenliği: KVKK md. 12 uyarınca gerekli teknik ve idari tedbirler alınmaktadır.
İlgili kişi hakları: Kanun'un 11. maddesi kapsamındaki taleplerinizi kvkk@{f.pick("firma|sirket|ornek")}.com.tr adresine iletebilirsiniz; talepleriniz en geç otuz gün içinde ücretsiz sonuçlandırılır.
Son güncelleme: {f.date()}"""


# ---------------------------------------------------------------- kvkk_basvuru
@fam("kvkk_basvuru")
def kvkkb_0(f):
    return f"""{f.company()}
VERİ SORUMLUSUNA BAŞVURU FORMU

Başvuru sahibinin
Adı Soyadı        : {f.name()}
T.C. Kimlik No    : {f.tckn()}
Adres             : {f.address()}
Telefon / E-posta : {f.phone()} / {f.email()}
Şirketle ilişkiniz: {f.pick("Müşteri|Eski çalışan|Ziyaretçi|İş ortağı|Çalışan adayı")}

Talep konusu (6698 sayılı KVKK md. 11):
{f.pick(["[X] Kişisel verilerimin işlenip işlenmediğini öğrenmek istiyorum.", "[X] Kişisel verilerimin silinmesini/yok edilmesini talep ediyorum.", "[X] Eksik veya yanlış işlenen verilerimin düzeltilmesini istiyorum.", "[X] Verilerimin aktarıldığı üçüncü kişileri bilmek istiyorum."])}
Açıklama: {f.pick(["Tarafınıza ait mağazadan alışveriş yaptıktan sonra rızam olmadan reklam SMS'leri almaya başladım.", "İşten ayrılmamdan sonra özlük dosyamın ne kadar süre saklanacağını öğrenmek istiyorum.", "Kamera kayıtlarında yer alan görüntülerimin silinmesini istiyorum."])}
Yanıtın gönderilmesini istediğim yöntem: {f.pick("Adresime posta ile|E-posta ile|Elden teslim")}

Başvuru tarihi: {f.date()}   İmza: ..........."""


@fam("kvkk_basvuru")
def kvkkb_1(f):
    return f"""{f.company()} Kişisel Verileri Koruma Birimine / Veri Sorumlusuna

Konu: 6698 sayılı Kanun'un 11. ve 13. maddeleri kapsamında bilgi talebim hk.

Ben {f.name()} (TCKN {f.tckn()}), {f.date()} tarihinden bu yana {f.pick("şirketinizin müşterisiyim|şirketinizde çalıştım|şirketinizin uygulamasını kullanıyorum")}.
Kanun'un 11. maddesi uyarınca;
a) hakkımda hangi kişisel verilerin işlendiğinin,
b) bu verilerin hangi amaçla işlendiğinin,
c) yurt içinde veya yurt dışında kimlere aktarıldığının
tarafıma bildirilmesini, ayrıca {f.pick(["pazarlama amaçlı işlemenin durdurulmasını", "verilerimin silinmesini", "hatalı adres bilgimin düzeltilmesini"])} talep ediyorum.
Başvurumun Kanun'un 13. maddesi uyarınca en geç otuz gün içinde sonuçlandırılmasını rica eder, aksi halde Kişisel Verileri Koruma Kurulu'na şikâyette bulunacağımı bildiririm.
Ek: Kimlik fotokopisi
{f.name()}  {f.address()}  {f.email()}"""


@fam("kvkk_basvuru")
def kvkkb_2(f):
    return f"""KİŞİSEL VERİLERİ KORUMA KURUMU'NA
ŞİKÂYET DİLEKÇESİ (KVKK md. 14)

Şikâyetçi: {f.name()}, {f.address()}
Şikâyet edilen veri sorumlusu: {f.company()}
Veri sorumlusuna başvuru tarihi: {f.date()}

Veri sorumlusuna {f.date()} tarihinde yaptığım başvuru {f.pick("otuz gün içinde cevaplanmamıştır.", "reddedilmiştir.", "yetersiz cevaplanmıştır.")} Şirket, açık rızam olmaksızın {f.pick("telefon numaramı üçüncü kişilerle paylaşmış", "sağlık bilgilerimi işverenime iletmiş", "fotoğrafımı reklamda kullanmış")} ve KVKK md. 5 ile md. 12'yi ihlal etmiştir.
Veri sorumlusu hakkında KVKK md. 18 uyarınca idari para cezası uygulanmasını ve verilerimin silinmesinin sağlanmasını talep ederim.
Ekler: Başvuru dilekçesi, cevap yazısı, ekran görüntüleri.
{f.date()}  {f.name()}"""


# ---------------------------------------------------------------- saglik_raporu
@fam("saglik_raporu")
def saglik_0(f):
    return f"""T.C. SAĞLIK BAKANLIĞI
{upper_tr(f.city())} {f.pick("ŞEHİR HASTANESİ|EĞİTİM VE ARAŞTIRMA HASTANESİ|DEVLET HASTANESİ")}
EPİKRİZ

Hasta Adı Soyadı: {f.name()}   Protokol No: {f.r.randint(10**6, 10**7)}
T.C. Kimlik No: {f.tckn()}   Doğum Tarihi: {f.date(1940, 2010)}
Yatış Tarihi: {f.date()}   Çıkış Tarihi: {f.date()}
Servis: {f.pick("Kardiyoloji|Genel Cerrahi|Nöroloji|Ortopedi|Dahiliye")}

Başvuru şikâyeti: {f.pick(["Göğüs ağrısı, nefes darlığı", "Karın ağrısı, bulantı", "Baş dönmesi, sol kolda güçsüzlük", "Düşme sonrası sağ kalçada ağrı"])}
Öykü: Hasta {f.r.randint(1, 10)} gündür devam eden şikâyetlerle acil servise başvurmuş. Özgeçmişinde {f.pick("hipertansiyon|diyabet|astım|bilinen hastalık yok")} mevcut.
Fizik muayene: Genel durum orta, bilinç açık, koopere. TA: {f.r.randint(90, 180)}/{f.r.randint(50, 110)} mmHg.
Tetkikler: Hemogram, biyokimya, EKG, {f.pick("BT|MR|USG|ekokardiyografi")} yapıldı.
Tanı: {f.pick(["Akut koroner sendrom (I21)", "Akut apandisit (K35)", "İskemik inme (I63)", "Femur boyun kırığı (S72.0)"])}
Tedavi: {f.pick(["Koroner anjiyografi ve stent", "Laparoskopik apendektomi", "Trombolitik tedavi", "Kalça protezi"])} uygulandı.
Taburculuk önerileri: İlaçlarını düzenli kullanması, {f.r.randint(7, 30)} gün sonra poliklinik kontrolü önerildi.

Sorumlu Hekim: Uzm. Dr. {f.name()} (Dip. Tescil No {f.r.randint(10000, 99999)})"""


@fam("saglik_raporu")
def saglik_1(f):
    return f"""SAĞLIK KURULU RAPORU

Rapor No: {f.r.randint(1000, 99999)}   Rapor Tarihi: {f.date()}
Hastanın Adı Soyadı: {f.name()}, Baba Adı: {f.pick(["Ali", "Mehmet", "Hasan"])}, TC: {f.tckn()}
Raporun Veriliş Nedeni: {f.pick(["Engellilik değerlendirmesi", "İşe giriş", "Sürücü belgesi", "Maluliyet tespiti (SGK)", "Adli rapor"])}

Klinik Bulgular ve Tanılar:
{para(f, [
        "Sol gözde görme keskinliği 0.3, sağ gözde 0.8.",
        "Lomber disk hernisi (M51.1), L4-L5 seviyesinde.",
        "Sağ elde 2. ve 3. parmakta hareket kısıtlılığı.",
        "Majör depresif bozukluk, tekrarlayan (F33).",
        "Kronik böbrek yetmezliği evre 3.",
    ], (2, 3))}
Tüm Vücut Fonksiyon Kaybı Oranı: %{f.r.randint(10, 90)}
Karar: {f.pick(["Ağır engelli değildir.", "Sürekli çalışmaya engel hali yoktur.", "Sürücü olmasında sakınca yoktur.", "Meslekte kazanma gücü kaybı mevcuttur."])}

Başhekim  Kurul Üyesi Uzm. Dr. {f.name()}  Kurul Üyesi Uzm. Dr. {f.name()}"""


@fam("saglik_raporu")
def saglik_2(f):
    return f"""Muayene Notu / Doktor Raporu

{f.pick(["Özel", "Medikal"])} {f.pick(["Yaşam", "Sağlık", "Şifa"])} Polikliniği
Tarih: {f.date()}
Hasta: {f.name()}, {f.r.randint(18, 90)} yaş

Hasta {f.pick("iş yerinde düşme sonrası", "trafik kazası sonrası", "darp edildiğini belirterek")} başvurdu. Muayenede {f.pick(["sağ ön kolda 3x4 cm ekimoz", "alında 2 cm kesi, sütur atıldı", "boyunda hassasiyet, servikal grafi normal"])} saptandı.
Basit tıbbi müdahale ile giderilebilir {f.pick("niteliktedir.|nitelikte değildir.")} Hayati tehlike yoktur.
Hastaya {f.r.randint(2, 10)} gün istirahat verilmiştir.
Reçete: {f.pick(["Parasetamol 500 mg 2x1", "İbuprofen 400 mg 3x1", "Amoksisilin 1 g 2x1"])}

Dr. {f.name()}  Kaşe / İmza"""


# ---------------------------------------------------------------- yazisma (e-posta, mektup)
@fam("yazisma")
def yazisma_0(f):
    a, b = f.name(), f.name()
    return f"""Kimden: {a} <{f.email()}>
Kime: {b} <{f.email()}>
{opt(f, .5, "Bilgi: " + f.email())}
Tarih: {f.date()} {f.r.randint(8, 22)}:{f.r.randint(10, 59)}
Konu: {f.pick(["RE: Toplantı notları", "Dosya hk.", "Fw: Sözleşme taslağı", "Ödeme gecikmesi", "Yarınki duruşma"])}

{f.pick(["Merhaba", "Sayın " + b, "Selamlar", "Değerli Meslektaşım"])},

{para(f, [
        "Ekte gönderdiğiniz taslağı inceledim, birkaç maddede değişiklik önerim var.",
        "Müvekkil ödemeyi bu hafta içinde yapacağını iletti.",
        "Yarın saat 10.00'da ofiste görüşebilir miyiz?",
        "Karşı tarafın avukatı uzlaşmaya açık görünüyor.",
        "Belgelerin aslını kargo ile gönderdim, takip numarası aşağıdadır.",
        "Konuyla ilgili sizi telefonla aramaya çalıştım ama ulaşamadım.",
    ], (2, 4))}

{f.pick(["İyi çalışmalar", "Saygılarımla", "Kolay gelsin", "Teşekkürler"])},
{a}
{f.phone()}"""


@fam("yazisma")
def yazisma_1(f):
    return f"""{f.city()}, {f.date()}

Sayın {f.name()},
{f.address()}

{f.pick(["Konu: Başvurunuz hakkında", "İlgi: " + f.date() + " tarihli yazınız", ""])}

{para(f, [
        f"{f.date()} tarihli mektubunuzu aldık; ilginiz için teşekkür ederiz.",
        "Talebiniz ilgili birimimiz tarafından değerlendirilmektedir.",
        "Sizinle yaptığımız telefon görüşmesine istinaden bu mektubu yazıyorum.",
        "Önümüzdeki ay şirket merkezimizde yapılacak etkinliğe sizi de davet etmek isteriz.",
        "Ekte istediğiniz belgelerin birer suretini bulabilirsiniz.",
        "Her türlü sorunuz için bizimle iletişime geçmekten çekinmeyiniz.",
    ], (2, 4))}

Saygılarımızla,
{f.name()}
{f.company()}"""


@fam("yazisma")
def yazisma_2(f):
    return f"""---------- İletilen mesaj ----------
Gönderen: {f.name()} ({f.email()})
Gönderildi: {f.date()}
Alıcı: {f.email()}
Konu: {f.pick(["Bilgi notu", "Acil: belgeler", "Toplantı daveti", "Teklif"])}

{f.pick(["Selam", "Merhabalar", "Hocam merhaba"])}, {f.pick(["dün konuştuğumuz konuyla ilgili", "müvekkilin dosyasıyla ilgili", "teklifimizle ilgili"])} kısa bir not geçiyorum. {f.pick(["Karşı taraf belgeleri cuma gününe kadar gönderecekmiş.", "Toplantıyı salı gününe aldık.", "Fiyat teklifimiz ektedir."])} Herhangi bir değişiklik olursa haber veririm.

Bu e-posta ve ekleri gizlidir; yalnızca alıcısına yöneliktir. Yanlışlıkla size ulaştıysa lütfen göndereni bilgilendirip siliniz.

{f.name()} | {f.company()}"""


# ---------------------------------------------------------------- mesajlasma
@fam("mesajlasma")
def mesaj_0(f):
    a, b = f.pick(["Ahmet", "Zeynep", "Av. Selin", "Mert"]), f.pick(["Ayşe Hanım", "Burak", "Müvekkil", "Ofis"])
    lines = [f"[{f.date()} {f.r.randint(8, 23):02d}:{f.r.randint(0, 59):02d}] {f.pick([a, b])}: {f.pick(['tamam', 'evrakları aldın mı', 'yarın duruşma var unutma', 'ödemeyi yaptım dekont attım', 'arayabilir misin', 'karşı taraf yine aramış', 'bugün gelemiyorum', 'saat kaçta buluşuyoruz', 'tebligat geldi mi', 'tamamdır teşekkürler', 'fotoğrafını attım'])}" for _ in range(f.r.randint(5, 14))]
    return "\n".join(lines)


@fam("mesajlasma")
def mesaj_1(f):
    a, b = f.name(), f.name()
    lines = [f"{f.date()}, {f.r.randint(0, 23):02d}:{f.r.randint(0, 59):02d} - {f.pick([a, b])}: {f.pick(['Merhaba avukat bey', 'Ev sahibi kirayı artırıyor ne yapmalıyım', 'Sözleşmede böyle bir madde yok', '<Medya dahil edilmedi>', 'Yarın ofise uğrarım', 'İhtarname mi çekelim', 'Peki ne kadar sürer', 'Bu mesaj silindi', 'Tamam anladım', 'Belgeleri e-postayla attım', 'Allah razı olsun'])}" for _ in range(f.r.randint(5, 14))]
    return "WhatsApp Sohbeti - Dışa Aktarım\n" * (f.r.random() < .5) + "\n".join(lines)


@fam("mesajlasma")
def mesaj_2(f):
    a, b = f.pick(["Ben", "Siz"]), f.pick(["Müvekkil", "Ece", "Kerem"])
    out = []
    for _ in range(f.r.randint(5, 12)):
        out.append(f"{f.pick([a, b])} ({f.r.randint(8, 23):02d}.{f.r.randint(0, 59):02d})")
        out.append(f.pick(["sabah haber verir misin", "dosya numarasını tekrar yazar mısın", "evet onayladım", "konum gönderildi", "sesli mesaj (0:42)", "noter randevusu cuma 14.00", "hesap numarası bu mu", "tamam abi"]))
    return "Telegram sohbet geçmişi\n" + "\n".join(out) if f.r.random() < .4 else "\n".join(out)


# ---------------------------------------------------------------- diger (other: not a legal document)
@fam("diger")
def diger_0(f):
    return f.pick([
        f"""Mercimek Çorbası Tarifi
Malzemeler: 1 su bardağı kırmızı mercimek, 1 adet soğan, 1 adet havuç, 1 yemek kaşığı salça, 6 su bardağı su, tuz, karabiber.
Hazırlanışı: Soğanı ve havucu doğrayıp tereyağında kavurun. Salçayı ekleyin. Yıkanmış mercimeği ve suyu ilave edip {f.r.randint(20, 40)} dakika pişirin. Blenderdan geçirip limon ile servis edin.""",
        f"""Haftalık Toplantı Gündemi - {f.company()} Pazarlama Ekibi
1. Sosyal medya kampanyası sonuçları
2. Yeni ürün lansmanı ({f.date()})
3. Bütçe revizyonu
4. Diğer konular
Katılım zorunludur. Toplantı odası: {f.r.randint(1, 9)}. kat.""",
        f"""{f.city()} hafta sonu hava durumu: Cumartesi parçalı bulutlu, en yüksek {f.r.randint(5, 35)} derece. Pazar günü sağanak yağış bekleniyor. Meteoroloji vatandaşları sel ve su baskınlarına karşı uyardı.""",
        f"""Alışveriş listesi:
- süt, yumurta, ekmek
- {f.r.randint(1, 5)} kg domates
- deterjan
- kedi maması
Not: Faturaları ödemeyi unutma!""",
        f"""{f.company()} {f.year()} Faaliyet Özeti
Şirketimiz bu yıl {f.r.randint(2, 30)} yeni ülkeye ihracat yaptı ve cirosunu %{f.r.randint(5, 80)} artırdı. Çalışan sayımız {f.r.randint(50, 3000)} kişiye ulaştı. Yeni fabrikamızın temeli {f.city()}'da atıldı.""",
        f"""Ders Notları - Mikroekonomi
Arz ve talep eğrilerinin kesiştiği nokta piyasa dengesini verir. Fiyat esnekliği, talep edilen miktardaki yüzde değişimin fiyattaki yüzde değişime oranıdır. Tam rekabet piyasasında firmalar fiyat alıcıdır.""",
        f"""Sevgili günlük, bugün {f.city()}'da hava çok güzeldi. Sabah erkenden kalkıp sahilde yürüdüm, öğleden sonra eski bir arkadaşımla kahve içtim. Akşam kitap okuyup erkenden yattım.""",
    ])


@fam("diger")
def diger_1(f):
    return f.pick([
        f"""Ürün Kullanım Kılavuzu - Kablosuz Kulaklık
1. Kulaklığı ilk kullanımdan önce {f.r.randint(1, 3)} saat şarj edin.
2. Eşleştirme için güç düğmesine 5 saniye basılı tutun; LED mavi-kırmızı yanıp sönecektir.
3. Telefonunuzun Bluetooth menüsünden cihazı seçin.
Garanti süresi 2 yıldır. Müşteri hizmetleri: {f.phone()}""",
        f"""Apartman Yönetimi Duyurusu
Değerli kat malikleri, {f.date()} tarihinde asansör bakımı yapılacağından 10.00-14.00 saatleri arasında asansör kullanılamayacaktır. Aidat ödemelerinin ayın 5'ine kadar yapılmasını rica ederiz. Yönetim""",
        f"""Gezi Programı: {f.r.randint(2, 7)} Günlük Kapadokya Turu
1. Gün: Göreme Açık Hava Müzesi, Uçhisar Kalesi
2. Gün: Balon turu (opsiyonel), Derinkuyu Yeraltı Şehri
3. Gün: Ihlara Vadisi yürüyüşü
Fiyata konaklama ve kahvaltı dahildir.""",
        f"""Basın Bülteni
{f.company()}, {f.city()}'da düzenlenen fuarda yeni ürün ailesini tanıttı. Genel Müdür {f.name()}, "Sürdürülebilir üretim önceliğimiz" dedi. Şirket önümüzdeki yıl {f.r.randint(100, 900)} kişiyi istihdam etmeyi planlıyor.""",
        f"""Spor Salonu Antrenman Programı
Pazartesi: Göğüs + triceps (4x12 bench press, 3x10 dips)
Çarşamba: Sırt + biceps
Cuma: Bacak + omuz
Her antrenmandan önce 10 dakika ısınma yapın.""",
        f"""Kitap Özeti: Roman, {f.pick(["İstanbul", "bir Anadolu kasabası", "bir sahil kenti"])}'nda geçen bir aile hikâyesini anlatıyor. Ana karakter, babasından kalan eski evi satıp satmamak konusunda kararsızdır. Yazar, göç ve aidiyet temalarını işliyor.""",
        f"""Toplantı Davetiyesi: Mezunlar Derneği Yıllık Buluşması
Tarih: {f.date()}  Yer: {f.city()} Kültür Merkezi
Program: Açılış konuşması, ödül töreni, akşam yemeği. Katılım için {f.email()} adresine yazınız.""",
    ])


@fam("diger")
def diger_2(f):
    return f.pick([
        f"""Teknik Şartname - Bilgisayar Alımı
İşlemci: en az 8 çekirdek; Bellek: 16 GB; Depolama: 512 GB SSD; Ekran: 15,6 inç. Garanti en az 3 yıl olmalıdır. Teslim süresi siparişten itibaren {f.r.randint(10, 60)} gündür.""",
        f"""Okul Aile Birliği Bülteni
Öğrencilerimizin dönem sonu gösterisi {f.date()} tarihinde okul bahçesinde yapılacaktır. Velilerimizin katılımını bekleriz. Kantin fiyat listesi panoda ilan edilmiştir.""",
        f"""Araç Bakım Kaydı
Plaka: {f.plate()}  Km: {f.r.randint(10000, 250000)}
Yapılan işlemler: motor yağı ve filtre değişimi, fren balatası kontrolü, lastik rotasyonu. Bir sonraki bakım {f.r.randint(10000, 15000)} km sonra.""",
        f"""Proje Durum Raporu (Sprint {f.r.randint(1, 40)})
Tamamlanan: giriş ekranı, ödeme entegrasyonu. Devam eden: bildirim servisi. Riskler: test ortamındaki performans sorunları. Bir sonraki demo {f.date()}.""",
        f"""Bahçe Bakım İpuçları: Domates fidelerini nisan sonunda dikin. Haftada iki kez derin sulama yapın. Yaprak bitlerine karşı sabunlu su kullanabilirsiniz.""",
        f"""Konferans Programı: Yapay Zekâ ve Toplum
09.30 Açılış, 10.00 Ana konuşma: {f.name()}, 11.30 Panel: Eğitimde dijital dönüşüm, 14.00 Atölyeler. Yer: {f.city()} Üniversitesi.""",
        f"""Müşteri Memnuniyet Anketi
1. Hizmetimizden ne kadar memnun kaldınız? (1-5)
2. Bizi arkadaşlarınıza tavsiye eder misiniz?
3. Görüş ve önerileriniz: ..................""",
    ])


LABELS = list(T)
assert all(len(v) == 3 for v in T.values()), {k: len(v) for k, v in T.items()}
