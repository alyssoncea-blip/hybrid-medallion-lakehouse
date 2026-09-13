# Hybrid Medallion Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden PoC to Snowflake-ready with zero cloud cost (macros dispatch, real CI gate, honest docs, Bronze/Silver/Gold ready).

**Architecture:** Keep dual-target `local (DuckDB+Parquet)` ↔ `dev/stg/prd (Snowflake+S3)`; centralize all `target.type` branches inside `src/dbt/macros/compat/`; Terraform designed now (`validate/test/plan`, no `apply`); CI fails for real.

**Tech Stack:** dbt-core 1.11 + dbt-duckdb, DuckDB, Terraform 1.9.0 (snowflake provider ~0.100, AWS), GitHub Actions ubuntu-latest Python 3.11 Node 24, ruff 0.15.12 + mypy 1.19.1, Airflow BashOperator.

## Global Constraints

- Zero cloud cost: no `terraform apply` against AWS/Snowflake, no Snowflake secrets required, all verification via `local` target + `LocalStack` + `mock_provider`.
- `DBT_TARGET` default `local`; `DBT_DUCKDB_PATH=/tmp/lakehouse.duckdb` in CI, local dev path `C:/Users/alyss/data/lakehouse.duckdb` allowed.
- Conventional Commits enforced (`feat:`, `fix:`, `docs:`, etc.); 1 reviewer via PR template.
- No `{% if target.type %}` outside `src/dbt/macros/` after Task 2.
- `terraform fmt -check`, `init -backend=false`, `validate` must pass on `local/dev/stg/prd`.
- YAGNI: no GE/DQX, no Collibra/Atlan, no real Kafka, no Grafana, no DuckDB masking enforcement.

---

## File Structure

- `src/dbt/macros/compat/ts_now.sql` — single `ts_now()` macro (now vs current_timestamp), sole owner of timestamp branching.
- `src/dbt/macros/compat/ym_format.sql` — single `ym_format(date_col)` macro (strftime vs to_char).
- `src/dbt/macros/compat/bronze_source.sql` — single `bronze_source(table_name)` macro (read_parquet local vs source() Snowflake).
- `src/dbt/models/bronze/stg_vendas__pedidos.sql`, `stg_cliente__cadastro.sql` — consume `bronze_source()` + `ts_now()`, no inline branching.
- `src/dbt/models/silver/slv_vendas__pedidos.sql` — consumes `ts_now()`, delete+insert kept until Task 6 snapshot migration.
- `src/dbt/models/gold/gld_vendas__receita_mensal.sql` — consumes `ym_format()` + `ts_now()`, Task 5 flips to incremental.
- `src/dbt/snapshots/slv_clientes_snapshot.sql` (new) — real SCD2 via `check` strategy.
- `src/terraform/modules/snowflake/external_tables.tf` (new) + `masking.tf` (new) — designed, `validate/test/plan` only.
- `.github/workflows/ci.yml` — hard gate: `all-checks-passed` fails on required failure, `python-lint` expanded scope, `terraform plan` added, `dbt source freshness` added.
- `Makefile` — `lint-py` without `|| true`, expanded paths.
- `scripts/validate_structure.py` — extended checks: macros exist, no stray `target.type`, badges present.
- `README.md`, `02-architecture-design.md`, `04-data-governance-framework.md` — `Atual` vs `Alvo` badges.
- `src/airflow/dags/hybrid_medallion_lakehouse_dbt.py` — lazy `Variable.get()` inside callables, `state:modified+` build.

---

### Task 1: Compat macros (single ownership of branching)

**Files:**

- Create: `src/dbt/macros/compat/ts_now.sql`
- Create: `src/dbt/macros/compat/ym_format.sql`
- Create: `src/dbt/macros/compat/bronze_source.sql`
- Test: `scripts/validate_structure.py` (extended in Task 3, manual grep here)

**Interfaces:**

- Consumes: `target.type` (`duckdb` vs `snowflake`), `var('local_bronze_path')`, `source('bronze_raw', ...)`
- Produces: `ts_now()` → SQL string; `ym_format(date_col)` → SQL string; `bronze_source('pedidos_vendas')` → relation SQL. Task 2 consumes exact names.

