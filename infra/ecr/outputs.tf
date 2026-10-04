output "repository_url" {
  description = "イメージ push 先の URL"
  value       = aws_ecr_repository.api.repository_url
}

output "repository_name" {
  description = "イメージ照会に使うリポジトリ名"
  value       = aws_ecr_repository.api.name
}
