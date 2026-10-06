# AWS リソース

## 管理方針

リソースの作成順序に合わせて Terraform の作業ディレクトリと state を分離します。

- [ecr](ecr/README.md): API イメージの保存先を作成。
- [api](api/README.md): Lambda・API Gateway REST API・実行 role・ログを作成。
- [hosting](hosting/README.md): Amplify の静的配信先を作成。API・ECR と独立した state。
- Docker のビルド・push: [backend](../backend/README.md) の独立スクリプトで実行。
- Amplify への配信: Terraform に含めず、手動デプロイを使用する方針。

## 認証と開発環境

SSO ログイン済みの AWS プロファイルを実行時に指定します。

- Terraform と AWS CLI の双方へ `AWS_PROFILE` を渡す。
- リージョンは AWS の環境変数・共有設定を使用。
- プロファイル名・認証情報はコードや設定ファイルに記載しない。
- 操作手順と Terraform の要件は各作業ディレクトリの README を参照。

## 状態ファイルの管理

現段階はローカル state を使用します。

- `.terraform.lock.hcl`: provider のバージョンとチェックサムを記録し、Git で管理。
- `.terraform/`、state、plan、個別の tfvars: Git 管理の対象外。
- state: 作業ディレクトリに保持し、紛失しないよう扱う。
- チーム運用・自動化の段階では共有 backend を検討する。

## 操作のまとめ

対象ディレクトリの README に従い、認証設定・plan・apply を同じ環境で実行します。
