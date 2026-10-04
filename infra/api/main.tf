# プロファイルとリージョンは実行環境から取得する。ECR の state は共有しない。
provider "aws" {}

data "aws_ecr_repository" "api" {
  name = var.repository_name
}

locals {
  name = "react-apigw-sandbox-api"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = 7
}

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

resource "aws_iam_role_policy" "lambda" {
  name = "${local.name}-runtime"
  role = aws_iam_role.lambda.id
  # ロググループは Terraform で先に作成し、ログ書き込み権限をそこへ限定する。
  # 同一アカウントの ECR は execution role 側で対象 repository の取得を許可する。
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
        Resource = data.aws_ecr_repository.api.arn
      }
    ]
  })
}

resource "aws_lambda_function" "api" {
  function_name = local.name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  architectures = ["x86_64"]
  memory_size   = 512
  timeout       = 15

  # アプリと Uvicorn の JSON に加え、Lambda のプラットフォームログも JSON 化する。
  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
  }

  environment {
    variables = {
      POWERTOOLS_LOG_LEVEL = "INFO"
      # Web Adapter の readiness 待機を初期化フェーズ内で行う。
      AWS_LWA_ASYNC_INIT = "false"
    }
  }

  lifecycle {
    precondition {
      condition     = startswith(var.image_uri, "${data.aws_ecr_repository.api.repository_url}@sha256:")
      error_message = "同じリージョン・アカウントの指定 ECR リポジトリにあるイメージを使用してください。"
    }
  }

  depends_on = [aws_iam_role_policy.lambda]
}
