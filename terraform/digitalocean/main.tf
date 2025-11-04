# =============================================================================
# DIGITALOCEAN INFRASTRUCTURE - PROENGLISH PLATFORM
# Budget: $40/month | Custo total: $37/month
# =============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# Configure DigitalOcean Provider
provider "digitalocean" {
  token = var.do_token
}

# =============================================================================
# SSH KEY PARA ACESSO AOS DROPLETS
# =============================================================================

resource "digitalocean_ssh_key" "main" {
  name       = "${var.project_name}-key"
  public_key = file(var.ssh_public_key_path)
}

# =============================================================================
# DROPLET PRINCIPAL - APLICAÇÃO
# Especificações: 2 vCPUs, 4GB RAM, 120GB NVMe SSD
# Custo: $32/mês
# =============================================================================

resource "digitalocean_droplet" "app" {
  image  = var.droplet_image
  name   = "${var.project_name}-app"
  region = var.region
  size   = var.droplet_size
  
  ssh_keys = [digitalocean_ssh_key.main.id]
  
  # User data for initial setup
  user_data = templatefile("${path.module}/user_data.sh", {
    domain_name = var.domain_name
    app_name    = var.project_name
  })
  
  # Monitoring enabled (free)
  monitoring = true
  
  # IPv6 enabled
  ipv6 = true
  
  tags = [
    "environment:${var.environment}",
    "project:${var.project_name}",
    "type:application",
    "managed-by:terraform"
  ]
}

# =============================================================================
# CLOUD FIREWALL - SEGURANÇA DE REDE
# Custo: $0 (gratuito)
# =============================================================================

resource "digitalocean_firewall" "app" {
  name = "${var.project_name}-firewall"

  droplet_ids = [digitalocean_droplet.app.id]

  # Inbound rules
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.allowed_ssh_ips
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Outbound rules
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "53"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  tags = [
    "environment:${var.environment}",
    "project:${var.project_name}",
    "managed-by:terraform"
  ]
}

# =============================================================================
# SPACES - OBJECT STORAGE (S3-compatible)
# Especificações: 250GB storage + 1TB CDN transfer
# Custo: $5/mês
# =============================================================================

resource "digitalocean_spaces_bucket" "media" {
  name   = "${var.project_name}-media"
  region = var.spaces_region
  
  # Public read access for media files
  acl = "public-read"
  
  # CORS configuration for frontend access
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "POST", "PUT", "DELETE"]
    allowed_origins = [
      "https://${var.domain_name}",
      "https://www.${var.domain_name}",
      "https://admin.${var.domain_name}"
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }

  # Lifecycle rule for old files
  lifecycle_rule {
    id      = "delete_old_uploads"
    enabled = true

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      days = 30
    }
  }
}

# =============================================================================
# DOMAIN E DNS RECORDS
# =============================================================================

# Domain (assumindo que já existe)
data "digitalocean_domain" "main" {
  name = var.domain_name
}

# A record para API
resource "digitalocean_record" "api" {
  domain = data.digitalocean_domain.main.name
  type   = "A"
  name   = "api"
  value  = digitalocean_droplet.app.ipv4_address
  ttl    = 300
}

# A record para www (se necessário)
resource "digitalocean_record" "www" {
  count  = var.create_www_record ? 1 : 0
  domain = data.digitalocean_domain.main.name
  type   = "A"
  name   = "www"
  value  = digitalocean_droplet.app.ipv4_address
  ttl    = 300
}

# AAAA record para IPv6
resource "digitalocean_record" "api_ipv6" {
  domain = data.digitalocean_domain.main.name
  type   = "AAAA"
  name   = "api"
  value  = digitalocean_droplet.app.ipv6_address
  ttl    = 300
}

# =============================================================================
# BACKUP SNAPSHOT (OPCIONAL)
# Custo: $6.40/mês (20% do droplet)
# =============================================================================

resource "digitalocean_volume_snapshot" "app_backup" {
  count = var.enable_backups ? 1 : 0
  
  name      = "${var.project_name}-app-backup-${formatdate("YYYY-MM-DD", timestamp())}"
  volume_id = digitalocean_droplet.app.id
  
  tags = [
    "environment:${var.environment}",
    "project:${var.project_name}",
    "type:backup",
    "managed-by:terraform"
  ]
}

# =============================================================================
# MONITORING ALERTS (GRATUITO)
# =============================================================================

resource "digitalocean_monitor_alert" "high_cpu" {
  alerts {
    email = [var.alert_email]
  }
  
  window      = "5m"
  type        = "v1/insights/droplet/cpu"
  compare     = "GreaterThan"
  value       = 80
  enabled     = true
  entities    = [digitalocean_droplet.app.id]
  description = "High CPU usage alert for ${var.project_name}"
  
  tags = [
    "environment:${var.environment}",
    "project:${var.project_name}",
    "managed-by:terraform"
  ]
}

resource "digitalocean_monitor_alert" "high_memory" {
  alerts {
    email = [var.alert_email]
  }
  
  window      = "5m"
  type        = "v1/insights/droplet/memory_utilization_percent"
  compare     = "GreaterThan"
  value       = 85
  enabled     = true
  entities    = [digitalocean_droplet.app.id]
  description = "High memory usage alert for ${var.project_name}"
  
  tags = [
    "environment:${var.environment}",
    "project:${var.project_name}",
    "managed-by:terraform"
  ]
}

resource "digitalocean_monitor_alert" "disk_usage" {
  alerts {
    email = [var.alert_email]
  }
  
  window      = "5m"
  type        = "v1/insights/droplet/disk_utilization_percent"
  compare     = "GreaterThan"
  value       = 90
  enabled     = true
  entities    = [digitalocean_droplet.app.id]
  description = "High disk usage alert for ${var.project_name}"
  
  tags = [
    "environment:${var.environment}",
    "project:${var.project_name}",
    "managed-by:terraform"
  ]
}

# =============================================================================
# PROJECT ORGANIZATION
# =============================================================================

resource "digitalocean_project" "main" {
  name        = var.project_name
  description = "ProEnglish Platform Infrastructure"
  purpose     = "Web Application"
  environment = title(var.environment)
  
  resources = [
    digitalocean_droplet.app.urn,
    digitalocean_spaces_bucket.media.urn,
    digitalocean_domain.main.urn
  ]
}