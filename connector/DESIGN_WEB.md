# Katip on claude.ai and ChatGPT web: options and decision

Status: decision draft, 16 November 2026. No code in this PR. The legal points are our reading and need a
lawyer's review. Platform rules were checked on 16 Nov 2026 and change often.

## 1. The question

Kalkan works today in Claude Desktop, Claude Code and Cowork because it runs on the lawyer's computer.
claude.ai web and ChatGPT web can only call **remote** MCP connectors: servers on the public internet that
Anthropic's or OpenAI's cloud calls over HTTPS. How do we give web users the same protection?

## 2. Two facts that decide most of it

**1. A remote tool that receives the document is too late.** In MCP, the model writes the tool's
arguments. If Claude or ChatGPT passes a document to a "mask this" tool, the model already has the document,
so it is already on Anthropic's or OpenAI's servers. Masking after that protects nothing. So the document must
reach Katip by some route that does not go through the chat: the lawyer's browser, an extension, or the firm's
own file server.

**2. Encryption doesn't help if the server has to read the text.** To find names, the server must see the
words in plain text. TLS protects the text on the way, and "zero retention" means we delete it afterwards, but
while it is being masked our server process reads everything. No form of encryption we could ship changes
that. (Homomorphic encryption can in theory run a model on encrypted data, but for a BERT tagger it is
research work and orders of magnitude too slow.) The only ways to avoid seeing the text are to mask on the
lawyer's device or inside hardware we cannot read (option D).

## 3. Options

| | Who sees the raw document | Katip's role under KVKK | Works in | Cost to run | Effort |
|---|---|---|---|---|---|
| **A. Katip-hosted masking server** | Katip's server (in memory) | Processor (*veri işleyen*): DPA with every firm | claude.ai web + mobile, ChatGPT web + mobile | Medium: CPU server for Base, 24/7 | 1–2 weeks code, plus legal and security work that never ends |
| **B. Browser extension** | Nobody but the lawyer's browser | None for content | Chrome/Edge desktop only | ~0 | 3–4 weeks, then upkeep each time the sites change |
| **C. Firm-hosted remote MCP** (own server or Kasa) | The firm's own server | None for content (the firm runs it) | claude.ai web + mobile, ChatGPT web + mobile | The firm's server; our support | ~2 weeks on top of the existing Helm/compose |
| **D. A or C inside a TEE** (confidential computing) | Nobody outside the enclave, if attestation is checked | Still a processor (A) | Same as A | High | Weeks to months |
| **E. Mask in the Katip web app, hand over by code** (the relay we already have) | Nobody but the lawyer's browser | Processor only for encrypted masked text, held ≤15 min | claude.ai web + mobile, ChatGPT web + mobile | Very low: one small VM | ~1–2 weeks |

### A. Katip-hosted remote MCP with zero retention

The lawyer uploads the document to a Katip page (not to the chat). Katip's server masks it and Claude or
ChatGPT fetches the masked text by id. Variant: host it on Hugging Face Spaces.

* **Privacy truth.** Katip's server reads every raw client document. "Zero retention" (RAM only, no logs, delete
  after reading) limits the damage of a breach, but nobody outside Katip can check it without an audit.
