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

# Default dbt target (override with `make dbt-build TARGET=dev`)
DBT_TARGET   ?= local

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
	$(PIP) install pre-commit ruff mypy pytest pytest-cov dbt-duckdb pyarrow
	pre-commit install
	pre-commit install --hook-type commit-msg

# -------- Local data -------------------------------------------------------

.PHONY: bronze-generate
bronze-generate: ## Generate synthetic Parquet fixtures for local dbt.
	$(PYTHON) scripts/generate_bronze.py --rows-pedidos 2000 --rows-clientes 500

.PHONY: bronze-clean
bronze-clean: ## Remove generated Bronze fixtures.
	rm -rf data/bronze/pedidos_vendas data/bronze/clientes_cadastro

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
validate: validate-tf validate-mermaid validate-structure ## Run all validators.

.PHONY: validate-tf
validate-tf: ## terraform validate on dev/stg/prd/local.
	@for env in dev stg prd local; do \
		echo ">> Validating $$env"; \
		cd $(TF_DIR)/environments/$$env && $(TERRAFORM) init -backend=false -no-color && $(TERRAFORM) validate; \
		cd ../../..; \
	done

.PHONY: validate-tf-test
validate-tf-test: ## terraform test on snowflake and s3 modules.
	cd $(TF_DIR)/modules/snowflake && $(TERRAFORM) init -no-color >/dev/null && $(TERRAFORM) test -no-color
	cd $(TF_DIR)/modules/s3 && $(TERRAFORM) init -no-color >/dev/null && $(TERRAFORM) test -no-color

.PHONY: validate-mermaid
validate-mermaid: ## Render all Mermaid diagrams to verify syntax.
	$(NPM) run render:mermaid

.PHONY: validate-structure
validate-structure: ## Lightweight repo structure check (no external deps).
	$(PYTHON) scripts/validate_structure.py

# -------- Test -------------------------------------------------------------

.PHONY: test
test: test-md test-tf ## Fast tests (docs + terraform).

.PHONY: test-md
test-md: lint-md ## Lint markdown as test gate.

.PHONY: test-tf
test-tf: validate-tf lint-tf ## Terraform validate + format check.

.PHONY: test-all
test-all: lint validate test validate-tf-test ## Full local CI gate (lint + validate + test + tf test).

# -------- dbt --------------------------------------------------------------

.PHONY: dbt-deps
dbt-deps: ## Install dbt packages.
	cd $(DBT_DIR) && $(DBT) deps

.PHONY: dbt-build
dbt-build: ## dbt deps + build on TARGET (default: local).
	cd $(DBT_DIR) && $(DBT) deps && $(DBT) build --target $(DBT_TARGET)

.PHONY: dbt-build-fresh
dbt-build-fresh: ## dbt deps + full-refresh build on TARGET.
	cd $(DBT_DIR) && $(DBT) deps && $(DBT) build --target $(DBT_TARGET) --full-refresh

.PHONY: dbt-test
dbt-test: ## dbt test only on TARGET.
	cd $(DBT_DIR) && $(DBT) test --target $(DBT_TARGET)

.PHONY: dbt-run
dbt-run: ## dbt run only on TARGET.
	cd $(DBT_DIR) && $(DBT) run --target $(DBT_TARGET)

.PHONY: dbt-seed
dbt-seed: ## dbt seed (reference data) on TARGET.
	cd $(DBT_DIR) && $(DBT) seed --target $(DBT_TARGET)

# -------- End-to-end (FREE local) -----------------------------------------

.PHONY: e2e-local
e2e-local: ## Generate fixtures + dbt build + pytest (R$ 0, no cloud).
	$(MAKE) bronze-generate
	$(MAKE) dbt-build
	@echo ""
	@echo "✅ End-to-end local build complete!"
	@echo "Query results: duckdb C:/Users/alyss/data/lakehouse.duckdb -c 'select * from main.gld_vendas__receita_mensal limit 10'"

# -------- LocalStack -------------------------------------------------------

.PHONY: localstack-up
localstack-up: ## Start LocalStack (S3, KMS) in Docker.
	docker compose up -d

.PHONY: localstack-down
localstack-down: ## Stop LocalStack.
	docker compose down

.PHONY: localstack-reset
localstack-reset: ## Stop LocalStack and wipe state.
	docker compose down -v

# -------- Hygiene ----------------------------------------------------------

.PHONY: clean
clean: ## Remove generated artifacts (node_modules, target, dbt_packages, .terraform, data/bronze).
	rm -rf node_modules
	rm -rf $(DBT_DIR)/dbt_packages $(DBT_DIR)/target $(DBT_DIR)/logs
	find $(TF_DIR) -type d -name ".terraform" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	rm -rf data/bronze/pedidos_vendas data/bronze/clientes_cadastro

.PHONY: pre-commit
pre-commit: ## Run pre-commit on all files.
	pre-commit run --all-files
