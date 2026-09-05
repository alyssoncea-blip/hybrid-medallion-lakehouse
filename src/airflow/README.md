# Airflow Orchestration for Hybrid Medallion Lakehouse

This directory contains the Airflow DAG and configuration to orchestrate the dbt pipeline.

## Quick Start (Local with Docker Compose)

### Prerequisites

- Docker + Docker Compose v2
- 4 GB+ RAM available for containers

### 1. Generate Bronze fixtures (one-time)

```bash
python scripts/generate_bronze.py --rows-pedidos 2000 --rows-clientes 500
```

### 2. Setup dbt profile for Airflow

```bash
mkdir -p src/airflow/.dbt
cp src/dbt/profiles.yml.example src/airflow/.dbt/profiles.yml
```

Edit `src/airflow/.dbt/profiles.yml` if needed (default `local` target uses DuckDB).

### 3. Start Airflow

```bash
docker compose -f docker-compose.airflow.yml up --build -d
```

### 4. Access Airflow UI

- URL: <http://localhost:8080>
- Username: `admin`
- Password: `admin`

### 5. Configure Airflow Variables (Admin → Variables)

| Key | Value | Description |
|-----|-------|-------------|
| `dbt_target` | `local` | Target: `local` (DuckDB), `dev` (Snowflake) |
| `dbt_project_dir` | `/opt/airflow/dbt` | Mounted from `src/dbt` |
| `dbt_profiles_dir` | `/opt/airflow/.dbt` | Mounted from `src/airflow/.dbt` |

### 6. Trigger DAG

- Go to **DAGs** → `hybrid_medallion_lakehouse_dbt` → **Trigger DAG**

## DAG Details

**DAG ID:** `hybrid_medallion_lakehouse_dbt`

**Schedule:** Daily at 06:00 UTC (`0 6 * * *`)

**Tasks:**

1. `validate_dbt_profile` — Verify profiles.yml exists and target configured
2. `print_dbt_version` — Log dbt version
3. `dbt_deps` — Install dbt packages
4. `dbt_build` — Run models (Bronze → Silver → Gold)
5. `dbt_test` — Run all data tests (53 tests)
6. `dbt_docs_generate` — Generate documentation (optional)
7. `dbt_source_freshness` — Check source freshness

## Switching to Snowflake (Cloud)

1. Update Airflow Variable `dbt_target` → `dev` (or `stg`/`prd`)
2. Add Snowflake credentials to `src/airflow/.dbt/profiles.yml`:

   ```yaml
   dev:
     type: snowflake
     account: <your-account>
     user: <your-user>
     password: <your-password>
     role: <your-role>
     warehouse: <your-warehouse>
     database: <your-database>
     schema: public
     threads: 4
   ```

3. Restart Airflow webserver: `docker compose -f docker-compose.airflow.yml restart airflow`

## Local Development (without Docker)

```bash
# Install dependencies
pip install -r src/airflow/requirements.txt

# Set environment variables
export DBT_PROJECT_DIR=/path/to/project/src/dbt
export DBT_PROFILES_DIR=/path/to/project/src/airflow/.dbt
export DBT_TARGET=local

# Run dbt manually
cd $DBT_PROJECT_DIR
dbt deps
dbt build --target local
dbt test --target local
```

## Project Structure

```text
src/airflow/
├── dags/
│   └── hybrid_medallion_lakehouse_dbt.py   # Main DAG
├── config/
│   └── (airflow.cfg overrides if needed)
├── plugins/
│   └── (custom operators/hooks if needed)
├── tests/
│   └── test_dag.py                         # DAG unit tests
├── requirements.txt                        # Python dependencies
└── README.md                               # This file
```

## Troubleshooting

**DAG not showing in UI:**

- Check `docker compose -f docker-compose.airflow.yml logs airflow`
- Verify DAG file syntax: `python -m py_compile src/airflow/dags/hybrid_medallion_lakehouse_dbt.py`

**dbt fails with "profile not found":**

- Verify `src/airflow/.dbt/profiles.yml` exists
- Check Airflow Variable `dbt_profiles_dir` = `/opt/airflow/.dbt`

**DuckDB permission error:**

- Ensure `data/` directory is writable: `chmod 777 data/`

**Out of memory:**

- Increase Docker Desktop memory limit to 6 GB+
- Or reduce `AIRFLOW__CORE__PARALLELISM` in docker-compose
