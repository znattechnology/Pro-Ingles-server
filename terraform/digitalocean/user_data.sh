#!/bin/bash

# =============================================================================
# DIGITALOCEAN DROPLET USER DATA - PROENGLISH PLATFORM
# Setup inicial automático do servidor
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# =============================================================================
# SYSTEM INITIALIZATION
# =============================================================================

log "Starting ProEnglish Platform setup..."
log "Domain: ${domain_name}"
log "App Name: ${app_name}"

# Update system packages
log "Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install essential packages
log "Installing essential packages..."
apt-get install -y \
    curl \
    wget \
    unzip \
    git \
    htop \
    nano \
    vim \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    logrotate \
    cron

# =============================================================================
# DOCKER INSTALLATION
# =============================================================================

log "Installing Docker..."

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group (if exists)
if id "ubuntu" &>/dev/null; then
    usermod -aG docker ubuntu
fi

log "Docker installed successfully"

# =============================================================================
# DOCKER COMPOSE INSTALLATION
# =============================================================================

log "Installing Docker Compose..."

# Download and install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create symlink for easier access
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

log "Docker Compose installed successfully"

# =============================================================================
# NGINX INSTALLATION
# =============================================================================

log "Installing Nginx..."
apt-get install -y nginx

# Start and enable Nginx
systemctl start nginx
systemctl enable nginx

log "Nginx installed successfully"

# =============================================================================
# CERTBOT INSTALLATION (SSL)
# =============================================================================

log "Installing Certbot for SSL certificates..."

# Install snapd (if not already installed)
apt-get install -y snapd

# Install certbot via snap
snap install core; snap refresh core
snap install --classic certbot

# Create symlink
ln -sf /snap/bin/certbot /usr/bin/certbot

log "Certbot installed successfully"

# =============================================================================
# REDIS INSTALLATION
# =============================================================================

log "Installing Redis..."
apt-get install -y redis-server

# Configure Redis
sed -i 's/^supervised no/supervised systemd/' /etc/redis/redis.conf
sed -i 's/^# maxmemory <bytes>/maxmemory 512mb/' /etc/redis/redis.conf
sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

# Start and enable Redis
systemctl restart redis-server
systemctl enable redis-server

log "Redis installed and configured successfully"

# =============================================================================
# FIREWALL CONFIGURATION
# =============================================================================

log "Configuring UFW firewall..."

# Reset UFW to defaults
ufw --force reset

# Set default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (port 22)
ufw allow ssh

# Allow HTTP (port 80)
ufw allow http

# Allow HTTPS (port 443)
ufw allow https

# Enable UFW
ufw --force enable

log "UFW firewall configured successfully"

# =============================================================================
# FAIL2BAN CONFIGURATION
# =============================================================================

log "Configuring Fail2Ban..."

# Create local jail configuration
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd
destemail = admin@${domain_name}
sendername = Fail2Ban-ProEnglish
sender = fail2ban@${domain_name}

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-noscript]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 6

[nginx-badbots]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 2

[nginx-noproxy]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 2
EOF

# Restart and enable Fail2Ban
systemctl restart fail2ban
systemctl enable fail2ban

log "Fail2Ban configured successfully"

# =============================================================================
# CREATE APPLICATION DIRECTORIES
# =============================================================================

log "Creating application directories..."

# Create app directory structure
mkdir -p /opt/${app_name}
mkdir -p /opt/${app_name}/app
mkdir -p /opt/${app_name}/nginx
mkdir -p /opt/${app_name}/ssl
mkdir -p /opt/${app_name}/logs
mkdir -p /opt/${app_name}/backups
mkdir -p /opt/${app_name}/scripts

# Set permissions
chown -R root:root /opt/${app_name}
chmod -R 755 /opt/${app_name}

log "Application directories created successfully"

# =============================================================================
# CREATE DOCKER COMPOSE CONFIGURATION
# =============================================================================

log "Creating Docker Compose configuration..."

cat > /opt/${app_name}/docker-compose.yml << 'EOF'
version: '3.8'

