terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.40" }
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

variable "bronze_lifecycle_transition_days" {
  type        = number
  description = "Days before Bronze objects move to Standard-IA."
  default     = 30
}

variable "bronze_lifecycle_glacier_days" {
  type        = number
  description = "Days before Bronze objects move to Glacier."
  default     = 90
}

variable "force_destroy" {
  type        = bool
  description = "Allow Terraform to destroy buckets with objects (dev only)."
  default     = false
}

resource "aws_s3_bucket" "bronze" {
  bucket        = "hybrid-lakehouse-${var.environment}-bronze"
  force_destroy = var.force_destroy
  tags = {
    environment = var.environment
    layer       = "bronze"
    project     = "hybrid-medallion-lakehouse"
    managed_by  = "terraform"
  }
}

resource "aws_s3_bucket" "silver" {
  bucket        = "hybrid-lakehouse-${var.environment}-silver"
  force_destroy = var.force_destroy
  tags = {
    environment = var.environment
    layer       = "silver"
    project     = "hybrid-medallion-lakehouse"
    managed_by  = "terraform"
  }
}

resource "aws_s3_bucket" "gold" {
  bucket        = "hybrid-lakehouse-${var.environment}-gold"
  force_destroy = var.force_destroy
  tags = {
    environment = var.environment
    layer       = "gold"
    project     = "hybrid-medallion-lakehouse"
    managed_by  = "terraform"
  }
}

# Versioning + encryption on all buckets
resource "aws_s3_bucket_versioning" "all" {
  for_each = {
    bronze = aws_s3_bucket.bronze
    silver = aws_s3_bucket.silver
    gold   = aws_s3_bucket.gold
  }
  bucket = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = {
    bronze = aws_s3_bucket.bronze
    silver = aws_s3_bucket.silver
    gold   = aws_s3_bucket.gold
  }
  bucket = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each = {
    bronze = aws_s3_bucket.bronze
    silver = aws_s3_bucket.silver
    gold   = aws_s3_bucket.gold
  }
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle: move to Standard-IA then Glacier (Bronze only by default)
resource "aws_s3_bucket_lifecycle_configuration" "bronze" {
  bucket = aws_s3_bucket.bronze.id
  rule {
    id     = "tiered-storage"
    status = "Enabled"
    transition {
      days          = var.bronze_lifecycle_transition_days
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = var.bronze_lifecycle_glacier_days
      storage_class = "GLACIER_IR"
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# KMS key (per environment)
resource "aws_kms_key" "data" {
  description             = "KMS key for Hybrid Medallion Lakehouse ${var.environment}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = false
  tags = {
    environment = var.environment
    project     = "hybrid-medallion-lakehouse"
  }
}

resource "aws_kms_alias" "data" {
  name          = "alias/hybrid-lakehouse-${var.environment}-data"
  target_key_id = aws_kms_key.data.key_id
}

output "bronze_bucket" { value = aws_s3_bucket.bronze.bucket }
output "silver_bucket" { value = aws_s3_bucket.silver.bucket }
output "gold_bucket"   { value = aws_s3_bucket.gold.bucket }
output "kms_key_arn"   { value = aws_kms_key.data.arn }
