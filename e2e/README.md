# E2E テスト

## 概要

Playwright の Chromium で、React から実際の FastAPI を呼び出す動作を確認します。

- 実 API 疎通: 別 Origin の通信と Hello World の表示。
- 通信失敗: エラー表示と、接続回復後の再試行。
- サーバー起動: Playwright が frontend と backend を自動起動。

以下のコマンドは、すべて `e2e/` 内で実行します。

## 開発環境

### 必要なツールと前提

- Node.js: `24` 以上。起動する frontend の条件により、24系は `24.11.0` 以上。
- npm: `11.17.0` 以上。
- Python: `3.13` 以上。
- uv: `0.10.12` で検証済み。
- [frontend](../frontend/README.md) と [backend](../backend/README.md) の依存をセットアップ済み。

### セットアップ

Playwright と対応する Chromium をインストールします。

```sh
npm ci
npm run browser:install
```

- npm 依存: `package-lock.json` で固定。
- Chromium: 固定した Playwright に対応するブラウザーを使用。
- `.npmrc`: 自動 install スクリプトを無効化し、依存解決時に公開後7日未満を除外。
- ブラウザー取得: `browser:install` を明示的に実行。

## テストの実行

### 全テスト

手動起動した frontend と backend は停止してから実行してください。

```sh
npm test
```

- frontend: `http://localhost:5173`。
- backend: `http://localhost:8000`。
- 既存サーバー: 再利用しません。ポート競合は解消してから実行します。
- API URL: frontend の `.env.local` を変更している場合は、既定の `http://localhost:8000` に戻してください。
- 終了時: Playwright が起動したサーバーを停止します。

### ブラウザーを表示して実行

画面の動きを確認する場合は headed モードを使います。

```sh
npm test -- --headed
```

### テストを指定して実行

```sh
npm test -- tests/hello.spec.ts
```

## 設定と失敗時の確認

### ファイルの役割

- `playwright.config.ts`: Chromium、サーバーの起動方法、接続先を定義。
- `tests/hello.spec.ts`: 疎通と通信失敗・再試行のテスト。
- `test-results/`: テストの出力。Git 管理の対象外。

### トレース

失敗時にはトレースが保存されます。出力された `trace.zip` のパスを指定して確認します。

```sh
npm exec -- playwright show-trace 'test-results/<テストの出力ディレクトリ>/trace.zip'
```

- 実際のパス: テスト失敗時の出力で確認。
- 確認できる内容: 操作、画面、ネットワーク通信。

## 操作のまとめ

- 事前準備: frontend と backend の依存をセットアップ。
- セットアップ: `npm ci` と `npm run browser:install`。
- 検証: 手動サーバーを停止し、`npm test`。
- 画面確認: `npm test -- --headed`。
