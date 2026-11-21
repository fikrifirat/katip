# Katip: KVKK masking for lawyers (Katip Kalkan for Claude)

*Avukatlar için KVKK kişisel veri maskeleme ve anonimleştirme · PII redaction for Turkish legal documents*

**Work on client files with Claude, with the client's personal data masked on your computer first.** Katip Kalkan
opens the document on your computer, replaces the names, ID numbers and health details it finds with
placeholders such as `[AD SOYAD-1]`, and gives Claude only the masked text. When your draft is ready, Katip
puts the real names back into the draft and saves it as a Word (.docx), text or Markdown file, again on your computer.

Built for Turkish lawyers and legal teams, on the recommendation in the KVKK Board's
[guide for lawyers](https://www.kvkk.gov.tr/Icerik/8990/avukatlarin-mesleki-faaliyetlerinde-kisisel-verilerin-korunmasina-iliskin-uygulama-rehberi-yayimlandi)
(22 September 2026) to mask or anonymise client data before sharing it with generative AI tools.

**What you get**

* Reads dilekçe, contracts, bilirkişi raporu, UYAP `.udf`, `.docx`, `.pdf`, scans and phone photos. OCR runs
  on your computer.
* Masks names (Turkish and foreign), T.C. kimlik, YKN and passport numbers, addresses, phone numbers, e-mail,
  IBAN, UETS addresses and KVKK m.6 health data.
* Three profiles: **court filing** keeps case numbers, court names and the disputed property readable;
  **sharing with AI** (the default) masks those too; **fully anonymous** also hides dates, places and
  institutions. Precedent citations (Yargıtay, Danıştay, AYM) stay readable in all three.
* The same person gets the same placeholder in every document of a matter.
* Finds documents where you already keep them: your case folder (with client subfolders) and Downloads, where UYAP
  downloads and e-mail attachments land. Nothing is copied.
* The final document with real names is saved next to the source document, on your computer. Claude gets the
  file name back, not the names.
* If a value Katip found would still be readable, it refuses to hand over the text.
* No account, no telemetry. The author receives nothing.

**Try it in three steps**

1. **Install:** in Claude Code run `claude plugin marketplace add fikrifirat/katip` and then
   `claude plugin install katip-kalkan@katip`. In Claude Desktop, double-click the `.mcpb` file
   ([details](#install)).
2. **Try it on a sample:** download [this synthetic petition](https://github.com/fikrifirat/katip/raw/main/docs/samples/dilekce_01.docx) (made-up people) into Downloads
   and type `/katip-incele dilekce_01`. Claude reviews it and sees `[AD SOYAD-1]` and `[T.C. KİMLİK NO-1]` where the
   names and ID numbers were. Run `katip_status` to see which rules and model did the masking.
3. **Check the numbers:** the [KVKK-Bench leaderboard](https://huggingface.co/spaces/f1k/kvkk-bench) compares Katip with other Turkish and
   multilingual models on the same test sets, including how many values each one lets through.

**Commands.** Say which document you mean, the way you'd say it to a colleague: words from its name, its type,
a file number, or "the one I just downloaded". Katip searches the real file names on your computer and shows
Claude only shortened names; if several match, Claude asks which one. Type a command in Claude Code or Cowork;
in Claude Desktop, pick the same item from the **+** menu.

| Command | What it does | Example |
|---|---|---|
| `/katip <document> <request>` | Anything with a client document: Katip masks it first, then Claude does what you ask. | `/katip 2026/123 bilirkişi raporu ile dava dilekçesini karşılaştır` |
| `/katip-incele <document>, [focus]` | Reviews a document: summary, claims and grounds, gaps and errors, suggestions. | `/katip-incele son indirdiğim UYAP evrakı, zamanaşımı` |
| `/katip-taslak <document>, [kind]` | Drafts a reply, marks gaps as `[…]` instead of inventing facts, and offers to save it with the real names as a Word (.docx), text or Markdown file next to the document. | `/katip-taslak Yılmaz kira ihtarnamesi, cevap` |

You can also just ask in plain words, for example "bugün indirdiğim bilirkişi raporunu özetle". Typing a
client's name to find a file sends that name to Claude as you typed it; a type, date or file number avoids that.

**Before you rely on it.** Katip can miss values: it masked 98.8% of values on a synthetic blind test set,
and misses more on real text. Files you attach to the chat and text you type are not masked. Masked text is
usually still personal data, and sending it abroad still needs a legal basis (KVKK m.9). Review every draft.
Details: [Limits and your responsibility](#limits-and-your-responsibility).

**Read more:** [FAQ](https://github.com/fikrifirat/katip/blob/main/FAQ.md) ·
[How Katip processes data](https://github.com/fikrifirat/katip/blob/main/PRIVACY.md) ·
[Privacy policy](#privacy-policy) ·
[Demo](https://fikrifirat.github.io/katip) ·
[KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench)

### Türkçe

**Müvekkil dosyaları üzerinde Claude ile çalışın; müvekkilin kişisel verileri önce bilgisayarınızda maskelensin.**
Katip Kalkan belgeyi kendi bilgisayarınızda açar, bulduğu ad soyad, kimlik numarası ve sağlık bilgilerini
`[AD SOYAD-1]` gibi yer tutucularla değiştirir ve Claude'a yalnızca maskeli metni verir. Taslak hazır
olduğunda gerçek adları taslağa yine bilgisayarınızda geri koyar ve Word (.docx), metin ya da Markdown dosyası olarak kaydeder.

Avukatlar ve hukuk ekipleri için geliştirildi. Kişisel Verileri Koruma Kurulu'nun
[avukatlar için uygulama rehberine](https://www.kvkk.gov.tr/Icerik/8990/avukatlarin-mesleki-faaliyetlerinde-kisisel-verilerin-korunmasina-iliskin-uygulama-rehberi-yayimlandi)
(22 Eylül 2026) yer alan öneriye göre tasarlandı: Rehber, müvekkil verilerinin üretken yapay zekâ
araçlarıyla paylaşılmadan önce maskelenmesini ya da anonimleştirilmesini önerir.

**Üç adımda deneyin**

1. **Kurun:** Claude Code'da `claude plugin marketplace add fikrifirat/katip`, ardından
   `claude plugin install katip-kalkan@katip` çalıştırın. Claude Desktop'ta `.mcpb` dosyasına çift tıklayın
   ([ayrıntılar](#install)).
2. **Örnekle deneyin:** [bu kurgusal dilekçeyi](https://github.com/fikrifirat/katip/raw/main/docs/samples/dilekce_01.docx) (kişiler uydurmadır) İndirilenler'e indirin ve
   `/katip-incele dilekce_01` yazın. Claude dilekçeyi inceler; adların ve kimlik numaralarının yerinde
   `[AD SOYAD-1]` ve `[T.C. KİMLİK NO-1]` görür. Maskelemeyi hangi kural ve modelin yaptığını `katip_status` gösterir.
3. **Sonuçlara bakın:** [KVKK-Bench sıralaması](https://huggingface.co/spaces/f1k/kvkk-bench) Katip'i aynı test setlerinde diğer Türkçe ve çok dilli
   modellerle karşılaştırır; her birinin kaç değeri kaçırdığı da görülür.

**Komutlar.** Belgeyi bir meslektaşınıza söyler gibi tarif edin: adından bir sözcük, türü, dosya numarası ya da
"son indirdiğim". Belgeleri kopyalamanız gerekmez: Katip dava klasörünüzde (alt klasörler dahil) ve UYAP
evrakı ile e-posta eklerinin düştüğü İndirilenler'de, gerçek dosya adlarında bilgisayarınızda arar; Claude'a
yalnızca kısaltılmış adları gösterir, birden çok belge uyarsa hangisi olduğunu sorar. Komutu Claude Code ya da
Cowork'te yazın; Claude Desktop'ta aynı öğeyi **+** menüsünden seçin.

| Komut | Ne yapar | Örnek |
|---|---|---|
| `/katip <belge> <istek>` | Müvekkil belgesiyle her iş: Katip önce maskeler, sonra Claude isteğinizi yapar. | `/katip 2026/123 bilirkişi raporu ile dava dilekçesini karşılaştır` |
| `/katip-incele <belge>, [odak]` | Belgeyi inceler: özet, talepler ve dayanaklar, eksik ve hatalar, öneriler. | `/katip-incele son indirdiğim UYAP evrakı, zamanaşımı` |
| `/katip-taslak <belge>, [tür]` | Taslak yazar, bilinmeyenleri uydurmak yerine `[…]` ile işaretler, isterseniz gerçek adlarla belgenin yanına Word (.docx), metin ya da Markdown dosyası olarak kaydeder. | `/katip-taslak Yılmaz kira ihtarnamesi, cevap` |

Dosyayı bulmak için müvekkilin adını yazarsanız o ad Claude'a yazdığınız gibi gider; belge türü, tarih ya da
dosya numarası bunu önler.

Dilekçe, sözleşme, bilirkişi raporu, UYAP `.udf`, `.docx`, `.pdf`, tarama ve telefon fotoğrafı okur.
Üç maskeleme düzeyi vardır: **Mahkemeye sunum** dosya numaralarını, mahkeme adlarını ve dava konusu
taşınmazı okunur bırakır; **Yapay zekâ ile paylaşım** (varsayılan) bunları da maskeler; **Tam anonim**
tarih, yer ve kurum adlarını da gizler. Emsal karar künyeleri her düzeyde okunur kalır.

Katip bazı değerleri kaçırabilir; sohbete eklediğiniz dosyalar ve yazdıklarınız maskelenmez. Maskeli
metin de çoğu zaman kişisel veridir ve yurt dışına aktarımı hukuki dayanak ister (KVKK m.9). Her taslağı
kontrol edin.

**Daha fazlası:** [Sık sorulan sorular](https://github.com/fikrifirat/katip/blob/main/FAQ.tr.md) ·
[Katip verileri nasıl işler](https://github.com/fikrifirat/katip/blob/main/PRIVACY.tr.md) ·
[Demo](https://fikrifirat.github.io/katip)

Keywords: KVKK, GDPR, PII redaction, personal data masking, pseudonymisation, anonymisation, Turkish NER,
legal AI, avukat, kişisel veri maskeleme, anonimleştirme, UYAP.

## Install

```
claude plugin marketplace add fikrifirat/katip
claude plugin install katip-kalkan@katip
```

Claude Desktop (chat): download `katip-kalkan.mcpb` from the
[latest Kalkan release](https://github.com/fikrifirat/katip/releases?q=kalkan) and double-click it.

**Choosing the folders.** Katip opens documents only from two places: your **case folder**, the folder where you
already keep client files (for example `Documents/Davalar`, subfolders included), and **Downloads**, where UYAP
downloads and e-mail attachments land. In Claude Desktop you pick both in the extension's settings; leave
Downloads empty if you don't want it searched. In Claude Code, list your case folders one per line in
`~/.katip/folders.txt` (Downloads is searched unless `KATIP_DOWNLOADS=0`). Don't pick Desktop, all of Documents
or your home folder; Katip warns you if you do, and if a folder syncs to iCloud, OneDrive or Google Drive (final
documents with real names are saved next to the source, so they would sync too). More:
[FAQ](https://github.com/fikrifirat/katip/blob/main/FAQ.md#which-folders-does-katip-use).

**Where it works.** Claude Desktop, Claude Code and Cowork on your computer. Not claude.ai in the browser,
mobile apps or ChatGPT: those reach only connectors on the provider's servers, so the document would leave
your computer before masking.

**Requirements.** macOS (tested by hand) or Linux; Windows is checked by automated tests on every change but not yet tried by a person. `python3` 3.9 or later on the
PATH, and [uv](https://docs.astral.sh/uv/) (recommended: `brew install uv`). With uv, Katip has the
name model, PDF and scan reading and the encrypted map. Without uv it runs on rules only, can't read
PDFs or scans, keeps the map in memory, and `katip_status` says so.

## Limits and your responsibility

Katip is a safety layer, not a guarantee, and not legal advice.

* **It can miss things.** Katip refuses to send text in which a value it *found* would still be
  readable, but a value it never found goes to Claude as is. On 80 blind synthetic legal documents
  (0.3.6, threshold 0.5, `ai` profile) it masked 748 of 757 personal values (98.8%); a value counts
  only when no word of it is left readable. On real text the
  [KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench) paper measures about 5% of name characters
  missed in court decisions and more in free prose. Unusual spellings, OCR errors on
  handwriting and context-only identifiers ("the defendant's brother, the mayor of …") can slip through.
  Check the masked text when it matters, and use the `anon` profile for the most sensitive files.
* **Masked text is still personal data under KVKK.** Pseudonymised text sent to Claude is less risky,
  but it is still personal data, and sending it abroad is still a transfer. Your firm remains the
  data controller and decides whether this use is lawful (KVKK m.4, m.9). Katip follows the KVKK Board's
  [guide for lawyers](https://www.kvkk.gov.tr/Icerik/8990/avukatlarin-mesleki-faaliyetlerinde-kisisel-verilerin-korunmasina-iliskin-uygulama-rehberi-yayimlandi) (22 Sep 2026), which recommends masking or anonymising data before sharing
  it with generative AI tools (p. 146).
* **Claude's answers about the law can be wrong.** Review every draft before you use it.
* **Attached files are not protected.** A file you attach to the chat is uploaded with your message,
  before any tool runs. Type the document's name instead; Katip finds it on your computer.
* The software is provided as is, without warranty (AGPL-3.0, sections 15–16).

## How it works and what it was trained on

Katip finds personal data in four steps, all on your computer:

1. **Rules** catch everything with a fixed shape or a checksum: T.C. kimlik (checksum), YKN (99-prefixed),
   passport and foreign IDs, VKN, IBAN (checksum), card, phone, plate and e-mail, plus addresses, case and
   bar numbers and KVKK art. 6 health terms from a word list.
2. **A small name model**, Katip Mask Nano · tr v1.1 (2.5 MB, a 2-layer BERT trained from scratch), finds
   person names the rules can't, including transliterated foreign names (Mohammad / Muhammed / Mhd).
3. **Propagation:** a value found once is masked everywhere it appears in the document and in the same
   matter, so a name caught in one sentence is also masked where the context was weaker.
4. **Leak check:** if any value Katip found would still be readable after masking, Katip refuses to send
   the text. It can't refuse for a value it never found, which is why step 2's recall matters.

Scans and photos go through local OCR (PaddleOCR PP-OCRv5) first.

**What the name model learned from.** No client or user documents, and Katip never learns from your files.
The training mix was:

* 8,000 synthetic legal documents generated from Katip's templates: petitions, judgments, leases, employment
  contracts, powers of attorney, notices, e-mails, minutes, chats and expert reports, with made-up people.
* 17,967 real Turkish sentences from Turkish Wiki NER (Altinok 2023, CC BY-SA 4.0), so it handles real prose
  and not only templates.
* Yargıtay sentences from the TurkishLegalNER *train* split, with the anonymised name slots filled in.
* Transliterated foreign names from 10 origin groups (Syrian, Iranian, Afghan, Georgian, Armenian, Greek, Arab,
  Russian/Ukrainian, Azerbaijani and Western), with the spelling variants seen in Turkish files.

**How it was tested,** on data kept out of training:

| Test | Result (rules + Nano v1.1) | What it shows |
|---|---|---|
| 80 blind synthetic legal documents, 757 values, names never seen in training | 748 / 757 masked (98.8%), 0.3.6 at threshold 0.5 | All value types, document layouts. 12 of 16 styles share templates with training, so this is optimistic |
| TurkishLegalNER *test* (real Yargıtay prose), name slots filled with held-out families, 1,011 names | Turkish names 98.7%, foreign names 94.6% [92.5–96.2] | Names in real court language |
| [KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench) leaderboard | See the board | Comparison with other Turkish and multilingual models on real text |

Not tested yet: real case files, because they can't leave a law firm. We plan to measure on documents that
pilot lawyers label on their own computers. Full details, confidence intervals and the training recipe:
the [Katip Mask Nano model card](https://huggingface.co/f1k/katip-mask-nano) and `lab/foreign/` in this repo.

## What Katip runs, sends and fetches

* **Runs:** a local MCP server (`python3 server.py`) on your computer. Claude Code, Cowork on your
  computer and Claude Desktop start it. It is not used in claude.ai on the web.
* **Reads:** only the documents Claude asks for, inside your case folder and Downloads (Claude Desktop: the
  folders in the settings; Claude Code: `~/Documents/katip-documents`, the folders in `~/.katip/folders.txt`
  and Downloads). To find a document it reads file and folder *names* there and matches your words locally.
  **Writes:** masked copies and restored documents next to the source document, never outside those
  folders; the encrypted placeholder map in `~/.katip/vault`.
* **Guards (Claude Code and Cowork):** a small hook (`hooks/guard.py`, standard library only) runs before
  Claude's own Read, Grep, Glob, Edit, Write and Bash tools. If a call touches those folders or
  `~/.katip`, it blocks the call and tells Claude to use Katip instead. It reads no file contents and
  makes no network calls. Claude Desktop chat doesn't run plugin hooks; there Katip's folder setting and
  Desktop's own permission prompts are the guard.
* **Sends:** nothing while processing documents, and no telemetry, analytics or crash reporting. Claude
  receives only the masked text, under Anthropic's terms. The one exception is precedent search
  (`emsal_ara`), off by default; once you turn it on and Claude calls it, short lowercase keyword queries go to the Ministry of Justice's
  public decision search, never the document or personal data (details and the off switch in
  [PRIVACY.md](PRIVACY.md)).
* **Fetches, once:** on first start, if uv is installed, uv downloads exact pinned versions of
  katip-mask 0.1.1 (the detection rules, the same as the app and the SDK), onnxruntime 1.32.0,
  numpy 2.5.4, cryptography 50.0.2, pymupdf 2.1 and rapidocr 3.10.0 from PyPI, and Python 3.12 if it's
  missing. Set `KATIP_AUTO_DEPS=0` to turn this off; Katip then uses the rules bundled in the plugin,
  which are the same. The Nano name model and the OCR text detector ship inside the plugin. The OCR
  text recogniser (PaddleOCR, 8 MB) ships inside the `.mcpb`; the Claude Code plugin downloads it from
  Hugging Face the first time you open a scan or photo, at a pinned commit, checked by SHA-256
  (`KATIP_OCR_DOWNLOAD=0` turns this off). If you set `KATIP_MODEL=base` or `mini`, that model is also
  downloaded from Hugging Face, once, at the commit pinned in katip-mask and checked by SHA-256.

## Privacy policy

Katip collects no data. Documents are read and masked on your computer, and nothing is sent to the
author or to any third party. The placeholder map (placeholder → real value) is stored on your computer,
encrypted with AES-256-GCM. The key is in the macOS Keychain, or in `~/.katip/key` readable only by you.
Maps are deleted after 30 days (`KATIP_VAULT_DAYS`) or at once with `forget_matter`. Support:
fikrifirat@gmail.com or [GitHub issues](https://github.com/fikrifirat/katip/issues). Full policy: [connector/PRIVACY.md](https://github.com/fikrifirat/katip/blob/main/connector/PRIVACY.md). The KVKK context for lawyers (m.4, m.6, m.9 after Law No. 7499, Avukatlık Kanunu
m.36): [PRIVACY.md](https://github.com/fikrifirat/katip/blob/main/PRIVACY.md) · [PRIVACY.tr.md](https://github.com/fikrifirat/katip/blob/main/PRIVACY.tr.md). Questions and answers, including what each profile masks: [FAQ.md](https://github.com/fikrifirat/katip/blob/main/FAQ.md) · [FAQ.tr.md](https://github.com/fikrifirat/katip/blob/main/FAQ.tr.md).

## How to use it

**A day with Katip.** A UYAP notification arrives; you download the bilirkişi raporu, which lands in Downloads.
In Claude you type `/katip-incele son indirdiğim bilirkişi raporu, hesap hataları`. Katip finds it, Claude
shows the approval prompt with the shortened name, and you get a review. Then `/katip-taslak 2026/123 bilirkişi
raporu, itiraz dilekçesi`: Claude drafts the objection and offers to save it with the real names;
`itiraz-dilekcesi.docx` appears next to the report, ready to check and file in UYAP. For a document in a case
folder, name it: `/katip Yılmaz kira sözleşmesindeki fesih şartlarını çıkar`.

**Commands (Claude Code and Cowork).** `/katip <belge> <istek>` for anything; `/katip-incele <belge>, [odak]`
to review and summarise; `/katip-taslak <belge>, [taslak türü]` to draft a reply and, if you want, save it
with the real names as a Word (.docx), text or Markdown file. In Claude Desktop the same three appear in the **+** menu as *Katip ile
güvenli çalış*, *Dilekçeyi incele ve özetle* and *Cevap taslağı hazırla*, each with a "Hangi belge?" field.

**What the approval prompt shows.** Before Katip opens a document, Claude asks for your approval. The prompt
names the document by its shortened name (`belge`) and a fixed line (`bilgi`) that says the document is masked
on this computer and that Katip can miss a value. Approve only documents you meant to share.

Claude Desktop warns that the extension gets "access to everything on your computer" and that the
developer information "has not been verified by Anthropic". It shows this for every extension installed
from a file. Signing doesn't remove it today, because Claude Desktop doesn't check MCPB signatures yet.
Katip reads only the documents Claude asks for, inside the case folder and Downloads you picked in the
settings.

**Don't attach client files to the chat.** An attached file is uploaded with your message. Type the document's
name instead, for example "son indirdiğim dilekçeyi özetle"; Katip opens it on your computer and gives Claude
only the masked text.

**Language.** Tool names, the permission-prompt line and errors are in Turkish by default. Set
*Language / Dil* to `en` (Claude Desktop) or `KATIP_LANG=en` for English. Claude itself answers in your language.

**File names are personal data too.** "Ayşe Kaya - epikriz.pdf" tells the AI who the client is. Katip's
`list_files` only shows words from a small legal vocabulary ("… - Vatandaşlık Dava Dilekçesi.udf"), and
Claude then opens files by id, so the name doesn't appear in the chat or in the permission prompt. Claude
Desktop's own file tools can still list the folder if you allow them. Decline them, or name files neutrally.
Each permission prompt shows a line in Turkish saying that the file is masked on this computer. To check that
your download was built by this repository's GitHub workflow from public code:

```
gh attestation verify katip-kalkan.mcpb --repo fikrifirat/katip
shasum -a 256 -c katip-kalkan.mcpb.sha256
```

**Profiles** (same as the Katip app): `ai` = Yapay zekâ ile paylaşım, the default here (all personal data,
the whole address, case/UYAP and bar numbers); `court` = Mahkemeye sunum (parties' own addresses masked in full, with
UETS and bar numbers; the address of the property in dispute, case numbers and dates stay readable); `anon` = Tam anonim (also dates, provinces, courts, companies and institutions).

**Scans and photos** are read on your computer: PaddleOCR PP-OCRv5 (bundled, 13 MB, via RapidOCR) for
handwriting and phone photos, and Tesseract for clean printed scans when it is installed
(`brew install tesseract tesseract-lang`), the same "Otomatik" routing as the app. On the 48 printed blind
scans no value was readable after masking; on 6 synthetic handwritten lease photos 47 of 48 values were
masked (one block/door number survived).

**Models.** The plugin ships **Katip Mask Nano · tr v1.1** (2.5 MB, Turkish and foreign client
names, trust 0.5) next to the rules. For better name recall pick **base** (110 MB, the most accurate on
KVKK-Bench) or **mini** (31 MB) as the name model in the extension's settings (Claude Desktop), or set
`KATIP_MODEL=base` in the shell you start Claude Code from: Katip downloads it once
through the katip-mask SDK, at a pinned commit, checks every file's SHA-256 and then works offline. If the
download fails it keeps using Nano and `katip_status` says so. A model folder of your own still works with
`katip-kalkan install-model <folder> --trust 0.5`. See
[katip_kalkan/models/README.md](katip_kalkan/models/README.md).

Example prompts:
* `/katip ekledigim son dilekceyi incele, dikkatlice ozetle ve duzeltmeler oner`
* "2026/123 dosyasındaki bilirkişi raporu ile dava dilekçesindeki talepleri karşılaştır."
* "Draft a reply to the petition I just added, then save it with the real names as cevap-dilekcesi.docx."
* "Make a masked copy of the lease contract I can email to the expert."

**ChatGPT: mask on your computer, share a code.**

```
katip-kalkan share dilekce.docx --relay https://<relay>
# prints katip-AbC....xyz  (works once, for 15 minutes)
```

Paste the code into ChatGPT with the Katip connector enabled. ChatGPT fetches the masked text from
the relay. The relay only ever holds masked text, encrypted, in memory. In the same chat it can search
Yargıtay decisions (with the gavel button) and read statutes. Setup and limits: [CHATGPT.md](CHATGPT.md).

## Tools

| Tool | What it does | Returns |
|---|---|---|
| `list_files` | Finds documents in your case folder and Downloads; with `ara` it matches your words against the real names on your computer. Words in a file name that could be a person's name show as … | ids, safe names, where |
| `mask_file` | Opens a .docx, .udf, .txt, .pdf, scan or phone photo on your computer (OCR runs locally) and masks it | masked text, counts |
| `write_masked_copy` | Saves `name.maskeli.docx` next to the original | path |
| `restore_to_file` | Puts the real values back into the AI's text and saves it next to the source document (.docx, .udf, .pdf, .txt or .md); checks the statute citations in it | file name, count and the citation check |
| `forget_matter` | Deletes a matter's placeholder map | ok |
| `open_folder` | Opens Katip's default folder in Finder or Explorer, creating it if needed | path and link |
| `emsal_ara` | Finds Yargıtay decisions for 1–5 short keyword queries (Claude writes them from the masked text). With `file_id`, the document is masked here and the decisions are ranked against it. Only the keywords leave; a decision is shown only if its esas/karar numbers are in the official text | decision, link, outcome, quoted paragraph, `result_id` |
| `mevzuat_bak` | Offline: reads a statute article (`TBK 344`) or checks every statute citation in a text (exists, in force, repealed, number and name match). 1,085 laws, article text for the core codes | verdicts, article text, source link, index date |
| `geri_bildirim` | Saves the lawyer's grade (0/1/2, would cite, note) for one `emsal_ara` result, on this computer | count of grades |
| `katip_status` | Shows the engine, OCR, threshold, your folder (with a link) and where the map is kept | status |
| `open_masked_document` (relay) | Opens a share code | masked text |
| `emsal_ara`, `mevzuat_bak`, `geri_bildirim` (relay) | The same research tools for ChatGPT; verdicts are stored on the relay, without notes | as above |

## Developers

```
cd connector
python -m pytest -q                       # 32 tests: formats, model, profiles, OCR, vault crypto, stdio MCP, relay
python -m katip_kalkan.local_server       # stdio MCP server
python -m katip_kalkan relay --port 8787  # relay (put TLS in front)
python build_bundle.py                    # dist/katip-kalkan.mcpb
claude plugin validate ./connector
bash tests/e2e_claude_code.sh            # real Claude Code run through the plugin
```

There are no required dependencies; `onnxruntime`, `numpy`, `cryptography`, `pymupdf` and `rapidocr`
are optional, pinned in `katip_kalkan/launch.py`. The detection engine is `katip_kalkan/engine.zip`, the same bundle the browser app runs
(`docs/katip_py.zip`; `build_bundle.py` refreshes it). `ner.py` is the Python twin of `src/ner.js`:
same spans as `ml/eval_system.py` on all 183 eval documents, and its WordPiece matches Hugging
Face `tokenizers` exactly.
Settings: `KATIP_FOLDER` (default folder, `~/Documents/katip-documents`), `KATIP_THRESHOLD` (0.5; was 0.7 before 0.3.6), `KATIP_MODEL` (folder or `none`), `KATIP_TRUST`,
`KATIP_PROFILE` (`ai`, `court`, `anon`), `KATIP_OCR` (`auto`, `paddle`, `tesseract`), `KATIP_ALLOWED_DIRS`, `KATIP_VAULT_DAYS` (30),
`KATIP_RELAY_TTL` (900 s), `KATIP_RELAY_MAX_READS` (1), `KATIP_RELAY_UPLOAD_TOKEN`; the other relay settings are in [CHATGPT.md](CHATGPT.md).

Blind set (80 synthetic legal documents, 757 values, `.txt`, `ai` profile; a value counts only when no word
of it is left readable): 0.3.6 at threshold 0.5, rules + Nano v1.1: 748. Earlier, at threshold 0.7 with
whole-address scoring: rules only 717, rules + Nano v1 739, rules + Nano v1.1 743 (0.3.5). Masked `.udf` copies drop
`sign.sgn` (the e-imza certificate carries the signer's name).

## Licences

Code: AGPL-3.0-or-later (commercial licence on request, see [COMMERCIAL.md](../COMMERCIAL.md)). Bundled
Katip Mask Nano model: CC BY-SA 4.0 (trained partly on Turkish Wikipedia NER data). Bundled PaddleOCR
PP-OCRv5 models: Apache-2.0. See [NOTICE.md](NOTICE.md) for all third-party components.
