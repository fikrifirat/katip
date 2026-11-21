# Katip for iOS

A small SwiftUI app for one job: mask a document on the phone, send only the masked text to ChatGPT or
Claude, and put the real names back into the answer.

Status: first scaffold (v0.1.0). The engine bundle is tested in Chromium. The Swift code has not been built in
Xcode yet.

## What it does

1. **Pick a profile:** Court filing, Sharing with AI (the default), or Fully anonymous. These are the same
   profiles as the web app, the `katip-mask` packages and Kalkan (`sdk/spec/profiles.json`). "What it masks, and
   why" opens the profile: what stays readable, each data type with its reason, the KVKK article behind it and
   links to the sources.
2. **Bring a document:** choose a file (PDF, .docx, .udf, text, photo), scan paper with the document camera,
   paste text, or use "Open in Katip" from Files, Mail or WhatsApp. Scans and image-only PDFs go through Apple's
   on-device OCR.
3. **Check:** the masked text has its placeholders highlighted, with counts by type. You can keep a value
   readable or add a missed name or phrase, and the document is masked again.
4. **Send:** "Send to ChatGPT" or "Send to Claude" copies the prompt (your request, a note to keep the
   placeholders, and the masked text) and opens the provider. Short texts are also pre-filled through the
   `?q=` link. The share sheet and Copy work with any other app.
5. **Put names back:** paste the AI's answer. Placeholders are replaced from this document's map, on the phone.
   Placeholders that don't belong to this document are listed, not guessed.

## Privacy design

* **Same engine everywhere.** The app runs the `katip-mask` JavaScript SDK (rules plus Katip Mask Mini or Nano)
  in a hidden, offline `WKWebView`, so its output matches the web app, PyPI/npm and Kalkan exactly. Swift does
  the files, storage and UI.
* **No network for documents.** The engine page is served from the app bundle by a custom scheme handler
  (`katip-engine://`). Its CSP allows no other origin, and the web view uses a non-persistent data store. Model
  files are served only if their SHA-256 matches `sdk/spec/models.json`.
* **The map stays on the phone.** Documents and their placeholder maps are stored AES-256-GCM encrypted. The key
  is in the Keychain (`WhenUnlockedThisDeviceOnly`, never synced). The file has complete data protection, is
  excluded from backups, and is deleted after 30 days (same as Kalkan's vault). Settings has "Delete all".
* **Clipboard.** Masked text and restored answers are copied as local-only (no Universal Clipboard) and expire
  after 10 minutes.
* Files opened from other apps are deleted from the app's Inbox once they have been read.

Masked text is pseudonymised, so it is usually still personal data. The app says so ("Is masked text still
personal data?") and lists what Katip does and what the lawyer still has to do. We don't say "KVKK-safe",
"anonymous" or "no leakage". The guarantee is the engine's: every *detected* value is masked everywhere, or no
text is given out.

## Build (on a Mac)

Needs Xcode 16+, Node 22+ and XcodeGen (`brew install node xcodegen`).

```sh
ios/setup.sh
open ios/Katip.xcodeproj
```

`setup.sh` builds `sdk/js`, bundles the engine into `ios/Katip/Resources/Engine` (engine.js, onnxruntime-web
wasm, Mini and Nano from `docs/models`, checked against the pinned hashes), and generates the Xcode project.
Both are git-ignored. Pick your team under Signing & Capabilities and run on a phone or simulator.

Engine smoke test (Chromium, no Xcode needed): `node ios/engine/build.mjs && node ios/engine/smoke.cjs`.

## Layout

| Path | What |
|---|---|
| `engine/bridge.js` | `window.katip.mask / restore / extract` on top of the SDK; .docx/.udf text reader |
| `engine/build.mjs` | esbuild bundle + ORT wasm + models + `profiles.json` |
| `Katip/Engine` | `MaskEngine` (WKWebView bridge), `EngineSchemeHandler` (bundle-only, hash-checked) |
| `Katip/Input` | PDF text / OCR, Vision OCR, document camera |
| `Katip/Store` | Sessions, encrypted store, profiles |
| `Katip/Handoff` | ChatGPT / Claude hand-off, clipboard |
| `Katip/Legal` | Per-profile and per-type reasons, sources, sanctions |
| `Katip/Views` | Home, document (check · send · restore), profile details, settings |

## Still to check on a device

* The ChatGPT and Claude `?q=` links open the apps (universal links) with the text filled in. If not, the text is
  already on the clipboard and the lawyer pastes it.
* Mini's speed in the web view on an older iPhone (about 1 s per page in desktop browsers). Nano is the fallback
  in Settings.
* Vision OCR Turkish support differs by iOS version. The app checks it and warns when Turkish is missing.
* App size is about 50 MB because Mini (31 MB) and the ORT wasm (14 MB) ship inside it.

## Next

* Share extension, so the answer can be sent from the ChatGPT or Claude app straight to "Restore in Katip".
* A masked .docx/.udf/PDF file out, not only text (the web app already does this).
* The shared feedback control (grading what Katip found), once its design is settled for the MCP and web app.
* Licence: the app is AGPL-3.0 like the rest of the repo. That works for TestFlight and an open-source App
  Store listing, but check App Store terms against AGPL before a public release, or ship under the commercial
  licence.
