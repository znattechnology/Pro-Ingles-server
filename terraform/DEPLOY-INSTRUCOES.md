# 🚀 Instruções de Deploy AWS - ProEnglish

**Configuração pronta com suas credenciais existentes!**

## ✅ **O que já está configurado:**
- ✅ Database Neon: Conectado e funcionando
- ✅ AWS S3: Bucket `lms-s3-backet` existente 
- ✅ CloudFront CDN: Configurado
- ✅ Django Secret Key: Aplicada
- ✅ Email SMTP: Gmail configurado
- ✅ Região AWS: eu-west-1

## 🚀 **Deploy em 3 passos:**

### **1. Inicializar Terraform**
```bash
cd /Users/vadao/Documents/Projectos_Next/Sistema_Ingles/Tuwi-Backend/terraform

# Inicializar
terraform init

# Ver o que será criado
terraform plan
```

### **2. Aplicar configuração**
```bash
# Deploy da infraestrutura
terraform apply

# Confirmar com 'yes' quando solicitado
```

### **3. Aguardar setup completo**
```bash
# Pegar IP da instância criada
INSTANCE_IP=$(terraform output -raw instance_public_ip)
echo "IP da instância: $INSTANCE_IP"

# Conectar e acompanhar instalação
ssh -i ~/.ssh/id_rsa ec2-user@$INSTANCE_IP
sudo tail -f /var/log/cloud-init-output.log
```

## 📊 **Custo Total: ~$20/mês**
- 🖥️ EC2 t3.small: $15.18/mês
- 💾 EBS 20GB: $2.00/mês  
- 🌐 Data transfer: $3.00/mês
- ☁️ S3: $0.00 (usando existente)
- **🎯 Orçamento $40/mês: ✅ DENTRO**

## ⏱️ **Tempo estimado:** 10-15 minutos

### **Progresso do setup:**
1. ⏳ Terraform apply (2-3 min)
2. ⏳ EC2 inicializando (1-2 min)
3. ⏳ Instalação automática (5-10 min)
4. ✅ Pronto para usar!

## 🔍 **Verificar se está funcionando:**

### **Após instalação completa:**
```bash
# Acessar aplicação
http://<IP_DA_INSTANCIA>:8000

# Status do sistema
ssh -i ~/.ssh/id_rsa ec2-user@<IP>
/opt/pro-english/scripts/status.sh
```

## 📱 **Próximos passos (após deploy):**

1. **Upload código Django:**
   ```bash
   scp -r -i ~/.ssh/id_rsa ./seu_projeto/ ec2-user@<IP>:/opt/pro-english/app/
   ```

2. **Iniciar aplicação:**
   ```bash
   ssh -i ~/.ssh/id_rsa ec2-user@<IP>
   sudo systemctl start pro-english
   ```

3. **Testar:**
   ```bash
   # Aplicação
   curl http://<IP>:8000
   
   # Django Admin
   http://<IP>:8000/admin/
   ```

## 🆘 **Se algo der errado:**

```bash
# Ver logs de instalação
sudo tail -f /var/log/cloud-init-output.log

# Verificar status
sudo systemctl status pro-english

# Reiniciar se necessário
sudo systemctl restart pro-english

# Destruir tudo e recomeçar
terraform destroy  # CUIDADO!
```

## 📞 **Suporte:**
- 📂 Logs: `/opt/pro-english/logs/`
- 🔧 Scripts: `/opt/pro-english/scripts/`
- ⚙️ Config: `/opt/pro-english/.env`

---

**🎯 Tudo pronto! Execute `terraform apply` para começar.**