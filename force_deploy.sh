#!/bin/bash

# Script para forçar o deploy da aplicação no EC2
# Este script será executado via AWS Systems Manager

echo "🚀 Forçando deploy da aplicação Django..."

# Configurações
ECR_REPOSITORY="225989361192.dkr.ecr.eu-west-1.amazonaws.com/pro-english-backend"
AWS_REGION="eu-west-1"
APP_NAME="proenglish-app"

# Login no ECR
echo "🔐 Fazendo login no ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY

# Obter a imagem mais recente com tag específica
echo "🔍 Procurando imagens disponíveis..."
LATEST_SHA=$(aws ecr describe-images \
    --repository-name pro-english-backend \
    --region $AWS_REGION \
    --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageDigest' \
    --output text)

# Procurar por uma tag SHA específica
LATEST_TAG=$(aws ecr describe-images \
    --repository-name pro-english-backend \
    --region $AWS_REGION \
    --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageTags[?starts_with(@, `main-`)] | [0]' \
    --output text)

if [ "$LATEST_TAG" == "None" ] || [ "$LATEST_TAG" == "" ]; then
    echo "⚠️  Nenhuma tag main- encontrada, procurando qualquer tag..."
    LATEST_TAG=$(aws ecr describe-images \
        --repository-name pro-english-backend \
        --region $AWS_REGION \
        --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageTags[0]' \
        --output text)
fi

if [ "$LATEST_TAG" == "None" ] || [ "$LATEST_TAG" == "" ]; then
    echo "❌ Nenhuma imagem com tag encontrada no ECR"
    exit 1
fi

echo "✅ Imagem encontrada: $LATEST_TAG"

# Parar container temporário
echo "⏹️  Parando container temporário..."
docker stop temp-healthcheck 2>/dev/null || true
docker rm temp-healthcheck 2>/dev/null || true

# Parar aplicação atual se existir
echo "⏹️  Parando aplicação atual..."
docker stop $APP_NAME 2>/dev/null || true
docker rm $APP_NAME 2>/dev/null || true

# Pull da nova imagem
echo "📥 Baixando imagem: $ECR_REPOSITORY:$LATEST_TAG"
docker pull $ECR_REPOSITORY:$LATEST_TAG

if [ $? -ne 0 ]; then
    echo "❌ Erro ao baixar imagem"
    exit 1
fi

# Obter secrets do AWS Secrets Manager
echo "🔐 Obtendo configurações do Secrets Manager..."
SECRET_ARN="arn:aws:secretsmanager:eu-west-1:225989361192:secret:pro-english/production/django-v2-fnJAXi"
SECRETS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --region $AWS_REGION --query SecretString --output text)

if [ $? -ne 0 ]; then
    echo "❌ Erro ao obter secrets"
    exit 1
fi

# Criar arquivo de environment
echo "📝 Criando arquivo de environment..."
echo $SECRETS | jq -r 'to_entries|map("\(.key)=\(.value)")|.[]' > /opt/app.env

# Adicionar configurações específicas do container
cat >> /opt/app.env << EOF
USE_POSTGRESQL=True
RATELIMIT_ENABLE=False
DEBUG=False
EOF

# Executar a aplicação Django
echo "🚀 Iniciando aplicação Django..."
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

if [ $? -eq 0 ]; then
    echo "✅ Aplicação iniciada com sucesso!"
    echo "🌐 Aguarde alguns segundos para a aplicação inicializar..."
    
    # Aguardar um pouco e verificar se está rodando
    sleep 10
    
    if docker ps | grep -q $APP_NAME; then
        echo "✅ Container está rodando!"
        
        # Testar health check local
        echo "🔍 Testando health check..."
        for i in {1..5}; do
            if curl -f -s http://localhost:8000/api/v1/health/ > /dev/null; then
                echo "✅ Aplicação respondendo corretamente!"
                break
            else
                echo "⏳ Tentativa $i/5 - aguardando aplicação inicializar..."
                sleep 5
            fi
        done
        
    else
        echo "❌ Container não está rodando - verificar logs"
        docker logs $APP_NAME
        exit 1
    fi
else
    echo "❌ Erro ao iniciar aplicação"
    exit 1
fi

echo "🎉 Deploy concluído com sucesso!"
echo "🌐 Aplicação disponível em: http://pro-english-alb-343566329.eu-west-1.elb.amazonaws.com"