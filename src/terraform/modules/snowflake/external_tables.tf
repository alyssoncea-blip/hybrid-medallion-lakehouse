###############################################################################
# Snowflake External Tables — Bronze landing (Alvo, no apply)
#
# Designed now, validated/tested with mock_provider only. Requires
# `terraform apply` with S3 + Snowflake creds (out of scope, zero-cost here).
#
# NOTE (provider ~> 0.92 (resolves to v0.100.0) deviation from plan sketch): `snowflake_external_table`
# requires `file_format`, `location` (not `stage`) and >=1 `column` block.
# `location` points at the stage above; columns map Parquet VALUE fields.
# `variable.environment` is NOT redeclared here (already in versions.tf).
###############################################################################

variable "bronze_bucket" {
  type        = string
  description = "S3 bucket hosting bronze/ prefix (Alvo)."
  default     = "hybrid-lh-bronze-dev"
}

resource "snowflake_stage" "bronze" {
  name     = "${upper(var.environment)}_HYBRID_LH_BRONZE_STAGE"
  database = snowflake_database.layer["bronze"].name
  schema   = snowflake_schema.bronze["raw_vendas"].name
  url      = "s3://${var.bronze_bucket}/bronze/"
  comment  = "Bronze landing stage (Alvo: requires apply with S3)"
}

resource "snowflake_external_table" "pedidos" {
  name        = "PEDIDOS_VENDAS_EXT"
  database    = snowflake_database.layer["bronze"].name
  schema      = snowflake_schema.bronze["raw_vendas"].name
  location    = "@${snowflake_stage.bronze.database}.${snowflake_stage.bronze.schema}.${snowflake_stage.bronze.name}/pedidos_vendas/"
  file_format = "TYPE = PARQUET"
  comment     = "External table over S3 bronze/pedidos_vendas (Alvo)"

  column {
    name = "pedido_id"
    type = "VARCHAR"
    as   = "VALUE:pedido_id::VARCHAR"
  }

  column {
    name = "data_pedido"
    type = "DATE"
    as   = "VALUE:data_pedido::DATE"
  }

  column {
    name = "valor_total"
    type = "NUMBER(18,2)"
    as   = "VALUE:valor_total::NUMBER(18,2)"
  }
}

resource "snowflake_external_table" "clientes" {
  name        = "CLIENTES_CADASTRO_EXT"
  database    = snowflake_database.layer["bronze"].name
  schema      = snowflake_schema.bronze["raw_vendas"].name
  location    = "@${snowflake_stage.bronze.database}.${snowflake_stage.bronze.schema}.${snowflake_stage.bronze.name}/clientes_cadastro/"
  file_format = "TYPE = PARQUET"
  comment     = "External table over S3 bronze/clientes_cadastro (Alvo)"

  column {
    name = "cliente_id"
    type = "VARCHAR"
    as   = "VALUE:cliente_id::VARCHAR"
  }

  column {
    name = "email"
    type = "VARCHAR"
    as   = "VALUE:email::VARCHAR"
  }
}
