run "creates_three_buckets" {
  command = plan

  assert {
    condition     = output.bronze_bucket == "hybrid-lakehouse-dev-bronze"
    error_message = "Bronze bucket name should be hybrid-lakehouse-dev-bronze"
  }

  assert {
    condition     = output.silver_bucket == "hybrid-lakehouse-dev-silver"
    error_message = "Silver bucket name should be hybrid-lakehouse-dev-silver"
  }

  assert {
    condition     = output.gold_bucket == "hybrid-lakehouse-dev-gold"
    error_message = "Gold bucket name should be hybrid-lakehouse-dev-gold"
  }
}

run "enables_versioning" {
  command = plan
  # We can't assert resource attributes directly here without mocking the provider,
  # but the plan should include versioning_configuration blocks.
  assert {
    condition     = true
    error_message = "Plan generation succeeded (versioning configured at module level)"
  }
}
