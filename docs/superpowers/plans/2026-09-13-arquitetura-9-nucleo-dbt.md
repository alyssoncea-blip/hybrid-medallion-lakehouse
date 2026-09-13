# Arquitetura 9 Núcleo dbt Implementation Plan

{% raw %}
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the architecture gaps to ~9/10: single-ownership date windows, canonical merge Silver, honest project defaults, minimal contracts.

**Architecture:** All branching lives in `src/dbt/macros/compat/`; models contain zero `target.type` and zero inline date arithmetic; `dbt_project.yml` defaults match model strategies; validator enforces both rules.

**Tech Stack:** dbt-core 1.11 + dbt-duckdb (local target), Python validator, GitHub Actions (unchanged).

## Global Constraints

- Zero cloud cost: local target only, no `terraform apply`, no Snowflake secrets, no new dependencies.
- Conventional Commits on every commit.
- No `target.type` outside `src/dbt/macros/` (existing rule, keep green).
- No inline date windows (`current_date - N`) outside `src/dbt/macros/` (new rule from Task 1 on).
- YAGNI: no constraint enforcement in the database, no new dbt packages, no CI workflow changes.
- Do NOT break CI/tests: every task ends with `validate_structure` PASS + `dbt build --target local` PASS + `lint:md` PASS when md touched.

---

## File Structure

- `src/dbt/macros/compat/lookback_filter.sql` (new) — single `lookback_filter(date_col, days)` macro, sole owner of recency-window branching.
- `src/dbt/macros/three_days_ago.sql` (deleted) — dead macro, logic absorbed by `lookback_filter`.
- `src/dbt/models/silver/slv_vendas__pedidos.sql` — consumes `lookback_filter`, strategy `merge`.
- `src/dbt/models/gold/gld_vendas__receita_mensal.sql` — consumes `lookback_filter`, keeps Task 5 comment.
- `src/dbt/dbt_project.yml` — honest layer defaults (silver `merge`, gold `incremental`).
- `scripts/validate_structure.py` — new `check_no_inline_windows()`, wired in `main()`.
- `src/dbt/models/silver/slv_vendas__pedidos.yml` — `data_type` documented on keys.
- `src/dbt/models/gold/_exposures.yml` (new) — BI exposure for the Gold mart.
- `docs/architecture/adr/silver-merge-and-lookback-filter.md` (new) — decision record.

---

### Task 1: lookback_filter macro + retire three_days_ago + enforce

**Files:**

- Create: `src/dbt/macros/compat/lookback_filter.sql`
- Delete: `src/dbt/macros/three_days_ago.sql`
- Modify: `src/dbt/models/silver/slv_vendas__pedidos.sql:9-14`
- Modify: `src/dbt/models/gold/gld_vendas__receita_mensal.sql:20-22`
- Modify: `scripts/validate_structure.py` (add function + wire in `main()`)

**Interfaces:**

- Consumes: `target.type`, nothing else.
- Produces: `lookback_filter(date_col, days)` → SQL predicate string. Task 2 consumes nothing from Task 1 except the green gate.

- [ ] **Step 1: Add the validator check first (failing test)**

Add to `scripts/validate_structure.py`, right after `check_no_stray_target_type` (lines 265-274):

```python
def check_no_inline_windows() -> int:
    banner("No inline date windows in models/")
    failures = 0
    pattern = re.compile(r"current_date\s*-\s*\d+")
    for f in (REPO_ROOT / "src" / "dbt" / "models").rglob("*.sql"):
        if pattern.search(f.read_text(encoding="utf-8")):
            fail(f"Inline date window in {f.relative_to(REPO_ROOT)} (use lookback_filter() from macros/compat)")
            failures += 1
    if failures == 0:
        ok("No inline date windows in models/")
    return failures
```

Wire it in `main()` after `total += check_no_stray_target_type()`:

```python
    total += check_no_inline_windows()
```

(`re` is already imported at the top of the file for the commit check — do NOT add another import.)

- [ ] **Step 2: Run validator to verify it fails**

Run: `python scripts/validate_structure.py`
Expected: FAIL with `Inline date window in src/dbt/models/silver/slv_vendas__pedidos.sql` and `.../gold/gld_vendas__receita_mensal.sql`, summary `2 check(s) failed.`