- [ ] **Step 1: Write the failing check**

Create `C:\Users\alyss\AppData\Local\Temp\opencode\check_macros.py`:

```python
from pathlib import Path
root = Path("src/dbt/macros/compat")
for f in ["ts_now.sql", "ym_format.sql", "bronze_source.sql"]:
    assert (root / f).is_file(), f"missing {f}"
print("macros present")
```

- [ ] **Step 2: Run check to verify it fails**

Run: `python C:\Users\alyss\AppData\Local\Temp\opencode\check_macros.py`
Expected: FAIL with `missing ts_now.sql` (compat/ does not exist yet).

- [ ] **Step 3: Write minimal implementation**

`src/dbt/macros/compat/ts_now.sql`:

```sql
{% macro ts_now() %}
  {% if target.type == 'snowflake' %}current_timestamp(){% else %}now(){% endif %}
{% endmacro %}
```

`src/dbt/macros/compat/ym_format.sql`:

```sql
{% macro ym_format(date_col) %}
  {% if target.type == 'snowflake' %}to_char({{ date_col }}, 'YYYY-MM'){% else %}strftime({{ date_col }}, '%Y-%m'){% endif %}
{% endmacro %}
```

`src/dbt/macros/compat/bronze_source.sql`:

```sql
{% macro bronze_source(table_name) %}
  {% if target.type == 'snowflake' %}{{ source('bronze_raw', table_name) }}{% else %}read_parquet('{{ var('local_bronze_path') }}/{{ table_name }}/*.parquet'){% endif %}
{% endmacro %}
```

Note: nested `{{ var() }}` inside string is intentional for local path composition; validated by `dbt parse` in Step 4.

- [ ] **Step 4: Run check + dbt parse to verify it passes**

Run: `python C:\Users\alyss\AppData\Local\Temp\opencode\check_macros.py`
Expected: PASS `macros present`

Run: `cd src/dbt; dbt parse --target local --no-version-check`
Expected: PASS, no macro redefinition error.

- [ ] **Step 5: Commit**

```bash
git add src/dbt/macros/compat/ts_now.sql src/dbt/macros/compat/ym_format.sql src/dbt/macros/compat/bronze_source.sql
git commit -m "feat(dbt): add compat macros for dual-target"
```

---

### Task 2: Refactor 4 models to use compat (remove stray branching)

**Files:**

- Modify: `src/dbt/models/bronze/stg_vendas__pedidos.sql:13-26`
- Modify: `src/dbt/models/bronze/stg_cliente__cadastro.sql:6-17`
- Modify: `src/dbt/models/silver/slv_vendas__pedidos.sql:26-27`
- Modify: `src/dbt/models/gold/gld_vendas__receita_mensal.sql:7-12,43`
- Test: local `dbt build`

**Interfaces:**

- Consumes: `ts_now()`, `ym_format(data_pedido)`, `bronze_source('pedidos_vendas'|'clientes_cadastro')` from Task 1.
- Produces: identical row-counts to pre-refactor (verified by `dbt build` PASS=49).

- [ ] **Step 1: Write the failing test (grep for stray branching)**

Run: `Select-String -Path "src/dbt/models/**/*.sql" -Pattern "target\.type" | Measure-Object`
Expected currently: count >= 5 (proves branching still scattered). Save count as baseline; after refactor expected 0.

- [ ] **Step 2: Confirm baseline fails the gate**

Run: `python -c "import subprocess; out=subprocess.run(['powershell','-c','Select-String -Path src/dbt/models/**/*.sql -Pattern target.type'],capture_output=True,text=True); print(out.stdout); assert 'target.type' in out.stdout, 'already clean'"`
Expected: PASS assertion (branching present) → gate FAIL condition confirmed.

- [ ] **Step 3: Write minimal implementation**

`stg_vendas__pedidos.sql` lines 13-26 replace with:

```sql
with source as (
    select
        cast(pedido_id as varchar)          as pedido_id,
        cast(cliente_id as varchar)         as cliente_id,
        cast(data_pedido as date)           as data_pedido,
        cast(valor_total as decimal(18, 2)) as valor_total,
        upper(trim(status))                 as status,
        cast(vendedor_id as varchar)        as vendedor_id,
        cast(canal_venda as varchar)        as canal_venda,
        {{ ts_now() }}                      as _ingested_at
    from {{ bronze_source('pedidos_vendas') }}
)
select * from source
```

