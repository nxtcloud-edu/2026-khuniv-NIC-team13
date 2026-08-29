# Get availability zones data
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-vpc"
    }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-igw"
    }
  )
}

# Public Subnets
resource "aws_subnet" "public" {
  count = length(var.availability_zones)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-public-subnet-${count.index + 1}"
      Type = "public"
    }
  )
}

# Private Subnets
resource "aws_subnet" "private" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-private-subnet-${count.index + 1}"
      Type = "private"
    }
  )
}

# Elastic IPs for NAT Gateway
resource "aws_eip" "nat" {
  count = var.enable_nat_gateway && var.nat_type == "gateway" ? length(var.availability_zones) : 0

  domain     = "vpc"
  depends_on = [aws_internet_gateway.main]

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-nat-eip-${count.index + 1}"
    }
  )
}

# NAT Gateways
resource "aws_nat_gateway" "main" {
  count = var.enable_nat_gateway && var.nat_type == "gateway" ? length(var.availability_zones) : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  depends_on    = [aws_internet_gateway.main]

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-nat-${count.index + 1}"
    }
  )
}

# ============================================================================
# NAT Instance Resources (used when nat_type = "instance")
# ============================================================================

# Elastic IPs for NAT Instance
resource "aws_eip" "nat_instance" {
  count = var.enable_nat_gateway && var.nat_type == "instance" ? var.nat_instance_count : 0

  domain     = "vpc"
  depends_on = [aws_internet_gateway.main]

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-nat-instance-eip-${count.index + 1}"
    }
  )
}

# EIP Association for NAT Instance
resource "aws_eip_association" "nat_instance" {
  count = var.enable_nat_gateway && var.nat_type == "instance" ? var.nat_instance_count : 0

  instance_id   = aws_instance.nat[count.index].id
  allocation_id = aws_eip.nat_instance[count.index].id
}

# Security Group for NAT Instance
resource "aws_security_group" "nat_instance" {
  count = var.enable_nat_gateway && var.nat_type == "instance" ? 1 : 0

  name        = "${var.project_name}-${var.environment}-nat-instance-sg"
  description = "Security group for NAT Instance"
  vpc_id      = aws_vpc.main.id

  # Allow all traffic from VPC CIDR (for NAT)
  ingress {
    description = "Allow all traffic from VPC for NAT"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  # Allow all outbound traffic
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-nat-instance-sg"
    }
  )
}

# Data source for Amazon Linux 2023 ARM AMI (for NAT Instance)
data "aws_ami" "amazon_linux_2023_arm" {
  count = var.enable_nat_gateway && var.nat_type == "instance" ? 1 : 0

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

# NAT Instance
resource "aws_instance" "nat" {
  count = var.enable_nat_gateway && var.nat_type == "instance" ? var.nat_instance_count : 0

  ami                    = data.aws_ami.amazon_linux_2023_arm[0].id
  instance_type          = var.nat_instance_type
  subnet_id              = aws_subnet.public[count.index].id
  vpc_security_group_ids = [aws_security_group.nat_instance[0].id]
  key_name               = var.nat_instance_key_name
  source_dest_check      = false

  # User data script to enable IP forwarding and NAT
  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -e

    # Enable IP forwarding
    echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
    sysctl -p

    # Get the primary network interface
    INTERFACE=$(ip route | grep default | awk '{print $5}')

    # Configure iptables for NAT
    yum install -y iptables-services
    systemctl enable iptables
    systemctl start iptables

    # Flush existing rules and set up NAT
    iptables -F
    iptables -t nat -F
    iptables -t nat -A POSTROUTING -o $INTERFACE -j MASQUERADE
    iptables -A FORWARD -i $INTERFACE -o $INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i $INTERFACE -o $INTERFACE -j ACCEPT

    # Save iptables rules
    service iptables save

    # Enable iptables to persist across reboots
    systemctl enable iptables
  EOF
  )

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-nat-instance-${count.index + 1}"
    }
  )

  lifecycle {
    ignore_changes = [ami]
  }
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-public-rt"
    }
  )
}

