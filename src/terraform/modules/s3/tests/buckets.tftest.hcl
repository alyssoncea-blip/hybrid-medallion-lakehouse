mock_provider "aws" {
  mock_resource "aws_s3_bucket" {
    defaults = {
      id = "hybrid-lakehouse-dev-bronze"
    }
  }
  mock_resource "aws_s3_bucket_versioning" {
    defaults = { id = "mock" }
  }
  mock_resource "aws_s3_bucket_server_side_encryption_configuration" {
    defaults = { id = "mock" }
  }
  mock_resource "aws_s3_bucket_public_access_block" {
    defaults = { id = "mock" }
  }
  mock_resource "aws_s3_bucket_lifecycle_configuration" {
    defaults = { id = "mock" }
  }
  mock_resource "aws_kms_key" {
    defaults = {
      id  = "arn:aws:kms:sa-east-1:111111111111:key/mock"
      arn = "arn:aws:kms:sa-east-1:111111111111:key/mock"
    }
  }
  mock_resource "aws_kms_alias" {
    defaults = { id = "mock" }
  }
}

variables {
  environment = "dev"
}

run "creates_three_buckets" {
  command = plan

  assert {
    condition     = output.bronze_bucket == "hybrid-lakehouse-dev-bronze"
    error_message = "Bronze bucket name should be hybrid-lakehouse-dev-bronze"
  }

  assert {
    condition     = output.silver_bucket == "hybrid-lakehouse-dev-silver"
    error_message = "Silver bucket name should be hybrid-lakehouse-dev-silver"
  }

  assert {
    condition     = output.gold_bucket == "hybrid-lakehouse-dev-gold"
    error_message = "Gold bucket name should be hybrid-lakehouse-dev-gold"
  }
}
