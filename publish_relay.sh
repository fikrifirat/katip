#!/usr/bin/env bash
# Publish the Katip relay (ChatGPT connector) as a Hugging Face Docker Space from your own machine.
#   pip install -U huggingface_hub && hf auth login      (token with write access)
#   ./publish_relay.sh [hf-username]
# The Space gets only the Python package (no models, no OCR files) plus hf/relay/Dockerfile and README.md.
# The ChatGPT connector URL is then https://<user>-katip-relay.hf.space/mcp
set -euo pipefail
U="${1:-f1k}"
cd "$(dirname "$0")"
hf repos create "$U/katip-relay" --repo-type space --space-sdk docker --region eu --exist-ok >/dev/null
tmp="$(mktemp -d)"
cp hf/relay/Dockerfile hf/relay/README.md "$tmp/"
rsync -a --exclude "__pycache__" --exclude "models" --exclude "ocr_models" --exclude "engine.zip" \
  connector/katip_kalkan/ "$tmp/katip_kalkan/"
sed -i.bak "s#https://f1k-katip-relay#https://$U-katip-relay#" "$tmp/README.md" && rm -f "$tmp/README.md.bak"
hf upload "$U/katip-relay" "$tmp" . --repo-type space --delete "*" --commit-message "Katip relay"
hf spaces variables add "$U/katip-relay" -e KATIP_RELAY_ORIGINS=https://fikrifirat.github.io \
  -e KATIP_RELAY_PUBLIC_URL="https://$U-katip-relay.hf.space" >/dev/null 2>&1 || \
  echo "Set the Space variables KATIP_RELAY_ORIGINS=https://fikrifirat.github.io and KATIP_RELAY_PUBLIC_URL=https://$U-katip-relay.hf.space in its settings."
echo "Space:   https://huggingface.co/spaces/$U/katip-relay"
echo "ChatGPT: https://$U-katip-relay.hf.space/mcp"
