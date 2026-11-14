# Katip Kalkan privacy policy

Last updated: 14 November 2026. Applies to Katip Kalkan 0.3.5 and later (Claude plugin and Claude
Desktop extension). Contact: open an issue at https://github.com/fikrifirat/katip/issues.

## Summary

Katip Kalkan runs on your computer and collects no data. The author receives nothing: no documents,
no masked text, no usage statistics, no crash reports.

## What it processes

The files you ask Claude to open with `mask_file` or `write_masked_copy`, inside your Katip folder
(`Documents/katip-documents` by default, or the folder you pick). They are read and masked on your
computer. Only the masked text, with placeholders such as `[AD SOYAD-1]`, is returned to Claude.

## What it stores, where, and for how long

* **Placeholder map** (placeholder → real value, per matter): on your computer in `~/.katip/vault`,
  encrypted with AES-256-GCM. The key is in the macOS Keychain, or in `~/.katip/key`, readable only by
  your user account. File names are keyed hashes, so they don't reveal the matter. Maps are deleted
  after 30 days (`KATIP_VAULT_DAYS`) or at once with the `forget_matter` tool. Without the
  `cryptography` package the map is kept in memory only and lost when Claude closes.
* **Restored documents** (`restore_to_file`): written only into your Katip folder, readable only by you.
* **Masked copies** (`write_masked_copy`): written next to the original.

## What it sends, and to whom

* **To the author or any third party:** nothing.
* **To Claude:** the masked text and short file names with name-like words hidden. Anthropic processes
  them under its own terms and privacy policy. Masked text is pseudonymised, which under KVKK is still
  personal data; the law firm using Katip decides whether sending it to Claude is lawful.
* **Network:** on first start only, if `uv` is installed, uv downloads pinned open-source packages
  (onnxruntime, numpy, cryptography, pymupdf, rapidocr) from PyPI and, if missing, Python 3.12 from
  uv's Python builds. These requests contain no document data. Set `KATIP_AUTO_DEPS=0` to turn them off.
  Katip makes no other network requests.

## What Katip can't protect

A file you attach to the chat is uploaded to Anthropic with your message, before any tool runs. Katip
can't mask it. Put client files in the Katip folder instead.

## Your rights

Under KVKK and the GDPR, the law firm using Katip is the data controller for its clients' data. To
exercise rights over client data, contact the firm. To delete everything Katip stores, use
`forget_matter` or delete the `~/.katip` folder. For questions about Katip itself, open an issue.

## ChatGPT relay (separate, not part of the plugin)

The optional `katip-kalkan share` command sends text that your computer has already masked and encrypted
with a one-time key to a relay you choose. The relay keeps it in memory only and deletes it after one
read or 15 minutes. It logs request method, path, status and size, never content, codes or keys. No
public relay is operated yet; this section will name the host and region before one is.
