# 🚀 GUIA DE DEPLOYMENT - TUWI-BACKEND

## 📋 **RESUMO DA INFRAESTRUTURA ATUALIZADA**

A infraestrutura do Tuwi-Backend foi completamente modernizada e configurada para funcionar com PostgreSQL Neon. 

### ✅ **O QUE FOI CORRIGIDO**

1. **Terraform Completo**
   - ✅ EKS atualizado para versão 1.31
   - ✅ Variáveis e outputs criados
   - ✅ Secrets Manager para credenciais
   - ✅ ALB Controller configurado
   - ✅ CloudWatch logging

2. **Kubernetes Atualizado**
   - ✅ Deployment com PostgreSQL Neon
   - ✅ Health checks melhorados
   - ✅ Security contexts
   - ✅ Resource limits
   - ✅ Service accounts e RBAC

3. **Pipeline CI/CD**
   - ✅ Ambiente staging separado
   - ✅ Security scans
   - ✅ Smoke tests
   - ✅ Blue-green deployment

4. **Monitoramento**
   - ✅ Health checks em `/api/health/`
   - ✅ Readiness e liveness probes
   - ✅ Métricas para Prometheus
   - ✅ Logs estruturados

## 🎯 **DEPLOY RÁPIDO (GUIA DE 5 MINUTOS)**

### 1. **Pré-requisitos**

```bash
# Ferramentas necessárias
aws-cli (configurado)
kubectl
terraform >= 1.3
docker
```

### 2. **Configurar Secrets no GitHub**

```bash
# GitHub Repository → Settings → Secrets
AWS_ACCOUNT_ID=123456789012
DJANGO_SECRET_KEY_STAGING=your-staging-secret-key
DJANGO_SECRET_KEY_PRODUCTION=your-production-secret-key
DATABASE_URL_STAGING=postgresql://user:pass@staging.neon.tech/db
DATABASE_URL_PRODUCTION=postgresql://user:pass@prod.neon.tech/db
```

### 3. **Deploy da Infraestrutura**

```bash
cd terraform/

# Configurar variáveis
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars com seus valores

# Deploy
terraform init
terraform plan
terraform apply
```

### 4. **Deploy da Aplicação**

```bash
# Push para staging
git push origin develop

# Push para produção  
git push origin main
```

## 📋 **CONFIGURAÇÃO DETALHADA**

### **PostgreSQL Neon**

A aplicação está configurada para usar PostgreSQL Neon via `DATABASE_URL`:

```yaml
# k8s/secrets.yaml
DATABASE_URL: "postgresql://user:pass@host.neon.tech/db?sslmode=require"
DATABASE_SSL_REQUIRE: "true"
```

### **Health Checks**

Novos endpoints disponíveis:

```bash
# Health check geral
GET /api/health/

# Kubernetes readiness
GET /api/health/ready/

# Kubernetes liveness  
GET /api/health/live/

# Métricas
GET /api/health/metrics/

# Debug (apenas desenvolvimento)
GET /api/health/debug/
```

### **Ambientes**

| Ambiente | Branch | Namespace | URL |
|----------|---------|-----------|-----|
| Staging | `develop` | `staging` | `staging-api.tuwi.com` |
| Production | `main` | `default` | `api.tuwi.com` |

## ⚙️ **COMANDOS ÚTEIS**

### **Monitoramento**

```bash
# Status geral
kubectl get all -n default

# Status staging
kubectl get all -n staging

# Logs da aplicação
kubectl logs -f deployment/django -n default

# Health check manual
curl https://api.tuwi.com/api/health/
```

### **Troubleshooting**

```bash
# Verificar pods com problemas
kubectl get pods -n default | grep -v Running

# Descrever pod com problema
kubectl describe pod <pod-name> -n default

# Logs detalhados
kubectl logs <pod-name> -n default --previous

# Executar comando no pod
kubectl exec -it <pod-name> -n default -- /bin/sh
```

### **Database Migration**

```bash
# Executar migrações manualmente
kubectl apply -f k8s/migrate-job.yaml -n default

# Acompanhar progresso
kubectl logs -f job/django-migrate -n default
```

