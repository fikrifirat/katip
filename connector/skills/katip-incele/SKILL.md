---
name: katip-incele
description: Dilekçe ya da belge incelemesi (review and summarise a client document) with Katip's KVKK masking. Use when the user types /katip-incele or asks for a careful summary, review or error check of a document in their Katip folder.
argument-hint: "[odak / focus, e.g. zamanaşımı ve deliller]"
---

# Belgeyi incele ve özetle

Follow every rule of the `katip` skill (Katip tools only, placeholders kept as written, no other way to
open the file). Then:

1. `mask_file` with `file_id: "latest"`, unless the user named another document (then `list_files`
   first). Profile `ai`.
2. Write in Turkish unless the user writes in another language:
   * **Özet**: what the document is, who it is from and to (by role and placeholder), what it asks for.
   * **Talepler ve dayanaklar**: each claim with the evidence and the legal ground the document gives.
   * **Eksik ve hatalar**: missing facts, deadlines (süre, zamanaşımı), evidence, contradictions, wrong
     or missing statute references, formal defects. Mark which ones need checking.
   * **Öneriler**: concrete fixes, in order of importance.
3. Focus on what the user asked for: $ARGUMENTS
4. End with one line reminding them to check the result: Katip can miss a value and the analysis can be
   wrong.
