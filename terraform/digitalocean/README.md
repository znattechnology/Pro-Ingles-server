# 🌊 DigitalOcean Infrastructure - ProEnglish Platform

Infraestrutura completa para a plataforma ProEnglish usando DigitalOcean com orçamento de $40/mês.

## 📋 Pré-requisitos

### 1. Conta DigitalOcean
- Criar conta em [DigitalOcean](https://cloud.digitalocean.com/)
- Gerar API Token em: Account → API → Tokens/Keys

### 2. Ferramentas Necessárias
```bash
# Terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# DigitalOcean CLI (opcional)
curl -sL https://github.com/digitalocean/doctl/releases/download/v1.100.0/doctl-1.100.0-linux-amd64.tar.gz | tar -xzv
sudo mv doctl /usr/local/bin/
```

### 3. Chave SSH
```bash
# Gerar chave SSH (se não existir)
ssh-keygen -t rsa -b 4096 -C "admin@proenglish.ao"
```

## 🚀 Configuração Inicial

### 1. Clonar e Configurar
```bash
cd terraform/digitalocean
cp terraform.tfvars.example terraform.tfvars
```

### 2. Editar Variáveis
Edite `terraform.tfvars` com seus valores:

```hcl
# Token da API DigitalOcean
do_token = "dop_v1_seu_token_aqui"

# Domínio da aplicação
domain_name = "proenglish.ao"

# URL do banco Neon
neon_database_url = "postgresql://user:pass@host/db"

# Django Secret Key
app_environment_vars = {
  DJANGO_SECRET_KEY = "sua-chave-secreta-aqui"
  # ... outras variáveis
}

# Email para alertas
alert_email = "admin@proenglish.ao"
```

### 3. Inicializar Terraform
```bash
terraform init
terraform plan
terraform apply
```

## 💰 Estrutura de Custos

| Serviço | Especificações | Custo/mês |
|---------|---------------|-----------|
| **Droplet** | 2 vCPUs, 4GB RAM, 120GB SSD | $32.00 |
| **Spaces** | 250GB storage + 1TB CDN | $5.00 |
| **Firewall** | Cloud Firewall | $0.00 |
| **Monitoring** | Básico | $0.00 |
| **Backup** | Opcional | $6.40 |
| **TOTAL** | | **$37.00** |

## 🏗️ Arquitetura

```
Internet
    ↓
DigitalOcean Cloud Firewall
    ↓
Droplet (Ubuntu 22.04)
├── Nginx (Reverse Proxy + SSL)
├── Docker Compose
│   ├── Django Backend
│   ├── Redis Cache
│   └── Nginx
└── Monitoring & Logs
    ↓
Neon PostgreSQL (Serverless)
DigitalOcean Spaces (S3-compatible)
```

## 📁 Estrutura de Arquivos

```
digitalocean/
├── main.tf                     # Recursos principais
├── variables.tf               # Variáveis de configuração
├── outputs.tf                 # Outputs do Terraform
├── user_data.sh              # Script de inicialização
├── terraform.tfvars.example  # Exemplo de variáveis
└── README.md                 # Esta documentação
```

## 🔧 Recursos Criados

### 1. Droplet Principal
- **Tipo**: Premium Basic (s-2vcpu-4gb)
- **SO**: Ubuntu 22.04 LTS
- **Região**: Frankfurt (fra1)
- **Features**: Monitoring, IPv6, Auto-backup

### 2. Cloud Firewall
- SSH (22) - IPs específicos
- HTTP (80) - Público
- HTTPS (443) - Público
- Outbound - Liberado

### 3. Spaces Storage
- **Bucket**: proenglish-media
- **CDN**: Habilitado
- **CORS**: Configurado para frontend

### 4. DNS Records
- A record: api.proenglish.ao
- AAAA record: IPv6
- WWW redirect (opcional)

### 5. Monitoring Alerts
- CPU > 80%
- Memory > 85%
- Disk > 90%

## 🚀 Deploy da Aplicação

### 1. Após o Terraform Apply
```bash
# Conectar ao servidor
ssh root@$(terraform output -raw droplet_ipv4_address)

# Verificar status do setup
tail -f /var/log/cloud-init-output.log
```

### 2. Configurar Variáveis de Ambiente
```bash
cd /opt/proenglish
cp .env.template .env
nano .env  # Editar com valores reais
```

### 3. Deploy da Aplicação
```bash
# Build e push da imagem Docker
docker build -t proenglish/backend:latest .
docker tag proenglish/backend:latest registry.digitalocean.com/proenglish/backend:latest
docker push registry.digitalocean.com/proenglish/backend:latest

# Deploy no servidor
/opt/proenglish/scripts/deploy.sh
```

### 4. Configurar SSL
```bash
# Gerar certificados SSL
certbot certonly --nginx -d api.proenglish.ao

# Restart nginx
docker-compose restart nginx
```

## 📊 Monitoramento

### 1. Scripts Automáticos
- **Backup**: Diário às 2:00 AM
- **Monitor**: A cada 5 minutos
- **Logs**: Rotação diária

### 2. Logs Importantes
```bash
# Logs da aplicação
tail -f /opt/proenglish/logs/app.log

# Logs do nginx
tail -f /opt/proenglish/logs/nginx/access.log

# Status dos serviços
/opt/proenglish/scripts/monitor.sh
```

### 3. DigitalOcean Dashboard
- Métricas de CPU, RAM, Disk
- Network traffic
- Alertas por email

## 🔄 Escalabilidade

### Fase 1: Otimização (0-6 meses)
- Cache Redis otimizado
- Queries de banco otimizadas
- Compressão de assets

### Fase 2: Upgrade Vertical (6-12 meses)
```bash
# Upgrade para General Purpose
terraform apply -var="droplet_size=s-2vcpu-8gb"  # $63/mês
```

### Fase 3: Upgrade Horizontal (12+ meses)
```bash
# Adicionar Load Balancer + Multiple Droplets
terraform apply -var="enable_load_balancer=true"  # +$10/mês
```

## 🔒 Segurança

### 1. Network Security
- Firewall com regras específicas
- SSH key-only authentication
- Fail2ban protection
- Rate limiting

### 2. Application Security
- HTTPS obrigatório
- Security headers
- CORS configurado
- Environment secrets

### 3. Backup Strategy
- Snapshots automáticos
- Backup de arquivos
- Database backup (Neon automático)

## 🛠️ Comandos Úteis

### Terraform
```bash
# Ver status dos recursos
terraform state list

# Ver outputs
terraform output

# Destroy tudo (CUIDADO!)
terraform destroy
```

### Servidor
```bash
# Status dos containers
docker-compose ps

# Logs da aplicação
docker-compose logs -f backend

# Restart serviços
docker-compose restart

# Shell no container
docker-compose exec backend bash
```

## 🆘 Troubleshooting

### 1. Droplet não responde
```bash
# Verificar via DigitalOcean Console
# Ou conectar via Recovery ISO

# Verificar logs de inicialização
cat /var/log/cloud-init-output.log
```

### 2. SSL não funciona
```bash
# Verificar certificados
certbot certificates

# Renovar certificados
certbot renew

# Verificar configuração nginx
nginx -t
```

### 3. Aplicação não inicia
```bash
# Verificar logs
docker-compose logs backend

# Verificar variáveis de ambiente
docker-compose exec backend env | grep DJANGO

# Restart completo
docker-compose down && docker-compose up -d
```

## 📞 Suporte

### DigitalOcean
- Documentação: https://docs.digitalocean.com/
- Community: https://www.digitalocean.com/community
- Support: Ticket system 24/7

### Contatos de Emergência
- DevOps Team: devops@proenglish.ao
- Admin: admin@proenglish.ao

## 📝 Changelog

### v1.0.0 (Initial Release)
- ✅ Droplet com Docker
- ✅ Spaces storage
- ✅ Cloud Firewall
- ✅ Monitoring básico
- ✅ SSL automático
- ✅ Backup scripts

### Roadmap
- [ ] Load Balancer setup
- [ ] Auto-scaling policies
- [ ] Advanced monitoring
- [ ] CI/CD pipeline
- [ ] Multi-region support

---

**Budget Target**: $40/mês ✅ **ACHIEVED**: $37/mês

Para mais informações, consulte o [plano de migração completo](../DIGITALOCEAN_MIGRATION_PLAN.md).