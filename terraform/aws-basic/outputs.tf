# =============================================================================
# AWS BASIC OUTPUTS - PROENGLISH PLATFORM
# =============================================================================

# =============================================================================
# EC2 INSTANCE INFORMATION
# =============================================================================

output "instance_id" {
  description = "ID da instância EC2"
  value       = aws_instance.app.id
}

output "instance_public_ip" {
  description = "IP público da instância"
  value       = aws_instance.app.public_ip
}

output "instance_private_ip" {
  description = "IP privado da instância"
  value       = aws_instance.app.private_ip
}

output "instance_public_dns" {
  description = "DNS público da instância"
  value       = aws_instance.app.public_dns
}

output "instance_type" {
  description = "Tipo da instância EC2"
  value       = aws_instance.app.instance_type
}

output "instance_availability_zone" {
  description = "Zona de disponibilidade da instância"
  value       = aws_instance.app.availability_zone
}

# =============================================================================
# ELASTIC IP (SE HABILITADO)
# =============================================================================

output "elastic_ip" {
  description = "Elastic IP (se habilitado)"
  value       = var.use_elastic_ip ? aws_eip.app[0].public_ip : null
}

# =============================================================================
# SECURITY GROUP INFORMATION
# =============================================================================

output "security_group_id" {
  description = "ID do Security Group"
  value       = aws_security_group.app.id
}

output "security_group_name" {
  description = "Nome do Security Group"
  value       = aws_security_group.app.name
}

# =============================================================================
# S3 BUCKET INFORMATION
# =============================================================================

output "s3_bucket_name" {
  description = "Nome do bucket S3 para media"
  value       = aws_s3_bucket.media.bucket
}

output "s3_bucket_domain" {
  description = "Domínio do bucket S3"
  value       = aws_s3_bucket.media.bucket_domain_name
}

output "s3_bucket_arn" {
  description = "ARN do bucket S3"
  value       = aws_s3_bucket.media.arn
}

output "s3_bucket_url" {
  description = "URL do bucket S3"
  value       = "https://${aws_s3_bucket.media.bucket_domain_name}"
}

# =============================================================================
# KEY PAIR INFORMATION
# =============================================================================

output "key_pair_name" {
  description = "Nome do key pair"
  value       = aws_key_pair.main.key_name
}

output "key_pair_fingerprint" {
  description = "Fingerprint do key pair"
  value       = aws_key_pair.main.fingerprint
}

# =============================================================================
# VPC INFORMATION
# =============================================================================

output "vpc_id" {
  description = "ID da VPC (default)"
  value       = data.aws_vpc.default.id
}

output "subnet_id" {
  description = "ID da subnet utilizada"
  value       = data.aws_subnet.default.id
}

# =============================================================================
# DNS INFORMATION (SE HABILITADO)
# =============================================================================

output "hosted_zone_id" {
  description = "ID da hosted zone Route 53 (se criada)"
  value       = var.create_hosted_zone ? aws_route53_zone.main[0].zone_id : null
}

output "hosted_zone_name_servers" {
  description = "Name servers da hosted zone (se criada)"
  value       = var.create_hosted_zone ? aws_route53_zone.main[0].name_servers : null
}

# =============================================================================
# APPLICATION URLS
# =============================================================================

output "application_url" {
  description = "URL da aplicação"
  value       = "http://${aws_instance.app.public_ip}:8000"
}

output "admin_url" {
  description = "URL do Django Admin"
  value       = "http://${aws_instance.app.public_ip}:8000/admin/"
}

output "api_url" {
  description = "URL da API"
  value       = "http://${aws_instance.app.public_ip}:8000/api/"
}

# =============================================================================
# SSH CONNECTION
# =============================================================================

output "ssh_connection" {
  description = "Comando SSH para conectar à instância"
  value       = "ssh -i ~/.ssh/id_rsa ec2-user@${aws_instance.app.public_ip}"
}

# =============================================================================
# MONITORING INFORMATION
# =============================================================================

