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

output "app_id" {
  description = "手動デプロイ先の Amplify app ID"
  value       = aws_amplify_app.frontend.id
}

output "branch_name" {
  description = "手動デプロイ先の公開ブランチ"
  value       = aws_amplify_branch.sandbox.branch_name
}

output "hosting_url" {
  description = "ブラウザーテストと API の CORS 許可に使用する Origin"
  value       = local.hosting_origin
}

output "region" {
  description = "配信先と同じリージョンで AWS CLI を実行するための値"
  value       = data.aws_region.current.region
}
