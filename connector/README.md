# Katip Kalkan: use ChatGPT and Claude without sending them your clients' personal data

Katip Kalkan connects ChatGPT and Claude to your documents through Katip. Before the AI reads a
dilekçe, contract or medical report, Katip replaces names, T.C. kimlik numbers, addresses,
phones, IBANs and health data with placeholders such as `[AD SOYAD-1]`. The real values stay on
your computer, and Katip puts them back in the final document on your computer.

You stay the reviewer: Katip reduces what leaves your office, and you still check its output.
Read [DESIGN.md](DESIGN.md) for how it works, the trade-offs and the KVKK notes.

## Two ways in

**Claude (Desktop, Code, Cowork): local connector.** Katip runs on your computer. Claude asks
for a file by its path and gets back only masked text, so the original never reaches Anthropic.

```
/plugin marketplace add fikrifirat/katip
/plugin install katip-kalkan@katip
```

Or download `katip-kalkan.mcpb` and double-click it to install in Claude Desktop. You need
Python 3.10 or later. If [uv](https://docs.astral.sh/uv/) is installed, Katip fetches its three
helpers (onnxruntime and numpy for the name model, cryptography for the encrypted map) once on
first start. Without them it still runs, on rules only and with the map in memory only, and
`katip_status` says so.

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

Then try:
* "Summarise ~/Dosyalar/2026-123/dilekce.docx for matter 2026/123."
* "Compare the plaintiff's claims in dilekce.udf with the expert report bilirkisi.docx."
* "Draft a reply and save it with the real names to ~/Desktop/cevap.txt."

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
| `mask_file` | Opens a .docx, .udf, .txt, .pdf, scan or phone photo on your computer (OCR runs locally) and masks it | masked text, counts |
| `write_masked_copy` | Saves `name.maskeli.docx` next to the original | path |
| `restore_to_file` | Puts the real values back into the AI's text and saves it on your computer | path and count only |
| `forget_matter` | Deletes a matter's placeholder map | ok |
| `katip_status` | Shows the engine, threshold and where the map is kept | status |
| `open_masked_document` (relay) | Opens a share code | masked text |

## Developers

```
cd connector
python -m pytest -q                       # 23 tests: formats, model, profiles, OCR, vault crypto, stdio MCP, relay
python -m katip_kalkan.local_server       # stdio MCP server
python -m katip_kalkan relay --port 8787  # relay (put TLS in front)
python build_bundle.py                    # dist/katip-kalkan.mcpb
claude plugin validate ./connector
bash tests/e2e_claude_code.sh            # real Claude Code run through the plugin
```

There are no required dependencies; `onnxruntime`, `numpy`, `cryptography` and `pymupdf` are
optional. The detection engine is `katip_kalkan/engine.zip`, the same bundle the browser app runs
(`docs/katip_py.zip`; `build_bundle.py` refreshes it). `ner.py` is the Python twin of `src/ner.js`:
same spans as `ml/eval_system.py` on all 183 eval documents, and its WordPiece matches Hugging
Face `tokenizers` exactly.
Settings: `KATIP_THRESHOLD` (0.7), `KATIP_MODEL` (folder or `none`), `KATIP_TRUST`,
`KATIP_PROFILE` (`ai`, `court`, `anon`), `KATIP_OCR` (`auto`, `paddle`, `tesseract`), `KATIP_ALLOWED_DIRS`, `KATIP_VAULT_DAYS` (30),
`KATIP_RELAY_TTL` (900 s), `KATIP_RELAY_MAX_READS` (1), `KATIP_RELAY_UPLOAD_TOKEN`.

Blind set (80 synthetic legal documents, 757 values, threshold 0.7, whole-address scoring):
rules only 717, rules + Nano v1 739, rules + Nano v1.1 743. Masked `.udf` copies drop
`sign.sgn` (the e-imza certificate carries the signer's name).
