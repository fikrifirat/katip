# Katip Kalkan: KVKK-safe Claude for Turkish legal documents

**Katip Kalkan masks personal data in client documents on your computer, before Claude reads them.**
Names, T.C. kimlik / YKN / passport numbers, addresses, phones, IBANs and health data in a dilekçe,
contract, bilirkişi raporu, UYAP `.udf`, scan or phone photo become placeholders such as `[AD SOYAD-1]`.
Claude works on the masked text. The real values and the placeholder map stay on your computer, and
Katip can put the real names back into the final document there.

*Türkçe:* Katip Kalkan, avukatların müvekkil belgelerindeki kişisel verileri (ad soyad, T.C. kimlik no,
adres, telefon, IBAN, sağlık verisi) Claude görmeden önce kendi bilgisayarlarında maskeleyen bir Claude
eklentisidir. KVKK uyumlu çalışmaya yardım eden yerel veri maskeleme ve anonimleştirme aracıdır;
belgeler ve gerçek adlar bilgisayardan çıkmaz.

Keywords: KVKK, GDPR, PII redaction, personal data masking, pseudonymisation, anonymisation, Turkish NER,
legal AI, avukat, kişisel veri maskeleme, anonimleştirme, UYAP.

## Install

```
claude plugin marketplace add fikrifirat/katip
claude plugin install katip-kalkan@katip
```

