"""
Unit tests for the hybrid_medallion_lakehouse_dbt DAG.

Run: pytest src/airflow/tests/test_dag.py -v

Note: These tests require airflow to be installed.
Run inside Airflow container: docker compose -f docker-compose.airflow.yml exec airflow pytest src/airflow/tests/test_dag.py -v
"""
import sys
from pathlib import Path

import pytest

# Skip tests if airflow not installed (local dev environment)
try:
    import airflow  # noqa: F401
except ImportError:
    pytest.skip("Airflow not installed - run tests inside Airflow container", allow_module_level=True)

# Add dags directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "dags"))

from hybrid_medallion_lakehouse_dbt import dag  # noqa: E402


def test_dag_loaded():
    """Test that DAG loads without errors."""
    assert dag is not None
    assert dag.dag_id == "hybrid_medallion_lakehouse_dbt"


def test_dag_schedule():
    """Test DAG schedule is daily at 06:00 UTC."""
    assert dag.schedule_interval == "0 6 * * *"


def test_dag_default_args():
    """Test default args are set correctly."""
    assert dag.default_args["owner"] == "data-engineering"
    assert dag.default_args["retries"] == 1
    assert dag.default_args["retry_delay"].total_seconds() == 300


def test_dag_catchup_false():
    """Test catchup is disabled."""
    assert dag.catchup is False


def test_dag_max_active_runs():
    """Test max_active_runs is 1."""
    assert dag.max_active_runs == 1


def test_dag_tags():
    """Test DAG has expected tags."""
    expected_tags = {"dbt", "lakehouse", "medallion", "hybrid"}
    assert set(dag.tags) == expected_tags


def test_task_count():
    """Test DAG has expected number of tasks."""
    # start, end, validate_profile, print_version, dbt_deps, dbt_build, dbt_test, dbt_docs, dbt_source_freshness
    expected_task_ids = {
        "start",
        "end",
        "validate_dbt_profile",
        "print_dbt_version",
        "dbt_deps",
        "dbt_build",
        "dbt_test",
        "dbt_docs_generate",
        "dbt_source_freshness",
    }
    actual_task_ids = {task.task_id for task in dag.tasks}
    assert actual_task_ids == expected_task_ids


def test_task_dependencies():
    """Test task dependencies are correct."""
    task_map = {task.task_id: task for task in dag.tasks}
    
    # start -> validate_profile, print_version
    assert task_map["start"].downstream_task_ids == {"validate_dbt_profile", "print_dbt_version"}
    
    # validate_profile, print_version -> dbt_deps
    assert task_map["validate_dbt_profile"].downstream_task_ids == {"dbt_deps"}
    assert task_map["print_dbt_version"].downstream_task_ids == {"dbt_deps"}
    
    # dbt_deps -> dbt_build -> dbt_test -> dbt_docs
    assert task_map["dbt_deps"].downstream_task_ids == {"dbt_build"}
    assert task_map["dbt_build"].downstream_task_ids == {"dbt_test"}
    assert task_map["dbt_test"].downstream_task_ids == {"dbt_docs_generate"}
    
    # dbt_docs, dbt_source_freshness -> end
    assert task_map["dbt_docs_generate"].downstream_task_ids == {"dbt_source_freshness"}
    assert task_map["dbt_source_freshness"].downstream_task_ids == {"end"}
    
    # end has no downstream
    assert task_map["end"].downstream_task_ids == set()


def test_dbt_tasks_use_correct_env():
    """Test dbt tasks have required environment variables."""
    task_map = {task.task_id: task for task in dag.tasks}
    
    for task_id in ["dbt_deps", "dbt_build", "dbt_test", "dbt_docs_generate", "dbt_source_freshness"]:
        task = task_map[task_id]
        assert isinstance(task, __import__("airflow.operators.bash", fromlist=["BashOperator"]).BashOperator)
        assert "DBT_PROFILES_DIR" in task.env
        assert "DBT_TARGET" in task.env


if __name__ == "__main__":
    pytest.main([__file__, "-v"])