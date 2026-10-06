# ブラウザー・HTTP 結合テスト

## 目次

- [概要](#概要)
- [開発環境](#開発環境)
- [テストの実行](#テストの実行)
- [設定と失敗時の確認](#設定と失敗時の確認)
- [操作のまとめ](#操作のまとめ)

## 概要

Playwright で、画面操作による E2E と、ブラウザーを使わない HTTP 結合を分けて確認します。

- 実 API 疎通: 別 Origin の通信と Hello World の表示。
- 通信失敗: エラー表示と、接続回復後の再試行。
- エラー時 CORS: 4xx・5xxの読み取り、Origin拒否、プリフライトと再試行。
- サーバー起動: ローカルでは Playwright が frontend と backend を自動起動。Hosting モードは配信済み画面を使用。

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

### テストの種類

配信後の検証でも、HTTP 応答だけを見るケースを E2E と呼びません。

| 種類 | 確認する範囲 | 画面記録 |
| --- | --- | --- |
| ブラウザー E2E | 画面操作 → API 呼び出し → 結果表示 | 操作前後の PNG |
| ブラウザー結合 | CORS・プリフライトの実際の判定 | 操作前後の PNG・通信観測 |
| HTTP 結合 | API と Lambda、Hosting の配信動作 | 画面なし |

- 配置: `tests/browser` と `tests/http`。
- 共通設定: 同じ実環境へ接続するため、接続先と Playwright の runner を共有。
- 補助確認: ブラウザーテスト内の `page.request` は CORS 拒否の根拠を確認する用途。主な検証対象は画面の動作。

### ローカルのテスト

手動起動した frontend と backend は停止してから実行してください。

```sh
npm test
```

- frontend: `http://localhost:5173`。
- backend: `http://localhost:8000`。
- 既存サーバー: 再利用しません。ポート競合は解消してから実行します。
- エラー検証 API: ローカル・コンテナではテスト起動時に自動で有効化。
- frontend の待ち受け: IPv4ループバック。`localhost` と `127.0.0.1` の別 Origin を同じ画面で検証。
- API URL: frontend の `.env.local` を変更している場合は、既定の `http://localhost:8000` に戻してください。
- 終了時: Playwright が起動したサーバーを停止します。

### ブラウザーを表示して実行

画面の動きを確認する場合は headed モードを使います。

```sh
npm test -- --headed
```

### コンテナを使ったテスト

コンテナ内の API を使って、同じ疎通・再試行テストを実行できます。

1. [backend の手順](../backend/README.md#イメージのビルド)で `sandbox-api:local` をビルドします。
2. 手動起動した frontend・backend・API コンテナを停止します。
3. `e2e/` 内で実行します。

```sh
npm run test:container
```

- 前提: Docker が稼働し、既定タグのイメージがローカルに存在。
- API: Playwright が `backend/compose.yaml` を使って自動起動。
- frontend: 通常のテストと同じ開発サーバーを自動起動。
- ポート: ホストの `8000` をコンテナの `8080` に接続。
- 終了: 起動したサーバーとコンテナを停止・削除。
- 検証範囲: ブラウザーからコンテナ内の API への通信。AWS 上の Lambda 実行は含みません。

### AWS 上の API を使ったテスト

ローカル frontend から、作成済みの API Gateway REST API を呼び出します。

```sh
AWS_API_BASE_URL="$(terraform -chdir=../infra/app output -raw api_base_url)" npm run test:aws
```

- 前提: [API の Terraform](../infra/app/README.md)を適用し、`enable_error_endpoints=true` に設定済み。
- 起動: frontend のみ。API URL は環境変数で渡し、実 URL をソースに保存しません。
- サーバー: ローカル backend は起動しません。
- ケース: 疎通・再試行・呼び出し ID と、エラー時 CORS・プリフライトを確認。
- エラー API を無効のまま疎通だけ検証: `npm run test:aws -- hello.spec.ts api.spec.ts`。
- ローカルモード: AWS 専用ケースは skip。
- 実行結果: 通常モードと同じ場所へ保存するため、前回のレポートを上書きします。

### Amplify 配信済み画面のテスト

Vite を起動せず、Amplify に公開したビルドから AWS の API を呼び出します。

```sh
AWS_API_BASE_URL="$(terraform -chdir=../infra/app output -raw api_base_url)" \
HOSTING_BASE_URL="$(terraform -chdir=../infra/app output -raw hosting_url)" \
  npm run test:hosting
```

- 前提: [frontend の手動デプロイ](../frontend/README.md#amplify-への手動デプロイ)を完了。app の Terraform が Hosting の Origin を許可。エラー API を有効化。
- 起動: ローカルの frontend・backend は起動しません。
- 接続先: ビルドへ埋め込んだ API URL と `AWS_API_BASE_URL` を一致させます。
- 検証: 正常応答、通信失敗後の再試行、4xx・5xx本文と相関 ID、429の Retry-After、プリフライトの許可・ヘッダー／メソッド拒否。
- 静的配信: JS の content-type、存在しない JS の404、ページ URL の直接アクセス。
- 未許可 Origin: `127.0.0.1:5173` を使う2ケースは skip。別 Origin の拒否はローカル・`test:aws` で確認。
- 画面記録: 操作の節目とテスト終了時に PNG を保存。

配信済みの成果物を検証するため、ローカルのソース変更は再ビルド・再公開後に反映されます。

### エラー時 CORS のケース

実レスポンスを使い、HTTP エラーとブラウザーの読み取り拒否を区別します。

- 読み取り: 404・405・422、400・409・418・429・500・502・503・504、未処理例外と応答検証500。
- ヘッダー: ブラウザーの JavaScript から Request ID と Retry-After を取得。
- Origin拒否: `127.0.0.1:5173` で同じ画面を開き、本文が公開されないことを確認。
- プリフライト: GET許可、Origin・ヘッダー・メソッド拒否。本リクエストの応答有無を Chromium の CDP で観測。
- 再試行: 拒否後に許可ケースへ切り替えて読み取り可能になることを確認。
- 連続呼び出し: 未処理500 → 応答検証500 → 明示的400を2回繰り返し、その後に Hello World の取得を確認。
- 添付: 操作前後のPNGと、プリフライト・本リクエストの応答一覧。
- モック: このテストでは API 応答を差し替えない。

プリフライトが拒否された場合、API の400本文を画面で読めるわけではありません。ブラウザーは本リクエストを送らず、fetch を失敗させます。

### 種類・ケースを指定して実行

```sh
npm test -- tests/browser/hello.spec.ts
```

- ブラウザーだけ: `npm run test:browser`。
- 配信後の HTTP 結合だけ: 接続先の環境変数を指定して `npm run test:http:hosting`。
- Hosting のブラウザーだけ: `npm run test:hosting -- --project=browser-chromium`。
- 実行結果の表示: `browser-chromium` と `http` の project 名で区別。

## 設定と失敗時の確認

### ファイルの役割

- `playwright.config.ts`: Chromium、サーバーの起動方法、接続先を定義。
- `playwright.container.config.ts`: API の起動を Docker に切り替え。
- `playwright.aws.config.ts`: API を AWS endpoint に切り替え、frontend のみ起動。
- `playwright.hosting.config.ts`: Amplify 配信済みの画面を検証。ローカルサーバーは起動しない。
- `scripts/run-api-container.sh`: コンテナを起動し、終了・中断時に削除。
- `tests/browser/hello.spec.ts`: 画面の疎通と通信失敗・再試行。
- `tests/browser/error-cors.spec.ts`: ブラウザーのエラー本文・相関 ID、Origin・プリフライトと再試行。
- `tests/browser/hosting.spec.ts`: 配信済み SPA の直接アクセスと API 呼び出し。
- `tests/http/api.spec.ts`: AWS API の本文・CORS ヘッダー・Lambda Request ID。
- `tests/http/hosting.spec.ts`: 配信ファイルの content-type・本文と未存在 JS の404。
- `helpers/capture.ts`: ブラウザーの操作前後の PNG 保存と添付を共通化。
- `helpers/endpoints.ts`: 両種類のテストで使う接続先を共通化。
- `test-results/`: テストの出力。Git 管理の対象外。

### 画面キャプチャと HTML レポート

ブラウザーテストは成功時も画面を保存します。画面操作のない HTTP 結合テストはキャプチャ対象外です。

- 操作の節目: 初期表示、API 成功、通信失敗、再試行成功で全画面 PNG を保存。
- ブラウザーテスト終了時: Playwright の `screenshot: 'on'` で成功・失敗とも自動保存。
- HTTP 結合テスト: ブラウザーを起動せず、ステータス・ヘッダー・本文で検証。画像・ブラウザートレースは保存しません。
- PNG: `test-results/` 内のテスト別ディレクトリ。
- HTML レポート: `playwright-report/`。画面キャプチャを添付。
- 保存先: 通常・コンテナの実行で共通。次の実行時に前の結果を上書きします。
- Git: 実行結果は管理対象外。

```sh
npm exec -- playwright show-report
```

節目の画像で表示の変化を比較し、失敗時は以下のトレースで通信や操作も調べます。

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
- コンテナ検証: イメージをビルドし、`npm run test:container`。
- 画面確認: `npm test -- --headed`。
