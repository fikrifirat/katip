---
title: Katip Relay for ChatGPT
emoji: ⚖️
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: agpl-3.0
short_description: Remote MCP connector for ChatGPT; documents masked on device
---

# Katip relay (ChatGPT connector)

This is the server behind **Katip** in ChatGPT. Add it in ChatGPT as a custom MCP server at
`https://f1k-katip-relay.hf.space/mcp` (no authentication).

What it does:

- **open_masked_document**: opens a document the lawyer already masked on their own device with Katip. The
  device encrypts the masked text with a one-time key and uploads only the ciphertext; the key is in the share
  code (`katip-XXXX.YYYY`) that the lawyer pastes into ChatGPT. The relay keeps the ciphertext in memory for
  at most 15 minutes and deletes it after one read. It never receives the original document or a real name.
- **emsal_ara**: finds Yargıtay decisions. Only lowercase keywords go to the court's public search.
- **mevzuat_bak**: reads a statute article or checks citations, from an offline copy of mevzuat.adalet.gov.tr.
- **geri_bildirim**: saves the lawyer's verdict on a decision (decision id, query words, verdict; nothing
  that identifies the user).

Masked text is still personal data (pseudonymised), so read the work before you send it anywhere.
Code: [github.com/fikrifirat/katip](https://github.com/fikrifirat/katip) (`connector/katip_kalkan/relay.py`).
