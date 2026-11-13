# Katip Kalkan connector: design

Status: prototype (v0.1, November 2026). Everything below about laws and store rules was
checked on 13 Nov 2026 and needs a lawyer's review before we rely on it.

## 1. The question

Lawyers want to keep using ChatGPT and Claude. We want to sit in between as a connector, so
personal data is masked before the AI reads a client document. Can we make sure the raw file
never reaches OpenAI's or Anthropic's servers?

**Short answer: not with a normal remote connector.** In MCP, the model fills in the tool's
arguments. If ChatGPT or Claude is going to "send the file to Katip", it must first have the
file, which means the file has already been uploaded to their servers. A remote connector can
only clean up after the leak.

There are three ways to get the file to us before the AI sees it.

| | (a) Local connector | (b) Mask on device, connector fetches by code | (c) Browser extension that catches uploads |
|---|---|---|---|
| How it works | A small Katip program runs on the lawyer's computer. Claude asks it for `~/Dosyalar/dilekce.docx`; Katip opens the file there and gives Claude only masked text. | The lawyer drops the file into the Katip app, where it is masked on the computer. Katip shows a one-time code. The lawyer pastes the code into ChatGPT, and our remote connector returns the masked text. | An extension on chatgpt.com and claude.ai swaps the file for a masked version as it is uploaded. |
| Does the original reach the AI company? | No. Only the path and the masked text do. | No. Only the code and the masked text do. | Usually no, but it depends on their web page staying the same. |
| What our server sees | Nothing. There is no server. | Encrypted masked text for up to 15 minutes, in memory only. | Nothing, if the extension masks locally. |
| Works in | Claude Desktop, Claude Code, Cowork | ChatGPT web, desktop and mobile; claude.ai web and mobile; any MCP client | Chrome or Edge on a desktop only |
| UX | Best: "summarise the petition on my desktop" | One extra step: drop the file, copy the code, paste it | Invisible when it works, and confusing when it breaks |
| Store listing | Anthropic directory, as a **plugin** (see 4) | OpenAI app directory and Anthropic connector directory (remote MCP) | Chrome Web Store only, not the AI stores |
| Weak spot | The model could still open the file with another tool. We block this in the skill and say it in the docs. | It's one extra step, and the code passes through the AI company (but it only unlocks masked text). | It breaks whenever the site changes, and may conflict with their terms. It doesn't cover the desktop apps or mobile. |

## 2. Recommendation (MVP)

Build **(a) for Claude and (b) for ChatGPT**. Both use the same engine and the same placeholder
map, and this PR contains both.

* **(a) gives the strongest guarantee and the best UX**, and Anthropic's directory now takes
  local servers as plugins, which gets us into a marketplace.
* **(b) is the only way into ChatGPT.** OpenAI limits local MCP plugins to approved partners.
  It also fits OpenAI's data rules. Their guidelines say apps must not "collect, solicit, or
  process" government identifiers (T.C. kimlik no) or health data. A remote Katip that
  received raw client files would break that rule, but the relay only ever receives masked
  text, so it doesn't.
* (c) stays a later add-on. We already have a text-only prototype in `katip-redact/extensions/kalkan-chrome`.

## 3. How the prototype works

```
 Lawyer's computer                                   AI company           Katip relay
 ────────────────────────────────────────────        ──────────           ───────────
 (a) dilekce.docx ──► katip-kalkan (stdio MCP) ──masked text──► Claude
                         │ vault: [AD SOYAD-1] = …  (AES-256-GCM, never leaves)
                         ▼
     final.docx  ◄── restore_to_file ◄──── text with placeholders ── Claude

 (b) dilekce.docx ──► Katip app / CLI: mask, encrypt with one-time key K
                         └──── nonce + ciphertext ─────────────────────────────► RAM, 15 min, 1 read
     code "katip-<id>.<K>" ──paste──► ChatGPT ──open_masked_document(code)──────► decrypt in memory,
                                              ◄────────── masked text ─────────── delete
```

