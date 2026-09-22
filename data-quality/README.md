# Data Quality

> **Status: ✅ Atual (local, R$0)** — DQ is enforced by dbt tests, not a separate framework.

## What runs today

| Layer | Mechanism | Location |
|---|---|---|
| Schema (unique, not_null, relationships) | dbt generic tests on model YAML | `src/dbt/models/**/**.yml` |
| Singular / business rules | dbt singular tests (severity config) | `src/dbt/tests/*.sql` |
| Source freshness | `dbt source freshness` + file-mtime gate | `src/dbt/models/bronze/_sources.yml`, `scripts/check_bronze_freshness.py` |
| Alert mapping | validate-only manifest joining tests → alerts | `observability/alerts/gold_alerts.yml` |

Key singular tests: `assert_gold_recency` (error), `assert_late_data_covered` (error),
`assert_cpf_masked` (error), `assert_no_future_orders`, `assert_revenue_not_negative`
(**warn by design** on synthetic fixtures).

## Not implemented (deferred, YAGNI)

- Great Expectations / DQX suites (`great-expectations/`, `dqx/` are placeholders)
- Data contract signing workflow (`contracts/` placeholder)
- Row-level anomaly detection beyond the singular tests above

DQ runs inside `dbt build` locally and in CI (`dbt-build-local` job); no separate
runner is required.
