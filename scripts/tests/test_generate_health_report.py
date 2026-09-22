"""Tests for scripts/generate_health_report.py."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_health_report as ghr


class TestSummarize:
    def test_counts_statuses(self):
        results = [
            {"status": "pass"},
            {"status": "success"},
            {"status": "warn"},
            {"status": "error"},
            {"status": "fail"},
            {"status": "skipped"},
        ]
        counts = ghr.summarize(results)
        assert counts == {"PASS": 2, "WARN": 1, "ERROR": 2, "SKIP": 1}

    def test_empty(self):
        assert ghr.summarize([]) == {"PASS": 0, "WARN": 0, "ERROR": 0, "SKIP": 0}


class TestFailingTests:
    def test_returns_only_failures(self):
        results = [
            {"status": "pass", "unique_id": "a"},
            {"status": "warn", "unique_id": "b"},
            {"status": "error", "unique_id": "c"},
            {"status": "fail", "unique_id": "d"},
        ]
        failing = ghr.failing_tests(results)
        assert [r["unique_id"] for r in failing] == ["b", "c", "d"]

    def test_none_failing(self):
        assert ghr.failing_tests([{"status": "pass"}]) == []


class TestTestName:
    def test_extracts_last_segment(self):
        assert ghr.test_name("test.project.assert_gold_recency") == "assert_gold_recency"

    def test_no_dots(self):
        assert ghr.test_name("solo") == "solo"


class TestParseAlertManifest:
    def test_parses_real_manifest(self):
        text = (ghr.ALERTS_MANIFEST).read_text(encoding="utf-8")
        alerts = ghr.parse_alert_manifest(text)
        names = {a["name"] for a in alerts}
        assert {"gold_recency_lag", "late_data_gap", "revenue_negative", "bronze_stale"} <= names

    def test_parses_scalars(self):
        text = """
alerts:
  - name: demo
    test: assert_x
    severity: error
    warn_hours: 6
"""
        alerts = ghr.parse_alert_manifest(text)
        assert alerts == [
            {"name": "demo", "test": "assert_x", "severity": "error", "warn_hours": "6"}
        ]

    def test_empty(self):
        assert ghr.parse_alert_manifest("") == []


class TestRenderMarkdown:
    def test_all_pass(self):
        md = ghr.render_markdown(
            {"PASS": 3, "WARN": 0, "ERROR": 0, "SKIP": 0}, [], [], "2026-09", []
        )
        assert "PASS=3" in md
        assert "None — all tests passed." in md
        assert "No Bronze parquet files found." in md

    def test_failing_with_revenue_note(self):
        failing = [
            {
                "status": "warn",
                "unique_id": "t.assert_revenue_not_negative",
                "message": "1 failing",
            }
        ]
        md = ghr.render_markdown(
            {"PASS": 1, "WARN": 1, "ERROR": 0, "SKIP": 0},
            failing,
            [{"name": "revenue_negative", "test": "assert_revenue_not_negative"}],
            "unknown",
            [("data/bronze/x.parquet", "2026-09-01T00:00:00+00:00", "1 day")],
        )
        assert "assert_revenue_not_negative" in md
        assert "warn by design" in md
        assert "revenue_negative" in md
        assert "data/bronze/x.parquet" in md


class TestMain:
    def test_missing_run_results_returns_1(self, tmp_path: Path, capsys):
        rc = ghr.main(["--run-results", str(tmp_path / "nope.json"), "--out", str(tmp_path / "o.md")])
        assert rc == 1
        assert "not found" in capsys.readouterr().err

    def test_writes_report(self, tmp_path: Path):
        run_results = tmp_path / "run_results.json"
        run_results.write_text(
            json.dumps(
                {
                    "results": [
                        {"status": "pass", "unique_id": "a.pass"},
                        {"status": "warn", "unique_id": "b.assert_revenue_not_negative"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        out = tmp_path / "health.md"
        rc = ghr.main(["--run-results", str(run_results), "--out", str(out)])
        assert rc == 0
        content = out.read_text(encoding="utf-8")
        assert "PASS=1" in content
        assert "WARN=1" in content

    def test_results_not_list_is_tolerated(self, tmp_path: Path):
        run_results = tmp_path / "run_results.json"
        run_results.write_text(json.dumps({"results": "corrupt"}), encoding="utf-8")
        out = tmp_path / "health.md"
        assert ghr.main(["--run-results", str(run_results), "--out", str(out)]) == 0
        assert out.is_file()
