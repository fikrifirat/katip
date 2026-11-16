---
name: katip
description: Client-document work with KVKK masking (müvekkil belgesi, kişisel veri maskeleme). Use when the user types /katip, or asks Claude to read, summarise, review, translate or draft from a client document on their computer (dilekçe, sözleşme, bilirkişi raporu, epikriz, UYAP .udf, .docx, .pdf, scans, photos, .txt). Katip masks personal data on the computer before Claude sees it.
argument-hint: "[istek / request, e.g. son eklediğim dilekçeyi özetle]"
---


# Client-document work with Katip's KVKK masking

`/katip <request>`, for example `/katip son eklediğim dilekçeyi özetle` or `/katip summarise the lease`.
Answer in the language the user writes in (usually Turkish, with Turkish legal terms). The request is:
$ARGUMENTS

The KVKK Board's guide for lawyers (22 Sep 2026) recommends masking or anonymising client data before it
is shared with generative AI tools. Katip does that masking on the user's computer.

1. **Find the document with Katip only.** Never open, list or search client documents with Read, Grep,
   Glob, Bash or any other tool: file names are personal data too, and the plugin blocks those tools in
   the Katip folder. Call `list_files` (it hides name-like words), then `mask_file` with its `file_id`
   (or the path the user gave). Put the shortened name in `belge` so the user sees which document they
   approve. For "the file I just added" pass `file_id: "latest"`. If it says `pages > 1`, call it again
   with `page` = 2, 3, ...
2. **Work only with `masked_text`.** Keep placeholders such as `[AD SOYAD-1]`, `[T.C. KİMLİK NO-1]` and
   `[ADRES-2]` exactly as written, also with Turkish suffixes: `[AD SOYAD-1]'in`. Never guess or ask for
   the real value behind a placeholder. Refer to people by role (müvekkil, davacı, davalı, vekil) and
   placeholder.
3. **Profiles.** Default `ai` (Yapay zekâ ile paylaşım). `court` (Mahkemeye sunum) only for a copy that
   goes to court; `anon` (Tam anonim) when nothing identifying may remain (publication, an article, a
   training example).
4. **Matter.** Only when the user works on several documents of one case, ask once for a neutral label
   (a file number such as `2026/123`, never a client name) and pass it as `matter`, so the same person
   gets the same placeholder in every document. For a single document, leave it out.
5. **Final document with real names.** Offer it once. Call `restore_to_file` with your text and a file
   name such as `cevap-dilekcesi.docx` (.docx, .txt or .md; saved in the Katip folder). Tell the user the
   file name. Never open the restored file: you are not meant to see the real values.
6. **Masked copy for someone else** (bilirkişi, karşı taraf, meslektaş): `write_masked_copy`.
7. **Scans and photos** are read with OCR on the user's computer (`ocr` in the result). Say once that
   OCR can misread a letter, so unusual spellings should be checked.
8. **Attached files and typed names are not masked.** If the user attached a client document to the
   chat, tell them plainly it was already uploaded with their message, and suggest the Katip folder
   (`open_folder`) next time. If they type a real name, don't repeat it.
9. **Review.** Remind the user once to read your work before using it: Katip can miss a value and your
   legal analysis can be wrong. Cite statutes and precedents only as the document gives them, or say
   that they need checking.
10. **Errors.** If `mask_file` fails, explain why in one or two plain sentences and suggest the Katip app
    (https://fikrifirat.github.io/katip). Never fall back to reading the file another way, and never ask
    the user to paste the text.
