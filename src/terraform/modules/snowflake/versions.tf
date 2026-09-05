terraform {
  required_version = ">= 1.7.0"

  required_providers {
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.92"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

provider "snowflake" {
  account  = var.snowflake_account
  user     = var.snowflake_user
  role     = var.snowflake_role
  region   = var.snowflake_region
  authenticator = var.snowflake_authenticator

  preview_features_enabled = [
    "snowflake_table_resource",
    "snowflake_external_table_resource",
    "snowflake_dynamic_table_resource",
    "snowflake_stream_resource",
    "snowflake_task_resource",
  ]
}

provider "aws" {
  region = var.aws_region
  profile = var.aws_profile
}

variable "snowflake_account" {
  type        = string
  description = "Snowflake account identifier (e.g., acme.sa-east-1)."
  sensitive   = false
}

variable "snowflake_user" {
  type        = string
  description = "Snowflake user used by Terraform (service user with SYSADMIN scoped privileges)."
}

variable "snowflake_role" {
  type        = string
  description = "Snowflake role assumed by Terraform (e.g., SECURITYADMIN for grants, SYSADMIN for objects)."
  default     = "SECURITYADMIN"
}

variable "snowflake_region" {
  type        = string
  description = "Snowflake region (must match account)."
  default     = "AWS_SA_EAST_1"
}

variable "snowflake_authenticator" {
  type        = string
  description = "Authenticator: externalbrowser, jwt, password, or snowflake."
  default     = "externalbrowser"
}

variable "aws_region" {
  type        = string
  description = "AWS region for object storage buckets."
  default     = "sa-east-1"
}

variable "aws_profile" {
  type        = string
  description = "AWS CLI profile used by Terraform."
  default     = "default"
}

variable "environment" {
  type        = string
  description = "Environment name: dev, stg, prd."
  validation {
    condition     = contains(["dev", "stg", "prd"], var.environment)
    error_message = "Environment must be dev, stg, or prd."
  }
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
