#!/bin/bash

echo "🚀 Deploy automático Django Pro English Backend"
echo "==============================================="

# Configurações
ECR_REPOSITORY="225989361192.dkr.ecr.eu-west-1.amazonaws.com/pro-english-backend"
AWS_REGION="eu-west-1"
APP_NAME="proenglish-app"
SECRET_ARN="arn:aws:secretsmanager:eu-west-1:225989361192:secret:pro-english/production/django-v2-fnJAXi"

# Login no ECR
echo "🔐 Login ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY

# Usar a imagem latest com tag "main"
LATEST_TAG="main"
echo "📥 Baixando imagem: $ECR_REPOSITORY:$LATEST_TAG"
docker pull $ECR_REPOSITORY:$LATEST_TAG

# Parar containers existentes
echo "⏹️ Parando containers..."
docker stop temp-healthcheck $APP_NAME 2>/dev/null || true
docker rm temp-healthcheck $APP_NAME 2>/dev/null || true

# Obter secrets e criar environment file
echo "🔐 Configurando environment..."
SECRETS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --region $AWS_REGION --query SecretString --output text)
echo $SECRETS | jq -r 'to_entries|map("\(.key)=\(.value)")|.[]' > /opt/app.env

# Adicionar configurações específicas
cat >> /opt/app.env << EOF
USE_POSTGRESQL=True
RATELIMIT_ENABLE=False
DEBUG=False
EOF

# Executar aplicação
echo "🚀 Iniciando Django..."
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

# Verificar deployment
echo "🔍 Verificando deployment..."
sleep 15

if docker ps | grep -q $APP_NAME; then
    echo "✅ Container rodando!"
    
    # Testar health check
    for i in {1..10}; do
        if curl -f -s http://localhost:8000/api/v1/health/ > /dev/null; then
            echo "✅ Health check OK!"
            break
        else
            echo "⏳ Aguardando... ($i/10)"
            sleep 3
        fi
    done
    
    echo "🎉 Deploy concluído com sucesso!"
    echo "🌐 App: http://pro-english-alb-343566329.eu-west-1.elb.amazonaws.com"
else
    echo "❌ Container não iniciou!"
    docker logs $APP_NAME
    exit 1
fi