# Uğur'a sorular: ajan sistemin GDPR belgeleri için

Bu soruların cevaplarıyla Katip, GDPR için gereken belgelerin (işleme kaydı, DPIA, aydınlatma metni,
sözleşmeler, aktarım değerlendirmesi, saklama politikası, ihlal prosedürü, başvuru prosedürü, teknik
tedbirler, AB Yapay Zekâ Tüzüğü notu, meşru menfaat testi) taslaklarını çıkarıyor. Her belgenin yanına
KVKK karşılığını ekliyor; KVKK uygulanıyorsa özet, envanter ve aydınlatma metni Türkçe de çıkıyor.

Kısa cevaplar yeterli. "Bilmiyorum" veya "henüz karar vermedim" de bir cevap: o nokta belgede açık
soru olarak işaretlenir. Müvekkil adı veya gerçek bir dosyadan bilgi gerekmiyor; sadece sistemin
nasıl çalıştığı.

## 1. Siz ve müvekkilleriniz

1. Büro nerede kurulu? AB'de bir şubeniz veya ortağınız var mı?
2. AB'deki müvekkiller size kendi dosyalarını (çalışan listeleri, sözleşmeler, yazışmalar) gönderiyor mu?
3. Hizmeti AB'deki **kişilere** de sunuyor musunuz (ör. AB'de yaşayan bireysel müvekkiller, AB'ye
   yönelik bir internet sitesi, Almanca/Fransızca tanıtım), yoksa sadece şirketlere mi?
4. Sistemi sadece kendi büronuzda mı kullanacaksınız, yoksa başka bürolara veya şirketlere de
   sunmayı düşünüyor musunuz (kendi adınızla, ücretli veya ücretsiz)?

## 2. Ajanlar ne yapıyor?

5. Kaç ajan var ve her biri ne iş yapıyor? (ör. "belgeleri sınıflandırıyor", "DD raporu için
   kamu kaynaklarında arama yapıyor", "mütalaa taslağı yazıyor")
6. Her ajan hangi yapay zekâ modelini kullanıyor? (ör. Claude, GPT, Mistral, kendi sunucunuzda
   açık kaynak bir model) Hangi abonelik veya API planıyla?
7. Ajanlar hangi araçlara erişiyor? (internet araması, e-posta, ortak klasör, veritabanı, MASAK /
   ilan.gov.tr / Ticaret Sicili Gazetesi gibi kaynaklar)
8. Bir ajanın çıktısı, bir avukat okumadan müvekkile veya mahkemeye gidebiliyor mu?
9. Ajanlar kişiler hakkında puan, risk skoru veya "şüpheli / değil" gibi bir sonuç üretiyor mu,
   yoksa sadece bulunan kaydı kaynağıyla mı gösteriyor?
10. Sistem bir kişiyle doğrudan sohbet ediyor mu (ör. müvekkil sitede bir sohbet botuyla konuşuyor)?

## 3. Hangi veriler?

11. Kimlerin verisi sisteme giriyor? (müvekkiller, DD raporundaki şirketlerin yöneticileri ve
    ortakları, dosyalardaki çalışanlar, tanıklar, karşı taraflar...)
12. Hangi tür veriler? Özellikle şunlar var mı:
    - TC kimlik / pasaport numarası
    - sağlık bilgisi (ör. iş kazası mütalaaları)
    - ceza, yaptırım listesi, mal varlığı dondurma, dava kayıtları
    - çocuklara ait bilgiler
13. Yılda yaklaşık kaç kişinin verisi işleniyor? (kabaca: 100, 1.000, 10.000+)

## 4. Veriler nereye gidiyor, nerede duruyor?

14. Metin, yapay zekâ modeline gönderilmeden önce maskeleniyor mu (ör. Katip Kalkan ile)?
    Maskelenmiyorsa hangi belgeler olduğu gibi gidiyor?
15. Belgeler, ajan hafızası, vektör veritabanı ve kayıtlar (log) nerede tutuluyor? Kendi
    bilgisayarınızda mı, bir sunucuda mı (hangi firma, hangi ülke)?
16. Model sağlayıcılarıyla bir veri işleme sözleşmesi (DPA) imzaladınız veya online kabul ettiniz mi?
    Sağlayıcı verilerinizi model eğitimi için kullanıyor mu? Gönderdiğiniz metni kaç gün saklıyor?

## 5. Saklama ve güvenlik

17. Dosyalar iş bittikten sonra ne kadar saklanıyor? Ajanların hafızası ve kayıtları da aynı sürede
    siliniyor mu?
18. Sisteme girişte iki aşamalı doğrulama var mı? Yedek alınıyor mu?
19. Bir veri sızıntısı olursa kim karar verecek ve kurumlara (KVKK Kurulu, AB denetim otoritesi)
    bildirimi kim yapacak?

## 6. Sözleşmeler ve sır saklama

20. AB'deki müvekkil sizi "veri işleyen" olarak mı görüyor (ör. sizden AVV / DPA imzalamanızı
    istedi mi), yoksa siz kendi mesleki kararınızla mı çalışıyorsunuz? Dosyaya göre değişiyor mu?
21. Aynı dosyalarda birlikte çalıştığınız yabancı bir büro var mı? Verileri birlikte mi belirliyorsunuz?
22. Müvekkillerinizin kendi sır saklama kuralları (ör. Almanya'da § 203 StGB) size de yükleniyor mu?
23. Ücretsiz bir yapay zekâ hesabı veya ortak kullanılan bir giriş (aynı şifreyle birden fazla kişi)
    var mı? Yedekten geri yükleme hiç denendi mi?
24. Dosyalarda çocuklara veya vefat etmiş kişilere ait bilgi var mı?

## 7. Son olarak

25. Bu belgeleri kim isteyecek veya kontrol edecek: AB'deki bir müvekkil mi, bir yatırımcı mı,
    yoksa kendi iç düzeniniz için mi? (Hangi belgeye öncelik vereceğimizi bu belirliyor.)
