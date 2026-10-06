#!/usr/bin/env bash
set -euo pipefail

if (( $# > 1 )); then
    printf 'Usage: %s [image-digest-uri]\n' "$0" >&2
    exit 2
fi

app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# push の標準出力を保存したローカルファイルから読み取る。URI は Git に含めない。
if (( $# == 1 )); then
    image_uri="$1"
elif [[ -f "$app_dir/image-uri.txt" ]]; then
    image_uri="$(cat "$app_dir/image-uri.txt")"
else
    printf 'digest URI の引数、または image-uri.txt が必要です。\n' >&2
    exit 2
fi

exec terraform -chdir="$app_dir" plan -var="image_uri=$image_uri" -out=app.tfplan
