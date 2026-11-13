#!/usr/bin/env bash
# End-to-end check through real Claude Code: install the plugin from this repo's
# marketplace, ask Claude to work on a client file, and verify that no gold value
# reached the model and that the restored letter has the real names.
#   bash connector/tests/e2e_claude_code.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
mkdir -p "$WORK/Dosyalar"
cp "$REPO/connector/tests/fixtures/dilekce_01.docx" "$REPO/connector/tests/fixtures/kira_foto_01.pdf" "$WORK/Dosyalar/"
export KATIP_HOME="$WORK/.katip"
claude plugin marketplace add "$REPO" >/dev/null
claude plugin install katip-kalkan@katip >/dev/null
P=mcp__plugin_katip-kalkan_katip-kalkan__
cd "$WORK"
claude -p < /dev/null "Matter 2026/123. Summarise the petition at $WORK/Dosyalar/dilekce_01.docx in 5 Turkish bullet points, then draft a 3-sentence reply letter to the plaintiff's lawyer and save the final version with the real names to $WORK/cevap.txt." \
  --allowedTools "Read,Bash,${P}mask_file,${P}restore_to_file" \
  --output-format stream-json --verbose > run.jsonl
claude -p < /dev/null "Matter 2026/124. What are the parties, the rent and the duration in the photographed lease $WORK/Dosyalar/kira_foto_01.pdf? Three bullets." \
  --allowedTools "Read,Bash,${P}mask_file" --output-format stream-json --verbose > run_photo.jsonl
mkdir -p "$WORK/katip-documents"
cp "$REPO/connector/tests/fixtures/dilekce_01.udf" "$WORK/katip-documents/Reza Karimi - Vatandaşlık Dava Dilekçesi.udf"
KATIP_FOLDER="$WORK/katip-documents" claude -p < /dev/null "Matter 2026/125. Summarise the citizenship petition in my Katip folder in 3 bullets." \
  --allowedTools "Read,Bash,Glob,${P}list_files,${P}mask_file" --output-format stream-json --verbose > run_names.jsonl
python3 - "$WORK" <<'PY'
import json, sys
raw = open(f"{sys.argv[1]}/run_names.jsonl", encoding="utf-8").read()
uses = [c for l in raw.splitlines() for c in (json.loads(l).get("message") or {}).get("content", [])
        if isinstance(c, dict) and c.get("type") == "tool_use"]
print("file names: tool calls:", [(c["name"].split("__")[-1], c["input"]) for c in uses])
print("client name seen by the model:", [w for w in ("Reza", "Karimi") if w in raw] or "none")
assert not any(c["name"] in ("Read", "Bash", "Glob") for c in uses) and "Karimi" not in raw
PY
python3 - "$REPO/connector/tests/fixtures/kira_foto_01.gold.json" "$WORK" <<'PY'
import json, sys
gold, work = json.load(open(sys.argv[1]))["entities"], sys.argv[2]
raw = open(f"{work}/run_photo.jsonl", encoding="utf-8").read()
calls = [c["name"] for l in raw.splitlines() for c in (json.loads(l).get("message") or {}).get("content", [])
         if isinstance(c, dict) and c.get("type") == "tool_use"]
leaked = [g["text"] for g in gold if g["text"] and g["text"] in raw]
print("photo: tool calls:", calls, "| values seen by the model:", leaked or "none")
assert not any(c in ("Read", "Bash") for c in calls) and not leaked
PY
python3 - "$REPO/connector/tests/fixtures/dilekce_01.gold.json" "$WORK" <<'PY'
import json, sys
gold, work = json.load(open(sys.argv[1])), sys.argv[2]
raw = open(f"{work}/run.jsonl", encoding="utf-8").read()
calls = [c["name"] for l in raw.splitlines() for c in (json.loads(l).get("message") or {}).get("content", [])
         if isinstance(c, dict) and c.get("type") == "tool_use"]
print("tool calls:", calls)
leaked = [g["text"] for g in gold if g["text"] in raw]
print("full gold values seen by the model:", leaked or "none")
name_parts = sorted({w for g in gold if g["entity_type"] == "PERSON" for w in g["text"].split() if len(w) >= 4})
seen_parts = [w for w in name_parts if w in raw]
print("name parts seen by the model:", seen_parts or "none")
letter = open(f"{work}/cevap.txt", encoding="utf-8").read()
print("restored letter:\n" + letter)
print("restored letter has real names:", any(g["text"].split()[0] in letter for g in gold if g["entity_type"] == "PERSON"))
assert not any(c in ("Read", "Bash") for c in calls), "Claude opened the file directly"
assert not leaked and not seen_parts
PY
