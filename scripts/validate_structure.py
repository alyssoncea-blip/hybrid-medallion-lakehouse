#!/usr/bin/env python
"""
scripts/validate_structure.py

Lightweight structural validator that runs WITHOUT requiring terraform/dbt/npm.
It checks:

  1. Required files exist
  2. .gitignore is present and non-empty
  3. All .tf files are syntactically valid (balanced braces, no obvious typos)
  4. All .yml / .yaml files parse
  5. All .json files parse
  6. Mermaid blocks in Markdown open and close correctly
  7. Conventional Commits messages in the git log

Exit code 0 on success, 1 on any failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "README.md",
    "01-project-charter.md",
    "02-architecture-design.md",
    "03-implementation-roadmap.md",
    "04-data-governance-framework.md",
    "05-risks-and-compliance.md",
    "CHANGELOG.md",
    "package.json",
    "Makefile",
    ".gitignore",
    ".env.example",
    ".markdownlint.jsonc",
    ".commitlintrc.yml",
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "src/dbt/dbt_project.yml",
    "src/dbt/profiles.yml.example",
    "src/dbt/packages.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/pre-commit.yml",
    "src/terraform/environments/local/main.tf",
    "src/terraform/environments/dev/main.tf",
    "src/terraform/environments/stg/main.tf",
    "src/terraform/environments/prd/main.tf",
    "src/terraform/modules/snowflake/warehouses.tf",
    "src/terraform/modules/snowflake/databases.tf",
    "src/terraform/modules/snowflake/roles.tf",
    "src/terraform/modules/snowflake/versions.tf",
    "src/terraform/modules/snowflake/outputs.tf",
    "src/terraform/modules/snowflake/tests/warehouses.tftest.hcl",
    "src/terraform/modules/s3/buckets.tf",
    "src/terraform/modules/s3/tests/buckets.tftest.hcl",
]


def banner(title: str) -> None:
    print(f"\n=== {title} ===")


def ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")


def check_required_files() -> int:
    banner("Required files")
    failures = 0
    for rel in REQUIRED_FILES:
        p = REPO_ROOT / rel
        if p.is_file() and p.stat().st_size > 0:
            ok(rel)
        else:
            fail(f"Missing or empty: {rel}")
            failures += 1
    return failures


def check_gitignore() -> int:
    banner(".gitignore")
    p = REPO_ROOT / ".gitignore"
    if not p.is_file():
        fail(".gitignore missing")
        return 1
    content = p.read_text(encoding="utf-8")
    required_patterns = [".terraform/", "*.tfstate", "dbt_packages/", "target/", "__pycache__/", ".env"]
    failures = 0
    for pat in required_patterns:
        if pat in content:
            ok(f"Pattern present: {pat}")
        else:
            fail(f"Pattern missing: {pat}")
            failures += 1
    return failures


def check_tf_syntax() -> int:
    banner("Terraform syntax (lightweight)")
    failures = 0
    tf_files = list(REPO_ROOT.rglob("*.tf"))
    tftest_files = list(REPO_ROOT.rglob("*.tftest.hcl"))
    for tf in tf_files + tftest_files:
        text = tf.read_text(encoding="utf-8")
        # Count braces and check balance
        opens = text.count("{")
        closes = text.count("}")
        if opens != closes:
            fail(f"Unbalanced braces in {tf.relative_to(REPO_ROOT)}: {opens} '{{' vs {closes} '}}'")
            failures += 1
        else:
            ok(f"Braces balanced: {tf.relative_to(REPO_ROOT)}")
        # Look for obvious typos
        for typo in ["resoruce", "provsioner", "databse", "acount"]:
            if typo in text:
                fail(f"Possible typo '{typo}' in {tf.relative_to(REPO_ROOT)}")
                failures += 1
    return failures


def check_yaml_files() -> int:
    banner("YAML / JSON parse")
    failures = 0

    # Try PyYAML; if not installed, fall back to a permissive regex check
    try:
        import yaml  # type: ignore

        parser = yaml.safe_load
    except ImportError:
        parser = None

    for ext in ("*.yml", "*.yaml"):
        for f in REPO_ROOT.rglob(ext):
            # Skip vendored / generated
            if any(part in f.parts for part in ("node_modules", ".terraform", "dbt_packages", "target")):
                continue
            try:
                if parser:
                    parser(f.read_text(encoding="utf-8"))
                    ok(f"YAML parses: {f.relative_to(REPO_ROOT)}")
                else:
                    # Fallback: just check basic structure
                    text = f.read_text(encoding="utf-8")
                    if text.count(":") < 1:
                        fail(f"YAML looks empty: {f.relative_to(REPO_ROOT)}")
                        failures += 1
                    else:
                        ok(f"YAML structure OK (fallback): {f.relative_to(REPO_ROOT)}")
            except Exception as exc:
                fail(f"YAML parse error in {f.relative_to(REPO_ROOT)}: {exc}")
                failures += 1

    for f in REPO_ROOT.rglob("*.json"):
        if any(part in f.parts for part in ("node_modules", ".terraform", "dbt_packages", "target")):
            continue
        try:
            json.loads(f.read_text(encoding="utf-8"))
            ok(f"JSON parses: {f.relative_to(REPO_ROOT)}")
        except Exception as exc:
            fail(f"JSON parse error in {f.relative_to(REPO_ROOT)}: {exc}")
            failures += 1
    return failures


def check_mermaid_blocks() -> int:
    banner("Mermaid block balance")
    failures = 0
    md_files = list(REPO_ROOT.rglob("*.md"))
    for md in md_files:
        text = md.read_text(encoding="utf-8")
        # Iterate fenced blocks to count balanced fences and mermaid openers
        in_block = False
        block_lang = None
        opens = 0
        closes = 0
        for line in text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("```"):
                if not in_block:
                    in_block = True
                    lang = stripped[3:].strip().lower()
                    block_lang = lang
                    if lang == "mermaid":
                        opens += 1
                else:
                    in_block = False
                    if block_lang == "mermaid":
                        closes += 1
                    block_lang = None
        if opens == 0:
            continue
        if opens != closes:
            fail(
                f"Mermaid blocks unbalanced in {md.relative_to(REPO_ROOT)}: {opens} ```mermaid vs {closes} closing ```"
            )
            failures += 1
        else:
            ok(f"{opens} mermaid block(s) balanced in {md.relative_to(REPO_ROOT)}")
    return failures


def check_dbt_models_have_yml() -> int:
    banner("dbt models have schema yml")
    failures = 0
    models_root = REPO_ROOT / "src" / "dbt" / "models"
    if not models_root.is_dir():
        fail("src/dbt/models directory missing")
        return 1
    for layer_dir in ("bronze", "silver", "gold"):
        layer = models_root / layer_dir
        if not layer.is_dir():
            continue
        sql_files = [p for p in layer.glob("*.sql") if not p.name.startswith("_")]
        yml_files = list(layer.glob("*.yml"))
        if not sql_files:
            continue
        if not yml_files:
            fail(f"Layer {layer_dir} has {len(sql_files)} .sql models but no schema .yml file")
            failures += 1
            continue
        ok(f"Layer {layer_dir} has {len(sql_files)} model(s) and {len(yml_files)} schema file(s)")
        # Check that each model is documented in some yml
        for sql in sql_files:
            model_name = sql.stem
            documented = any(model_name in y.read_text(encoding="utf-8") for y in yml_files)
            if not documented:
                fail(f"Model {model_name}.sql not documented in any .yml in {layer_dir}/")
                failures += 1
            else:
                ok(f"Model {model_name} documented")
    return failures


def check_tests_exist() -> int:
    banner("dbt tests and Terraform tests")
    failures = 0
    dbt_tests = list((REPO_ROOT / "src" / "dbt" / "tests").glob("*.sql"))
    if len(dbt_tests) >= 1:
        ok(f"Found {len(dbt_tests)} dbt singular test(s)")
    else:
        fail("No dbt singular tests in src/dbt/tests/")
        failures += 1
    tf_tests = list(REPO_ROOT.rglob("*.tftest.hcl"))
    if len(tf_tests) >= 1:
        ok(f"Found {len(tf_tests)} Terraform test file(s)")
    else:
        fail("No Terraform test files (*.tftest.hcl)")
        failures += 1
    return failures


def check_commit_messages() -> int:
    banner("Conventional Commits (git log)")
    failures = 0
    import subprocess

    try:
        result = subprocess.run(
            ["git", "log", "--pretty=%s"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  SKIP  git not available or not a repo")
        return 0

    allowed = {
        "feat", "fix", "docs", "style", "refactor",
        "perf", "test", "build", "ci", "chore", "revert",
    }
    pattern = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]+\))?!?:\s.+")
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        m = pattern.match(line)
        if not m or m.group("type") not in allowed:
            fail(f"Non-conventional commit: {line}")
            failures += 1
        else:
            ok(f"Conventional commit: {line[:60]}")
    return failures


def main() -> int:
    print(f"Validating structure of {REPO_ROOT}")
    total = 0
    total += check_required_files()
    total += check_gitignore()
    total += check_tf_syntax()
    total += check_yaml_files()
    total += check_mermaid_blocks()
    total += check_dbt_models_have_yml()
    total += check_tests_exist()
    total += check_commit_messages()

    banner("Summary")
    if total == 0:
        print("  All structural checks passed.")
        return 0
    print(f"  {total} check(s) failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
