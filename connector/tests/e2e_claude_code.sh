#!/usr/bin/env bash
# End-to-end check through real Claude Code: install the plugin from this repo's
# marketplace, ask Claude to work on a client file, and verify that no gold value
# reached the model and that the restored letter has the real names.
#   bash connector/tests/e2e_claude_code.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
mkdir -p "$WORK/Dosyalar"
cp "$REPO/connector/tests/fixtures/dilekce_01.docx" "$WORK/Dosyalar/"
export KATIP_HOME="$WORK/.katip"
claude plugin marketplace add "$REPO" >/dev/null
claude plugin install katip-kalkan@katip >/dev/null
P=mcp__plugin_katip-kalkan_katip-kalkan__
cd "$WORK"
claude -p < /dev/null "Matter 2026/123. Summarise the petition at $WORK/Dosyalar/dilekce_01.docx in 5 Turkish bullet points, then draft a 3-sentence reply letter to the plaintiff's lawyer and save the final version with the real names to $WORK/cevap.txt." \
  --allowedTools "Read,Bash,${P}mask_file,${P}restore_to_file" \
  --output-format stream-json --verbose > run.jsonl
python3 - "$REPO/connector/tests/fixtures/dilekce_01.gold.json" "$WORK" <<'PY'
import json, sys
gold, work = json.load(open(sys.argv[1])), sys.argv[2]
raw = open(f"{work}/run.jsonl", encoding="utf-8").read()
calls = [c["name"] for l in raw.splitlines() for c in (json.loads(l).get("message") or {}).get("content", [])
         if isinstance(c, dict) and c.get("type") == "tool_use"]
print("tool calls:", calls)
leaked = [g["text"] for g in gold if g["text"] in raw]
print("full gold values seen by the model:", leaked or "none")
letter = open(f"{work}/cevap.txt", encoding="utf-8").read()
print("restored letter has real names:", any(g["text"].split()[0] in letter for g in gold if g["entity_type"] == "PERSON"))
assert not any(c in ("Read", "Bash") for c in calls), "Claude opened the file directly"
assert not leaked
PY
