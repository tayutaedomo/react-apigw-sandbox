# PoC の検証結果

ローカルから AWS 上の API まで、確認済みの挙動と検証方法を記録しています。

- 対象: React / FastAPI、CORS、コンテナ、ECR、Lambda / REST API。
- 構成と操作手順: [ルート README](../README.md)から各ディレクトリへ移動できます。
- 検証範囲: 各項目の結果と、末尾の未検証事項を参照してください。

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

エラー本文の読み取りと CORS による拒否は確認済みです。Gateway 自身が生成するエラーは下記の未検証範囲です。

## 未検証の範囲

Gateway 自身のエラー時 CORS、Lambda 統合の障害、Amplify 上のブラウザー疎通、認証・credentials は未検証です。
