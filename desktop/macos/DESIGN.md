# Katip for Mac: first run and everyday use (design v0.5)

## Why

A lawyer downloads Katip.app and has to get from "what is this?" to "my client's names never reach the AI"
alone, with no terminal, no README and no call with us. Today the app is a bare menu with "Start engine", the
model choice and the Claude connection need a terminal or an extension file, and nothing says what happened.

**Success:** a lawyer on a new Mac opens the app, answers four short screens, and within two minutes masks a
document, pastes it into Claude, and puts the names back into the answer. Claude Desktop (or Claude Code) can
use Katip directly after one button.

**Anti-goals:** a setup that silently changes the lawyer's files or Claude settings; a wizard that is a wall of
text; anything that sends a document off the computer; an app that keeps memory busy while nobody uses it.

## Approaches considered

1. **Native SwiftUI window + menu bar, talking to the local engine** (picked). One app, Mac-native, the engine
   does all the Katip work; the app only shows and asks.
2. Reuse Klasör's web UI inside a WKWebView. Faster to ship, but two UIs to keep in sync, it looks like a web
   page, and Klasör's flow is folder-first, not "mask this, restore that".
3. Menu bar only, settings in a popover. Too cramped for a first-run guide and for reading masked text.

## First run (a window opens by itself the first time)

1. **Hoş geldiniz / Welcome.** One line on what Katip does, three promises (works on this Mac; nothing is
   uploaded; you check the result), one button.
2. **Hazırlık / Getting ready.** Registers and starts the engine; shows each check with a tick (engine
   started, case keys protected in the Keychain, legal texts index ready). Retry and "show log" on failure.
3. **Ad tanıma modeli / Name model.** Three cards: Nano (included, fastest), Mini (31 MB), Base (111 MB,
   most accurate, recommended). Picking Mini or Base downloads it with a progress bar; each file is checked
   against its pinned fingerprint. Offline: stays on Nano and says so.
4. **Claude'a bağla / Connect Claude** (optional). Detects Claude Desktop and Claude Code. One button each:
   adds Katip to that app (keeps a backup of the old settings file) and says to restart Claude. Already
   connected through the Katip extension: says so and does nothing. "Later" is fine.
5. **Hazır / Ready.** Tries it on a sample sentence right there, so the lawyer sees masking and restoring
   work, then points at the menu bar icon.

## Everyday window

Sidebar: **Maskele** (paste text or drop a file; profile; case label; masked result with Copy and Save),
**Geri yükle** (paste the AI's answer; real names back; Copy and Save), **Davalar** (case keys on this Mac,
with Forget), **Bağlantılar** (Claude Desktop, Claude Code, precedent search on/off, Resmî Gazete marked
"soon"), **Ayarlar** (model, idle minutes, open at login, show log, reset).

Menu bar: state, Open Katip, Mask clipboard, Restore clipboard, Start or Stop, Quit.

## Calls I made

- Turkish when the Mac's language is Turkish, otherwise English.
- The app writes Claude settings only on the lawyer's button press, merges instead of replacing, and keeps
  `claude_desktop_config.json.katip-backup`.
- Claude gets Katip through the same bundled engine (`katip-engine mcp`), so nothing else to install.
  Claude's config holds only that command; the MCP process reads `~/.katip/engine-settings.json` and follows it
  live, so switching precedent search or Downloads off reaches a running Claude within seconds (review finding).
  Resmî Gazete (needs the Chrome driver) stays out of the bundle for now.
- Claude Desktop's settings file keeps its permissions (it can hold other servers' tokens) and the backup is the
  file as it was before Katip ever touched it. A Katip that moved shows as "moved, connect again".
