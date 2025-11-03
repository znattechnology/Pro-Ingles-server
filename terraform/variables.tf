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

variable "cluster_name" {
  description = "Nome do cluster EKS"
  type        = string
  default     = "pro-english-eks"
}

variable "cluster_version" {
  description = "Versão do Kubernetes"
  type        = string
  default     = "1.31"
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
  default     = "t3.small"
}

variable "min_size" {
  description = "Capacidade mínima do Auto Scaling Group"
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Capacidade máxima do Auto Scaling Group"
  type        = number
  default     = 3
}

variable "desired_capacity" {
  description = "Capacidade desejada do Auto Scaling Group"
  type        = number
  default     = 1
}

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

variable "app_image_tag" {
  description = "Tag da imagem Docker"
  type        = string
  default     = "latest"
}

variable "app_replicas" {
  description = "Número de réplicas da aplicação"
  type        = number
  default     = 2
}

variable "app_cpu_request" {
  description = "CPU request para containers"
  type        = string
  default     = "100m"
}

variable "app_cpu_limit" {
  description = "CPU limit para containers"
  type        = string
  default     = "500m"
}

variable "app_memory_request" {
  description = "Memory request para containers"
  type        = string
  default     = "256Mi"
}

variable "app_memory_limit" {
  description = "Memory limit para containers"
  type        = string
  default     = "1Gi"
}

# =============================================================================
# MONITORING & LOGGING
# =============================================================================

variable "enable_logging" {
  description = "Habilitar CloudWatch logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Dias de retenção dos logs"
  type        = number
  default     = 30
}

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