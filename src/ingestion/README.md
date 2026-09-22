# Ingestion

> **Status: 🔭 Alvo** — designed, not applied. Local ingestion is handled elsewhere.

## Current (✅) vs target (🔭)

| Path | Implementation | Status |
|---|---|---|
| Local fixtures (batch) | `scripts/generate_bronze.py` → `data/bronze/*.parquet` | ✅ Atual |
| Streaming simulation | `src/streaming` (FileQueue → `data/bronze/streaming/`) | 🔭 simulation Alvo (landing-only, not consumed by dbt) |
| Snowpipe | Terraform external tables + stage (`src/terraform/modules/snowflake/external_tables.tf`) | 🔭 Alvo (no apply) |
| Kafka Connect | `kafka-connect/` placeholder | 🔭 Alvo |
| API connectors | `api-connectors/` placeholder | 🔭 Alvo |

## Known gap (streaming → dbt)

The `bronze_source()` macro globs `<table>/*.parquet` and does **not** match the
Hive-partitioned streaming layout (`event_date=*/event_hour=*`). Streaming output
is landing-only until either the macro or a connector is chosen. Documented in
`src/dbt/models/bronze/_sources.yml` and `src/streaming/README.md`.
