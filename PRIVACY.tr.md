# Katip verileri nasıl işler

[English](PRIVACY.md) · **Türkçe**

Son güncelleme: 20 Kasım 2026. Bu metin Katip web uygulamasını (fikrifirat.github.io/katip ve Hugging Face
Space), Python ve JavaScript için `katip-mask` paketlerini ve Claude için Katip Kalkan bağlayıcısını kapsar.
İletişim: fikrifirat@gmail.com ya da [GitHub issues](https://github.com/fikrifirat/katip/issues) (oraya gerçek kişisel veri yazmayın). Metin ileride geliştiricinin kendi
sitesine taşınacak; bu dosya kopya olarak kalır.

## Kısaca

Katip, Türkçe belgelerdeki kişisel verileri bulur ve **kendi bilgisayarınızda** maskeler. Geliştiricinin
belgelerinizi alan bir sunucusu yoktur; Katip'te hesap, analitik, telemetri ya da hata raporlama yoktur.
Maskeleme, bir yapay zekâ sağlayıcısına gönderdiğiniz veriyi azaltır. Bu gönderimi tek başına hukuka uygun
hâle getirmez ve bazı değerleri kaçırabilir; çıktıyı yine sizin kontrol etmeniz gerekir. Kısa cevaplar: [FAQ.tr.md](FAQ.tr.md).

## Her bileşen verinizle ne yapar

| | Belgeler nerede işlenir | Bilgisayarınızdan ne çıkar | Ne saklanır |
|---|---|---|---|
| **Web uygulaması** | Tarayıcı sekmenizde | Hiçbir şey. Sayfanın içerik güvenliği politikası (CSP) başka adreslere veri gönderilmesini engeller. Maskeli kopyayı siz indirirsiniz. | Hiçbir şey. Sekmeyi kapatınca belge silinir. |
| **Gönder sayfası** (`gonder.html`) | Tarayıcı sekmenizde | Varsayılan olarak hiçbir şey. Claude'u ya da ChatGPT'yi maskeli metinle siz açarsınız, ya da metni kopyalar veya paylaşırsınız. Yalnızca "Kendi API anahtarınızla burada sorun"u kullanırsanız maskeli metin (asla asıl belge ya da yer tutucu eşleşmeleri değil) tarayıcınızdan doğrudan kendi hesabınızla api.anthropic.com ya da api.openai.com'a gider; sayfanın CSP'si yalnızca bu iki adrese izin verir. | Tarayıcınızın deposunda: dil, profil, gönderim kaydı (zaman, profil, hedef, veri türü sayıları; değerler asla) ve değerlendirmeleriniz. API anahtarınız yalnızca "Bu cihazda hatırla"yı işaretlerseniz. Yer tutucu eşleşmeleri yalnızca açık sekmede tutulur. |
| **katip-mask (Python, npm)** | Kendi programınızın içinde | Hiçbir şey; yalnızca `model=` verirseniz model dosyaları bir kez Hugging Face'ten sabit bir sürümle indirilir ve SHA-256 ile doğrulanır. Metin gönderilmez. | İndirilen modeller, `~/.cache/katip-mask` içinde. |
| **Katip Kalkan (Claude)** | Bilgisayarınızda, Claude'un başlattığı yerel bir programda | Yalnızca maskeli metin, kullanmayı seçtiğiniz Claude'a. İlk açılışta açık kaynak yardımcı paketler bir kez PyPI'dan indirilir. | Yer tutucu eşleşmeleri (`[AD SOYAD-1]` → gerçek ad), `~/.katip/vault` içinde AES-256-GCM ile şifreli; 30 gün sonra ya da istediğinizde silinir. Ayrıntı: [connector/PRIVACY.md](connector/PRIVACY.md). |

Barındırma: web uygulaması GitHub Pages ve Hugging Face üzerinden sunulur. Her web sitesinde olduğu gibi bu
şirketler IP adresinizi ve tarayıcınızın istediği dosyaları kendi gizlilik politikalarına göre görür.
Belgelerinizi hiçbir zaman almazlar.

## Kim neden sorumlu

* **Avukat ya da hukuk bürosu olarak siz**, müvekkillerinizin verileri için **veri sorumlususunuz** (KVKK
  m.3). Hangi veriyi, hangi araçla ve hangi hukuki sebebe dayanarak işleyeceğinize siz karar verirsiniz.
* **Katip'in geliştiricisi** müvekkil verilerinizi almaz, görmez ve saklamaz; bu nedenle bu veriler için
  veri işleyen konumunda değildir.
* **Metin gönderdiğiniz yapay zekâ sağlayıcısı** (Anthropic, OpenAI, Google vb.) metni kendi koşullarına göre
  işler. Sunucuları Türkiye dışındaysa kişisel veri göndermek yurt dışına aktarımdır.

## Avukatlar için hukuki çerçeve

Bu metin genel bilgidir, hukuki görüş değildir.

* **Avukatlar veri sorumlusudur.** Kurul'un [*Avukatların Mesleki Faaliyetlerinde Kişisel Verilerin
  Korunmasına İlişkin Uygulama Rehberi*](https://www.kvkk.gov.tr/Icerik/8990/avukatlarin-mesleki-faaliyetlerinde-kisisel-verilerin-korunmasina-iliskin-uygulama-rehberi-yayimlandi) (KVKK Yayınları No. 115, 22 Eylül 2026'da duyuruldu) bunu açıkça
  söyler ve üretken yapay zekâ araçlarını ayrıca ele alır (s. 120–121). Müvekkil belgelerini bu araçlara
  yüklemenin yurt dışına aktarım sayılabileceğini belirtir ve paylaşmadan önce verilerin maskelenmesini ya da
  anonimleştirilmesini önerir (s. 146).
* **Yurt dışına aktarım hukuki dayanak ister (KVKK m.9).** 7499 sayılı Kanun'la (1 Haziran 2024'te yürürlüğe
  girdi) yapılan değişiklikten sonra aktarım; m.5 ya da m.6'daki işleme şartlarından biri bulunduğunda **ve**
  ülke hakkında yeterlilik kararı varsa ya da uygun bir güvence sağlanmışsa yapılabilir: imzalanıp beş iş günü
  içinde Kurul'a bildirilen standart sözleşme, Kurul'un onayladığı bağlayıcı şirket kuralları veya Kurul'un
  izin verdiği yazılı taahhütname. Bunlar olmadan arızi aktarım yalnızca m.9/6'da sayılan dar hâllerde
  mümkündür. Kurul'un güncel yeterlilik kararlarına ve sağlayıcının veri işleme koşullarına bakın.
