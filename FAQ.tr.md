# Katip: sık sorulan sorular

[English](FAQ.md) · **Türkçe**

Avukatlar ve büro çalışanları için kısa cevaplar. Katip'in verileri nasıl işlediğinin ayrıntısı:
[PRIVACY.tr.md](PRIVACY.tr.md). Bu metin genel bilgidir, hukuki görüş değildir.

[rehber]: https://www.kvkk.gov.tr/Icerik/8990/avukatlarin-mesleki-faaliyetlerinde-kisisel-verilerin-korunmasina-iliskin-uygulama-rehberi-yayimlandi

## Katip nedir?

Türkçe belgelerdeki kişisel verileri (ad soyad, T.C. kimlik numarası, telefon, adres, sağlık bilgisi ve
dahası) bulup `[AD SOYAD-1]` gibi yer tutucularla değiştiren bir araç. Bu işi **kendi bilgisayarınızda**
yapar. Tarayıcıda çalışan bir web uygulaması, Python ve JavaScript için `katip-mask` paketleri ve Claude'un
müvekkil belgesi üzerinde Katip'in bulduğu değerleri görmeden çalışmasını sağlayan Katip Kalkan eklentisi
olarak kullanılabilir.

## Avukat bir belgeyi yapay zekâya vermeden önce neden maskelesin?

