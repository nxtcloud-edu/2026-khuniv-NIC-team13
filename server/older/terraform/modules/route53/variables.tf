variable "domain_name" {
  description = "Domain name for Route53 Hosted Zone"
  type        = string
  default     = ""

  validation {
    condition     = var.domain_name == "" || can(regex("^([a-z0-9]+(-[a-z0-9]+)*\\.)+[a-z]{2,}$", var.domain_name))
    error_message = "Domain name must be a valid domain format or empty."
  }
}

variable "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  type        = string
}

variable "create_hosted_zone" {
  description = "Create a new Route53 Hosted Zone"
  type        = bool
  default     = true
}

variable "existing_hosted_zone_id" {
  description = "Existing Hosted Zone ID (if create_hosted_zone is false)"
  type        = string
  default     = ""
}

variable "create_acm_certificate" {
  description = "Create ACM certificate for CloudFront"
  type        = bool
  default     = true
}

variable "acm_certificate_arn" {
  description = "Existing ACM certificate ARN (if create_acm_certificate is false)"
  type        = string
  default     = ""
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

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

