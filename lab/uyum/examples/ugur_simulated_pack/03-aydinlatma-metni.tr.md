# Aydınlatma metni (KVKK m.10)

**Sistem:** Uğur Hukuk ajan sistemi (simulated) · **Veri sorumlusu:** Uğur Hukuk Bürosu (simulated) · **Anket tarihi:** 2026-11-23

> **Avukat incelemesi için TASLAK.** Katip bu metni yukarıdaki ankete göre hazırladı. Hukuki görüş değildir; sistemin KVKK'ya, GDPR'a veya AB Yapay Zekâ Tüzüğü'ne uygun olduğu anlamına gelmez. **[AÇIK: ...]** ile işaretli yerler eksik bilgidir.

Bu metin, kişisel veriler elde edilirken verilir ve açık rıza metninden ayrı tutulur (Aydınlatma Yükümlülüğünün Yerine Getirilmesinde Uyulacak Usul ve Esaslar Hakkında Tebliğ). Amaç ve hukuki sebepler genel ifadelerle değil, faaliyet bazında yazılmalıdır.

## Veri sorumlusu

Uğur Hukuk Bürosu (simulated), Şişli, İstanbul (fictional). Kişisel verilerle ilgili başvurular için: **[AÇIK: iletişim adresi]**.

## Kişisel verileriniz hangi amaçla ve hangi hukuki sebeple işleniyor

| Amaç | Hukuki sebep | Saklama süresi |
|---|---|---|
| Müvekkil belgelerini almak, dosyaya göre kaydetmek, çıkar çatışmasını kontrol etmek | KVKK m.5/2-c (sözleşmenin kurulması veya ifası) **[AÇIK: teyit edin; müvekkil işi için m.5/2-e daha uygun olabilir]**; KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması) | Dosya kapandıktan sonra 10 yıl |
| Almanca/Hollandaca taranmış belgeleri Türkçe metne dönüştürmek | KVKK m.5/2-f (meşru menfaat) **[AÇIK: teyit edin; müvekkil işi için m.5/2-e daha uygun olabilir]**; KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması) | **[AÇIK: saklama süresi]** |
| DD konusu şirketin arkasındaki kişiler hakkında yaptırım, malvarlığı dondurma, iflas, dava kayıtları ve basın haberlerini bulmak | KVKK m.5/2-f (meşru menfaat) **[AÇIK: teyit edin; müvekkil işi için m.5/2-e daha uygun olabilir]** | Dosya kapandıktan sonra 10 yıl |
| Müvekkil için DD raporu ve hukuki mütalaa hazırlamak | KVKK m.5/2-f (meşru menfaat) **[AÇIK: teyit edin; müvekkil işi için m.5/2-e daha uygun olabilir]**; KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması) | Dosya kapandıktan sonra 10 yıl |
| Hazırlanan taslakları müvekkile iletmek | KVKK m.5/2-c (sözleşmenin kurulması veya ifası) **[AÇIK: teyit edin; müvekkil işi için m.5/2-e daha uygun olabilir]**; KVKK m.6/3-d (bir hakkın tesisi, kullanılması veya korunması) | Silinmiyor |
| Sistemi çalıştırmak, hataları ayıklamak ve güvenliğini sağlamak | KVKK m.5/2-f (meşru menfaat) **[AÇIK: teyit edin; müvekkil işi için m.5/2-e daha uygun olabilir]** | **[AÇIK: saklama süresi]** |

## Verilerinizi nasıl topluyoruz

Elektronik ortamda (e-posta, belge yükleme, kamuya açık kayıtlarda arama) ve gerektiğinde fiziki belgelerden:

- E-posta ile belge alımı, dosyalama ve çıkar çatışması kontrolü: doğrudan sizden, müvekkilimizin bize ilettiği belgelerden
- Taranmış yabancı belgelerin metne çevrilmesi ve tercümesi: müvekkilimizin bize ilettiği belgelerden
- Yönetici ve ortakların DD taraması: kamuya açık kaynaklardan
- DD raporu ve hukuki mütalaa taslakları: müvekkilimizin bize ilettiği belgelerden
- Taslakların müvekkile e-postayla gönderilmesi: sistemlerimizin kayıtlarından
- Sistemin işletilmesi: sistemlerimizin kayıtlarından

