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
    -- Incremental watermark on ano_mes (via gold_watermark()): recompute the
    -- last N whole months from max Gold ano_mes so in-window late-arriving
    -- Silver rows are absorbed by the merge on unique_key.
    -- LIMIT (documented): Silver rows older than the watermark window are
    -- skipped on incremental runs; a --full-refresh picks them up.
    {% if is_incremental() %}
        and {{ ym_format('data_pedido') }} >= {{ gold_watermark() }}
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
