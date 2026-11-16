# Katip: questions and answers

**English** · [Türkçe](FAQ.tr.md)

Short answers for lawyers and their teams. How Katip handles data in detail: [PRIVACY.md](PRIVACY.md).
This is general information, not legal advice.

[guide]: https://www.kvkk.gov.tr/Icerik/8990/avukatlarin-mesleki-faaliyetlerinde-kisisel-verilerin-korunmasina-iliskin-uygulama-rehberi-yayimlandi

## What is Katip?

A tool that finds personal data in Turkish documents (names, T.C. kimlik numbers, phone numbers, addresses,
health details and more) and replaces it with placeholders such as `[AD SOYAD-1]`, **on your own computer**.
It comes as a web app that runs in your browser, as `katip-mask` packages for Python and JavaScript, and as
Katip Kalkan, a plugin that lets Claude work on a client document without seeing the values Katip finds.

## Why would a lawyer mask a document before using AI?

Because the lawyer is the data controller for the client's data, and sending it to an AI provider abroad is a
transfer that needs a legal basis. The KVKK Board's [guide for lawyers][guide] (*Avukatların Mesleki
Faaliyetlerinde Kişisel Verilerin Korunmasına İlişkin Uygulama Rehberi*, announced 22 September 2026) covers
generative AI tools directly (pp. 120–121), says that uploading client documents to them can be a transfer
abroad, and recommends masking or anonymising data before sharing it (p. 146). Katip is built to follow that
recommendation. KVKK m.4 adds that you should process only what the task needs, and an AI that drafts a
petition rarely needs the client's name.

## Does Katip make using AI KVKK-compliant?

No. Masking reduces how much client data leaves your office. You still need a legal basis for any transfer
(KVKK m.9), your duty of professional secrecy still applies (Avukatlık Kanunu m.36), and you still check the
result. Masked text is usually still personal data, because the context can point to a person.

## How does it work?

1. Rules find structured values: T.C. kimlik, tax and passport numbers, IBANs, phone numbers, e-mails,
   plates, UETS addresses, case numbers.
2. A small language model (Katip Mask) finds names, places and organisations in running text.
3. A value found once is masked everywhere it repeats, including with Turkish suffixes (`Ayşe'nin`).
4. A final check looks for any value it found that is still readable. If there is one, Katip refuses to
   give out the text.

The model was trained on synthetic documents, public Turkish Wikipedia NER data and the TurkishLegalNER
training split. No client documents were used. Details and test results:
[connector/README.md](connector/README.md#how-it-works-and-what-it-was-trained-on).

## What does it mask, and what does it keep readable?

You pick a profile. Each one masks everything the one before it does, plus more.

| | Court filing (`court`) | Sharing with AI (`ai`, default in Kalkan) | Fully anonymous (`anon`) |
|---|---|---|---|
| Names, T.C. kimlik, passport and foreign IDs, phone, e-mail, IBAN, UETS | masked | masked | masked |
| Health and other special-category data (KVKK m.6) | masked | masked | masked |
| Criminal record details | readable | masked | masked |
| A party's own address | masked | masked | masked |
| Address of the property in dispute | readable | masked | masked |
| Other addresses | street readable, building and door number masked | masked | masked |
| Bar registry number | masked | masked | masked |
| Your own case and investigation numbers | readable | masked | masked |
| Court and institution names, dates, place names | readable | readable | masked |
| Precedent citations (Yargıtay, Danıştay, AYM …) | readable | readable | readable |

Why: these rules come from a practising lawyer's review of real filings. A court needs case numbers, court
names and precedent citations; a party's home address is personal data, while the address of a property in
dispute is evidence. For the AI profile we keep your own case numbers masked, because they can identify the
client and the AI rarely needs them.

## What does Katip not do?

* **It can miss values.** On synthetic test documents it masks about 99% of values; on real text it misses
  more ([KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench)). Always read the output before sharing it.
* **It does not mask what you attach or type in a chat.** Only text that passes through Katip is masked. A
  file you attach to Claude or ChatGPT goes to the provider as it is.
* **It does not anonymise.** Placeholders are pseudonymisation while the context or the map can point to a
  person.
* **It does not check your legal reasoning,** and neither does the AI.

## Where does Katip Kalkan work?

On your own computer only: in **Claude Desktop** (chat, installed from the `.mcpb` file), **Claude Code** and
**Cowork** running on your computer. It does **not** work in claude.ai in the browser, in the Claude or
ChatGPT mobile apps, or in ChatGPT on the web. Those can only use connectors that run on the provider's
servers, so the document would have to leave your computer before it is masked, which defeats the purpose.
In a browser, use the [Katip web app](https://fikrifirat.github.io/katip): it masks the document inside your
browser tab, and you copy or download the masked text yourself. macOS is tested; Windows is supported and
checked by automated tests, but not yet tried by a person.

## How do I use it?

Leave your documents where they are. Katip searches your case folder (with client subfolders) and Downloads,
where UYAP downloads and e-mail attachments land. Say which document you mean the way you'd tell a colleague:
words from its name, its type, a file number, or "the one I just downloaded". Katip matches your words against
the real file names on your computer and shows Claude only shortened names; if several match, Claude asks which
one. Type a command in Claude Code or Cowork; in Claude Desktop, pick the same item from the **+** menu.

* `/katip <document> <request>`: anything with a client document. Katip masks it first, then Claude does what
  you ask. Example: `/katip 2026/123 bilirkişi raporu ile dava dilekçesini karşılaştır`.
* `/katip-incele <document>, [focus]`: a review: summary, claims and grounds, gaps and errors, suggestions.
  Example: `/katip-incele son indirdiğim UYAP evrakı, zamanaşımı`.
* `/katip-taslak <document>, [kind]`: a draft reply, with gaps marked `[…]` instead of invented facts. Claude
  then offers to save it with the real names as a Word file next to the document. Example:
  `/katip-taslak Yılmaz kira ihtarnamesi, cevap`.

Typing a client's name to find a file sends that name to Claude as you typed it; a document type, date or file
number finds it without that. Before Katip opens a document, Claude asks for your approval and shows the
document's shortened name. Approve only the documents you meant to share.

## Which folders does Katip use?

Two: your **case folder**, the one where you already keep client files (for example `Documents/Davalar`, with
subfolders), and **Downloads**. Nothing is copied. Final documents with real names are saved next to the source
document. In Claude Desktop you pick both in the extension's settings (leave Downloads empty if you don't want it
searched). In Claude Code, list your case folders one per line in `~/.katip/folders.txt`. Don't choose your
Desktop, all of Documents or your home folder, because Katip could then open any file there; Katip warns you if
you do, and also if a folder syncs to iCloud, OneDrive or Google Drive. In Claude Code and Cowork, Claude's own
file tools are blocked from these folders, so documents are opened only through Katip.

## Where does my data go?

Nowhere, apart from what you choose to send. The web app runs in your browser tab, and the Kalkan plugin runs on
your computer and gives Claude only the masked text. The author runs no server that receives documents, and there
are no accounts, analytics or telemetry. Kalkan keeps the placeholder map encrypted on your computer for 30 days
so it can put the real names back into your final document. See [PRIVACY.md](PRIVACY.md).

## Who is responsible if something is missed?

You, as the data controller, decide what to send and check it before you do. Katip is free, open-source
software provided as is. It reduces risk; it does not take it over.

## How do I report a problem or a value it missed?

Open a [GitHub issue](https://github.com/fikrifirat/katip/issues). Please describe the pattern with made-up
values. Never paste a real client document or real personal data.
