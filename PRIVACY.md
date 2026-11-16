# How Katip processes data

**English** · [Türkçe](PRIVACY.tr.md)

Last updated: 16 November 2026. This statement covers the Katip web app (fikrifirat.github.io/katip and the
Hugging Face Space), the `katip-mask` packages for Python and JavaScript, and the Katip Kalkan connector for
Claude. Contact: [GitHub issues](https://github.com/fikrifirat/katip/issues). It will move to the author's own
site later; this file stays as a copy.

## In short

Katip finds personal data in Turkish documents and masks it **on your own computer**. The author runs no
server that receives your documents, and Katip has no accounts, analytics, telemetry or crash reporting.
Masking reduces what you send to an AI provider. It does not make that sending lawful by itself, and it can
miss values, so you still review the output.

## What each part does with your data

| | Where documents are processed | What leaves your computer | What is stored |
|---|---|---|---|
| **Web app** | In your browser tab | Nothing. The page's Content-Security-Policy blocks sending data to other addresses. You download the masked copy yourself. | Nothing. Closing the tab discards the document. |
| **katip-mask (Python, npm)** | In your own program | Nothing, unless you pass `model=`: then the model files are downloaded once from Hugging Face at a fixed commit and checked by SHA-256. No text is sent. | Downloaded models in `~/.cache/katip-mask`. |
| **Katip Kalkan (Claude)** | On your computer, by a local program that Claude starts | Only the masked text, to Claude, which you chose to use. On first start, open-source helper packages are downloaded once from PyPI. | The placeholder map (`[AD SOYAD-1]` → real name), encrypted with AES-256-GCM in `~/.katip/vault`, deleted after 30 days or on request. Details: [connector/PRIVACY.md](connector/PRIVACY.md). |

Hosting: the web app is served by GitHub Pages and Hugging Face. Like any website, they see your IP address
and the files your browser requests, under their own privacy policies. They never receive your documents.

## Who is responsible for what

* **You (the lawyer or law firm) are the data controller** (*veri sorumlusu*, KVKK m.3) for your clients'
  data. You decide what to process, with which tools, and on which legal basis.
* **The author of Katip** does not receive, see or store your clients' data, so Katip's author is not a data
  processor (*veri işleyen*) for it.
* **An AI provider you send text to** (Anthropic, OpenAI, Google, ...) processes that text under its own terms.
  If its servers are outside Türkiye, sending personal data to it is a transfer abroad.

## The legal context for lawyers

This is general information, not legal advice.

* **Lawyers are data controllers.** The Board's guide for lawyers, *Avukatların Mesleki Faaliyetlerinde
  Kişisel Verilerin Korunmasına İlişkin Uygulama Rehberi* (KVKK Yayınları No. 115, announced 22 September
  2026), says so and covers generative AI tools directly (pp. 120–121). It notes that uploading client
  documents to such a tool can be a transfer of personal data abroad, and it recommends masking or
  anonymising data before sharing it (p. 146).
* **Transfers abroad need a legal basis (KVKK m.9).** Since Law No. 7499 (in force 1 June 2024), a transfer
  abroad is allowed when one of the processing conditions of m.5 or m.6 exists **and** there is an adequacy
  decision for the country, or an appropriate safeguard: standard contracts signed and notified to the Board
  within five business days, binding corporate rules approved by the Board, or a written undertaking approved
  by the Board. Occasional transfers without these are allowed only in the narrow cases listed in m.9(6).
  Check the Board's current adequacy decisions and the provider's data processing terms.
* **Special-category data needs more care (KVKK m.6).** Health data, criminal records, religion, biometric
  data and the like are common in case files and have stricter processing conditions.
* **Process only what you need (KVKK m.4).** Personal data must be "relevant, limited and proportionate" to
  the purpose. An AI that helps you draft a petition rarely needs the client's name or T.C. kimlik number.
* **Professional secrecy applies on top (Avukatlık Kanunu m.36).** A lawyer may not disclose what they learn
  through their work, whatever KVKK allows.

## What masking does, and what it does not

* Katip replaces the values it finds with placeholders such as `[AD SOYAD-1]` and keeps the real values on
  your computer. If a value it found would still be readable after masking, it refuses to give out the text.
* **It can miss values.** A value it never found stays in the text. On synthetic test documents Katip masks
  about 99% of values; on real text the misses are higher (see
  [KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench)). Check the output before you send it.
* **Masked text is usually still personal data.** Replacing names with placeholders is pseudonymisation, not
  anonymisation, while the map exists and the context (dates, events, places) can point to a person. KVKK
  still applies to it; masking reduces the risk and the amount of data, which supports m.4 and m.12.
* **Attached files and typed text are not masked.** A file you attach to a chat, or a name you type, goes to
  the AI provider as it is. Only text that passes through Katip is masked.

## What we say about Katip, and what we don't

We say: "Katip masks personal data on your computer before you share a document with an AI, so less client
data leaves your office. You still need a legal basis for any transfer and you still check the result."

We don't say Katip is "KVKK-compliant", "KVKK-safe" or "anonymous", that it makes sending data to an AI
lawful, or that it finds every value.

## Your rights

Katip's author holds no personal data about Katip's users or their clients, so there is nothing to access or
delete on the author's side. Data Katip stores on your computer can be deleted at any time: the Kalkan map
with `forget_matter` or by deleting `~/.katip`, downloaded models by deleting `~/.cache/katip-mask`. Your
clients exercise their KVKK m.11 rights with you, as the data controller.
