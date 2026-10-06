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
  value       = "https://${aws_amplify_branch.sandbox.branch_name}.${aws_amplify_app.frontend.default_domain}"
}

output "region" {
  description = "配信先と同じリージョンで AWS CLI を実行するための値"
  value       = data.aws_region.current.region
}
