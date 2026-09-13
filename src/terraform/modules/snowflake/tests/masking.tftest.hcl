###############################################################################
# Terraform Tests — Snowflake masking attachments (mock_provider version)
#
# Validates the LGPD masking-policy and tag attachments as code, with no real
# Snowflake credentials required. Run with: terraform test
###############################################################################

mock_provider "snowflake" {
  mock_data "snowflake_account" {
    defaults = {
      account = "test-account"
    }
  }
  mock_resource "snowflake_table_column_masking_policy_application" {
    defaults = {
      column = "CPF"
    }
  }
  mock_resource "snowflake_tag_association" {
    defaults = {
      object_type = "COLUMN"
    }
  }
}

variables {
  environment                 = "dev"
  notification_users          = []
  data_classification_default = "interno"
}

run "attaches_masking_policy_to_cliente_cpf_column" {
  command = plan

  assert {
    condition     = snowflake_table_column_masking_policy_application.cliente_cpf.column == "CPF"
    error_message = "Masking policy must attach to the CPF column"
  }

  assert {
    condition     = snowflake_table_column_masking_policy_application.cliente_cpf.table == "DEV_HYBRID_LH_SILVER.CLIENTE.SLV_CLIENTES_SNAPSHOT"
    error_message = "Masking policy must attach to the Silver cliente snapshot table"
  }
}

run "tags_cliente_pii_columns" {
  command = plan

  assert {
    condition     = length(snowflake_tag_association.cliente_pii) == 3
    error_message = "Expected 3 tag associations (cpf, email, nome)"
  }

  assert {
    condition     = snowflake_tag_association.cliente_pii["cpf"].tag_value == "cpf"
    error_message = "Missing tag association for the cpf column"
  }

  assert {
    condition     = snowflake_tag_association.cliente_pii["email"].tag_value == "email"
    error_message = "Missing tag association for the email column"
  }

  assert {
    condition     = snowflake_tag_association.cliente_pii["nome"].tag_value == "nome"
    error_message = "Missing tag association for the nome column"
  }
}
