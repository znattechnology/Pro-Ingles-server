# =============================================================================
# AWS BASIC INFRASTRUCTURE - PROENGLISH PLATFORM
# Budget: $40/month | Configuração econômica para teste
# =============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
}

# =============================================================================
# VPC SIMPLES - USANDO DEFAULT VPC PARA ECONOMIA
# =============================================================================

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
# SECURITY GROUP - REGRAS DE FIREWALL
# =============================================================================

resource "aws_security_group" "app" {
  name_prefix = "${var.project_name}-"
  vpc_id      = data.aws_vpc.default.id
  description = "Security group for ProEnglish application"

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_ips
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

  # Django development server (temporário)
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
    Name = "${var.project_name}-security-group"
  })
}

# =============================================================================
# KEY PAIR PARA SSH
# =============================================================================

resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-key"
  public_key = file(var.ssh_public_key_path)

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-ssh-key"
  })
}

# =============================================================================
# EC2 INSTANCE - SERVIDOR PRINCIPAL
# t3.small (~$15/mês) - Adequado para teste
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
  
  # EBS optimized for better performance
  ebs_optimized = true

  # Root volume configuration
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true
    
    tags = merge(var.common_tags, {
      Name = "${var.project_name}-root-volume"
    })
  }

  # User data for initial setup
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    project_name = var.project_name
    neon_db_url  = var.neon_database_url
    secret_key   = var.django_secret_key
  }))

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-server"
    Type = "Application"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# S3 BUCKET PARA ARQUIVOS ESTÁTICOS
# =============================================================================

resource "aws_s3_bucket" "media" {
  bucket = "${var.project_name}-media-${random_string.bucket_suffix.result}"

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-media-bucket"
  })
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# S3 bucket policy for public read
resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.media.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.media]
}

# S3 bucket CORS configuration
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "POST", "PUT", "DELETE"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# =============================================================================
# CLOUDWATCH ALARMS BÁSICOS (Gratuito)
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.project_name}-high-cpu"
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