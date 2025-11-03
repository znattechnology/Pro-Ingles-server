# =============================================================================
# TERRAFORM OUTPUTS - PROENGLISH-BACKEND
# =============================================================================

# VPC OUTPUTS
output "vpc_id" {
  description = "ID da VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block da VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "IDs das subnets privadas"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "IDs das subnets públicas"
  value       = module.vpc.public_subnets
}

# APPLICATION LOAD BALANCER OUTPUTS
output "alb_dns_name" {
  description = "DNS name do Application Load Balancer"
  value       = aws_lb.app.dns_name
}

output "alb_zone_id" {
  description = "Zone ID do Application Load Balancer"
  value       = aws_lb.app.zone_id
}

output "alb_arn" {
  description = "ARN do Application Load Balancer"
  value       = aws_lb.app.arn
}

# AUTO SCALING GROUP OUTPUTS
output "asg_name" {
  description = "Nome do Auto Scaling Group"
  value       = aws_autoscaling_group.app.name
}

output "asg_arn" {
  description = "ARN do Auto Scaling Group"
  value       = aws_autoscaling_group.app.arn
}

# ECR OUTPUTS
output "ecr_repository_url" {
  description = "URL do repositório ECR"
  value       = aws_ecr_repository.app.repository_url
}

output "ecr_repository_arn" {
  description = "ARN do repositório ECR"
  value       = aws_ecr_repository.app.arn
}

# IAM OUTPUTS
output "ec2_role_arn" {
  description = "ARN da IAM role para EC2"
  value       = aws_iam_role.ec2_role.arn
}

output "ec2_instance_profile_name" {
  description = "Nome do instance profile para EC2"
  value       = aws_iam_instance_profile.ec2_profile.name
}

# SECRETS MANAGER
output "django_secrets_arn" {
  description = "ARN do secret do Django no Secrets Manager"
  value       = aws_secretsmanager_secret.django_secrets.arn
}

# CLOUDWATCH
output "log_group_name" {
  description = "Nome do CloudWatch log group"
  value       = var.enable_logging ? aws_cloudwatch_log_group.app_logs[0].name : null
}

# DEPLOYMENT INFO
output "deployment_info" {
  description = "Informações importantes para deployment"
  value = {
    alb_dns_name      = aws_lb.app.dns_name
    ecr_repository    = aws_ecr_repository.app.repository_url
    aws_region        = var.aws_region
    app_url          = "http://${aws_lb.app.dns_name}"
    asg_name         = aws_autoscaling_group.app.name
  }
}