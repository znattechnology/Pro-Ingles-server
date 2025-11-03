#!/bin/bash

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
yum install -y unzip
unzip awscliv2.zip
./aws/install

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Get secrets from AWS Secrets Manager
SECRETS=$(aws secretsmanager get-secret-value --secret-id ${SECRET_ARN} --region ${AWS_REGION} --query SecretString --output text)

# Parse secrets and create environment file
echo $SECRETS | jq -r 'to_entries|map("\(.key)=\(.value)")|.[]' > /opt/app.env

# Log in to ECR
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY}

# Create a simple health check endpoint until real app is deployed
docker run -d \
  --name temp-healthcheck \
  --restart unless-stopped \
  -p 8000:80 \
  nginx:alpine

# Create a simple health endpoint
docker exec temp-healthcheck sh -c 'echo "{ \"status\": \"waiting_for_deployment\", \"message\": \"Infrastructure ready, waiting for application deployment\" }" > /usr/share/nginx/html/index.html'

# Health check script
cat << 'EOF' > /opt/health-check.sh
#!/bin/bash
HEALTH_URL="http://localhost:8000/api/v1/health/"
if curl -f -s $HEALTH_URL > /dev/null; then
    echo "$(date): Health check passed"
    exit 0
else
    echo "$(date): Health check failed, restarting container"
    docker restart proenglish-app
    exit 1
fi
EOF

chmod +x /opt/health-check.sh

# Schedule health checks every 5 minutes
echo "*/5 * * * * /opt/health-check.sh >> /var/log/health-check.log 2>&1" | crontab -

# Auto-update script for new deployments
cat << 'EOF' > /opt/deploy-update.sh
#!/bin/bash
ECR_REPOSITORY="${ECR_REPOSITORY}"
AWS_REGION="${AWS_REGION}"

# Check if there are any images in ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY
IMAGE_COUNT=$(aws ecr describe-images --repository-name $(echo $ECR_REPOSITORY | cut -d'/' -f2) --region $AWS_REGION --query 'length(imageDetails)' --output text 2>/dev/null || echo "0")

if [ "$IMAGE_COUNT" -gt 0 ]; then
    # Get latest image
    LATEST_TAG=$(aws ecr describe-images --repository-name $(echo $ECR_REPOSITORY | cut -d'/' -f2) --region $AWS_REGION --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageTags[0]' --output text)
    
    if [ "$LATEST_TAG" != "None" ] && [ "$LATEST_TAG" != "" ]; then
        echo "$(date): New image available: $LATEST_TAG, updating..."
        
        # Stop temp health check
        docker stop temp-healthcheck || true
        docker rm temp-healthcheck || true
        
        # Pull and run real application
        docker pull $ECR_REPOSITORY:$LATEST_TAG
        docker stop proenglish-app || true
        docker rm proenglish-app || true
        
        docker run -d \
          --name proenglish-app \
          --restart unless-stopped \
          -p 8000:8000 \
          --env-file /opt/app.env \
          --log-driver awslogs \
          --log-opt awslogs-group="/aws/ec2/pro-english-production" \
          --log-opt awslogs-region=$AWS_REGION \
          --log-opt awslogs-stream="$(curl -s http://169.254.169.254/latest/meta-data/instance-id)" \
          $ECR_REPOSITORY:$LATEST_TAG
        
        echo "$(date): Update completed with image $LATEST_TAG"
    else
        echo "$(date): No tagged images found"
    fi
else
    echo "$(date): No images in ECR yet, keeping temp health check"
fi
EOF

chmod +x /opt/deploy-update.sh

# Schedule deployment checks every 10 minutes
echo "*/10 * * * * /opt/deploy-update.sh >> /var/log/deploy-update.log 2>&1" | crontab -

echo "Userdata script completed successfully" > /var/log/userdata-complete.log