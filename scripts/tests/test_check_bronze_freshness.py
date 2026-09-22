"""Tests for scripts/check_bronze_freshness.py."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts import check_bronze_freshness as cbf


def _touch(path: Path, age_hours: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"PAR1fake")
    mtime = datetime.now(UTC) - timedelta(hours=age_hours)
    ts = mtime.timestamp()
    os.utime(path, (ts, ts))


class TestFindParquetFiles:
    def test_finds_sorted_files(self, tmp_path: Path):
        _touch(tmp_path / "a" / "x.parquet", 1)
        _touch(tmp_path / "b" / "y.parquet", 1)
        files = cbf.find_parquet_files(tmp_path)
        assert len(files) == 2
        assert files == sorted(files)

    def test_empty_dir(self, tmp_path: Path):
        assert cbf.find_parquet_files(tmp_path) == []

    def test_ignores_non_parquet(self, tmp_path: Path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "notes.txt").write_text("x")
        assert cbf.find_parquet_files(tmp_path) == []


class TestNewestMtime:
    def test_returns_newest(self, tmp_path: Path):
        old = tmp_path / "old.parquet"
        new = tmp_path / "new.parquet"
        _touch(old, 48)
        _touch(new, 1)
        result = cbf.newest_mtime([old, new])
        assert result.tzinfo is not None
        age = datetime.now(UTC) - result
        assert age < timedelta(hours=2)


class TestCheckFreshness:
    def test_fresh_returns_zero(self, tmp_path: Path, monkeypatch, capsys):
        _touch(tmp_path / "t" / "fresh.parquet", 1)
        monkeypatch.setattr(cbf, "BRONZE_DIR", tmp_path)
        assert cbf.check_freshness(24, 48) == 0
        assert "OK" in capsys.readouterr().out

    def test_warn_returns_zero(self, tmp_path: Path, monkeypatch, capsys):
        _touch(tmp_path / "t" / "aging.parquet", 30)
        monkeypatch.setattr(cbf, "BRONZE_DIR", tmp_path)
        assert cbf.check_freshness(24, 48) == 0
        assert "WARN" in capsys.readouterr().err

    def test_stale_returns_one(self, tmp_path: Path, monkeypatch, capsys):
        _touch(tmp_path / "t" / "stale.parquet", 72)
        monkeypatch.setattr(cbf, "BRONZE_DIR", tmp_path)
        assert cbf.check_freshness(24, 48) == 1
        assert "ERROR" in capsys.readouterr().err

    def test_no_files_returns_one(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.setattr(cbf, "BRONZE_DIR", tmp_path)
        assert cbf.check_freshness(24, 48) == 1
        assert "no parquet" in capsys.readouterr().err


class TestCli:
    def test_parse_args_defaults(self):
        args = cbf.parse_args([])
        assert args.warn_hours == 24.0
        assert args.error_hours == 48.0

    def test_parse_args_custom(self):
        args = cbf.parse_args(["--warn-hours", "6", "--error-hours", "12"])
        assert args.warn_hours == 6.0
        assert args.error_hours == 12.0

    def test_main_uses_bronze_dir(self, tmp_path: Path, monkeypatch, capsys):
        _touch(tmp_path / "t" / "fresh.parquet", 0.5)
        monkeypatch.setattr(cbf, "BRONZE_DIR", tmp_path)
        assert cbf.main([]) == 0
