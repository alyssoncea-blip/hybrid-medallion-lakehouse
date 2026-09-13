{{ config(
    materialized='incremental',
    unique_key=['ano_mes', 'canal_venda', 'cliente_sk'],
    on_schema_change='append_new_columns',
    tags=['gold', 'vendas', 'metric']
) }}

with pedidos as (
    select
        {{ ym_format('data_pedido') }} as ano_mes,
        canal_venda,
        cliente_sk,
        valor_total,
        status
    from {{ ref('slv_vendas__pedidos') }}
    where status in ('PAGO', 'FATURADO', 'CANCELADO', 'DEVOLVIDO')
    -- Task 5 correction: plan sketch filtered `{{ this }}` (Gold) by
    -- max(data_pedido), but Gold has no data_pedido column (it groups by
    -- ano_mes). Use a Silver-native static recency window instead.
    {% if is_incremental() %}
        and {{ lookback_filter('data_pedido', 90) }}
    {% endif %}
),

agg as (
    select
        ano_mes,
        canal_venda,
        cliente_sk,
        sum(case when status in ('PAGO','FATURADO') then valor_total else 0 end) as receita_bruta,
        sum(case when status = 'CANCELADO'         then valor_total else 0 end) as cancelamentos,
        sum(case when status = 'DEVOLVIDO'         then valor_total else 0 end) as devolucoes,
        count(*)                                                              as qtd_pedidos
    from pedidos
    group by 1, 2, 3
)

select
    ano_mes,
    canal_venda,
    cliente_sk,
    receita_bruta,
    receita_bruta - cancelamentos - devolucoes    as receita_liquida,
    cancelamentos,
    devolucoes,
    qtd_pedidos,
    {{ ts_now() }} as _gold_loaded_at
from agg
