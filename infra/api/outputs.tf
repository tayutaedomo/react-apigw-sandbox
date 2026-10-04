output "api_base_url" {
  description = "フロントエンド・結合テストで使用する REST API の URL"
  value       = aws_api_gateway_stage.sandbox.invoke_url
}

output "function_name" {
  description = "CloudWatch で確認する Lambda 関数名"
  value       = aws_lambda_function.api.function_name
}

output "image_uri" {
  description = "この state がデプロイした digest URI"
  value       = aws_lambda_function.api.image_uri
}
