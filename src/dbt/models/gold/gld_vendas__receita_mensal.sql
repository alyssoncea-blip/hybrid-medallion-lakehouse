{{ config(
    materialized='table',
    tags=['gold', 'vendas', 'metric']
) }}

with pedidos as (
    select
        to_char(data_pedido, 'YYYY-MM') as ano_mes,
        canal_venda,
        cliente_sk,
        valor_total,
        status
    from {{ ref('slv_vendas__pedidos') }}
    where status in ('PAGO', 'FATURADO', 'CANCELADO', 'DEVOLVIDO')
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
    current_timestamp()                            as _gold_loaded_at
from agg
