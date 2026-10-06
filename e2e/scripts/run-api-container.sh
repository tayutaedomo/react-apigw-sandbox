#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_name="sandbox-api-e2e-$$"
compose=(docker compose --project-name "$project_name" --file "$script_dir/../../backend/compose.yaml")

cleanup() {
    "${compose[@]}" down --timeout 5 >/dev/null 2>&1 || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# 起動設定は Compose に委譲し、このスクリプトはテスト固有の終了処理を担う。
ENABLE_ERROR_ENDPOINTS=true "${compose[@]}" up --no-build --abort-on-container-exit --exit-code-from api &
wait "$!"
