# Release Notes — Hybrid Medallion Lakehouse v0.2.0

> **First public release** of the Hybrid Medallion Lakehouse — a complete Bronze/Silver/Gold data platform with Terraform IaC, dbt transformations, and **free local development** (no cloud account required).

## What's in v0.2.0

### Architecture (target state)

- **Medallion architecture**: Bronze (raw Parquet) → Silver (cleansed, SCD2) → Gold (dimensional marts)
- **Hybrid storage**: S3/GCS for Bronze, Snowflake-managed for Silver/Gold
- **Multi-cloud ready**: AWS (sa-east-1) primary, GCP supported via Terraform provider swap

### Local dev (R$ 0)

- **DuckDB** as the warehouse — single binary, embedded, no server
- **Parquet files** in `data/bronze/` for Bronze layer
- **LocalStack** (Docker) for S3/KMS emulation when validating Terraform
- **Synthetic data generator** (`scripts/generate_bronze.py`): 2,000 pedidos + 500 clientes with valid (non-real) CPFs
- **Same dbt models and Terraform modules** deploy to both local and cloud

### Code shipped

- **4 dbt models** (Bronze/Silver/Gold) with portable SQL across Snowflake and DuckDB
- **1 seed** (dim_produto — 10 SKUs of auto parts)
- **53 data tests + 2 singular tests** — all pass on DuckDB
- **2 Terraform modules**: snowflake (warehouses, databases, RBAC) and s3 (3 buckets with KMS, versioning, lifecycle)
- **4 environments**: local (LocalStack) / dev / stg / prd — all validate clean
- **5 Terraform tests** with `mock_provider` — no real cloud required

### CI/CD

- **GitHub Actions** with 7 parallel jobs; default pipeline runs without cloud secrets
- **Conventional Commits** enforced via commitlint and pre-commit
- **CODEOWNERS** routing reviews by area
- **Issue templates**: bug, feature, governance, documentation, security

### Documentation

- **5 numbered docs**: project charter, architecture, roadmap, governance, risks
- **Cost-conscious README** explaining two execution paths (free local / paid cloud) and the real cost of each
- **Mermaid diagrams** for architecture, lineage, SCD2, masking

## Quick start (R$ 0)

```powershell
# 1. Generate Bronze fixtures
python scripts/generate_bronze.py

# 2. Setup dbt profile (one-time)
mkdir $env:USERPROFILE\.dbt
cp src/dbt/profiles.yml.example $env:USERPROFILE\.dbt\profiles.yml

# 3. Build the lakehouse end-to-end
cd src/dbt
dbt deps
dbt build --target local
```

Expected:

```
Done. PASS=49 WARN=1 ERROR=0 SKIP=0 NO-OP=0 TOTAL=50
```

Query the Gold layer:

```powershell
duckdb C:\Users\alyss\data\lakehouse.duckdb -c "select * from main.gld_vendas__receita_mensal order by receita_liquida desc limit 10"
```

## Cost reality

| Path | Cost | When to use |
|---|---|---|
| `local` (DuckDB + Parquet) | **R$ 0** | dev laptop, CI, demos, learning |
| `local` (LocalStack + Terraform) | R$ 0 | validating Terraform structure |
| `dev` (Snowflake trial) | R$ 0 / 30 days | initial integration testing |
| `stg` (Snowflake) | ~$500–2k/month | pre-prod validation |
| `prd` (Snowflake Enterprise) | ~$2k–10k/month | production |

## What's NOT in v0.2.0 (planned for v0.3+)

- Airflow DAGs (currently the platform assumes dbt Cloud or Snowflake Tasks as orchestrator)
- Snowpark Python jobs (the structure is there, no example yet)
- Real-time streaming via Kafka (Bronze assumes batch/micro-batch)
- GitHub Pages for hosted docs
- Branch `develop` and `release/*` workflow enforcement

## Verification

This release was validated end-to-end on Windows 11 with:

- Terraform 1.12.1
- dbt-core 1.11.8 + dbt-duckdb 1.10.1 + dbt-snowflake 1.12.0
- Node.js 24.14.1 + npm 11.11.0
- Python 3.11 (Anaconda)

## Authors

- Project Lead: Alysson Cea
- Architecture and engineering: Hybrid Medallion Lakehouse team
- See [`01-project-charter.md`](01-project-charter.md) for stakeholders and RACI

## License

TBD — see [LICENSE](LICENSE) (placeholder).
