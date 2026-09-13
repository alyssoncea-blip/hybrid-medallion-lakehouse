-- Gold recency (severity warn): Gold must cover Silver's latest month.
-- SLA: max Gold ano_mes may not lag behind the month of Silver
-- max(data_pedido). Rows = months Gold is behind -> FAIL (warn for now;
-- promote to error once the incremental watermark is battle-tested).
-- Scoped to Gold-eligible statuses ('ABERTO' never reaches Gold by design).
{{ config(severity='error') }}

with silver_max as (
    select max(data_pedido) as max_data_pedido
    from {{ ref('slv_vendas__pedidos') }}
    where status in ('PAGO', 'FATURADO', 'CANCELADO', 'DEVOLVIDO')
),
gold_max as (
    select max(ano_mes) as max_ano_mes
    from {{ ref('gld_vendas__receita_mensal') }}
)
select
    {{ ym_format('silver_max.max_data_pedido') }} as silver_ano_mes,
    gold_max.max_ano_mes as gold_ano_mes
from silver_max
cross join gold_max
where gold_max.max_ano_mes < {{ ym_format('silver_max.max_data_pedido') }}
