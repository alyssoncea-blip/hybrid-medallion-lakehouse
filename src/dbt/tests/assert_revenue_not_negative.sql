-- Generic singular test: revenue cannot be negative
select
    ano_mes,
    canal_venda,
    cliente_sk,
    receita_liquida
from {{ ref('gld_vendas__receita_mensal') }}
where receita_liquida < 0
