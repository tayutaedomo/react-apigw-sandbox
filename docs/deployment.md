# ユースケース別のデプロイ手順

## 目次

- [まず選ぶユースケース](#まず選ぶユースケース)
- [共通の準備](#共通の準備)
- [初回に環境全体を構築する](#初回に環境全体を構築する)
- [バックエンドだけを更新する](#バックエンドだけを更新する)
- [フロントエンドだけを更新する](#フロントエンドだけを更新する)
- [AWS の設定だけを変更する](#aws-の設定だけを変更する)
- [バックエンドと画面を両方更新する](#バックエンドと画面を両方更新する)
- [API の接続先を変更する](#api-の接続先を変更する)
- [同じ成果物をもう一度公開する](#同じ成果物をもう一度公開する)
- [以前のバージョンへ切り戻す](#以前のバージョンへ切り戻す)
- [途中で失敗した場合に再開する](#途中で失敗した場合に再開する)
- [デプロイ後に確認する](#デプロイ後に確認する)
- [操作のまとめ](#操作のまとめ)

## まず選ぶユースケース

変更した対象に応じて、必要な工程だけを実行します。Terraform apply と画面の公開は別の操作です。

| 変更・目的 | API のビルド・push | app の plan・apply | React のビルド | Amplify 手動公開 | 手順 |
| --- | --- | --- | --- | --- | --- |
| AWS 環境がまだない | 必要 | 必要。ECR は先に作成 | 必要 | 必要 | [初回構築](#初回に環境全体を構築する) |
| API コード・Python 依存・Dockerfile・OS 更新 | 必要 | 必要。新 digest を指定 | 不要※ | 不要※ | [バックエンド更新](#バックエンドだけを更新する) |
| 画面・CSS・npm 依存 | 不要 | 不要 | 必要 | 必要 | [フロントエンド更新](#フロントエンドだけを更新する) |
| Lambda 設定・追加 Origin・エラー API の切り替え・Gateway 定義・Hosting の rewrite | 不要 | 必要。現在の digest を維持 | 不要※ | 不要※ | [設定変更](#aws-の設定だけを変更する) |
| API と画面を同時に変更 | 必要 | 必要 | 必要 | 必要 | [両方の更新](#バックエンドと画面を両方更新する) |
| 画面が呼ぶ API URL を変更 | API の変更内容による | AWS リソース変更がある場合 | 必要 | 必要 | [接続先変更](#api-の接続先を変更する) |
| 確認済み dist を再公開 | 不要 | 不要 | 不要 | 必要 | [同じ成果物の再公開](#同じ成果物をもう一度公開する) |
| 前の API / 画面へ戻す | 再ビルドしない | API を戻す場合 | 再ビルドしない | 画面を戻す場合 | [切り戻し](#以前のバージョンへ切り戻す) |

※ API URL と画面が利用する API の仕様が変わらない場合。URL が変われば接続先変更、画面の修正も必要なら両方の更新を選びます。

- Git push: 画面を公開しません。Amplify の Git 連携・自動ビルドは無効です。
- イメージの push: Lambda を更新しません。digest を指定して app の apply が必要です。
- Terraform apply: `dist/` を公開しません。Amplify の手動公開が別途必要です。
- 既に動いているこの PoC: 初回構築ではなく、更新対象に対応する手順を選びます。

## 共通の準備

### 実行場所と前提

**本書のコマンドはすべてリポジトリのルートで実行します。** ディレクトリを移動せず、`terraform -chdir` と `npm --prefix` を使います。

- AWS: SSO ログイン済み。同じアカウント・リージョンで操作。
- 認証: `AWS_PROFILE` を実行環境で指定。プロファイル名をファイルへ保存しません。
- ツールと依存: [backend](../backend/README.md#開発環境)、[frontend](../frontend/README.md#開発環境)、[e2e](../e2e/README.md#開発環境)、[infra/app](../infra/app/README.md#開発環境と認証)の準備が完了。
- 更新時: `infra/ecr` と `infra/app` のローカル state を保持。state を統合する必要がある環境は [移行手順](../infra/app/README.md#既存環境の-state-移行)を先に実施。
- ソース: デプロイ対象のコミットを確認。OS 更新だけでもビルド結果は変わるため、実行イメージは digest で識別。
- コマンド: 成功を確認して次へ進みます。plan を作成したら、変更対象を確認してその保存済み plan を apply。

```sh
export AWS_PROFILE='<使用するプロファイル>'
mkdir -p .deployment
```

- `.deployment/`: candidate digest・切り戻し用 digest・画面の保存先。Git 管理対象外。
- 初回構築: state がまだないため、output の照会は app の apply 後に行います。

### 更新を通して保持する設定

エラー API の有効状態と追加 Origin は、Git 管理外の `infra/app/deployment.auto.tfvars.json` で保持します。毎回フラグを付け忘れて設定が変わることを避けます。

この PoC でエラー時 CORS を検証する設定例です。初回構築時は、次の内容を `infra/app/deployment.auto.tfvars.json` に保存します。既存環境では下記の確認コマンドで現在の設定を確認してから作成し、既存ファイルは上書きしません。

```json
{
  "enable_error_endpoints": true,
  "allowed_origins": ["http://localhost:5173"]
}
```

- Hosting の Origin: Terraform が自動追加。ファイルへ転記しません。
- `enable_error_endpoints=false`: 意図的なエラー API を公開しない設定。
- 既存の個別 tfvars がある場合: その設定を維持し、同じ変数を複数のファイルへ重複定義しません。
- 設定ファイルをまだ作っていない既存環境: 下記で現在の Lambda 設定を確認し、有効状態と追加 Origin を引き継いでから作成。
- `CORS_ALLOW_ORIGINS` から引き継ぐ際: Hosting の Origin は除き、localhost 等の追加 Origin だけを `allowed_origins` へ記載。
- `image_uri`: このファイルには含めず、plan スクリプトで digest を指定。

```sh
aws lambda get-function-configuration \
  --function-name "$(terraform -chdir=infra/app output -raw function_name)" \
  --query 'Environment.Variables' --output json
```

設定を持たず既定値だけで plan すると、エラー API は無効になります。更新前に継続する設定を明示します。

## 初回に環境全体を構築する

### 対象と前提

ECR → API イメージ → app → React の順に構築します。既存環境の更新には使いません。

- ECR・app の AWS リソースと state が未作成の環境が対象。
- [共通の準備](#共通の準備)を完了し、個別設定ファイルを作成済み。

### 手順

1. ECR を作成します。初回だけです。

```sh
terraform -chdir=infra/ecr init -lockfile=readonly
terraform -chdir=infra/ecr plan -out=ecr.tfplan
terraform -chdir=infra/ecr apply ecr.tfplan
```

2. API イメージをビルド・push し、成功後に digest を受け渡します。

```sh
backend/scripts/build-image.sh
backend/scripts/push-image.sh > .deployment/candidate-image-uri.txt
cp .deployment/candidate-image-uri.txt infra/app/image-uri.txt
```

3. app を作成します。plan は API・Hosting・関連権限とログの作成を含みます。

```sh
terraform -chdir=infra/app init -lockfile=readonly
terraform -chdir=infra/app fmt -check
terraform -chdir=infra/app validate
infra/app/scripts/plan.sh
terraform -chdir=infra/app apply app.tfplan
```

4. React をビルドして手動公開します。

```sh
npm --prefix frontend ci
frontend/scripts/build-hosting.sh
node frontend/scripts/deploy-hosting.mjs
```

5. [デプロイ後の確認](#デプロイ後に確認する)を実施。画面を確認できたら [成果物の保存](#フロントエンドだけを更新する)を実施します。

### 完了条件

- app の output に API URL と Hosting URL がある。
- Amplify の手動公開が成功し、配信済み画面から Hello World を取得できる。
- エラー API を有効にした場合はエラー本文・ヘッダー・プリフライトも確認。

初回だけ ECR を作成し、以後は変更対象ごとの更新手順を使います。

## バックエンドだけを更新する

### 対象と前提

FastAPI のコード・Python 依存・Dockerfile・OS パッケージを更新します。API URL と画面の仕様が変わらなければ React の再公開は不要です。

- ECR・app が構築済み。
- 現在の個別設定を保持。
- 検証: Python のコード・依存変更は下記の API テストを実行。コンテナ変更時の確認はビルド後に行います。

```sh
uv run --directory backend --locked pytest
```

### 手順

1. 現在の digest を切り戻し用に保存します。

```sh
terraform -chdir=infra/app output -raw image_uri > .deployment/previous-image-uri.txt
```

2. 新しいイメージをビルド・push します。push が成功するまで既存の `image-uri.txt` は置き換えません。

```sh
backend/scripts/build-image.sh
```

Dockerfile・OS パッケージ等を変更した場合は、ビルドしたコンテナを push 前に確認します。

```sh
npm --prefix e2e run test:container
```

ビルド・必要なテストの成功後に push します。

```sh
backend/scripts/push-image.sh > .deployment/candidate-image-uri.txt
cp .deployment/candidate-image-uri.txt infra/app/image-uri.txt
```

3. 新しい digest を指定して Lambda を更新します。

```sh
infra/app/scripts/plan.sh
terraform -chdir=infra/app apply app.tfplan
```

- plan の確認: 通常は Lambda の image URI の更新。無関係な変更・置換があれば、その原因を確認してから適用。
- OS 更新だけの場合も同じ手順。既存の digest は自動で更新されません。
- Gateway: イメージだけの変更で deployment を作り直す必要はありません。

4. [デプロイ後の確認](#デプロイ後に確認する)を実施します。

API 更新はビルド → push → plan → apply。push だけでは更新完了ではありません。

## フロントエンドだけを更新する

### 対象と前提

React・CSS・npm 依存を変更します。API と AWS の設定が変わらなければ、Docker と Terraform apply は不要です。

- app が構築済み。
- API URL は app の output から取得。
- 前回確認済みの画面を保存している場合、切り戻し用に退避してから更新。

### 手順

1. 前回確認済みの成果物があれば保存します。

```sh
if [ -f .deployment/last-good-frontend.tar.gz ]; then
  cp .deployment/last-good-frontend.tar.gz .deployment/previous-frontend.tar.gz
fi
```

2. 依存のセットアップ・チェック・配信用ビルドを実行します。

```sh
npm --prefix frontend ci
npm --prefix frontend run check
frontend/scripts/build-hosting.sh
```

3. ビルド済みの `frontend/dist/` を公開します。

```sh
node frontend/scripts/deploy-hosting.mjs
```

4. [デプロイ後の確認](#デプロイ後に確認する)を実施します。

### 確認済み成果物の保存

画面の公開と確認が成功した場合だけ、その公開に使った `dist/` を保存します。ローカルに残った別ビルドを保存しないでください。

```sh
tar -czf .deployment/last-good-frontend.tar.gz -C frontend/dist .
```

- 初回構築・接続先変更・両方の更新でも、画面を公開して確認した後に実行。
- 更新前に `previous-frontend.tar.gz` として退避したものが切り戻し対象。
- 現在の方式: 成果物をローカルで保存。Amplify の過去ジョブからの自動復元は実装していません。

画面更新はビルド → 手動公開。Git push と Terraform apply だけでは画面は更新されません。

## AWS の設定だけを変更する

### 対象と前提

Lambda のメモリ・タイムアウト・ログ設定、追加 Origin、エラー API の切り替え、Gateway の定義、Hosting の rewrite を変更します。

- アプリのコードと依存は変更しない。
- 現在のコードで対応できる設定が対象。新しい設定の読み取りをコードへ追加する場合はバックエンド更新も必要。
- Origin・エラー API の変更: 個別 tfvars を編集。
- メモリ・Gateway 定義等の変更: Terraform の対象定義を編集。

### 手順

1. 実行中の digest を使い、設定変更に未適用の別イメージを混ぜません。

```sh
terraform -chdir=infra/app output -raw image_uri > infra/app/image-uri.txt
```

2. 対象の設定を変更し、plan・apply します。

```sh
terraform -chdir=infra/app fmt -check
terraform -chdir=infra/app validate
infra/app/scripts/plan.sh
terraform -chdir=infra/app apply app.tfplan
```

- plan の確認: 変更した設定だけが対象になり、image URI が維持されること。
- エラー API: `deployment.auto.tfvars.json` の `enable_error_endpoints` を変更。
- 追加 Origin: 同ファイルの `allowed_origins` を変更。Hosting の Origin は自動追加。
- Gateway 定義: 設定変更に合わせ、Terraform の trigger が新しい deployment とステージ切り替えを管理。
- Hosting の rewrite: Terraform の設定更新で反映。既存の静的成果物のアップロードは不要。
- API / Hosting URL が変わる変更: [接続先変更](#api-の接続先を変更する)も実施。

3. [デプロイ後の確認](#デプロイ後に確認する)を実施します。エラー API を無効にした場合は正常系の確認を使います。

設定だけの変更では、既存イメージと静的成果物を使い続けます。

## バックエンドと画面を両方更新する

### 対象と前提

API の仕様変更に合わせて画面も変更する場合です。個別の更新を API → 画面の順に実行します。

- API 公開から画面公開までの間、利用者は旧画面から新 API を呼びます。
- 新 API は旧画面も受け付ける形で先に追加し、その後に新画面を公開。
- 古い API の削除が必要な場合: 新画面の確認後、別のバックエンド更新として実施。

### 手順

1. [バックエンド更新](#バックエンドだけを更新する)を実施し、新 API の疎通を確認。
2. [フロントエンド更新](#フロントエンドだけを更新する)を実施。
3. 配信済み画面で新機能と既存機能を確認し、公開した画面の成果物を保存。

各手順の digest・画面保存も実施します。画面と API を同時に切り替える仕組みはありません。

## API の接続先を変更する

### 対象と前提

画面へ埋め込む API URL が変わる場合です。Lambda の digest だけの更新では、この手順は不要です。

- app の API URL が変更された場合: AWS の設定を適用後、画面を再ビルド。
- 明示的に別 API を使う場合: その API が Hosting の Origin を許可していることを確認。
- URL の変更だけで、ビルド済み JS の接続先は切り替わりません。

### 手順

1. [フロントエンド更新](#フロントエンドだけを更新する)の成果物退避を実施。
2. 通常は app の最新 output で再ビルドします。

```sh
frontend/scripts/build-hosting.sh
```

別 API を明示する場合は、上のコマンドの代わりに次を使います。

```sh
frontend/scripts/build-hosting.sh 'https://example.execute-api.us-east-1.amazonaws.com/sandbox'
```

3. 手動公開し、画面が意図した API を呼ぶことを確認。

```sh
node frontend/scripts/deploy-hosting.mjs
```

- 別 API の検証: Playwright の `AWS_API_BASE_URL` もその URL に合わせます。
- `HOSTING_BASE_URL`: 引き続き app の Hosting URL を使用。
- Hosting URL 自体を変えた場合: 新しい Hosting へ成果物を公開し、API の Origin 設定とテスト接続先も確認。

接続先変更は、API URL の更新だけでなく React の再ビルドと公開まで必要です。

## 同じ成果物をもう一度公開する

### 対象と手順

公開処理の再実行等で、確認済みの同じ `frontend/dist/` をもう一度公開します。

```sh
node frontend/scripts/deploy-hosting.mjs
```

- コード・依存・API URL を変えていないことが前提。
- 再ビルド: 不要。手動公開スクリプトもビルドしません。
- ローカル dist の出所が不明な場合: [フロントエンド更新](#フロントエンドだけを更新する)として対象コミットからビルド。
- 再公開後: [デプロイ後の確認](#デプロイ後に確認する)を実施。

再公開するのは指定した成果物です。Git の現在のコードを自動で公開する処理ではありません。

## 以前のバージョンへ切り戻す

### API の切り戻し

更新前に保存した digest を再指定します。前のソースから再ビルドすると OS 更新等で別イメージになるため、再ビルドしません。

前提: `.deployment/previous-image-uri.txt` があり、その digest のイメージが ECR に残っていること。

```sh
cp .deployment/previous-image-uri.txt infra/app/image-uri.txt
infra/app/scripts/plan.sh
terraform -chdir=infra/app apply app.tfplan
```

- plan の確認: Lambda の image URI が意図した前の digest に戻ること。
- 環境変数・Terraform の定義: この操作では現在の設定を維持。
- 設定にも互換性のない変更がある場合: 必要な設定差分も戻して同じ plan で確認。
- apply 後: [デプロイ後の確認](#デプロイ後に確認する)を実施。

### 画面の切り戻し

更新前に保存した成果物を復元して、同じ Hosting へ手動公開します。

前提: `.deployment/previous-frontend.tar.gz` が、戻したい公開済み成果物であること。アーカイブ内の `index.html` と assets を確認します。

```sh
tar -tzf .deployment/previous-frontend.tar.gz
rm -rf frontend/dist
mkdir -p frontend/dist
tar -xzf .deployment/previous-frontend.tar.gz -C frontend/dist
node frontend/scripts/deploy-hosting.mjs
```

- 削除対象: ローカルのビルド出力 `frontend/dist/`。ソースは削除しません。
- API URL: 保存した JS に埋め込まれた URL に戻ります。その API の利用可否も確認。
- 公開後: 配信済み画面を確認し、復元した成果物を `last-good-frontend.tar.gz` に保存。
- API も戻す必要がある場合: 旧画面と旧 API の互換性を確認し、両方の切り戻しを実施。

### AWS 設定の切り戻し

対象の Terraform / 個別 tfvars の差分を戻し、[設定変更](#aws-の設定だけを変更する)の手順で plan・apply します。

- state ファイルを過去のものへ戻す操作ではありません。
- plan で実リソースの変更を確認して、必要な設定を戻します。

切り戻しは API の digest、画面の成果物、AWS の設定を分けて判断します。

## 途中で失敗した場合に再開する

失敗した工程から再開します。成功済みの工程まで毎回やり直す必要はありません。

| 失敗した場所 | 次にする操作 |
| --- | --- |
| API ビルド | 原因を修正しビルドを再実行。push・apply へ進まない |
| ECR push | ローカルイメージを確認し、push を再実行。成功後に candidate digest をコピー |
| Terraform plan | 入力・設定を修正し、新しい plan を作成 |
| Terraform apply | エラーと現在の state を確認し、改めて plan・apply。実行済みの変更を前提に再評価 |
| React ビルド | 原因を修正し再ビルド。残った以前の dist を誤って公開しない |
| Amplify アップロード | 同じ成果物で手動公開スクリプトを再実行。失敗したアップロードでは公開を開始しない |
| Amplify 公開失敗・待機上限 | 下記でジョブを確認。待機上限はジョブ停止ではないため、公開結果を確認してから再実行・切り戻しを選ぶ |
| 公開後のテスト | 画面・ログ・接続先・Origin を確認。原因に応じて修正再公開または切り戻し |

直近の Amplify ジョブを確認します。開始時刻・job ID・status で今回の公開を識別します。

```sh
aws amplify list-jobs \
  --app-id "$(terraform -chdir=infra/app output -raw app_id)" \
  --branch-name "$(terraform -chdir=infra/app output -raw branch_name)" \
  --region "$(terraform -chdir=infra/app output -raw region)" \
  --max-results 5 --query 'jobSummaries[].{id:jobId,status:status,start:startTime}' --output table
```

公開が成功していたら検証へ進み、失敗していたらジョブの詳細と原因を確認します。

## デプロイ後に確認する

### 画面と API の確認

通常は、配信済みの画面と実 API の両方を Playwright で確認します。

エラー API を有効にしている場合:

```sh
AWS_API_BASE_URL="$(terraform -chdir=infra/app output -raw api_base_url)" \
HOSTING_BASE_URL="$(terraform -chdir=infra/app output -raw hosting_url)" \
  npm --prefix e2e run test:hosting
```

エラー API を無効にしている場合は、正常系・静的配信・直接アクセスだけを選びます。

```sh
AWS_API_BASE_URL="$(terraform -chdir=infra/app output -raw api_base_url)" \
HOSTING_BASE_URL="$(terraform -chdir=infra/app output -raw hosting_url)" \
  npm --prefix e2e run test:hosting -- hello.spec.ts api.spec.ts hosting.spec.ts
```

- ブラウザー: 正常応答・再試行、必要に応じてエラー時 CORS。操作の節目の PNG を保存。
- HTTP 結合: Request ID、JS の配信、未存在 JS の404。画面記録は対象外。
- 詳細: [e2e の確認方法](../e2e/README.md#設定と失敗時の確認)。
- 画面を公開した場合: 成功を確認してから公開に使った成果物を保存。

### Terraform とログの確認

apply を実施したケースでは、同じ個別設定・digest で再 plan し、差分がないことを確認します。

```sh
infra/app/scripts/plan.sh
```

API の確認が必要な場合は、Lambda のログでエラーや Request ID を照合します。

```sh
aws logs tail '/aws/lambda/react-apigw-sandbox-api' --since 10m
```

- Lambda イメージ更新: `image_uri` の output と指定した digest が一致することも確認。
- 画面だけの公開: Terraform apply は不要。配信済み画面の確認を実施。

## 操作のまとめ

- API 更新: ビルド → push → digest 指定 → plan・apply → 確認。
- 画面更新: ビルド → 手動公開 → 確認 → 公開成果物を保存。
- AWS 設定変更: 現在の digest を維持 → plan・apply → 確認。
- 接続先変更: API URL の確認 → React の再ビルド・公開 → 確認。
- 切り戻し: 保存した digest・成果物を使い、設定の変更は別に判断。