**Placeholders.** Each value becomes a typed, numbered label such as `[AD SOYAD-1]`,
`[T.C. KİMLİK NO-1]` or `[ADRES-2]`. A *matter* label (for example `2026/123`) keeps the
numbers the same across every document in the case, so the AI can reason across them ("the
plaintiff in the petition is the patient in the medical report"). Once a value is found, it is
masked everywhere it appears in the document and in later documents of the same matter
(`_propagate` in `core.py`).

**Re-identification ("unmask") stays on the device.** `restore_to_file` takes the AI's text,
puts the real values back, and writes a local file. The tool result returns only the path and
a count. If we returned the restored text, the real names would go straight back to the AI,
which defeats the point.

**Leak check.** Before masked text is returned, every detected value is searched for in the
output. If one is still there, the call fails and nothing is returned.

## 4. Marketplace rules (checked 13 Nov 2026)

**Anthropic connector directory**
([submission](https://claude.com/docs/connectors/building/submission.md),
[policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy),
[remote guide](https://support.claude.com/en/articles/12922490)):
* Local servers: "desktop extension listings in the directory are deprecated, and the directory
  no longer accepts local servers packaged as MCP Bundles (MCPB). To distribute a local server
  through the directory, include it in a plugin". **So our listing is the plugin in
  `connector/`** (`.claude-plugin/plugin.json`, `.mcp.json`, a skill). The `.mcpb` file still
  works for a direct one-click install.
* Every tool needs `title` and `readOnlyHint` / `destructiveHint` annotations. Ours have them,
  and a test checks it.
* We need a privacy policy (`PRIVACY.md`), three example prompts, a test account with sample data
  for remote servers, and results under 25k tokens. We page at 40k characters, roughly 10–12k tokens.
* Legal is a "high-risk use case" under the usage policy, so we need human-in-the-loop wording
  and disclosure. Katip keeps the lawyer as the reviewer, and the README says so.
* Remote servers need HTTPS and Streamable HTTP. OAuth is needed only when there are user
  accounts. The relay has no accounts: holding the code is the permission.

**OpenAI apps / plugins**
([guidelines](https://developers.openai.com/apps-sdk/app-submission-guidelines),
[submission](https://developers.openai.com/apps-sdk/deploy/submission)):
* Submissions come from a verified individual or organisation, with a public HTTPS endpoint,
  privacy policy, terms, support and website URLs, test cases and a demo video.
* Restricted data: "Do not collect, solicit, or process … Government identifiers … Protected
  health information". This is why the ChatGPT side must stay mask-on-device. Special-category
  data is allowed only if strictly necessary, with consent and prominent disclosure.
* Annotations: `readOnlyHint`, `destructiveHint` and `openWorldHint` must be explicit booleans.
* Local MCP: "Local MCP submissions are limited to approved partners". This comes from a
  summary of the desktop-only page and needs re-checking. Either way, (a) is not a ChatGPT
  option for us today.

## 5. Security

| Goal | What the prototype does | Before production |
|---|---|---|
| Zero retention (relay) | Drops live only in RAM, expire after 15 min (`KATIP_RELAY_TTL`), and are deleted after 1 read (`KATIP_RELAY_MAX_READS`). No disk and no database. | Run on hosts with no swap or with encrypted swap, turn off core dumps, and keep the relay in Turkey for residency. |
| Ciphertext only at rest | The device encrypts with a fresh 128-bit AES-GCM key. The relay stores only the nonce and ciphertext, and the key exists only in the code. | Add a per-firm upload token (`KATIP_RELAY_UPLOAD_TOKEN`, already supported) and rate limits. |
| In transit | The relay sends HSTS. | Put TLS 1.3 in front (Caddy or nginx), as both stores require HTTPS. |
| No content logs | The access log has method, path, status and byte count only. MCP logs have the method and duration. Tests check that no code, key or value appears in logs. | Use the same rule for the reverse proxy: no request bodies, no query strings. |
| Vault at rest (device) | AES-256-GCM. The key is in the macOS Keychain or a 0600 file. File names are an HMAC of the matter. The vault expires after 30 days (`KATIP_VAULT_DAYS`). If `cryptography` is missing, the vault stays in memory only. | Windows DPAPI key storage, and per-platform `cryptography` wheels in the MCPB bundle. |
| Scope | `--allow DIR` (MCPB setting) limits which folders Katip can open. Files over 25 MB are refused. Masked copies and restored files never overwrite existing files. | Signed MCPB and plugin releases. |
| Model misuse | The skill and server instructions tell Claude never to open originals with other tools. | Firms' Claude admins can turn off direct file access, and we document that. |

## 6. KVKK and VERBİS (to confirm with counsel)

* **Who is responsible.** The lawyer or law partnership is the data controller (*veri
  sorumlusu*), as the KVKK lawyers' guide of 22 Sep 2026 says. For path (a), Katip is
  software running on the controller's own computer, and Katip as a company processes no
  personal data. For path (b), Katip is a data processor (*veri işleyen*) for encrypted masked
  text, which calls for a data processing agreement (DPA) with each firm, even though we can't
  read the stored data.
* **Masked is not anonymous.** The firm can reverse the masking with its vault, and case facts
  can still point to a person. Under KVKK this is pseudonymised personal data, so text that
  goes to OpenAI or Anthropic may still be a **transfer abroad (Art. 9, as amended in 2024)**.
  Katip greatly reduces what leaves the firm. Special-category data (Art. 6: health, criminal
  records, religion and so on) is masked by default. Katip doesn't make the transfer legal on
  its own. Firms still need a lawful basis and safeguards for the AI provider, such as standard
  contracts or a business plan with training off and limited retention. We should say exactly
  this in sales, not "fully compliant".
* **VERBİS.** Lawyers practising under the Attorneyship Law are exempt from VERBİS registration
  by Board decision 2018/32. Whether law partnerships are exempt needs checking. Katip itself
  registers only if it crosses the thresholds as a controller of its own customer data.
  Processing client data for firms doesn't make us register for that data.
* **Privacy notice and breach.** Firms should mention AI tools and Katip in their client
  privacy notice (*aydınlatma metni*). Our relay design means a breach exposes at most
  encrypted masked text from the last 15 minutes. We still need a 72-hour breach notification
  runbook.

## 7. What's next

1. Add a "Send to ChatGPT" button in the Katip app (GitHub Pages), so masking and the code
   happen in the browser (WebCrypto) and lawyers don't need the CLI.
2. Done in v0.2: the connector runs Katip Mask Nano · tr v1.1 on the device (fixes the
   all-caps surname miss, `Emal YILDIRIM`) and takes Base · tr v2 via `install-model`.
3. Done in v0.3: scans and photos are read locally (PaddleOCR + Tesseract, "Otomatik" routing).
   Still open: burn-in PDF copies from the connector (MuPDF needs the Artifex licence for closed
   distribution); use the Katip app for those.
4. Bundle `cryptography` wheels per platform, sign releases, and submit the plugin.
5. Deploy the relay in a Turkish region behind TLS, then submit it to OpenAI and Anthropic.
