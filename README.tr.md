# Katip Yerel: tarayıcıda çalışan KVKK maskeleme

[English](README.md) · **Türkçe**

[![Canlı demo](https://img.shields.io/badge/demo-GitHub%20Pages-2f7d4f)](https://fikrifirat.github.io/katip/)
[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Space-katip--yerel-yellow)](https://huggingface.co/spaces/f1k/katip-yerel)
[![Model](https://img.shields.io/badge/%F0%9F%A4%97%20model-name--tagger--tiny-yellow)](https://huggingface.co/f1k/katip-tr-name-tagger-tiny)
[![Lisans: AGPL-3.0 + ticari](https://img.shields.io/badge/lisans-AGPL--3.0%20%2B%20ticari-blue)](COMMERCIAL.md)

Katip, Türkçe hukuk belgelerindeki kişisel verileri (T.C. kimlik no, VKN, IBAN, telefon, e-posta,
plaka, adres, ad soyad, KVKK md. 6 sağlık verileri) bulur ve maskeler; **belge bilgisayarınızdan hiç
çıkmaz**. Dosya tarayıcı sekmesinin içinde açılır, incelenir, maskelenir ve sızıntı kontrolünden
geçer. Hiçbir şey yüklenmez veya saklanmaz; sayfanın güvenlik politikası (CSP) başka bir adrese veri
gönderilmesini engeller. Bilgisayardan yalnızca indirdiğiniz maskelenmiş kopya çıkar.

Dava dosyalarını, sözleşmeleri veya mahkeme belgelerini müvekkil, bilirkişi ya da yapay zekâ
araçlarıyla KVKK'ya uygun paylaşması gereken hukuk büroları, şirket hukuk ve uyum ekipleri için.

![Katip Yerel](screenshot.png)

## Temel sonuçlar

Katip'in sentetik Türkçe hukuk belgeleri üzerinde ölçüldü. **Kör set**, geliştirme ve eğitim
sırasında hiç görülmemiş isimler içeren 16 belge türünde (4'ü yeni) 80 belgedir.

| | Sonuç |
| --- | --- |
| Bulunan değerler (kör set, varsayılan ayarlar) | **757'de 756 (%99,9)**; 10 fazladan işaretleme, hepsi sağlık terimi |
| Bulunan isimler | 365'te 364 (%99,7); yalnızca kurallarla %98,4 |
| Maskeden sonra hâlâ okunabilen değerler (uçtan uca, yalnızca kurallar) | metin, PDF, Word ve UDF'de %0,8; fotoğraf ve taramalarda %0,7–1,1 |
| İsim içermeyen hukuk metninde yanlış alarm | 3 belgede toplam 3 |
| Belge başına süre | metin, PDF, Word, UDF'de 0,1–0,3 sn; OCR ile 2–4,5 sn (4 çekirdekli bulut sunucusu) |
| Belge açıldıktan sonra yapılan ağ isteği | **0** (Chromium'da doğrulandı) |
| İlk yükleme | motor dosyaları (Python, PDF, OCR) yaklaşık 30 MB, isim etiketleyici için yaklaşık 30 MB daha; sonra tarayıcı önbelleğinde kalır |

### Demodaki modeller

| Model | Nedir | Bulunan değer (kör set) | Bulunan isim |
| --- | --- | --- | --- |
| **Katip Tiny** (önerilen) | Katip Kural + `katip-tr-name-tagger-tiny`, 2,6 MB | **757'de 756 (%99,9)** | 365'te 364 |
| **Katip Kural** | Katip'in Türkçe kuralları v0.2, 0,3 MB | 757'de 751 (%99,2) | 365'te 359 |
| Vanilla: kvkk-pii | açık kaynak [kvkk-pii](https://pypi.org/project/kvkk-pii/) 0.2 regex katmanı, varsayılan ayarlar (karşılaştırma) | 757'de 183 (%24,2) | 365'te 0 |
| Katip BERTurk | isim, adres ve sağlık terimleri için BERTurk ince ayarı | eğitimde | |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="metrics/accuracy-dark.svg">
  <img alt="Kör sette veri türüne göre bulunan değerler" src="metrics/accuracy-light.svg" width="720">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="metrics/speed-dark.svg">
  <img alt="Biçime göre belge başına süre ve maskeden sonra okunabilen değerler" src="metrics/speed-light.svg" width="720">
</picture>

**Bu sonuçların henüz göstermedikleri.** Belgelerin hepsi sentetiktir ve kör setteki 16 belge
türünün 12'si eğitim verisiyle aynı şablonları paylaşır; gerçek dava dosyalarında sonuçlar daha
düşük olacaktır. Süreler tipik bir dizüstü bilgisayardan değil, bulut sunucusundan alınmıştır. Ham
veriler: [`metrics/`](metrics/). Betikler: `ml/benchmark.py`, `ml/make_charts.py`. Gerçek
belgelerle ölçmemize yardım edin: [İletişim](#sorular-pilot-ve-iletişim).

## Desteklenenler

| Belge | Yöntem |
| --- | --- |
| Metin katmanlı PDF | kutunun altındaki karakterler gerçekten silinir (MuPDF `applyRedactions`), meta veriler temizlenir |
| Taranmış PDF, fotoğraf (PNG, JPG) | Türkçe OCR (Tesseract), kutular görüntüye işlenir |
| Word `.docx` | metin, izlenen silmeler, yorum yazarları ve belge özellikleri maskelenir |
| UYAP `.udf` | yerinde maskelenir, geçerli bir UDF olarak kalır |
| Düz metin | |

| Veri türü | Tespit |
| --- | --- |
| T.C. kimlik no, VKN, IBAN, kart numarası | sağlama (checksum) doğrulamalı kalıplar |
| Telefon, e-posta, plaka, doğum tarihi | bağlam sözcükleriyle Türkçe biçimler |
| Adres | Türk adres yapısı (Mh., Cd., Sk., No, ilçe/il) |
| Ad soyad | isim listeleri, ipucu sözcükler (Av., Sayın, davacı …), büyük harf ve ek kuralları, ayrıca cihaz üzerinde çalışan isim etiketleyici |
| KVKK md. 6 özel nitelikli veriler (sağlık, sendika …) | sözlük, incelemeye işaretlenir |

Denendiği belge türleri: dilekçe, karar, kira ve iş sözleşmesi, fatura, aydınlatma metni,
vekâletname, ihtarname, mektup, e-posta, duruşma tutanağı, mesajlaşma kaydı, epikriz ve bilirkişi raporu.

## Deneyin

- **Demo:** https://fikrifirat.github.io/katip/ (veya [Hugging Face Space](https://huggingface.co/spaces/f1k/katip-yerel)).
  16 örnek belgeden birini seçip cevap anahtarına göre bulma oranını, isabeti, kaçanları ve yanlış
  alarmları canlı görün ya da kendi dosyanızı açın.
- Belge seçer seçmez görünür; bulunan değerler sayfanın üzerinde işaretlenir.
- Tek inceleme ekranı: her değeri sayfada veya listede açıp kapatın, kaçanları ekleyin, sonra
  **Maskeleri uygula** ve indirin. Maske rengini ve isteğe bağlı filigranı seçin.
- Tespit modelini, OCR modelini, güven eşiğini ve veri türlerini değiştirin; arayüz Türkçe ve İngilizce.
- **Hata bildir** küçük bir rapor hazırlar (ayarlar, skorlar, maskelenmiş çıktı; orijinal yalnızca
  siz işaretlerseniz) ve bir e-posta taslağı açar.

## Nasıl çalışır

| Adım | Bileşen |
| --- | --- |
| Tespit kuralları | Katip'in Python tanıyıcıları ve sözcük listeleri, değiştirilmeden, Pyodide içinde (WebAssembly'ye derlenmiş Python) |
| İsim etiketleyici | [`katip-tr-name-tagger-tiny`](https://huggingface.co/f1k/katip-tr-name-tagger-tiny), 2,6 MB int8 ONNX, transformers.js |
| Metin, UDF, Word | Pyodide içinde standart kütüphane Python (`src/py/local_formats.py`) |
| PDF | MuPDF.js |
| Tarama ve fotoğraf | Türkçe modelle tesseract.js |
| Sızıntı kontrolü | çıktı her maskelenen değer için yeniden okunur (metin katmanı veya ikinci OCR) |

Tarayıcıdaki kurallar Katip'in sunucu motoruyla birebir aynı sonucu verir (1.803 değerde 0 fark);
tarayıcıdaki etiketleyici Python onnxruntime ile aynıdır (152 değerde 0 fark).

## Yol haritası

- [x] PDF, tarama, fotoğraf, Word, UDF ve metin için tamamen tarayıcıda maskeleme
- [x] Cihaz üzerinde isim etiketleyici, herkese açık demo, Hugging Face Space ve model
- [ ] İsim, adres ve sağlık terimleri için BERTurk modeli ([`ml/berturk/`](ml/berturk/), eğitimde)
- [ ] Pilot bürolardan, izinli gerçek belgelerle değerlendirme
- [ ] Dizüstü ve telefon süreleri; daha küçük ilk indirme
- [ ] Kurum ve mahkeme adları, esas/karar numaraları, daha fazla KVKK md. 6 kategorisi
- [ ] Excel, e-posta (`.eml`, `.msg`) ve klasörle toplu işlem
- [ ] Çevrimdışı kullanım için tarayıcı eklentisi ve masaüstü uygulaması

## Sorular, pilot ve iletişim

- Sorular, kaçan maskelemeler, öneriler: [issue açın](https://github.com/fikrifirat/katip/issues/new/choose).
  Lütfen gerçek kişisel veri paylaşmayın; demodaki *Hata bildir* düğmesini veya sahte değerleri kullanın.
- Büronuzda pilot, entegrasyon veya ticari lisans: **fikrifirat@gmail.com**.

## Geliştirme

Derleme, test ve eğitim adımları için [İngilizce README](README.md#develop).

## Lisans

Kod ve demo: **[AGPL-3.0](LICENSE)**; AGPL'nin kaynak kodu paylaşma yükümlülüğü olmadan ürünlerde,
kurum içi sistemlerde veya çevrimiçi hizmetlerde kullanım için **ticari lisans** vardır, bkz.
[COMMERCIAL.md](COMMERCIAL.md). Modeller: CC BY-NC 4.0.

Üçüncü taraf bileşenler: MuPDF (AGPL-3.0, Artifex), kvkk-pii (MIT, Aleonis; yalnızca karşılaştırma), Pyodide (MPL-2.0), tesseract.js ve `tur` modeli
(Apache-2.0), transformers.js (Apache-2.0), ONNX Runtime (MIT), OpenSubtitles sıklık listesinden
`common_words.txt` (CC BY-SA 4.0). Örnek belgeler sentetiktir; gerçek kişilerle benzerlik tesadüfidir.
