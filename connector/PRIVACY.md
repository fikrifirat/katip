# Katip Kalkan privacy policy

Last updated: 13 November 2026. Contact: open an issue at https://github.com/fikrifirat/katip/issues.

## Local connector (Claude plugin and Claude Desktop extension)

* **What it collects:** nothing. Katip runs on your computer and makes no network requests.
* **What it processes:** the files you ask the AI to open with `mask_file` or `write_masked_copy`.
  They are read on your computer, masked on your computer, and only the masked text is returned
  to the AI app you use.
* **What it stores:** the placeholder map for each matter (for example `[AD SOYAD-1]` and the
  real name), encrypted with AES-256-GCM in `~/.katip/vault`. The key is in your system
  keychain or in `~/.katip/key`, readable only by you. Maps are deleted after 30 days, or
  sooner with `forget_matter`. Restored documents are written only where you tell Katip to.
* **Third parties:** none. The AI app you use (Claude) receives the masked text under its own
  terms.

## Relay (ChatGPT connector)

* **What it receives:** text that your computer has already masked and encrypted with a one-time
  key. The relay never receives the original file, real names, or the placeholder map.
* **Retention:** kept in memory only, deleted after it is read once or after 15 minutes,
  whichever comes first. It is never written to disk.
* **Logs:** request method, path, status code and size. No document content, share codes or keys.
* **Third parties and location:** hosted by Katip. The hosting region will be stated here before
  public launch.

## Your rights

Under KVKK, the law firm using Katip is the data controller for its clients' data. To exercise
rights over client data, contact the firm. For questions about Katip itself, open an issue.
