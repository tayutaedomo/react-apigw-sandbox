# -----------------------------------------------------------------------------
# 1. 実行環境と静的サイトの配信先
# -----------------------------------------------------------------------------
# 認証とリージョンは実行環境から取得する。API / ECR の state には依存しない。
provider "aws" {}
data "aws_region" "current" {}

# Git と接続せず、ローカルで作成した dist を手動デプロイする静的 Hosting。
# Terraform は配信先だけを作成し、ビルド・アップロード・公開を実行しない。
resource "aws_amplify_app" "frontend" {
  name                        = "react-apigw-sandbox-frontend"
  platform                    = "WEB"
  enable_auto_branch_creation = false

  # SPA のページ URL を直接開いても index.html を返す。
  # JS / CSS 等の拡張子を除外し、アセットを HTML に置き換えない。
  # AWS の SPA 向け推奨例: https://docs.aws.amazon.com/amplify/latest/userguide/redirect-rewrite-examples.html
  custom_rule {
    source = "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>"
    target = "/index.html"
    status = "200"
  }
}

# -----------------------------------------------------------------------------
# 2. 手動デプロイの公開単位
# -----------------------------------------------------------------------------
# Amplify の branch は配信 URL の単位。Git ブランチの自動連携は行わない。
# 固定の sandbox URL に、明示的にアップロードした成果物だけを公開する。
resource "aws_amplify_branch" "sandbox" {
  app_id            = aws_amplify_app.frontend.id
  branch_name       = "sandbox"
  stage             = "DEVELOPMENT"
  framework         = "React"
  enable_auto_build = false
}
