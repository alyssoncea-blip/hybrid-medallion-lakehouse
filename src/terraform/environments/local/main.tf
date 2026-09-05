###############################################################################
# Terraform — Environment: local
#
# Aplica o módulo snowflake/s3 contra o LocalStack rodando em localhost:4566.
# Custo: R$ 0 (LocalStack Community Edition).
#
# Pré-requisitos:
#   1. Docker Desktop rodando
#   2. docker compose up -d (sobe LocalStack com S3, KMS, SQS)
#   3. aws cli instalado e configurado com dummy credentials
#
# Uso:
#   cd src/terraform/environments/local
#   terraform init
#   terraform plan
#   terraform apply
###############################################################################

terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

provider "aws" {
  region                      = "sa-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3  = "http://localhost:4566"
    sts = "http://localhost:4566"
    kms = "http://localhost:4566"
  }
}

variable "environment" {
  type    = string
  default = "local"
}

variable "force_destroy" {
  type    = bool
  default = true # local: permitir destroy com objetos
}

module "s3" {
  source = "../../modules/s3"

  environment   = var.environment
  force_destroy = var.force_destroy
  # local: desabilitar lifecycle (LocalStack tem limitações em lifecycle rules)
  bronze_lifecycle_transition_days = 365
  bronze_lifecycle_glacier_days    = 730
}

output "local_buckets" {
  description = "Bucket names created in LocalStack for the local environment."
  value = {
    bronze = module.s3.bronze_bucket
    silver = module.s3.silver_bucket
    gold   = module.s3.gold_bucket
  }
}
