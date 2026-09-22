"""Tests for scripts/validate_structure.py (repo-wide gates)."""

from __future__ import annotations

from scripts import validate_structure as vs


class TestRepoGates:
    """The validator is itself a CI gate — assert it passes on this repo."""

    def test_required_files_present(self):
        assert vs.check_required_files() == 0

    def test_gitignore_present(self):
        assert vs.check_gitignore() == 0

    def test_tf_syntax(self):
        assert vs.check_tf_syntax() == 0

    def test_yaml_json_parse(self):
        assert vs.check_yaml_files() == 0

    def test_mermaid_blocks_balanced(self):
        assert vs.check_mermaid_blocks() == 0

    def test_dbt_models_documented(self):
        assert vs.check_dbt_models_have_yml() == 0

    def test_tests_exist(self):
        assert vs.check_tests_exist() == 0

    def test_observability_alerts_resolve(self):
        assert vs.check_observability_alerts() == 0

    def test_no_stray_target_type(self):
        assert vs.check_no_stray_target_type() == 0

    def test_no_inline_windows(self):
        assert vs.check_no_inline_windows() == 0


class TestCommitMessages:
    def test_conventional_commits_pass(self):
        # Repo history is enforced by commitlint + pre-commit; must be clean.
        assert vs.check_commit_messages() == 0
