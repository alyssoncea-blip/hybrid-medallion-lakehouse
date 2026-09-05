###############################################################################
# Snowflake Databases — Hybrid Medallion Lakehouse
#
# One database per layer to enforce least-privilege and per-layer governance.
#  - BRONZE  : raw landing (autoingest / Snowpipe)
#  - SILVER  : cleansed and conformed (dbt)
#  - GOLD    : business marts (BI / ML)
#  - GOVERN  : governance metadata (policies, tags, audit)
#  - ANALYTICS : semantic layer (shared dimensions / metrics)
###############################################################################

locals {
  databases = {
    bronze = {
      name                = "${upper(var.environment)}_HYBRID_LH_BRONZE"
      data_retention_days = 1
      comment             = "Bronze layer — raw landing zone (schema-on-read)"
    }
    silver = {
      name                = "${upper(var.environment)}_HYBRID_LH_SILVER"
      data_retention_days = 7
      comment             = "Silver layer — cleansed, conformed, SCD2"
    }
    gold = {
      name                = "${upper(var.environment)}_HYBRID_LH_GOLD"
      data_retention_days = 90
      comment             = "Gold layer — business marts, ML features"
    }
    govern = {
      name                = "${upper(var.environment)}_HYBRID_LH_GOVERN"
      data_retention_days = 90
      comment             = "Governance metadata (lineage, policies, tags)"
    }
    analytics = {
      name                = "${upper(var.environment)}_HYBRID_LH_ANALYTICS"
      data_retention_days = 90
      comment             = "Semantic layer and certified metrics"
    }
  }
}

resource "snowflake_database" "layer" {
  for_each = local.databases

  name                        = each.value.name
  comment                     = each.value.comment
  data_retention_time_in_days = each.value.data_retention_days
  is_transient                = false

  lifecycle {
    prevent_destroy = true
  }
}

# Schemas per layer (extensible per domain)
resource "snowflake_schema" "bronze" {
  for_each = toset([
    "raw_vendas",
    "raw_estoque",
    "raw_fiscal",
    "raw_crm",
    "raw_erp",
    "raw_apis_externas",
  ])

  database                    = snowflake_database.layer["bronze"].name
  name                        = upper(each.value)
  comment                     = "Bronze raw landing for ${each.value}"
  is_transient                = true
  data_retention_time_in_days = 1

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_schema" "silver" {
  for_each = toset([
    "vendas",
    "estoque",
    "fiscal",
    "cliente",
    "produto",
    "fornecedor",
    "financeiro",
  ])

  database                    = snowflake_database.layer["silver"].name
  name                        = upper(each.value)
  comment                     = "Silver cleansed and conformed data for ${each.value}"
  data_retention_time_in_days = 7

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_schema" "gold" {
  for_each = toset([
    "vendas",
    "estoque",
    "fiscal",
    "cliente",
    "produto",
    "fornecedor",
    "financeiro",
  ])

  database                    = snowflake_database.layer["gold"].name
  name                        = upper(each.value)
  comment                     = "Gold business marts for ${each.value}"
  data_retention_time_in_days = 90

  lifecycle {
    prevent_destroy = true
  }
}
