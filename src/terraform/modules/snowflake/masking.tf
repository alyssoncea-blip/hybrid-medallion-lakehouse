###############################################################################
# Snowflake Governance — LGPD masking (YAGNI: 1 policy + 1 tag only)
#
# - snowflake_masking_policy.pii_cpf: masks CPF (VARCHAR) for non-privileged
#   roles; the full value stays visible only to the auditor role.
# - snowflake_tag.pii: classification tag for PII columns (e.g. cpf, email).
#
# Both live in the SILVER CLIENTE schema, the domain that holds CPF/PII.
# `variable.environment` is already declared in versions.tf (not redeclared).
#
# Intentionally deferred (documented, not implemented):
# - Row access policies: out of scope for the single-policy LGPD minimum.
#
# Attachments below are validate-only as code (terraform test with the mock
# provider; no apply, no secrets). DuckDB local runs do not enforce masking;
# enforcement happens on Snowflake targets at deploy time.
###############################################################################

resource "snowflake_masking_policy" "pii_cpf" {
  name             = "${upper(var.environment)}_HYBRID_LH_PII_CPF"
  database         = snowflake_database.layer["silver"].name
  schema           = snowflake_schema.silver["cliente"].name
  return_data_type = "VARCHAR"
  body             = "case when current_role() in ('${snowflake_account_role.platform_roles["HYBRID_LH_AUDITOR_ROLE"].name}') then val else regexp_replace(val, '[0-9]', '*') end"

  argument {
    name = "val"
    type = "VARCHAR"
  }

  comment = "LGPD: mask CPF for non-privileged roles (${var.environment})"
}

resource "snowflake_tag" "pii" {
  name           = "${upper(var.environment)}_HYBRID_LH_PII"
  database       = snowflake_database.layer["silver"].name
  schema         = snowflake_schema.silver["cliente"].name
  allowed_values = ["cpf", "email", "nome"]
  comment        = "LGPD: PII classification tag (${var.environment})"
}

# Attach the CPF masking policy to the CPF column of the Silver cliente
# table (dbt snapshot slv_clientes_snapshot in the CLIENTE schema).
resource "snowflake_table_column_masking_policy_application" "cliente_cpf" {
  column         = "CPF"
  masking_policy = "${snowflake_database.layer["silver"].name}.${snowflake_schema.silver["cliente"].name}.${snowflake_masking_policy.pii_cpf.name}"
  table          = "${snowflake_database.layer["silver"].name}.${snowflake_schema.silver["cliente"].name}.SLV_CLIENTES_SNAPSHOT"
}

# Tag the PII columns (cpf/email/nome) of the Silver cliente table.
resource "snowflake_tag_association" "cliente_pii" {
  for_each = toset(["cpf", "email", "nome"])

  object_identifiers = [
    "\"${snowflake_database.layer["silver"].name}\".\"${snowflake_schema.silver["cliente"].name}\".\"SLV_CLIENTES_SNAPSHOT\".\"${upper(each.value)}\""
  ]
  object_type = "COLUMN"
  tag_id      = "${snowflake_database.layer["silver"].name}.${snowflake_schema.silver["cliente"].name}.${snowflake_tag.pii.name}"
  tag_value   = each.value
}
