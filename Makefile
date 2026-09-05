# Hybrid Medallion Lakehouse — Makefile
# Use `make help` to list targets. Compatible with GNU Make and PowerShell via `make.bat`.

# -------- Variables --------------------------------------------------------

PYTHON       ?= python
PIP          ?= $(PYTHON) -m pip
TERRAFORM    ?= terraform
DBT          ?= dbt
NODE         ?= node
NPM          ?= npm
MMDC         ?= npx -p @mermaid-js/mermaid-cli mmdc

DOCS_DIR     := .
TF_DIR       := src/terraform
DBT_DIR      := src/dbt
SCRIPTS_DIR  := scripts

# -------- Default target ---------------------------------------------------

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help.
	@$(NODE) scripts/show-help.mjs

# -------- Setup ------------------------------------------------------------

.PHONY: setup
setup: setup-node setup-python ## Install all dev tooling (Node + Python).

.PHONY: setup-node
setup-node: ## Install Node-based linters (markdownlint, mermaid-cli, cspell).
	$(NPM) install

.PHONY: setup-python
setup-python: ## Install Python dev tools (ruff, mypy, pytest, pre-commit).
	$(PIP) install --upgrade pip
	$(PIP) install pre-commit ruff mypy pytest pytest-cov
	pre-commit install
	pre-commit install --hook-type commit-msg

# -------- Lint -------------------------------------------------------------

.PHONY: lint
lint: lint-md lint-tf lint-py ## Run all linters.

.PHONY: lint-md
lint-md: ## Lint Markdown files.
	$(NPM) run lint:md

.PHONY: lint-md-fix
lint-md-fix: ## Lint and auto-fix Markdown files.
	$(NPM) run lint:md:fix

.PHONY: lint-tf
lint-tf: ## Check Terraform formatting.
	$(TERRAFORM) fmt -check -recursive $(TF_DIR)

.PHONY: lint-tf-fix
lint-tf-fix: ## Auto-format Terraform code.
	$(TERRAFORM) fmt -recursive $(TF_DIR)

.PHONY: lint-py
lint-py: ## Lint Python (ruff + mypy).
	ruff check $(DBT_DIR) src/snowpark scripts 2>/dev/null || true
	mypy --ignore-missing-imports $(DBT_DIR) src/snowpark 2>/dev/null || true

# -------- Validate ---------------------------------------------------------

.PHONY: validate
validate: validate-tf validate-mermaid ## Run all validators.

.PHONY: validate-tf
validate-tf: ## terraform init + validate on every environment.
	@for env in dev stg prd; do \
		echo ">> Validating $$env"; \
		cd $(TF_DIR)/environments/$$env && $(TERRAFORM) init -backend=false -no-color && $(TERRAFORM) validate; \
		cd ../../..; \
	done

.PHONY: validate-mermaid
validate-mermaid: ## Render all Mermaid diagrams to verify syntax.
	$(NPM) run render:mermaid

# -------- Test -------------------------------------------------------------

.PHONY: test
test: test-md test-tf ## Run fast tests (docs + terraform).

.PHONY: test-md
test-md: lint-md ## Lint markdown as test gate.

.PHONY: test-tf
test-tf: validate-tf lint-tf ## Terraform validate + format check.

.PHONY: test-all
test-all: lint validate test ## Full local CI gate (lint + validate + test).

# -------- dbt --------------------------------------------------------------

.PHONY: dbt-deps
dbt-deps: ## Install dbt packages.
	cd $(DBT_DIR) && $(DBT) deps

.PHONY: dbt-build
dbt-build: ## dbt deps + run + test on dev target.
	cd $(DBT_DIR) && $(DBT) deps && $(DBT) build --target dev

.PHONY: dbt-test
dbt-test: ## dbt test only (uses selected target).
	cd $(DBT_DIR) && $(DBT) test

# -------- Hygiene ----------------------------------------------------------

.PHONY: clean
clean: ## Remove generated artifacts (node_modules, target, dbt_packages, .terraform).
	rm -rf node_modules
	rm -rf $(DBT_DIR)/dbt_packages $(DBT_DIR)/target $(DBT_DIR)/logs
	find $(TF_DIR) -type d -name ".terraform" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

.PHONY: pre-commit
pre-commit: ## Run pre-commit on all files.
	pre-commit run --all-files
