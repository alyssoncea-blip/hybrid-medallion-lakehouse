###############################################################################
# Terraform Tests — Snowflake module (mock_provider version)
#
# Uses terraform test with the built-in mock provider, so no real Snowflake
# credentials are required. Run with: terraform test
###############################################################################

mock_provider "snowflake" {
  mock_data "snowflake_account" {
    defaults = {
      account = "test-account"
    }
  }
  mock_resource "snowflake_warehouse" {
    defaults = {
      name = "MOCK_WH"
    }
  }
  mock_resource "snowflake_resource_monitor" {
    defaults = {
      name = "MOCK_RM"
    }
  }
  mock_resource "snowflake_database" {
    defaults = {
      name = "MOCK_DB"
    }
  }
  mock_resource "snowflake_schema" {
    defaults = {
      name = "MOCK_SCHEMA"
    }
  }
  mock_resource "snowflake_account_role" {
    defaults = {
      name = "MOCK_ROLE"
    }
  }
  mock_resource "snowflake_grant_privileges_to_account_role" {
    defaults = {
      id = "MOCK_GRANT"
    }
  }
}

variables {
  environment                 = "dev"
  notification_users          = []
  data_classification_default = "interno"
}

run "creates_one_warehouse_per_workload" {
  command = plan

  assert {
    condition     = length(output.warehouse_names) == 5
    error_message = "Expected 5 warehouses (ingest, transform, bi, ml, admin), got ${length(output.warehouse_names)}"
  }

  assert {
    condition     = contains(keys(output.warehouse_names), "ingest")
    error_message = "Missing 'ingest' warehouse"
  }

  assert {
    condition     = contains(keys(output.warehouse_names), "transform")
    error_message = "Missing 'transform' warehouse"
  }

  assert {
    condition     = contains(keys(output.warehouse_names), "bi")
    error_message = "Missing 'bi' warehouse"
  }

  assert {
    condition     = contains(keys(output.warehouse_names), "ml")
    error_message = "Missing 'ml' warehouse"
  }

  assert {
    condition     = contains(keys(output.warehouse_names), "admin")
    error_message = "Missing 'admin' warehouse"
  }
}

run "creates_databases_for_all_layers" {
  command = plan

  assert {
    condition     = length(output.database_names) == 5
    error_message = "Expected 5 databases (bronze, silver, gold, govern, analytics)"
  }

  assert {
    condition     = contains(keys(output.database_names), "bronze")
    error_message = "Missing 'bronze' database"
  }

  assert {
    condition     = contains(keys(output.database_names), "silver")
    error_message = "Missing 'silver' database"
  }

  assert {
    condition     = contains(keys(output.database_names), "gold")
    error_message = "Missing 'gold' database"
  }
}

run "creates_resource_monitor_per_warehouse" {
  command = plan

  assert {
    condition     = length(output.resource_monitor_names) == 5
    error_message = "Resource monitor count mismatch: ${length(output.resource_monitor_names)}"
  }
}

run "creates_domain_reader_roles" {
  command = plan

  assert {
    condition     = length(output.domain_reader_roles) >= 7
    error_message = "Expected at least 7 domain reader roles, got ${length(output.domain_reader_roles)}"
  }

  assert {
    condition     = contains(keys(output.domain_reader_roles), "vendas")
    error_message = "Missing domain reader for 'vendas'"
  }

  assert {
    condition     = contains(keys(output.domain_reader_roles), "fiscal")
    error_message = "Missing domain reader for 'fiscal'"
  }
}
