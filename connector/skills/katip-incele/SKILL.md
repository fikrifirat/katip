---
name: katip-incele
description: Dilekçe ya da belge incelemesi (review and summarise a client document) with Katip's KVKK masking. Use when the user types /katip-incele or asks for a careful summary, review or error check of a client document on their computer.
argument-hint: "[belge, odak / document, focus — e.g. Yılmaz kira sözleşmesi, zamanaşımı]"
---

# Belgeyi incele ve özetle

Follow every rule of the `katip` skill (Katip tools only, placeholders kept as written, no other way to
open the file). Then:

1. Find the document as rule 1 of the `katip` skill says: the request names it ("Yılmaz kira
   sözleşmesi", "2026/123 bilirkişi raporu", "son indirdiğim"), so call `list_files` with those words as
   `ara`, or use `file_id: "latest"` when it says the newest or names nothing. Ask if several match. Then
   `mask_file`, profile `ai`.
2. Write in Turkish unless the user writes in another language:
   * **Özet**: what the document is, who it is from and to (by role and placeholder), what it asks for.
   * **Talepler ve dayanaklar**: each claim with the evidence and the legal ground the document gives.
   * **Eksik ve hatalar**: missing facts, deadlines (süre, zamanaşımı), evidence, contradictions, wrong
     or missing statute references, formal defects. Mark which ones need checking.
   * **Öneriler**: concrete fixes, in order of importance.
3. The request (document, then what to focus on): $ARGUMENTS
4. End with one line reminding them to check the result: Katip can miss a value and the analysis can be
   wrong.
