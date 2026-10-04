# React / API Gateway Sandbox

React と FastAPI のローカル構成です。

## 必要なツール

- Node.js `26.5.0`
- npm `11.17.0`
- Python `3.13.11`
- uv（`0.10.12` で検証）

Node.js と npm のバージョンは `frontend/` と `e2e/`、Python は `backend/` に設定しています。
Vite+ はローカル依存なので、グローバルの `vp` インストールは不要です。

## セットアップ

リポジトリのルートで実行します。

```sh
npm --prefix frontend ci
npm --prefix e2e ci
uv sync --project backend --locked
npm --prefix e2e run browser:install
```

直接依存は完全なバージョンで指定し、間接依存は各ディレクトリの lockfile で固定しています。
通常のインストールには `npm ci` と `uv sync --locked` を使います。

## 起動

ターミナル1:

```sh
cd backend
uv run --locked uvicorn app.main:app --reload --host localhost --port 8000
```

ターミナル2（リポジトリのルート）:

```sh
npm --prefix frontend run dev
```

`http://localhost:5173` に Hello World が表示されます。
「API を呼び出す」を押すと `GET http://localhost:8000/hello` を呼び、
`API: Hello World` を表示します。
API ドキュメントは `http://localhost:8000/docs` です。

## 設定

API URL の既定値は `http://localhost:8000` です。
変更する場合は `frontend/.env.example` を `frontend/.env.local` にコピーし、
`VITE_API_BASE_URL` を編集して開発サーバーを再起動してください。
この値はブラウザーに公開されるため秘密情報は入れません。

CORS の許可 Origin は `http://localhost:5173` のみです。
`127.0.0.1` で開いた画面は対象外です。credentials は送信しません。
ブラウザーから API を直接呼び、Vite プロキシは使いません。

`frontend/package.json` の Vite alias と override は、React プラグインを
Vite+ の固定 core に接続するための設定です。

## テスト

```sh
npm --prefix frontend run check
npm --prefix frontend run build
uv run --directory backend --locked pytest
npm --prefix e2e test
```

API テストは Hello レスポンスと Origin の許可・不許可を確認します。
Playwright は frontend と backend を自動起動し、実 API 疎通と通信失敗後の再試行を確認します。
手動で起動したサーバーはテスト前に停止してください。
