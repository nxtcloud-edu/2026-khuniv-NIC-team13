variable "repository_names" {
  description = "List of ECR repository names"
  type        = list(string)
  default     = ["pertino-service-a", "pertino-service-b"]

  validation {
    condition     = length(var.repository_names) > 0
    error_message = "At least one repository name is required."
  }
}

variable "image_tag_mutability" {
  description = "The tag mutability setting for the repository (MUTABLE or IMMUTABLE)"
  type        = string
  default     = "MUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "Image tag mutability must be either 'MUTABLE' or 'IMMUTABLE'."
  }
}

variable "scan_on_push" {
  description = "Indicates whether images are scanned after being pushed to the repository"
  type        = bool
  default     = true
}

variable "max_image_count" {
  description = "Maximum number of images to keep in the repository"
  type        = number
  default     = 10

  validation {
    condition     = var.max_image_count > 0
    error_message = "Max image count must be greater than 0."
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

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

