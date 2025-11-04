# =============================================================================
# DIGITALOCEAN VARIABLES - PROENGLISH PLATFORM
# =============================================================================

# =============================================================================
# PROVIDER CONFIGURATION
# =============================================================================

variable "do_token" {
  description = "DigitalOcean API Token"
  type        = string
  sensitive   = true
}

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

variable "region" {
  description = "Região do DigitalOcean para Droplets"
  type        = string
  default     = "fra1"  # Frankfurt - Próximo à Europa/África
  
  validation {
    condition = contains([
      "nyc1", "nyc3", "ams3", "fra1", "lon1", 
      "sgp1", "tor1", "blr1", "sfo2", "sfo3"
    ], var.region)
    error_message = "Region must be a valid DigitalOcean region."
  }
}

variable "spaces_region" {
  description = "Região do DigitalOcean Spaces"
  type        = string
  default     = "fra1"
}

# =============================================================================
# DROPLET CONFIGURATION
# =============================================================================

variable "droplet_image" {
  description = "Imagem do sistema operacional"
  type        = string
  default     = "ubuntu-22-04-x64"
}

variable "droplet_size" {
  description = "Tamanho do Droplet"
  type        = string
  default     = "s-2vcpu-4gb"  # $32/mês - 2 vCPUs, 4GB RAM, 120GB SSD
  
  validation {
    condition = contains([
      "s-1vcpu-512mb-10gb",    # $4/mês - Basic
      "s-1vcpu-1gb",           # $8/mês - Basic
      "s-1vcpu-2gb",           # $16/mês - Basic  
      "s-2vcpu-4gb",           # $32/mês - Basic (ESCOLHIDO)
      "s-4vcpu-8gb",           # $63/mês - General Purpose
      "c-2",                   # $42/mês - CPU-Optimized
      "m-2vcpu-16gb"           # $84/mês - Memory-Optimized
    ], var.droplet_size)
    error_message = "Droplet size must be a valid DigitalOcean size slug."
  }
}

# =============================================================================
# NETWORK & SECURITY CONFIGURATION
# =============================================================================

variable "domain_name" {
  description = "Nome do domínio principal"
  type        = string
  default     = "proenglish.ao"
}

variable "create_www_record" {
  description = "Criar record DNS para www"
  type        = bool
  default     = true
}

variable "allowed_ssh_ips" {
  description = "IPs permitidos para acesso SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # ALTERAR para IPs específicos em produção
}

variable "ssh_public_key_path" {
  description = "Caminho para a chave SSH pública"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

variable "app_environment_vars" {
  description = "Variáveis de ambiente da aplicação"
  type        = map(string)
  default = {
    DJANGO_SETTINGS_MODULE = "core.settings.production"
    DJANGO_DEBUG          = "False"
    DJANGO_SECRET_KEY     = ""  # Será definido via terraform.tfvars
    DATABASE_URL          = ""  # Neon PostgreSQL URL
    REDIS_URL            = "redis://localhost:6379/0"
    CACHE_URL            = "redis://localhost:6379/1"
  }
  sensitive = true
}

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

variable "enable_spaces_cdn" {
  description = "Habilitar CDN para Spaces"
  type        = bool
  default     = true
}

variable "spaces_cors_origins" {
  description = "Origens permitidas para CORS no Spaces"
  type        = list(string)
  default = [
    "https://proenglish.ao",
    "https://www.proenglish.ao",
    "https://admin.proenglish.ao"
  ]
}

# =============================================================================
# BACKUP CONFIGURATION
# =============================================================================

variable "enable_backups" {
  description = "Habilitar backups automáticos (custo adicional: $6.40/mês)"
  type        = bool
  default     = false  # Pode ser habilitado depois
}

variable "backup_retention_days" {
  description = "Dias de retenção dos backups"
  type        = number
  default     = 30
}

# =============================================================================
# MONITORING & ALERTING
# =============================================================================

variable "alert_email" {
  description = "Email para receber alertas de monitoramento"
  type        = string
  default     = "admin@proenglish.ao"
}

variable "enable_monitoring_alerts" {
  description = "Habilitar alertas de monitoramento"
  type        = bool
  default     = true
}

# CPU alert threshold (percentage)
variable "cpu_alert_threshold" {
  description = "Threshold de CPU para alerta (%)"
  type        = number
  default     = 80
  
  validation {
    condition     = var.cpu_alert_threshold >= 0 && var.cpu_alert_threshold <= 100
    error_message = "CPU alert threshold must be between 0 and 100."
  }
}

# Memory alert threshold (percentage)
variable "memory_alert_threshold" {
  description = "Threshold de memória para alerta (%)"
  type        = number
  default     = 85
  
  validation {
    condition     = var.memory_alert_threshold >= 0 && var.memory_alert_threshold <= 100
    error_message = "Memory alert threshold must be between 0 and 100."
  }
}

# Disk alert threshold (percentage)
variable "disk_alert_threshold" {
  description = "Threshold de disco para alerta (%)"
  type        = number
  default     = 90
  
  validation {
    condition     = var.disk_alert_threshold >= 0 && var.disk_alert_threshold <= 100
    error_message = "Disk alert threshold must be between 0 and 100."
  }
}

# =============================================================================
# DATABASE CONFIGURATION (NEON)
# =============================================================================

variable "neon_database_url" {
  description = "URL de conexão do PostgreSQL Neon"
  type        = string
  sensitive   = true
}

variable "neon_project_name" {
  description = "Nome do projeto no Neon"
  type        = string
  default     = "proenglish-backend"
}

# =============================================================================
# TAGS CONFIGURATION
# =============================================================================

variable "common_tags" {
  description = "Tags comuns para todos os recursos"
  type        = list(string)
  default = [
    "project:proenglish",
    "managed-by:terraform",
    "cost-center:infrastructure"
  ]
}

# =============================================================================
# SCALING CONFIGURATION
# =============================================================================

variable "enable_load_balancer" {
  description = "Habilitar Load Balancer (para scaling futuro)"
  type        = bool
  default     = false  # Não necessário inicialmente
}

variable "enable_auto_scaling" {
  description = "Habilitar auto scaling (futuro)"
  type        = bool
  default     = false
}

# =============================================================================
# COST OPTIMIZATION
# =============================================================================

variable "cost_alert_threshold" {
  description = "Threshold de custo mensal para alerta (USD)"
  type        = number
  default     = 45  # $5 acima do orçamento de $40
}

variable "enable_cost_alerts" {
  description = "Habilitar alertas de custo"
  type        = bool
  default     = true
}