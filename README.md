# React / API Gateway Sandbox

## 概要

React の画面から FastAPI の Hello World API を呼び出せます。

- フロントエンド: React、Vite+、TypeScript 7。
- バックエンド: FastAPI。
- ブラウザーテスト: Playwright。
- 実行環境: ローカル。AWS リソースの作成・デプロイは含みません。

### ディレクトリごとの手順

各ディレクトリ内での操作と開発環境は、以下の README に記載しています。

- [frontend](frontend/README.md): 画面の開発、API URL の設定、型検査・ビルド。
- [backend](backend/README.md): API の起動、CORS、API テスト。
- [e2e](e2e/README.md): Playwright のセットアップ、実行、トレース確認。

## セットアップ

### 必要なツール

ランタイムは最低バージョンを定義し、依存パッケージは固定します。

- Node.js: `24` 以上（Vite+ の条件により、24系は `24.11.0` 以上）。
- npm: `11.17.0` 以上。
- Python: `3.13` 以上。
- uv: `0.10.12` で検証済み。

最低バージョンは依存定義に記載しています。

- `frontend/` と `e2e/`: `package.json` の `engines`。
- `backend/`: `pyproject.toml` の `requires-python`。
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

### npm のインストール制限

依存パッケージの自動スクリプトを無効化し、公開後7日を経過したバージョンを選択します。

- 設定場所: `frontend/.npmrc` と `e2e/.npmrc`。
- `ignore-scripts=true`: インストール時の `preinstall`・`install`・`postinstall` などを実行しません。
- `min-release-age=7`: 依存解決時に公開後7日未満のバージョンを除外します。
- `save-exact=true`: 依存追加時に完全なバージョンを保存します。
- `npm run` と `npm test`: 指定したスクリプトは実行できます。付随する pre/post スクリプトは実行しません。

通常のセットアップでは lockfile を維持し、更新時にも同じ制限で依存を解決します。
設定の仕様は [npm の公式ドキュメント](https://docs.npmjs.com/cli/v11/using-npm/config/) を参照してください。

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
