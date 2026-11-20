# Katip in ChatGPT

ChatGPT can only use connectors that run on a server, so it can't open a file on the lawyer's computer the
way Claude Desktop does. Katip in ChatGPT works in two steps:

1. **Mask on the device.** The lawyer masks the document on their own computer, with the Katip web app or
   `katip-kalkan share`. The masked text is encrypted with a one-time key, and only the ciphertext is uploaded
   to the Katip relay. The device shows a share code such as `katip-AbC…xyz`.
2. **Paste the code into ChatGPT.** ChatGPT calls `open_masked_document`. The relay decrypts the text in memory,
   returns it and deletes it. Codes work once and expire after 15 minutes.

The relay never receives the original document or a real value. ChatGPT sees placeholders such as
`[AD SOYAD-1]`; the real values go back into ChatGPT's answer on the device (Katip web app "Paste the answer"
step, or `katip-kalkan restore answer.txt cevap.docx`).

In the same chat, the relay also offers the research tools from the Claude connector:

| Tool | What it does | What leaves the relay |
| --- | --- | --- |
| `open_masked_document` | Opens a share code | Nothing (it returns the masked text to ChatGPT) |
| `emsal_ara` | Finds Yargıtay decisions; results show as cards with the gavel ("Hüküm ver") button | Only the lowercase keywords, to bedesten.adalet.gov.tr |
| `mevzuat_bak` | Reads a statute article or checks every citation in a text | Nothing (offline index) |
| `geri_bildirim` | Saves the lawyer's verdict from the gavel button: Alakasız / İlgili / Atıf yaparım | Nothing; stored on the relay |

ChatGPT supports the MCP Apps standard, so the results view is the same file as in Claude
(`katip_kalkan/ui/emsal.html`). It has no network access; it talks only to ChatGPT.

## Differences from the Claude connector

- **No local file access.** There is no `list_files`, `mask_file` or `restore_to_file`; masking and restoring
  happen on the device, before and after the chat.
- **Ranking context.** Claude's `emsal_ara` masks the document on the computer and ranks against it. In
  ChatGPT, `baglam` (one or two masked sentences stating the issue) does that job. The relay refuses `baglam`
  if it holds a run of 5+ digits, an e-mail address or a link, so an unmasked ID number can't be passed by
  mistake. It uses `baglam` in memory and doesn't store it.
- **Query check.** On the computer, Katip also refuses a query word that belongs to a value masked in that
  matter. The relay has no vault, so it can't; but ChatGPT never saw the real values, only placeholders, and
  the lowercase-words-only rule still applies (no capitals, digits or signs).
- **Verdicts are stored on the relay**, not on the lawyer's computer: the decision id, the query words, the
  rank and the verdict, with no user id and no free-text note (`geri_bildirim` has no `not` field here).

## Run the relay

The relay is one Python file plus the research modules; its only dependency is `cryptography`.

```
cd connector && pip install cryptography
KATIP_HOME=/var/lib/katip python -m katip_kalkan relay --host 0.0.0.0 --port 8787   # put TLS in front
```

**Hugging Face Space (simplest for the beta):** `./publish_relay.sh` (from the repo root, after
`hf auth login`) creates the Docker Space `<user>/katip-relay` in the EU region and uploads only the Python
package with `hf/relay/Dockerfile`. The connector URL is then `https://<user>-katip-relay.hf.space/mcp`.
On a free Space, a restart clears the stored verdicts (drops are meant to be short-lived anyway); add a
Space volume or move to a small server when verdicts start to matter.

Settings: `PORT` (8787), `KATIP_RELAY_TTL` (900 s), `KATIP_RELAY_MAX_READS` (1), `KATIP_RELAY_MAX_KB` (2048
per drop), `KATIP_RELAY_MAX_TOTAL_MB` (256), `KATIP_RELAY_DROPS_PER_HOUR` (60 uploads per address),
`KATIP_RELAY_ORIGINS` (web origins allowed to upload, e.g. `https://fikrifirat.github.io`),
`KATIP_RELAY_UPLOAD_TOKEN` (optional bearer token for uploads; the CLI reads it too),
`KATIP_RELAY_PUBLIC_URL` (sets the view's `domain` for ChatGPT), `KATIP_EMSAL_ONLINE` (precedent search is off
unless this is `1`; the relay's Dockerfile sets it), `KATIP_HOME` (where decision texts, runs and verdicts are kept).

## Add it to ChatGPT (testing)

In ChatGPT: Settings → Apps & Connectors → Advanced → turn on Developer mode. Then add a custom MCP server:
name "Katip", URL `https://<user>-katip-relay.hf.space/mcp`, authentication "No authentication". In a chat,
pick Katip from the tools menu and paste a share code. (OpenAI renames these menus often; their guide is
"Connect from ChatGPT" in the Apps SDK docs.)

Publishing in the ChatGPT app directory needs a privacy policy URL that names the relay's host and region,
test prompts and screenshots. OpenAI's rules forbid apps that collect government ID numbers or health data:
the relay only ever receives masked text, which is why this design fits them.

## Share code format (for the web app and other clients)

- Payload: UTF-8 JSON `{"file_name", "kind", "masked_text", "entity_counts", "placeholders"}`. `placeholders`
  is the list of labels used, never values. `file_name` must be the safe (shortened) name.
- Encrypt with AES-GCM, a fresh random 128-bit key, a 12-byte random nonce and additional data
  `katip-drop-v1`. In the browser: `crypto.subtle.generateKey({name: "AES-GCM", length: 128}, true, ["encrypt"])`
  and `encrypt({name: "AES-GCM", iv: nonce, additionalData: utf8("katip-drop-v1")}, key, utf8(json))`.
- `POST <relay>/v1/drops` with `{"nonce": b64url(nonce), "ciphertext": b64url(ct)}` (base64url, no padding).
  The answer is `{"id", "expires_in", "max_reads"}`; 429 means too many uploads from this address.
- Share code: `katip-<id>.<b64url(raw key)>` (id 16 chars, key 22 chars). Show it with a copy button and the
  line "Works once, for 15 minutes."
