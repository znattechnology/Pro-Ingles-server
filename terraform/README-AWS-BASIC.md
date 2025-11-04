# 🚀 AWS Basic Setup - ProEnglish Platform

Configuração AWS econômica para teste da plataforma ProEnglish com orçamento de **$40/mês**.

## 💰 **Estrutura de Custos**

| Serviço | Especificações | Custo/mês |
|---------|---------------|-----------|
| **EC2 t3.small** | 2 vCPUs, 2GB RAM, 20GB SSD | $15.18 |
| **EBS Storage** | 20GB gp3 | $2.00 |
| **S3 Storage** | Arquivos estáticos | $1.00 |
| **Data Transfer** | Tráfego básico | $3.00 |
| **TOTAL** | | **~$22/mês** |
| **🎯 Orçamento** | | **$40/mês** |
| **✅ Margem** | | **$18/mês** |

## 📋 **Pré-requisitos**

### 1. Conta AWS
- Conta AWS ativa
- AWS CLI configurado
- Terraform instalado

### 2. Banco de Dados Neon
- Conta no [Neon](https://neon.tech) (gratuita)
- URL de conexão PostgreSQL

### 3. Chave SSH
```bash
# Gerar chave SSH (se não existir)
ssh-keygen -t rsa -b 4096 -C "admin@proenglish.ao"
```

## 🚀 **Deploy Rápido**

### **Passo 1: Configurar Variáveis**
```bash
cd terraform
cp terraform.tfvars.basic.example terraform.tfvars
```

Edite `terraform.tfvars`:
```hcl
# Database Neon (OBRIGATÓRIO)
neon_database_url = "postgresql://user:pass@host:5432/db?sslmode=require"

# Django Secret Key (OBRIGATÓRIO) 
django_secret_key = "sua-chave-secreta-super-longa-aqui"

# SSH (OBRIGATÓRIO)
ssh_public_key_path = "~/.ssh/id_rsa.pub"

# Configurações básicas
project = "proenglish"
instance_type = "t3.small"  # $15.18/mês
aws_region = "us-east-1"
```

### **Passo 2: Deploy Terraform**
```bash
# Inicializar Terraform
terraform init

# Ver o que será criado
terraform plan

# Aplicar configuração
terraform apply
```

### **Passo 3: Aguardar Setup**
```bash
# Pegar IP da instância
INSTANCE_IP=$(terraform output -raw instance_public_ip)

# Verificar progresso da instalação
ssh -i ~/.ssh/id_rsa ec2-user@$INSTANCE_IP
sudo tail -f /var/log/cloud-init-output.log
```

## 📁 **Estrutura Criada**

```
AWS Resources:
├── EC2 Instance (t3.small)
├── Security Group
├── SSH Key Pair  
├── S3 Bucket (media files)
└── CloudWatch Alarms

Server Structure:
/opt/proenglish/
├── app/                 # Django application
├── scripts/            # Management scripts
├── logs/               # Application logs
├── backups/            # Backup files
├── .env                # Environment variables
└── setup-info.txt      # Setup information
```

## ⚙️ **Configuração da Aplicação**

### **1. Upload do Código Django**
```bash
# Comprimir seu código
tar -czf proenglish-app.tar.gz -C /caminho/para/seu/django/app .

# Upload para servidor
scp -i ~/.ssh/id_rsa proenglish-app.tar.gz ec2-user@$INSTANCE_IP:/opt/proenglish/

# Conectar e extrair
ssh -i ~/.ssh/id_rsa ec2-user@$INSTANCE_IP
cd /opt/proenglish
tar -xzf proenglish-app.tar.gz -C app/
```

### **2. Configurar Variáveis de Ambiente**
```bash
# Editar arquivo .env
sudo nano /opt/proenglish/.env
```

Exemplo de `.env`:
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Django
DJANGO_SECRET_KEY=sua-chave-secreta
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<IP_DA_INSTANCIA>

# AWS S3 (será preenchido automaticamente)
AWS_STORAGE_BUCKET_NAME=proenglish-media-xxxxxxxx
AWS_S3_REGION_NAME=us-east-1

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_URL=redis://localhost:6379/1
```

### **3. Configurar Django**
```bash
# Navegar para app
cd /opt/proenglish/app

# Carregar environment
source /opt/proenglish/.env

# Executar migrações
python3 manage.py migrate

# Criar superuser
python3 manage.py createsuperuser

# Coletar arquivos estáticos
python3 manage.py collectstatic --noinput
```

### **4. Iniciar Aplicação**
```bash
# Iniciar serviço
sudo systemctl start proenglish
sudo systemctl enable proenglish

# Verificar status
sudo systemctl status proenglish

# Ver logs
journalctl -u proenglish -f
```

## 🔧 **Comandos Úteis**

### **Status e Monitoramento**
```bash
# Status geral do sistema
/opt/proenglish/scripts/status.sh

# Monitorar recursos
htop

# Ver logs da aplicação
journalctl -u proenglish -f

# Ver logs de setup
sudo tail -f /var/log/cloud-init-output.log
```

### **Gerenciamento da Aplicação**
```bash
# Reiniciar aplicação
sudo systemctl restart proenglish

# Parar aplicação
sudo systemctl stop proenglish

# Django management
cd /opt/proenglish/app
python3 manage.py <comando>
```

### **Backup e Manutenção**
```bash
# Fazer backup manual
/opt/proenglish/scripts/backup.sh

# Ver backups
ls -la /opt/proenglish/backups/

# Atualizar sistema
sudo yum update -y
```

## 🌐 **Acessar Aplicação**

Após o setup completo:

- **🌍 Aplicação**: `http://<IP_DA_INSTANCIA>:8000`
- **👨‍💼 Admin Django**: `http://<IP_DA_INSTANCIA>:8000/admin/`
- **🔗 API**: `http://<IP_DA_INSTANCIA>:8000/api/`

## 🔒 **Configurações de Segurança**

### **1. Atualizar Security Group**
```bash
# Editar terraform.tfvars para seu IP específico
allowed_ssh_ips = ["SEU.IP.AQUI/32"]

# Aplicar mudança
terraform apply
```

### **2. Configurar SSL (Produção)**
```bash
# Instalar certbot
sudo yum install -y certbot python3-certbot-nginx

# Configurar domínio (se tiver)
sudo certbot --nginx -d seudominio.com
```

### **3. Configurar Firewall**
```bash
# Verificar regras do firewall
sudo firewall-cmd --list-all

# Restringir acesso SSH (exemplo)
sudo firewall-cmd --permanent --remove-port=22/tcp
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="SEU.IP.AQUI/32" port protocol="tcp" port="22" accept'
sudo firewall-cmd --reload
```

## 📊 **Monitoramento de Custos**

### **CloudWatch Dashboards**
- Acesse: AWS Console → CloudWatch → Dashboards
- Métricas da instância: CPU, Memory, Network

### **Cost Explorer**
- Acesse: AWS Console → Cost Management → Cost Explorer
- Configure alertas de custo para $35/mês

### **Otimizações Futuras**
```bash
# Se precisar de mais recursos:
instance_type = "t3.medium"  # $30.36/mês

# Se precisar de menos recursos:
instance_type = "t3.micro"   # $8.76/mês
```

## 🆘 **Troubleshooting**

### **Aplicação não inicia**
```bash
# Verificar logs
journalctl -u proenglish -n 50

# Verificar Django
cd /opt/proenglish/app
python3 manage.py check

# Testar manualmente
python3 manage.py runserver 0.0.0.0:8000
```

### **Erro de conectividade**
```bash
# Verificar security group
aws ec2 describe-security-groups --group-ids <SG_ID>

# Verificar nginx
sudo systemctl status nginx
sudo nginx -t
```

### **Problemas de banco**
```bash
# Testar conexão
python3 -c "import psycopg2; print('OK')"

# Verificar migrations
python3 manage.py showmigrations
```

## 🔄 **Scaling e Upgrades**

### **Upgrade Vertical**
```bash
# Editar terraform.tfvars
instance_type = "t3.medium"  # +$15.18/mês

# Aplicar upgrade
terraform apply
```

### **Adicionar Load Balancer** 
```bash
# Futuro: Application Load Balancer
# Custo adicional: ~$16/mês
```

### **Storage Adicional**
```bash
# Aumentar volume EBS
root_volume_size = 40  # +$2.00/mês

terraform apply
```

## 📝 **Logs e Debugging**

### **Locais de Logs**
```bash
# Setup inicial
/var/log/cloud-init-output.log

# Aplicação Django
/opt/proenglish/logs/app.log
journalctl -u proenglish

# Nginx
/var/log/nginx/access.log
/var/log/nginx/error.log

# Sistema
/var/log/messages
dmesg
```

## 📞 **Suporte**

### **Comandos de Diagnóstico**
```bash
# Status completo
/opt/proenglish/scripts/status.sh

# Informações do sistema
cat /opt/proenglish/setup-info.txt

# Recursos
free -h
df -h
ps aux | grep python
```

### **Recrear Infraestrutura**
```bash
# Destruir (CUIDADO!)
terraform destroy

# Recriar
terraform apply
```

---

## ✅ **Checklist de Deploy**

- [ ] ✅ Configurar `terraform.tfvars`
- [ ] ✅ Executar `terraform apply`
- [ ] ✅ Aguardar setup completo (5-10 min)
- [ ] ✅ Upload código Django
- [ ] ✅ Configurar `.env`
- [ ] ✅ Executar migrações
- [ ] ✅ Criar superuser
- [ ] ✅ Iniciar serviço
- [ ] ✅ Testar aplicação
- [ ] ✅ Configurar SSL (produção)
- [ ] ✅ Configurar monitoramento

**🎯 Meta de Custo: $40/mês ✅ Alcançada: ~$22/mês**