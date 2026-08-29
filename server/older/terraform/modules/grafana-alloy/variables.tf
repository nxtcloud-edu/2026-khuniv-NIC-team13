variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Environment must be either 'dev' or 'prod'."
  }
}

variable "cluster_id" {
  description = "ECS cluster ID to deploy Alloy into"
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet IDs for the Alloy ECS tasks"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for the Alloy ECS tasks"
  type        = list(string)
}

# Grafana Cloud Secrets Manager ARNs
variable "grafana_cloud_secret_arns" {
  description = "ARNs of Secrets Manager secrets for Grafana Cloud configuration"
  type = object({
    prometheus_endpoint = string
    prometheus_username = string
    api_key             = string
  })
}

# Scrape Targets
variable "scrape_targets" {
  description = "List of Prometheus scrape targets for Alloy to collect metrics from"
  type = list(object({
    name            = string
    address         = string
    metrics_path    = optional(string, "/actuator/prometheus")
    scrape_interval = optional(string, "5s")
  }))
}

# ECS Task Configuration
variable "desired_count" {
  description = "Number of Alloy tasks to run"
  type        = number
  default     = 1
}

variable "cpu" {
  description = "CPU units for the Alloy task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory (MiB) for the Alloy task"
  type        = number
  default     = 512
}

variable "alloy_image" {
  description = "Grafana Alloy container image (pin to a specific version for production)"
  type        = string
  default     = "grafana/alloy:v1.14.0"
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
