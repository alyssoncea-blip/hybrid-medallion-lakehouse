-- Late-data coverage (severity warn): every Silver
-- (ano_mes, canal_venda, cliente_sk) inside the watermark window must already
-- be reflected in Gold. Returned rows = FAIL (warn for now; promote to error
-- once the incremental watermark is battle-tested).
-- Scoped to Gold-eligible statuses ('ABERTO' never reaches Gold by design).
{{ config(severity='warn') }}

with silver_keys as (
    select distinct
        {{ ym_format('data_pedido') }} as ano_mes,
        canal_venda,
        cliente_sk
    from {{ ref('slv_vendas__pedidos') }}
    where status in ('PAGO', 'FATURADO', 'CANCELADO', 'DEVOLVIDO')
        and {{ ym_format('data_pedido') }} >= {{ gold_watermark(relation=ref('gld_vendas__receita_mensal')) }}
),
gold_keys as (
    select ano_mes, canal_venda, cliente_sk
    from {{ ref('gld_vendas__receita_mensal') }}
)
select
    s.ano_mes,
    s.canal_venda,
    s.cliente_sk
from silver_keys s
left join gold_keys g
    on s.ano_mes = g.ano_mes
    and s.canal_venda = g.canal_venda
    and s.cliente_sk = g.cliente_sk
where g.ano_mes is null
