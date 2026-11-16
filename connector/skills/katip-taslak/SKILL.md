---
name: katip-taslak
description: Cevap dilekçesi, itiraz ya da yazı taslağı (draft a reply or letter) from a client document with Katip's KVKK masking, optionally saved with the real names as a Word file. Use when the user types /katip-taslak or asks for a draft based on a document in their Katip folder.
argument-hint: "[taslak türü / kind of draft, e.g. cevap dilekçesi]"
---

# Taslak hazırla

Follow every rule of the `katip` skill (Katip tools only, placeholders kept as written, no other way to
open the file). Then:

1. `mask_file` with `file_id: "latest"`, unless the user named another document (then `list_files`
   first). Profile `ai`.
2. Write the draft the user asked for: $ARGUMENTS. Use the usual Turkish structure of that document
   (for a petition: mahkeme, taraflar, konu, açıklamalar, hukuki nedenler, deliller, sonuç ve istem).
   Keep every placeholder exactly as written. Don't invent facts, dates, statute numbers or precedents:
   mark gaps as `[…]` for the lawyer to fill in.
3. Ask whether to save it with the real names. If yes, call `restore_to_file` with a file name such as
   `cevap-dilekcesi.docx` and tell the user the file name. Never open that file.
4. Remind them once to review the draft before filing it.
