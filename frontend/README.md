# フロントエンド

## 概要

React の画面から FastAPI を直接呼び、取得結果や通信失敗を表示します。

- React: 画面と状態管理。
- TypeScript 7: 型検査。
- Vite+: 開発サーバー、lint、ビルド。

以下のコマンドは、すべて `frontend/` 内で実行します。

## 開発環境

### 必要なツール

- Node.js: `24` 以上。Vite+ の条件により、24系は `24.11.0` 以上。
- npm: `11.17.0` 以上。
- API の起動: [backend の手順](../backend/README.md)を参照。

### セットアップ

lockfile に記録した依存をインストールします。

```sh
npm ci
```

- 直接依存: `package.json` で完全なバージョンを指定。
- 間接依存: `package-lock.json` で固定。
- Vite+: ローカル依存を使うため、グローバルインストールは不要。

## 開発と動作確認

### 開発サーバー

```sh
npm run dev
```

- 画面: `http://localhost:5173`。
- 初期表示: `Hello World`。
- 「API を呼び出す」: バックエンドの `/hello` を取得。
- 成功時: `API: Hello World` を表示。
- 失敗時: エラーを表示し、ボタンから再試行可能。
- 終了: `Ctrl+C`。

API 呼び出しを確認する前に、別ターミナルでバックエンドを起動してください。

### エラーレスポンスの検証

「エラーレスポンスの CORS 検証」でケースを選び、実 API のエラー応答を確認できます。

- 前提: backend の `ENABLE_ERROR_ENDPOINTS=true`。AWS では [API の設定](../infra/api/README.md#エラー検証-api-の有効化)を使用。
- 読み取り成功: HTTP ステータス・本文・Request ID、429では Retry-After を表示。
- 読み取り失敗: CORS または通信状態の確認を案内。fetch の例外だけでは原因を断定しません。
- プリフライト: 許可 GET、未許可ヘッダー、未許可 PUT を選択可能。
- 未許可 Origin: `http://127.0.0.1:5173` は許可対象外。両ホスト名で開く場合は `npm run dev -- --host 127.0.0.1` で起動。
- 再試行: 別のケースを選んで同じボタンから実行可能。

HTTP エラーも本文を表示するため、CORS 拒否による読み取り失敗との違いを確認できます。

### 接続先の設定

`VITE_API_BASE_URL` で API の接続先を変更できます。既定値は `http://localhost:8000` です。

```sh
cp .env.example .env.local
```

1. `.env.local` の `VITE_API_BASE_URL` を編集します。
2. 開発サーバーを再起動します。

- この値はビルド時にフロントへ取り込まれ、ブラウザーに公開されます。
- 秘密情報は設定しません。
- バックエンドの許可 Origin は `http://localhost:5173`。画面を `127.0.0.1` で開くと別 Origin になります。
- Vite プロキシと credentials は使用しません。

## チェックとビルド

### 型検査・lint

```sh
npm run check
```

- `tsc --noEmit`: TypeScript 7 の型検査。
- `vp lint`: Vite+ の lint。

### ビルド

```sh
npm run build
```

- 型検査後、Vite+ でビルドします。
- 成果物は `dist/` に出力します。
- ブラウザーテストは [e2e の手順](../e2e/README.md)で実行します。

## 依存インストールの設定

`.npmrc` で自動スクリプトと公開直後の依存解決を制限しています。

- `ignore-scripts=true`: install/postinstall 等を自動実行しません。
- `min-release-age=7`: 依存解決時に公開後7日未満のバージョンを除外します。
- `save-exact=true`: 追加する直接依存を完全なバージョンで保存します。
- `engine-strict=true`: 依存が要求するランタイム条件を確認します。

`npm run` で指定したスクリプトは実行できます。付随する pre/post は実行しません。

## 操作のまとめ

- セットアップ: `npm ci`。
- 開発: バックエンドを起動し、`npm run dev`。
- 検証: `npm run check` と `npm run build`。
