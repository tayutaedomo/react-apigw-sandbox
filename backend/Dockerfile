# タグの移動で内容が変わらないよう、各ベースイメージを digest で固定する。
FROM ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 AS uv
FROM public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0@sha256:17cfd08eff1dfea3f6a9a1e9c65fdac80aa4919b6085e746615530f43f57d2f1 AS adapter
FROM python:3.13-slim-bookworm@sha256:5024f48ba9441d4b13a95d3945abc6365538e3a31109833367a1923523c6efed AS os-base

# builder と runtime が同じ更新済み OS パッケージを使用する。
# update と upgrade を同じ RUN に置き、古い一覧で更新しないようにする。
# apt の一覧とキャッシュは同じレイヤー内で削除し、実行イメージへ残さない。
# OS パッケージはビルド時の配布版へ更新するため、同じ base digest でも
# ビルド日によって結果が変わる。配布・実行には完成したイメージの digest を使う。
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

FROM os-base AS builder

# uv は builder のみに置き、lockfile から実行時依存だけを作成する。
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
ENV UV_PYTHON_DOWNLOADS=never
RUN uv sync --locked --no-dev --no-install-project --no-cache

# runtime には仮想環境・アプリ・Adapter のみを追加する。
# uv、lockfile、テスト依存はコピーしない。Python ベースの内容は含まれる。
FROM os-base AS runtime
# 非 root の UID/GID を作る。アプリは root 所有のまま読み取り・実行のみ許可する。
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY --from=adapter /lambda-adapter /opt/extensions/lambda-adapter
COPY --from=builder /app/.venv /app/.venv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    AWS_LWA_PORT=8080 \
    AWS_LWA_READINESS_CHECK_PATH=/hello \
    AWS_LWA_READINESS_CHECK_HEALTHY_STATUS=200 \
    POWERTOOLS_SERVICE_NAME=sandbox-api
WORKDIR /app
COPY app ./app
# ローカル Docker の既定ユーザー。Lambda はプラットフォームの実行ユーザーを使うため、
# AWS 上でファイルの読み取りと Adapter の実行権限を別途確認する。
USER 10001:10001

EXPOSE 8080
CMD ["python", "-m", "app.server"]