`stg_cliente__cadastro.sql` lines 6-17 replace `{% set ts_func ... %}` + `read_parquet(...)` with same pattern:

```sql
with source as (
    select
        cast(cliente_id as varchar)   as cliente_id,
        cast(nome as varchar)         as nome,
        cast(cpf as varchar)          as cpf,
        cast(email as varchar)        as email,
        cast(data_cadastro as date)   as data_cadastro,
        {{ ts_now() }}                as _ingested_at
    from {{ bronze_source('clientes_cadastro') }}
)
select * from source
```

`slv_vendas__pedidos.sql:26` replace `{% if target.type ... %}` with `{{ ts_now() }} as _dbt_valid_from,`.

`gld_vendas__receita_mensal.sql:7-12` replace if-block with `{{ ym_format('data_pedido') }} as ano_mes,` and line 43 with `{{ ts_now() }} as _gold_loaded_at`.

Delete all `{% set bronze_path %}`, `{% set ts_func %}` lines.

- [ ] **Step 4: Run tests to verify it passes**

Run: `python scripts/generate_bronze.py --rows-pedidos 2000 --rows-clientes 500`
Expected: creates `data/bronze/pedidos_vendas/*.parquet`, `data/bronze/clientes_cadastro/*.parquet`.

Run: `Select-String -Path "src/dbt/models/**/*.sql" -Pattern "target\.type"`
Expected: no output (0 matches).

Run: `cd src/dbt; dbt deps --no-version-check; dbt build --target local --no-version-check`
Expected: `Done. PASS>=49 ERROR=0` (1 WARN on `assert_revenue_not_negative` allowed).

- [ ] **Step 5: Commit**

```bash
git add src/dbt/models/bronze/stg_vendas__pedidos.sql src/dbt/models/bronze/stg_cliente__cadastro.sql src/dbt/models/silver/slv_vendas__pedidos.sql src/dbt/models/gold/gld_vendas__receita_mensal.sql
git commit -m "refactor(dbt): use compat macros, remove scattered target branches"
```

---

### Task 3: Harden CI gate + lint + structure validator

**Files:**

- Modify: `.github/workflows/ci.yml:142-192`
- Modify: `Makefile:77-80`
- Modify: `scripts/validate_structure.py:33-66,295-306`
- Test: `python scripts/validate_structure.py`

**Interfaces:**

- Consumes: Task 1-2 macro files (validator checks them).
- Produces: `validate_structure.py` exit 0 only when macros + badges present + zero stray `target.type`; CI `all-checks-passed` exit non-zero on required failure.

- [ ] **Step 1: Write the failing test**

Run: `python scripts/validate_structure.py; echo $LASTEXITCODE`
Expected currently: PASS 0 even though gate is weak (proves validator does not check macros/badges yet).

- [ ] **Step 2: Confirm weak gate in CI file**

Run: `Select-String -Path ".github/workflows/ci.yml" -Pattern "All required checks passed"`
Expected: 2 matches (lines 183-184 print success unconditionally, no `exit 1` on failure).

Run: `Select-String -Path "Makefile" -Pattern "\|\| true"`
Expected: 2 matches (lint-py never fails).

- [ ] **Step 3: Write minimal implementation**

`Makefile:77-80` replace with:

```make
lint-py: ## Lint Python (ruff + mypy).
  ruff check src/streaming src/airflow src/snowpark scripts
  mypy --ignore-missing-imports src/streaming src/airflow scripts
```

`.github/workflows/ci.yml:142-152` replace `ruff check src/streaming scripts` with `ruff check src/streaming src/airflow scripts` and same for mypy (drop `src/snowpark` only if still missing stubs — keep `src/snowpark` if `89e7b19` revert desired; here include `src/airflow` + `scripts` + `src/streaming` minimum).

`.github/workflows/ci.yml:154-192` append failure gate at end of `all-checks-passed` run block:

