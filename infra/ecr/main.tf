# プロファイルとリージョンは AWS の環境変数・共有設定から取得する。
# この state では ECR だけを管理し、Lambda・API Gateway・Amplify とは分離する。
provider "aws" {}

resource "aws_ecr_repository" "api" {
  name                 = var.repository_name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  # タグの上書きを禁止し、イメージが残っているリポジトリを誤って削除しない。
  # 暗号化は ECR 標準の AES256 を使い、専用 KMS キーは作成しない。
  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project   = "react-apigw-sandbox"
    ManagedBy = "Terraform"
  }
}
