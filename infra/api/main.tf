# -----------------------------------------------------------------------------
# 1. 実行環境と既存リソース
# -----------------------------------------------------------------------------
# プロファイルとリージョンは実行環境から取得する。ECR の state は共有しない。
provider "aws" {}

# ECR は別の state で管理するため、ここでは既存 repository を照会する。
# API を削除してもイメージの保存先が削除されないよう、resource として作成しない。
data "aws_ecr_repository" "api" {
  name = var.repository_name
}

# 関数・API・ログに共通の名前を使い、AWS 上で関連するリソースを識別しやすくする。
locals {
  name = "react-apigw-sandbox-api"
}

# -----------------------------------------------------------------------------
# 2. ログの保存先と Lambda の実行権限
# -----------------------------------------------------------------------------
# Lambda の既定命名規則に合わせて先に作成し、保持期間を管理する。
# 初期の疎通確認には7日保持とし、ログが無期限に蓄積されることを避ける。
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = 7
}

# 信頼ポリシーは、この role を引き受けられるサービスを Lambda に限定する。
# ログ書き込みなどの実行権限は、下の role policy で別に定義する。
resource "aws_iam_role" "lambda" {
  name = "${local.name}-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# 汎用の managed policy ではなく、この API が使うリソースに限定した権限を付与する。
resource "aws_iam_role_policy" "lambda" {
  name = "${local.name}-runtime"
  role = aws_iam_role.lambda.id
  # ロググループは Terraform で先に作成し、ログ書き込み権限をそこへ限定する。
  # 同一アカウントの ECR は execution role 側で対象 repository の取得を許可する。
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # グループ作成は Terraform が担うため、Lambda に CreateLogGroup は付与しない。
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      },
      # 対象 repository の manifest とレイヤーを取得する権限だけを付与する。
      # push・削除や、ほかの repository へのアクセスは不要。
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
        Resource = data.aws_ecr_repository.api.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# 3. コンテナ方式の Lambda
# -----------------------------------------------------------------------------
# Web Adapter を同梱したイメージを使うため、zip の runtime / handler は設定しない。
# digest URI により、plan で確認したイメージと実行するイメージを一致させる。
resource "aws_lambda_function" "api" {
  function_name = local.name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  # ビルドスクリプトの linux/amd64 と実行アーキテクチャを合わせる。
  architectures = ["x86_64"]
  # 512 MB / 15秒は初期疎通の設定値。性能・タイムアウトの検証時に調整する。
  memory_size = 512
  timeout     = 15

  # アプリと Uvicorn の JSON に加え、Lambda のプラットフォームログも JSON 化する。
  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
  }

  environment {
    variables = {
      # Uvicorn と HTTP ログの出力レベルをアプリ側でも INFO に揃える。
      POWERTOOLS_LOG_LEVEL = "INFO"
      # Web Adapter の readiness 待機を初期化フェーズ内で行う。
      AWS_LWA_ASYNC_INIT = "false"
    }
  }

  # variables.tf の URI 形式検証に加え、実際の repository URL と一致させる。
  # 別アカウント・別リージョン・別 repository のイメージを誤指定しないための検証。
  lifecycle {
    precondition {
      condition     = startswith(var.image_uri, "${data.aws_ecr_repository.api.repository_url}@sha256:")
      error_message = "同じリージョン・アカウントの指定 ECR リポジトリにあるイメージを使用してください。"
    }
  }

  # role ARN の参照だけでは policy の作成完了を待たないため、依存を明示する。
  # 関数作成時に ECR 取得とログ書き込みの権限を用意しておく。
  depends_on = [aws_iam_role_policy.lambda]
}

