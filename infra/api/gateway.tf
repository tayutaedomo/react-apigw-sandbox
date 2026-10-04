resource "aws_api_gateway_rest_api" "api" {
  name = local.name
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

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

resource "aws_api_gateway_method" "api" {
  for_each      = local.resource_ids
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = each.value
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  for_each                = local.resource_ids
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = each.value
  http_method             = aws_api_gateway_method.api[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
  timeout_milliseconds    = 29000
}

resource "aws_lambda_permission" "gateway" {
  statement_id  = "AllowSandboxRestApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/sandbox/*"
}

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
  lifecycle {
    create_before_destroy = true
  }
  depends_on = [aws_lambda_permission.gateway]
}

resource "aws_api_gateway_stage" "sandbox" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.api.id
  stage_name    = "sandbox"
}
