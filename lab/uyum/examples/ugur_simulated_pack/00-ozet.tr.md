# Özet ve yapılacaklar

**Sistem:** Uğur Hukuk ajan sistemi (simulated) · **Veri sorumlusu:** Uğur Hukuk Bürosu (simulated) · **Anket tarihi:** 2026-11-23

> **Avukat incelemesi için TASLAK.** Katip bu metni yukarıdaki ankete göre hazırladı. Hukuki görüş değildir; sistemin KVKK'ya, GDPR'a veya AB Yapay Zekâ Tüzüğü'ne uygun olduğu anlamına gelmez. **[AÇIK: ...]** ile işaretli yerler eksik bilgidir.

## Önce bunlar

Önem ve verinin hassasiyetine göre sıralandı.

1. **Google Gemini API (free tier)'e müvekkil verisi gönderilmesi durdurulmalı** *(GDPR Arts. 28(1), 28(3), 28(10), 9(1); Avukatlık Kanunu m.36)*
2. **'Emailing drafts to clients': saklama süresi sınırsız** *(GDPR Arts. 5(1)(e), 13(2)(a); KVKK m.7)*
3. **'DD screening of officers and shareholders' kişilere risk etiketi veriyor** *(GDPR Arts. 4(4), 5(1)(d), 15, 22)*
4. **'Sending agent' avukat okumadan dışarı çıktı gönderiyor** *(GDPR Arts. 5(1)(d), 22, 25(1), 32(1)(b), 33)*
5. **Anthropic (Claude API) maskelenmemiş hassas veri alıyor** *(GDPR Arts. 5(1)(c), 25, 32(1)(a))*

## Tüm bulgular

17 yapılmalı, 9 risk, 18 açık soru, 15 not. Ayrıntılı açıklamalar İngilizce belgelerde (00-overview.md ve ilgili belge).

### Hangi hukuk, neye uygulanıyor

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | AB temsilcisi atanmalı (GDPR m.27) | GDPR Art. 27 | 00, 01, 03 |
| Açık soru | Yılda kaç kişinin verisi işleniyor? | GDPR Arts. 35(3), 37(1); Recital 91 | 02 |
| Not | DPO zorunlu görünmüyor; gerekçe yazılmalı | GDPR Art. 37(1)(c), Recital 91 | 00 |

### Hukuki sebepler

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | 'Email intake, filing and conflict check' için hukuki sebep ayrılmalı (sözleşmenin tarafı olmayan kişiler) | GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019 | 01, 03, 11 |
| Yapılmalı | 'Emailing drafts to clients' için hukuki sebep ayrılmalı (sözleşmenin tarafı olmayan kişiler) | GDPR Art. 6(1)(b), 6(1)(f); EDPB Guidelines 2/2019 | 01, 03, 11 |
| Yapılmalı | 'Operating the system' için meşru menfaat testi yazılmalı | GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21 | 01, 02, 11 |
| Yapılmalı | 'DD screening of officers and shareholders' için meşru menfaat testi yazılmalı | GDPR Art. 6(1)(f), Recital 47; CJEU C-252/21 | 01, 02, 11 |

### Özel nitelikli ve ceza verileri

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | Ceza verileri için yasal dayanak gösterilmeli (GDPR m.10) | GDPR Art. 10 | 01, 02, 10 |
| Yapılmalı | 'Operating the system': özel nitelikli veri için şart (GDPR m.9, KVKK m.6/3) | GDPR Art. 9; KVKK m.6/3, m.6/4 | 01, 02, 09 |
| Yapılmalı | Ceza verisi için KVKK m.6/3 şartı | KVKK m.6/1, m.6/3-d, m.6/4 | 01, 09 |
| Not | Vefat etmiş kişilerin verileri | GDPR Recital 27 | 02 |
| Not | Yaptırım listesi veya devam eden dava KVKK m.6 kapsamında mı? | KVKK m.5, m.6/1 | 01 |

