# アプリの AWS リソース

## 目次

- [構成と方針](#構成と方針)
- [開発環境と認証](#開発環境と認証)
- [初回構築と更新](#初回構築と更新)
- [疎通とログ](#疎通とログ)
- [既存環境の state 移行](#既存環境の-state-移行)
- [削除とまとめ](#削除とまとめ)

## 構成と方針

Lambda・REST API・Amplify Hosting を同じ Terraform state で管理し、ECR は独立させます。

- API: Regional REST API、`sandbox` ステージ、Lambda proxy 統合。
- Lambda: digest 指定のコンテナ、`x86_64`、512 MB、タイムアウト15秒。
- Hosting: React の静的ビルドを配信する Amplify app と `sandbox` ブランチ。
- 配信先 Origin: Amplify のドメインを Terraform 内で参照し、Lambda の CORS 設定へ自動追加。
- ECR: [専用 state](../ecr/README.md)の既存 repository を照会。ここでは作成・削除しません。
- 定義: [main.tf](main.tf)に実行環境・ログと権限・Lambda・Gateway・Hosting をセクション別に配置。
- ビルド・公開: Terraform に含めず、backend / frontend の独立スクリプトで実行。
- 認証・credentials: 未導入。Gateway 自身のエラー時 CORS は後続の検証対象。

以下のコマンドは、特記がなければ `infra/app/` 内で実行します。

## 開発環境と認証

### 必要なツール

- Terraform: `1.5` 以上、`2.0` 未満。
- AWS Provider: `6.67.0` に固定。lockfile を Git 管理。
- AWS CLI v2: SSO ログイン済み。
- Docker / Buildx: API イメージのビルド・push 時に使用。
- Node.js・npm・zip: [frontend のビルドと公開](../../frontend/README.md#amplify-への手動デプロイ)で使用。

### 実行時の設定

```sh
export AWS_PROFILE='<使用するプロファイル>'
```

- リージョン: AWS の環境変数・プロファイル設定を使用。
- ECR と Lambda: 同一リージョン・同一アカウント。
- 必要な権限: Lambda、IAM、CloudWatch Logs、API Gateway、Amplify の管理と ECR の照会・push。
- 認証情報・実環境値・state・plan・個別 tfvars: Git 管理対象外。

## 初回構築と更新

### API イメージの準備

`backend/` 内でビルドと push を別々に実行します。ECR は先に作成済みであることが前提です。

```sh
./scripts/build-image.sh
./scripts/push-image.sh > ../infra/app/image-uri.txt
```

- イメージ: `sandbox-api:local` をビルドし、private ECR に push。
- リモートタグ: 省略時は Git SHA・UTC日時・プロセス ID で自動発番。
- `image-uri.txt`: digest URI の受け渡しファイル。Git 管理対象外。
- 同じイメージの配布: 再ビルドせず同じ digest を使用。

### Terraform の適用

`infra/app/` に戻り、API と Hosting を一度の plan / apply で管理します。

```sh
terraform init -lockfile=readonly
terraform fmt -check
terraform validate
./scripts/plan.sh
terraform apply app.tfplan
terraform output -raw api_base_url
terraform output -raw hosting_url
```

- plan: `image-uri.txt` を読み込み、`app.tfplan` に保存。
- digest を直接渡す場合: `./scripts/plan.sh '<repository>@sha256:<digest>'`。
- 検証: タグ指定と、指定 ECR repository に一致しない digest URI を拒否。
- CORS: localhost と Hosting の Origin を完全一致で許可。Origin の手動受け渡しは不要。
- 参照順: Hosting の作成・ドメイン取得後に Lambda の Origin 設定を適用。
- API Gateway: イメージ・Lambda 環境変数だけの変更では再デプロイしません。
- Hosting: 配信先の作成だけでは画面を公開しません。下記の手動デプロイが必要です。

### エラー検証 API と追加 Origin

意図的なエラー API は必要な場合だけ有効化します。

```sh
TF_VAR_enable_error_endpoints=true ./scripts/plan.sh
terraform apply app.tfplan
```

- `enable_error_endpoints`: 既定 `false`。Lambda の `ENABLE_ERROR_ENDPOINTS` へ反映。
- 有効状態を維持する更新: 同じ変数を渡して plan。省略すると検証 API は無効化されます。
- `allowed_origins`: Hosting に加えて許可する一覧。既定は `http://localhost:5173`。
- Hosting の Origin: 自動追加。`allowed_origins` に重複して書く必要はありません。
- Hosting だけを許可する場合: `allowed_origins = []`。
- 追加 Origin の形式: `http(s)://host[:port]`。wildcard・パス・末尾 `/` は使用しません。
- 個別設定: Git 管理対象外の `*.auto.tfvars.json` で保持可能。
- Lambda: 許可一覧を `CORS_ALLOW_ORIGINS` の JSON 配列へ変換して渡します。

### React の手動公開

`frontend/` 内で、リソース作成とは別に実行します。

```sh
./scripts/build-hosting.sh
node scripts/deploy-hosting.mjs
```

- ビルド: app の API URL を JS へ埋め込み、`dist/` を生成。
- 公開: app の app ID・branch・region を使い、ビルド済み ZIP をアップロード。
- Git 連携・自動ビルド: 無効。Git push や Terraform apply だけでは画面を更新しません。
- SPA: ページ URL は `index.html` へ rewrite。JS・CSS 等は除外。
- URL: Amplify の既定 HTTPS ドメイン。独自ドメインは使用しません。
- 詳細: [frontend の手動デプロイ手順](../../frontend/README.md#amplify-への手動デプロイ)。

## 疎通とログ

### ブラウザー・HTTP 結合テスト

`e2e/` 内で、実行時に接続先を渡します。

```sh
AWS_API_BASE_URL="$(terraform -chdir=../infra/app output -raw api_base_url)" \
HOSTING_BASE_URL="$(terraform -chdir=../infra/app output -raw hosting_url)" \
  npm run test:hosting
```

- ブラウザー: 配信済み画面の正常・エラー応答、CORS、プリフライト、再試行。
- HTTP 結合: 配信ファイル・ステータス・Lambda の Request ID。画面キャプチャは対象外。
- エラーケースの前提: `enable_error_endpoints=true`。
- localhost → AWS の検証: [e2e の手順](../../e2e/README.md#aws-上の-api-を使ったテスト)を参照。

### CloudWatch の確認と接続方針

```sh
aws logs tail '/aws/lambda/react-apigw-sandbox-api' --since 10m
```

- ロググループ: Terraform で明示的に作成し、7日保持。destroy で削除されます。
- 形式: アプリ・Uvicorn・Lambda プラットフォームの JSON ログ。
- 追跡: 応答の `X-Request-Id` と `lambda_request_id` を照合。
- readiness probe: 呼び出しコンテキストがないため、生成 UUID を使用。
- Web Adapter: 未処理500後に閉じられた接続の再利用を避けるため、接続再利用を無効化。
- トレードオフ: 毎回ローカル TCP 接続を作成。性能への影響は未測定。本番採用は別途判断。
- 通信経路: [接続再利用の図解](../../docs/connection-reuse.md)。Lambda 実行環境の再利用は維持。
- Gateway の実行ログ: 未設定。アカウント全体のログ用 role 設定は変更しません。

## 既存環境の state 移行

旧 `infra/api`・`infra/hosting` の state は、リソースを再作成せずに統合できます。初回構築では不要です。

1. Terraform の並行実行を止め、両方の state・backup を Git 管理外の安全な場所へ保存。
2. 旧 API の `terraform.tfstate` と `image-uri.txt` を `infra/app/` に移動。
3. `infra/app/` を初期化してから、旧 Hosting の管理対象を移動。

```sh
terraform init -lockfile=readonly
terraform state mv -state=../hosting/terraform.tfstate -state-out=terraform.tfstate aws_amplify_app.frontend aws_amplify_app.frontend
terraform state mv -state=../hosting/terraform.tfstate -state-out=terraform.tfstate aws_amplify_branch.sandbox aws_amplify_branch.sandbox
terraform state mv -state=../hosting/terraform.tfstate -state-out=terraform.tfstate data.aws_region.current data.aws_region.current
```

4. 旧 `cors.auto.tfvars.json` は Hosting の Origin を渡すためのものなので廃止。独自の追加 Origin があれば `allowed_origins` に引き継ぐ。
5. 現在のエラー API 設定を維持して plan し、作成・削除・置換がないことを確認。
6. output だけの変更を apply し、再 plan に差分がないことを確認。
7. 空になった旧 Hosting state と旧 plan は保管または撤去し、旧ディレクトリで apply しない。

state の統合は管理情報の移動です。AWS リソース自体や公開 URL を変更しません。

## 削除とまとめ

```sh
terraform plan -destroy -var="image_uri=$(cat image-uri.txt)" -out=destroy.tfplan
terraform apply destroy.tfplan
```

- 削除対象: API・Lambda・IAM・ロググループ・Amplify。配信中の画面も削除されます。
- ECR・イメージ: 独立 state のため保持されます。

ECR を独立させ、API と Hosting をアプリ単位で管理します。成果物のビルドと公開は独立スクリプトで実行します。
