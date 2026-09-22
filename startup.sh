#!/bin/sh
set -eu

export HF_HOME="${HF_HOME:-/runpod-volume/hf-home}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-/runpod-volume/hf-cache}"
export TMPDIR="${TMPDIR:-/runpod-volume/tmp}"
mkdir -p "$HF_HOME" "$HF_HUB_CACHE" "$TMPDIR"

if [ "${USE_MOCK_PIPELINE:-0}" != "1" ]; then
  python /bootstrap_models.py
fi
exec /start.sh