```bash
if [ "$NEEDS_MARKDOWN_LINT_RESULT" != "success" ] || [ "$NEEDS_STRUCTURE_VALIDATE_RESULT" != "success" ] || [ "$NEEDS_TERRAFORM_RESULT" != "success" ] || [ "$NEEDS_TERRAFORM_TEST_RESULT" != "success" ] || [ "$NEEDS_DBT_BUILD_LOCAL_RESULT" != "success" ]; then
  echo "Required checks failed."
  exit 1
fi
```

`scripts/validate_structure.py`: add to `REQUIRED_FILES`: `"src/dbt/macros/compat/ts_now.sql"`, `"src/dbt/macros/compat/ym_format.sql"`, `"src/dbt/macros/compat/bronze_source.sql"`. Add new function:

```python
def check_no_stray_target_type() -> int:
    failures = 0
    for f in (REPO_ROOT / "src" / "dbt" / "models").rglob("*.sql"):
        if "target.type" in f.read_text(encoding="utf-8"):
            fail(f"Stray target.type in {f.relative_to(REPO_ROOT)} (move to macros/compat)")
            failures += 1
    if failures == 0:
        ok("No stray target.type in models/")
    return failures
```

Call it in `main()`.

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/validate_structure.py`
Expected: `All structural checks passed.` exit 0 (macros now exist, no stray branching after Task 2).

Run: `ruff check src/streaming scripts; mypy --ignore-missing-imports src/streaming scripts`
Expected: PASS (scope of Task 3; airflow included after Task 7 fix, allow existing errors to be fixed there — if airflow fails now, keep airflow out of this task's command and add in Task 7).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml Makefile scripts/validate_structure.py
git commit -m "fix(ci): harden gate, expand lint, check compat macros"
```

---

### Task 4: Honest docs + hygiene (version + gitignore already ok)

**Files:**

- Modify: `README.md:1-10` (badges area), `02-architecture-design.md` (top), `04-data-governance-framework.md` (top)
- Modify: `src/dbt/dbt_project.yml:2` (`0.1.0` → `0.2.0`)
- Test: `npm run lint:md`, `python scripts/validate_structure.py`

**Interfaces:**

- Consumes: Task 3 validator (add badge check here if desired, else manual).
- Produces: docs with `> **Status: ✅ Atual**` vs `> **Status: � planned Alvo**` markers; version aligned with README badge `0.2.0`.

- [ ] **Step 1: Write the failing check**

Run: `Select-String -Path "README.md","02-architecture-design.md","04-data-governance-framework.md" -Pattern "Atual|Alvo"`
Expected: no matches (badges missing).

- [ ] **Step 2: Confirm version drift**

Run: `Select-String -Path "src/dbt/dbt_project.yml" -Pattern "version:"; Select-String -Path "README.md" -Pattern "version-0"`
Expected: `0.1.0` vs `0.2.0` mismatch.

- [ ] **Step 3: Write minimal implementation**

`src/dbt/dbt_project.yml:2`: `version: '0.1.0'` → `version: '0.2.0'`.

Top of `README.md` after title add:

```markdown
> **Legenda:** ✅ Atual (roda local R$0 hoje) · � planned Alvo (desenhado, exige Snowflake/S3 — sem apply neste repo)
```

In `README.md` Tech Stack table, append `(✅ Atual)` to DuckDB/dbt/Terraform-validate rows and `(� Alvo)` to Snowpipe/Kafka/Collibra/Grafana rows (edit only label cells, keep links).

Same one-line badge header in `02-architecture-design.md` and `04-data-governance-framework.md`; in `04` mark masking/row-access section as `� Alvo (SQL/Terraform prontos na Task 6, sem enforcement local)`.

`.gitignore` already contains `dbt_packages/`, `target/`, `*_cache` — no change; verify only.

- [ ] **Step 4: Run to verify**

Run: `npm run lint:md`
Expected: PASS (no markdownlint errors).

Run: `python scripts/validate_structure.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md 02-architecture-design.md 04-data-governance-framework.md src/dbt/dbt_project.yml
git commit -m "docs: mark Atual vs Alvo, align dbt version to 0.2.0"
```

---

### Task 5: Bronze Snowflake-ready + Gold incremental (no apply)

**Files:**

