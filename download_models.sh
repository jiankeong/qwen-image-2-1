#!/usr/bin/env bash
set -euo pipefail

DEST="${1:-/runpod-volume/models}"
REPO='abenzerps/Qwen-Image-2.1-Uncensored-GGUF'
BASE="https://huggingface.co/${REPO}/resolve/main"

download() {
  local relative="$1" target="${DEST}/$1"
  mkdir -p "$(dirname "$target")"
  curl --fail --location --retry 5 --continue-at - --output "$target" "${BASE}/${relative}"
  test -s "$target"
}

download 'qwen-image-2.1-UC-Q6_K.gguf'
mkdir -p "${DEST}/diffusion_models"
mv "${DEST}/qwen-image-2.1-UC-Q6_K.gguf" "${DEST}/diffusion_models/qwen-image-2.1-UC-Q6_K.gguf"
download 'text_encoders/qwen3vl_8b_int8_convrot.safetensors'
download 'vae/qwen_image_2.1_vae_bf16.safetensors'

printf 'Models ready in %s\n' "$DEST"