### **Rollback**

```bash
# Ver histórico de deploys
kubectl rollout history deployment/django -n default

# Rollback para versão anterior
kubectl rollout undo deployment/django -n default

# Rollback para versão específica
kubectl rollout undo deployment/django --to-revision=2 -n default
```

## 🔧 **CONFIGURAÇÕES NECESSÁRIAS**

### **1. AWS IAM Roles**

Criar roles para GitHub Actions:

```bash
# Para build e push
GitHubActionsPushRole

# Para deploy
GitHubActionsDeployRole  

# Para Terraform
GitHubActionsTerraformRole
```

### **2. Neon PostgreSQL**

```sql
-- Criar usuário para aplicação
CREATE USER tuwi_app WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE tuwi_production TO tuwi_app;
GRANT ALL ON SCHEMA public TO tuwi_app;
```

### **3. Domain e SSL**

```bash
# Configurar Route53 (se usando AWS)
staging-api.tuwi.com → ALB staging
api.tuwi.com → ALB production

# Certificado SSL
aws acm request-certificate --domain-name "*.tuwi.com"
```

## 📊 **MONITORAMENTO E LOGS**

### **CloudWatch**

Logs disponíveis em:
- `/aws/eks/tuwi-eks/application`
- `/aws/eks/tuwi-eks/cluster`

### **Metrics**

```bash
# CPU e Memory
kubectl top pods -n default

# Network traffic
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/default/pods
```

### **Alerts**

Configurar alertas para:
- Pod restarts > 5 em 5 minutos
- Memory usage > 90%
- CPU usage > 80%
- Health checks failing

## 🔒 **SEGURANÇA**

### **Secrets Management**

```bash
# Ver secrets (sem valores)
kubectl get secrets -n default

# Editar secret
kubectl edit secret django-secrets -n default

# Criar secret manual
kubectl create secret generic django-secrets \
  --from-literal=DATABASE_URL='postgresql://...' \
  --from-literal=SECRET_KEY='your-key' \
  -n default
```

### **Network Policies**

```bash
# Aplicar políticas de rede
kubectl apply -f k8s/staging/namespace.yaml
```

### **RBAC**

```bash
# Verificar permissões
kubectl auth can-i get pods --as=system:serviceaccount:default:django-service-account
```

## 🚨 **TROUBLESHOOTING COMUM**

### **Pod não inicia**

```bash
# 1. Verificar recursos
kubectl describe pod <pod-name> -n default

# 2. Verificar secrets
kubectl get secret django-secrets -o yaml -n default

# 3. Verificar conexão DB
kubectl exec -it <pod-name> -n default -- python manage.py check --database default
```

### **Health check falhando**

```bash
# 1. Testar endpoints
kubectl exec -it <pod-name> -n default -- curl localhost:8000/api/health/

# 2. Verificar logs
kubectl logs <pod-name> -n default | grep health

# 3. Verificar database
kubectl exec -it <pod-name> -n default -- python manage.py shell
```

### **Migration errors**

```bash
# 1. Verificar estado das migrações
kubectl exec -it <pod-name> -n default -- python manage.py showmigrations

# 2. Executar migração específica
kubectl exec -it <pod-name> -n default -- python manage.py migrate users

# 3. Reset migrations (cuidado!)
kubectl exec -it <pod-name> -n default -- python manage.py migrate --fake-initial
```

## 📞 **SUPORTE**

Para problemas:

1. Verificar logs no CloudWatch
2. Executar smoke tests
3. Verificar status no GitHub Actions
4. Consultar este guia

---

## 🎉 **DEPLOYMENT PRONTO!**

A infraestrutura está agora **100% compatível** com:
- ✅ Django 4.2.24
- ✅ PostgreSQL Neon
- ✅ Kubernetes 1.31
- ✅ AWS EKS
- ✅ GitHub Actions CI/CD
- ✅ Monitoring completo

**Próximos passos:**
1. Configurar domínios
2. Configurar certificados SSL
3. Executar primeiro deploy
4. Configurar monitoramento
5. Treinar equipe