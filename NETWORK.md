# Every network call Katip can make

*Checked against the code on 25 Nov 2026. A pull request that adds a request updates this page
([CONTRIBUTING.md](CONTRIBUTING.md)). If you find one that isn't here, that is a security report
([SECURITY.md](SECURITY.md)).*

**No app sends telemetry or analytics.** Nothing reports usage, crashes or document counts anywhere.
Documents are masked on the device and are never uploaded to be masked.

"Opens a link" below means Katip asks the browser or the system to open a web address. Katip itself sends
nothing; the browser does what browsers do with an address.

## Web app (fikrifirat.github.io/katip)

| What | Where it goes | What is sent | When | How to avoid it |
| --- | --- | --- | --- | --- |
| The app's own files (engine, PDF and OCR libraries, name model) | the site itself | nothing (downloads only) | page load; OCR and model files on first use | – |
| Ask an AI with your own key (Anthropic or OpenAI) | api.anthropic.com or api.openai.com | the **masked** text and your question, with the key you typed | only when you enter a key and press Ask | don't enter a key; the key stays in your browser only if you tick "remember" |
| Send to Claude or ChatGPT | opens a link to claude.ai or chatgpt.com | the masked prompt travels **in the address**, so it can stay in browser history and the provider's logs | button press | use Copy instead and paste |
| Report a mistake | opens an e-mail draft | nothing until you send it yourself | button press | – |
| Statute, KVKK and source links | opens a link | nothing | click | – |

The page's Content-Security-Policy only lets it connect to its own site, so it can't load code or send
data anywhere else. The Chromium test `src/tests/tests_e2e_cep.cjs` fails if the letter page makes a request to
another site. `tests_e2e_demo.cjs` counts such requests for the main page but doesn't fail on them yet.

## Kalkan (Claude connector)

| What | Where it goes | What is sent | When | How to avoid it |
| --- | --- | --- | --- | --- |
| Install missing Python packages | PyPI, and a Python 3.12 download if none is found | nothing personal | first start, only if packages are missing | `KATIP_AUTO_DEPS=0` (then install them yourself) |
| OCR recognition model | huggingface.co (PaddlePaddle) | nothing | first scanned page, plugin installs only (the `.mcpb` file bundles it) | `KATIP_OCR_DOWNLOAD=0` |
| Mini or Base name model | huggingface.co/f1k | nothing | first use, only if `KATIP_MODEL` is `mini` or `base` (Nano is bundled) | keep the default, or `KATIP_MASK_OFFLINE=1` |
| EU name model (about 1.1 GB) | huggingface.co (urchade/gliner) | nothing | only if `KATIP_EU_NER=gliner` | off by default |
| Precedent search (`emsal_ara`) | bedesten.adalet.gov.tr | lowercase keywords (3+ letters, no digits, none of the masked values) and decision ids; logged in `~/.katip/emsal/requests.log` | when you or Claude search | **off by default**; turn on with the "precedent search" setting or `KATIP_EMSAL_ONLINE=1` |
| Sanctions lists (`dd_update`) | masak.hmb.gov.tr | nothing about anyone (downloads the public lists) | when Claude updates them | don't approve the tool |
| ilan.gov.tr lookup (`dd_ilan_lookup`) | www.ilan.gov.tr, in your own Chrome | **the name you are screening** | when Claude calls it | don't approve the tool |
| Trade Registry Gazette lookup (`dd_gazette_lookup`) | www.ticaretsicil.gov.tr, in your own Chrome | **the company name** and registry office, with your own e-Devlet login; cookies kept encrypted for 8 hours | when Claude calls it | don't approve the tool; `dd_gazette_logout` deletes the login; `KATIP_TSG_SESSION_HOURS=0` keeps none |
| Share a masked document (`katip-kalkan share`) | a relay you choose (`KATIP_RELAY_URL`; default 127.0.0.1) | the masked text, encrypted; the key stays in the share code | when you run the command | don't run it |
| Statute check (`mevzuat_bak`), grades (`geri_bildirim`) | nowhere | – | – | offline copy of the statutes; grades stay in `~/.katip` |

There is no update check: Kalkan updates through Claude's plugin system.

**The hosted ChatGPT relay** (f1k-katip-relay.hf.space) is a server, not part of Kalkan. It receives the
encrypted masked text you choose to share, keeps it in memory for at most 15 minutes and deletes it after one
read. Its precedent search is always on and sends keywords to bedesten.adalet.gov.tr.

## Klasör (desktop app)

| What | Where it goes | What is sent | When | How to avoid it |
| --- | --- | --- | --- | --- |
| Its own window | 127.0.0.1 only, random port and token | – | always | – |
| Base name model (about 110 MB) | huggingface.co/f1k | nothing | **first document, because Base is the default** | choose Nano or no model in settings, or `KATIP_MASK_OFFLINE=1` |
| OCR recognition model | huggingface.co (PaddlePaddle) | nothing | first scanned page | `KATIP_OCR_DOWNLOAD=0` |

## Python and JavaScript SDKs (`katip-mask`)

| What | Where it goes | What is sent | When | How to avoid it |
| --- | --- | --- | --- | --- |
| Name model | huggingface.co/f1k at a pinned commit, checked by SHA-256 | nothing | only when you pick a model (the default is rules only) or run `download` | `KATIP_MASK_OFFLINE=1`; a mirror with `KATIP_MASK_ENDPOINT` |

## iOS app (not released yet)

The engine runs from the app bundle in a web view with no network access. Send to ChatGPT or Claude opens a
link with the masked prompt in it (up to 6,000 characters), otherwise copies it to the clipboard for 10
minutes. Legal, privacy and source links open a link. The app makes no requests of its own.

## Known gaps, to be fixed

- The due-diligence tools (`dd_ilan_lookup`, `dd_gazette_lookup`, `dd_update`) are always on in Kalkan; only
  Claude's approval prompt stands between them and a request. They should follow the same off-by-default
  setting as precedent search.
- Klasör downloads Base on first use by default. It should ask first, or start with the bundled Nano.
- The web app's main-page test should fail, not just count, when a request goes to another site.
- The Send to Claude or ChatGPT links put the masked text in an address; the app should say so next to the
  button.
