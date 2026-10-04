variable "repository_name" {
  description = "API コンテナを保存する private ECR リポジトリ名"
  type        = string
  default     = "react-apigw-sandbox-api"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]*(?:[._/-][a-z0-9]+)*$", var.repository_name)) && length(var.repository_name) >= 2 && length(var.repository_name) <= 256
    error_message = "ECR の命名規則に従う2〜256文字のリポジトリ名を指定してください。"
  }
}