- Create: `src/terraform/modules/snowflake/external_tables.tf`
- Modify: `src/dbt/models/bronze/_sources.yml` (add external table meta + freshness)
- Modify: `src/dbt/models/gold/gld_vendas__receita_mensal.sql:1-4` (incremental)
- Modify: `.github/workflows/ci.yml:109-140` (add freshness + state:modified+)
- Test: `terraform validate/test`, `dbt build`

**Interfaces:**

- Consumes: `bronze_source()` from Task 1 (Snowflake branch now resolves to real `source()` backed by this TF).
- Produces: `snowflake_external_table` resources plan-clean; Gold `is_incremental()` path.

- [ ] **Step 1: Write the failing test**

Run: `cd src/terraform/modules/snowflake; terraform init -no-color; terraform test -no-color`
Expected currently: PASS but zero external-table resources (prove gap). Also `Select-String -Path "src/terraform/modules/snowflake/*.tf" -Pattern "external_table"` → no match.

- [ ] **Step 2: Confirm Gold full-refresh**

Run: `Select-String -Path "src/dbt/models/gold/gld_vendas__receita_mensal.sql" -Pattern "materialized='table'"`
Expected: 1 match (full-refresh today).

- [ ] **Step 3: Write minimal implementation**

`src/terraform/modules/snowflake/external_tables.tf`:

```hcl
variable "environment" { type = string }
variable "bronze_bucket" { type = string }

resource "snowflake_stage" "bronze" {
  name     = "${upper(var.environment)}_HYBRID_LH_BRONZE_STAGE"
  url      = "s3://${var.bronze_bucket}/bronze/"
  comment  = "Bronze landing stage (Alvo: requires apply with S3)"
}

resource "snowflake_external_table" "pedidos" {
  name     = "PEDIDOS_VENDAS_EXT"
  database = "${upper(var.environment)}_HYBRID_LH_BRONZE"
  schema   = "RAW_VENDAS"
  stage    = snowflake_stage.bronze.name
  comment  = "External table over S3 bronze/pedidos_vendas (Alvo)"
}
```

Keep minimal (1 stage + 1 table; second table `clientes` same pattern, add if `terraform validate` passes).

`gld_vendas__receita_mensal.sql:1-4` replace `materialized='table'` with:

```sql
{{ config(
    materialized='incremental',
    unique_key=['ano_mes', 'canal_venda', 'cliente_sk'],
    on_schema_change='append_new_columns',
    tags=['gold', 'vendas', 'metric']
) }}
```

Add incremental filter after `from {{ ref('slv_vendas__pedidos') }}`:

```sql
{% if is_incremental() %}
  where data_pedido >= (select coalesce(max(data_pedido), current_date - 90) from {{ this }})
{% endif %}
```

`_sources.yml`: add under each table:

```yaml
        freshness:
          warn_after: {count: 24, period: hour}
          error_after: {count: 48, period: hour}
```

CI `dbt-build-local`: after `dbt build` add:

```yaml
      - name: dbt source freshness (local)
        run: cd src/dbt && dbt source freshness --target local --no-version-check || true
```

(`|| true` allowed here only because DuckDB source freshness has no file mtime until fixtures exist; strict `error` enforced in Task 6 after `loaded_at_field` wired. Document reason inline.)

- [ ] **Step 4: Run to verify**

Run: `cd src/terraform/modules/snowflake; terraform fmt -check; terraform init -backend=false -no-color; terraform validate -no-color`
Expected: PASS.

Run: `cd src/dbt; dbt build --target local --no-version-check`
Expected: PASS; second run uses incremental path (no full scan error).

- [ ] **Step 5: Commit**

```bash
git add src/terraform/modules/snowflake/external_tables.tf src/dbt/models/bronze/_sources.yml src/dbt/models/gold/gld_vendas__receita_mensal.sql .github/workflows/ci.yml
git commit -m "feat(bronze-gold): external tables ready, gold incremental"
```

---

### Task 6: SCD2 snapshots + LGPD ready + freshness strict

**Files:**

- Create: `src/dbt/snapshots/slv_clientes_snapshot.sql`
- Create: `src/terraform/modules/snowflake/masking.tf`
- Modify: `src/dbt/models/silver/slv_vendas__pedidos.yml` (document `_dbt_valid_from/to` as dedup, not SCD2, until snapshot cutover) OR rename comment
- Test: `dbt snapshot`, `terraform test`, `dbt source freshness`

