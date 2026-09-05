-- Generic singular test: ensure no future-dated orders slip into Gold
select
    pedido_id,
    data_pedido,
    current_date as today
from {{ ref('slv_vendas__pedidos') }}
where data_pedido > current_date
