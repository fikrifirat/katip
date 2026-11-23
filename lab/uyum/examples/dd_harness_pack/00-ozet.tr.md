# Özet ve yapılacaklar

**Sistem:** Örnek Hukuk agent harness · **Veri sorumlusu:** Örnek Hukuk Bürosu · **Anket tarihi:** 2026-11-23

> **Avukat incelemesi için TASLAK.** Katip bu metni yukarıdaki ankete göre hazırladı. Hukuki görüş değildir; sistemin KVKK'ya, GDPR'a veya AB Yapay Zekâ Tüzüğü'ne uygun olduğu anlamına gelmez. **[AÇIK: ...]** ile işaretli yerler eksik bilgidir.

## Önce bunlar

Önem ve verinin hassasiyetine göre sıralandı.

1. **Ceza verileri için yasal dayanak gösterilmeli (GDPR m.10)** *(GDPR Art. 10)*
2. **AB müvekkilleri için SCC hazırlanmalı (Türkiye için yeterlilik kararı yok)** *(GDPR Art. 46(2)(c); Decision (EU) 2021/914)*
3. **Canlıya almadan önce DPIA yapılmalı** *(GDPR Arts. 35(1), 35(7), 36; WP248 rev.01)*
4. **Yurt dışına aktarım (KVKK m.9): Anthropic (Claude API), Mistral AI, Hetzner** *(KVKK m.9; Regulation on transfers abroad (10 Jul 2024))*
5. **Mistral AI ile veri işleme sözleşmesi yapılmalı** *(GDPR Art. 28(3))*

## Tüm bulgular

5 yapılmalı, 1 risk, 8 açık soru, 9 not. Ayrıntılı açıklamalar İngilizce belgelerde (00-overview.md ve ilgili belge).

### Hangi hukuk, neye uygulanıyor

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Açık soru | GDPR size doğrudan uygulanıyor mu (m.3/2)? | GDPR Arts. 3(2), 27; EDPB Guidelines 3/2018 | 00, 01, 03, 07 |
| Not | DPO zorunlu görünmüyor; gerekçe yazılmalı | GDPR Art. 37(1)(c), Recital 91 | 00 |

### Özel nitelikli ve ceza verileri

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | Ceza verileri için yasal dayanak gösterilmeli (GDPR m.10) | GDPR Art. 10 | 01, 02, 10 |
| Not | Yaptırım listesi veya devam eden dava KVKK m.6 kapsamında mı? | KVKK m.5, m.6/1 | 01 |

### Hizmet sağlayıcılar ve sözleşmeler

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | Mistral AI ile veri işleme sözleşmesi yapılmalı | GDPR Art. 28(3) | 04 |
| Risk | Anthropic (Claude API) maskeli metinde de olay ayrıntılarını görüyor | GDPR Arts. 9, 25, 32; Recital 26 | 02, 09 |
| Açık soru | Mistral AI gönderilen verilerle model eğitiyor mu? | GDPR Arts. 5(1)(b), 28(3)(a) | 04 |
| Açık soru | Anthropic (Claude API) istem ve çıktıları ne kadar saklıyor? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |
| Açık soru | Mistral AI istem ve çıktıları ne kadar saklıyor? | GDPR Arts. 5(1)(e), 28(3)(g) | 04, 06 |

### Yurt dışına aktarım

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | AB müvekkilleri için SCC hazırlanmalı (Türkiye için yeterlilik kararı yok) | GDPR Art. 46(2)(c); Decision (EU) 2021/914 | 05, 04 |
| Yapılmalı | Yurt dışına aktarım (KVKK m.9): Anthropic (Claude API), Mistral AI, Hetzner | KVKK m.9; Regulation on transfers abroad (10 Jul 2024) | 05 |
| Not | Anthropic (Claude API): AB müvekkil verisinin ileri aktarımı | GDPR Art. 44; Decision (EU) 2021/914 | 05 |

### Güvenlik

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Yapılmalı | Canlıya almadan önce DPIA yapılmalı | GDPR Arts. 35(1), 35(7), 36; WP248 rev.01 | 02 |
| Açık soru | Güvenlik: Yedekleme? | GDPR Art. 32(1)(c) | 09 |
| Açık soru | Güvenlik: İhlal sorumlusu kişi? | GDPR Arts. 33-34 | 09 |
| Açık soru | Güvenlik: Çok faktörlü giriş? | GDPR Art. 32(1)(b) | 09 |
| Açık soru | Güvenlik: Yedekten geri yükleme testi? | GDPR Art. 32(1)(c)-(d) | 09 |
| Not | Maskeli metin anonim değil, takma adlıdır | GDPR Art. 4(5), Recital 26; CJEU C-413/23 P | 02, 03, 09 |
| Not | 'eu' maskeleme profili beta: tek başına geçen adlar zayıf nokta | GDPR Arts. 25, 32(1)(a) | 09 |

### Aydınlatma ve başvurular

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Not | 'Drafting DD reports and legal opinions': veriler kişinin kendisinden alınmıyor (GDPR m.14) | GDPR Art. 14(3), 14(5) | 03 |
| Not | 'Client intake and conflict check': veriler kişinin kendisinden alınmıyor (GDPR m.14) | GDPR Art. 14(3), 14(5) | 03 |
| Not | 'DD screening of target companies and their people': veriler kişinin kendisinden alınmıyor (GDPR m.14) | GDPR Art. 14(3), 14(5) | 03 |

### AB Yapay Zekâ Tüzüğü

| Tür | Bulgu | Dayanak | Belge |
|---|---|---|---|
| Not | Yapay zekâ okuryazarlığı | AI Act Art. 4 | 10, 09 |

## Belgeler

İngilizce belgeler AB müvekkilleri ve denetim otoriteleri içindir. Türkçe belgeler: [kişisel veri işleme envanteri](01-envanter.tr.md) ve [aydınlatma metni](03-aydinlatma-metni.tr.md).