### Hizmet sağlayıcılar ve sözleşmeler

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | Düsseldorf correspondent firm (fictional) ile ortak veri sorumluluğu düzenlemesi yapılmalı | GDPR Art. 26(1)-(2) | 04, 03 |
| Yapılmalı | Her müvekkil için veri sorumlusu mu veri işleyen mi olduğunuz netleşmeli | GDPR Arts. 4(7)-(8), 28(3), 30(2); EDPB Guidelines 07/2020 | 04, 01, 07 |
| Yapılmalı | Google Gemini API (free tier)'e müvekkil verisi gönderilmesi durdurulmalı | GDPR Arts. 28(1), 28(3), 28(10), 9(1); Avukatlık Kanunu m.36 | 04, 02 |
| Risk | Supabase (pgvector) maskeli metinde de olay ayrıntılarını görüyor | GDPR Arts. 9, 25, 32; Recital 26 | 02, 09 |
| Risk | Anthropic (Claude API) maskelenmemiş hassas veri alıyor | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Risk | Google Gemini API (free tier) maskelenmemiş hassas veri alıyor | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Risk | Google Workspace (Gmail, Drive) maskelenmemiş hassas veri alıyor | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Risk | LangSmith (LangChain) maskelenmemiş hassas veri alıyor | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Risk | OpenAI (API) maskelenmemiş hassas veri alıyor | GDPR Arts. 5(1)(c), 25, 32(1)(a) | 02, 09 |
| Açık soru | Supabase (pgvector) ile veri işleme sözleşmesi var mı? | GDPR Art. 28(3) | 04 |
| Açık soru | Brave Search API veri işleyen mi veri sorumlusu mu? | GDPR Arts. 4(7)-(8), 28 | 04 |
| Açık soru | LangSmith (LangChain) veri işleyen mi veri sorumlusu mu? | GDPR Arts. 4(7)-(8), 28 | 04 |
| Açık soru | Supabase (pgvector) gönderilen verilerle model eğitiyor mu? | GDPR Arts. 5(1)(b), 28(3)(a) | 04 |
| Açık soru | Anthropic (Claude API) istem ve çıktıları ne kadar saklıyor? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Açık soru | Google Gemini API (free tier) istem ve çıktıları ne kadar saklıyor? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Açık soru | OpenAI (API) istem ve çıktıları ne kadar saklıyor? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Açık soru | Supabase (pgvector) istem ve çıktıları ne kadar saklıyor? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |

### Yurt dışına aktarım

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | AB müvekkilleri için SCC hazırlanmalı (Türkiye için yeterlilik kararı yok) | GDPR Art. 46(2)(c); Decision (EU) 2021/914 | 05, 04 |
| Yapılmalı | Yurt dışına aktarım (KVKK m.9): OpenAI (API), Anthropic (Claude API), Google Gemini API (free tier), Google Workspace (Gmail, Drive), Supabase (pgvector), LangSmith (LangChain), Brave Search API | KVKK m.9; Regulation on transfers abroad (10 Jul 2024) | 05 |
| Açık soru | Brave Search API için hangi aktarım aracı kullanılıyor? | GDPR Arts. 45-46 | 05 |
| Not | Anthropic (Claude API): AB müvekkil verisinin ileri aktarımı | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Not | Google Gemini API (free tier): AB müvekkil verisinin ileri aktarımı | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Not | Google Workspace (Gmail, Drive): AB müvekkil verisinin ileri aktarımı | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Not | LangSmith (LangChain): AB müvekkil verisinin ileri aktarımı | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Not | OpenAI (API): AB müvekkil verisinin ileri aktarımı | GDPR Art. 44; Decision (EU) 2021/914 | 05 |
| Not | Supabase (pgvector): AB'de sunucu, AB dışı ana şirket | GDPR Arts. 28(2), 44, 48; EDPB Guidelines 05/2021 | 05 |

