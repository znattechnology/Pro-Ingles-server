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

# Configuration
ECR_REPOSITORY="225989361192.dkr.ecr.eu-west-1.amazonaws.com/pro-english-backend"
AWS_REGION="eu-west-1"
SECRET_ARN="arn:aws:secretsmanager:eu-west-1:225989361192:secret:pro-english/production/django-v2-fnJAXi"
APP_NAME="proenglish-app"

# Get secrets from AWS Secrets Manager and create environment file
echo "Getting secrets and creating environment file..."
SECRETS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --region $AWS_REGION --query SecretString --output text)
echo $SECRETS | jq -r 'to_entries|map("\(.key)=\(.value)")|.[]' > /opt/app.env

# Add additional configuration
cat >> /opt/app.env << EOF
USE_POSTGRESQL=True
RATELIMIT_ENABLE=False
DEBUG=False
EOF

# Log in to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY

# Try to deploy the real application immediately
echo "Attempting to deploy Django application..."
IMAGE_COUNT=$(aws ecr describe-images --repository-name pro-english-backend --region $AWS_REGION --query 'length(imageDetails)' --output text 2>/dev/null || echo "0")

if [ "$IMAGE_COUNT" -gt 0 ]; then
    echo "Images found in ECR, deploying Django application..."
    
    # First try to get image with 'main' tag
    LATEST_TAG=$(aws ecr describe-images --repository-name pro-english-backend --region $AWS_REGION --query 'imageDetails[?contains(imageTags, `main`)].imageTags[0] | [0]' --output text 2>/dev/null)
    
    if [ "$LATEST_TAG" == "None" ] || [ "$LATEST_TAG" == "" ]; then
        # If no 'main' tag, get the most recent image
        LATEST_TAG=$(aws ecr describe-images --repository-name pro-english-backend --region $AWS_REGION --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageTags[0]' --output text)
    fi
    
    if [ "$LATEST_TAG" != "None" ] && [ "$LATEST_TAG" != "" ]; then
        echo "Deploying with image tag: $LATEST_TAG"
        
        # Pull the image
        docker pull $ECR_REPOSITORY:$LATEST_TAG
        
        # Run the Django application
        docker run -d \
          --name $APP_NAME \
          --restart unless-stopped \
          -p 8000:8000 \
          --env-file /opt/app.env \
          --log-driver awslogs \
          --log-opt awslogs-group="/aws/ec2/pro-english-production" \
          --log-opt awslogs-region=$AWS_REGION \
          --log-opt awslogs-stream="$(curl -s http://169.254.169.254/latest/meta-data/instance-id)" \
          $ECR_REPOSITORY:$LATEST_TAG
        
        # Wait a bit and check if it's running
        sleep 15
        
        if docker ps | grep -q $APP_NAME; then
            echo "Django application deployed successfully!"
            
            # Test health check
            for i in {1..10}; do
                if curl -f -s http://localhost:8000/api/v1/health/ > /dev/null; then
                    echo "Health check passed - Django is responding!"
                    break
                else
                    echo "Waiting for Django to start... ($i/10)"
                    sleep 5
                fi
            done
        else
            echo "Django container failed to start, falling back to temp health check"
            # Create temp health check as fallback
            docker run -d \
              --name temp-healthcheck \
              --restart unless-stopped \
              -p 8000:80 \
              nginx:alpine
            
            docker exec temp-healthcheck sh -c 'echo "{ \"status\": \"waiting_for_deployment\", \"message\": \"Infrastructure ready, waiting for application deployment\" }" > /usr/share/nginx/html/index.html'
        fi
    else
        echo "No tagged images found, creating temp health check"
        # Create temp health check
        docker run -d \
          --name temp-healthcheck \
          --restart unless-stopped \
          -p 8000:80 \
          nginx:alpine
        
        docker exec temp-healthcheck sh -c 'echo "{ \"status\": \"waiting_for_deployment\", \"message\": \"Infrastructure ready, waiting for application deployment\" }" > /usr/share/nginx/html/index.html'
    fi
else
    echo "No images in ECR yet, creating temp health check"
    # Create temp health check
    docker run -d \
      --name temp-healthcheck \
      --restart unless-stopped \
      -p 8000:80 \
      nginx:alpine
    
    docker exec temp-healthcheck sh -c 'echo "{ \"status\": \"waiting_for_deployment\", \"message\": \"Infrastructure ready, waiting for application deployment\" }" > /usr/share/nginx/html/index.html'
fi

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

# Improved auto-update script for new deployments
cat << 'EOF' > /opt/deploy-update.sh
#!/bin/bash
ECR_REPOSITORY="225989361192.dkr.ecr.eu-west-1.amazonaws.com/pro-english-backend"
AWS_REGION="eu-west-1"
SECRET_ARN="arn:aws:secretsmanager:eu-west-1:225989361192:secret:pro-english/production/django-v2-fnJAXi"
APP_NAME="proenglish-app"

echo "$(date): Checking for new deployments..."

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY

# Check if there are any images in ECR
IMAGE_COUNT=$(aws ecr describe-images --repository-name pro-english-backend --region $AWS_REGION --query 'length(imageDetails)' --output text 2>/dev/null || echo "0")

if [ "$IMAGE_COUNT" -gt 0 ]; then
    # First try to get image with 'main' tag
    LATEST_TAG=$(aws ecr describe-images --repository-name pro-english-backend --region $AWS_REGION --query 'imageDetails[?contains(imageTags, `main`)].imageTags[0] | [0]' --output text 2>/dev/null)
    
    if [ "$LATEST_TAG" == "None" ] || [ "$LATEST_TAG" == "" ]; then
        # If no 'main' tag, get the most recent image
        LATEST_TAG=$(aws ecr describe-images --repository-name pro-english-backend --region $AWS_REGION --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageTags[0]' --output text)
    fi
    
    if [ "$LATEST_TAG" != "None" ] && [ "$LATEST_TAG" != "" ]; then
        echo "$(date): Found image with tag: $LATEST_TAG"
        
        # Check if we're already running this image
        if docker ps --format "table {{.Image}}" | grep -q "$ECR_REPOSITORY:$LATEST_TAG"; then
            echo "$(date): Already running latest image $LATEST_TAG"
            exit 0
        fi
        
        echo "$(date): Updating to new image: $LATEST_TAG"
        
        # Stop temp health check if running
        docker stop temp-healthcheck 2>/dev/null || true
        docker rm temp-healthcheck 2>/dev/null || true
        
        # Pull new image
        docker pull $ECR_REPOSITORY:$LATEST_TAG
        
        # Stop current app if running
        docker stop $APP_NAME 2>/dev/null || true
        docker rm $APP_NAME 2>/dev/null || true
        
        # Recreate environment file
        SECRETS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --region $AWS_REGION --query SecretString --output text)
        echo $SECRETS | jq -r 'to_entries|map("\(.key)=\(.value)")|.[]' > /opt/app.env
        cat >> /opt/app.env << EOF2
USE_POSTGRESQL=True
RATELIMIT_ENABLE=False
DEBUG=False
EOF2
        
        # Run new container
        docker run -d \
          --name $APP_NAME \
          --restart unless-stopped \
          -p 8000:8000 \
          --env-file /opt/app.env \
          --log-driver awslogs \
          --log-opt awslogs-group="/aws/ec2/pro-english-production" \
          --log-opt awslogs-region=$AWS_REGION \
          --log-opt awslogs-stream="$(curl -s http://169.254.169.254/latest/meta-data/instance-id)" \
          $ECR_REPOSITORY:$LATEST_TAG
        
        echo "$(date): Update completed with image $LATEST_TAG"
        
        # Verify deployment
        sleep 10
        if docker ps | grep -q $APP_NAME; then
            echo "$(date): New container is running successfully"
        else
            echo "$(date): New container failed to start, checking logs..."
            docker logs $APP_NAME
        fi
    else
        echo "$(date): No tagged images found"
    fi
else
    echo "$(date): No images in ECR yet"
fi
EOF

chmod +x /opt/deploy-update.sh

# Schedule deployment checks every 5 minutes (more frequent)
echo "*/5 * * * * /opt/deploy-update.sh >> /var/log/deploy-update.log 2>&1" | crontab -

echo "Userdata script completed successfully" > /var/log/userdata-complete.log