output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = var.enable_nat_gateway && var.nat_type == "gateway" ? aws_nat_gateway.main[*].id : []
}

output "nat_instance_ids" {
  description = "List of NAT Instance IDs"
  value       = var.enable_nat_gateway && var.nat_type == "instance" ? aws_instance.nat[*].id : []
}

output "nat_instance_public_ips" {
  description = "List of NAT Instance public IPs"
  value       = var.enable_nat_gateway && var.nat_type == "instance" ? aws_eip.nat_instance[*].public_ip : []
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ID of the ECS security group"
  value       = aws_security_group.ecs.id
}

output "vpc_endpoint_ids" {
  description = "Map of VPC endpoint IDs"
  value = merge(
    var.enable_vpc_endpoints ? {
      s3       = aws_vpc_endpoint.s3[0].id
      dynamodb = aws_vpc_endpoint.dynamodb[0].id
    } : {},
    var.enable_vpc_endpoints && var.enable_vpc_interface_endpoints ? {
      ecr             = aws_vpc_endpoint.ecr[0].id
      ecr_dkr         = aws_vpc_endpoint.ecr_dkr[0].id
      cloudwatch_logs = aws_vpc_endpoint.cloudwatch_logs[0].id
    } : {}
  )
}

output "vpc_endpoint_security_group_id" {
  description = "ID of the VPC endpoint security group"
  value       = var.enable_vpc_endpoints && var.enable_vpc_interface_endpoints ? aws_security_group.vpc_endpoint[0].id : null
}

