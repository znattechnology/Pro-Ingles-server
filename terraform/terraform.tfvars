# AWS BASIC TERRAFORM VARIABLES - PROENGLISH PLATFORM
# Budget: $40/month | Configurações atuais aplicadas
# =============================================================================

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================

project     = "pro-english"
environment = "production"
aws_region  = "eu-west-1"  # Mantendo região original

# =============================================================================
# EC2 CONFIGURATION
# =============================================================================

instance_type = "t3.small"  # $15.18/mês - 2 vCPUs, 2GB RAM
root_volume_size = 20        # 20GB suficiente

# =============================================================================
# SSH CONFIGURATION
# =============================================================================

ssh_public_key_path = "~/.ssh/id_rsa.pub"

# =============================================================================
# DATABASE CONFIGURATION (NEON POSTGRESQL) - CONFIGURAÇÕES EXISTENTES
# =============================================================================

neon_database_url = "postgresql://neondb_owner:npg_0Xo1HNrcObmp@ep-divine-dew-agc1ldk8-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# =============================================================================
# DJANGO CONFIGURATION - USANDO CONFIGURAÇÕES ATUAIS
# =============================================================================

django_secret_key = "django-insecure-#d5&bor1y4=^@y$tln91_5jzv7q*q@v4p%l+bh8z@16i4+*hpx"
django_debug      = "False"
allowed_hosts     = "*"

cors_allowed_origins = "http://localhost:3000,http://127.0.0.1:3000,https://proenglish.ao,https://pro-ingles-client-nine.vercel.app,https://pro-ingles-client-git-main-znattechnology95-1655s-projects.vercel.app,https://proenglish.com,https://www.proenglish.com"
csrf_trusted_origins = "http://localhost:3000,http://127.0.0.1:3000,https://proenglish.ao,https://pro-ingles-client-nine.vercel.app,https://pro-ingles-client-git-main-znattechnology95-1655s-projects.vercel.app,https://proenglish.com,https://www.proenglish.com"

# =============================================================================
# COST OPTIMIZATION SETTINGS
# =============================================================================

use_elastic_ip = false              # Para economizar
enable_detailed_monitoring = false # Para economizar

# =============================================================================
# TAGS CONFIGURATION
# =============================================================================

common_tags = {
  Project     = "ProEnglish-Backend"
  Environment = "production"
  ManagedBy   = "Terraform"
  Owner       = "DevOps-Team"
  CostCenter  = "Infrastructure"
  Budget      = "40USD-Monthly"
}

# =============================================================================
# NOTES
# =============================================================================

# ✅ Configurações importadas do .env existente:
# - Database Neon: Conectado e funcionando
# - Django Secret: Usando chave atual
# - CORS Origins: Frontend configurado
# - AWS Region: eu-west-1 (original)
# 
# 💰 Custo estimado: ~$22/mês
# 🎯 Orçamento: $40/mês
# ✅ Margem: $18/mês
