#!/usr/bin/env bash
# Publish the models and the Space to Hugging Face from your own machine.
#   pip install -U huggingface_hub && hf auth login      (token with write access)
#   ./publish_hf.sh [hf-username]
# If ml/berturk/out exists (after train_berturk.py), the BERTurk model is uploaded too and
# the Space gets a copy of its browser files, so "Katip BERTurk" runs there. No retraining.
set -euo pipefail
U="${1:-f1k}"
cd "$(dirname "$0")"
hf repos create "$U/katip-tr-name-tagger-tiny" --repo-type model --public --exist-ok
hf upload "$U/katip-tr-name-tagger-tiny" hf/model . --repo-type model --commit-message "katip-tr-name-tagger-tiny v1"

BT=ml/berturk/out
if [ -f "$BT/onnx/model_quantized.onnx" ]; then
  hf repos create "$U/katip-tr-pii-berturk" --repo-type model --public --exist-ok
  cp ml/berturk/MODEL_CARD.md "$BT/README.md"
  hf upload "$U/katip-tr-pii-berturk" "$BT" . --repo-type model --exclude "checkpoint-*" --commit-message "katip-tr-pii-berturk v2: trained with real Turkish text"
fi

hf repos create "$U/katip-yerel" --repo-type space --space-sdk static --public --exist-ok
tmp="$(mktemp -d)"; cp -r docs/. "$tmp/"; cp hf/space/README.md "$tmp/README.md"
if [ -f "$BT/onnx/model_quantized.onnx" ]; then
  M="$tmp/models/katip-tr-pii-berturk"; mkdir -p "$M/onnx"
  cp "$BT/config.json" "$BT/tokenizer.json" "$BT/tokenizer_config.json" "$M/"
  cp "$BT/onnx/model_quantized.onnx" "$M/onnx/"
  python3 -c "import json,sys; p=sys.argv[1]; r=json.load(open(p)); [m.pop('elsewhere', None) for m in r]; json.dump(r, open(p, 'w'), ensure_ascii=False, indent=1)" "$tmp/models/registry.json"
fi
hf upload "$U/katip-yerel" "$tmp" . --repo-type space --commit-message "Katip Yerel demo"
echo "Model: https://huggingface.co/$U/katip-tr-name-tagger-tiny"
[ -f "$BT/onnx/model_quantized.onnx" ] && echo "Model: https://huggingface.co/$U/katip-tr-pii-berturk"
echo "Space: https://huggingface.co/spaces/$U/katip-yerel"
