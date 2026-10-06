variable "image_uri" {
  description = "デプロイする private ECR イメージの digest URI"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com(\\.cn)?/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$", var.image_uri))
    error_message = "タグではなく ECR の digest URI（repository@sha256:...）を指定してください。"
  }
}

variable "repository_name" {
  description = "ECR 専用 state で作成したリポジトリ名"
  type        = string
  default     = "react-apigw-sandbox-api"
}

variable "enable_error_endpoints" {
  description = "FastAPI の意図的なエラー検証 API を有効にする"
  type        = bool
  default     = false
}

variable "allowed_origins" {
  description = "ブラウザーからの読み取りを許可する Origin の一覧（完全一致）"
  type        = list(string)
  default     = ["http://localhost:5173"]

  validation {
    condition = length(var.allowed_origins) > 0 && alltrue([
      for origin in var.allowed_origins : can(regex("^https?://[A-Za-z0-9.-]+(:[0-9]+)?$", origin))
    ])
    error_message = "空でない http(s)://host[:port] の一覧を指定してください。wildcard・パスは使用できません。"
  }
}
