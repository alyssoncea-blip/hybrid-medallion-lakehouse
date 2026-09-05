# Changelog

All notable changes to the **Hybrid Medallion Lakehouse** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-09-05

### Highlights

- **End-to-end local development** without cloud account (R$ 0): DuckDB warehouse + Parquet files + LocalStack for S3 emulation
- **GitHub Actions CI** with 7 parallel jobs; default pipeline runs without cloud secrets
- **5 Terraform test files** with `mock_provider` so terraform test runs without credentials
- **53 dbt data tests** + 2 singular tests passing against DuckDB
- **All 4 Terraform environments** (local/dev/stg/prd) validate cleanly

### Added

- **Local environment (R$ 0)**: DuckDB target in dbt profiles, Parquet fixtures in `data/bronze/`, generator script `scripts/generate_bronze.py`
- **LocalStack** integration via `docker-compose.yml` (S3, KMS, SQS) for Terraform local target
- **GitHub Actions CI** (`.github/workflows/ci.yml`):
  - markdown-lint, mermaid-render, structure-validate (Python, no deps)
  - terraform validate (matrix: local, dev, stg, prd)
  - terraform test (Snowflake and S3 modules with mock providers)
  - dbt build (local DuckDB) — uploads `lakehouse.duckdb` as artifact
  - dbt build (Snowflake) — auto-skip when secrets missing
  - python-lint (ruff + mypy)
  - all-checks-passed gate
- **CODEOWNERS** routing reviews by area (docs, terraform, dbt, CI)
- **Issue templates**: documentation.md, security.md (in addition to existing bug/feature/governance)
- **CI / CD section** in README with 7-job pipeline overview and secrets table
- **Dynamic CI badge** linking to GitHub Actions workflow
- **Makefile targets**: `bronze-generate`, `dbt-build-fresh`, `validate-tf-test`, `e2e-local`, `localstack-up/down/reset`
- **PowerShell entry point** (`scripts/make.ps1`) mirroring Make targets
- **cspell dictionary** with domain terms (snowflake, medallion, dbt, etc.)
- **.markdownlintignore** for vendor directories (dbt_packages, node_modules)
- **Repository structure validator** (`scripts/validate_structure.py`) — runs without external dependencies

### Changed

- `snowflake_grants` resource replaced with `snowflake_grant_privileges_to_account_role` (provider 0.100 API)
- `on_database` argument replaced with `on_account_object { object_type = "DATABASE" }`
- `suspend_immediate_trigger` removed (was always-false; Snowflake API requires numeric > 0)
- `s3_bucket_lifecycle_configuration` requires explicit empty `filter {}` block
- HCL: all one-liner `variable` blocks converted to multi-line (HCL 1.12 rejects multi-arg one-liners)
- dbt 1.11 conventions: `tags` on `sources` moved to `config:`; test arguments nested under `arguments:`
- dbt packages: `calogica/dbt_expectations` → `metaplane/dbt_expectations` (deprecated); `dbt_date` removed (transitive)
- dbt models made portable across Snowflake/DuckDB via `{% if target.type %}` for `current_timestamp` vs `now()`, `to_char` vs `strftime`
- Silver model uses `delete+insert` incremental strategy and `row_number()` dedup (DuckDB-friendly)
- Profiles and Terraform modules organized for 4 environments (local/dev/stg/prd) with cost annotations

### Fixed

- Mermaid CLI path resolution on Windows (`fileURLToPath` instead of `new URL().pathname`)
- Mermaid CLI execution via `shell: true` (required on Windows for `.cmd` resolution)
- Markdownlint config: disabled noisy rules (MD013 line length in tables, MD036 emphasis-as-heading, MD040 fence language, MD025 single H1)
- Terraform workspace handling: explicit `unique_key` set to `pedido_id` (was composite)
- Documented business risk: R-07 regulatory risk rewritten from BACEN/CMN/BCB to ANPD/Receita/Sindipeças (retail/auto-parts context, not financial institution)

## [0.1.0] — 2026-09-05

### Added

- Initial commit of the Hybrid Medallion Lakehouse project scaffolding and documentation:
  - Project charter, architecture design, implementation roadmap
  - Data governance framework, risks & compliance baseline
  - Repository structure (src/, pipelines/, data-quality/, observability/)
  - Conventional Commits + pre-commit + PR template
