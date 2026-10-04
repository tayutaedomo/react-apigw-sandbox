# バックエンド

## 概要

FastAPI で Hello World API を提供します。

- FastAPI: API と OpenAPI ドキュメント。
- Uvicorn: ローカルの HTTP サーバー。
- uv: 仮想環境と依存の管理。
- Powertools for AWS Lambda: HTTP リクエストと例外の JSON ログ。
- pytest / httpx2: API テスト。

以下のコマンドは、すべて `backend/` 内で実行します。

## 開発環境

### 必要なツール

- Python: `3.13` 以上。`pyproject.toml` の `requires-python` に定義。
- uv: `0.10.12` で検証済み。
- Docker Compose: ローカル起動と E2E のコンテナ管理。
- Docker と Buildx: コンテナのビルド・起動時に必要。

### セットアップ

lockfile に記録した依存をインストールします。

```sh
uv sync --locked
```

- 仮想環境: `.venv/` に作成。
- 直接依存: `pyproject.toml` で完全なバージョンを指定。
- 間接依存: `uv.lock` で固定。
- テスト依存: `dev` グループも標準でインストール。
- 実行時: `uv run` を使うため、仮想環境の手動 activate は不要。

## 起動と API の確認

### 開発サーバー

```sh
uv run --locked uvicorn app.main:app --reload --host localhost --port 8000
```

- API: `http://localhost:8000`。
- OpenAPI ドキュメント: `http://localhost:8000/docs`。
- `--reload`: ソース変更時にサーバーを再起動。
- 終了: `Ctrl+C`。

### Hello World

別ターミナルからレスポンスを確認できます。

```sh
curl http://localhost:8000/hello
```

- メソッド・パス: `GET /hello`。
- HTTP ステータス: `200`。
- 本文: `{"message":"Hello World"}`。

### CORS

ブラウザーからのアクセスは `http://localhost:5173` を許可します。

- 設定場所: `app/main.py` の `CORSMiddleware`。
- 許可メソッド: `GET`。
- credentials: 許可しません。
- `http://127.0.0.1:5173`: 別 Origin のため対象外。

CORS はブラウザーがレスポンスを読み取れるかの制御です。`curl` の疎通だけではブラウザーの動作は確認できないため、[e2e テスト](../e2e/README.md)も使用します。

## コンテナのビルドと起動

### イメージのビルド

ビルド専用スクリプトで、Lambda 向けの `linux/amd64` イメージを作成します。

```sh
./scripts/build-image.sh
```

- 既定のタグ: `sandbox-api:local`。
- タグの変更: `./scripts/build-image.sh sandbox-api:check`。
- Dockerfile: Python、uv、Lambda Web Adapter のイメージを digest で固定。
- アプリ依存: `uv.lock` からインストール。テスト依存は含めません。
- Lambda Web Adapter: `/opt/extensions/lambda-adapter` に配置。
- 出力: 単一アーキテクチャのイメージをローカル Docker に読み込み。
- スクリプトの対象: ビルドのみ。ECR への push や AWS リソース作成は行いません。

### ローカルコンテナの起動

手動起動した API を停止してから、コンテナで同じ API を公開します。

```sh
docker compose up --no-build
```

