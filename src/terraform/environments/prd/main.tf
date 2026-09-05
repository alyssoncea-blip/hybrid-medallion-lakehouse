terraform {
  required_version = ">= 1.7.0"
  required_providers {
    snowflake = { source = "Snowflake-Labs/snowflake", version = "~> 0.92" }
    aws       = { source = "hashicorp/aws", version = "~> 5.40" }
  }
}

provider "snowflake" {
  account       = var.snowflake_account
  user          = var.snowflake_user
  role          = var.snowflake_role
  region        = var.snowflake_region
  authenticator = var.snowflake_authenticator
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

variable "snowflake_account" {
  type        = string
  description = "Snowflake account identifier (e.g., acme.sa-east-1)."
}

variable "snowflake_user" {
  type        = string
  description = "Snowflake service user used by Terraform."
}

variable "snowflake_role" {
  type        = string
  description = "Snowflake role assumed by Terraform."
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

variable "notification_users" {
  type        = list(string)
  description = "Snowflake users notified by resource monitors."
  default     = ["data-governance@hybrid-lakehouse.local"]
}

variable "data_classification_default" {
  type        = string
  description = "Default classification tag applied to untagged tables."
  default     = "confidencial"
  validation {
    condition     = contains(["publico", "interno", "confidencial", "restrito"], var.data_classification_default)
    error_message = "Must be one of: publico, interno, confidencial, restrito."
  }
}

variable "environment" {
  type        = string
  description = "dev, stg, or prd"
  validation {
    condition     = contains(["dev", "stg", "prd"], var.environment)
    error_message = "Environment must be dev, stg, or prd."
  }
}

module "snowflake" {
  source = "../../modules/snowflake"

  environment                 = var.environment
  notification_users          = var.notification_users
  data_classification_default = var.data_classification_default
}

module "s3" {
  source = "../../modules/s3"

  environment = var.environment
}
