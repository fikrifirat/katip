# Katip for Mac: first run and everyday use (design v0.2)

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

## How it was checked

`Katip --tour <folder>` walks the first run and every screen with real work (engine start, a real Mini download
with fingerprint checks, a Claude Desktop connection into a test settings file, masking) and saves a PNG per
step; run in English and Turkish, light and dark. Engine tests: `python -m pytest -q tests/`.
