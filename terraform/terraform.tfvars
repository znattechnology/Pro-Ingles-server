# =============================================================================
# TERRAFORM VARIABLES - PROENGLISH-BACKEND
# =============================================================================

project = "pro-english"
environment = "production"
aws_region = "eu-west-1"
cluster_name = "pro-english-eks"

# Database Configuration
neon_database_url = "postgresql://user:pass@host:5432/database"  # Substitua pelos valores reais
django_secret_key = "sua-django-secret-key-aqui"                  # Substitua por uma secret key real

# Application Configuration
allowed_hosts = "localhost,127.0.0.1,pro-english-alb-343566329.eu-west-1.elb.amazonaws.com"
app_replicas = 2

# Frontend Configuration - Domínios Vercel (URLs estáveis)
cors_allowed_origins = "http://localhost:3000,https://pro-ingles-client-nine.vercel.app,https://pro-ingles-client-git-main-znattechnology95-1655s-projects.vercel.app,https://proenglish.com,https://www.proenglish.com"
csrf_trusted_origins = "http://localhost:3000,https://pro-ingles-client-nine.vercel.app,https://pro-ingles-client-git-main-znattechnology95-1655s-projects.vercel.app,https://proenglish.com,https://www.proenglish.com"

# Tags
common_tags = {
  Project     = "ProEnglish-Backend"
  Environment = "production"
  ManagedBy   = "Terraform"
  Owner       = "DevOps-Team"
}