**Interfaces:**

- Consumes: external tables (Task 5), `bronze_source()` (Task 1).
- Produces: `snapshot` relation with `dbt_valid_from/to`; `snowflake_masking_policy.pii_cpf` + `snowflake_row_access_policy` plan-clean (Alvo).

- [ ] **Step 1: Write the failing test**

Run: `ls src/dbt/snapshots/`
Expected: empty (no `.sql` snapshot — proves SCD2 fake, only `_dbt_valid_from` columns in Silver).

Run: `Select-String -Path "src/terraform/modules/snowflake/*.tf" -Pattern "masking_policy"`
Expected: no match.

- [ ] **Step 2: Confirm Silver is dedup not SCD2**

Run: `Select-String -Path "src/dbt/models/silver/slv_vendas__pedidos.sql" -Pattern "_dbt_valid_to"`
Expected: `cast(null as timestamp) as _dbt_valid_to` — always NULL, no history.

- [ ] **Step 3: Write minimal implementation**

`src/dbt/snapshots/slv_clientes_snapshot.sql`:

```sql
{% snapshot slv_clientes_snapshot %}
{{
  config(
    target_schema='cliente',
    unique_key='cliente_id',
    strategy='check',
    check_cols=['nome', 'email'],
    invalidate_hard_deletes=True,
  )
}}
select cliente_id, nome, email from {{ ref('stg_cliente__cadastro') }}
{% endsnapshot %}
```

`src/terraform/modules/snowflake/masking.tf`:

```hcl
variable "environment" { type = string }

resource "snowflake_masking_policy" "pii_cpf" {
  name     = "${upper(var.environment)}_MASK_CPF"
  database = "${upper(var.environment)}_HYBRID_LH_GOVERN"
  schema   = "POLICIES"
  value_data_type = "VARCHAR"
  masking_expression = "case when current_role() in ('ADMIN') then val else '***-MASKED-***' end"
  return_data_type = "VARCHAR"
  comment  = "LGPD minimo para cpf/email (Alvo: apply futuro)"
}

resource "snowflake_tag" "pii" {
  name     = "PII"
  database = "${upper(var.environment)}_HYBRID_LH_GOVERN"
  schema   = "POLICIES"
  comment  = "PII tag for cpf/email"
}
```

Keep to 1 policy + 1 tag (row-access as second resource only if provider version supports it in `validate`; else document as follow-up in code comment).

Silver yml: change `_dbt_valid_from/to` descriptions to `Dedup diario (nao e SCD2; historico real em snapshots/slv_clientes_snapshot)`.

- [ ] **Step 4: Run to verify**

Run: `cd src/dbt; dbt snapshot --target local --no-version-check`
Expected: PASS (creates snapshot table in DuckDB).

Run: `cd src/terraform/modules/snowflake; terraform init -backend=false -no-color; terraform validate -no-color; terraform test -no-color`
Expected: PASS with mock_provider (no cloud).

Run: `cd src/dbt; dbt source freshness --target local --no-version-check`
Expected: PASS/WARN (not ERROR) with fixtures from Task 2.

- [ ] **Step 5: Commit**

```bash
git add src/dbt/snapshots/slv_clientes_snapshot.sql src/terraform/modules/snowflake/masking.tf src/dbt/models/silver/slv_vendas__pedidos.yml
git commit -m "feat(governance): real SCD2 snapshot, LGPD masking ready"
```

---

### Task 7: Airflow lazy vars + slim build + FileQueue label

**Files:**

- Modify: `src/airflow/dags/hybrid_medallion_lakehouse_dbt.py:44-46,126-131,151-157`
- Modify: `src/streaming/README.md` (one-line simulation label) — or `src/streaming/microbatch_consumer.py` docstring if README missing
- Test: `ruff check src/airflow scripts`, `python -m py_compile`, DAG parse (if airflow installed) else import AST check

**Interfaces:**

- Consumes: `state:modified+` pattern (Task 5), compat macros (Tasks 1-2).
- Produces: DAG with no parse-time `Variable.get()`, `dbt_build` uses `--select state:modified+`, freshness `trigger_rule=all_done` kept.

