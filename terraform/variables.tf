# =============================================================================
# TERRAFORM VARIABLES - PROENGLISH-BACKEND
# =============================================================================

variable "project" {
  description = "Nome do projeto"
  type        = string
  default     = "pro-english"
}

variable "environment" {
  description = "Ambiente (staging, production)"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "eu-west-1"
}

# =============================================================================
# SSH & SECURITY CONFIGURATION
# =============================================================================

variable "ssh_public_key_path" {
  description = "Caminho para a chave SSH pública"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

# =============================================================================
# COST OPTIMIZATION VARIABLES
# =============================================================================

variable "root_volume_size" {
  description = "Tamanho do volume raiz em GB"
  type        = number
  default     = 20  # 20GB suficiente para aplicação básica
  
  validation {
    condition     = var.root_volume_size >= 8 && var.root_volume_size <= 50
    error_message = "Root volume size must be between 8 and 50 GB for budget."
  }
}

variable "use_elastic_ip" {
  description = "Usar Elastic IP (+$3.65/mês) - Para produção"
  type        = bool
  default     = false  # Para economizar, usar IP dinâmico
}

variable "enable_detailed_monitoring" {
  description = "Habilitar monitoramento detalhado (+$2.10/mês)"
  type        = bool
  default     = false  # Usar monitoramento básico gratuito
}

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block para VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Zonas de disponibilidade"
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
}

variable "public_subnets" {
  description = "Subnets públicas"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnets" {
  description = "Subnets privadas"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
}

# =============================================================================
# EC2 AUTO SCALING CONFIGURATION
# =============================================================================

variable "instance_type" {
  description = "Tipo de instância EC2"
  type        = string
  default     = "t3.small"  # ~$15/mês - 2 vCPUs, 2GB RAM
  
  validation {
    condition = contains([
      "t3.micro",   # Free tier ou $8/mês
      "t3.small",   # $15/mês - ESCOLHIDO
      "t3.medium"   # $30/mês
    ], var.instance_type)
    error_message = "Instance type must be t3.micro, t3.small, or t3.medium for budget."
  }
}

# Removido: Auto Scaling não necessário para configuração básica

# =============================================================================
# DATABASE CONFIGURATION (NEON)
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
  description = "CORS allowed origins for frontend"
  type        = string
  default     = "https://localhost:3000"
}

variable "csrf_trusted_origins" {
  description = "CSRF trusted origins for frontend"
  type        = string
  default     = "https://localhost:3000"
}

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Removido: Configurações de containers não necessárias para configuração básica

# =============================================================================
# MONITORING & LOGGING
# =============================================================================

# Removido: CloudWatch logging pode gerar custos extras

# =============================================================================
# TAGS
# =============================================================================

variable "common_tags" {
  description = "Tags comuns para todos os recursos"
  type        = map(string)
  default = {
    Project     = "ProEnglish-Backend"
    Environment = "production"
    ManagedBy   = "Terraform"
    Owner       = "DevOps-Team"
  }
}