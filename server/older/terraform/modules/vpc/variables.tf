variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2b"]

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones are required."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "pertino"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Environment must be either 'dev' or 'prod'."
  }
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets (deprecated: use nat_type instead)"
  type        = bool
  default     = true
}

variable "nat_type" {
  description = "Type of NAT to use: 'gateway' for NAT Gateway, 'instance' for NAT Instance"
  type        = string
  default     = "gateway"

  validation {
    condition     = contains(["gateway", "instance"], var.nat_type)
    error_message = "nat_type must be either 'gateway' or 'instance'."
  }
}

variable "nat_instance_type" {
  description = "EC2 instance type for NAT Instance (only used when nat_type = 'instance')"
  type        = string
  default     = "t4g.nano"
}

variable "nat_instance_count" {
  description = "Number of NAT Instances to create when nat_type = 'instance'. Set to 1 for cost-optimized single-NAT routing across private subnets."
  type        = number
  default     = 1

  validation {
    condition     = var.nat_instance_count >= 1 && floor(var.nat_instance_count) == var.nat_instance_count
    error_message = "nat_instance_count must be a positive integer."
  }
}

variable "nat_instance_key_name" {
  description = "SSH key pair name for NAT Instance (optional, for debugging)"
  type        = string
  default     = null
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = true
}

variable "enable_vpc_interface_endpoints" {
  description = "Enable VPC Interface endpoints (ECR, ECR DKR, CloudWatch Logs). When false, traffic routes through NAT."
  type        = bool
  default     = true
}

variable "restrict_alb_to_cloudfront" {
  description = "Restrict ALB ingress to CloudFront only using AWS managed prefix list. When true, direct ALB access is blocked."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

