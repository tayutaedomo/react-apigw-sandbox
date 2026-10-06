# Amplify Hosting

## 構成と方針

Terraform は静的サイトの配信先を作成し、成果物の公開は手動スクリプトで行います。

- 管理対象: Amplify app と `sandbox` ブランチ。
- platform: `WEB`。React の静的ビルドを配信。
- Git 連携・自動ビルド: 無効。Git の push だけでは公開されません。
- state: ECR・API と独立。Hosting の削除は API に影響しません。
- URL: Amplify の既定 HTTPS ドメイン。独自ドメインは使用しません。
- SPA: ページ URL は `index.html` へ rewrite。JS・CSS 等は除外し、アセットをそのまま配信。
- 公開処理: [frontend の手動デプロイ](../../frontend/README.md#amplify-への手動デプロイ)へ委譲。

以下のコマンドは `infra/hosting/` 内で実行します。

## 開発環境と認証

- Terraform: `1.5` 以上、`2.0` 未満。
- AWS Provider: `6.67.0` に固定。lockfile を Git 管理。
- AWS CLI v2: SSO ログイン済み。
- `AWS_PROFILE`: 使用するプロファイルを実行環境で指定。
- リージョン: プロファイル・AWS 環境変数の値を使用。
- 必要な権限: Amplify app・branch の作成、照会、変更、削除。
- 個別の認証設定・state・plan: Git 管理対象外。

## 作成と確認

```sh
terraform init -lockfile=readonly
terraform fmt -check
terraform validate
terraform plan -out=hosting.tfplan
terraform apply hosting.tfplan
terraform output -raw hosting_url
```

- app 作成時点では画面は公開されません。別途、成果物のデプロイが必要です。
- `app_id` / `branch_name` / `region`: 手動デプロイスクリプトが照会。
- `hosting_url`: API の CORS 許可とブラウザーテストで使用。
- API の許可設定: [infra/api](../api/README.md#配信先-origin-の許可)で Hosting の Origin を追加。
- 配信更新後: `terraform plan` で配信先の設定差分がないことを確認可能。

## 削除とまとめ

```sh
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```

- この state の削除対象: Amplify app・branch。配信中のサイトも削除されます。
- API・ECR: 別 state のため保持されます。
- API の CORS: 削除した Hosting の Origin は API 側の設定から別途削除します。

配信先を Terraform、ビルドと成果物の公開を frontend の独立スクリプトで管理します。