- ホストの API: `http://localhost:8000`。
- コンテナ内: Uvicorn が `0.0.0.0:8080` で待ち受け。
- ファイルシステム: 読み取り専用。書き込み用に `/tmp` を用意。
- 終了: `Ctrl+C` の後に `docker compose down` でコンテナとネットワークを削除。
- ブラウザー検証: [e2e のコンテナテスト](../e2e/README.md#コンテナを使ったテスト)を使用。

ローカルでは Uvicorn に直接アクセスします。Lambda Web Adapter の Lambda イベント変換・拡張機能起動は、AWS 上で別途検証します。

### 実行イメージと権限

ビルド環境を分離し、通常のコンテナ実行は非 root に制限します。

- builder: uv で実行時依存の仮想環境を作成。
- runtime: Python ベースに仮想環境、アプリ、Web Adapter のみを追加。uv・lockfile・テスト依存はコピーしません。
- ユーザー: UID / GID `10001`。アプリのファイルは root 所有で、実行ユーザーから書き換えません。
- Compose: 読み取り専用、`/tmp` のみ書き込み可能、全 capability を削除、権限昇格を禁止。
- Lambda: プラットフォームが実行ユーザーを設定するため、AWS 上の権限と読み取り可能性はデプロイ時に確認する対象です。
- 適用範囲: Compose の制限は Dockerfile 自体や Lambda の設定へ自動的には引き継がれません。

これらは権限と同梱物を減らす対策です。ベースイメージの脆弱性がないことを保証するものではなく、digest の更新と脆弱性検査は別途必要です。

## 構造化ログ

### HTTP リクエストの記録

Powertools の Logger で、リクエスト完了・例外を JSON として標準出力へ記録します。

- `service`: `sandbox-api`。
- `method` / `path`: HTTP メソッドとパス。
- `status_code`: HTTP ステータス。
- `duration_ms`: 処理時間（ミリ秒）。
- `correlation_id`: Lambda の呼び出し ID。ローカルでは生成した UUID。
- `lambda_request_id`: Lambda の呼び出し ID。ローカルではフィールドを省略。
- `request_id_source`: `lambda` / `local` / `unavailable`。
- `X-Request-Id`: レスポンス開始を取得できる場合、同じ ID を付与。
- Lambda の ID: Web Adapter が渡す `x-amzn-lambda-context` の `request_id` を取得。
- readiness probe・コンテキスト不正: Lambda 内では ID を生成せず ID フィールドを省略（Powertools は `None` の値を除去）。
- 未処理例外の 500: 外側の FastAPI がレスポンスを生成するため、ID ヘッダーは付与されません。ログで追跡します。
- 例外: ERROR レベルで例外名とスタックトレースを記録し、例外を再送出。

リクエスト本文・クエリ文字列・認証ヘッダーは記録しません。メタデータはログごとに渡し、同時リクエスト間で共有しません。

仕様の参照: [Web Adapter のコンテキスト転送](https://github.com/aws/aws-lambda-web-adapter/blob/v1.1.0/src/lib.rs)。

### コンテナログの確認

別ターミナルで JSON ログを確認できます。

```sh
docker compose logs --follow api
```

- HTTP ログ: `app/request_logging.py` のミドルウェアで記録。
- Uvicorn の起動・終了ログ: `app/server.py` で Powertools の JSON formatter を使用。
- Uvicorn の標準アクセスログ: HTTP ログとの重複を避けるためコンテナでは無効化。
- 開発用の `uvicorn --reload`: アプリの HTTP ログは JSON、Uvicorn 自体のログは標準形式。

アプリの動作と相関 ID は HTTP ログ、サーバーの起動状態は Uvicorn ログで確認します。

### Uvicorn の JSON 化とログレベル

`app.server` から起動すると、Uvicorn の起動・終了・エラーログも JSON になります。

- 変更前の例: `INFO: Started server process [1]`。
- 変更後の主なフィールド: `level`, `message`, `timestamp`, `service`。HTTP 固有の情報はミドルウェアのログにのみ含みます。
- formatter: Powertools が Python の LogRecord を JSON へ変換。
- handler: 変換したログを標準出力へ送信。
- logger: `uvicorn.error` から `uvicorn` へ伝播させ、1回だけ出力。
- access log: 二重記録を避け、HTTP の記録はミドルウェアに集約。

```sh
POWERTOOLS_LOG_LEVEL=WARNING docker compose up --no-build
# Docker を使わず同じ JSON 設定で起動する場合（ポート 8080）
POWERTOOLS_LOG_LEVEL=DEBUG uv run --locked python -m app.server
```

- 既定: `INFO`。
- 許可値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`。
- `WARNING`: 正常リクエストと INFO の起動ログを抑制。ERROR の例外ログは出力。
- 不正な値: 起動時にエラーにして、設定の誤りを明示。
- `uvicorn --reload` を直接起動する場合: このサーバー設定を通らず、Uvicorn 自体は標準形式。

HTTP の ID 付き JSON と Uvicorn の JSON を標準出力へ集め、共通の環境変数で出力量を切り替えます。設定形式は [Uvicorn の Logging 設定](https://www.uvicorn.org/settings/#logging)を参照してください。

## テスト

### 実行コマンド

```sh
uv run --locked pytest
```

### 確認する内容

- `/hello` のステータスと JSON 本文。
- 許可 Origin に対する CORS ヘッダー。
- 未許可 Origin に許可ヘッダーを付けないこと。
- ステータス・処理時間・相関 ID を JSON に記録すること。
- 例外を記録し、500 レスポンスを維持すること。
- 同時リクエスト間で相関 ID とステータスを混同しないこと。
- 本文・クエリ文字列・認証ヘッダーを記録しないこと。

## 操作のまとめ

- セットアップ: `uv sync --locked`。
- 開発: Uvicorn を `--reload` 付きで起動。
- コンテナ: `./scripts/build-image.sh` でビルドし、`docker compose up --no-build` で起動。
- 検証: `uv run --locked pytest`。
