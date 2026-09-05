###############################################################################
# Snowflake Warehouse — Hybrid Medallion Lakehouse
#
# Creates:
#   - One warehouse per workload type (ingest, transform, bi, ml, admin)
#   - Resource monitors per warehouse (notify at thresholds, suspend at 100)
#   - Auto-suspend / auto-resume policy aligned to FinOps guidance
###############################################################################

locals {
  warehouses = {
    ingest = {
      name           = "${upper(var.environment)}_HYBRID_LH_INGEST_WH"
      size           = "XSMALL"
      auto_suspend   = 60
      auto_resume    = true
      min_clusters   = 1
      max_clusters   = var.environment == "prd" ? 3 : 1
      scaling_policy = "ECONOMY"
      comment        = "Bronze ingestion workloads (Snowpipe, COPY INTO)"
    }
    transform = {
      name           = "${upper(var.environment)}_HYBRID_LH_TRANSFORM_WH"
      size           = var.environment == "prd" ? "MEDIUM" : "SMALL"
      auto_suspend   = 60
      auto_resume    = true
      min_clusters   = 1
      max_clusters   = var.environment == "prd" ? 4 : 1
      scaling_policy = "STANDARD"
      comment        = "dbt Silver/Gold transformations"
    }
    bi = {
      name           = "${upper(var.environment)}_HYBRID_LH_BI_WH"
      size           = var.environment == "prd" ? "MEDIUM" : "XSMALL"
      auto_suspend   = 60
      auto_resume    = true
      min_clusters   = 1
      max_clusters   = var.environment == "prd" ? 4 : 1
      scaling_policy = "STANDARD"
      comment        = "BI consumers (Power BI, Tableau)"
    }
    ml = {
      name           = "${upper(var.environment)}_HYBRID_LH_ML_WH"
      size           = var.environment == "prd" ? "LARGE" : "MEDIUM"
      auto_suspend   = 120
      auto_resume    = true
      min_clusters   = 1
      max_clusters   = var.environment == "prd" ? 2 : 1
      scaling_policy = "ECONOMY"
      comment        = "ML feature engineering and Snowpark workloads"
    }
    admin = {
      name           = "${upper(var.environment)}_HYBRID_LH_ADMIN_WH"
      size           = "XSMALL"
      auto_suspend   = 30
      auto_resume    = true
      min_clusters   = 1
      max_clusters   = 1
      scaling_policy = "ECONOMY"
      comment        = "Administrative queries (DDL, grants, monitoring)"
    }
  }

  budget_per_warehouse = {
    ingest    = var.environment == "prd" ? 800 : 200
    transform = var.environment == "prd" ? 3500 : 600
    bi        = var.environment == "prd" ? 2500 : 400
    ml        = var.environment == "prd" ? 4000 : 800
    admin     = var.environment == "prd" ? 200 : 50
  }
}

resource "snowflake_warehouse" "wh" {
  for_each = local.warehouses

  name                = each.value.name
  warehouse_size      = each.value.size
  auto_suspend        = each.value.auto_suspend
  auto_resume         = each.value.auto_resume
  min_cluster_count   = each.value.min_clusters
  max_cluster_count   = each.value.max_clusters
  scaling_policy      = each.value.scaling_policy
  comment             = each.value.comment
  resource_monitor    = snowflake_resource_monitor.wh_monitor[each.key].name
  initially_suspended = false
}

resource "snowflake_resource_monitor" "wh_monitor" {
  for_each = local.warehouses

  name            = "RM_${upper(var.environment)}_HYBRID_LH_${upper(each.key)}"
  credit_quota    = local.budget_per_warehouse[each.key]
  frequency       = "MONTHLY"
  start_timestamp = "IMMEDIATELY"

  notify_users    = var.notification_users
  notify_triggers = [50, 75, 90]
  suspend_trigger = 100
}
