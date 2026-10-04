#!/usr/bin/env bash
set -euo pipefail

if (( $# > 1 )); then
    printf 'Usage: %s [image-tag]\n' "$0" >&2
    exit 2
fi

backend_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
image_tag="${1:-sandbox-api:local}"

# OS 更新の RUN は毎回実行し、更新のない過去のレイヤーを再利用しない。
# 他ステージのキャッシュは利用する。Dockerfile を直接ビルドする場合も同じ指定が必要。
docker buildx build \
    --platform linux/amd64 \
    --no-cache-filter os-base \
    --provenance=false \
    --sbom=false \
    --load \
    --tag "$image_tag" \
    "$backend_dir"
