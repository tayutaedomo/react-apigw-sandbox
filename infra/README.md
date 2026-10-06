# AWS リソース

## 目次

- [管理方針](#管理方針)
- [認証と開発環境](#認証と開発環境)
- [状態ファイルの管理](#状態ファイルの管理)
- [操作のまとめ](#操作のまとめ)

## 管理方針

リソースの作成順序に合わせて Terraform の作業ディレクトリと state を分離します。

- [ecr](ecr/README.md): API イメージの保存先を作成。
- [app](app/README.md): Lambda・REST API・Amplify・関連権限とログをまとめて作成。
- Origin: 同じ app state の Hosting を参照し、API の CORS 許可へ自動追加。
- Docker のビルド・push: [backend](../backend/README.md) の独立スクリプト。
- React のビルド・Amplify への公開: [frontend](../frontend/README.md) の独立スクリプト。Terraform に公開処理は含めません。

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

初回構築・API / 画面の更新・設定変更・切り戻しは [ユースケース別のデプロイ手順](../docs/deployment.md)を参照してください。

対象ディレクトリの README に従い、認証設定・plan・apply を同じ環境で実行します。
