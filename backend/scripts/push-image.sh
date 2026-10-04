#!/usr/bin/env bash
set -euo pipefail

if (( $# < 1 || $# > 2 )); then
    printf 'Usage: %s <remote-tag> [local-image]\n' "$0" >&2
    exit 2
fi

remote_tag="$1"
local_image="${2:-sandbox-api:local}"
if [[ ! "$remote_tag" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$ ]]; then
    printf 'ECR のタグは1〜128文字の英数字・アンダースコア・ピリオド・ハイフンで指定してください。\n' >&2
    exit 2
fi

backend_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ecr_dir="$backend_dir/../infra/ecr"
repository_url="$(terraform -chdir="$ecr_dir" output -raw repository_url)"
repository_name="$(terraform -chdir="$ecr_dir" output -raw repository_name)"

# 認証先は適用済み state から取得する。プロファイル名をスクリプトに埋め込まない。
# ECR の URL からリージョンを取得し、別リージョンへの誤った認証を避ける。
if [[ "$repository_url" =~ ^([0-9]{12}\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com(\.cn)?)/(.+)$ ]]; then
    registry="${BASH_REMATCH[1]}"
    region="${BASH_REMATCH[2]}"
    url_repository="${BASH_REMATCH[4]}"
else
    printf 'Terraform output の ECR URL が不正です。\n' >&2
    exit 1
fi
if [[ "$url_repository" != "$repository_name" ]]; then
    printf 'Terraform output のリポジトリ名と URL が一致しません。\n' >&2
    exit 1
fi

# ビルドと push は分離する。存在する単一 amd64 イメージだけを push する。
platform="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$local_image")"
if [[ "$platform" != 'linux/amd64' ]]; then
    printf 'linux/amd64 イメージが必要です（取得値: %s）。\n' "$platform" >&2
    exit 1
fi

# ログイントークンは標準入力で渡す。Docker の認証設定も一時ディレクトリに隔離する。
docker_auth_dir="$(mktemp -d)"
trap 'rm -rf -- "$docker_auth_dir"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
aws ecr get-login-password --region "$region" |
    docker --config "$docker_auth_dir" login --username AWS --password-stdin "$registry"

destination="$repository_url:$remote_tag"
docker image tag "$local_image" "$destination"
docker --config "$docker_auth_dir" push "$destination"

# 後続の Lambda は可変タグに依存せず、この digest URI でイメージを指定する。
digest="$(aws ecr describe-images --region "$region" --repository-name "$repository_name" \
    --image-ids "imageTag=$remote_tag" --query 'imageDetails[0].imageDigest' --output text)"
if [[ ! "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]; then
    printf 'push 後のイメージ digest を取得できませんでした。\n' >&2
    exit 1
fi
printf 'Image URI: %s@%s\n' "$repository_url" "$digest"
