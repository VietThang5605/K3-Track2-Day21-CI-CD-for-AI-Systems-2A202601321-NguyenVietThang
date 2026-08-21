# 1. Cấu hình Terraform Provider cho AWS
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# 2. Khai báo Region (trùng với region bạn đã tạo S3 Bucket)
provider "aws" {
  region = "ap-southeast-1"
}

# 3. Tự động tìm AMI Ubuntu 22.04 LTS mới nhất từ Canonical
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical ID chính chủ
}

# 4. Đăng ký SSH Public Key lên AWS EC2
# Key này sẽ lấy từ ~/.ssh/mlops_deploy.pub
resource "aws_key_pair" "deployer" {
  key_name   = "mlops-deploy-key"
  public_key = file("~/.ssh/mlops_deploy.pub")
}

# 5. Tạo Security Group (Tường lửa cho phép Port 22 SSH và Port 8000 Inference API)
resource "aws_security_group" "mlops_sg" {
  name        = "mlops-serve-sg"
  description = "Cho phep SSH (port 22) va Inference API (port 8000)"

  # Cho phép kết nối SSH (Port 22)
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Cho phép kết nối API FastAPI (Port 8000)
  ingress {
    description = "FastAPI Inference API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Cho phép máy chủ EC2 kết nối ra ngoài Internet để cài thư viện
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "mlops-serve-sg"
  }
}

# 6. Khởi tạo EC2 Instance (t2.micro / Free tier)
resource "aws_instance" "mlops_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t2.micro"
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.mlops_sg.id]

  root_block_device {
    volume_size = 10 # 10 GB SSD
    volume_type = "gp3"
  }

  tags = {
    Name = "mlops-serve"
  }
}

# 7. In ra địa chỉ Public IP sau khi khởi tạo thành công
output "ec2_public_ip" {
  description = "Public IP cua may chu EC2 dung cho GitHub Actions Secrets"
  value       = aws_instance.mlops_server.public_ip
}
