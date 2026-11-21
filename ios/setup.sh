#!/bin/sh
# Builds the offline engine bundle and generates Katip.xcodeproj. Run from anywhere, once and after engine changes.
# Needs Node 22+ and XcodeGen (brew install node xcodegen).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/.." && pwd)
cd "$root/sdk/js" && npm ci --no-audit --no-fund && npm run build
cd "$root" && node ios/engine/build.mjs
cd "$here" && xcodegen generate
echo "Done. Open ios/Katip.xcodeproj, pick your team under Signing & Capabilities, and run."
