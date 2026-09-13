# Arquitetura 9 — Núcleo dbt/Medallion — Design

{% raw %}
**Date:** 2026-09-13
**Status:** Approved
**Scope:** Núcleo dbt/Medallion, zero cloud cost, Snowflake-ready
**Baseline:** arquitetura 7.5/10 (tech reassessment @651710a)
**Meta:** arquitetura ~9/10

## 1. Context

O reassessment apontou que o teto da arquitetura (7.5) vem de incoerências criadas pelos próprios PRs anteriores: `macros/three_days_ago.sql` morta (ninguém usa), janelas `current_date - 3/-90` hardcoded inline nos models, `dbt_project.yml` com defaults que mentem (silver=`merge` vs model `delete+insert`, gold=`table` vs model `incremental`), e ausência de contratos/exposures fechando o lineage até o consumo.

## 2. Macros compat completas (Approved)

Nova macro `lookback_filter(date_col, days)` em `src/dbt/macros/compat/lookback_filter.sql`:

- DuckDB: `{{ date_col }} >= current_date - {{ days }}`
- Snowflake: `{{ date_col }} >= dateadd('day', -{{ days }}, current_date)`

`src/dbt/macros/three_days_ago.sql` é **deletado** (macro morta eliminada, não movida). Silver usa `{{ lookback_filter('data_pedido', 3) }}`, Gold usa `{{ lookback_filter('data_pedido', 90) }}`. A partir daqui, zero aritmética de data inline em `models/` — `scripts/validate_structure.py` ganha `check_no_inline_windows()` barrando `current_date - N` fora de `macros/`, espelhando `check_no_stray_target_type`.

Isolation: cada macro tem um propósito, chamada sem ler internals, testada via `dbt parse` + `dbt build` local.

## 3. Estratégias canônicas + defaults honestos (Approved)

`src/dbt/models/silver/slv_vendas__pedidos.sql`: `incremental_strategy` `delete+insert` → `merge`, mantendo `unique_key='pedido_id'`, dedup `row_number` e `on_schema_change='append_new_columns'`. Troca só o mecanismo de escrita.

`src/dbt/dbt_project.yml`: silver declara `merge` + `unique_key` de verdade; gold declara `incremental`. Nenhum default mente após isso — o yml vira contrato legível da arquitetura.

## 4. Contratos mínimos + exposures (Approved)

Sem enforcement no banco (YAGNI, DuckDB local): `data_type` + `constraints: not_null` documentados nos schema yml das chaves (`pedido_id`, `cliente_id`); cobertura via `unique/not_null/relationships` existentes em `dbt test`. Novo `src/dbt/models/gold/_exposures.yml` declara `gld_vendas__receita_mensal` como exposta a BI (dono + descrição). Menor contrato que fecha Bronze→Silver→Gold→consumo sem custo cloud.

## 5. ADR + testes (Approved)

ADR curta em `docs/architecture/` registrando: merge canônico na Silver, `lookback_filter`, defaults como contrato, e o que ficou de fora (row-access, backend remoto, freshness estrito, snowpark no lint).

Testes (todos R$0): `dbt build --target local` verde (inclui snapshot), `scripts/validate_structure.py` com as 2 travas (stray `target.type` + inline windows), `dbt parse --target local` sem erro, `npm run lint:md` verde.

## 6. Gates

Gate de aceite: `dbt build --target local` PASS; grep `target.type` em `models/` = 0; grep `current_date -` em `models/` = 0; `three_days_ago.sql` inexistente; defaults do yml == estratégias dos models; CI verde na main.

Fora de escopo (YAGNI): row-access, backend S3, `terraform plan`, snowpark no lint, freshness estrito, Kafka-vs-FileQueue.
{% endraw %}