- [ ] **Step 3: Write the macro + migrate the models + delete the dead file**

`src/dbt/macros/compat/lookback_filter.sql`:

```sql
{% macro lookback_filter(date_col, days) %}
  {% if target.type == 'snowflake' %}{{ date_col }} >= dateadd('day', -{{ days }}, current_date){% else %}{{ date_col }} >= current_date - {{ days }}{% endif %}
{% endmacro %}
```

`slv_vendas__pedidos.sql` lines 11-13 replace with:

```sql
    {% if is_incremental() %}
      where {{ lookback_filter('data_pedido', 3) }}
    {% endif %}
```

`gld_vendas__receita_mensal.sql` lines 20-22 replace with:

```sql
    {% if is_incremental() %}
        and {{ lookback_filter('data_pedido', 90) }}
    {% endif %}
```

Keep the Task 5 explanatory comment above (lines 17-19) untouched. Delete `src/dbt/macros/three_days_ago.sql` via `git rm`.

- [ ] **Step 4: Run all gates to verify green**

Run: `python scripts/validate_structure.py`
Expected: `All structural checks passed.`, exit 0 (shows `PASS No inline date windows in models/`).

Run: `cd src/dbt; dbt parse --target local --no-version-check`
Expected: PASS, no macro errors.

Run fixtures only if missing: if `data/bronze/pedidos_vendas/` is empty, run `python scripts/generate_bronze.py --rows-pedidos 2000 --rows-clientes 500`. If fixtures already exist, do NOT regenerate (the generator appends and duplicates rows).

Run: `cd src/dbt; dbt build --target local --no-version-check`
Expected: `PASS>=49 ERROR=0` (1 WARN on `assert_revenue_not_negative` allowed).

- [ ] **Step 5: Commit**

```bash
git add src/dbt/macros/compat/lookback_filter.sql src/dbt/models/silver/slv_vendas__pedidos.sql src/dbt/models/gold/gld_vendas__receita_mensal.sql scripts/validate_structure.py
git rm -q src/dbt/macros/three_days_ago.sql
git commit -m "refactor(dbt): centralize recency windows in lookback_filter, retire three_days_ago"
```

---

### Task 2: Canonical merge Silver + honest project defaults

**Files:**

- Modify: `src/dbt/models/silver/slv_vendas__pedidos.sql:1-7`
- Modify: `src/dbt/dbt_project.yml:31-44`
- Test: `dbt build --target local` (full + repeat for incremental path)

**Interfaces:**

- Consumes: green gate from Task 1, `lookback_filter` (already used in the model).
- Produces: model strategies equal project defaults. Task 3 consumes nothing except the green gate.

- [ ] **Step 1: Show the drift (failing condition)**

Run: `Select-String -Path "src/dbt/dbt_project.yml" -Pattern "incremental_strategy|materialized"`
Expected: silver `merge` vs model `delete+insert` (line 3 of the model), gold `table` vs model `incremental` — drift confirmed.

- [ ] **Step 2: Confirm current build is green before changing strategy**

Run: `cd src/dbt; dbt build --target local --no-version-check`
Expected: PASS (baseline; proves any later failure comes from this task).

- [ ] **Step 3: Write minimal implementation**

`slv_vendas__pedidos.sql` line 3: `incremental_strategy='delete+insert',` → `incremental_strategy='merge',`. Nothing else in the file changes (unique_key, dedup, schema change handling stay).

`dbt_project.yml` lines 39-40: `+materialized: table` → `+materialized: incremental` under `gold:`. Silver block already says `merge` — untouched.

- [ ] **Step 4: Run build twice to verify both paths**

Run: `cd src/dbt; dbt build --target local --no-version-check`
Expected: PASS (full build with new merge strategy).

Run it again immediately:
Expected: PASS (second run exercises `is_incremental()` + merge path with `lookback_filter`).

Run: `python scripts/validate_structure.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dbt/models/silver/slv_vendas__pedidos.sql src/dbt/dbt_project.yml
git commit -m "refactor(dbt): canonical merge silver, honest gold default"
```

---

### Task 3: Minimal contracts + exposure + ADR

