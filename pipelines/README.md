# Pipelines

> **Status: ✅ Atual (local, R$0)** for dbt orchestration; 🔭 for Airflow-in-Docker.

## What lives where

| Concern | Location | Status |
|---|---|---|
| CI/CD (GitHub Actions) | `.github/workflows/ci.yml` | ✅ Atual |
| dbt orchestration DAG | `src/airflow/dags/hybrid_medallion_lakehouse_dbt.py` | ✅ Atual (parses without Airflow via lazy Variables) |
| Local make targets | `Makefile` (`dbt-build`, `e2e-local`, `test-py`) | ✅ Atual |
| Airflow runtime (Docker) | `docker-compose.airflow.yml` + `Dockerfile.airflow` | 🔭 Alvo (needs Docker) |
| Orchestration stubs | `ci-cd/`, `orchestration/` | placeholders (empty by design) |

## Local path (R$0)

```bash
make e2e-local   # fixtures + dbt build + pytest
```

## Airflow path (optional)

```bash
docker compose -f docker-compose.airflow.yml up -d
```

See `src/airflow/README.md` for DAG variables and task graph.
