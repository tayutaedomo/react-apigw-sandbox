# React / API Gateway Sandbox

## このプロジェクトで検証すること

React から API を呼び出し、正常時とエラー時の CORS の挙動を検証する PoC です。

- 現在: ローカルと AWS 上で Hello World の疎通を確認。
- 今後: Amplify Hosting、Gateway・Lambda 統合の障害、エラー時 CORS を検証。
- 開発・実行手順: 各ディレクトリの README に記載。

## 現在の構成

### ローカルの通信経路

ブラウザーから別 Origin の FastAPI を直接呼び出します。

```mermaid
flowchart LR
    V["Vite+ 開発サーバー<br/>localhost:5173"] -->|React を配信| B[ブラウザー]
    B -->|"GET /hello"| F["FastAPI / Uvicorn<br/>localhost:8000"]
```

- フロントエンド: React + TypeScript 7 + Vite+。
- バックエンド: FastAPI + Uvicorn。
- コンテナ: Lambda Web Adapter を同梱した `linux/amd64` イメージ。ローカルでは Uvicorn に直接アクセス。
- ログ: Powertools for AWS Lambda による JSON ログ。
- ブラウザーテスト: Playwright / Chromium。
- Vite プロキシ: 使用せず、別 Origin の通信を検証。

### AWS の通信経路

ローカルの React から、AWS 上の REST API を呼び出します。

```mermaid
flowchart LR
    V["Vite+ 開発サーバー"] -->|React を配信| B[ブラウザー]
    B -->|HTTPS| G[API Gateway REST API]
    G -->|Lambda proxy| L["Lambda / Web Adapter / FastAPI"]
    E[ECR] -.->|digest でイメージ指定| L
```

- 配信: 現在はローカル Vite。Amplify Hosting は未追加。
- IaC: ECR と API を別の Terraform state で管理。
- API と Lambda: SSO プロファイルのリージョンを使用。
- 認証と credentials: 未導入。

## PoC の概要

検証済みの内容は [PoC の検証結果](docs/poc.md)にまとめています。

- React / FastAPI: Hello World の表示と通信失敗後の再試行。
- CORS: 許可・未許可 Origin と credentials 不許可。
- コンテナ: OS 更新、非 root 実行、構造化ログ。
- ECR: 独立した Terraform、イメージ push と digest 取得。
- AWS API: Lambda / REST API の疎通と CloudWatch の Request ID 照合。

## 今後の検証対象

以下は、まだ検証していない構成と動作です。

- イメージ: スキャンで検出した脆弱性への対応と再スキャン。
- 配信: Amplify Hosting と手動デプロイ。
- エラー時 CORS: アプリの4xx・5xx、Gateway と Lambda 統合の障害。
- 追加検討: 認証方式と credentials を含む CORS。

## 開発・実行手順への案内

操作する対象の README を参照してください。コマンドは各ディレクトリ内で実行します。

- [frontend](frontend/README.md): 開発環境、画面の起動、API URL の設定、型検査・ビルド。
- [backend](backend/README.md): 開発環境、API・コンテナの起動、構造化ログ、API テスト。
- [infra](infra/README.md): ECR・API の Terraform、認証と state の管理。
- [e2e](e2e/README.md): 通常・コンテナのブラウザーテスト、画面キャプチャ・トレース確認。

まず frontend と backend のセットアップ・疎通を確認し、ブラウザーでの自動検証には e2e の手順を使用してください。