**Files:**

- Modify: `src/dbt/models/silver/slv_vendas__pedidos.yml` (add `data_type` on keys)
- Create: `src/dbt/models/gold/_exposures.yml`
- Create: `docs/architecture/adr/silver-merge-and-lookback-filter.md`
- Test: `dbt build`, `validate_structure`, `npm run lint:md`

**Interfaces:**

- Consumes: green gate from Task 2.
- Produces: nothing downstream (last task). Docs only + yml metadata.

- [ ] **Step 1: Write the failing check (exposure missing)**

Run: `Test-Path -LiteralPath "src/dbt/models/gold/_exposures.yml"`
Expected: False (file does not exist yet).

- [ ] **Step 2: Confirm models yml lacks data_type**

Run: `Select-String -Path "src/dbt/models/silver/slv_vendas__pedidos.yml" -Pattern "data_type"`
Expected: no matches.

- [ ] **Step 3: Write minimal implementation**

In `slv_vendas__pedidos.yml`, add `data_type: varchar` to the `pedido_sk`, `pedido_id` and `cliente_sk` column entries (documentation only — DuckDB ignores it at runtime, zero behavior change). Example for one entry:

```yaml
      - name: pedido_id
        description: ID natural do pedido vindo da fonte.
        data_type: varchar
        tests:
          - not_null
```

Do NOT add `constraints:` blocks (enforcement is out of scope and could break the DuckDB build).

`src/dbt/models/gold/_exposures.yml`:

```yaml
version: 2

exposures:
  - name: receita_mensal_bi
    description: Receita liquida mensal por canal e cliente para dashboards de BI.
    type: dashboard
    owner:
      name: data-engineering
    depends_on:
      - ref('gld_vendas__receita_mensal')
```

`docs/architecture/adr/silver-merge-and-lookback-filter.md`:

```markdown
# ADR: Silver em merge + lookback_filter + defaults como contrato

## Status

Accepted (2026-09-13).

## Context

A Silver usava `delete+insert` enquanto o default declarava `merge`; a Gold usava `incremental` enquanto o default declarava `table`. Janelas de recencia (`-3`, `-90` dias) estavam hardcoded nos models e a macro `three_days_ago` estava morta.

## Decision

- Silver canonica em `merge` com `unique_key='pedido_id'`.
- Janelas via `lookback_filter(date_col, days)` em `macros/compat/`; `three_days_ago.sql` removida.
- Defaults do `dbt_project.yml` espelham as estrategias reais.
- Contratos minimos via `data_type` + testes; exposure `receita_mensal_bi` declara o consumo de BI.

## Consequences

- DRY obrigatorio: validator barra `target.type` e janelas inline em `models/`.
- De fora (futuro): row-access policy, backend S3, `terraform plan`, snowpark no lint, freshness estrito.
```

- [ ] **Step 4: Run all gates to verify green**

Run: `cd src/dbt; dbt build --target local --no-version-check`
Expected: PASS (exposures parse, data_type ignored by DuckDB).

Run: `python scripts/validate_structure.py`
Expected: PASS (also validates the new yml files parse).

Run: `npm run lint:md`
Expected: PASS (ADR must be lint-clean; keep lines short, blank lines around lists).

- [ ] **Step 5: Commit**

```bash
git add src/dbt/models/silver/slv_vendas__pedidos.yml src/dbt/models/gold/_exposures.yml docs/architecture/adr/silver-merge-and-lookback-filter.md
git commit -m "docs(dbt): minimal contracts, gold exposure, merge ADR"
```

---

## Self-Review

1. **Spec coverage:** Sec 2 macro → Task 1; Sec 3 merge+defaults → Task 2; Sec 4 contracts/exposures → Task 3; Sec 5 ADR+tests → Task 3 + per-task Step 4 gates. No gaps.
2. **Placeholder scan:** no TBD/TODO/`|| true`/vague steps; every code change shows exact code; every test step shows exact command + expected output.
3. **Type consistency:** `lookback_filter(date_col, days)` identical in Task 1 definition and Task 1-2 usages; `check_no_inline_windows` name identical in code, wire-up and gate expectations; file paths identical across tasks.
{% endraw %}
