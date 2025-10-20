# =============================================================================
# GITHUB ACTIONS IAM USER - Para CI/CD
# =============================================================================

resource "aws_iam_user" "github_actions" {
  name = "${var.project}-github-actions"
  path = "/"

  tags = merge(var.common_tags, {
    Name        = "${var.project}-github-actions-user"
    Purpose     = "CI/CD automation"
    Service     = "GitHub Actions"
  })
}

resource "aws_iam_access_key" "github_actions" {
  user = aws_iam_user.github_actions.name
}

# Policy para ECR access
resource "aws_iam_user_policy" "github_actions_ecr" {
  name = "${var.project}-github-actions-ecr-policy"
  user = aws_iam_user.github_actions.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
          "ecr:ListImages"
        ]
        Resource = [
          aws_ecr_repository.app.arn,
          "*"
        ]
      }
    ]
  })
}

# Policy para Auto Scaling (restart deployments)
resource "aws_iam_user_policy" "github_actions_autoscaling" {
  name = "${var.project}-github-actions-autoscaling-policy"
  user = aws_iam_user.github_actions.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:UpdateAutoScalingGroup",
          "autoscaling:DescribeInstances",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      }
    ]
  })
}

# =============================================================================
# OUTPUTS PARA GITHUB SECRETS
# =============================================================================

output "github_actions_credentials" {
  description = "Credenciais para configurar no GitHub Actions"
  value = {
    aws_access_key_id     = aws_iam_access_key.github_actions.id
    aws_secret_access_key = aws_iam_access_key.github_actions.secret
    aws_account_id        = data.aws_caller_identity.current.account_id
    aws_region            = var.aws_region
    ecr_repository        = aws_ecr_repository.app.name
    alb_dns_name         = aws_lb.app.dns_name
  }
  sensitive = true
}

# Data source para account ID
data "aws_caller_identity" "current" {}