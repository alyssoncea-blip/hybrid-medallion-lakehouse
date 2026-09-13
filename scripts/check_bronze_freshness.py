"""check_bronze_freshness.py

Local Bronze freshness gate (stdlib only).

NOTE: local file mtime is an ingestion proxy only. The authoritative
freshness check is `dbt source freshness` with warn/error thresholds,
which applies on Snowflake targets (dev/stg/prd). DuckDB local runs do
not support metadata-based freshness, so this script gates CI on the
mtime of the local Parquet fixtures instead.

Exit codes:
  0 - fresh (at least one parquet newer than warn-hours), or stale-but-warn
      (newest parquet older than warn-hours but newer than error-hours;
      prints a warning to stderr).
  1 - stale (no parquet newer than error-hours) or no parquet files found.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRONZE_DIR = ROOT / "data" / "bronze"


def find_parquet_files(bronze_dir: Path) -> list[Path]:
    """Return all Parquet files under <bronze_dir>/*/*.parquet, sorted."""
    return sorted(bronze_dir.glob("*/*.parquet"))


def newest_mtime(files: list[Path]) -> datetime:
    """Return the newest modification time across files (UTC, tz-aware)."""
    latest = max(p.stat().st_mtime for p in files)
    return datetime.fromtimestamp(latest, tz=UTC)


def check_freshness(warn_hours: float, error_hours: float) -> int:
    """Evaluate Bronze freshness; print status and return exit code."""
    now = datetime.now(UTC)
    files = find_parquet_files(BRONZE_DIR)
    if not files:
        print(
            f"ERROR: no parquet files found under {BRONZE_DIR} "
            f"(expected data/bronze/*/*.parquet). "
            "Run scripts/generate_bronze.py to create fixtures.",
            file=sys.stderr,
        )
        return 1
    newest = newest_mtime(files)
    age = now - newest
    error_cutoff = timedelta(hours=error_hours)
    warn_cutoff = timedelta(hours=warn_hours)
    if age > error_cutoff:
        print(
            f"ERROR: bronze fixtures stale: newest parquet is {age} old "
            f"(>{error_hours}h error threshold; newest={newest.isoformat()}, "
            f"files={len(files)}).",
            file=sys.stderr,
        )
        return 1
    if age > warn_cutoff:
        print(
            f"WARN: bronze fixtures aging: newest parquet is {age} old "
            f"(>{warn_hours}h warn threshold; newest={newest.isoformat()}, "
            f"files={len(files)}).",
            file=sys.stderr,
        )
        return 0
    print(
        f"OK: bronze fixtures fresh: newest parquet is {age} old "
        f"(newest={newest.isoformat()}, files={len(files)})."
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-hours", type=float, default=24.0)
    parser.add_argument("--error-hours", type=float, default=48.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    return check_freshness(args.warn_hours, args.error_hours)


if __name__ == "__main__":
    raise SystemExit(main())
