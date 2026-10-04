#!/usr/bin/env bash
set -euo pipefail

container_name="sandbox-api-e2e-$$"

cleanup() {
    docker rm --force "$container_name" >/dev/null 2>&1 || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

docker run --rm --init --platform linux/amd64 \
    --name "$container_name" \
    --read-only --tmpfs /tmp \
    --publish 127.0.0.1:8000:8080 \
    sandbox-api:local &

wait "$!"
