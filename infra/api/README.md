# Lambda / REST API

## 構成と方針

API Gateway REST API から、コンテナ方式の Lambda 上の FastAPI を呼び出します。

- ECR: [専用ディレクトリ](../ecr/README.md)で作成済みの repository を参照。
- state: ECR と独立したローカル state。
- リソース定義: [main.tf](main.tf)に実行環境・権限・Lambda・Gateway・公開ステージをセクション別に配置。
- イメージ: タグではなく digest URI を指定。
- Lambda: `x86_64`、512 MB、タイムアウト15秒。
- 統合: Lambda proxy。ルートと配下のパスを FastAPI へ渡す。
- API: Regional、ステージ名 `sandbox`。
- ログ: CloudWatch に7日保持。アプリ・Uvicorn・Lambda のプラットフォームログを JSON で記録。
- 認証: この段階は未導入。
- CORS: 現在の FastAPI 設定で `http://localhost:5173` を許可。credentials は不許可。
- Gateway 自身のエラー時 CORS・広範囲の障害検証: 後続フェーズの対象。

以下のコマンドは、特記がなければ `infra/api/` 内で実行します。

## 開発環境と認証

### 必要なツール

- Terraform: `1.5` 以上、`2.0` 未満。
- AWS Provider: `6.67.0` に固定。
- AWS CLI v2: SSO ログイン済み。
- Docker / Buildx: イメージのビルド・push 時に使用。
- frontend / e2e: [各 README](../../e2e/README.md)に従ってセットアップ済み。

### 実行時の設定

```sh
export AWS_PROFILE='<使用するプロファイル>'
```

- リージョン: プロファイルに設定した値を使用。
- 対象: ECR と Lambda は同一リージョン・同一アカウント。
- 権限: Lambda、IAM、CloudWatch Logs、API Gateway の作成・照会、ECR の照会・push。
- 個別の環境値: プロファイル名や実 URL をソースに記載しない。

## イメージの準備

### ビルドと push

`backend/` 内で実行します。ビルド・push は別々のスクリプトです。

```sh
./scripts/build-image.sh
./scripts/push-image.sh > ../infra/api/image-uri.txt
```

- ローカルタグ: `sandbox-api:local`。
- リモートタグ: 省略時は Git SHA・UTC日時・プロセス ID で自動発番。
- push の標準出力: digest URI のみ。進捗は標準エラー。
- `image-uri.txt`: Git 管理対象外のローカル受け渡しファイル。
- 同じイメージを別環境へ配布する場合: 再ビルドせず同じ digest を使用。

## Terraform の操作

### 初期化と plan

`infra/api/` に戻って実行します。

```sh
terraform init -lockfile=readonly
terraform fmt -check
terraform validate
./scripts/plan.sh
```

- plan: `image-uri.txt` を読み込み、`api.tfplan` に保存。
- URI を直接渡す場合: `./scripts/plan.sh '<repository>@sha256:<digest>'`。
- 検証: タグ指定と、参照 repository の URL に一致しない URI を拒否。
- ECR: data source で照会し、この state から作成・削除しない。

### apply と endpoint の取得

保存された plan を確認してから apply します。

```sh
terraform apply api.tfplan
terraform output -raw api_base_url
```

- 実行されるイメージ: plan に保存した digest。
- 更新: 新しいイメージを push し、plan を再作成して apply。
- Lambda は ECR のタグ変更へ自動追従しない。
- state・plan・イメージ URI: Git 管理対象外。

## 疎通とログ

### ブラウザー / API 結合テスト

`e2e/` 内で、Terraform output を環境変数へ渡して実行します。

```sh
AWS_API_BASE_URL="$(terraform -chdir=../infra/api output -raw api_base_url)" npm run test:aws
```

- API: AWS 上の REST API を使用。ローカル backend は起動しない。
- frontend: Playwright がローカル Vite サーバーを起動し、API URL を渡す。
- 検証: Hello World、CORS、通信失敗・再試行、レスポンスの追跡 ID。
- 画面キャプチャ: [e2e の README](../../e2e/README.md#画面キャプチャと-html-レポート)を参照。

### CloudWatch の確認

```sh
aws logs tail '/aws/lambda/react-apigw-sandbox-api' --since 10m
```

- アプリ: `request_id_source=lambda` と `lambda_request_id` を確認。
- 対応: レスポンスの `X-Request-Id` と Lambda の呼び出し ID を照合。
- 初期化: Uvicorn の起動 JSON と Web Adapter の起動を確認。
- readiness probe: 呼び出しコンテキストがないため、生成 UUID が記録される。
- API Gateway の実行ログ: この段階では未設定。アカウント全体のログ用 role 設定は変更しない。

## 削除と操作のまとめ

- API 側だけを削除する場合: この state に digest を渡し `terraform destroy -var="image_uri=$(cat image-uri.txt)"`。
- ECR とイメージ: API 側の destroy では削除されない。