Çünkü müvekkilin verileri için veri sorumlusu avukattır ve bu verileri yurt dışındaki bir yapay zekâ
sağlayıcısına göndermek, hukuki dayanak isteyen bir yurt dışına aktarımdır. Kişisel Verileri Koruma Kurulu'nun
[*Avukatların Mesleki Faaliyetlerinde Kişisel Verilerin Korunmasına İlişkin Uygulama Rehberi*][rehber]
(22 Eylül 2026'da duyuruldu) üretken yapay zekâ araçlarını ayrıca ele alır (s. 120–121). Müvekkil
belgelerini bu araçlara yüklemenin yurt dışına aktarım sayılabileceğini belirtir ve paylaşmadan önce
verilerin maskelenmesini ya da anonimleştirilmesini önerir (s. 146). Katip bu öneriye göre tasarlandı.
KVKK m.4 de yalnızca işin gerektirdiği verinin işlenmesini ister; dilekçe taslağı hazırlayan bir yapay zekânın
müvekkilin adına çoğu zaman ihtiyacı yoktur.

## Katip, yapay zekâ kullanımını KVKK'ya uygun hâle getirir mi?

Hayır. Maskeleme, büronuzdan çıkan müvekkil verisini azaltır. Her aktarım için yine hukuki bir dayanak
gerekir (KVKK m.9), sır saklama yükümlülüğünüz sürer (Avukatlık Kanunu m.36) ve sonucu yine siz kontrol
edersiniz. Maskeli metin de çoğu zaman kişisel veridir, çünkü bağlam bir kişiye işaret edebilir.

## Nasıl çalışır?

1. Kurallar yapılı değerleri bulur: T.C. kimlik, vergi ve pasaport numaraları, IBAN, telefon, e-posta,
   plaka, UETS adresi, dosya numaraları.
2. Küçük bir dil modeli (Katip Mask) metin içindeki ad, yer ve kurum adlarını bulur.
3. Bir kez bulunan değer, ek almış hâlleri de dahil (`Ayşe'nin`) geçtiği her yerde maskelenir.
4. Son bir kontrol, bulunan değerlerden okunabilir kalan var mı diye bakar. Varsa Katip metni vermeyi
   reddeder.

Model sentetik belgeler, Türkçe Vikipedi'den derlenmiş açık bir varlık tanıma veri seti ve TurkishLegalNER'in
eğitim bölümüyle eğitildi. Hiçbir müvekkil belgesi kullanılmadı. Ayrıntılar ve test sonuçları:
[connector/README.md](connector/README.md#how-it-works-and-what-it-was-trained-on).

## Neyi maskeler, neyi okunur bırakır?

Bir profil seçersiniz. Her profil, bir öncekinin maskelediği her şeyi ve fazlasını maskeler.

| | Mahkemeye sunum (`court`) | Yapay zekâ ile paylaşım (`ai`, Kalkan'da varsayılan) | Tam anonim (`anon`) |
|---|---|---|---|
| Ad soyad, T.C. kimlik, pasaport ve yabancı kimlik no, telefon, e-posta, IBAN, UETS | maskelenir | maskelenir | maskelenir |
| Sağlık ve diğer özel nitelikli veriler (KVKK m.6) | maskelenir | maskelenir | maskelenir |
| Adli sicil bilgileri | okunur | maskelenir | maskelenir |
| Tarafın kendi adresi | maskelenir | maskelenir | maskelenir |
| Dava konusu taşınmazın adresi | okunur | maskelenir | maskelenir |
| Diğer adresler | cadde/sokak okunur, bina ve kapı no maskelenir | maskelenir | maskelenir |
| Baro sicil numarası | maskelenir | maskelenir | maskelenir |
| Kendi dosyanızın esas ve soruşturma numaraları | okunur | maskelenir | maskelenir |
| Mahkeme ve kurum adları, tarihler, yer adları | okunur | okunur | maskelenir |
| Emsal karar künyeleri (Yargıtay, Danıştay, AYM …) | okunur | okunur | okunur |

Neden: bu kurallar, çalışan bir avukatın gerçek dilekçeler üzerindeki değerlendirmesinden çıktı. Mahkemenin
dosya numarasına, mahkeme adına ve emsal künyesine ihtiyacı vardır. Tarafın ikametgâhı kişisel veridir; dava
konusu taşınmazın adresi ise delildir. Yapay zekâ profilinde kendi dosya numaralarınızı maskeli tutuyoruz,
çünkü müvekkili tanınır kılabilirler ve yapay zekânın bunlara nadiren ihtiyacı olur.

## Katip ne yapmaz?

* **Bazı değerleri kaçırabilir.** Sentetik test belgelerinde değerlerin yaklaşık %99'unu maskeler; gerçek
  metinde daha fazlasını kaçırır ([KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench)). Paylaşmadan
  önce çıktıyı mutlaka okuyun.
* **Sohbete eklediğiniz dosyayı ya da yazdığınızı maskelemez.** Yalnızca Katip'ten geçen metin maskelenir.
  Claude'a ya da ChatGPT'ye eklediğiniz bir dosya sağlayıcıya olduğu gibi gider.
* **Anonimleştirmez.** Bağlam ya da eşleşme tablosu bir kişiye işaret edebildiği sürece yer tutucular takma
  adlandırmadır.
* **Hukuki değerlendirmenizi denetlemez;** yapay zekâ da denetlemez.

## Verilerim nereye gider?

Sizin göndermeyi seçtiğiniz dışında hiçbir yere. Web uygulaması tarayıcı sekmenizde çalışır; Kalkan eklentisi
bilgisayarınızda çalışır ve Claude'a yalnızca maskeli metni verir. Geliştiricinin belge alan bir sunucusu
yoktur; hesap, analitik ya da telemetri yoktur. Kalkan, gerçek adları son belgenize geri koyabilmek için yer
tutucu eşleşmelerini bilgisayarınızda 30 gün şifreli tutar. Ayrıntı: [PRIVACY.tr.md](PRIVACY.tr.md).

## Bir değer kaçarsa sorumlu kim?

Veri sorumlusu olarak neyin gönderileceğine siz karar verir, göndermeden önce siz kontrol edersiniz. Katip
ücretsiz, açık kaynaklı ve "olduğu gibi" sunulan bir yazılımdır. Riski azaltır, üstlenmez.

## Bir sorunu ya da kaçan bir değeri nasıl bildiririm?

Bir [GitHub issue](https://github.com/fikrifirat/katip/issues) açın. Örüntüyü uydurma değerlerle anlatın.
Gerçek bir müvekkil belgesini ya da gerçek kişisel veriyi asla yapıştırmayın.