services:
  backend:
    image: ${app_name}/backend:latest
    container_name: ${app_name}_backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=$${DATABASE_URL}
      - DJANGO_SECRET_KEY=$${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=False
      - DJANGO_ALLOWED_HOSTS=${domain_name},api.${domain_name},www.${domain_name}
      - REDIS_URL=redis://redis:6379/0
      - CACHE_URL=redis://redis:6379/1
      - SPACES_BUCKET=${app_name}-media
      - SPACES_ENDPOINT=https://fra1.digitaloceanspaces.com
      - SPACES_REGION=fra1
    volumes:
      - ./logs:/app/logs
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - redis
    networks:
      - app_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: ${app_name}_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - app_network
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

  nginx:
    image: nginx:alpine
    container_name: ${app_name}_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./ssl:/etc/ssl/certs:ro
      - static_volume:/var/www/static:ro
      - media_volume:/var/www/media:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - backend
    networks:
      - app_network

volumes:
  redis_data:
  static_volume:
  media_volume:

networks:
  app_network:
    driver: bridge
EOF

log "Docker Compose configuration created successfully"

# =============================================================================
# CREATE NGINX CONFIGURATION
# =============================================================================

log "Creating Nginx configuration..."

mkdir -p /opt/${app_name}/nginx/conf.d

# Main nginx.conf
cat > /opt/${app_name}/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log notice;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # Basic Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # Gzip Settings
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

    # Include server configurations
    include /etc/nginx/conf.d/*.conf;
}
EOF

# Server configuration
cat > /opt/${app_name}/nginx/conf.d/app.conf << EOF
upstream backend {
    server backend:8000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name ${domain_name} www.${domain_name} api.${domain_name};
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# Main API server
server {
    listen 443 ssl http2;
    server_name api.${domain_name};
    
    # SSL Configuration (will be updated after certificate generation)
    ssl_certificate /etc/ssl/certs/api.${domain_name}.pem;
    ssl_certificate_key /etc/ssl/certs/api.${domain_name}.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # File upload limit
    client_max_body_size 100M;
    
    # Rate limiting
    limit_req zone=api burst=20 nodelay;
    
    # API endpoints
    location / {
        proxy_pass http://backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Admin with additional rate limiting
    location /admin/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Static files
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /var/www/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Health check
    location /health/ {
        proxy_pass http://backend;
        access_log off;
    }
}
EOF

log "Nginx configuration created successfully"

# =============================================================================
# CREATE ENVIRONMENT FILE TEMPLATE
# =============================================================================

log "Creating environment file template..."

cat > /opt/${app_name}/.env.template << 'EOF'
# =============================================================================
# PROENGLISH PLATFORM - ENVIRONMENT VARIABLES
# =============================================================================

# Database Configuration (Neon PostgreSQL)
DATABASE_URL=postgresql://username:password@host:5432/database

# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${domain_name},api.${domain_name},www.${domain_name}

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://${domain_name},https://www.${domain_name}
CSRF_TRUSTED_ORIGINS=https://${domain_name},https://www.${domain_name}

# Redis Configuration
REDIS_URL=redis://redis:6379/0
CACHE_URL=redis://redis:6379/1

# DigitalOcean Spaces Configuration
SPACES_ACCESS_KEY_ID=your-spaces-access-key
SPACES_SECRET_ACCESS_KEY=your-spaces-secret-key
SPACES_BUCKET=${app_name}-media
SPACES_ENDPOINT=https://fra1.digitaloceanspaces.com
SPACES_REGION=fra1

# Email Configuration (optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn-here
EOF

log "Environment file template created successfully"

# =============================================================================
# CREATE MANAGEMENT SCRIPTS
# =============================================================================

log "Creating management scripts..."

# Deployment script
cat > /opt/${app_name}/scripts/deploy.sh << 'EOF'
#!/bin/bash

set -e

APP_NAME="${app_name}"
APP_DIR="/opt/$APP_NAME"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting deployment for $APP_NAME..."

cd $APP_DIR

# Pull latest images
log "Pulling latest Docker images..."
docker-compose pull

# Stop services
log "Stopping services..."
docker-compose down

# Start services
log "Starting services..."
docker-compose up -d

# Wait for services to be ready
log "Waiting for services to be ready..."
sleep 30

# Run migrations (if needed)
log "Running database migrations..."
docker-compose exec -T backend python manage.py migrate --noinput

# Collect static files
log "Collecting static files..."
docker-compose exec -T backend python manage.py collectstatic --noinput

# Check service health
log "Checking service health..."
docker-compose exec -T backend python manage.py check

log "Deployment completed successfully!"
EOF

# Backup script
cat > /opt/${app_name}/scripts/backup.sh << 'EOF'
#!/bin/bash

set -e

APP_NAME="${app_name}"
APP_DIR="/opt/$APP_NAME"
BACKUP_DIR="$APP_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting backup process..."

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application data
log "Creating application backup..."
tar -czf "$BACKUP_DIR/app_backup_$DATE.tar.gz" \
    -C $APP_DIR \
    --exclude=backups \
    --exclude=logs \
    .

# Keep only last 7 backups
log "Cleaning old backups..."
find $BACKUP_DIR -name "app_backup_*.tar.gz" -type f -mtime +7 -delete

log "Backup completed: app_backup_$DATE.tar.gz"
EOF

# Monitoring script
cat > /opt/${app_name}/scripts/monitor.sh << 'EOF'
#!/bin/bash

APP_NAME="${app_name}"
APP_DIR="/opt/$APP_NAME"

check_service() {
    local service=$1
    if docker-compose -f $APP_DIR/docker-compose.yml ps | grep -q "$service.*Up"; then
        echo "✓ $service is running"
        return 0
    else
        echo "✗ $service is not running"
        return 1
    fi
}

echo "=== ProEnglish Platform Status ==="
echo "Timestamp: $(date)"
echo

cd $APP_DIR

# Check Docker services
echo "Docker Services:"
check_service backend
check_service redis
check_service nginx
echo

# Check system resources
echo "System Resources:"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"
echo

# Check application health
echo "Application Health:"
if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✓ Application is responding"
else
    echo "✗ Application is not responding"
fi

echo "=== End Status Report ==="
EOF

# Make scripts executable
chmod +x /opt/${app_name}/scripts/*.sh

log "Management scripts created successfully"

# =============================================================================
# CREATE SYSTEMD SERVICE (OPTIONAL)
# =============================================================================

log "Creating systemd service for automatic startup..."

cat > /etc/systemd/system/${app_name}.service << EOF
[Unit]
Description=ProEnglish Platform
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/${app_name}
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl daemon-reload
systemctl enable ${app_name}.service

log "Systemd service created and enabled"

# =============================================================================
# CREATE LOGROTATE CONFIGURATION
# =============================================================================

log "Configuring log rotation..."

cat > /etc/logrotate.d/${app_name} << EOF
/opt/${app_name}/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/${app_name}/docker-compose.yml restart nginx
    endscript
}
EOF

log "Log rotation configured successfully"

# =============================================================================
# SETUP CRON JOBS
# =============================================================================

log "Setting up cron jobs..."

# Add cron jobs
(crontab -l 2>/dev/null; echo "# ProEnglish Platform automated tasks") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/${app_name}/scripts/backup.sh >> /opt/${app_name}/logs/backup.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/${app_name}/scripts/monitor.sh >> /opt/${app_name}/logs/monitor.log 2>&1") | crontab -

log "Cron jobs configured successfully"

# =============================================================================
# FINAL SETUP STEPS
# =============================================================================

log "Performing final setup steps..."

# Create log files
touch /opt/${app_name}/logs/backup.log
touch /opt/${app_name}/logs/monitor.log
touch /opt/${app_name}/logs/app.log

# Set proper permissions
chown -R root:root /opt/${app_name}
chmod -R 755 /opt/${app_name}
chmod 600 /opt/${app_name}/.env.template

# Create a setup completion flag
touch /opt/${app_name}/.setup_complete

log "=== ProEnglish Platform Setup Complete ==="
log "Next steps:"
log "1. Copy your .env file to /opt/${app_name}/.env"
log "2. Build and push your Docker image"
log "3. Generate SSL certificates: certbot certonly --nginx -d api.${domain_name}"
log "4. Deploy your application: /opt/${app_name}/scripts/deploy.sh"
log "5. Monitor your application: /opt/${app_name}/scripts/monitor.sh"
log ""
log "Server IP: $(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)"
log "SSH Access: ssh root@$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)"
log ""
log "Setup completed successfully!"

# =============================================================================
# SYSTEM OPTIMIZATION
# =============================================================================

log "Applying system optimizations..."

# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize kernel parameters
cat >> /etc/sysctl.conf << 'EOF'

# ProEnglish Platform Optimizations
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
vm.swappiness = 10
EOF

# Apply sysctl changes
sysctl -p

log "System optimizations applied successfully"

# Reboot message
log "Setup is complete. The system will reboot in 1 minute to apply all changes."
echo "Rebooting in 1 minute..." | wall
nohup bash -c 'sleep 60 && reboot' > /dev/null 2>&1 &

exit 0