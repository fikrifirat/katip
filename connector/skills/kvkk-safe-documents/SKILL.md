---
name: kvkk-safe-documents
description: Use whenever the user asks Claude to read, summarise, review, translate or draft from a client document on their computer (dilekçe, sözleşme, bilirkişi raporu, epikriz, UYAP .udf, .docx, .pdf, .txt). Masks personal data locally with Katip before Claude sees it.
---

# KVKK-safe document work with Katip

Client documents contain personal data that must not be sent to an AI provider unmasked
(KVKK m.4, m.9 and the KVKK lawyers' guide of 22 Sep 2026).

1. Never open a client document with Read, Bash, cat or any other tool. Call the Katip
   `mask_file` tool with the file's absolute path instead, and work only with the
   `masked_text` it returns. If it says `pages > 1`, call it again with `page` = 2, 3, ...
2. Ask the user for a neutral matter label (a file number such as `2026/123`, not a client
   name) and pass it as `matter`, so all documents of one case share placeholders.
3. Keep placeholders such as `[AD SOYAD-1]`, `[T.C. KİMLİK NO-1]` and `[ADRES-2]` exactly as
   written, including in Turkish suffixes: write `[AD SOYAD-1]'in`, not a guessed name.
4. Never ask the user for the real values behind a placeholder.
5. When the user wants the final text with real names, call `restore_to_file` with your text
   and an output path. Tell the user the path. You will not see the real values, and that is
   intended.
6. If the user wants to send a masked copy to someone, use `write_masked_copy`.
7. If `mask_file` fails (scanned PDF, unsupported type), tell the user to open the file in the
   Katip app, which runs OCR on their computer. Do not fall back to reading the file directly.
