terraform {
  required_version = ">= 1.7.0"
  required_providers {
    snowflake = { source = "Snowflake-Labs/snowflake", version = "~> 0.92" }
    aws       = { source = "hashicorp/aws",             version = "~> 5.40" }
  }
}

provider "snowflake" {
  account  = var.snowflake_account
  user     = var.snowflake_user
  role     = var.snowflake_role
  region   = var.snowflake_region
  authenticator = var.snowflake_authenticator
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

variable "snowflake_account"           { type = string }
variable "snowflake_user"              { type = string }
variable "snowflake_role"              { type = string, default = "SECURITYADMIN" }
variable "snowflake_region"            { type = string, default = "AWS_SA_EAST_1" }
variable "snowflake_authenticator"     { type = string, default = "externalbrowser" }
variable "aws_region"                  { type = string, default = "sa-east-1" }
variable "aws_profile"                 { type = string, default = "default" }
variable "notification_users"          { type = list(string), default = [] }
variable "data_classification_default" { type = string, default = "interno" }

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
