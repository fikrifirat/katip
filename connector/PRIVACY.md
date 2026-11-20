# Katip Kalkan privacy policy

Last updated: 14 November 2026. Applies to Katip Kalkan 0.3.5 and later (Claude plugin and Claude
Desktop extension). Contact: fikrifirat@gmail.com, or open an issue at https://github.com/fikrifirat/katip/issues
(never post real personal data there).

How all of Katip handles data, and the KVKK context for lawyers: [../PRIVACY.md](../PRIVACY.md)
([Türkçe](../PRIVACY.tr.md)).

## Summary

Katip Kalkan runs on your computer and collects no data. The author receives nothing: no documents,
no masked text, no usage statistics, no crash reports.

## What it processes

The files you ask Claude to open with `mask_file` or `write_masked_copy`, inside the folders you allow:
your case folder (the one you pick in the settings; `Documents/katip-documents` if you pick none), its
subfolders, and Downloads. To find a document, `list_files` reads file and folder names in those folders
on your computer and returns shortened names to Claude. They are read and masked on your
computer. Only the masked text, with placeholders such as `[AD SOYAD-1]`, is returned to Claude.

## What it stores, where, and for how long

* **Placeholder map** (placeholder → real value, per matter): on your computer in `~/.katip/vault`,
  encrypted with AES-256-GCM. The key is in the macOS Keychain, or in `~/.katip/key`, readable only by
  your user account. File names are keyed hashes, so they don't reveal the matter. Maps are deleted
  after 30 days (`KATIP_VAULT_DAYS`) or at once with the `forget_matter` tool. Without the
  `cryptography` package the map is kept in memory only and lost when Claude closes.
* **Restored documents** (`restore_to_file`): written next to the document you masked (or into your case folder), only inside the allowed folders, readable only by you.
* **Masked copies** (`write_masked_copy`): written next to the original.

## What it sends, and to whom

* **To the author or any third party:** nothing.
* **To Claude:** the masked text and short file names with name-like words hidden. Anthropic processes
  them under its own terms and privacy policy. Masked text is pseudonymised, which under KVKK is still
  personal data; the law firm using Katip decides whether sending it to Claude is lawful.
* **Network:** on first start only, if `uv` is installed, uv downloads pinned open-source packages
  (katip-mask, onnxruntime, numpy, cryptography, pymupdf, rapidocr) from PyPI and, if missing, Python 3.12
  from uv's Python builds. If you set `KATIP_MODEL=base` or `mini`, that model is downloaded once from
  Hugging Face at a pinned commit. The Claude Code plugin also downloads the PaddleOCR text recogniser
  once from Hugging Face, at a pinned commit, the first time you open a scan or photo
  (`KATIP_OCR_DOWNLOAD=0` turns this off; the `.mcpb` already contains it). These requests contain no document data. Set `KATIP_AUTO_DEPS=0` to turn
  the package downloads off.
* **Precedent search (`emsal_ara`), off by default:** only if you turn on the "Precedent search" setting
  (or `KATIP_EMSAL_ONLINE=1`) and Claude calls it, short keyword queries such as
  `kira tespit hakkaniyet` go to the Ministry of Justice's public decision search (bedesten.adalet.gov.tr),
  and the full text of the decisions found is fetched from there. A query may hold only lowercase letters;
  Katip refuses it, before sending anything, if a word has a capital, a digit or a sign, or is part of a
  value Katip masked in that matter. The document, its masked text and any quote from it are never sent.
  Every request is listed in `~/.katip/emsal/requests.log`. While the setting is off (the
  default), Katip makes no network requests at all.
  Katip makes no other network requests. `mevzuat_bak` (statutes) works offline.
* **Grades (`geri_bildirim`):** kept on your computer in `~/.katip/emsal/grades.jsonl`: the public decision
  id, the query words, your grade and note. They reach the author only if you send that file yourself
  (`katip-kalkan feedback --export grades.json` writes it so you can read it first).

## What Katip can't protect

A file you attach to the chat is uploaded to Anthropic with your message, before any tool runs. Katip
can't mask it. Put client files in the Katip folder instead.

## Your rights

Under KVKK and the GDPR, the law firm using Katip is the data controller for its clients' data. To
exercise rights over client data, contact the firm. To delete everything Katip stores, use
`forget_matter` or delete the `~/.katip` folder. For questions about Katip itself, open an issue.

## ChatGPT relay (separate, not part of the plugin)

The ChatGPT connector is a relay server (see [CHATGPT.md](CHATGPT.md)). It never receives an original
document or a real value:

* **Share codes.** Your device (the Katip web app or `katip-kalkan share`) masks the document, encrypts the
  masked text with a one-time key and uploads only the ciphertext. The key is in the share code you paste into
  ChatGPT. The relay keeps the ciphertext in memory only and deletes it after one read or 15 minutes.
* **Precedent search.** Only short lowercase keyword queries go from the relay to the Ministry of Justice's
  decision search. The optional ranking context (`baglam`) is masked text, used in memory and not stored.
* **Verdicts.** The gavel button stores the decision id, the query words, the rank and your verdict on the
  relay, with no account, name or note.
* **Logs** hold request method, path, status and size, never content, codes or keys.

Masked text is still personal data in pseudonymised form, and ChatGPT receives it. No public relay is operated
yet; this section will name the host and region before one is.
