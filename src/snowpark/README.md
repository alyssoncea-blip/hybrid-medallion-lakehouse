# Snowpark Python Jobs

This directory contains Snowpark Python jobs for advanced feature engineering and ML preprocessing that go beyond what dbt SQL can express.

## Structure

```
src/snowpark/
├── jobs/
│   ├── feature_engineering_dim_produto.py   # Main feature engineering job
│   └── (add more jobs here)
├── udfs/
│   ├── feature_udfs.py                      # Reusable UDFs for feature engineering
│   └── (add more UDFs here)
├── requirements.txt                          # Python dependencies
└── README.md                                 # This file
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r src/snowpark/requirements.txt
```

### 2. Set Environment Variables
```bash
export SNOWFLAKE_ACCOUNT=your-account
export SNOWFLAKE_USER=your-user
export SNOWFLAKE_PASSWORD=your-password
export SNOWFLAKE_WAREHOUSE=your-warehouse
export SNOWFLAKE_DATABASE=your-database
export SNOWFLAKE_SCHEMA=PUBLIC
export SNOWFLAKE_ROLE=your-role  # optional
```

### 3. Run Feature Engineering Job
```bash
# Dry run (print plan only)
python src/snowpark/jobs/feature_engineering_dim_produto.py --dry-run

# Execute
python src/snowpark/jobs/feature_engineering_dim_produto.py
```

### 4. Using UDFs in SQL
```python
from snowflake.snowpark import Session
from src.snowpark.udfs.feature_udfs import register_udfs

session = Session.builder.configs(connection_params).create()
udfs = register_udfs(session)

# Now use in SQL:
# SELECT PRICE_BUCKET(preco_unitario) FROM SILVER.STG_DIM_PRODUTO
```

## Job: Feature Engineering for dim_produto

**Input:** `SILVER.STG_DIM_PRODUTO` (from dbt Silver layer)  
**Output:** `GOLD.GLD_DIM_PRODUTO_FEATURES` (enriched features)

### Features Generated:

| Feature | Description |
|---------|-------------|
| `price_bucket` | LOW/MEDIUM/HIGH/PREMIUM categorization |
| `price_normalized` | Min-max normalized price (0-1) |
| `above_avg_price` | Binary flag (1 if above average) |
| `has_fabricante` | Binary flag for manufacturer presence |
| `nome_length` | Product name length (complexity proxy) |
| `sku_numeric_suffix` | Numeric suffix from SKU |
| `is_<category>` | One-hot encoded category flags |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Bronze    │────▶│   Silver    │────▶│    Gold     │
│  (Raw)      │     │ (Cleaned)   │     │ (Enriched)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
  dbt models         dbt models         Snowpark Python
  (Parquet/           (views/            (feature eng,
   raw tables)         tables)           UDFs, ML prep)
```

## CI/CD Integration

The Airflow DAG (`src/airflow/dags/hybrid_medallion_lakehouse_dbt.py`) can be extended to trigger Snowpark jobs after dbt build:

```python
# In Airflow DAG:
run_snowpark_features = BashOperator(
    task_id="snowpark_feature_engineering",
    bash_command="""
        cd /opt/airflow &&
        python src/snowpark/jobs/feature_engineering_dim_produto.py
    """,
    env={
        "SNOWFLAKE_ACCOUNT": Variable.get("snowflake_account"),
        "SNOWFLAKE_USER": Variable.get("snowflake_user"),
        "SNOWFLAKE_PASSWORD": Variable.get("snowflake_password"),
        "SNOWFLAKE_WAREHOUSE": Variable.get("snowflake_warehouse"),
        "SNOWFLAKE_DATABASE": Variable.get("snowflake_database"),
        "SNOWFLAKE_SCHEMA": Variable.get("snowflake_schema"),
    },
)
```

## Development

### Local Testing (without Snowflake)
```bash
# Test UDFs locally
python src/snowpark/udfs/feature_udfs.py

# Test job logic (dry run)
python src/snowpark/jobs/feature_engineering_dim_produto.py --dry-run
```

### Adding New Jobs
1. Create `src/snowpark/jobs/<job_name>.py`
2. Follow the pattern: `create_session` → `read` → `transform` → `write`
3. Add CLI args for configuration
4. Update this README

### Adding New UDFs
1. Add function to `src/snowpark/udfs/feature_udfs.py`
2. Register in `register_udfs()`
3. Test locally with `python src/snowpark/udfs/feature_udfs.py`
4. Use in SQL via `register_udfs(session)`