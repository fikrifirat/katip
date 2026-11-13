---
title: Katip Yerel
emoji: 🛡️
colorFrom: green
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: agpl-3.0
short_description: Turkish KVKK PII redaction that runs fully in your browser
models:
- f1k/katip-tr-name-tagger-tiny
- f1k/katip-tr-pii-berturk
tags:
- pii
- redaction
- kvkk
- turkish
- legal
- privacy
- webassembly
---

# Katip Yerel

Türkçe hukuk belgelerinde kişisel verileri (T.C. kimlik no, VKN, IBAN, telefon, e-posta, plaka,
adres, ad soyad, KVKK md. 6 özel nitelikli veriler) **tamamen tarayıcıda** bulur ve maskeler.
Belge hiçbir sunucuya yüklenmez; sayfanın güvenlik politikası başka bir adrese veri gönderilmesini engeller.

Turkish PII redaction for legal documents (PDF, scanned PDF, photos, Word, UYAP .udf, text),
running entirely client-side: Python rules in Pyodide, true PDF redaction with MuPDF (WASM),
OCR with Tesseract.js, and an optional 2.6 MB on-device name tagger
([katip-tr-name-tagger-tiny](https://huggingface.co/f1k/katip-tr-name-tagger-tiny)) via transformers.js.

- Drop a file and get the masked copy: scanning, masking and the leak check run automatically.
- Untick anything that should stay visible, or type a missed term; then download.
- 16 synthetic samples with answer keys; model, OCR, threshold, data types and mask style under "Gelişmiş ayarlar".
- "Görüş bildir" opens a ready e-mail for feedback.

Source: https://github.com/fikrifirat/katip · Licence: AGPL-3.0, with a commercial licence
available for use in products or real operations (contact fikrifirat@gmail.com or open an issue).