* **Özel nitelikli veriler daha fazla özen ister (KVKK m.6).** Sağlık verisi, ceza mahkûmiyeti, din,
  biyometrik veri gibi bilgiler dava dosyalarında sık geçer ve daha sıkı işleme şartlarına tabidir.
* **Yalnızca gerekeni işleyin (KVKK m.4).** Kişisel veriler işlendikleri amaçla "bağlantılı, sınırlı ve
  ölçülü" olmalıdır. Dilekçe taslağına yardım eden bir yapay zekânın müvekkilin adına ya da T.C. kimlik
  numarasına nadiren ihtiyacı olur.
* **Sır saklama yükümlülüğü ayrıca geçerlidir (Avukatlık Kanunu m.36).** Avukat, mesleği nedeniyle öğrendiği
  bilgileri KVKK ne derse desin açıklayamaz.

## Maskeleme ne yapar, ne yapmaz

* Katip bulduğu değerleri `[AD SOYAD-1]` gibi yer tutucularla değiştirir ve gerçek değerleri bilgisayarınızda
  tutar. Bulduğu bir değer maskelemeden sonra hâlâ okunabiliyorsa metni vermeyi reddeder.
* **Bazı değerleri kaçırabilir.** Hiç bulamadığı bir değer metinde kalır. Sentetik test belgelerinde
  değerlerin yaklaşık %99'unu maskeler; gerçek metinde kaçırma oranı daha yüksektir
  ([KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench)). Göndermeden önce çıktıyı kontrol edin.
* **Maskeli metin çoğu zaman hâlâ kişisel veridir.** Adları yer tutucuyla değiştirmek, eşleşme tablosu
  durdukça ve bağlam (tarih, olay, yer) bir kişiye işaret edebildikçe anonimleştirme değil takma adlandırmadır.
  KVKK bu metne de uygulanır; maskeleme riski ve veri miktarını azaltır, bu da m.4 ve m.12'yi destekler.
* **Sohbete eklenen dosyalar ve yazdıklarınız maskelenmez.** Sohbete eklediğiniz bir dosya ya da yazdığınız
  bir ad, sağlayıcıya olduğu gibi gider. Yalnızca Katip'ten geçen metin maskelenir.

## Katip hakkında ne diyoruz, ne demiyoruz

Diyoruz ki: "Katip, bir belgeyi yapay zekâ ile paylaşmadan önce kişisel verileri bilgisayarınızda maskeler;
böylece büronuzdan daha az müvekkil verisi çıkar. Her aktarım için yine hukuki bir dayanağa ihtiyacınız var
ve sonucu yine siz kontrol edersiniz."

Demiyoruz ki: Katip "KVKK uyumlu"dur, "KVKK açısından güvenlidir" ya da "anonimdir"; yapay zekâya veri
göndermeyi hukuka uygun hâle getirir; ya da her değeri bulur.

## Haklarınız

Katip'in geliştiricisi kullanıcılar ya da müvekkilleri hakkında kişisel veri tutmaz; bu yüzden geliştirici
tarafında erişilecek ya da silinecek bir veri yoktur. Katip'in bilgisayarınızda sakladıkları her zaman
silinebilir: Kalkan eşleşmeleri `forget_matter` ile ya da `~/.katip` klasörünü silerek, indirilen modeller
`~/.cache/katip-mask` klasörünü silerek. Müvekkilleriniz KVKK m.11'deki haklarını veri sorumlusu olarak size
karşı kullanır.