* **KVKK.** The firm stays the controller and Katip becomes its processor. That needs a written processing
  agreement (KVKK m.12(2) makes the controller jointly responsible for the processor's security), security
  measures, and a 72-hour breach procedure. Health and criminal data (m.6) would pass through us in clear.
* **Hosting place.** HF Spaces run on HF's cloud outside Türkiye, and we cannot pick a Turkish region. Raw
  data going there is a transfer abroad under m.9 (as amended by Law 7499): the firm needs an m.5/m.6 condition
  **and** an adequacy decision or an appropriate safeguard, such as standard contracts notified to the Board
  within five business days. A Turkish host (a local cloud or colocation) removes that leg of the transfer,
  though the masked text still goes abroad to the AI provider afterwards.
* **Avukatlık Kanunu m.36.** The lawyer's secrecy duty covers what they show to any outside service. Using a
  processor under contract is common (e-mail, cloud storage), but every extra party that reads the full file is
  something the lawyer has to justify. The Board's lawyers' guide (22 Sep 2026, pp. 120–121 and 146) points the
  other way: it recommends masking or anonymising **before** sharing with AI tools. A service where raw files
  go to a third party first works against that advice.
* **Platform.** Fine on both. ChatGPT's app rules forbid apps that "collect, solicit, or process" government
  IDs or health data, so the remote MCP side must only ever return masked text (it would).
* **Verdict.** Technically easy, but it turns Katip from "we never see your data" into a processor of the most
  sensitive files a firm has. It also breaks the sentence in our privacy statement that is our main selling
  point. Not recommended. HF in particular is the wrong place for raw client files.

### B. Browser extension that masks inside claude.ai and ChatGPT

The extension masks the text or file in the page, with Mini or Nano running locally, before it is pasted or
sent.

* **Privacy truth.** Nothing leaves the computer unmasked, as long as the extension catches it. A file
  dragged in a way the extension doesn't handle, or text typed straight into the chat box, goes out as is.
* **KVKK / m.36.** Same as the local Kalkan: Katip processes no client data. Fits the guide's "mask before
  sharing" advice.
* **Platform.** Chrome Web Store review, permissions on chatgpt.com and claude.ai, and the sites' terms may not
  welcome scripts that change their pages. It breaks when their page changes. No desktop apps, no mobile, and
  many firms lock down extensions.
* **Licences.** Text and .docx/.udf are fine. PDF burn-in uses MuPDF.js (AGPL), which needs the Artifex licence
  if we ship it in a closed extension. Keeping the extension under AGPL avoids that.
* **Verdict.** Good convenience later, built on the same engine as E. Too fragile to be the main path.

### C. Firm-hosted remote MCP (own server or Kasa)

The firm runs a Katip MCP server next to its own files (file server, DMS or Kasa). Claude asks for "the
petition in matter 2026/123"; the server reads it from the firm's storage and returns masked text.

* **Privacy truth.** Raw files stay inside the firm. Only masked text goes to the AI provider. Katip sees
  nothing.
* **KVKK / m.36.** The firm controls everything. It is the strongest position after on-device masking.
* **Platform.** The server must be reachable over public HTTPS from Anthropic's and OpenAI's clouds, which
  means opening a port. Anthropic publishes the IP range its connectors call from, so the firm can allowlist it,
  but that range is shared by all Anthropic customers, so it is not authentication. We need OAuth so only the
  firm's lawyers can open the firm's files: claude.ai supports OAuth (including a fixed client ID and secret),
  ChatGPT supports OAuth for custom apps. On Team/Enterprise plans an admin adds the connector for the firm.
* **Verdict.** The right product for mid-size and large firms and for Kasa customers. It is a sales-led
  deployment, not a self-serve web feature, so it doesn't answer "a solo lawyer on claude.ai".

### D. Confidential computing (TEE)

Run A or C inside an enclave (AMD SEV-SNP or Intel TDX confidential VMs, AWS Nitro Enclaves). The cloud host and
our own staff can't read memory, and a signed attestation proves which code is running.

* **Privacy truth.** Better than A, if someone checks the attestation. In the claude.ai and ChatGPT flow nobody
  does: the lawyer's browser talks to our upload page, and it would have to verify the attestation itself. Without
  that, it is "trust us" with extra steps.
* **KVKK.** We are still a processor; data in an enclave is still processed. m.9 still applies if the enclave is
  abroad. We have not found a confidential-VM offer in a Turkish region, and this needs checking.
* **Verdict.** Worth revisiting for a hosted enterprise tier. Too costly and too hard to prove for now.

### E. Mask in the Katip web app, hand over by code (recommended)

This is the relay already in `connector/katip_kalkan/relay.py`, plus a button in the web app.

1. The lawyer opens the Katip web app (GitHub Pages), drops the file, and it is masked in the browser with Mini
   (default) or Nano.
2. The browser encrypts the masked text with a fresh one-time key (WebCrypto, AES-GCM) and uploads only the
   ciphertext to the relay. It shows a code `katip-<id>.<key>`.
3. The lawyer pastes the code into claude.ai or ChatGPT. The remote tool `open_masked_document` decrypts it in
   memory, returns the masked text once, and deletes it. Drops expire after 15 minutes.
4. To put names back, the lawyer pastes the AI's answer into the web app. The placeholder map never left the
   browser.

* **Privacy truth.** Raw text never leaves the computer. The relay holds only encrypted masked text, for at most
  15 minutes, and can't read it without the code. The AI provider gets the code and the masked text, nothing
  more. Masking can still miss values, so the lawyer reviews the preview before sharing.
* **KVKK.** Masked text is pseudonymised and still personal data. For the relay, Katip is a processor of
  encrypted masked text, so we still offer a short DPA, but what a breach could expose is small. Hosting the
  relay in Türkiye avoids an m.9 transfer for that leg. The leg to the AI provider is the firm's transfer, as it
  is today with the local Kalkan.
* **Avukatlık Kanunu m.36.** Matches the guide's advice to mask before sharing with AI tools. The lawyer decides
  what goes out and sees it first.
* **Platform.** The relay needs no accounts: holding the code is the permission, so the connector can be
  authless. claude.ai allows authless custom connectors on all plans (Free users get one). ChatGPT needs a
  plan that allows custom apps or developer mode; which plans allow it has changed several times, so check before
  launch. Listing in OpenAI's app directory needs a verified organisation, a privacy policy and a demo. Works on
  mobile too, because the call comes from their cloud.
* **Baseline that works today.** The lawyer can already copy the masked text from the web app and paste it into
  the chat, with no server at all. The relay is worth building because long documents paste badly, it gives us
  a listing in both directories, and the code keeps the masked text out of the chat history.
* **Cost.** A small VM in a Turkish data centre with TLS. The relay is stdlib Python and keeps at most 256 MB in
  RAM.
* **Effort.** Relay: done, needs TLS, rate limits, a Turkish host, swap and core dumps off. Web app: a "Send to
  Claude / ChatGPT" button with WebCrypto, and a "Put names back" box (1–2 weeks with tests).

## 4. Decision

**Build E now.** It is the only option where a solo lawyer on claude.ai or ChatGPT web gets the same promise as
the local Kalkan: the raw document never leaves their computer. Most of it already exists, and it costs almost
nothing to run.

**Offer C to firms** (own server or Kasa) as the "fetch from our files" version, sold with deployment.

**Keep B as a later add-on** on the same engine, for lawyers who want it inside the chat page.

**Don't build A**, and don't put raw client documents on Hugging Face. Revisit D only if a large customer asks
for a hosted tier and will verify attestation.

## 5. What we say

We say: "The Katip web app masks your document in your browser. Claude or ChatGPT gets only the masked text,
through a one-time code. Our relay holds encrypted masked text for up to 15 minutes and cannot read your
original. You still check the result, and you still need a legal basis for sending data to an AI provider."

We don't say "KVKK-compliant", "KVKK-safe", "anonymous" or "end-to-end encrypted", and we don't say masking finds
every value.

## 6. Open questions

1. Turkish host for the relay: which provider, and does it allow no-swap, no-log VMs?
2. Which ChatGPT plans allow custom remote apps today (re-check at build time).
3. Should the web app keep the placeholder map only for the tab's life, or in encrypted browser storage so the
   lawyer can restore later?
4. DPA template for the relay, to review with counsel.

## Sources

* KVKK, *Avukatların Mesleki Faaliyetlerinde Kişisel Verilerin Korunmasına İlişkin Uygulama Rehberi* (KVKK
  Yayınları No. 115, 22 Sep 2026), pp. 120–121 and 146. Linked in [PRIVACY.md](../PRIVACY.md).
* KVKK m.4, m.5, m.6, m.9 (as amended by Law No. 7499), m.12; Avukatlık Kanunu m.36.
* Anthropic, [Getting started with custom connectors using remote MCP](https://support.claude.com/en/articles/11175166-getting-started-with-connectors-on-claude-ai):
  remote servers are called from Anthropic's cloud, must be public HTTPS, may be authless or OAuth.
* OpenAI, [App submission guidelines](https://developers.openai.com/apps-sdk/app-submission-guidelines):
  restricted data (government identifiers, health information).
* Earlier design for the local connector and the relay: [DESIGN.md](DESIGN.md).
