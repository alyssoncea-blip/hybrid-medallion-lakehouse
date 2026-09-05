###############################################################################
# Snowflake RBAC — Role Hierarchy (least privilege)
#
#   SYSADMIN (built-in)
#     └── <ENV>_HYBRID_LH_ADMIN
#           ├── <ENV>_HYBRID_LH_INGEST_ROLE
#           ├── <ENV>_HYBRID_LH_TRANSFORM_ROLE
#           ├── <ENV>_HYBRID_LH_BI_READER_ROLE
#           ├── <ENV>_HYBRID_LH_ML_ROLE
#           ├── <ENV>_HYBRID_LH_AUDITOR_ROLE
#           └── <ENV>_HYBRID_LH_DOMAIN_<X>_READER (per domain)
#
# Uses snowflake_grant_privileges_to_account_role (provider 0.100+).
###############################################################################

locals {
  domain_roles = toset([
    "vendas", "estoque", "fiscal", "cliente",
    "produto", "fornecedor", "financeiro",
  ])

  env_prefix = upper(var.environment)

  # Pre-compute fully qualified schema names for the cross-product grants,
  # so HCL string interpolation does not fight with the ternary operator.
  transform_target_schemas = {
    for pair in setproduct(keys(snowflake_schema.silver), keys(snowflake_schema.gold)) :
    "${pair[0]}.${pair[1]}" => pair[0] == "silver" ? "${snowflake_database.layer["silver"].name}.${snowflake_schema.silver[pair[1]].name}" : "${snowflake_database.layer["gold"].name}.${snowflake_schema.gold[pair[1]].name}"
  }
}

resource "snowflake_account_role" "platform_roles" {
  for_each = toset([
    "HYBRID_LH_ADMIN",
    "HYBRID_LH_INGEST_ROLE",
    "HYBRID_LH_TRANSFORM_ROLE",
    "HYBRID_LH_BI_READER_ROLE",
    "HYBRID_LH_ML_ROLE",
    "HYBRID_LH_AUDITOR_ROLE",
  ])

  name    = "${local.env_prefix}_${each.value}"
  comment = "Platform role: ${each.value} (${var.environment})"
}

resource "snowflake_account_role" "domain_reader" {
  for_each = local.domain_roles

  name    = "${local.env_prefix}_HYBRID_LH_DOMAIN_${upper(each.key)}_READER"
  comment = "Read-only role for the ${each.key} domain (${var.environment})"
}

# USAGE on databases for every platform role
resource "snowflake_grant_privileges_to_account_role" "platform_db_usage" {
  for_each = {
    for pair in setproduct(keys(snowflake_database.layer), keys(snowflake_account_role.platform_roles)) :
    "${pair[0]}.${pair[1]}" => {
      database = pair[0]
      role     = pair[1]
    }
  }

  account_role_name = snowflake_account_role.platform_roles[each.value.role].name

  on_account_object {
    object_name = snowflake_database.layer[each.value.database].name
    object_type = "DATABASE"
  }

  privileges = ["USAGE"]
}

# Ingest role: USAGE on Bronze schemas
resource "snowflake_grant_privileges_to_account_role" "ingest_schemas" {
  for_each = snowflake_schema.bronze

  account_role_name = snowflake_account_role.platform_roles["HYBRID_LH_INGEST_ROLE"].name

  on_schema {
    schema_name = "${snowflake_database.layer["bronze"].name}.${each.value.name}"
  }

  privileges = ["USAGE", "CREATE TABLE", "CREATE EXTERNAL TABLE", "CREATE STAGE", "CREATE PIPE"]
}

# Transform role: full control on Silver and Gold schemas
resource "snowflake_grant_privileges_to_account_role" "transform_schemas" {
  for_each = local.transform_target_schemas

  account_role_name = snowflake_account_role.platform_roles["HYBRID_LH_TRANSFORM_ROLE"].name

  on_schema {
    schema_name = each.value
  }

  privileges = ["USAGE", "CREATE TABLE", "CREATE VIEW", "CREATE FUNCTION", "CREATE PROCEDURE"]
}

# BI reader: USAGE on Gold schemas + SELECT on all/future tables
resource "snowflake_grant_privileges_to_account_role" "bi_schemas" {
  for_each = snowflake_schema.gold

  account_role_name = snowflake_account_role.platform_roles["HYBRID_LH_BI_READER_ROLE"].name

  on_schema {
    schema_name = "${snowflake_database.layer["gold"].name}.${each.value.name}"
  }

  privileges = ["USAGE"]
}

resource "snowflake_grant_privileges_to_account_role" "bi_tables" {
  for_each = snowflake_schema.gold

  account_role_name = snowflake_account_role.platform_roles["HYBRID_LH_BI_READER_ROLE"].name

  on_schema_object {
    all {
      object_type_plural = "TABLES"
      in_schema          = "${snowflake_database.layer["gold"].name}.${each.value.name}"
    }
  }

  privileges = ["SELECT"]
}

resource "snowflake_grant_privileges_to_account_role" "bi_future_tables" {
  for_each = snowflake_schema.gold

  account_role_name = snowflake_account_role.platform_roles["HYBRID_LH_BI_READER_ROLE"].name

  on_schema_object {
    future {
      object_type_plural = "TABLES"
      in_schema          = "${snowflake_database.layer["gold"].name}.${each.value.name}"
    }
  }

  privileges = ["SELECT"]
}

# ML role: USAGE on Silver/Gold
resource "snowflake_grant_privileges_to_account_role" "ml_schemas" {
  for_each = local.transform_target_schemas

  account_role_name = snowflake_account_role.platform_roles["HYBRID_LH_ML_ROLE"].name

  on_schema {
    schema_name = each.value
  }

  privileges = ["USAGE"]
}

# Domain readers: USAGE + SELECT on a single domain in Silver
resource "snowflake_grant_privileges_to_account_role" "domain_schemas" {
  for_each = local.domain_roles

  account_role_name = snowflake_account_role.domain_reader[each.key].name

  on_schema {
    schema_name = "${snowflake_database.layer["silver"].name}.${upper(each.key)}"
  }

  privileges = ["USAGE"]
}

resource "snowflake_grant_privileges_to_account_role" "domain_tables" {
  for_each = local.domain_roles

  account_role_name = snowflake_account_role.domain_reader[each.key].name

  on_schema_object {
    all {
      object_type_plural = "TABLES"
      in_schema          = "${snowflake_database.layer["silver"].name}.${upper(each.key)}"
    }
  }

  privileges = ["SELECT"]
}

# Auditor: USAGE on all databases
resource "snowflake_grant_privileges_to_account_role" "auditor_databases" {
  for_each = snowflake_database.layer

  account_role_name = snowflake_account_role.platform_roles["HYBRID_LH_AUDITOR_ROLE"].name

  on_account_object {
    object_name = each.value.name
    object_type = "DATABASE"
  }

  privileges = ["USAGE"]
}
