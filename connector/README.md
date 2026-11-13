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
Python 3.10 or later. Run `pip install cryptography` to keep the placeholder map between
sessions; without it, the map lives in memory only.

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
| `mask_file` | Opens a .docx, .udf, .txt or text-layer .pdf on your computer and masks it | masked text, counts |
| `write_masked_copy` | Saves `name.maskeli.docx` next to the original | path |
| `restore_to_file` | Puts the real values back into the AI's text and saves it on your computer | path and count only |
| `forget_matter` | Deletes a matter's placeholder map | ok |
| `katip_status` | Shows the engine, threshold and where the map is kept | status |
| `open_masked_document` (relay) | Opens a share code | masked text |

## Developers

```
cd connector
python -m pytest -q                       # 15 tests: formats, vault crypto, stdio MCP, relay
python -m katip_kalkan.local_server       # stdio MCP server
python -m katip_kalkan relay --port 8787  # relay (put TLS in front)
python build_bundle.py                    # dist/katip-kalkan.mcpb
claude plugin validate ./connector
bash tests/e2e_claude_code.sh            # real Claude Code run through the plugin
```

There are no runtime dependencies; `cryptography` and `pymupdf` are optional. The detection
engine is `katip_kalkan/engine.zip`, the same bundle the browser app runs (`docs/katip_py.zip`).
Settings: `KATIP_THRESHOLD` (0.7), `KATIP_ALLOWED_DIRS`, `KATIP_VAULT_DAYS` (30),
`KATIP_RELAY_TTL` (900 s), `KATIP_RELAY_MAX_READS` (1), `KATIP_RELAY_UPLOAD_TOKEN`.

Known gap: the rules engine misses some all-caps surnames (`Emal YILDIRIM` becomes
`[AD SOYAD-1] YILDIRIM`). The BERTurk model fixes this in the browser app, and it's next for
the connector.
