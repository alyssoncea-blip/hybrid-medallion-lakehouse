"""generate_health_report.py

Health report generator (standard library only).

Reads the alert manifest (observability/alerts/gold_alerts.yml) and a dbt
run_results.json, then writes a Markdown health summary with PASS/WARN/ERROR
counts, failing tests (with a synthetic-data note for revenue negatives),
max Gold ano_mes and Bronze file mtimes.

max_ano_mes is best-effort: when the `duckdb` package is importable (it ships
with dbt-duckdb in the dbt-build-local CI job) and the local DuckDB file
resolves via DBT_DUCKDB_PATH (CI) or data/lakehouse.duckdb (local default),
the script queries max(ano_mes) from gld_vendas__receita_mensal; otherwise it
reports "unknown". No new dependencies are required.

Usage:
    python scripts/generate_health_report.py --run-results <path> --out <path>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALERTS_MANIFEST = ROOT / "observability" / "alerts" / "gold_alerts.yml"
BRONZE_DIR = ROOT / "data" / "bronze"
GOLD_TABLE = "gld_vendas__receita_mensal"
REVENUE_TEST = "assert_revenue_not_negative"

try:
    import duckdb  # type: ignore[import-not-found]
except ImportError:
    duckdb = None  # type: ignore[assignment]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-results", required=True, help="Path to dbt run_results.json")
    parser.add_argument("--out", required=True, help="Path to write the Markdown report")
    return parser.parse_args(argv)


def load_run_results(path: Path) -> dict[str, object]:
    """Load and return the parsed run_results.json document."""
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def parse_alert_manifest(text: str) -> list[dict[str, str]]:
    """Minimally parse the known alert-manifest shape (no PyYAML; stdlib only).

    Returns one dict per `- name:` entry with the scalar keys found
    (name/test/severity/window/reason) plus warn_hours/error_hours when set.
    """
    alerts: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        name_match = re.match(r"\s*-\s*name:\s*(\S+)\s*$", line)
        if name_match:
            current = {"name": name_match.group(1)}
            alerts.append(current)
            continue
        if current is None:
            continue
        kv_match = re.match(
            r"\s*(test|severity|window|reason|warn_hours|error_hours):\s*(.+?)\s*$", line
        )
        if kv_match:
            current[kv_match.group(1)] = kv_match.group(2)
    return alerts


def test_name(unique_id: str) -> str:
    """Extract the short test name from a dbt unique_id."""
    return unique_id.rsplit(".", 1)[-1]


def summarize(results: list[dict[str, object]]) -> dict[str, int]:
    """Count dbt results as PASS/WARN/ERROR/SKIP buckets."""
    counts = {"PASS": 0, "WARN": 0, "ERROR": 0, "SKIP": 0}
    for result in results:
        status = str(result.get("status", "")).lower()
        if status in ("pass", "success"):
            counts["PASS"] += 1
        elif status == "warn":
            counts["WARN"] += 1
        elif status in ("error", "fail"):
            counts["ERROR"] += 1
        else:
            counts["SKIP"] += 1
    return counts


def failing_tests(results: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return non-passing results (warn/error/fail), preserving run order."""
    failing = []
    for result in results:
        if str(result.get("status", "")).lower() in ("warn", "error", "fail"):
            failing.append(result)
    return failing


def resolve_duckdb_path() -> Path | None:
    """Resolve the local DuckDB file via DBT_DUCKDB_PATH or the repo default."""
    env_path = os.environ.get("DBT_DUCKDB_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path)
    default_path = ROOT / "data" / "lakehouse.duckdb"
    if default_path.is_file():
        return default_path
    return None


def query_max_ano_mes() -> str:
    """Return max(ano_mes) from the Gold table, or 'unknown' when unavailable."""
    if duckdb is None:
        return "unknown (duckdb package not available)"
    db_path = resolve_duckdb_path()
    if db_path is None:
        return "unknown (no local DuckDB file found)"
    try:
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            row = con.execute(f"select max(ano_mes) from {GOLD_TABLE}").fetchone()
        finally:
            con.close()
    except duckdb.Error as exc:
        return f"unknown ({exc})"
    if not row or row[0] is None:
        return "unknown (empty gold table)"
    return str(row[0])


def bronze_mtimes() -> list[tuple[str, str, str]]:
    """Return (relative path, iso mtime, age) for each Bronze parquet file."""
    entries: list[tuple[str, str, str]] = []
    now = datetime.now(UTC)
    for path in sorted(BRONZE_DIR.glob("*/*.parquet")):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        entries.append((path.relative_to(ROOT).as_posix(), mtime.isoformat(), str(now - mtime)))
    return entries


def render_markdown(
    counts: dict[str, int],
    failing: list[dict[str, object]],
    alerts: list[dict[str, str]],
    max_ano_mes_value: str,
    mtimes: list[tuple[str, str, str]],
) -> str:
    """Render the health report Markdown."""
    alert_by_test = {a["test"]: a for a in alerts if "test" in a}
    lines = [
        "# Lakehouse Health Report",
        "",
        f"PASS={counts['PASS']} WARN={counts['WARN']} ERROR={counts['ERROR']}",
        "",
        f"SKIP={counts['SKIP']}",
        "",
        "## Failing tests",
        "",
    ]
    if not failing:
        lines.append("None — all tests passed.")
    else:
        for result in failing:
            name = test_name(str(result.get("unique_id", "?")))
            status = str(result.get("status", "?")).upper()
            message = str(result.get("message", "")).strip()
            alert = alert_by_test.get(name, {})
            alert_name = alert.get("name", "n/a")
            lines.append(f"- **{name}** [{status}] (alert: {alert_name}) {message}".rstrip())
            if name == REVENUE_TEST:
                lines.append(
                    "  - Note: warn by design — the synthetic fixture generator "
                    "produces negative-revenue (canal, cliente, month) combinations."
                )
    lines += ["", "## Gold recency", "", f"max_ano_mes: {max_ano_mes_value}", "", "## Bronze mtimes", ""]
    if not mtimes:
        lines.append("No Bronze parquet files found.")
    else:
        for rel, iso, age in mtimes:
            lines.append(f"- {rel}: mtime={iso} age={age}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    run_results_path = Path(args.run_results)
    if not run_results_path.is_file():
        print(f"ERROR: run_results not found: {run_results_path}", file=sys.stderr)
        return 1
    manifest_text = (
        ALERTS_MANIFEST.read_text(encoding="utf-8") if ALERTS_MANIFEST.is_file() else ""
    )
    alerts = parse_alert_manifest(manifest_text)
    document = load_run_results(run_results_path)
    raw_results = document.get("results", [])
    results = raw_results if isinstance(raw_results, list) else []
    typed_results: list[dict[str, object]] = [r for r in results if isinstance(r, dict)]
    counts = summarize(typed_results)
    failing = failing_tests(typed_results)
    report = render_markdown(counts, failing, alerts, query_max_ano_mes(), bronze_mtimes())
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Health report written to {out_path} " f"(PASS={counts['PASS']} WARN={counts['WARN']} ERROR={counts['ERROR']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
