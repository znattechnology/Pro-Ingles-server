# =============================================================================
# AWS BASIC INFRASTRUCTURE - PROENGLISH PLATFORM
# Budget: $40/month | Configuração econômica para teste
# =============================================================================

# Usar VPC padrão para economizar custos
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnet" "default" {
  id = data.aws_subnets.default.ids[0]
}

# =============================================================================
# SSH KEY PAIR
# =============================================================================

resource "aws_key_pair" "main" {
  key_name   = "${var.project}-key"
  public_key = file(var.ssh_public_key_path)

  tags = merge(var.common_tags, {
    Name = "${var.project}-ssh-key"
  })
}

# =============================================================================
# SECURITY GROUP - SIMPLES E ECONÔMICO
# =============================================================================

resource "aws_security_group" "app" {
  name_prefix = "${var.project}-"
  vpc_id      = data.aws_vpc.default.id
  description = "Security group for ProEnglish application"

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # ALTERAR para IP específico
    description = "SSH access"
  }

  # HTTP access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  # HTTPS access
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

  # Django dev server (temporário)
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Django dev server"
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project}-security-group"
  })
}

# =============================================================================
# EC2 INSTANCE - SERVIDOR PRINCIPAL (t3.small ~$15/mês)
# =============================================================================

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name              = aws_key_pair.main.key_name
  vpc_security_group_ids = [aws_security_group.app.id]
  subnet_id             = data.aws_subnet.default.id
  
  # Enable detailed monitoring (free for basic)
  monitoring = true
  
  # Root volume configuration (pequeno para economizar)
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20  # 20GB suficiente
    delete_on_termination = true
    encrypted             = true
    
    tags = merge(var.common_tags, {
      Name = "${var.project}-root-volume"
    })
  }

  # User data for initial setup
  user_data = base64encode(templatefile("${path.module}/userdata-simple.sh", {
    project_name = var.project
    neon_db_url  = var.neon_database_url
    secret_key   = var.django_secret_key
  }))

  tags = merge(var.common_tags, {
    Name = "${var.project}-server"
    Type = "Application"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# S3 BUCKET - USANDO BUCKET EXISTENTE
# Bucket: lms-s3-backet (já configurado e funcionando)
# CloudFront: https://d13552ljikd29j.cloudfront.net
# =============================================================================

# Usando bucket S3 existente - não precisa criar novo
# lms-s3-backet já está configurado e funcionando
# Economiza custos e mantém configurações existentes

# =============================================================================
# CLOUDWATCH ALARMS BÁSICOS (GRATUITO)
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.project}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ec2 cpu utilization"

  dimensions = {
    InstanceId = aws_instance.app.id
  }

  tags = var.common_tags
}




