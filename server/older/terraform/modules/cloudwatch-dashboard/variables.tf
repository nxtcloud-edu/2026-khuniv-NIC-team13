# CloudWatch Dashboard Module - Variables

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

variable "dashboard_name" {
  description = "Name of the CloudWatch Dashboard"
  type        = string
  default     = "Pertineo-monitor"
}

variable "region" {
  description = "AWS region for the dashboard"
  type        = string
  default     = "ap-northeast-2"
}

# ECS Configuration
variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "service_a_name" {
  description = "Name of ECS Service A"
  type        = string
  default     = "service-a"
}

variable "service_b_name" {
  description = "Name of ECS Service B"
  type        = string
  default     = "service-b"
}

# ALB Configuration
variable "alb_arn_suffix" {
  description = "ARN suffix of the Application Load Balancer (after app/)"
  type        = string
}

variable "target_group_arn_suffix" {
  description = "ARN suffix of the Target Group for Service A (after targetgroup/)"
  type        = string
}

# DynamoDB Configuration
variable "dynamodb_table_names" {
  description = "List of DynamoDB table names to monitor"
  type        = list(string)
  default     = []
}

# CloudWatch Logs Configuration
variable "service_a_log_group" {
  description = "CloudWatch Log Group name for Service A"
  type        = string
}

variable "service_b_log_group" {
  description = "CloudWatch Log Group name for Service B"
  type        = string
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
