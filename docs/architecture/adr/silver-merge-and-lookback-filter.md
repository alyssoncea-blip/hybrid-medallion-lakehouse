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