# Private Route Tables
resource "aws_route_table" "private" {
  count = length(var.availability_zones)

  vpc_id = aws_vpc.main.id

  # Route for NAT Gateway (when nat_type = "gateway")
  dynamic "route" {
    for_each = var.enable_nat_gateway && var.nat_type == "gateway" ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.main[count.index].id
    }
  }

  # Route for NAT Instance (when nat_type = "instance")
  dynamic "route" {
    for_each = var.enable_nat_gateway && var.nat_type == "instance" ? [1] : []
    content {
      cidr_block           = "0.0.0.0/0"
      network_interface_id = element(aws_instance.nat[*].primary_network_interface_id, count.index)
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-private-rt-${count.index + 1}"
    }
  )
}

# Public Route Table Associations
resource "aws_route_table_association" "public" {
  count = length(var.availability_zones)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private Route Table Associations
resource "aws_route_table_association" "private" {
  count = length(var.availability_zones)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# VPC Endpoint Security Group (used by Interface endpoints only)
resource "aws_security_group" "vpc_endpoint" {
  count = var.enable_vpc_endpoints && var.enable_vpc_interface_endpoints ? 1 : 0

  name        = "${var.project_name}-${var.environment}-vpc-endpoint-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-vpc-endpoint-sg"
    }
  )
}

# S3 Gateway Endpoint
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_vpc_endpoints ? 1 : 0

  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${data.aws_region.current.id}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat([aws_route_table.public.id], aws_route_table.private[*].id)

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-s3-endpoint"
    }
  )
}

# DynamoDB Gateway Endpoint
resource "aws_vpc_endpoint" "dynamodb" {
  count = var.enable_vpc_endpoints ? 1 : 0

  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${data.aws_region.current.id}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat([aws_route_table.public.id], aws_route_table.private[*].id)

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-dynamodb-endpoint"
    }
  )
}

# ECR Interface Endpoint
resource "aws_vpc_endpoint" "ecr" {
  count = var.enable_vpc_endpoints && var.enable_vpc_interface_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.id}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint[0].id]
  private_dns_enabled = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-ecr-endpoint"
    }
  )
}

# ECR DKR Interface Endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  count = var.enable_vpc_endpoints && var.enable_vpc_interface_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.id}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint[0].id]
  private_dns_enabled = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-ecr-dkr-endpoint"
    }
  )
}

# CloudWatch Logs Interface Endpoint
resource "aws_vpc_endpoint" "cloudwatch_logs" {
  count = var.enable_vpc_endpoints && var.enable_vpc_interface_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.id}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint[0].id]
  private_dns_enabled = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-cloudwatch-logs-endpoint"
    }
  )
}

# Get current region
data "aws_region" "current" {}

# AWS Managed Prefix List for CloudFront origin-facing IPs
data "aws_ec2_managed_prefix_list" "cloudfront" {
  count = var.restrict_alb_to_cloudfront ? 1 : 0
  name  = "com.amazonaws.global.cloudfront.origin-facing"
}

# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  # HTTP ingress - CloudFront only or open to internet
  dynamic "ingress" {
    for_each = var.restrict_alb_to_cloudfront ? [] : [1]
    content {
      description = "HTTP from Internet"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  dynamic "ingress" {
    for_each = var.restrict_alb_to_cloudfront ? [1] : []
    content {
      description     = "HTTP from CloudFront"
      from_port       = 80
      to_port         = 80
      protocol        = "tcp"
      prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront[0].id]
    }
  }

  # HTTPS ingress - CloudFront only or open to internet
  dynamic "ingress" {
    for_each = var.restrict_alb_to_cloudfront ? [] : [1]
    content {
      description = "HTTPS from Internet"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  dynamic "ingress" {
    for_each = var.restrict_alb_to_cloudfront ? [1] : []
    content {
      description     = "HTTPS from CloudFront"
      from_port       = 443
      to_port         = 443
      protocol        = "tcp"
      prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront[0].id]
    }
  }

  ingress {
    description = "Custom TCP 8443 from Internet"
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-alb-sg"
    }
  )
}

# ECS Security Group
resource "aws_security_group" "ecs" {
  name        = "${var.project_name}-${var.environment}-ecs-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow traffic from ALB"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # ECS 서비스 간 내부 통신 (Service Discovery/Cloud Map)
  # 같은 ECS Security Group을 사용하는 태스크끼리 직접 통신할 수 있도록 허용
  ingress {
    description = "Allow inter-task traffic on service-a port (8080) within ECS SG"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    self        = true
  }

  ingress {
    description = "Allow inter-task traffic on service-b port (3000) within ECS SG"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    self        = true
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-ecs-sg"
    }
  )
}

