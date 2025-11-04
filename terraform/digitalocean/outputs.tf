# =============================================================================
# DIGITALOCEAN OUTPUTS - PROENGLISH PLATFORM
# =============================================================================

# =============================================================================
# DROPLET INFORMATION
# =============================================================================

output "droplet_id" {
  description = "ID do Droplet principal"
  value       = digitalocean_droplet.app.id
}

output "droplet_name" {
  description = "Nome do Droplet"
  value       = digitalocean_droplet.app.name
}

output "droplet_ipv4_address" {
  description = "Endereço IPv4 público do Droplet"
  value       = digitalocean_droplet.app.ipv4_address
}

output "droplet_ipv6_address" {
  description = "Endereço IPv6 público do Droplet"
  value       = digitalocean_droplet.app.ipv6_address
}

output "droplet_private_ipv4_address" {
  description = "Endereço IPv4 privado do Droplet"
  value       = digitalocean_droplet.app.ipv4_address_private
}

output "droplet_size" {
  description = "Tamanho do Droplet"
  value       = digitalocean_droplet.app.size
}

output "droplet_region" {
  description = "Região do Droplet"
  value       = digitalocean_droplet.app.region
}

output "droplet_vcpus" {
  description = "Número de vCPUs do Droplet"
  value       = digitalocean_droplet.app.vcpus
}

output "droplet_memory" {
  description = "Memória do Droplet (MB)"
  value       = digitalocean_droplet.app.memory
}

output "droplet_disk" {
  description = "Armazenamento do Droplet (GB)"
  value       = digitalocean_droplet.app.disk
}

# =============================================================================
# NETWORKING INFORMATION
# =============================================================================

output "firewall_id" {
  description = "ID do Cloud Firewall"
  value       = digitalocean_firewall.app.id
}

output "firewall_name" {
  description = "Nome do Cloud Firewall"
  value       = digitalocean_firewall.app.name
}

# =============================================================================
# DNS INFORMATION
# =============================================================================

output "api_domain" {
  description = "Domínio da API"
  value       = "api.${var.domain_name}"
}

output "api_url" {
  description = "URL completa da API"
  value       = "https://api.${var.domain_name}"
}

output "dns_records" {
  description = "Records DNS criados"
  value = {
    api_ipv4 = digitalocean_record.api.fqdn
    api_ipv6 = digitalocean_record.api_ipv6.fqdn
    www_ipv4 = var.create_www_record ? digitalocean_record.www[0].fqdn : null
  }
}

# =============================================================================
# STORAGE INFORMATION
# =============================================================================

output "spaces_bucket_name" {
  description = "Nome do bucket Spaces"
  value       = digitalocean_spaces_bucket.media.name
}

output "spaces_bucket_domain" {
  description = "Domínio do bucket Spaces"
  value       = digitalocean_spaces_bucket.media.bucket_domain_name
}

output "spaces_endpoint" {
  description = "Endpoint do Spaces"
  value       = "https://${var.spaces_region}.digitaloceanspaces.com"
}

output "spaces_cdn_endpoint" {
  description = "Endpoint CDN do Spaces"
  value       = digitalocean_spaces_bucket.media.bucket_domain_name
}

# =============================================================================
# PROJECT INFORMATION
# =============================================================================

output "project_id" {
  description = "ID do projeto DigitalOcean"
  value       = digitalocean_project.main.id
}

output "project_name" {
  description = "Nome do projeto"
  value       = digitalocean_project.main.name
}

# =============================================================================
# BACKUP INFORMATION
# =============================================================================

output "backup_enabled" {
  description = "Status dos backups"
  value       = var.enable_backups
}

output "backup_snapshot_id" {
  description = "ID do snapshot de backup"
  value       = var.enable_backups ? digitalocean_volume_snapshot.app_backup[0].id : null
}

# =============================================================================
# MONITORING INFORMATION
# =============================================================================

output "monitoring_alerts" {
  description = "Alertas de monitoramento configurados"
  value = {
    cpu_alert_id    = digitalocean_monitor_alert.high_cpu.id
    memory_alert_id = digitalocean_monitor_alert.high_memory.id
    disk_alert_id   = digitalocean_monitor_alert.disk_usage.id
  }
}

# =============================================================================
# COST INFORMATION
# =============================================================================

output "estimated_monthly_cost" {
  description = "Custo mensal estimado (USD)"
  value = {
    droplet         = var.droplet_size == "s-2vcpu-4gb" ? 32 : 0
    spaces          = 5
    backups         = var.enable_backups ? 6.40 : 0
    load_balancer   = var.enable_load_balancer ? 10 : 0
    total           = (var.droplet_size == "s-2vcpu-4gb" ? 32 : 0) + 5 + (var.enable_backups ? 6.40 : 0) + (var.enable_load_balancer ? 10 : 0)
  }
}

# =============================================================================
# CONNECTION INFORMATION
# =============================================================================

output "ssh_connection" {
  description = "Comando SSH para conectar ao Droplet"
  value       = "ssh root@${digitalocean_droplet.app.ipv4_address}"
  sensitive   = false
}

output "application_endpoints" {
  description = "Endpoints da aplicação"
  value = {
    api_health      = "https://api.${var.domain_name}/health/"
    api_admin       = "https://api.${var.domain_name}/admin/"
    api_docs        = "https://api.${var.domain_name}/api/docs/"
    media_storage   = "https://${digitalocean_spaces_bucket.media.bucket_domain_name}/"
  }
}

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

output "environment_variables" {
  description = "Variáveis de ambiente para configuração da aplicação"
  value = {
    # Server Information
    SERVER_IP           = digitalocean_droplet.app.ipv4_address
    SERVER_REGION       = digitalocean_droplet.app.region
    
    # Application URLs
    API_DOMAIN          = "api.${var.domain_name}"
    API_URL             = "https://api.${var.domain_name}"
    
    # Storage Configuration
    SPACES_BUCKET       = digitalocean_spaces_bucket.media.name
    SPACES_ENDPOINT     = "https://${var.spaces_region}.digitaloceanspaces.com"
    SPACES_CDN_ENDPOINT = digitalocean_spaces_bucket.media.bucket_domain_name
    SPACES_REGION       = var.spaces_region
    
    # Cache Configuration
    REDIS_URL           = "redis://localhost:6379/0"
    CACHE_URL           = "redis://localhost:6379/1"
    
    # Django Configuration
    DJANGO_ALLOWED_HOSTS = "${var.domain_name},api.${var.domain_name},www.${var.domain_name}"
    DJANGO_CORS_ORIGINS  = join(",", var.spaces_cors_origins)
  }
  sensitive = false
}

# =============================================================================
# DEPLOYMENT INFORMATION
# =============================================================================

output "deployment_info" {
  description = "Informações para deployment"
  value = {
    terraform_workspace = terraform.workspace
    deployment_time     = timestamp()
    droplet_urn         = digitalocean_droplet.app.urn
    spaces_urn          = digitalocean_spaces_bucket.media.urn
    project_urn         = digitalocean_project.main.urn
  }
}

# =============================================================================
# MONITORING URLS
# =============================================================================

output "monitoring_urls" {
  description = "URLs para monitoramento"
  value = {
    digitalocean_dashboard = "https://cloud.digitalocean.com/projects/${digitalocean_project.main.id}/resources"
    droplet_graphs         = "https://cloud.digitalocean.com/droplets/${digitalocean_droplet.app.id}/graphs"
    spaces_usage           = "https://cloud.digitalocean.com/spaces/${digitalocean_spaces_bucket.media.name}?bucket=${digitalocean_spaces_bucket.media.name}&region=${var.spaces_region}"
  }
}