output "cloudwatch_alarm_cpu" {
  description = "Nome do alarme de CPU"
  value       = aws_cloudwatch_metric_alarm.high_cpu.alarm_name
}

# =============================================================================
# COST ESTIMATION
# =============================================================================

output "estimated_monthly_cost" {
  description = "Custo mensal estimado (USD)"
  value = {
    ec2_instance     = var.instance_type == "t3.small" ? 15.18 : var.instance_type == "t3.micro" ? 0 : 30.36
    ebs_storage      = var.root_volume_size * 0.10  # $0.10/GB/mês para gp3
    elastic_ip       = var.use_elastic_ip ? 3.65 : 0
    s3_storage       = 1.00  # Estimativa para poucos GB
    data_transfer    = 2.00  # Estimativa para tráfego básico
    route53          = var.create_hosted_zone ? 0.50 : 0
    total_estimated  = (var.instance_type == "t3.small" ? 15.18 : var.instance_type == "t3.micro" ? 0 : 30.36) + (var.root_volume_size * 0.10) + (var.use_elastic_ip ? 3.65 : 0) + 1.00 + 2.00 + (var.create_hosted_zone ? 0.50 : 0)
  }
}

# =============================================================================
# ENVIRONMENT VARIABLES FOR APPLICATION
# =============================================================================

output "environment_variables" {
  description = "Variáveis de ambiente para configurar na aplicação"
  value = {
    # Server configuration
    SERVER_IP           = aws_instance.app.public_ip
    SERVER_REGION       = var.aws_region
    
    # Database
    DATABASE_URL        = var.neon_database_url
    
    # Django settings
    DJANGO_SECRET_KEY   = var.django_secret_key
    DJANGO_DEBUG        = var.django_debug
    DJANGO_ALLOWED_HOSTS = "${var.domain_name},${aws_instance.app.public_ip},${aws_instance.app.public_dns}"
    
    # AWS S3 settings
    AWS_STORAGE_BUCKET_NAME = aws_s3_bucket.media.bucket
    AWS_S3_REGION_NAME      = var.aws_region
    AWS_S3_ENDPOINT_URL     = "https://s3.${var.aws_region}.amazonaws.com"
    
    # CORS settings
    CORS_ALLOWED_ORIGINS = join(",", var.cors_allowed_origins)
    
    # Cache settings (local Redis)
    REDIS_URL           = "redis://localhost:6379/0"
    CACHE_URL           = "redis://localhost:6379/1"
  }
  sensitive = true
}

# =============================================================================
# NEXT STEPS INFORMATION
# =============================================================================

output "next_steps" {
  description = "Próximos passos após o deploy"
  value = [
    "1. Conectar via SSH: ssh -i ~/.ssh/id_rsa ec2-user@${aws_instance.app.public_ip}",
    "2. Verificar status da instalação: sudo tail -f /var/log/cloud-init-output.log",
    "3. Aguardar conclusão do setup (5-10 minutos)",
    "4. Acessar aplicação: http://${aws_instance.app.public_ip}:8000",
    "5. Configurar domínio DNS apontando para: ${aws_instance.app.public_ip}",
    "6. Configurar SSL com Let's Encrypt",
    "7. Fazer deploy da aplicação Django"
  ]
}

# =============================================================================
# SECURITY REMINDERS
# =============================================================================

output "security_reminders" {
  description = "Lembretes de segurança importantes"
  value = [
    "⚠️  Alterar SSH access de 0.0.0.0/0 para IPs específicos",
    "⚠️  Configurar backup regular dos dados",
    "⚠️  Monitorar custos mensalmente",
    "⚠️  Manter sistema atualizado",
    "⚠️  Configurar SSL/HTTPS em produção",
    "⚠️  Revisar logs de segurança regularmente"
  ]
}

# =============================================================================
# DEPLOYMENT INFORMATION
# =============================================================================

output "deployment_info" {
  description = "Informações do deployment"
  value = {
    terraform_workspace = terraform.workspace
    deployment_time     = timestamp()
    aws_region         = var.aws_region
    project_name       = var.project_name
    environment        = var.environment
  }
}