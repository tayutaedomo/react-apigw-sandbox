# PoC の検証結果

## 目次

- [React と FastAPI の疎通](#react-と-fastapi-の疎通)
- [基本的な CORS](#基本的な-cors)
- [コンテナと構造化ログ](#コンテナと構造化ログ)
- [ECR とイメージの登録](#ecr-とイメージの登録)
- [Lambda と REST API](#lambda-と-rest-api)
- [アプリのエラー時 CORS](#アプリのエラー時-cors)
- [Amplify Hosting と手動デプロイ](#amplify-hosting-と手動デプロイ)
- [Gateway のパラメーター検証エラーと CORS](#gateway-のパラメーター検証エラーと-cors)
- [残タスク TODO](#残タスク-todo)

ローカルと Amplify Hosting から AWS 上の API まで、確認済みの挙動と検証方法を記録しています。

- 対象: React / FastAPI、CORS、コンテナ、ECR、Lambda / REST API、Amplify Hosting。
- 構成と操作手順: [ルート README](../README.md)から各ディレクトリへ移動できます。
- 検証範囲: 各項目の結果と、末尾の TODOを参照してください。

## React と FastAPI の疎通

画面から実 API を呼び、結果を表示できることを確認しています。

| 検証内容 | 確認できたこと | 検証方法 |
| --- | --- | --- |
| Hello World API | `GET /hello` が `200` と `{"message":"Hello World"}` を返す | API テスト |
| ブラウザーからの呼び出し | React が API の結果を取得し、`API: Hello World` を表示する | Playwright |
| 通信失敗と再試行 | エラーを表示し、接続回復後に同じボタンから再試行できる | Playwright |

## 基本的な CORS

許可 Origin の通信と、未許可 Origin に対するレスポンスヘッダーを確認しています。

| 検証内容 | 確認できたこと | 検証方法 |
| --- | --- | --- |
| 許可 Origin | `http://localhost:5173` に許可ヘッダーを返し、ブラウザーから本文を読める | API テスト / Playwright |
| 未許可 Origin | `http://localhost:9999` に `Access-Control-Allow-Origin` を付けない | API テスト |
| credentials | 許可レスポンスに `Access-Control-Allow-Credentials` を付けない | API テスト |

## コンテナと構造化ログ

同じ API をコンテナで実行し、リクエスト単位でログを確認できることを検証しています。

| 検証内容 | 確認できたこと | 検証方法 |
| --- | --- | --- |
| OS パッケージ更新 | 共通 OS ステージで更新し、再ビルドでも更新処理を実行する | Docker ビルド・パッケージ確認 |
| イメージのビルド | 独立スクリプトで digest 固定の `linux/amd64` イメージを作成できる | Docker ビルド |
| コンテナからの疎通 | React からコンテナ内の API を呼び、通信失敗後の再試行もできる | Playwright |
| Lambda 向けの配置 | Web Adapter の実行ファイルを同梱し、テスト依存を含めない | コンテナ内の確認 |
| 実行権限と同梱物 | 非 root で実行し、実行イメージに uv・テスト依存を含めない | コンテナ内の確認 |
| 読み取り専用での実行 | `/tmp` を用意した読み取り専用コンテナで API が動く | コンテナ起動・HTTP 疎通 |
| JSON ログ | HTTP と Uvicorn 起動ログを JSON として読み取れる | コンテナログの確認 |
| リクエストの識別 | ステータス・処理時間・相関 ID を記録し、同時リクエストで混同しない | API テスト |
| 例外の記録 | テスト用 API の未処理例外を ERROR ログに記録し、500 を返す | API テスト |
| 記録するデータ | 本文・クエリ文字列・認証ヘッダーをログに含めない | API テスト |

## ECR とイメージの登録

ECR の作成と Docker イメージの push を分離して実行できることを確認しています。

| 検証内容 | 確認できたこと | 検証方法 |
| --- | --- | --- |
| ECR 専用の IaC | ECR 1件を独立した Terraform state で作成できる | plan / apply |
| 再適用の差分 | 作成後の plan が変更なしになる | Terraform |
| リポジトリ設定 | immutable タグ、push 時のスキャン、AES256 暗号化が設定される | AWS CLI |
| イメージ登録 | 独立スクリプトで push し、digest URI を取得できる | Docker / AWS CLI |
| 入力と終了処理 | 不正タグ・異なるアーキテクチャを拒否し、成功・失敗時に一時認証設定を削除する | ローカルテスト |
| 脆弱性スキャン | 初回イメージのスキャン完了と検出内容を確認できる | ECR basic scanning |

初回スキャン（2026-10-04）は Critical 3件・High 13件・Medium 7件・Low 2件を検出しています。Critical はベースイメージ内の Perl に関する検出で、イメージ更新による解消は未検証です。

## Lambda と REST API

Lambda 上の Web Adapter を経由し、React から Hello World を取得できることを確認しています。

| 検証内容 | 確認できたこと | 検証方法 |
| --- | --- | --- |
| digest 指定 | push の出力を plan へ渡し、Lambda の実行 digest が一致する | Terraform / AWS CLI |
| Terraform の適用 | API 関連13リソースを追加し、再 plan で差分がない | plan / apply |
| Web Adapter | 拡張機能が起動し、REST API のイベントを FastAPI へ渡せる | Playwright / CloudWatch |
| ブラウザー疎通 | ローカル React が AWS の API を呼び、結果を表示する | Playwright |
| CORS と再試行 | 許可 Origin の通信と、通信失敗後の回復を確認できる | Playwright |
| 起動ログ | Uvicorn の起動ログを CloudWatch 上で JSON として取得できる | ログ解析 |
| Request ID | HTTP ログの Lambda ID がプラットフォームログの ID と一致する | ログ解析 |

## アプリのエラー時 CORS

FastAPI 全体を CORS とリクエストログで包み、未処理例外を含むエラー応答を検証しています。配置の理由と応答経路は [CORS 全体適用の図解](cors.md)に記載しています。

| 検証内容 | 確認できたこと | 検証方法 |
| --- | --- | --- |
| 標準のエラー | 404・405・422でステータスと本文を読める | API テスト / Playwright |
| 明示的なエラー | 400・409・418・429・500・502・503・504を読める | API テスト / Playwright |
| 未処理例外・応答検証エラー | 500にも CORS と相関 ID が付き、内部情報を本文へ出さない | API テスト / Playwright |
| 相関 ID | 応答の ID とログが一致し、JavaScript からヘッダーを読める | API テスト / Playwright |
| 429の再試行情報 | JavaScript から `Retry-After: 1` を読める | API テスト / Playwright |
| 未許可 Origin | サーバーはエラーを返すが、ブラウザーは本文を読み取れない | API テスト / Playwright |
| Originなし | エラー本文を返し、CORS 許可ヘッダーを付けない | API テスト |
| プリフライト許可 | GETを許可し、その後の本リクエストのエラー本文を読める | API テスト / Playwright・CDP |
| プリフライト拒否 | 未許可 Origin・ヘッダー・メソッドを拒否し、本リクエストを送らない | API テスト / Playwright・CDP |
| 拒否後の再試行 | 許可されるケースへ切り替えると本文を読める | Playwright |
| 未処理500後の連続呼び出し | 500・400・正常応答を続けて読める | Playwright |
| 検証 API の切り替え | 既定では `/errors/` を登録せず、有効化すると意図的なエラーを再現できる | API テスト |

- 検証環境: ローカル・コンテナ・AWS 上の API。
- ログの対応: 429・未処理500・応答検証500のステータスと相関 ID を照合。
- 画面記録: ケース選択・応答表示・拒否・再試行の PNG をレポートに添付。
- ログ: 処理済み HTTP エラーは INFO、未処理例外・応答検証エラーは ERROR。
- プリフライト: CORS が直接応答するため、アプリのリクエストログと相関 ID は付けない。
- 502・504・429: この項目は FastAPI が意図的に返す応答。Gateway の統合障害・タイムアウト・スロットリングとは別の検証。
- 認証・credentials: 未導入。401・403や credentials の許可は対象外。

### AWS で観測した接続再利用の問題

未処理500の直後に別の API を呼ぶと、Web Adapter の接続リセットにより Gateway が502を返す挙動を観測しました。

通信経路・再利用する対象・本番採用時の判断は [接続再利用の図解](connection-reuse.md)を参照してください。Lambda 実行環境の再利用を無効にする設定ではありません。

- アプリ側: Uvicorn は例外が再送出されると接続を閉じる。
- AWS側: 失敗した呼び出しは FastAPI の HTTP ログがなく、Adapter に `Connection reset by peer` が記録された。
- 対応: `AWS_LWA_POOL_IDLE_TIMEOUT_SECONDS=0` で Adapter の接続再利用を無効化。
- 判断: 例外の再送出と ERROR ログを維持し、毎回の TCP 接続コストを許容。性能への影響は未測定。
- 回帰検証: 未処理500 → 応答検証500 → 明示的400を2回繰り返し、その後に正常応答を取得。

### AWS で観測したログ出力の遅延

未処理500の ERROR ログが応答直後に見つからず、後続の正常呼び出しの後に出力されるケースを観測しました。

- ログ処理: FastAPI が500本文を送った後に例外を再送出し、外側のミドルウェアが記録する。
- 推測: Adapter が応答を返した後の Lambda 停止と、後続呼び出しでの後処理再開と整合する。CloudWatch 自体の配信遅延もあるため、停止時点までは測定していない。
- 相関 ID: 遅れて出力されたログでも、元の500応答と Lambda プラットフォームの ID に一致。
- 処理時間: 最終本文送信前に確定し、後続呼び出しまでの待機を除外。API テストで60秒の待機を模擬して検証。
- 限界: 応答直後のログ出力は保証しない。後続実行がない場合の出力保証は未検証。
- 仕様の参照: [Lambda の実行環境と未完了処理の再開](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)。

エラー本文の読み取りと CORS による拒否は確認済みです。Gateway のパラメーター検証エラーは下記で確認し、スロットリング・Lambda 統合障害は未検証です。

## Amplify Hosting と手動デプロイ

ビルド済み React を手動公開し、配信済み画面から別 Origin の AWS API を読み取れることを確認しています。

| 検証内容 | 確認できたこと | 検証方法 |
| --- | --- | --- |
| 配信先の管理 | API と Hosting を app の同じ state で管理し、ECR は独立させられる | Terraform |
| 手動公開 | ビルドとデプロイを分離し、ZIP のアップロード後に公開できる | 手動デプロイスクリプト |
| 失敗時の動作 | アップロード失敗で公開を開始せず、一時 ZIP を削除する | ローカルスクリプトテスト |
| 静的配信 | JS を正しい content-type で配信し、存在しない JS は404になる | HTTP 結合テスト |
| SPA の直接アクセス | ページ URL を直接開いても React の画面と API 呼び出しが動く | Playwright |
| 許可 Origin | Hosting の Origin を自動追加し、localhost と Amplify から正常・エラー応答を読める | API テスト / Playwright |
| エラーと追跡情報 | 配信済み画面から4xx・5xx、Request ID、429の Retry-After を読める | Playwright |
| プリフライト | 配信先でも GET許可・未許可ヘッダー／メソッド拒否を確認できる | Playwright / CDP |
| 再試行 | 配信済み画面でも通信失敗・CORS拒否の後に読み取りを再試行できる | Playwright |

- 配信経路: ブラウザー → REST API → Lambda / Web Adapter / FastAPI。Vite プロキシは使いません。
- 未許可 Origin の拒否: ローカル画面から AWS API を使って確認。Hosting モードの別ホスト名を使うケースは対象外。
- 操作手順: [アプリのリソース作成](../infra/app/README.md)、[ビルドと手動公開](../frontend/README.md#amplify-への手動デプロイ)、[配信済み画面のテスト](../e2e/README.md#amplify-配信済み画面のテスト)。

成果物の公開と AWS リソースの作成を分離し、実際に配信された React からの CORS を検証しています。

## Gateway のパラメーター検証エラーと CORS

Lambda を呼び出さずに Gateway の400を再現し、Gateway Response の CORS 設定前後でブラウザーの読み取りを確認しています。[構成と比較手順の図解](gateway-cors.md)を参照してください。

| 検証内容 | 確認できたこと | 検証方法 |
| --- | --- | --- |
| Gateway の検証エラー | `/gateway-probe` の必須クエリ `value` がないと400を生成する | HTTP 結合テスト |
| CORS なし | 400本文は存在するが、Hosting の JavaScript から読めない | HTTP / ブラウザー結合テスト |
| CORS あり | Hosting から400・本文・Gateway の request ID を読める | HTTP / ブラウザー結合テスト |
| 未許可 Origin | 固定の許可 Origin と一致せず、ブラウザーが本文の読み取りを拒否する | ブラウザー結合テスト |
| 正常への切り替え | 必須クエリ付き GET は Gateway の MOCK 統合から200を返し、本文を読める | HTTP / ブラウザー結合テスト |
| 既存 API | Hello World の表示・再試行と Lambda の ID の取得を維持する | Playwright |

- 対象: `BAD_REQUEST_PARAMETERS`。FastAPI の422とは別の検証エラー。
- 許可: Gateway のエラーと MOCK 応答は Hosting の一つの Origin に固定。FastAPI の追加許可一覧とは独立。
- 記録: ブラウザー結合テストの結果をテスト専用パネルに表示し、400/CORS拒否・正常 GET の PNG を添付。
- 観測: 未定義 POST は既存の greedy proxy に転送され FastAPI の404になったため、この構成ではパラメーター検証を使用。
- 公開への反映: apply 完了直後に前の応答を観測。設定の反映後に比較。
- 未検証: スロットリング・Lambda 統合障害・認証・credentials・検証パスのプリフライト許可。

Gateway の400と FastAPI のエラーを分け、CORS が必要な応答の発生箇所を確認しています。

## 残タスク TODO

Gateway のパラメーター検証エラーの CORS は確認済みです。次の候補はスロットリングと Lambda 統合障害です。アプリが意図的に返す429・502・504は確認済みですが、実際のスロットリング・統合障害は未検証です。

### Gateway・Lambda 統合障害の CORS

- [x] Gateway のパラメーター検証エラーを再現する。
- [ ] Gateway のスロットリング等、他のエラー種別を検証する。
- [x] Gateway のパラメーター検証エラーに CORS を設定し、許可・未許可 Origin の挙動を確認する。
- [ ] Lambda の呼び出し権限不足・タイムアウト・不正な統合応答を再現し、エラー応答と CORS を確認する。
- [x] Amplify のページの Origin から、Gateway の400本文の読み取りと CORS による拒否を確認する。
- [x] Gateway の400/CORS拒否から正常 GET へ切り替え、画面の変化を記録する。
- [ ] Lambda 統合障害の設定を戻した後の正常応答・再試行を検証する。
- [x] Gateway の通信経路・エラー発生箇所・CORS の適用範囲を図解する。
- [ ] Lambda 統合障害の通信経路・発生箇所・CORS の適用範囲を図解する。

### ベース構成の追加検証・改善

- [ ] イメージの脆弱性検出に対応し、最新のデプロイ対象イメージを再スキャンする。
- [ ] Web Adapter の接続再利用を無効化した場合の性能を測定し、本番採用時の判断材料を整理する。
- [ ] 未処理500のログ出力遅延を追加検証する。後続呼び出しがない場合の出力も確認する。
- [ ] 保存した digest・画面成果物を使い、API と画面の切り戻し手順を実環境で検証する。

### 認証・credentials：方針決定後に検証

- [ ] 認証方式を選定して実装し、認証エラーの401・403と CORS を検証する。
- [ ] credentials を含む通信方式を決め、許可・拒否・プリフライトの挙動を検証する。

完了した項目はチェックし、確認した挙動と検証方法を本文の該当項目に記録します。認証・credentials は、方式を決めてから着手する対象です。
