variable "name" {
  description = "Name of the Application Load Balancer"
  type        = string
  default     = "pertino-alb"
}

variable "subnet_ids" {
  description = "List of public subnet IDs for ALB"
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnets are required for ALB."
  }
}

variable "security_group_id" {
  description = "Security Group ID for ALB"
  type        = string
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate for HTTPS"
  type        = string
  default     = ""
}

variable "service_a_target_group_config" {
  description = "Configuration for Service A target group"
  type = object({
    port                  = number
    protocol              = string
    health_check_path     = string
    health_check_port     = number
    health_check_protocol = string
    healthy_threshold     = optional(number, 2)
    unhealthy_threshold   = optional(number, 2)
    timeout               = optional(number, 5)
    interval              = optional(number, 30)
    matcher               = optional(string, "200")
  })
  default = {
    port                  = 8080
    protocol              = "HTTP"
    health_check_path     = "/health"
    health_check_port     = 8080
    health_check_protocol = "HTTP"
    healthy_threshold     = 2
    unhealthy_threshold   = 2
    timeout               = 5
    interval              = 30
    matcher               = "200"
  }
}

variable "enable_http_redirect" {
  description = "Enable HTTP to HTTPS redirect"
  type        = bool
  default     = true
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

variable "idle_timeout" {
  description = "The time in seconds that the connection is allowed to be idle"
  type        = number
  default     = 60
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for ALB"
  type        = bool
  default     = false
}

# Blue/Green Deployment Variables
variable "enable_blue_green" {
  description = "Enable blue/green deployment (creates green target group and test listener)"
  type        = bool
  default     = false
}

variable "test_listener_port" {
  description = "Port for test traffic listener (used for green environment validation)"
  type        = number
  default     = 8443
}