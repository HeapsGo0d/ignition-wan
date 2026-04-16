#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_PATH="${1:-$ROOT_DIR/supir-workflows.zip}"

FILES=(
  "$ROOT_DIR/workflows/img_supir_upscale_sfw.json"
  "$ROOT_DIR/workflows/img_supir_upscale_nsfw.json"
  "$ROOT_DIR/workflows/img_supir_upscale_sfw_clean.json"
  "$ROOT_DIR/workflows/img_supir_upscale_sfw_detail.json"
  "$ROOT_DIR/workflows/img_supir_upscale_nsfw_clean.json"
  "$ROOT_DIR/workflows/img_supir_upscale_nsfw_detail.json"
)

for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: missing file: $f" >&2
    exit 1
  fi
done

zip -j "$OUT_PATH" "${FILES[@]}"
echo "Created: $OUT_PATH"
