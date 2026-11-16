---
name: katip-taslak
description: Cevap dilekçesi, itiraz ya da yazı taslağı (draft a reply or letter) from a client document with Katip's KVKK masking, optionally saved with the real names as a Word file. Use when the user types /katip-taslak or asks for a draft based on a client document on their computer.
argument-hint: "[belge, taslak türü / document, kind — e.g. son UYAP evrakı, cevap dilekçesi]"
---

# Taslak hazırla

Follow every rule of the `katip` skill (Katip tools only, placeholders kept as written, no other way to
open the file). Then:

1. Find the document as rule 1 of the `katip` skill says: the request names it ("Yılmaz kira
   sözleşmesi", "2026/123 bilirkişi raporu", "son indirdiğim"), so call `list_files` with those words as
   `ara`, or use `file_id: "latest"` when it says the newest or names nothing. Ask if several match. Then
   `mask_file`, profile `ai`.
2. Write the draft the user asked for (document, then the kind of draft): $ARGUMENTS. Use the usual Turkish structure of that document
   (for a petition: mahkeme, taraflar, konu, açıklamalar, hukuki nedenler, deliller, sonuç ve istem).
   Keep every placeholder exactly as written. Don't invent facts, dates, statute numbers or precedents:
   mark gaps as `[…]` for the lawyer to fill in.
3. Ask whether to save it with the real names. If yes, call `restore_to_file` with a file name such as
   `cevap-dilekcesi.docx` (saved next to the source document) and tell the user the file name. Never open that file.
4. Remind them once to review the draft before filing it.
