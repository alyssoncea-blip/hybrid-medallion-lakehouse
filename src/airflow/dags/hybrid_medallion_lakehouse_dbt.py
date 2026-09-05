"""
Hybrid Medallion Lakehouse — Airflow DAG for dbt pipeline orchestration.

This DAG runs the complete dbt pipeline:
  1. dbt deps          — install packages
  2. dbt build         — run models (Bronze → Silver → Gold)
  3. dbt test          — run all data tests
  4. dbt docs generate — generate documentation (optional)

Supports two execution modes via Airflow Variables:
  - target: "local"  → DuckDB (free, no cloud needed)
  - target: "dev"    → Snowflake dev (requires secrets)

Variables to set in Airflow UI (Admin → Variables):
  - dbt_target: "local" | "dev" | "stg" | "prd"
  - dbt_project_dir: "/opt/airflow/dbt" (mounted from repo)
  - dbt_profiles_dir: "/opt/airflow/.dbt" (mounted from repo)

For local development with Docker Compose, see docker-compose.airflow.yml
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

DBT_PROJECT_DIR = Variable.get("dbt_project_dir", default_var="/opt/airflow/dbt")
DBT_PROFILES_DIR = Variable.get("dbt_profiles_dir", default_var="/opt/airflow/.dbt")
DBT_TARGET = Variable.get("dbt_target", default_var="local")

# Environment variables for dbt
DBT_ENV = {
    "DBT_PROFILES_DIR": DBT_PROFILES_DIR,
    "DBT_TARGET": DBT_TARGET,
    # DuckDB path for local target
    "DBT_DUCKDB_PATH": "/opt/airflow/data/lakehouse.duckdb",
}

# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────
def validate_dbt_profile(**context) -> None:
    """Verify dbt profile exists and target is configured."""
    profiles_yml = os.path.join(DBT_PROFILES_DIR, "profiles.yml")
    if not os.path.exists(profiles_yml):
        raise FileNotFoundError(f"dbt profiles.yml not found at {profiles_yml}")
    
    import yaml
    with open(profiles_yml) as f:
        profiles = yaml.safe_load(f)
    
    project_name = "hybrid_medallion_lakehouse"
    if project_name not in profiles:
        raise ValueError(f"Project '{project_name}' not found in profiles.yml")
    
    if DBT_TARGET not in profiles[project_name].get("outputs", {}):
        raise ValueError(f"Target '{DBT_TARGET}' not configured in profiles.yml")
    
    print(f"✓ dbt profile validated: project={project_name}, target={DBT_TARGET}")


def print_dbt_version(**context) -> None:
    """Log dbt version for debugging."""
    import subprocess
    result = subprocess.run(["dbt", "--version"], capture_output=True, text=True)
    print(f"dbt version: {result.stdout.strip()}")


# ──────────────────────────────────────────────────────────────────────────────
# DAG Definition
# ──────────────────────────────────────────────────────────────────────────────
with DAG(
    dag_id="hybrid_medallion_lakehouse_dbt",
    description="Orchestrates dbt pipeline for Hybrid Medallion Lakehouse (Bronze/Silver/Gold)",
    default_args=DEFAULT_ARGS,
    schedule="0 6 * * *",  # Daily at 06:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["dbt", "lakehouse", "medallion", "hybrid"],
    doc_md=__doc__,
) as dag:

    # ─── Start / End markers ───
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end", trigger_rule="none_failed_min_one_success")

    # ─── Validation tasks ───
    validate_profile = PythonOperator(
        task_id="validate_dbt_profile",
        python_callable=validate_dbt_profile,
    )

    print_version = PythonOperator(
        task_id="print_dbt_version",
        python_callable=print_dbt_version,
    )

    # ─── dbt execution tasks ───
    with TaskGroup(group_id="dbt_pipeline") as dbt_pipeline:
        
        dbt_deps = BashOperator(
            task_id="dbt_deps",
            bash_command=f"cd {DBT_PROJECT_DIR} && dbt deps --no-version-check",
            env=DBT_ENV,
            retries=2,
        )

        dbt_build = BashOperator(
            task_id="dbt_build",
            bash_command=f"cd {DBT_PROJECT_DIR} && dbt build --target {DBT_TARGET} --no-version-check",
            env=DBT_ENV,
            execution_timeout=timedelta(hours=1),
        )

        dbt_test = BashOperator(
            task_id="dbt_test",
            bash_command=f"cd {DBT_PROJECT_DIR} && dbt test --target {DBT_TARGET} --no-version-check",
            env=DBT_ENV,
            execution_timeout=timedelta(hours=1),
        )

        dbt_docs = BashOperator(
            task_id="dbt_docs_generate",
            bash_command=f"cd {DBT_PROJECT_DIR} && dbt docs generate --target {DBT_TARGET} --no-version-check",
            env=DBT_ENV,
            retries=0,  # docs generation is optional, don't fail pipeline
        )

        # Task dependencies within pipeline
        dbt_deps >> dbt_build >> dbt_test >> dbt_docs

    # ─── Freshness check (for source tables) ───
    dbt_source_freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt source freshness --target {DBT_TARGET} --no-version-check",
        env=DBT_ENV,
        retries=1,
        trigger_rule="all_done",  # run even if tests fail
    )

    # ─── Overall flow ───
    start >> [validate_profile, print_version] >> dbt_pipeline >> dbt_source_freshness >> end