- Run from Downloads, macOS translocates the app; the welcome screen offers "Move and reopen" to Applications.
- Every screen of the window stays alive, so switching screens never loses pasted text.
- Open at login uses `SMAppService` (the Mac's own login items list), off by default.

## v0.3: Features and Models panels (25 Nov 2026)

**Why:** every extra Katip can do (precedent search, statute lookup, MASAK screening, ilan.gov.tr, the Trade
Registry Gazette) needs something before it works: consent to go online, a list download, a browser, or the
lawyer's own e-Devlet login. Hidden in a terminal or a Claude prompt, a lawyer never finds them. Models are the
same: which one is used, swapping, downloading, deleting.

**Approaches:** (A, picked) one panel per kind of thing, each feature a card with its own short setup, models
local only; (B) a hosted masking service as an "online model" (rejected: client text would leave the Mac);
(C) online AI for the research features (later, needs keys and cost). Fikri picked A.

**Features panel (Özellikler):** a card per feature with a state (Off, Needs setup, Ready, Problem), a switch and
a setup sheet that says what the feature sends where, and does the setup:

| Feature | Online? | Setup |
|---|---|---|
| Statute lookup (mevzuat_bak) | no | none, on by default |
| Precedent search (emsal_ara, geri_bildirim) | keywords to bedesten.adalet.gov.tr | consent (the switch) |
| MASAK screening (dd_screen, dd_record, dd_sources, dd_update) | masak.hmb.gov.tr lists | first download, refresh |
| ilan.gov.tr lookup (dd_ilan_lookup) | ilan.gov.tr, one name per run | a browser: Google Chrome, or download Chromium |
| Trade Registry Gazette (dd_gazette_lookup, dd_gazette_logout) | ticaretsicil.gov.tr, lawyer's login | a browser; login kept N hours (0 = every time); log out |

Switching a feature on runs its setup. Claude sees a feature's tools only while it is on and ready: the MCP
process filters `tools/list`, refuses calls to hidden tools, and sends `notifications/tools/list_changed` when
that changes, so a running Claude picks it up without a restart. Playwright ships inside the app; the browser
is the Mac's own Chrome, or Chromium downloaded on the lawyer's button press.

**Models panel (Modeller):** Nano (included), Mini and Base, plus any model folder the lawyer adds. Per model:
use as default, download (pinned, every file checked by SHA-256), delete (not Nano, not the one in use).
"Online" only means where a model is downloaded from (Hugging Face, pinned commit); masking never runs online.

## v0.4: Review queue, the lawyer as judge (25 Nov 2026)

**Why:** a missed name is the one failure that breaks Katip's promise (KVKK). The model knows when it is unsure,
but nobody sees that. Fikri asked for a queue of feedback "candidates" the lawyer can review any time, with a
judge's gavel, starting with the most impactful kind and planned so more kinds can join.

**First kind: masking.** Every time Katip masks (in the app or for Claude), two kinds of candidates are kept:

- *Unsure*: a name Katip masked with low confidence (score under 0.80). "Is this personal data?"
- *Possibly missed*: a word the model scored between 0.20 and the masking threshold that nothing masked. "Katip
  did not mask this. Should it have?"

The lawyer strikes the gavel: **Mask it** (always masked on this Mac from now on), **Not personal data** (never
masked again), or **Later**. Verdicts become the firm's own lists (`mask_terms`, `allow_terms`), which the engine
already supports and now applies to every document, in the app and in Claude. Each verdict can be undone; the
learned lists can be edited.

**Privacy:** candidates hold real client values, so the queue and the lists are encrypted with the vault key
(memory only when the vault is), never leave the Mac and are never exported. Candidates expire with the case keys;
forgetting a case drops its candidates and every word learned from them. The context shown around a candidate
has every other detected value replaced by •••.

**Safety calls (from the independent review):** if the lists can't be decrypted (Keychain refused, key changed),
masking stops with a clear message instead of running without the "always mask" list, and the Review screen
offers to start the lists again (the old file is set aside). "Not personal data" on a name Katip did mask asks
first, because it unmasks that word in every case; on a missed word it only closes the card. A failing feature
check never hides the masking tools from Claude. A model folder that went missing falls back to Nano.

**Planned next kinds** (the queue has a `kind` field and one card per kind):

| Kind | Candidate | Verdict | Learns | Can be shared? |
|---|---|---|---|---|
| precedent | an emsal_ara result not judged yet | on point / related / not relevant, would cite | ranking (grades.jsonl) | yes, public decisions only |
| dd_match | a "review" band DD hit | same person / not the same | match thresholds | no (third parties' data) |
| doctype | a document type read with low confidence | right / pick the type | the doctype packs | yes, type and keywords only |
| citation | a citation_check problem | real / typo / wrong | the statute index | yes |
| mask (export) | masking verdicts rewritten as invented sentences | approve each | the shared name model | yes, after the lawyer checks each |

## v0.5: Folders, About, and an app that never changes itself (25 Nov 2026)

**Why:** Fikri could not open the built app past the first step and kept getting macOS's "modify apps" prompt.
Two causes, both fixed: (1) the bundled engine wrote Python bytecode (`__pycache__`) inside Katip.app, which macOS
treats as one app changing another and which breaks the signature; it now never writes bytecode, Kalkan ships
precompiled (unchecked-hash .pyc) and the build drops leftovers. (2) Test runs and the real app shared one launchd
agent, so a test home could take over the real one; tests now use their own label (`KATIP_AGENT_LABEL`) and the app
rewrites an agent whose storage settings are not its own.

**Folders:** Settings lists every place Katip keeps something (documents folder, cases, models, MASAK lists,
gazette pages, precedents, settings, log, the Claude Desktop settings file) with Show in Finder; the same button
sits where each one matters (Models, Cases, the MASAK, gazette and precedent setups). Katip's own folders are
created when missing; the lawyer's folders never are.

**About:** version, build and engine version, what Katip does, who makes it, GitHub, report a problem, GitHub
Sponsors, the AGPL terms in plain words and every bundled component with its licence. No prices in the app.

**Not done:** Developer ID signing and notarisation. An ad-hoc signed app downloaded from the internet is
rejected by Gatekeeper; until it is notarised, the lawyer has to use right-click, Open once.

## How it was checked

`Katip --tour <folder>` walks the first run and every screen with real work (engine start, a real Mini download
with fingerprint checks, a Claude Desktop connection into a test settings file, masking) and saves a PNG per
step; run in English and Turkish, light and dark. Engine tests: `python -m pytest -q tests/`.
