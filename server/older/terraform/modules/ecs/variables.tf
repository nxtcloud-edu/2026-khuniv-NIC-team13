variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
  default     = "pertino-cluster"
}

variable "service_a_config" {
  description = "Configuration for Service A (Spring Boot)"
  type = object({
    name             = string
    image            = string
    cpu              = number
    memory           = number
    desired_count    = number
    port             = number
    environment_vars = map(string)
    secrets          = map(string)
  })
  default = {
    name             = "service-a"
    image            = ""
    cpu              = 256
    memory           = 512
    desired_count    = 1
    port             = 8080
    environment_vars = {}
    secrets          = {}
  }
}

variable "service_b_config" {
  description = "Configuration for Service B (FastAPI/LangChain)"
  type = object({
    name             = string
    image            = string
    cpu              = number
    memory           = number
    desired_count    = number
    port             = number
    environment_vars = map(string)
    secrets          = map(string)
  })
  default = {
    name             = "service-b"
    image            = ""
    cpu              = 256
    memory           = 1024
    desired_count    = 1
    port             = 3000
    environment_vars = {}
    secrets          = {}
  }
}

variable "service_discovery_namespace_id" {
  description = "Service Discovery namespace ID from VPC module"
  type        = string
}

variable "subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for ECS tasks"
  type        = list(string)
}

variable "dynamodb_table_arns" {
  description = "List of DynamoDB table ARNs for Task Role policy"
  type        = list(string)
  default     = []
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs for Task Role policy"
  type        = list(string)
  default     = []
}

variable "s3_vector_bucket_arns" {
  description = "List of S3 Vectors bucket ARNs for Task Role policy"
  type        = list(string)
  default     = []
}

variable "ecr_repository_urls" {
  description = "Map of ECR repository URLs"
  type        = map(string)
  default     = {}
}

variable "task_execution_role_arn" {
  description = "ARN of existing Task Execution Role (optional, will create if not provided)"
  type        = string
  default     = ""
}

variable "task_role_arn" {
  description = "ARN of existing Task Role (optional, will create if not provided)"
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

variable "service_a_target_group_arn" {
  description = "ARN of the ALB target group for Service A (optional)"
  type        = string
  default     = ""
}

variable "service_b_target_group_arn" {
  description = "ARN of the ALB target group for Service B (optional)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Blue/Green Deployment Variables
variable "enable_blue_green" {
  description = "Enable blue/green deployment with CodeDeploy for Service A"
  type        = bool
  default     = false
}

# Auto Scaling Variables
variable "service_a_autoscaling" {
  description = "Auto scaling configuration for Service A"
  type = object({
    min_capacity = number
    max_capacity = number
  })
  default = {
    min_capacity = 1
    max_capacity = 4
  }
}

variable "service_b_autoscaling" {
  description = "Auto scaling configuration for Service B"
  type = object({
    min_capacity = number
    max_capacity = number
  })
  default = {
    min_capacity = 1
    max_capacity = 4
  }
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix for ALBRequestCountPerTarget auto scaling metric"
  type        = string
  default     = ""
}

variable "service_a_target_group_arn_suffix" {
  description = "Target group ARN suffix for ALBRequestCountPerTarget auto scaling metric"
  type        = string
  default     = ""
}

variable "blue_green_config" {
  description = "Configuration for blue/green deployment"
  type = object({
    # ALB listener ARNs
    prod_listener_arn = string
    test_listener_arn = string
    # Target group names (not ARNs - CodeDeploy needs names)
    blue_target_group_name  = string
    green_target_group_name = string
    # Deployment configuration
    deployment_config_name = optional(string, "CodeDeployDefault.ECSAllAtOnce")
    # Termination wait time in minutes (0-120)
    termination_wait_time_in_minutes = optional(number, 5)
  })
  default = {
    prod_listener_arn                = ""
    test_listener_arn                = ""
    blue_target_group_name           = ""
    green_target_group_name          = ""
    deployment_config_name           = "CodeDeployDefault.ECSAllAtOnce"
    termination_wait_time_in_minutes = 5
  }
}
