# React / API Gateway Sandbox

## 概要

React の画面から FastAPI の Hello World API を呼び出せます。

- フロントエンド: React、Vite+、TypeScript 7。
- バックエンド: FastAPI。
- ブラウザーテスト: Playwright。
- 実行環境: ローカル。AWS リソースの作成・デプロイは含みません。

## セットアップ

### 必要なツール

以下のバージョンで実行します。

- Node.js: `26.5.0`
- npm: `11.17.0`
- Python: `3.13.11`
- uv: `0.10.12` で検証済み。

バージョン設定は各ディレクトリに配置しています。

- `frontend/` と `e2e/`: `.node-version` と `package.json`。
- `backend/`: `.python-version` と `pyproject.toml`。
- Vite+: プロジェクト内の依存を使用。グローバルの `vp` インストールは不要です。

### 依存のインストール

リポジトリのルートで実行します。

```sh
npm --prefix frontend ci
npm --prefix e2e ci
uv sync --project backend --locked
npm --prefix e2e run browser:install
```

依存バージョンを再現するため、lockfile を使ってインストールします。

- 直接依存: 完全なバージョンで指定。
- 間接依存: 各ディレクトリの lockfile で固定。
- 通常のセットアップ: `npm ci` と `uv sync --locked` を使用。

## 起動と動作確認

### バックエンドの起動

ターミナル1で FastAPI を起動します。

```sh
cd backend
uv run --locked uvicorn app.main:app --reload --host localhost --port 8000
```

### フロントエンドの起動

ターミナル2で、リポジトリのルートから React を起動します。

```sh
npm --prefix frontend run dev
```

### 画面と API の確認

ブラウザーで `http://localhost:5173` を開きます。

- 初期表示: `Hello World`。
- 「API を呼び出す」をクリック: `GET http://localhost:8000/hello` を実行。
- 成功時: `API: Hello World` を表示。
- 失敗時: エラーを表示。ボタンから再試行できます。
- API ドキュメント: `http://localhost:8000/docs`。

## 設定

### API URL の変更

`VITE_API_BASE_URL` で接続先を変更できます。既定値は `http://localhost:8000` です。

1. `frontend/.env.example` を `frontend/.env.local` にコピーします。
2. `VITE_API_BASE_URL` を編集します。
3. フロントエンドの開発サーバーを再起動します。

この値はブラウザーに公開されるため、秘密情報は入れません。

### CORS とアクセス先

画面は `http://localhost:5173` で開いてください。この Origin のみを API が許可します。

- `http://127.0.0.1:5173`: 別 Origin のため対象外。
- API 呼び出し: ブラウザーから直接実行。Vite プロキシは使いません。
- credentials: 送信しません。

ホスト名とポートを変更した場合は、API の許可 Origin も見直してください。

### Vite+ と React プラグイン

React プラグインには、Vite+ と同じ固定 core を使わせます。

- 設定場所: `frontend/package.json`。
- Vite alias: `@voidzero-dev/vite-plus-core` に接続。
- override: 間接依存の Vite も同じ core に統一。

この設定により、React プラグインと Vite+ の core を揃えます。

## テスト

### 実行コマンド

リポジトリのルートで実行します。Playwright は両サーバーを自動起動するため、手動起動したサーバーは先に停止してください。

```sh
npm --prefix frontend run check
npm --prefix frontend run build
uv run --directory backend --locked pytest
npm --prefix e2e test
```

### 確認する内容

各コマンドは次の項目を確認します。

- `check`: TypeScript の型検査と lint。
- `build`: フロントエンドのビルド。
- `pytest`: Hello レスポンス、Origin の許可・不許可。
- Playwright: 別 Origin の実 API 疎通、通信失敗後の再試行。

## 操作のまとめ

- 初回: 依存と Chromium をインストールします。
- 起動: バックエンドとフロントエンドを別ターミナルで実行します。
- 確認: `http://localhost:5173` で API 呼び出しを試します。
- 検証: 手動起動したサーバーを停止し、テストコマンドを実行します。