### Ajanlar ve insan kontrolü

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Risk | 'DD screening of officers and shareholders' kişilere risk etiketi veriyor | GDPR Arts. 4(4), 5(1)(d), 15, 22 | 02, 10 |
| Risk | 'Sending agent' avukat okumadan dışarı çıktı gönderiyor | GDPR Arts. 5(1)(d), 22, 25(1), 32(1)(b), 33 | 02, 03, 07, 09 |

### Güvenlik

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | Canlıya almadan önce DPIA yapılmalı | GDPR Arts. 35(1), 35(7), 36; WP248 rev.01 | 02 |
| Yapılmalı | Güvenlik: yedekten geri yükleme testi eklenmeli | GDPR Art. 32(1)(c)-(d) | 09 |
| Yapılmalı | Ortak hesaplar ve açıkta API anahtarları kaldırılmalı | GDPR Art. 32(1)(b), 32(4) | 09 |
| Risk | Bulut modelleri ham metni görüyor | GDPR Arts. 25, 32(1)(a) | 02, 09 |
| Açık soru | AB belgeleri hangi maskeleme profiliyle işleniyor? | GDPR Art. 32(1)(a) | 09 |
| Açık soru | Güvenlik: Depolamada şifreleme? | GDPR Art. 32(1)(a) | 09 |
| Açık soru | Güvenlik: Çok faktörlü giriş? | GDPR Art. 32(1)(b) | 09 |
| Not | Maskeli metin anonim değil, takma adlıdır | GDPR Art. 4(5), Recital 26; CJEU C-413/23 P | 02, 03, 09 |

### Saklama süreleri

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | 'Emailing drafts to clients': saklama süresi sınırsız | GDPR Arts. 5(1)(e), 13(2)(a); KVKK m.7 | 06, 01 |
| Açık soru | 'OCR and translation of scanned foreign documents' verileri ne kadar saklanıyor? | GDPR Arts. 5(1)(e), 30(1)(f) | 01, 06 |
| Açık soru | 'Operating the system' verileri ne kadar saklanıyor? | GDPR Arts. 5(1)(e), 30(1)(f) | 01, 06 |

### Aydınlatma ve başvurular

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Açık soru | Kişisel veri iletişim adresi | GDPR Arts. 13(1)(a), 30(1)(a); KVKK m.10/1-a | 01, 03 |
| Not | 'Drafting DD reports and legal opinions': veriler kişinin kendisinden alınmıyor (GDPR m.14) | GDPR Art. 14(3), 14(5) | 03 |
| Not | 'Email intake, filing and conflict check': veriler kişinin kendisinden alınmıyor (GDPR m.14) | GDPR Art. 14(3), 14(5) | 03 |
| Not | 'OCR and translation of scanned foreign documents': veriler kişinin kendisinden alınmıyor (GDPR m.14) | GDPR Art. 14(3), 14(5) | 03 |
| Not | 'DD screening of officers and shareholders': veriler kişinin kendisinden alınmıyor (GDPR m.14) | GDPR Art. 14(3), 14(5) | 03 |

### AB Yapay Zekâ Tüzüğü

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Açık soru | Herhangi bir etiket kişinin suç işleme olasılığını mı tahmin ediyor? (AI Act m.5/1-d) | AI Act Art. 5(1)(d); GDPR Art. 4(4) | 10, 02 |
| Açık soru | Sistemi kendi adınızla başkalarına sunacak mısınız? | AI Act Arts. 3(3), 50 | 10 |
| Not | Yapay zekâ okuryazarlığı | AI Act Art. 4 | 10, 09 |

## Belgeler

İngilizce belgeler AB müvekkilleri ve denetim otoriteleri içindir. Türkçe belgeler: [kişisel veri işleme envanteri](01-envanter.tr.md) ve [aydınlatma metni](03-aydinlatma-metni.tr.md).
