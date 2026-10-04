#!/usr/bin/env bash
set -euo pipefail

if (( $# > 1 )); then
    printf 'Usage: %s [image-tag]\n' "$0" >&2
    exit 2
fi

backend_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
image_tag="${1:-sandbox-api:local}"

docker buildx build \
    --platform linux/amd64 \
    --provenance=false \
    --sbom=false \
    --load \
    --tag "$image_tag" \
    "$backend_dir"