# -----------------------------------------------------------------------------
# 4. REST API のルーティングと Lambda proxy 統合
# -----------------------------------------------------------------------------
# HTTP API ではなく REST API を使い、後続の Gateway エラー時 CORS の検証に備える。
# 今回はリージョン内の API 疎通を検証するため、edge-optimized ではなく REGIONAL を使う。
resource "aws_api_gateway_rest_api" "api" {
  name = local.name
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# FastAPI 側でパスを管理できるよう、/hello など配下のパスをまとめて渡す。
# API のエンドポイント追加ごとに Gateway の resource を増やす必要をなくす。
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "{proxy+}"
}

locals {
  # greedy proxy はルート自体に一致しないため、ルートも別に統合する。
  resource_ids = {
    root  = aws_api_gateway_rest_api.api.root_resource_id
    proxy = aws_api_gateway_resource.proxy.id
  }
}

# root と proxy に同じ定義を適用し、片方だけ設定が変わることを避ける。
# ANY でメソッドの判定を FastAPI に委譲し、OPTIONS も CORS ミドルウェアへ渡す。
# 認証方式は未決定のため NONE。ブラウザーの CORS 制御は認証の代替にはならない。
resource "aws_api_gateway_method" "api" {
  for_each      = local.resource_ids
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = each.value
  http_method   = "ANY"
  authorization = "NONE"
}

# AWS_PROXY はリクエストを Lambda イベントとして渡し、Lambda の応答を HTTP へ戻す。
# Web Adapter がイベントを HTTP に変換するため、Gateway で本文の mapping は作らない。
resource "aws_api_gateway_integration" "lambda" {
  for_each    = local.resource_ids
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = each.value
  http_method = aws_api_gateway_method.api[each.key].http_method
  # Lambda Invoke API は POST。ブラウザーから受け付ける ANY とは別の設定。
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
  # この統合の待機上限を29秒とし、Lambda 自体の15秒上限より長く設定する。
  timeout_milliseconds = 29000
}

# 実行 role は Lambda 内で使う権限。この permission は外部からの呼び出し許可。
# 呼び出し元をこの REST API の sandbox ステージに限定し、ほかの API へ開放しない。
resource "aws_lambda_permission" "gateway" {
  statement_id  = "AllowSandboxRestApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/sandbox/*"
}

# -----------------------------------------------------------------------------
# 5. API 定義の snapshot と公開ステージ
# -----------------------------------------------------------------------------
# REST API は resource / method を作るだけでは公開されず、deployment が必要。
# Lambda のイメージ更新は同じ invoke ARN を使うため、API 定義の更新とは分けて扱う。
resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  # 設定した API 定義だけを hash 化する。AWS が補完する computed 属性を含めると、
  # apply 後の refresh で hash が変わり、変更がなくても再 deployment されてしまう。
  triggers = {
    redeployment = sha1(jsonencode({
      proxy_path = aws_api_gateway_resource.proxy.path_part
      methods = { for key, method in aws_api_gateway_method.api : key => {
        resource_id   = method.resource_id
        http_method   = method.http_method
        authorization = method.authorization
      } }
      integrations = { for key, integration in aws_api_gateway_integration.lambda : key => {
        resource_id             = integration.resource_id
        http_method             = integration.http_method
        integration_http_method = integration.integration_http_method
        type                    = integration.type
        uri                     = integration.uri
        timeout_milliseconds    = integration.timeout_milliseconds
      } }
    }))
  }
  # 新しい snapshot を作り、ステージを切り替えてから古い snapshot を削除する。
  # 公開ステージが参照する deployment を先に削除しないようにする。
  lifecycle {
    create_before_destroy = true
  }
  # 更新判定の参照で method / integration を待ち、明示依存で呼び出し許可も待つ。
  # API 公開時に Lambda を呼び出せる構成を揃える。
  depends_on = [aws_lambda_permission.gateway]
}

# sandbox という固定ステージを最新 snapshot に向け、利用する URL を維持する。
# 同じ URL で検証できるよう、deployment ID を URL に使わない。
resource "aws_api_gateway_stage" "sandbox" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.api.id
  stage_name    = "sandbox"
}
