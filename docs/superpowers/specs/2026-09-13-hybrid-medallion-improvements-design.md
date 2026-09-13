# Hybrid Medallion Improvements — Design

{% raw %}
**Date:** 2026-09-13
**Status:** Approved
**Scope:** Full P0-P2, zero cloud cost, Snowflake-ready
**Tech assessment baseline:** 6.4/10

## 1. Context

Repo `Hybrid Medallion Lakehouse` is a PoC of 1 domain (vendas+clientes, 4 dbt models) with enterprise-level docs but gap code-vs-doc: `src/ingestion`, `data-quality`, `observability` empty, Bronze breaks on Snowflake (`read_parquet` hardcoded in `src/dbt/models/bronze/stg_vendas__pedidos.sql:26`), Silver SCD2 fake, Gold full-refresh, CI gate weakened to `always pass`, `lint-py || true`.

Constraints validated: zero cloud cost (DuckDB + Parquet + LocalStack only, Terraform `validate/test` + `plan`, no `apply`). Success: code runs local today with no rework when Snowflake is enabled.

## 2. Architecture (Approved)

Keep dual-target dbt `local (DuckDB)` ↔ `dev/stg/prd (Snowflake+S3)`. Remove scattered `{% if target.type %}`. Add `src/dbt/macros/compat/` with `dispatch`:

- `ts_now()` — `now()` DuckDB vs `current_timestamp()` Snowflake
- `ym_format()` — `strftime` vs `to_char`
- `bronze_source()` — `read_parquet` local vs `source()` external table Snowflake

Bronze Snowflake = external tables provisioned in Terraform (designed now, applied later). Gold = incremental + `state:modified+`. Docs get `Atual` vs `Alvo` badges.

Isolation: each macro has single purpose, callable without reading internals, tested independently. Changing internals does not break consumers.

## 3. Components (Approved)

- `dbt`: `macros/compat/*`, `models/bronze` via `bronze_source()`, `models/silver` with `snapshots/` real SCD2, `models/gold` incremental.
- `terraform`: external tables + 1 masking policy + 1 row-access policy for `cpf/email` + remote backend S3 + `plan` in PR. `modules/snowflake`, `modules/s3` interface unchanged.
- `pipelines`: DAG without `Variable.get()` at parse-time, `dbt build --select state:modified+`, controlled subprocess timeout.
- `docs`: `README.md`, `02-architecture-design.md`, `04-data-governance-framework.md` with badges, `CONVENTIONS.md` unchanged.
- `scripts`: `generate_bronze.py`, `validate_structure.py` extended to check macros and badges, no `if target.type` outside `macros/`.

Out of scope (YAGNI): GE/DQX, Collibra/Atlan, real Kafka, Grafana, enforcement of masking in DuckDB.

## 4. Data Flow (Approved)

`generate_bronze.py` → `data/bronze/*.parquet` → `bronze_source()` → staging dedup (`row_number`) → `snapshots` SCD2 Silver with `merge` handling late-arriving → Gold incremental → `dbt show` / CSV local today, Snowflake views tomorrow. `FileQueue` retired or labeled `simulation`. Freshness via `source freshness` + row-count.

## 5. Errors, CI Gates, Observability R$0 (Approved)

Harden CI to fail for real: revert `always pass`, remove `|| true`, lint covers `snowpark/airflow/dbt`, `terraform fmt/validate/test` + `plan` (no apply). Freshness runs in local CI. `assert_revenue_not_negative` = `warn` on synthetic, `error` in prod. No Grafana now — logs + `dbt artifacts` + simple freshness/row-count/estimated-cost dashboard. Schema drift fails explicitly.

## 6. Tests (Approved)

- dbt: `unique/not_null/relationships` + 2 singulars + `dbt test --select state:modified+`, snapshots tested with late-arriving fixture, 1 Bronze contract test.
- Python: `pytest` for compat, streaming, snowpark.
- Terraform: `test` with `mock_provider` + local `plan`.
- Structure: `validate_structure.py` checks macros, badges, no stray `if target.type`.
- Docs: `markdownlint + cspell + mermaid` kept.

## 7. Phases / Gates

- P0 (1-2d, R$0): macros dispatch, CI hard, badges, `.gitignore` hygiene (`*_cache`, `dbt_packages/`, `target/`), align version 0.1.0 vs 0.2.0.
- P1 (design now, apply later): Bronze external tables, SCD2 snapshots, LGPD SQL/Terraform ready, freshness in CI.
- P2: retire/scope `ingestion/streaming`, remote backend + `plan` + tflint/checkov, unify `Makefile/make.ps1`.

Gate P0→P1: CI green with real failures, zero `if target.type` outside macros, docs badged.
Gate P1→P2: `dbt build --target local` passes + `terraform plan` clean on 4 envs without secrets.

{% endraw %}
