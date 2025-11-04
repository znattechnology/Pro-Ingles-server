# =============================================================================
# AWS BASIC VARIABLES - PROENGLISH PLATFORM
# Budget: $40/month
# =============================================================================

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "proenglish"
}

variable "environment" {
  description = "Ambiente (staging, production)"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["staging", "production", "development"], var.environment)
    error_message = "Environment must be staging, production, or development."
  }
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"  # Região mais barata
  
  validation {
    condition = contains([
      "us-east-1", "us-west-2", "eu-west-1", 
      "ap-southeast-1", "sa-east-1"
    ], var.aws_region)
    error_message = "AWS region must be a valid region."
  }
}

# =============================================================================
# EC2 CONFIGURATION
# =============================================================================

variable "instance_type" {
  description = "Tipo de instância EC2"
  type        = string
  default     = "t3.small"  # ~$15/mês - 2 vCPUs, 2GB RAM
  
  validation {
    condition = contains([
      "t3.micro",   # Free tier - 1 vCPU, 1GB RAM
      "t3.small",   # $15/mês - 2 vCPUs, 2GB RAM
      "t3.medium",  # $30/mês - 2 vCPUs, 4GB RAM
      "t2.micro"    # Free tier - 1 vCPU, 1GB RAM
    ], var.instance_type)
    error_message = "Instance type must be a valid EC2 instance type for budget."
  }
}

variable "root_volume_size" {
  description = "Tamanho do volume raiz em GB"
  type        = number
  default     = 20  # 20GB é suficiente para aplicação básica
  
  validation {
    condition     = var.root_volume_size >= 8 && var.root_volume_size <= 50
    error_message = "Root volume size must be between 8 and 50 GB."
  }
}

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

variable "ssh_public_key_path" {
  description = "Caminho para a chave SSH pública"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "allowed_ssh_ips" {
  description = "IPs permitidos para acesso SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # ALTERAR para IPs específicos
}

# =============================================================================
# DOMAIN CONFIGURATION
# =============================================================================

variable "domain_name" {
  description = "Nome do domínio principal"
  type        = string
  default     = "proenglish.ao"
}

variable "create_hosted_zone" {
  description = "Criar hosted zone no Route 53 ($0.50/mês)"
  type        = bool
  default     = false  # Para economizar, usar DNS externo
}

variable "create_www_record" {
  description = "Criar record DNS para www"
  type        = bool
  default     = true
}

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

variable "neon_database_url" {
  description = "URL de conexão do PostgreSQL Neon"
  type        = string
  sensitive   = true
}

variable "django_secret_key" {
  description = "Django Secret Key"
  type        = string
  sensitive   = true
}

variable "django_debug" {
  description = "Django Debug mode"
  type        = string
  default     = "False"
}

variable "allowed_hosts" {
  description = "Django allowed hosts"
  type        = string
  default     = "*"
}

variable "cors_allowed_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default = [
    "https://proenglish.ao",
    "https://www.proenglish.ao",
    "http://localhost:3000"
  ]
}

# =============================================================================
# COST OPTIMIZATION
# =============================================================================

variable "use_elastic_ip" {
  description = "Usar Elastic IP ($3.65/mês) - Recomendado para produção"
  type        = bool
  default     = false  # Para economizar, usar IP público dinâmico
}

variable "enable_detailed_monitoring" {
  description = "Habilitar monitoramento detalhado ($2.10/mês)"
  type        = bool
  default     = false  # Usar monitoramento básico gratuito
}

variable "backup_retention_days" {
  description = "Dias de retenção de backup"
  type        = number
  default     = 7
}

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================

variable "sns_topic_arn" {
  description = "ARN do tópico SNS para alertas (opcional)"
  type        = string
  default     = ""
}

variable "cpu_alarm_threshold" {
  description = "Threshold de CPU para alerta (%)"
  type        = number
  default     = 80
  
  validation {
    condition     = var.cpu_alarm_threshold >= 0 && var.cpu_alarm_threshold <= 100
    error_message = "CPU alarm threshold must be between 0 and 100."
  }
}

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

variable "s3_lifecycle_enabled" {
  description = "Habilitar lifecycle policy no S3 para economia"
  type        = bool
  default     = true
}

variable "s3_ia_transition_days" {
  description = "Dias para transição para IA (Infrequent Access)"
  type        = number
  default     = 30
}

variable "s3_glacier_transition_days" {
  description = "Dias para transição para Glacier"
  type        = number
  default     = 90
}

# =============================================================================
# TAGS CONFIGURATION
# =============================================================================

variable "common_tags" {
  description = "Tags comuns para todos os recursos"
  type        = map(string)
  default = {
    Project     = "ProEnglish-Backend"
    Environment = "production"
    ManagedBy   = "Terraform"
    Owner       = "DevOps-Team"
    CostCenter  = "Infrastructure"
    Budget      = "40USD-Monthly"
  }
}

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

variable "admin_email" {
  description = "Email do administrador para alertas"
  type        = string
  default     = "admin@proenglish.ao"
}

# =============================================================================
# FEATURE FLAGS
# =============================================================================

variable "enable_cloudwatch_logs" {
  description = "Habilitar CloudWatch Logs (pode gerar custos)"
  type        = bool
  default     = false  # Para economizar
}

variable "enable_ssl_certificate" {
  description = "Habilitar certificado SSL via ACM"
  type        = bool
  default     = true  # ACM é gratuito
}

variable "enable_auto_backup" {
  description = "Habilitar backup automático (EBS snapshots)"
  type        = bool
  default     = false  # Para economizar inicialmente
}