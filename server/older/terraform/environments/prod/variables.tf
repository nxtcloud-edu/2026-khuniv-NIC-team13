variable "terraform_cloud_organization" {
  description = "Terraform Cloud organization name"
  type        = string
  default     = "pertino-org"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.terraform_cloud_organization))
    error_message = "Organization name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "terraform_cloud_workspace" {
  description = "Terraform Cloud workspace name for prod environment"
  type        = string
  default     = "pertino-prod"

  validation {
    condition     = can(regex("^[a-z0-9-_]+$", var.terraform_cloud_workspace))
    error_message = "Workspace name must contain only lowercase letters, numbers, hyphens, and underscores."
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "pertino"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Environment must be either 'dev' or 'prod'."
  }
}

variable "domain_name" {
  description = "Domain name for Route53 and CloudFront"
  type        = string
  default     = ""

  validation {
    condition     = var.domain_name == "" || can(regex("^[a-z0-9.-]+$", var.domain_name))
    error_message = "Domain name must be a valid domain format."
  }
}

variable "alb_certificate_arn" {
  description = "ACM certificate ARN for ALB HTTPS listener (used when domain_name is empty)"
  type        = string
  default     = "arn:aws:acm:ap-northeast-2:055292472277:certificate/3a11b79c-e3bd-4e01-b968-7920225dfa42"
}

variable "create_hosted_zone" {
  description = "Create a new Route53 Hosted Zone. Set to false if using an existing zone."
  type        = bool
  default     = true
}

variable "existing_hosted_zone_id" {
  description = "Existing Route53 Hosted Zone ID (required if create_hosted_zone is false)"
  type        = string
  default     = ""
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = true
}

variable "enable_vpc_interface_endpoints" {
  description = "Enable VPC Interface endpoints (ECR, CloudWatch). When false, uses NAT instance."
  type        = bool
  default     = false
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "restrict_alb_to_cloudfront" {
  description = "Restrict ALB access to CloudFront only. When true, direct ALB access is blocked for security."
  type        = bool
  default     = false
}
