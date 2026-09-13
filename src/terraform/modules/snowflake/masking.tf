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
# - Policy/tag attachment to columns (SET MASKING POLICY / SET TAG) happens
#   at deploy time on Snowflake targets; DuckDB local runs do not enforce
#   masking. Wire attachments when the first Snowflake-backed domain ships.
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
