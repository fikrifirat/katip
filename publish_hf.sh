#!/usr/bin/env bash
# Publish the model and the Space to Hugging Face from your own machine.
#   pip install -U huggingface_hub && hf auth login      (token with write access)
#   ./publish_hf.sh [hf-username]
set -euo pipefail
U="${1:-fikrifirat}"
cd "$(dirname "$0")"
hf repos create "$U/katip-tr-name-tagger-tiny" --repo-type model --public --exist-ok
hf upload "$U/katip-tr-name-tagger-tiny" hf/model . --repo-type model --commit-message "katip-tr-name-tagger-tiny v1"
hf repos create "$U/katip-yerel" --repo-type space --space-sdk static --public --exist-ok
tmp="$(mktemp -d)"; cp -r docs/. "$tmp/"; cp hf/space/README.md "$tmp/README.md"
hf upload "$U/katip-yerel" "$tmp" . --repo-type space --commit-message "Katip Yerel demo"
echo "Model: https://huggingface.co/$U/katip-tr-name-tagger-tiny"
echo "Space: https://huggingface.co/spaces/$U/katip-yerel"
