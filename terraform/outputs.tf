# =============================================================================
# AWS BASIC OUTPUTS - PROENGLISH PLATFORM
# Budget: $40/month - Configuração econômica
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

output "availability_zone" {
  description = "Zona de disponibilidade da instância"
  value       = aws_instance.app.availability_zone
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
  description = "Nome do bucket S3 para media (existente)"
  value       = "lms-s3-backet"
}

output "s3_bucket_domain" {
  description = "Domínio do bucket S3"
  value       = "lms-s3-backet.s3.us-east-1.amazonaws.com"
}

output "s3_bucket_url" {
  description = "URL do bucket S3"
  value       = "https://lms-s3-backet.s3.us-east-1.amazonaws.com"
}

output "cloudfront_domain" {
  description = "Domínio CloudFront (CDN)"
  value       = "https://d13552ljikd29j.cloudfront.net"
}

# =============================================================================
# SSH INFORMATION
# =============================================================================

output "ssh_connection" {
  description = "Comando SSH para conectar à instância"
  value       = "ssh -i ~/.ssh/id_rsa ec2-user@${aws_instance.app.public_ip}"
}

output "key_pair_name" {
  description = "Nome do key pair"
  value       = aws_key_pair.main.key_name
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
# COST BREAKDOWN
# =============================================================================

output "estimated_monthly_cost" {
  description = "Custo mensal estimado (USD)"
  value = {
    ec2_instance    = var.instance_type == "t3.small" ? 15.18 : var.instance_type == "t3.micro" ? 8.76 : 30.36
    ebs_storage     = var.root_volume_size * 0.10  # $0.10/GB/mês para gp3
    s3_storage      = 0.00   # Usando bucket existente
    data_transfer   = 3.00   # Estimativa para tráfego básico
    total_estimated = (var.instance_type == "t3.small" ? 15.18 : var.instance_type == "t3.micro" ? 8.76 : 30.36) + (var.root_volume_size * 0.10) + 0.00 + 3.00
  }
}

output "cost_breakdown" {
  description = "Breakdown detalhado de custos"
  value = {
    "💰 CUSTO MENSAL ESTIMADO" = "~$20/mês"
    "🖥️  EC2 t3.small"          = "$15.18"
    "💾 EBS 20GB (gp3)"        = "$2.00"
    "☁️  S3 storage (existente)" = "$0.00"
    "🌐 Data transfer"         = "$3.00"
    "⚠️  Margem de segurança"   = "$0.18"
    "🎯 DENTRO DO ORÇAMENTO"   = "✅ $40/mês"
    "💾 S3 Bucket"             = "lms-s3-backet (existente)"
    "🚀 CloudFront CDN"        = "Configurado"
  }
}

# =============================================================================
# NEXT STEPS INFORMATION
# =============================================================================

output "next_steps" {
  description = "Próximos passos após o deploy"
  value = [
    "1. 🔐 Conectar via SSH: ssh -i ~/.ssh/id_rsa ec2-user@${aws_instance.app.public_ip}",
    "2. 📋 Verificar status da instalação: sudo tail -f /var/log/cloud-init-output.log",
    "3. ⏳ Aguardar conclusão do setup (5-10 minutos)",
    "4. 📂 Upload do código Django para: /opt/${var.project}/app/",
    "5. ⚙️ Configurar arquivo .env: /opt/${var.project}/.env",
    "6. 🚀 Iniciar aplicação: sudo systemctl start ${var.project}",
    "7. 🌐 Acessar aplicação: http://${aws_instance.app.public_ip}:8000",
    "8. 🔒 Configurar SSL para produção",
    "9. 📊 Monitorar custos mensalmente"
  ]
}

# =============================================================================
# MANAGEMENT COMMANDS
# =============================================================================

output "management_commands" {
  description = "Comandos úteis para gerenciar a aplicação"
  value = {
    "🔄 Status do sistema"     = "/opt/${var.project}/scripts/status.sh"
    "🚀 Iniciar aplicação"     = "sudo systemctl start ${var.project}"
    "🛑 Parar aplicação"       = "sudo systemctl stop ${var.project}"
    "🔄 Reiniciar aplicação"   = "sudo systemctl restart ${var.project}"
    "📊 Status do serviço"     = "sudo systemctl status ${var.project}"
    "💾 Fazer backup"          = "/opt/${var.project}/scripts/backup.sh"
    "📝 Ver logs da aplicação" = "journalctl -u ${var.project} -f"
    "📈 Monitorar recursos"    = "htop"
  }
}

# =============================================================================
# ENVIRONMENT VARIABLES FOR APPLICATION
# =============================================================================

output "environment_setup" {
  description = "Configuração de ambiente para a aplicação"
  value = {
    # AWS S3 Configuration (existente)
    USE_S3                  = "True"
    AWS_ACCESS_KEY_ID       = "AKIATJHQD7YUMJW3I34U"
    AWS_S3_BUCKET_NAME      = "lms-s3-backet"
    AWS_S3_REGION_NAME      = "us-east-1"
    AWS_CLOUDFRONT_DOMAIN   = "https://d13552ljikd29j.cloudfront.net"
    
    # Server Information
    SERVER_IP     = aws_instance.app.public_ip
    SERVER_REGION = var.aws_region
    
    # Database (Neon existente)
    DATABASE_URL = var.neon_database_url
    
    # Django Settings
    DJANGO_SECRET_KEY    = var.django_secret_key
    DJANGO_DEBUG         = "False"
    DJANGO_ALLOWED_HOSTS = "${aws_instance.app.public_ip},${aws_instance.app.public_dns}"
    
    # Cache Settings
    REDIS_URL = "redis://localhost:6379/0"
    CACHE_URL = "redis://localhost:6379/1"
    
    # CORS Settings
    CORS_ALLOWED_ORIGINS = var.cors_allowed_origins
  }
  sensitive = true
}

# =============================================================================
# SECURITY REMINDERS
# =============================================================================

output "security_checklist" {
  description = "Lista de verificação de segurança"
  value = [
    "🔒 Alterar SSH access de 0.0.0.0/0 para IPs específicos",
    "🔐 Configurar chaves SSH sem senha ou com senha forte",
    "🛡️ Instalar fail2ban para proteção contra ataques",
    "📜 Configurar certificados SSL/TLS para HTTPS",
    "🚨 Configurar alertas de monitoramento de custos",
    "📊 Revisar logs de segurança regularmente",
    "🔄 Manter sistema atualizado (yum update)",
    "💾 Configurar backup automático dos dados importantes",
    "🔍 Monitorar uso de recursos para otimizar custos",
    "📧 Configurar notificações de alarmes CloudWatch"
  ]
}

# =============================================================================
# SCALING INFORMATION
# =============================================================================

output "scaling_options" {
  description = "Opções de escalabilidade futuras"
  value = {
    "📈 Upgrade Vertical" = {
      "t3.medium" = "$30.36/mês (2 vCPUs, 4GB RAM)"
      "t3.large"  = "$60.72/mês (2 vCPUs, 8GB RAM)"
    }
    "🔄 Load Balancer" = {
      "Application LB" = "+$16.20/mês"
      "Network LB"     = "+$16.20/mês"
    }
    "💾 Storage Upgrade" = {
      "EBS gp3 50GB"  = "+$3.00/mês"
      "EBS gp3 100GB" = "+$8.00/mês"
    }
    "🌐 CDN" = {
      "CloudFront" = "A partir de $1.00/mês"
    }
  }
}

# =============================================================================
# MONITORING URLS
# =============================================================================

output "monitoring_info" {
  description = "Informações de monitoramento"
  value = {
    "📊 CloudWatch Metrics" = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#metricsV2:graph=~();query=AWS/EC2;search=${aws_instance.app.id}"
    "💰 Cost Explorer"      = "https://console.aws.amazon.com/cost-management/home#/cost-explorer"
    "🖥️ EC2 Console"        = "https://console.aws.amazon.com/ec2/home?region=${var.aws_region}#Instances:search=${aws_instance.app.id}"
    "☁️ S3 Console"         = "https://console.aws.amazon.com/s3/buckets/lms-s3-backet"
  }
}

# =============================================================================
# DEPLOYMENT SUMMARY
# =============================================================================

output "deployment_summary" {
  description = "Resumo do deployment"
  value = {
    "🎯 Objetivo"           = "Deploy econômico ProEnglish - $40/mês"
    "⏰ Data do Deploy"     = timestamp()
    "🌍 Região"             = var.aws_region
    "🏷️ Projeto"            = var.project
    "🖥️ Tipo de Instância"  = var.instance_type
    "💾 Storage"            = "${var.root_volume_size}GB EBS gp3"
    "☁️ S3 Bucket"          = "lms-s3-backet"
    "🔐 SSH Key"            = aws_key_pair.main.key_name
    "🛡️ Security Group"     = aws_security_group.app.name
    "✅ Status"             = "Deployed Successfully"
    "💰 Custo Estimado"     = "~$22/mês (dentro do orçamento $40/mês)"
  }
}