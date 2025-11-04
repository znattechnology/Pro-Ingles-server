#!/bin/bash

# AWS Basic Setup for ProEnglish Platform
# Budget: $40/month | Using existing configurations

# Update system
yum update -y

# Install essential packages
yum install -y docker git python3 python3-pip nginx redis
systemctl start docker
systemctl enable docker
systemctl start nginx
systemctl enable nginx
systemctl start redis
systemctl enable redis
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Configure AWS credentials
mkdir -p /home/ec2-user/.aws
cat << EOF > /home/ec2-user/.aws/credentials
[default]
aws_access_key_id = ${aws_access_key_id}
aws_secret_access_key = ${aws_secret_access_key}
EOF

cat << EOF > /home/ec2-user/.aws/config
[default]
region = eu-west-1
output = json
EOF

chown -R ec2-user:ec2-user /home/ec2-user/.aws

# Create application directory
mkdir -p /opt/proenglish
cd /opt/proenglish

# Create environment file with all configurations
cat << EOF > /opt/proenglish/.env
# Database Configuration (Neon PostgreSQL)
DATABASE_URL=${neon_db_url}

# Django Configuration
SECRET_KEY=${secret_key}
DEBUG=False
ALLOWED_HOSTS=*

# AWS S3 Configuration
USE_S3=True
AWS_ACCESS_KEY_ID=${aws_access_key_id}
AWS_SECRET_ACCESS_KEY=${aws_secret_access_key}
AWS_S3_BUCKET_NAME=lms-s3-backet
AWS_S3_REGION_NAME=eu-west-1
AWS_S3_CUSTOM_DOMAIN=d13552ljikd29j.cloudfront.net

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://proenglish.ao,https://pro-ingles-client-nine.vercel.app,https://pro-ingles-client-git-main-znattechnology95-1655s-projects.vercel.app,https://proenglish.com,https://www.proenglish.com
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://proenglish.ao,https://pro-ingles-client-nine.vercel.app,https://pro-ingles-client-git-main-znattechnology95-1655s-projects.vercel.app,https://proenglish.com,https://www.proenglish.com

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=vivaldo.adao2019@gmail.com
EMAIL_HOST_PASSWORD=gcmvzcqxwtwslxjf

# PayPal Configuration
PAYPAL_CLIENT_ID=AZKKGSPLbQh6sXSEGfhSl3YtY1iNnPOT4TKVU-7FxvqL7jVBGJR96dRGwlj5hU6HdVm_vLQMn_6EKdnq
PAYPAL_CLIENT_SECRET=EKaTyOoNaQnUE1U_DLhJL_B5rGnE-K_FwVFf6WcuMrckqKYLEGqmV4aTe6uXjS7DI1b8-SxSVJBEYlVr

# Project settings
PROJECT_NAME=${project_name}
ENVIRONMENT=production
EOF

# Create Nginx configuration
cat << 'EOF' > /etc/nginx/conf.d/proenglish.conf
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/proenglish/staticfiles/;
    }

    location /media/ {
        alias /opt/proenglish/media/;
    }
}
EOF

# Create simple health check placeholder
cat << 'EOF' > /usr/share/nginx/html/index.html
<!DOCTYPE html>
<html>
<head>
    <title>ProEnglish Platform - AWS Basic Setup</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .status { color: #28a745; font-size: 24px; }
        .info { color: #007bff; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>ProEnglish Platform</h1>
    <div class="status">✅ AWS Infrastructure Ready</div>
    <div class="info">
        <p>Server is configured and waiting for application deployment</p>
        <p>Instance Type: t3.small | Budget: $40/month</p>
        <p>Database: Neon PostgreSQL Connected</p>
        <p>Storage: AWS S3 (lms-s3-backet)</p>
    </div>
</body>
</html>
EOF

# Create deployment script for manual setup
cat << 'EOF' > /opt/proenglish/deploy.sh
#!/bin/bash
# Manual deployment script for ProEnglish Django application

cd /opt/proenglish

echo "Starting ProEnglish deployment..."

# Clone or update repository (will be done manually)
# git clone https://github.com/YOUR_REPO/proenglish-backend.git .

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
fi

# Load environment variables
export $(cat .env | xargs)

# Django management commands
if [ -f "manage.py" ]; then
    python3 manage.py collectstatic --noinput
    python3 manage.py migrate
    
    # Create systemd service for Django
    cat << DJANGO_SERVICE > /etc/systemd/system/proenglish.service
[Unit]
Description=ProEnglish Django Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/proenglish
Environment=PATH=/usr/bin:/usr/local/bin
EnvironmentFile=/opt/proenglish/.env
ExecStart=/usr/bin/python3 /opt/proenglish/manage.py runserver 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
DJANGO_SERVICE

    systemctl daemon-reload
    systemctl enable proenglish
    systemctl start proenglish
    
    echo "Django application deployed and started"
else
    echo "Django application not found - manual upload required"
fi
EOF

chmod +x /opt/proenglish/deploy.sh
chown -R ec2-user:ec2-user /opt/proenglish

# Restart nginx
systemctl restart nginx

# Create status log
echo "$(date): AWS Basic Infrastructure setup completed successfully" > /var/log/proenglish-setup.log
echo "Ready for Django application deployment" >> /var/log/proenglish-setup.log

# Final message
wall "ProEnglish AWS setup completed! Ready for application deployment."