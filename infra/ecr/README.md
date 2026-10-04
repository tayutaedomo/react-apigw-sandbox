# ECR

## 作成するものと方針

API コンテナ用の private ECR リポジトリだけを作成します。

- 既定名: `react-apigw-sandbox-api`。
- タグ: immutable。既存タグの上書きを禁止。
- スキャン: push 時の basic scanning を有効化。
- 暗号化: ECR 標準の AES256。
- 削除: イメージが残っている状態での強制削除を禁止。
- Lifecycle policy: 未設定。現段階ではイメージを自動削除しない。
- イメージの build・push: Terraform には含めない。
- スキャン結果: 安全性の保証や push のブロックにはならないため、結果を確認する。

以下のコマンドは、すべて `infra/ecr/` 内で実行します。

## 開発環境と認証

### 必要なツール

- Terraform: `1.5` 以上、`2.0` 未満。
- AWS Provider: `6.67.0` に固定。
- AWS CLI v2: SSO ログイン済み。
- IAM 権限: ECR の作成・照会・タグ管理。push 時には認証・レイヤー転送権限も必要。

### 実行時の設定

シェルで使用する SSO プロファイルを指定します。実際の名前をファイルには記載しません。

```sh
export AWS_PROFILE='<使用するプロファイル>'
```

- リージョン: プロファイルの設定を使用。
- 変更する場合: `AWS_REGION` と `AWS_DEFAULT_REGION` を同じ値に設定して Terraform / CLI を揃える。
- 資格情報: Terraform の変数や tfvars に含めない。
- リポジトリ名を変える場合: `TF_VAR_repository_name` を使用。

## 作成手順

### 初期化と検証

```sh
terraform init
terraform fmt -check
terraform validate
```

- provider とチェックサム: `.terraform.lock.hcl` で固定。
- 初期化後の `.terraform/`: Git 管理対象外。

### plan と apply

作成先と差分を確認してから、保存した plan を適用します。

```sh
terraform plan -out=ecr.tfplan
terraform apply ecr.tfplan
terraform output -raw repository_url
```

- state: このディレクトリ内に保持。ほかの AWS リソースと共有しない。
- plan: 認証情報やアカウント情報を含む可能性があるため、Git 管理対象外。
- output: push スクリプトが URL とリポジトリ名を読み取る。
- AWS の確認: `aws ecr describe-repositories --repository-names react-apigw-sandbox-api`。

## イメージと削除

### push とスキャン

イメージの操作は [backend の手順](../../backend/README.md#ecr-への-push)を使用します。

- push ごとに一意のタグを指定。
- 後続の Lambda は digest URI を使用する方針。
- スキャン結果: ECR コンソール、または `aws ecr describe-image-scan-findings` で確認。
- アカウント全体の scanning 設定によっては挙動が異なるため、実環境の設定も確認。

### 削除時の注意

リポジトリを削除する場合は、先に不要なイメージを明示的に削除します。

- `force_delete = false`: Terraform がイメージを巻き込んで削除しない。
- リポジトリ削除: 内容と plan を確認した後に `terraform destroy`。
- state: AWS リソースを残したまま削除しない。

## 操作のまとめ

- 初期化・検証: `terraform init`、`terraform validate`。
- 作成: plan を確認してから apply。
- イメージ: backend のスクリプトで build・push。
