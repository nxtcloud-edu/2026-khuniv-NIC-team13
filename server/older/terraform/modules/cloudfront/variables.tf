variable "aliases" {
  description = "List of aliases (domains) for the CloudFront distribution"
  type        = list(string)
  default     = []
}

variable "s3_origin_config" {
  description = "S3 origin configuration"
  type = object({
    bucket_regional_domain_name = string
    bucket_id                   = string
    oac_id                      = string
  })
}

variable "alb_origin_config" {
  description = "ALB origin configuration"
  type = object({
    alb_dns_name = string
    alb_zone_id  = string
  })
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate for HTTPS"
  type        = string
  default     = ""
}

variable "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL to associate with CloudFront (WAFv2 requires ARN, not ID)"
  type        = string
  default     = ""
}

variable "price_class" {
  description = "Price class for CloudFront distribution"
  type        = string
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_All", "PriceClass_200", "PriceClass_100"], var.price_class)
    error_message = "Price class must be one of: PriceClass_All, PriceClass_200, PriceClass_100."
  }
}

variable "enable_logging" {
  description = "Enable CloudFront logging"
  type        = bool
  default     = false
}

variable "log_bucket" {
  description = "S3 bucket for CloudFront logs"
  type        = string
  default     = ""
}

variable "log_prefix" {
  description = "Prefix for CloudFront log files"
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