## Verileriniz kimlere ve hangi amaçla aktarılıyor

| Alıcı | Ne için | Rolü | Ülke | Ne aktarılıyor |
|---|---|---|---|---|
| OpenAI (API) | giriş ve taslak için dil modeli | hizmet sağlayıcı (veri işleyen) | ABD | maskelenmemiş |
| Anthropic (Claude API) | tarama ve taslak için dil modeli | hizmet sağlayıcı (veri işleyen) | ABD | maskelenmemiş |
| Google Gemini API (free tier) | OCR ve tercüme | kendi adına hareket eden kurum | ABD | maskelenmemiş |
| Google Workspace (Gmail, Drive) | e-posta ve dosya depolama | hizmet sağlayıcı (veri işleyen) | ABD | maskelenmemiş |
| Supabase (pgvector) | vektör veritabanı | hizmet sağlayıcı (veri işleyen) | Almanya | maskeli (maskeleme aracının tespit ettiği adlar ve kimlik numaraları yer tutucularla değiştirilmiş) |
| LangSmith (LangChain) | ajan izleme (istemler ve çıktılar) | **[AÇIK: rolü]** | ABD | maskelenmemiş |
| Brave Search API | kişi adıyla web araması | **[AÇIK: rolü]** | ABD | maskelenmemiş |
| Düsseldorf correspondent firm (fictional) | bazı dosyalarda birlikte çalıştığımız hukuk bürosu | ortak veri sorumlusu | Almanya | dosyaya göre |
| Müvekkillerimiz | hazırladığımız rapor ve görüşler | veri sorumlusu | müvekkilin ülkesi | rapor içeriği |

## Yurt dışına aktarım (KVKK m.9)

OpenAI (API) (ABD); Anthropic (Claude API) (ABD); Google Gemini API (free tier) (ABD); Google Workspace (Gmail, Drive) (ABD); Supabase (pgvector) (Almanya); LangSmith (LangChain) (ABD); Brave Search API (ABD). Bu aktarımlar KVKK m.9'daki araçlardan birine dayanır: **[AÇIK: her alıcı için standart sözleşme veya diğer uygun güvence]**. Maskeli metin de bizim için kişisel veridir; bu nedenle aynı kurallar uygulanır.

## Yapay zekâ kullanımı

Belgeleri sınıflandırmak, araştırma yapmak ve taslak hazırlamak için yapay zekâ sistemleri kullanıyoruz. **[AÇIK: hangi çıktıların gönderilmeden önce avukat tarafından okunduğunu doğru biçimde yazın; ankete göre bazı çıktılar incelenmeden gönderiliyor]** Hakkınızda yalnızca otomatik sistemlerle yapılan analiz sonucunda aleyhinize bir sonuç çıkmasına itiraz edebilirsiniz (KVKK m.11/1-g).

## Haklarınız (KVKK m.11)

Bize başvurarak; kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenmişse bilgi talep etme, işlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme, yurt içinde veya yurt dışında aktarıldığı üçüncü kişileri bilme, eksik veya yanlış işlenmişse düzeltilmesini isteme, KVKK m.7'deki şartlar çerçevesinde silinmesini veya yok edilmesini isteme, bu işlemlerin aktarıldığı üçüncü kişilere bildirilmesini isteme, münhasıran otomatik sistemlerle analiz sonucu aleyhinize bir sonucun ortaya çıkmasına itiraz etme ve kanuna aykırı işleme nedeniyle zarara uğramanız hâlinde zararın giderilmesini talep etme haklarına sahipsiniz.

Başvurunuzu yazılı olarak veya Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ'de sayılan yöntemlerle **[AÇIK: iletişim adresi]** adresine iletebilirsiniz. Başvurular en geç otuz gün içinde ücretsiz olarak sonuçlandırılır (KVKK m.13/2). Avukatlık Kanunu m.36'daki sır saklama yükümlülüğü, başka kişilere ait bilgilerin size verilmesini sınırlayabilir.

## AB'de bulunan kişiler

AB'de bulunan kişiler için ayrıca GDPR kapsamındaki bilgilendirme metni geçerlidir (03-privacy-notice.md).
