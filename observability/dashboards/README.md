# Observability Dashboards

> **Status: ✅ Atual (local, R$0)** via CI artifacts + dbt docs; 🔭 Grafana for cloud.

## Available signals today (R$0)

| Signal | How to view |
|---|---|
| Lakehouse health (PASS/WARN/ERROR, Bronze mtimes, Gold recency) | CI artifact `lakehouse-health` (`/tmp/health.md`) or `python scripts/generate_health_report.py --run-results src/dbt/target/run_results.json --out health.md` |
| dbt test results / lineage | `dbt docs generate && dbt docs serve` (in `src/dbt`) |
| Coverage | CI artifact `coverage-xml` |
| Alerts (manifest) | `../alerts/gold_alerts.yml` (validated by `scripts/validate_structure.py`) |
| CI gate status | GitHub Actions `All Checks Passed` job |

## Not implemented (deferred, YAGNI)

- Grafana / Snowflake Account Usage dashboards (🔭 Alvo)
- Cost per warehouse / per-query dashboards (🔭 Alvo)
- OpenLineage graph UI (🔭 Alvo)
