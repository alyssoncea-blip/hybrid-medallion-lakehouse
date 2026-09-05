###############################################################################
# Output — useful values for downstream pipelines (dbt, ingestion, CI)
###############################################################################

output "warehouse_names" {
  description = "Map of workload → warehouse name."
  value = {
    for k, w in snowflake_warehouse.wh : k => w.name
  }
}

output "database_names" {
  description = "Map of layer → database name."
  value = {
    for k, d in snowflake_database.layer : k => d.name
  }
}

output "role_names" {
  description = "Map of purpose → role name."
  value = {
    for k, r in snowflake_account_role.platform_roles : k => r.name
  }
}

output "domain_reader_roles" {
  description = "Map of domain → reader role name."
  value = {
    for k, r in snowflake_account_role.domain_reader : k => r.name
  }
}

output "resource_monitor_names" {
  description = "Map of workload → resource monitor name."
  value = {
    for k, m in snowflake_resource_monitor.wh_monitor : k => m.name
  }
}
