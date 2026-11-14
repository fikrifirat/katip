---
title: Katip Mask
emoji: 🛡️
colorFrom: green
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: agpl-3.0
short_description: Turkish KVKK PII redaction that runs fully in your browser
models:
- f1k/katip-mask-nano
- f1k/katip-mask-base
tags:
- pii
- redaction
- kvkk
- turkish
- legal
- privacy
- webassembly
- gdpr
- anonymization
- pseudonymization
- de-identification
- data-masking
- personal-data
- legal-nlp
- lawyer
- avukat
- kisisel-veri
- anonimlestirme
- maskeleme
---

# Katip Mask

Türkçe hukuk belgelerinde kişisel verileri (T.C. kimlik no, VKN, IBAN, telefon, e-posta, plaka,
adres, ad soyad, KVKK md. 6 özel nitelikli veriler) **tamamen tarayıcıda** bulur ve maskeler.
Belge hiçbir sunucuya yüklenmez; sayfanın güvenlik politikası başka bir adrese veri gönderilmesini engeller.

Turkish PII redaction for legal documents (PDF, scanned PDF, photos, Word, UYAP .udf, text),
running entirely client-side: Python rules in Pyodide, true PDF redaction with MuPDF (WASM),
OCR with Tesseract.js and PaddleOCR, and an on-device name model
([Katip Mask Nano](https://huggingface.co/f1k/katip-mask-nano), 2.5 MB, Turkish and foreign client names) via transformers.js;
the 110 MB [Katip Mask Base](https://huggingface.co/f1k/katip-mask-base) is one click away under "Gelişmiş ayarlar".

- Drop a file and get the masked copy: scanning, masking and the leak check run automatically.
- Untick anything that should stay visible, or type a missed term; then download.
- 80 synthetic samples (16 document types, 5 each) with answer keys; model, OCR, threshold, data types and mask style under "Gelişmiş ayarlar".
- "Görüş bildir" opens a ready e-mail for feedback.

Source: https://github.com/fikrifirat/katip · Licence: AGPL-3.0, with a commercial licence
available for use in products or real operations (contact fikrifirat@gmail.com or open an issue).
