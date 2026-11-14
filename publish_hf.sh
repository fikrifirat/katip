#!/usr/bin/env bash
# Publish the Katip Mask models and the demo Space to Hugging Face from your own machine.
#   pip install -U huggingface_hub && hf auth login      (token with write access)
#   ./publish_hf.sh [hf-username]
# First moves the old repos to the Katip Mask names once (hf/rename_to_katip_mask.py; safe to repeat).
# Katip Mask Nano: hf/nano (v1.1). Files no longer in the release are removed; v1 stays at the tag v1.0.
# Katip Mask Base: uploaded only if ml/berturk/out exists (after train_berturk.py); the Space then gets a copy
# of its browser files, so "Katip Mask Base" runs there. No retraining.
# Hugging Face serves large and binary files (samples, models, wasm, fonts) from its CDN after a redirect,
# so the Space copy of index.html allows *.hf.co and *.huggingface.co; still nothing but this site and HF.
set -euo pipefail
U="${1:-f1k}"
cd "$(dirname "$0")"
python3 hf/rename_to_katip_mask.py "$U"

hf upload "$U/katip-mask-nano" hf/nano . --repo-type model --delete "*" --commit-message "Katip Mask Nano · tr v1.1: CC BY-SA 4.0, credit Turkish Wiki NER"

BT=ml/berturk/out
if [ -f "$BT/onnx/model_quantized.onnx" ]; then
  cp ml/berturk/MODEL_CARD.md "$BT/README.md"; cp hf/LICENSE.models "$BT/LICENSE"
  hf upload "$U/katip-mask-base" "$BT" . --repo-type model --exclude "checkpoint-*" --commit-message "Katip Mask Base · tr v2: CC BY-SA 4.0, credit BERTurk and Turkish Wiki NER"
fi

tmp="$(mktemp -d)"; cp -r docs/. "$tmp/"; cp hf/space/README.md "$tmp/README.md"
python3 - "$tmp/index.html" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p, encoding="utf-8").read()
hf = " https://*.hf.co https://*.huggingface.co"
for d in ("connect-src", "script-src", "font-src", "img-src"):
    s = re.sub(rf"({d} [^;\"]*)", lambda m: m.group(1) + hf, s, count=1)
open(p, "w", encoding="utf-8").write(s)
PY
if [ -f "$BT/onnx/model_quantized.onnx" ]; then
  M="$tmp/models/katip-mask-base"; mkdir -p "$M/onnx"
  cp "$BT/config.json" "$BT/tokenizer.json" "$BT/tokenizer_config.json" "$M/"
  cp "$BT/onnx/model_quantized.onnx" "$M/onnx/"
  python3 -c "import json,sys; p=sys.argv[1]; r=json.load(open(p)); [m.pop('elsewhere', None) for m in r]; json.dump(r, open(p, 'w'), ensure_ascii=False, indent=1)" "$tmp/models/registry.json"
fi
hf upload "$U/katip-mask" "$tmp" . --repo-type space --delete "*" --commit-message "Katip Mask demo"
echo "Model: https://huggingface.co/$U/katip-mask-nano"
[ -f "$BT/onnx/model_quantized.onnx" ] && echo "Model: https://huggingface.co/$U/katip-mask-base"
echo "Space: https://huggingface.co/spaces/$U/katip-mask"
