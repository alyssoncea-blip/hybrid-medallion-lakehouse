terraform {
  required_version = ">= 1.7.0"

  required_providers {
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.92"
    }
  }
}

# Module-level variables (provider is configured in the calling environment)

variable "environment" {
  type        = string
  description = "Environment name: dev, stg, or prd."
  validation {
    condition     = contains(["dev", "stg", "prd"], var.environment)
    error_message = "Environment must be dev, stg, or prd."
  }
}

variable "notification_users" {
  type        = list(string)
  description = "Snowflake users notified by resource monitors."
  default     = []
}

variable "data_classification_default" {
  type        = string
  description = "Default classification tag applied to untagged tables."
  default     = "interno"
  validation {
    condition     = contains(["publico", "interno", "confidencial", "restrito"], var.data_classification_default)
    error_message = "Must be one of: publico, interno, confidencial, restrito."
  }
}
