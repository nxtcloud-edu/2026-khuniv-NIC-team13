variable "table_name" {
  description = "Name of the DynamoDB table"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_.-]+$", var.table_name))
    error_message = "Table name must contain only alphanumeric characters, hyphens, underscores, and periods."
  }
}

variable "hash_key" {
  description = "Attribute to use as the hash (partition) key"
  type        = string
}

variable "hash_key_type" {
  description = "Attribute type for the hash key (S, N, or B)"
  type        = string
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.hash_key_type)
    error_message = "Hash key type must be 'S' (String), 'N' (Number), or 'B' (Binary)."
  }
}

variable "range_key" {
  description = "Attribute to use as the range (sort) key (optional)"
  type        = string
  default     = ""
}

variable "range_key_type" {
  description = "Attribute type for the range key (S, N, or B)"
  type        = string
  default     = "S"

  validation {
    condition     = var.range_key == "" || contains(["S", "N", "B"], var.range_key_type)
    error_message = "Range key type must be 'S' (String), 'N' (Number), or 'B' (Binary)."
  }
}

variable "enable_point_in_time_recovery" {
  description = "Enable Point-in-time Recovery"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable server-side encryption"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (optional, uses AWS managed key if not provided)"
  type        = string
  default     = null
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

variable "ttl_attribute" {
  description = "Name of the attribute to use for TTL (Time To Live). If null, TTL is disabled."
  type        = string
  default     = null
}

variable "global_secondary_indexes" {
  description = "Global secondary indexes (empty range_key if sort key not used)"
  type = list(object({
    name            = string
    hash_key        = string
    hash_key_type   = string
    range_key       = string
    range_key_type  = string
    projection_type = string
  }))
  default = []
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

