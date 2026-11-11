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

- 16 synthetic sample documents with answer keys: see recall, precision, misses and false alarms live.
- Switch the detection model, OCR model, confidence threshold and data types.
- Before/after view, leak check on the output, report a mistake by e-mail.

Source: https://github.com/fikrifirat/katip · Licence: AGPL-3.0, with a commercial licence
available for use in products or real operations (contact fikrifirat@gmail.com or open an issue).