Claude Desktop (chat): download `katip-kalkan.mcpb` from the
[latest Kalkan release](https://github.com/fikrifirat/katip/releases?q=kalkan) and double-click it.

**Requirements.** macOS (tested) or Linux; Windows is not tested yet. `python3` 3.9 or later on the
PATH, and [uv](https://docs.astral.sh/uv/) (recommended: `brew install uv`). With uv, Katip has the
name model, PDF and scan reading and the encrypted map. Without uv it runs on rules only, can't read
PDFs or scans, keeps the map in memory, and `katip_status` says so.

## Limits and your responsibility

Katip is a safety layer, not a guarantee, and not legal advice.

* **It can miss things.** On 80 blind synthetic legal documents it masked 743 of 757 personal values
  (98%), not all of them; see also [KVKK-Bench](https://huggingface.co/spaces/f1k/kvkk-bench). Unusual spellings, OCR errors on
  handwriting and context-only identifiers ("the defendant's brother, the mayor of …") can slip through.
  Check the masked text when it matters, and use the `anon` profile for the most sensitive files.
* **Masked text is still personal data under KVKK.** Pseudonymised text sent to Claude is less risky,
  but it is still personal data, and sending it abroad is still a transfer. Your firm remains the
  data controller and decides whether this use is lawful (KVKK m.4, m.9).
* **Claude's answers about the law can be wrong.** Review every draft before you use it.
* **Attached files are not protected.** A file you attach to the chat is uploaded with your message,
  before any tool runs. Put client files in your Katip folder instead (see below).
* The software is provided as is, without warranty (AGPL-3.0, sections 15–16).

## What Katip runs, sends and fetches

* **Runs:** a local MCP server (`python3 server.py`) on your computer. Claude Code, Cowork on your
  computer and Claude Desktop start it. It is not used in claude.ai on the web.
* **Reads:** only the files Claude asks for, inside your Katip folder (`Documents/katip-documents` by
  default). **Writes:** masked copies next to the original, and restored documents only into the
  Katip folder; the encrypted placeholder map in `~/.katip/vault`.
* **Sends:** nothing. Katip has no telemetry, analytics or crash reporting, and makes no network calls
  while processing documents. Claude receives only the masked text, under Anthropic's terms.
* **Fetches, once:** on first start, if uv is installed, uv downloads exact pinned versions of
  onnxruntime 1.32.0, numpy 2.5.4, cryptography 50.0.2, pymupdf 2.1 and rapidocr 3.10.0 from PyPI,
  and Python 3.12 if it's missing. Set `KATIP_AUTO_DEPS=0` to turn this off. The name model and the OCR
  models ship inside the plugin; nothing is downloaded from Hugging Face.

## Privacy policy

Katip collects no data. Documents are read and masked on your computer, and nothing is sent to the
author or to any third party. The placeholder map (placeholder → real value) is stored on your computer,
encrypted with AES-256-GCM. The key is in the macOS Keychain, or in `~/.katip/key` readable only by you.
Maps are deleted after 30 days (`KATIP_VAULT_DAYS`) or at once with `forget_matter`. Contact:
[GitHub issues](https://github.com/fikrifirat/katip/issues). Full policy: [PRIVACY.md](PRIVACY.md).

## How to use it

Claude Desktop warns that the extension gets "access to everything on your computer" and that the
developer information "has not been verified by Anthropic". It shows this for every extension installed
from a file. Signing doesn't remove it today, because Claude Desktop doesn't check MCPB signatures yet.
Katip reads only the files Claude passes to it, inside its folder. That is `Documents/katip-documents` by
default, created on first use, or the folder you pick in the settings. Ask Claude to "open my Katip folder"
(the `open_folder` tool) to see it.

**Don't attach client files to the chat.** Drop the file into your Katip folder and ask, for example:
"Katip klasörüne az önce eklediğim dilekçeyi özetle." Katip opens the newest file (`file_id: "latest"`),
masks it on your computer and gives Claude only the masked text.

**Shortcut.** In Claude Code / Cowork, type `/katip son eklediğim dilekçeyi özetle` (the plugin's `katip`
skill). In Claude Desktop, choose *Katip ile güvenli çalış* from the **+** menu (an MCP prompt) and type
your request.

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
the whole address, case/UYAP and bar numbers); `court` = Mahkemeye sunum (streets, case numbers and dates
stay readable); `anon` = Tam anonim (also dates, provinces, courts, companies and institutions).

**Scans and photos** are read on your computer: PaddleOCR PP-OCRv5 (bundled, 13 MB, via RapidOCR) for
handwriting and phone photos, and Tesseract for clean printed scans when it is installed
(`brew install tesseract tesseract-lang`), the same "Otomatik" routing as the app. On the 48 printed blind
scans no value was readable after masking; on 6 synthetic handwritten lease photos 47 of 48 values were
masked (one block/door number survived).

**Models.** The plugin ships **Katip Mask Nano · tr v1.1** (2.5 MB, Turkish and foreign client
names, trust 0.5) next to the rules. For the 110 MB **Katip Mask Base · tr v2**, download it from
Hugging Face and run `katip-kalkan install-model <folder> --trust 0.5`. See
[katip_kalkan/models/README.md](katip_kalkan/models/README.md).

Example prompts:
* `/katip ekledigim son dilekceyi incele, dikkatlice ozetle ve duzeltmeler oner`
* "Katip klasöründeki bilirkişi raporu ile dava dilekçesindeki talepleri karşılaştır (dosya 2026/123)."
* "Draft a reply to the petition I just added, then save it with the real names as cevap-dilekcesi.docx."
* "Make a masked copy of the lease contract I can email to the expert."

**ChatGPT: mask on your computer, share a code.**

```
katip-kalkan share dilekce.docx --relay https://<relay>
# prints katip-AbC....xyz  (works once, for 15 minutes)
```

Paste the code into ChatGPT with the Katip app enabled. ChatGPT fetches the masked text from
the relay. The relay only ever holds masked text, encrypted, in memory.

## Tools

| Tool | What it does | Returns |
|---|---|---|
| `list_files` | Lists the files in your Katip folder with ids. Words in a file name that could be a person's name show as … | ids, safe names |
| `mask_file` | Opens a .docx, .udf, .txt, .pdf, scan or phone photo on your computer (OCR runs locally) and masks it | masked text, counts |
| `write_masked_copy` | Saves `name.maskeli.docx` next to the original | path |
| `restore_to_file` | Puts the real values back into the AI's text and saves it in your Katip folder (.docx, .txt or .md) | file name and count only |
| `forget_matter` | Deletes a matter's placeholder map | ok |
| `open_folder` | Opens your Katip folder in Finder or Explorer, creating it if needed | path and link |
| `katip_status` | Shows the engine, OCR, threshold, your folder (with a link) and where the map is kept | status |
| `open_masked_document` (relay) | Opens a share code | masked text |

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
Settings: `KATIP_FOLDER` (default folder, `~/Documents/katip-documents`), `KATIP_THRESHOLD` (0.7), `KATIP_MODEL` (folder or `none`), `KATIP_TRUST`,
`KATIP_PROFILE` (`ai`, `court`, `anon`), `KATIP_OCR` (`auto`, `paddle`, `tesseract`), `KATIP_ALLOWED_DIRS`, `KATIP_VAULT_DAYS` (30),
`KATIP_RELAY_TTL` (900 s), `KATIP_RELAY_MAX_READS` (1), `KATIP_RELAY_UPLOAD_TOKEN`.

Blind set (80 synthetic legal documents, 757 values, threshold 0.7, whole-address scoring):
rules only 717, rules + Nano v1 739, rules + Nano v1.1 743. Masked `.udf` copies drop
`sign.sgn` (the e-imza certificate carries the signer's name).

## Licences

Code: AGPL-3.0-or-later (commercial licence on request, see [COMMERCIAL.md](../COMMERCIAL.md)). Bundled
Katip Mask Nano model: CC BY-SA 4.0 (trained partly on Turkish Wikipedia NER data). Bundled PaddleOCR
PP-OCRv5 models: Apache-2.0. See [NOTICE.md](NOTICE.md) for all third-party components.
