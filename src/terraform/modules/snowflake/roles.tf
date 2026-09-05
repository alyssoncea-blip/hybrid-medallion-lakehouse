###############################################################################
# Snowflake RBAC — Role Hierarchy (least privilege)
#
#   SYSADMIN (built-in)
#     └── HYBRID_LH_ADMIN
#           ├── HYBRID_LH_INGEST_ROLE
#           ├── HYBRID_LH_TRANSFORM_ROLE
#           ├── HYBRID_LH_BI_READER_ROLE
#           ├── HYBRID_LH_ML_ROLE
#           ├── HYBRID_LH_DOMAIN_<X>_READER (per domain)
#           └── HYBRID_LH_AUDITOR_ROLE
###############################################################################

locals {
  domain_roles = toset([
    "vendas", "estoque", "fiscal", "cliente",
    "produto", "fornecedor", "financeiro",
  ])
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

  name    = "${upper(var.environment)}_${each.value}"
  comment = "Platform role: ${each.value}"
}

resource "snowflake_account_role" "domain_reader" {
  for_each = local.domain_roles

  name    = "${upper(var.environment)}_HYBRID_LH_DOMAIN_${upper(each.key)}_READER"
  comment = "Read-only role for the ${each.key} domain"
}

# Role hierarchy grants
resource "snowflake_grants" "hierarchy" {
  for_each = snowflake_account_role.platform_roles

  role_name = each.value.name

  grants = [
    "USAGE on database ${snowflake_database.layer["bronze"].name} to role ${each.value.name}",
    "USAGE on database ${snowflake_database.layer["silver"].name} to role ${each.value.name}",
    "USAGE on database ${snowflake_database.layer["gold"].name} to role ${each.value.name}",
  ]
}

# Ingest role: read external stages, write Bronze
resource "snowflake_grants" "ingest" {
  role_name = snowflake_account_role.platform_roles["HYBRID_LH_INGEST_ROLE"].name

  grants = [
    for schema in snowflake_schema.bronze :
    "USAGE on schema ${snowflake_database.layer[\"bronze\"].name}.${schema.name} to role ${snowflake_account_role.platform_roles[\"HYBRID_LH_INGEST_ROLE\"].name}"
  ]

  depends_on = [snowflake_grants.hierarchy]
}

# Transform role: read Bronze/Silver, write Silver/Gold
resource "snowflake_grants" "transform" {
  role_name = snowflake_account_role.platform_roles["HYBRID_LH_TRANSFORM_ROLE"].name

  grants = concat(
    [for schema in snowflake_schema.silver :
      "USAGE, CREATE TABLE, CREATE VIEW on schema ${snowflake_database.layer[\"silver\"].name}.${schema.name} to role ${snowflake_account_role.platform_roles[\"HYBRID_LH_TRANSFORM_ROLE\"].name}"],
    [for schema in snowflake_schema.gold :
      "USAGE, CREATE TABLE, CREATE VIEW on schema ${snowflake_database.layer[\"gold\"].name}.${schema.name} to role ${snowflake_account_role.platform_roles[\"HYBRID_LH_TRANSFORM_ROLE\"].name}"],
  )
}

# BI reader: read Gold only
resource "snowflake_grants" "bi" {
  role_name = snowflake_account_role.platform_roles["HYBRID_LH_BI_READER_ROLE"].name

  grants = [for schema in snowflake_schema.gold :
    "USAGE on schema ${snowflake_database.layer[\"gold\"].name}.${schema.name} to role ${snowflake_account_role.platform_roles[\"HYBRID_LH_BI_READER_ROLE\"].name}"
  ]
}

# Auditor: read everything, write nothing
resource "snowflake_grants" "auditor" {
  role_name = snowflake_account_role.platform_roles["HYBRID_LH_AUDITOR_ROLE"].name

  grants = [
    "USAGE on all schemas in database ${snowflake_database.layer[\"bronze\"].name} to role ${snowflake_account_role.platform_roles[\"HYBRID_LH_AUDITOR_ROLE\"].name}",
    "USAGE on all schemas in database ${snowflake_database.layer[\"silver\"].name} to role ${snowflake_account_role.platform_roles[\"HYBRID_LH_AUDITOR_ROLE\"].name}",
    "USAGE on all schemas in database ${snowflake_database.layer[\"gold\"].name} to role ${snowflake_account_role.platform_roles[\"HYBRID_LH_AUDITOR_ROLE\"].name}",
  ]
}
