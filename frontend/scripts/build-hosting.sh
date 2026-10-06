#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
frontend_dir="$(cd -- "$script_dir/.." && pwd)"
if (( $# > 1 )); then
  echo '使用方法: ./scripts/build-hosting.sh [API の HTTPS URL]' >&2
  exit 1
fi

# 接続先はビルド時に埋め込む。Terraform output を使うが AWS の更新は行わない。
api_url="${1:-$(terraform -chdir="$frontend_dir/../infra/app" output -raw api_base_url)}"
export VITE_API_BASE_URL="$api_url"
node --input-type=module <<'JS'
const url = new URL(process.env.VITE_API_BASE_URL);
if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) {
  throw new Error('API の接続先は認証情報・クエリ・フラグメントなしの HTTPS URL にしてください');
}
JS

cd -- "$frontend_dir"
npm run build