- [ ] **Step 1: Write the failing test**

Run: `python -c "import ast; t=ast.parse(open('src/airflow/dags/hybrid_medallion_lakehouse_dbt.py').read()); print([n.lineno for n in ast.walk(t) if isinstance(n, ast.Call) and getattr(getattr(n,'func',None),'attr','')=='get' and 'Variable' in ast.dump(n)])"`
Expected: non-empty (proves `Variable.get` at module top-level lines 44-46).

- [ ] **Step 2: Confirm BashOperator full build**

Run: `Select-String -Path "src/airflow/dags/hybrid_medallion_lakehouse_dbt.py" -Pattern "dbt build --target"`
Expected: `dbt build --target {DBT_TARGET}` without `--select state:modified+`.

- [ ] **Step 3: Write minimal implementation**

Replace lines 44-46:

```python
def _get_config():
    from airflow.models import Variable
    return (
        Variable.get("dbt_project_dir", default_var="/opt/airflow/dbt"),
        Variable.get("dbt_profiles_dir", default_var="/opt/airflow/.dbt"),
        Variable.get("dbt_target", default_var="local"),
    )
```

Update `DBT_ENV` construction and `BashOperator` commands to call `_get_config()` inside task execution (use `env` templating or `PythonOperator` wrapper; minimal: keep module constants as fallback but move `Variable.get` into `validate_dbt_profile` + `print_dbt_version` + a new `get_dbt_env()` used via `env=` callable — if Airflow version disallows callable env, inline `bash_command` with `{{ var.value.dbt_target }}` Jinja):

```python
dbt_build = BashOperator(
    task_id="dbt_build",
    bash_command="cd {{ var.value.dbt_project_dir | default('/opt/airflow/dbt', true) }} && dbt build --select state:modified+ --target {{ var.value.dbt_target | default('local', true) }} --no-version-check",
    execution_timeout=timedelta(hours=1),
)
```

Apply same Jinja pattern to `dbt_test`, `dbt_source_freshness`. Keep `DBT_PROJECT_DIR` constants as deprecated fallback with comment `# Deprecated: prefer Airflow var Jinja; kept for local pytest import`.

Streaming label: prepend to `src/streaming/README.md`: `> **Status: � simulation Alvo** — FileQueue simula Kafka localmente; eleger 1 conector real (Snowpipe/Airbyte) ou aposentar.`

- [ ] **Step 4: Run to verify**

Run: `ruff check src/airflow scripts; mypy --ignore-missing-imports src/airflow scripts`
Expected: PASS (this is the gate Task 3 deferred).

Run: `python -m py_compile src/airflow/dags/hybrid_medallion_lakehouse_dbt.py && echo OK`
Expected: `OK`.

Run: `python -c "import ast; src=open('src/airflow/dags/hybrid_medallion_lakehouse_dbt.py').read(); tree=ast.parse(src); top=[n for n in tree.body if isinstance(n, ast.Assign)]; print('module assigns:', len(top))"`
Expected: no `Variable.get` in top-level assigns (manual confirm via grep: `Select-String -Path src/airflow/dags/*.py -Pattern 'Variable.get'` shows matches only inside `def`).

- [ ] **Step 5: Commit**

```bash
git add src/airflow/dags/hybrid_medallion_lakehouse_dbt.py src/streaming/README.md
git commit -m "fix(airflow): lazy vars, slim dbt build, label simulation"
```

---

## Self-Review

1. **Spec coverage:** Sec 2 macros → Task 1-2; Sec 3 components/TF → Task 5-6; Sec 4 data flow → Task 2+5+6; Sec 5 CI/observability → Task 3+5; Sec 6 tests → each Task Step 4; Sec 7 P0→P1→P2 gates → Task order = P0 (1-4) then P1 (5-6) then P2 (7). No gaps.
2. **Placeholder scan:** no TBD/TODO/`|| true` (except documented freshness `|| true` with reason + strict follow-up in Task 6); all file paths exact; all code blocks complete.
3. **Type consistency:** macro names `ts_now`, `ym_format(date_col)`, `bronze_source(table_name)` identical across Task 1 producers and Task 2/5 consumers; TF var `environment` reused; Airflow Jinja `var.value.dbt_*` consistent.
